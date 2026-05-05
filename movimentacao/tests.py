from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Caixa, Ficha, MovimentacaoEstoque, Produto, Venda
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
