from decimal import Decimal

from django.test import TestCase

from movimentacao.models import Caixa, Ficha, MovimentacaoEstoque, Produto, Venda


class TestDashboardData(TestCase):
    def test_dashboard_uses_historical_sale_values(self):
        caixa = Caixa.objects.create(nome="Caixa Principal", usuario="caixa", senha="123")
        produto = Produto.objects.create(
            caixa=caixa,
            nome="Pastel",
            medida="UN",
            preco=Decimal("5.00"),
        )
        MovimentacaoEstoque.objects.create(
            caixa=caixa,
            produto=produto,
            quantidade=2,
            tipo="E",
        )
        ficha = Ficha.objects.create(numero=1, saldo=Decimal("20.00"))
        movimentacao = MovimentacaoEstoque.objects.create(
            caixa=caixa,
            produto=produto,
            quantidade=2,
            tipo="S",
        )
        Venda.objects.create(movimentacao=movimentacao, ficha=ficha)

        produto.preco = Decimal("8.00")
        produto.save()

        response = self.client.get("/dashboard/data/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(float(data["receita"]), 10.0)
        self.assertEqual(data["vendasDetalhadas"][0]["valorTotal"], 10.0)
        self.assertEqual(data["vendasDetalhadas"][0]["produto_preco"], 5.0)
