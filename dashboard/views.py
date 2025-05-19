from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Sum, Count, F, DecimalField, ExpressionWrapper
from django.utils.timezone import localtime
from movimentacao.models import Venda

@api_view(['GET'])
def dashboard_data(request):
    vendas = Venda.objects.select_related('movimentacao__produto').annotate(
        valor_total=ExpressionWrapper(
            F('movimentacao__produto__preco') * F('movimentacao__quantidade'),
            output_field=DecimalField()
        )
    )

    total_vendas = vendas.count()
    receita = vendas.aggregate(total=Sum('valor_total'))['total'] or 0
    clientes_ativos = vendas.values('ficha').distinct().count()

    vendas_por_horario = {
        "00h-06h": 0,
        "06h-12h": 0,
        "12h-18h": 0,
        "18h-24h": 0,
    }
    for v in vendas:
        hora = localtime(v.data).hour
        if hora < 6:
            vendas_por_horario["00h-06h"] += 1
        elif hora < 12:
            vendas_por_horario["06h-12h"] += 1
        elif hora < 18:
            vendas_por_horario["12h-18h"] += 1
        else:
            vendas_por_horario["18h-24h"] += 1

    vendas_por_categoria = (
        vendas.values('movimentacao__produto__categoria')
        .annotate(total=Count('id'))
        .order_by('-total')
    )
    categoria_formatada = [
        {"name": cat["movimentacao__produto__categoria"].capitalize(), "value": cat["total"]}
        for cat in vendas_por_categoria
    ]

    top_produtos = (
        vendas.values('movimentacao__produto__nome')
        .annotate(vendidos=Count('id'))
        .order_by('-vendidos')[:10]
    )
    top_produtos_formatado = [
        {"nome": p["movimentacao__produto__nome"], "vendidos": p["vendidos"]}
        for p in top_produtos
    ]

    return Response({
        "totalVendas": total_vendas,
        "receita": receita,
        "clientesAtivos": clientes_ativos,
        "vendasPorHorario": vendas_por_horario,
        "vendasPorCategoria": categoria_formatada,
        "topProdutos": top_produtos_formatado,
    })