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

    vendas_por_horario = {f"{h:02d}h-{(h+1)%24:02d}h": 0 for h in range(24)}

    for v in vendas:
        hora = localtime(v.data).hour
        chave = f"{hora:02d}h-{(hora+1)%24:02d}h"
        vendas_por_horario[chave] += 1

    EMOJIS_CATEGORIA = {
        "doce": "🍬",
        "salgado": "🥨",
        "bebida": "🍹",
        "jogos": "🎯",
    }

    vendas_por_categoria = (
        vendas.values('movimentacao__produto__categoria')
        .annotate(total=Sum('movimentacao__quantidade'))
        .order_by('-total')
    )

    categoria_formatada = [
        {
            "name": f"{EMOJIS_CATEGORIA.get(cat['movimentacao__produto__categoria'].lower(), '')} {cat['movimentacao__produto__categoria'].capitalize()}",
            "value": cat["total"]
        }
        for cat in vendas_por_categoria
    ]

    top_produtos = (
        vendas.values('movimentacao__produto__nome')
        .annotate(vendidos=Sum('movimentacao__quantidade')) 
        .order_by('-vendidos')[:10]
    )
    top_produtos_formatado = [
        {"nome": p["movimentacao__produto__nome"], "vendidos": p["vendidos"]}
        for p in top_produtos
    ]

    vendas_list = []
    for v in vendas:
        vendas_list.append({
            "id": v.id,
            "horario": localtime(v.data).isoformat(),
            "produto": v.movimentacao.produto.nome,
            "categoria": v.movimentacao.produto.categoria,
            "quantidade": v.movimentacao.quantidade,
            "valorTotal": float(v.valor_total),
        })
        
    return Response({
        "totalVendas": total_vendas,
        "receita": receita,
        "clientesAtivos": clientes_ativos,
        "vendasPorHorario": vendas_por_horario,
        "vendasPorCategoria": categoria_formatada,
        "topProdutos": top_produtos_formatado,
        "vendasDetalhadas": vendas_list,
    })
