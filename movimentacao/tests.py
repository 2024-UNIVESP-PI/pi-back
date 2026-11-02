from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.core import signing
from django.core.management import call_command
from django.db.models import Sum
from django.test import TestCase, override_settings
from unittest.mock import patch
from django.utils import timezone

from .models import (
    Caixa,
    Ficha,
    MovimentacaoEstoque,
    Produto,
    QRCodeReserva,
    Recarga,
    ReservaProduto,
    Venda,
)
from .serializers import VendaSerializer
from publico.models import Sugestao
from .authentication import TOKEN_SALT, SignedTokenAuthentication, create_access_token


def authenticate_test_client(client, role="admin"):
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {create_access_token('test', role)}"


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

    def test_successful_sale_debits_ficha_and_stock_atomically(self):
        MovimentacaoEstoque.objects.create(
            caixa=self.caixa,
            produto=self.produto,
            quantidade=2,
            tipo="E",
        )
        ficha = Ficha.objects.create(numero=3, saldo=Decimal("10.00"))
        serializer = VendaSerializer(data={
            "ficha": ficha.id,
            "movimentacao": {
                "caixa": self.caixa.id,
                "produto": self.produto.id,
                "quantidade": 2,
            },
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        self.produto.refresh_from_db()
        ficha.refresh_from_db()
        self.assertEqual(self.produto.estoque, 0)
        self.assertEqual(ficha.saldo, Decimal("0.00"))
        self.assertEqual(Venda.objects.count(), 1)

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
    def setUp(self):
        authenticate_test_client(self.client, "caixa")

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
        self.assertEqual(response.json()["is_admin"], True)
        self.assertEqual(response.json()["role"], "admin")
        self.assertTrue(response.json()["token"])

    @override_settings(ADMIN_USERNAME="admin", ADMIN_PASSWORD="secret")
    def test_admin_login_rejects_invalid_credentials(self):
        response = self.client.post(
            "/movimentacao/admin-login/",
            data={"username": "admin", "password": "wrong"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)


class TestSignedTokenAPI(TestCase):
    def setUp(self):
        self.caixa = Caixa.objects.create(
            nome="Caixa Principal", usuario="caixa-auth", senha="123"
        )

    def login(self, usuario="admin", senha="secret"):
        if usuario == "admin":
            response = self.client.post(
                "/movimentacao/admin-login/",
                {"username": usuario, "password": senha},
                content_type="application/json",
            )
        else:
            response = self.client.post(
                "/movimentacao/caixas/login/",
                {"usuario": usuario, "senha": senha},
                content_type="application/json",
            )
        return response.json()["token"]

    @override_settings(ADMIN_USERNAME="admin", ADMIN_PASSWORD="secret")
    def test_private_endpoint_rejects_anonymous_and_accepts_admin_token(self):
        self.assertEqual(self.client.get("/movimentacao/produtos/").status_code, 401)
        token = self.login()
        response = self.client.get(
            "/movimentacao/produtos/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 200)

    @override_settings(ADMIN_USERNAME="admin", ADMIN_PASSWORD="secret")
    def test_admin_only_endpoint_rejects_caixa_token(self):
        token = self.login("caixa-auth", "123")
        response = self.client.get(
            "/movimentacao/produtos/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(response.status_code, 403)

    def test_caixa_can_retrieve_only_own_record(self):
        token = self.login("caixa-auth", "123")
        response = self.client.get(
            f"/movimentacao/caixas/{self.caixa.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 200)

        other = Caixa.objects.create(nome="Outro", usuario="outro", senha="123")
        response = self.client.get(
            f"/movimentacao/caixas/{other.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(response.status_code, 404)

    @override_settings(ADMIN_USERNAME="admin", ADMIN_PASSWORD="secret")
    def test_expired_token_is_rejected(self):
        token = signing.dumps({"sub": "admin", "role": "admin"}, salt=TOKEN_SALT)
        # A token with a timestamp older than the configured lifetime is invalid.
        with patch(
            "movimentacao.authentication.TOKEN_MAX_AGE", 0
        ):
            response = self.client.get(
                "/movimentacao/produtos/", HTTP_AUTHORIZATION=f"Bearer {token}"
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
        authenticate_test_client(self.client, "caixa")

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

    def test_public_reservation_rejects_duplicate_product_in_request(self):
        response = self.client.post(
            "/movimentacao/reservas-publicas/criar/",
            data={
                "nome_completo": "Maria Silva",
                "cpf": "12345678901",
                "qr_code": "RESERVA-TESTE",
                "produtos": [
                    {"produto_id": self.produto_permitido.id, "quantidade": 1},
                    {"produto_id": self.produto_permitido.id, "quantidade": 1},
                ],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ReservaProduto.objects.count(), 0)

    def test_public_reservation_lookup_requires_creation_token(self):
        response = self.client.post(
            "/movimentacao/reservas-publicas/criar/",
            data={
                "nome_completo": "Maria Silva",
                "cpf": "12345678901",
                "qr_code": "RESERVA-TESTE",
                "produtos": [{"produto_id": self.produto_permitido.id, "quantidade": 1}],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        consulta_token = response.json()["consulta_token"]

        without_token = self.client.get(
            "/movimentacao/reservas-publicas/por-cpf/?cpf=12345678901"
        )
        self.assertEqual(without_token.status_code, 401)

        lookup = self.client.get(
            "/movimentacao/reservas-publicas/por-cpf/",
            {"cpf": "12345678901", "consulta_token": consulta_token},
        )
        self.assertEqual(lookup.status_code, 200)
        self.assertEqual(len(lookup.json()["reservas"]), 1)

    def test_public_reservation_lookup_rejects_token_for_another_cpf(self):
        token_response = self.client.post(
            "/movimentacao/reservas-publicas/criar/",
            data={
                "nome_completo": "Maria Silva",
                "cpf": "12345678901",
                "produtos": [{"produto_id": self.produto_permitido.id, "quantidade": 1}],
            },
            content_type="application/json",
        )
        token = token_response.json()["consulta_token"]
        response = self.client.get(
            "/movimentacao/reservas-publicas/por-cpf/",
            {"cpf": "98765432100", "consulta_token": token},
        )
        self.assertEqual(response.status_code, 401)

    def test_confirm_without_ficha_returns_validation_error(self):
        reserva = ReservaProduto.objects.create(
            nome_completo="Maria Silva",
            cpf="12345678901",
            produto=self.produto_permitido,
            quantidade=1,
            status="pendente",
        )

        response = self.client.post(
            f"/movimentacao/reservas/{reserva.id}/confirmar/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("vinculada a uma ficha", response.json()["error"])
        reserva.refresh_from_db()
        self.produto_permitido.refresh_from_db()
        self.assertEqual(reserva.status, "pendente")
        self.assertEqual(self.produto_permitido.estoque, 0)

    def test_confirm_debits_ficha_and_stock(self):
        ficha = Ficha.objects.create(numero=21, saldo=Decimal("10.00"))
        MovimentacaoEstoque.objects.create(
            caixa=self.caixa,
            produto=self.produto_permitido,
            quantidade=2,
            tipo="E",
        )
        reserva = ReservaProduto.objects.create(
            ficha=ficha,
            nome_completo="Maria Silva",
            cpf="12345678901",
            produto=self.produto_permitido,
            quantidade=1,
            status="pendente",
        )

        response = self.client.post(
            f"/movimentacao/reservas/{reserva.id}/confirmar/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        ficha.refresh_from_db()
        self.produto_permitido.refresh_from_db()
        reserva.refresh_from_db()
        self.assertEqual(ficha.saldo, Decimal("4.00"))
        self.assertEqual(self.produto_permitido.estoque, 1)
        self.assertEqual(reserva.status, "confirmada")
        self.assertEqual(Venda.objects.filter(ficha=ficha).count(), 1)

    def test_confirm_with_insufficient_balance_keeps_reservation_and_stock(self):
        ficha = Ficha.objects.create(numero=22, saldo=Decimal("5.00"))
        MovimentacaoEstoque.objects.create(
            caixa=self.caixa,
            produto=self.produto_permitido,
            quantidade=1,
            tipo="E",
        )
        reserva = ReservaProduto.objects.create(
            ficha=ficha,
            nome_completo="Maria Silva",
            cpf="12345678901",
            produto=self.produto_permitido,
            quantidade=1,
            status="pendente",
        )

        response = self.client.post(
            f"/movimentacao/reservas/{reserva.id}/confirmar/",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        ficha.refresh_from_db()
        self.produto_permitido.refresh_from_db()
        reserva.refresh_from_db()
        self.assertEqual(ficha.saldo, Decimal("5.00"))
        self.assertEqual(self.produto_permitido.estoque, 1)
        self.assertEqual(reserva.status, "pendente")
        self.assertEqual(Venda.objects.count(), 0)


class TestPopulateDevCommand(TestCase):
    def setUp(self):
        call_command("populate_dev", "--reset", "--history-days", "15", verbosity=0)
        authenticate_test_client(self.client, "admin")


    def test_populate_dev_generates_fifteen_days_of_sales_with_minimum_volume(self):
        total_vendas = Venda.objects.count()
        self.assertGreaterEqual(total_vendas, 300)
        self.assertLessEqual(total_vendas, 500)

        vendas = Venda.objects.select_related(
            "movimentacao__produto",
            "movimentacao__caixa",
            "ficha",
        )
        dias_com_vendas = sorted({
            timezone.localtime(venda.data).date() for venda in vendas
        })
        self.assertEqual(len(dias_com_vendas), 15)
        self.assertEqual(dias_com_vendas[-1], timezone.localdate() - timedelta(days=1))

        vendas_por_dia = {}
        vendas_por_horario = {f"{hora:02d}h-{(hora + 1) % 24:02d}h": 0 for hora in range(24)}
        for venda in vendas:
            stamp = timezone.localtime(venda.data)
            chave_dia = stamp.strftime("%Y-%m-%d")
            vendas_por_dia[chave_dia] = vendas_por_dia.get(chave_dia, 0) + 1
            vendas_por_horario[f"{stamp.hour:02d}h-{(stamp.hour + 1) % 24:02d}h"] += 1

        pico = max(vendas_por_horario.items(), key=lambda item: item[1])
        pico_hora = int(pico[0].split("h")[0])
        self.assertGreaterEqual(pico_hora, 18)
        self.assertLessEqual(pico_hora, 21)

        dias_primeiros_trinta = [
            (dias_com_vendas[0] + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(3)
        ]
        self.assertGreater(
            sum(vendas_por_dia.values()),
            sum(vendas_por_dia.get(dia, 0) for dia in dias_primeiros_trinta),
        )

    def test_populate_dev_keeps_stock_movements_consistent(self):
        movimentacoes = MovimentacaoEstoque.objects.select_related("produto").all()
        self.assertGreater(len(movimentacoes), 0)

        por_produto = {}
        for movimentacao in movimentacoes:
            total_atual = por_produto.get(movimentacao.produto_id, 0)
            por_produto[movimentacao.produto_id] = (
                total_atual - movimentacao.quantidade
                if movimentacao.tipo == "S"
                else total_atual + movimentacao.quantidade
            )

        for produto_id, estoque_final in por_produto.items():
            produto = Produto.objects.get(pk=produto_id)
            self.assertGreaterEqual(estoque_final, 0)
            self.assertEqual(int(produto.estoque), int(estoque_final))

    def test_populate_dev_keeps_ficha_balances_consistent_with_ledger(self):
        for ficha in Ficha.objects.all():
            recargas = ficha.recargas.aggregate(total=Sum("valor"))["total"] or Decimal("0.00")
            vendas = ficha.compras.aggregate(total=Sum("valor_total"))["total"] or Decimal("0.00")
            self.assertEqual(ficha.saldo, recargas - vendas)

    def test_populate_dev_marks_food_and_drinks_as_perishable(self):
        self.assertGreater(Produto.objects.filter(perecivel=True).count(), 0)
        self.assertTrue(
            Produto.objects.filter(
                perecivel=True,
                categoria__in=["bebidas", "salgados", "doces"],
            ).exists()
        )
        self.assertFalse(
            Produto.objects.filter(categoria="jogos", perecivel=True).exists()
        )

    def test_populate_dev_dashboard_uses_operational_history(self):
        response = self.client.get("/dashboard/data/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["metadadosModeloDemanda"]["fonteDados"], "operacional")
        self.assertTrue(data["metadadosModeloDemanda"]["validacaoReal"])
        self.assertEqual(data["metadadosModeloDemanda"]["avaliacao"]["eventos_treino"], 3)
        self.assertEqual(data["metadadosModeloDemanda"]["avaliacao"]["eventos_holdout"], 2)
        self.assertGreater(len(data["previsaoDemandaProdutos"]), 0)
        self.assertGreater(len(data["produtosEstoquePrevisao"]), 0)
        self.assertGreater(data["totalVendas"], 0)

    def test_populate_dev_reset_is_idempotent(self):
        total_vendas = Venda.objects.count()

        call_command("populate_dev", "--reset", "--history-days", "15", verbosity=0)

        self.assertEqual(Venda.objects.count(), total_vendas)
        self.assertGreaterEqual(Venda.objects.count(), 300)


class TestDemoSeedEndpoint(TestCase):
    @override_settings(DEMO_SEED_TOKEN="seed-token")
    def test_seed_demo_requires_token(self):
        response = self.client.post("/movimentacao/seed-demo/", {"history_days": 1})
        self.assertEqual(response.status_code, 403)

    @override_settings(DEMO_SEED_TOKEN="seed-token")
    def test_seed_demo_recreates_data_with_token(self):
        response = self.client.post(
            "/movimentacao/seed-demo/",
            {"history_days": 1},
            HTTP_X_DEMO_SEED_TOKEN="seed-token",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["history_days"], 1)
        self.assertGreaterEqual(Venda.objects.count(), 6)
