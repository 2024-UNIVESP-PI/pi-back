from decimal import Decimal

from django.test import TestCase

from dashboard.synthetic_forecasting import (
    generate_synthetic_event_history,
    predict_product_demand,
    synthetic_forecast_metadata,
)
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
            perecivel=True,
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
        self.assertEqual(data["metadadosModeloDemanda"]["fonteDados"], "sintetica")
        self.assertIn("sintéticos", data["metadadosModeloDemanda"]["aviso"])
        self.assertGreater(len(data["previsaoDemandaProdutos"]), 0)


class TestSyntheticForecast(TestCase):
    def test_history_is_repeatable_and_contains_no_personal_records(self):
        first = generate_synthetic_event_history(seed=7, event_count=4)
        second = generate_synthetic_event_history(seed=7, event_count=4)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 4 * 4 * 3 * 7)
        self.assertTrue(all("cpf" not in row and "nome" not in row for row in first))
        self.assertEqual({row["event_id"] for row in first}, {
            "synthetic-event-01", "synthetic-event-02",
            "synthetic-event-03", "synthetic-event-04",
        })

    def test_forecast_metadata_reports_event_level_holdout_and_synthetic_limit(self):
        metadata = synthetic_forecast_metadata()

        self.assertEqual(metadata["fonteDados"], "sintetica")
        self.assertEqual(metadata["avaliacao"]["eventos_holdout"], 2)
        self.assertEqual(
            metadata["avaliacao"]["particao"],
            "eventos completos mantidos fora do treino",
        )
        self.assertIn("não validadas em eventos reais", metadata["aviso"])

    def test_product_forecast_is_nonnegative_and_accounts_for_reservations(self):
        caixa = Caixa.objects.create(nome="Caixa", usuario="caixa", senha="123")
        produto = Produto.objects.create(
            caixa=caixa,
            nome="Pastel",
            categoria="salgados",
            medida="UN",
            preco=Decimal("8.00"),
            estoque=3,
            perecivel=True,
        )

        forecasts, metadata = predict_product_demand(
            [produto], {produto.id: {"quantidade": 5, "pessoas": 2}}
        )

        self.assertEqual(metadata["fonteDados"], "sintetica")
        self.assertEqual(forecasts[0]["reservasAtivas"], 5)
        self.assertEqual(forecasts[0]["fichasRelacionadas"], 2)
        self.assertGreaterEqual(forecasts[0]["demandaPrevista3Dias"], 0)
        self.assertEqual(
            forecasts[0]["producaoSugerida"],
            max(0, forecasts[0]["demandaPrevista3Dias"] - 3),
        )

    def test_dashboard_forecasts_only_perishable_products(self):
        caixa = Caixa.objects.create(nome="Caixa", usuario="caixa", senha="123")
        Produto.objects.create(
            caixa=caixa,
            nome="Jogo de argolas",
            categoria="jogos",
            medida="UN",
            preco=Decimal("4.00"),
        )
        perishable = Produto.objects.create(
            caixa=caixa,
            nome="Milho cozido",
            categoria="salgados",
            medida="UN",
            preco=Decimal("6.00"),
            perecivel=True,
        )

        data = self.client.get("/dashboard/data/").json()

        self.assertEqual(
            [row["produtoId"] for row in data["previsaoDemandaProdutos"]],
            [perishable.id],
        )
