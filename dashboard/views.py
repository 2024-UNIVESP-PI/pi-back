from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Sum
from django.utils.timezone import localtime
from dashboard.predictions import (
    build_daily_sales,
    build_reservation_insights,
    calculate_growth,
    predict_hourly_demand,
    predict_revenue,
    predict_stock_needs,
)
from movimentacao.models import Venda

@api_view(['GET'])
def dashboard_data(request):
    # Verificar se há vendas antes de processar
    vendas = Venda.objects.select_related(
        'movimentacao__produto',
        'movimentacao__caixa',
        'ficha'
    )
    vendas_list_for_prediction = list(vendas)

    total_vendas = vendas.count()
    receita = vendas.aggregate(total=Sum('valor_total'))['total'] or 0
    clientes_ativos = vendas.values('ficha').distinct().count()

    # Inicializa vendas por horário (sempre retorna dicionário com 24 horas)
    vendas_por_horario = {f"{h:02d}h-{(h+1)%24:02d}h": 0 for h in range(24)}

    # Processa vendas por horário apenas se houver vendas
    if vendas_list_for_prediction:
        for v in vendas_list_for_prediction:
            try:
                hora = localtime(v.data).hour
                chave = f"{hora:02d}h-{(hora+1)%24:02d}h"
                vendas_por_horario[chave] += 1
            except (AttributeError, TypeError):
                # Se houver erro ao acessar data, continua
                continue

    vendas_por_categoria = (
        vendas.values('movimentacao__produto__categoria')
        .annotate(total=Sum('movimentacao__quantidade'))
        .order_by('-total')
    )

    # Garantir que categoria_formatada sempre seja uma lista (mesmo vazia)
    categoria_formatada = []
    vendas_por_categoria_list = list(vendas_por_categoria)
    if vendas_por_categoria_list:
        categoria_formatada = [
            {
                "name": cat['movimentacao__produto__categoria'].capitalize() if cat['movimentacao__produto__categoria'] else 'Sem categoria',
                "value": cat["total"]
            }
            for cat in vendas_por_categoria_list
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

    # Lista de vendas detalhadas (só processa se houver vendas)
    vendas_list = []
    if vendas_list_for_prediction:
        for v in vendas_list_for_prediction:
            caixa = v.movimentacao.caixa
            ficha = v.ficha
            produto = v.movimentacao.produto
            data_venda = localtime(v.data)
            vendas_list.append({
                "id": str(v.id),
                "horario": data_venda.isoformat(),
                "data": data_venda.strftime("%d/%m/%Y"),
                "hora": data_venda.strftime("%H:%M:%S"),
                "caixa_id": caixa.id if caixa else None,
                "caixa_nome": caixa.nome if caixa else "N/A",
                "caixa_usuario": caixa.usuario if caixa else "N/A",
                "ficha_id": ficha.id if ficha else None,
                "ficha_numero": ficha.numero if ficha else "N/A",
                "ficha_saldo": float(ficha.saldo) if ficha else 0,
                "produto_id": produto.id if produto else None,
                "produto": produto.nome if produto else "N/A",
                "produto_nome": produto.nome if produto else "N/A",
                "produto_categoria": (produto.categoria or "Sem categoria") if produto else "Sem categoria",
                "produto_preco": float(v.valor_unitario or produto.preco) if produto else 0,
                "categoria": (produto.categoria or "Sem categoria") if produto else "Sem categoria",
                "quantidade": v.movimentacao.quantidade,
                "valorTotal": float(v.valor_total),
            })
    
    predicao_demanda, confianca_demanda = predict_hourly_demand(
        vendas_por_horario,
        vendas_list_for_prediction,
    )
    dias_ordenados = build_daily_sales(vendas_list_for_prediction)
    crescimento = calculate_growth(dias_ordenados)
    produtos_estoque_previsao, produtos_risco = predict_stock_needs(vendas_list_for_prediction)
    
    # 4. Ticket médio
    ticket_medio = float(receita) / total_vendas if total_vendas > 0 else 0
    
    predicao_receita_3dias, confianca_receita = predict_revenue(dias_ordenados)
    
    # 7. Horários de pico (identificação simples)
    horarios_ordenados = sorted(vendas_por_horario.items(), key=lambda x: x[1], reverse=True)
    horarios_pico = [{"horario": h[0], "vendas": h[1]} for h in horarios_ordenados[:3]]
    
    # Garantir que tendenciaVendas sempre tenha dados (mesmo que vazios)
    if len(dias_ordenados) > 0:
        ultimos_7_dias = dias_ordenados[-7:]
        tendencia_dias = [d[0].isoformat() for d in ultimos_7_dias]
        tendencia_vendas = [d[1]["total"] for d in ultimos_7_dias]
        tendencia_receita = [round(d[1]["receita"], 2) for d in ultimos_7_dias]
    else:
        # Se não há dados, retorna array vazio para não quebrar os gráficos
        tendencia_dias = []
        tendencia_vendas = []
        tendencia_receita = []
        
    return Response({
        "totalVendas": total_vendas,
        "receita": receita,
        "clientesAtivos": clientes_ativos,
        "ticketMedio": round(ticket_medio, 2),
        "crescimentoPercentual": round(crescimento, 2),
        "vendasPorHorario": vendas_por_horario,
        "vendasPorCategoria": categoria_formatada,
        "topProdutos": top_produtos_formatado,
        "vendasDetalhadas": vendas_list,
        # Predições ML
        "predicaoDemanda": predicao_demanda,
        "predicaoReceita3Dias": predicao_receita_3dias,
        "produtosEstoquePrevisao": produtos_estoque_previsao[:10],  # Top 10
        "produtosRiscoEstoque": produtos_risco[:5],  # Top 5 mais críticos
        "horariosPico": horarios_pico,
        "tendenciaVendas": {
            "dias": tendencia_dias,
            "vendas": tendencia_vendas,
            "receita": tendencia_receita,
        },
        "confiancaPredicoes": {
            "demanda": confianca_demanda,
            "receita": confianca_receita,
        },
        "reservas": build_reservation_insights()
    })
