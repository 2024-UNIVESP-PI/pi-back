from decimal import Decimal

from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from .models import Caixa, Ficha, MovimentacaoEstoque, Produto, QRCodeReserva, Venda
from .serializers import VendaSerializer


class TestEstoquePersistence(TestCase):
    def setUp(self):
        self.caixa = Caixa.objects.create(
            nome="Caixa Principal",
            usuario="caixa",
            senha="123",
        )
        self.produto = Produto.objects.create(
            caixa=self.caixa,
            nome="Pastel",
            medida="UN",
            preco=Decimal("5.00"),
        )

    def test_movimentacoes_update_product_stock(self):
        MovimentacaoEstoque.objects.create(
            caixa=self.caixa,
            produto=self.produto,
            quantidade=10,
            tipo="E",
        )

        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 10)

        MovimentacaoEstoque.objects.create(
            caixa=self.caixa,
            produto=self.produto,
            quantidade=3,
            tipo="S",
        )

        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque, 7)

    def test_failed_sale_rolls_back_stock_movement(self):
        MovimentacaoEstoque.objects.create(
            caixa=self.caixa,
            produto=self.produto,
            quantidade=2,
            tipo="E",
        )
        ficha = Ficha.objects.create(numero=1, saldo=Decimal("1.00"))

        serializer = VendaSerializer(data={
            "ficha": ficha.id,
            "movimentacao": {
                "caixa": self.caixa.id,
                "produto": self.produto.id,
                "quantidade": 1,
            },
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)

        with self.assertRaises(ValidationError):
            serializer.save()

        self.produto.refresh_from_db()
        ficha.refresh_from_db()
        self.assertEqual(self.produto.estoque, 2)
        self.assertEqual(ficha.saldo, Decimal("1.00"))
        self.assertEqual(Venda.objects.count(), 0)
        self.assertEqual(MovimentacaoEstoque.objects.count(), 1)

    def test_existing_stock_movement_cannot_change_product_or_type(self):
        outro_produto = Produto.objects.create(
            caixa=self.caixa,
            nome="Suco",
            medida="UN",
            preco=Decimal("4.00"),
        )
        movimentacao = MovimentacaoEstoque.objects.create(
            caixa=self.caixa,
            produto=self.produto,
            quantidade=5,
            tipo="E",
        )

        movimentacao.produto = outro_produto
        with self.assertRaises(ValidationError):
            movimentacao.save()

        movimentacao.refresh_from_db()
        movimentacao.tipo = "S"
        with self.assertRaises(ValidationError):
            movimentacao.save()

    def test_sale_keeps_historical_price_after_product_price_changes(self):
        MovimentacaoEstoque.objects.create(
            caixa=self.caixa,
            produto=self.produto,
            quantidade=2,
            tipo="E",
        )
        ficha = Ficha.objects.create(numero=2, saldo=Decimal("20.00"))
        movimentacao = MovimentacaoEstoque.objects.create(
            caixa=self.caixa,
            produto=self.produto,
            quantidade=2,
            tipo="S",
        )
        venda = Venda.objects.create(movimentacao=movimentacao, ficha=ficha)

        self.assertEqual(venda.valor_unitario, Decimal("5.00"))
        self.assertEqual(venda.preco_total, Decimal("10.00"))

        self.produto.preco = Decimal("8.00")
        self.produto.save()
        venda.refresh_from_db()

        self.assertEqual(venda.preco_total, Decimal("10.00"))


class TestFichaPersistence(TestCase):
    def test_recarga_action_uses_validated_decimal_value(self):
        caixa = Caixa.objects.create(
            nome="Caixa Principal",
            usuario="caixa",
            senha="123",
        )
        ficha = Ficha.objects.create(numero=10, saldo=Decimal("2.50"))

        response = self.client.post(
            f"/movimentacao/fichas/{ficha.id}/recarga/",
            data={
                "valor": "7.25",
                "caixa_id": caixa.id,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        ficha.refresh_from_db()
        self.assertEqual(ficha.saldo, Decimal("9.75"))
        self.assertEqual(ficha.recargas.count(), 1)


class TestAuthenticationPersistence(TestCase):
    def test_caixa_password_is_hashed_and_login_still_works(self):
        caixa = Caixa.objects.create(
            nome="Caixa Principal",
            usuario="caixa",
            senha="123",
        )

        caixa.refresh_from_db()
        self.assertNotEqual(caixa.senha, "123")
        self.assertTrue(check_password("123", caixa.senha))

        response = self.client.post(
            "/movimentacao/caixas/login/",
            data={"usuario": "caixa", "senha": "123"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("senha", response.json())

    @override_settings(ADMIN_USERNAME="admin", ADMIN_PASSWORD="secret")
    def test_admin_login_uses_backend_settings(self):
        response = self.client.post(
            "/movimentacao/admin-login/",
            data={"username": "admin", "password": "secret"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"is_admin": True})

    @override_settings(ADMIN_USERNAME="admin", ADMIN_PASSWORD="secret")
    def test_admin_login_rejects_invalid_credentials(self):
        response = self.client.post(
            "/movimentacao/admin-login/",
            data={"username": "admin", "password": "wrong"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)


class TestQRCodeReservationFlow(TestCase):
    def setUp(self):
        self.caixa = Caixa.objects.create(
            nome="Caixa Principal",
            usuario="caixa",
            senha="123",
        )
        self.produto_permitido = Produto.objects.create(
            caixa=self.caixa,
            nome="Bolo",
            medida="UN",
            preco=Decimal("6.00"),
            disponivel_reserva=True,
            limite_reserva=2,
            quantidade_reserva_disponivel=5,
        )
        self.produto_fora_qr = Produto.objects.create(
            caixa=self.caixa,
            nome="Suco",
            medida="UN",
            preco=Decimal("4.00"),
            disponivel_reserva=True,
            limite_reserva=2,
            quantidade_reserva_disponivel=5,
        )
        self.qr_code = QRCodeReserva.objects.create(
            codigo="RESERVA-TESTE",
            descricao="Reserva Teste",
            ativo=True,
        )
        self.qr_code.produtos_disponiveis.set([self.produto_permitido])

    def test_public_products_returns_availability_for_qr_products_only(self):
        response = self.client.get(
            "/movimentacao/reservas-publicas/RESERVA-TESTE/produtos/"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["produtos"]), 1)
        self.assertEqual(data["produtos"][0]["id"], self.produto_permitido.id)
        self.assertEqual(data["produtos"][0]["disponivel"], 5)
        self.assertEqual(data["produtos"][0]["reservado"], 0)

    def test_public_reservation_rejects_product_outside_qr_code(self):
        response = self.client.post(
            "/movimentacao/reservas-publicas/criar/",
            data={
                "nome_completo": "Maria Silva",
                "cpf": "12345678901",
                "qr_code": "RESERVA-TESTE",
                "produtos": [
                    {
                        "produto_id": self.produto_fora_qr.id,
                        "quantidade": 1,
                    }
                ],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("não está disponível neste QR code", response.json()["error"])
