from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from movimentacao.models import (
    Caixa,
    Ficha,
    MovimentacaoEstoque,
    Produto,
    QRCodeReserva,
    Recarga,
    ReservaProduto,
    Venda,
)
from publico.models import Sugestao


class Command(BaseCommand):
    help = "Popula o banco de dados com um cenário realista de festa junina."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Limpa os dados existentes antes de popular o banco.",
        )

    def handle(self, *args, **options):
        has_data = any(
            model.objects.exists()
            for model in [
                Caixa,
                Produto,
                Ficha,
                MovimentacaoEstoque,
                Venda,
                Recarga,
                QRCodeReserva,
                ReservaProduto,
                Sugestao,
            ]
        )

        if has_data and not options["reset"]:
            self.stdout.write(
                self.style.WARNING(
                    "Ja existem dados no banco. Use `python manage.py populate_dev --reset` "
                    "para recriar a base de demonstracao."
                )
            )
            return

        with transaction.atomic():
            if options["reset"]:
                self.stdout.write("Limpando os dados existentes...")
                ReservaProduto.objects.all().delete()
                QRCodeReserva.objects.all().delete()
                Venda.objects.all().delete()
                Recarga.objects.all().delete()
                MovimentacaoEstoque.objects.all().delete()
                Ficha.objects.all().delete()
                Produto.objects.all().delete()
                Caixa.objects.all().delete()
                Sugestao.objects.all().delete()

            now = timezone.now()

            caixas = self._criar_caixas()
            produtos = self._criar_produtos(caixas)
            fichas = self._criar_fichas()
            self._criar_recargas(fichas, caixas, now)
            self._criar_vendas(fichas, produtos, caixas, now)
            self._criar_reservas(fichas, produtos, now)
            self._criar_sugestoes(now)

        self.stdout.write(
            self.style.SUCCESS(
                "Banco populado com dados de festa junina. "
                "Login caixa principal: usuario `caixa`, senha `caixa123`. "
                "Admin padrao: usuario `admin`, senha `admin123`."
            )
        )

    def _criar_caixas(self):
        caixas_data = [
            ("principal", "Caixa Principal", "caixa", "caixa123"),
            ("bebidas", "Caixa Bebidas", "bebidas", "bebidas123"),
            ("comidas", "Caixa Comidas", "comidas", "comidas123"),
            ("jogos", "Caixa Jogos", "jogos", "jogos123"),
        ]
        caixas = {}

        for key, nome, usuario, senha in caixas_data:
            caixa = Caixa(nome=nome, usuario=usuario)
            caixa.set_senha(senha)
            caixa.save()
            caixas[key] = caixa

        return caixas

    def _criar_produtos(self, caixas):
        produtos_data = [
            {
                "nome": "Agua mineral",
                "categoria": "bebidas",
                "medida": "UN",
                "preco": "2.00",
                "estoque": 260,
                "caixa": "bebidas",
                "reserva": True,
                "limite": 4,
                "reserva_disponivel": 90,
            },
            {
                "nome": "Refrigerante lata",
                "categoria": "bebidas",
                "medida": "UN",
                "preco": "5.00",
                "estoque": 180,
                "caixa": "bebidas",
                "reserva": True,
                "limite": 3,
                "reserva_disponivel": 60,
            },
            {
                "nome": "Suco natural",
                "categoria": "bebidas",
                "medida": "UN",
                "preco": "4.00",
                "estoque": 120,
                "caixa": "bebidas",
                "reserva": False,
            },
            {
                "nome": "Cachorro quente",
                "categoria": "salgados",
                "medida": "UN",
                "preco": "8.00",
                "estoque": 140,
                "caixa": "comidas",
                "reserva": True,
                "limite": 2,
                "reserva_disponivel": 50,
            },
            {
                "nome": "Pastel de carne",
                "categoria": "salgados",
                "medida": "UN",
                "preco": "7.00",
                "estoque": 110,
                "caixa": "comidas",
                "reserva": True,
                "limite": 2,
                "reserva_disponivel": 45,
            },
            {
                "nome": "Milho verde",
                "categoria": "salgados",
                "medida": "UN",
                "preco": "6.00",
                "estoque": 95,
                "caixa": "comidas",
                "reserva": False,
            },
            {
                "nome": "Canjica",
                "categoria": "doces",
                "medida": "UN",
                "preco": "5.00",
                "estoque": 85,
                "caixa": "comidas",
                "reserva": False,
            },
            {
                "nome": "Bolo de pote",
                "categoria": "doces",
                "medida": "UN",
                "preco": "6.00",
                "estoque": 90,
                "caixa": "comidas",
                "reserva": True,
                "limite": 3,
                "reserva_disponivel": 40,
            },
            {
                "nome": "Brigadeiro",
                "categoria": "doces",
                "medida": "UN",
                "preco": "2.00",
                "estoque": 230,
                "caixa": "comidas",
                "reserva": False,
            },
            {
                "nome": "Pescaria",
                "categoria": "jogos",
                "medida": "UN",
                "preco": "5.00",
                "estoque": 180,
                "caixa": "jogos",
                "reserva": True,
                "limite": 4,
                "reserva_disponivel": 70,
            },
            {
                "nome": "Boca do palhaco",
                "categoria": "jogos",
                "medida": "UN",
                "preco": "4.00",
                "estoque": 160,
                "caixa": "jogos",
                "reserva": False,
            },
            {
                "nome": "Correio elegante",
                "categoria": "jogos",
                "medida": "UN",
                "preco": "3.00",
                "estoque": 200,
                "caixa": "principal",
                "reserva": False,
            },
        ]
        produtos = {}

        for item in produtos_data:
            estoque = item.pop("estoque")
            caixa = caixas[item.pop("caixa")]
            reserva = item.pop("reserva", False)
            limite = item.pop("limite", 2)
            reserva_disponivel = item.pop("reserva_disponivel", 0)
            produto = Produto.objects.create(
                caixa=caixa,
                disponivel_reserva=reserva,
                limite_reserva=limite,
                quantidade_reserva_disponivel=reserva_disponivel,
                preco=Decimal(item["preco"]),
                nome=item["nome"],
                categoria=item["categoria"],
                medida=item["medida"],
            )
            MovimentacaoEstoque.objects.create(
                caixa=caixa,
                produto=produto,
                quantidade=estoque,
                tipo="E",
            )
            produtos[produto.nome] = produto

        return produtos

    def _criar_fichas(self):
        fichas = {}
        for numero in range(101, 117):
            fichas[numero] = Ficha.objects.create(numero=numero, saldo=Decimal("0.00"))

        ficha_inativa = Ficha.objects.create(
            numero=117,
            saldo=Decimal("0.00"),
            is_active=False,
            deleted_at=timezone.now() - timedelta(hours=2),
        )
        fichas[117] = ficha_inativa
        return fichas

    def _criar_recargas(self, fichas, caixas, now):
        recargas_data = [
            (101, "80.00", "principal", now - timedelta(hours=5, minutes=50), "Recarga inicial - familia Santos"),
            (102, "45.00", "principal", now - timedelta(hours=5, minutes=20), "Recarga inicial"),
            (103, "60.00", "bebidas", now - timedelta(hours=4, minutes=45), "Recarga no caixa bebidas"),
            (104, "35.00", "comidas", now - timedelta(hours=4, minutes=10), "Recarga em dinheiro"),
            (105, "100.00", "principal", now - timedelta(hours=3, minutes=50), "Recarga PIX"),
            (106, "25.00", "jogos", now - timedelta(hours=3, minutes=30), "Recarga jogos"),
            (107, "70.00", "principal", now - timedelta(hours=2, minutes=55), "Recarga inicial"),
            (108, "50.00", "comidas", now - timedelta(hours=2, minutes=25), "Recarga inicial"),
            (109, "40.00", "bebidas", now - timedelta(hours=1, minutes=55), "Recarga inicial"),
            (110, "120.00", "principal", now - timedelta(hours=1, minutes=15), "Recarga familia Oliveira"),
            (111, "30.00", "jogos", now - timedelta(minutes=55), "Recarga final de noite"),
            (112, "55.00", "principal", now - timedelta(minutes=40), "Recarga inicial"),
        ]

        for numero, valor, caixa_key, data, observacoes in recargas_data:
            ficha = fichas[numero]
            ficha.recarga(Decimal(valor))
            recarga = Recarga.objects.create(
                ficha=ficha,
                caixa=caixas[caixa_key],
                valor=Decimal(valor),
                observacoes=observacoes,
            )
            Recarga.objects.filter(pk=recarga.pk).update(data=data)

    def _criar_vendas(self, fichas, produtos, caixas, now):
        vendas_data = [
            (101, "Cachorro quente", 2, "comidas", now - timedelta(hours=5, minutes=35)),
            (101, "Refrigerante lata", 2, "bebidas", now - timedelta(hours=5, minutes=30)),
            (102, "Pescaria", 3, "jogos", now - timedelta(hours=5, minutes=5)),
            (103, "Pastel de carne", 2, "comidas", now - timedelta(hours=4, minutes=25)),
            (103, "Agua mineral", 3, "bebidas", now - timedelta(hours=4, minutes=18)),
            (104, "Bolo de pote", 2, "comidas", now - timedelta(hours=3, minutes=45)),
            (105, "Milho verde", 4, "comidas", now - timedelta(hours=3, minutes=25)),
            (105, "Boca do palhaco", 5, "jogos", now - timedelta(hours=3, minutes=10)),
            (106, "Correio elegante", 4, "principal", now - timedelta(hours=2, minutes=48)),
            (107, "Canjica", 3, "comidas", now - timedelta(hours=2, minutes=20)),
            (107, "Suco natural", 4, "bebidas", now - timedelta(hours=2, minutes=5)),
            (108, "Brigadeiro", 8, "comidas", now - timedelta(hours=1, minutes=45)),
            (109, "Refrigerante lata", 3, "bebidas", now - timedelta(hours=1, minutes=22)),
            (110, "Cachorro quente", 5, "comidas", now - timedelta(minutes=58)),
            (110, "Pescaria", 4, "jogos", now - timedelta(minutes=50)),
            (111, "Agua mineral", 2, "bebidas", now - timedelta(minutes=35)),
            (112, "Pastel de carne", 3, "comidas", now - timedelta(minutes=20)),
        ]

        for ficha_numero, produto_nome, quantidade, caixa_key, data in vendas_data:
            produto = produtos[produto_nome]
            movimentacao = MovimentacaoEstoque.objects.create(
                caixa=caixas[caixa_key],
                produto=produto,
                quantidade=quantidade,
                tipo="S",
            )
            venda = Venda.objects.create(
                movimentacao=movimentacao,
                ficha=fichas[ficha_numero],
            )
            MovimentacaoEstoque.objects.filter(pk=movimentacao.pk).update(data=data)
            Venda.objects.filter(pk=venda.pk).update(
                valor_unitario=produto.preco,
                valor_total=produto.preco * quantidade,
            )

    def _criar_reservas(self, fichas, produtos, now):
        qr_code = QRCodeReserva.objects.create(
            codigo="ARRAIA-LCG-2026",
            descricao="Reservas antecipadas - ArraiaTech",
            data_inicio=now - timedelta(days=2),
            data_expiracao=now + timedelta(days=7),
            ativo=True,
        )
        qr_code.produtos_disponiveis.set(
            [
                produtos["Agua mineral"],
                produtos["Refrigerante lata"],
                produtos["Cachorro quente"],
                produtos["Pastel de carne"],
                produtos["Bolo de pote"],
                produtos["Pescaria"],
            ]
        )

        reservas_data = [
            ("Mariana Souza", "12345678901", "Cachorro quente", 2, "pendente", None, now - timedelta(days=1, hours=4)),
            ("Joao Pedro Lima", "23456789012", "Refrigerante lata", 2, "pendente", None, now - timedelta(days=1, hours=2)),
            ("Carla Mendes", "34567890123", "Bolo de pote", 3, "confirmada", 104, now - timedelta(hours=6)),
            ("Roberto Alves", "45678901234", "Pescaria", 4, "confirmada", 106, now - timedelta(hours=5, minutes=45)),
            ("Ana Clara Rocha", "56789012345", "Agua mineral", 4, "finalizada", 111, now - timedelta(hours=2)),
            ("Paulo Henrique", "67890123456", "Pastel de carne", 1, "cancelada", None, now - timedelta(days=2)),
        ]

        for nome, cpf, produto_nome, quantidade, status, ficha_numero, data in reservas_data:
            reserva = ReservaProduto.objects.create(
                ficha=fichas.get(ficha_numero) if ficha_numero else None,
                produto=produtos[produto_nome],
                quantidade=quantidade,
                nome_completo=nome,
                cpf=cpf,
                qr_code_reserva=qr_code,
                status=status,
                data_confirmacao=data + timedelta(minutes=35)
                if status in ["confirmada", "finalizada"]
                else None,
                observacoes="Reserva criada para teste ao vivo.",
            )
            ReservaProduto.objects.filter(pk=reserva.pk).update(data_reserva=data)

    def _criar_sugestoes(self, now):
        sugestoes_data = [
            ("Larissa Nunes", "1198765432", "Adicionar opcao de vinho quente sem alcool.", "pendente", now - timedelta(days=1)),
            ("Miguel Martins", "1197654321", "Aumentar placas indicando os caixas.", "avaliada", now - timedelta(hours=8)),
            ("Beatriz Costa", "1196543210", "Criar combo de pastel com refrigerante.", "pendente", now - timedelta(hours=3)),
        ]

        for nome, telefone, texto, situacao, data in sugestoes_data:
            sugestao = Sugestao.objects.create(
                nome=nome,
                telefone=telefone,
                sugestao=texto,
                situacao=situacao,
            )
            Sugestao.objects.filter(pk=sugestao.pk).update(data_sugestao=data)
