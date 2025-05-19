from django.core.management.base import BaseCommand
from movimentacao.models import Caixa, Produto, Ficha, Venda
from decimal import Decimal


class Command(BaseCommand):
    help = 'Popula o banco de dados com dados de desenvolvimento'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Limpa os dados antes de popular o banco',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write("🧨 Limpando os dados existentes...")
            
            # Apague primeiro os registros que referenciam Ficha
            Venda.objects.all().delete()
            
            Ficha.objects.all().delete()
            Produto.objects.all().delete()
            Caixa.objects.all().delete()

            self.stdout.write("✔️ Dados antigos removidos com sucesso.")

        caixa = Caixa.objects.create(nome="Caixa Principal")

        produtos = [
            # Bebidas
            {"nome": "Cerveja", "categoria": "bebida", "medida": "UN", "preco": "5.00", "estoque": 120},
            {"nome": "Água", "categoria": "bebida", "medida": "UN", "preco": "2.00", "estoque": 200},
            {"nome": "Refrigerante", "categoria": "bebida", "medida": "UN", "preco": "4.50", "estoque": 150},

            # Salgados
            {"nome": "Coxinha", "categoria": "salgado", "medida": "UN", "preco": "3.50", "estoque": 100},
            {"nome": "Pão de Queijo", "categoria": "salgado", "medida": "UN", "preco": "2.00", "estoque": 120},
            {"nome": "Esfiha", "categoria": "salgado", "medida": "UN", "preco": "4.00", "estoque": 90},

            # Doces
            {"nome": "Brigadeiro", "categoria": "doce", "medida": "UN", "preco": "1.50", "estoque": 300},
            {"nome": "Beijinho", "categoria": "doce", "medida": "UN", "preco": "1.50", "estoque": 250},
            {"nome": "Bolo de Pote", "categoria": "doce", "medida": "UN", "preco": "6.00", "estoque": 80},

            # Jogos
            {"nome": "Ping Pong", "categoria": "jogos", "medida": "UN", "preco": "5.00", "estoque": 2},
            {"nome": "Totó", "categoria": "jogos", "medida": "UN", "preco": "3.00", "estoque": 1},
            {"nome": "Pebolim", "categoria": "jogos", "medida": "UN", "preco": "4.00", "estoque": 1},
        ]


        for p in produtos:
            Produto.objects.create(
                caixa=caixa,
                nome=p["nome"],
                categoria=p["categoria"],
                medida=p["medida"],
                preco=Decimal(p["preco"]),
                estoque=p["estoque"]
            )


        fichas = [
            {"numero": 1, "saldo": "50.00"},
            {"numero": 2, "saldo": "20.00"},
            {"numero": 3, "saldo": "35.00"},
            {"numero": 4, "saldo": "10.00"},
            {"numero": 5, "saldo": "60.00"},
        ]

        for f in fichas:
            Ficha.objects.create(
                numero=f["numero"],
                saldo=Decimal(f["saldo"])
            )

        self.stdout.write(self.style.SUCCESS("✅ Banco populado com sucesso com produtos e fichas fictícias."))