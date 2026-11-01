import random
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

    # Fator de movimento por dia: crescimento gradual nos dias mais recentes.
    FATOR_DIA_MIN = 0.88
    FATOR_DIA_MAX = 1.12
    VENDAS_BASE_POR_DIA = 21

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Limpa os dados existentes antes de popular o banco.",
        )
        parser.add_argument(
            "--history-days",
            type=int,
            default=15,
            help="Quantidade de dias de operação histórica para popular (padrao: 15).",
        )

    def handle(self, *args, **options):
        history_days = max(1, int(options.get("history_days") or 15))

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
            self._criar_recargas(fichas, caixas, now, history_days)
            self._criar_vendas(fichas, produtos, caixas, now, history_days)
            self._criar_reservas(fichas, produtos, now)
            self._criar_sugestoes(now)

        self.stdout.write(
            self.style.SUCCESS(
                "Banco populado com dados de festa junina. "
                f"Historico de {history_days} dias de operacao. "
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
                "estoque": 600,
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
                "estoque": 420,
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
                "estoque": 260,
                "caixa": "bebidas",
                "reserva": False,
            },
            {
                "nome": "Cachorro quente",
                "categoria": "salgados",
                "medida": "UN",
                "preco": "8.00",
                "estoque": 380,
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
                "estoque": 330,
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
                "estoque": 300,
                "caixa": "comidas",
                "reserva": False,
            },
            {
                "nome": "Canjica",
                "categoria": "doces",
                "medida": "UN",
                "preco": "5.00",
                "estoque": 280,
                "caixa": "comidas",
                "reserva": False,
            },
            {
                "nome": "Bolo de pote",
                "categoria": "doces",
                "medida": "UN",
                "preco": "6.00",
                "estoque": 240,
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
                "estoque": 350,
                "caixa": "comidas",
                "reserva": False,
            },
            {
                "nome": "Pescaria",
                "categoria": "jogos",
                "medida": "UN",
                "preco": "5.00",
                "estoque": 260,
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
                "estoque": 220,
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
                perecivel=item.pop("perecivel", item["categoria"] != "jogos"),
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
            fichas[numero] = Ficha.objects.create(
                numero=numero,
                saldo=Decimal("0.00"),
            )

        ficha_inativa = Ficha.objects.create(
            numero=117,
            saldo=Decimal("0.00"),
            is_active=False,
            deleted_at=timezone.now() - timedelta(hours=2),
        )
        fichas[117] = ficha_inativa
        return fichas

    def _criar_recargas(self, fichas, caixas, now, history_days):
        data_inicio = timezone.localtime(now).replace(
            hour=10, minute=0, second=0, microsecond=0
        ) - timedelta(days=history_days)
        for ficha in fichas.values():
            if ficha.is_active:
                valor = Decimal("150.00")
                ficha.recarga(valor)
                recarga = Recarga.objects.create(
                    ficha=ficha,
                    caixa=caixas["principal"],
                    valor=valor,
                    observacoes="Carga inicial da ficha para o histórico demonstrativo.",
                )
                Recarga.objects.filter(pk=recarga.pk).update(data=data_inicio)

        recargas_data = [
            (101, "80.00", "principal", 13, "Recarga inicial - familia Santos"),
            (102, "45.00", "principal", 12, "Recarga inicial"),
            (103, "60.00", "bebidas", 11, "Recarga no caixa bebidas"),
            (104, "35.00", "comidas", 10, "Recarga em dinheiro"),
            (105, "100.00", "principal", 9, "Recarga PIX"),
            (106, "25.00", "jogos", 8, "Recarga jogos"),
            (107, "70.00", "principal", 7, "Recarga inicial"),
            (108, "50.00", "comidas", 6, "Recarga inicial"),
            (109, "40.00", "bebidas", 5, "Recarga inicial"),
            (110, "120.00", "principal", 4, "Recarga familia Oliveira"),
            (111, "30.00", "jogos", 3, "Recarga final de noite"),
            (112, "55.00", "principal", 2, "Recarga inicial"),
        ]

        for numero, valor, caixa_key, dias_atras, observacoes in recargas_data:
            ficha = fichas[numero]
            valor = Decimal(valor)
            ficha.recarga(valor)
            recarga = Recarga.objects.create(
                ficha=ficha,
                caixa=caixas[caixa_key],
                valor=valor,
                observacoes=observacoes,
            )
            Recarga.objects.filter(pk=recarga.pk).update(
                data=(timezone.localtime(now) - timedelta(days=dias_atras)).replace(
                    hour=14, minute=0, second=0, microsecond=0
                )
            )

    def _criar_vendas(self, fichas, produtos, caixas, now, history_days):
        produtos_list = list(produtos.values())
        pesos_por_produto = [
            0.10,  # Agua mineral
            0.16,  # Refrigerante lata
            0.08,  # Suco natural
            0.14,  # Cachorro quente
            0.12,  # Pastel de carne
            0.06,  # Milho verde
            0.06,  # Canjica
            0.05,  # Bolo de pote
            0.05,  # Brigadeiro
            0.05,  # Pescaria
            0.03,  # Boca do palhaco
            0.02,  # Correio elegante
        ]
        horas = [
            (16, 1.0),
            (17, 2.0),
            (18, 5.0),
            (19, 7.0),
            (20, 8.0),
            (21, 6.0),
            (22, 3.0),
        ]
        nomes_horas = [str(hour) for hour, _ in horas]
        pesos_horas = [peso for _, peso in horas]
        rng = random.Random(20240624)
        vendas_criadas = 0

        for dia_atraso in range(history_days):
            data = timezone.localtime(now) - timedelta(days=history_days - dia_atraso)
            fator_dia = self.FATOR_DIA_MIN + (
                (self.FATOR_DIA_MAX - self.FATOR_DIA_MIN)
                * ((dia_atraso + 1) / history_days)
            )
            quantidade_vendas = max(6, int(round(self.VENDAS_BASE_POR_DIA * fator_dia)))

            for _ in range(quantidade_vendas):
                produto = rng.choices(produtos_list, weights=pesos_por_produto, k=1)[0]
                quantidade = rng.choices(
                    [1, 1, 1, 2, 2, 3],
                    weights=[0.6, 0.2, 0.1, 0.05, 0.03, 0.02],
                    k=1,
                )[0]
                valor_total = produto.preco * quantidade
                ficha = self._escolher_ficha(fichas, valor_total)
                hora = rng.choices(nomes_horas, weights=pesos_horas, k=1)[0]
                minuto = rng.randint(0, 59)

                movimentacao = MovimentacaoEstoque.objects.create(
                    caixa=produto.caixa,
                    produto=produto,
                    quantidade=quantidade,
                    tipo="S",
                )
                venda = Venda.objects.create(
                    movimentacao=movimentacao,
                    ficha=ficha,
                )
                MovimentacaoEstoque.objects.filter(pk=movimentacao.pk).update(
                    data=data.replace(hour=int(hora), minute=minuto, second=0, microsecond=0)
                )
                Venda.objects.filter(pk=venda.pk).update(
                    valor_unitario=produto.preco,
                    valor_total=produto.preco * quantidade,
                )
                vendas_criadas += 1

        self.stdout.write(
            self.style.SUCCESS(f"{vendas_criadas} vendas registradas nos ultimos {history_days} dias.")
        )

    def _escolher_ficha(self, fichas, valor_total):
        for numero in sorted(fichas):
            ficha = Ficha.objects.get(numero=numero)
            if not ficha.is_active or ficha.deleted_at is not None:
                continue
            if ficha.saldo >= valor_total:
                return ficha
        raise ValueError("Ficha sem saldo suficiente para registrar a venda.")

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
