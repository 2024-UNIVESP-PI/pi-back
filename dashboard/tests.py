from decimal import Decimal

from django.test import TestCase

from movimentacao.models import Caixa, Ficha, MovimentacaoEstoque, Produto, Venda


class TestDashboardData(TestCase):
    def criar_venda(self, produto, ficha, caixa, quantidade=1):
        movimentacao = MovimentacaoEstoque.objects.create(
            caixa=caixa,
            produto=produto,
            quantidade=quantidade,
            tipo="S",
        )
        return Venda.objects.create(movimentacao=movimentacao, ficha=ficha)

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
        self.criar_venda(produto, ficha, caixa, quantidade=2)

        produto.preco = Decimal("8.00")
        produto.save()

        response = self.client.get("/dashboard/data/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(float(data["receita"]), 10.0)
        self.assertEqual(data["vendasDetalhadas"][0]["valorTotal"], 10.0)
        self.assertEqual(data["vendasDetalhadas"][0]["produto_preco"], 5.0)

    def test_dashboard_returns_prediction_confidence_and_stock_suggestions(self):
        caixa = Caixa.objects.create(nome="Caixa Principal", usuario="caixa", senha="123")
        produto = Produto.objects.create(
            caixa=caixa,
            nome="Cachorro quente",
            medida="UN",
            preco=Decimal("8.00"),
        )
        MovimentacaoEstoque.objects.create(
            caixa=caixa,
            produto=produto,
            quantidade=20,
            tipo="E",
        )
        ficha = Ficha.objects.create(numero=1, saldo=Decimal("200.00"))

        for _ in range(4):
            self.criar_venda(produto, ficha, caixa, quantidade=2)

        response = self.client.get("/dashboard/data/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("confiancaPredicoes", data)
        self.assertGreaterEqual(data["confiancaPredicoes"]["demanda"], 0.2)
        self.assertGreaterEqual(data["confiancaPredicoes"]["receita"], 0)
        self.assertEqual(len(data["predicaoDemanda"]), 4)
        self.assertGreater(data["predicaoReceita3Dias"], 0)
        self.assertGreater(len(data["produtosEstoquePrevisao"]), 0)
        self.assertIn("confianca", data["produtosEstoquePrevisao"][0])
