from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Sum, Count, F, DecimalField, ExpressionWrapper, Avg
from django.utils.timezone import localtime, now, timedelta
from datetime import datetime
from collections import defaultdict
from movimentacao.models import Venda, Produto, ReservaProduto

@api_view(['GET'])
def dashboard_data(request):
    # Verificar se há vendas antes de processar
    vendas = Venda.objects.select_related(
        'movimentacao__produto',
        'movimentacao__caixa',
        'ficha'
    ).annotate(
        valor_total=ExpressionWrapper(
            F('movimentacao__produto__preco') * F('movimentacao__quantidade'),
            output_field=DecimalField()
        )
    )

    total_vendas = vendas.count()
    receita = vendas.aggregate(total=Sum('valor_total'))['total'] or 0
    clientes_ativos = vendas.values('ficha').distinct().count()

    # Inicializa vendas por horário (sempre retorna dicionário com 24 horas)
    vendas_por_horario = {f"{h:02d}h-{(h+1)%24:02d}h": 0 for h in range(24)}

    # Processa vendas por horário apenas se houver vendas
    if vendas.exists():
        for v in vendas:
            try:
                hora = localtime(v.data).hour
                chave = f"{hora:02d}h-{(hora+1)%24:02d}h"
                vendas_por_horario[chave] += 1
            except (AttributeError, TypeError):
                # Se houver erro ao acessar data, continua
                continue

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

    # Garantir que categoria_formatada sempre seja uma lista (mesmo vazia)
    categoria_formatada = []
    vendas_por_categoria_list = list(vendas_por_categoria)
    if vendas_por_categoria_list:
        categoria_formatada = [
            {
                "name": f"{EMOJIS_CATEGORIA.get(cat['movimentacao__produto__categoria'].lower() if cat['movimentacao__produto__categoria'] else '', '')} {cat['movimentacao__produto__categoria'].capitalize() if cat['movimentacao__produto__categoria'] else 'Sem categoria'}",
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
    if vendas.exists():
        for v in vendas:
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
                "produto_preco": float(produto.preco) if produto else 0,
                "categoria": (produto.categoria or "Sem categoria") if produto else "Sem categoria",
                "quantidade": v.movimentacao.quantidade,
                "valorTotal": float(v.valor_total),
            })
    
    # ========== PREDIÇÕES SIMPLES DE ML ==========
    
    # 1. Predição de demanda por horário (média móvel simples)
    # Calcula média das últimas horas para prever próximas horas
    vendas_por_horario_lista = [(k, v) for k, v in vendas_por_horario.items()]
    vendas_por_horario_lista.sort(key=lambda x: x[0])
    
    # Predição: média móvel dos últimos 3 períodos
    predicao_demanda = {}
    if len(vendas_por_horario_lista) >= 3:
        for i in range(3, len(vendas_por_horario_lista)):
            media = sum([v[1] for v in vendas_por_horario_lista[i-3:i]]) / 3
            predicao_demanda[vendas_por_horario_lista[i][0]] = round(media, 1)
    
    # Predição para próximas 3 horas
    if vendas_por_horario_lista:
        ultimas_3 = [v[1] for v in vendas_por_horario_lista[-3:]]
        media_ultimas = sum(ultimas_3) / len(ultimas_3) if ultimas_3 else 0
        hora_atual = now().hour
        for i in range(1, 4):
            hora_futura = (hora_atual + i) % 24
            chave = f"{hora_futura:02d}h-{(hora_futura+1)%24:02d}h"
            predicao_demanda[chave] = round(media_ultimas, 1)
    
    # 2. Tendência de vendas (linear simples)
    # Agrupa vendas por dia
    vendas_por_dia = defaultdict(lambda: {"total": 0, "receita": 0})
    for v in vendas:
        data_venda = localtime(v.data).date()
        vendas_por_dia[data_venda]["total"] += 1
        vendas_por_dia[data_venda]["receita"] += float(v.valor_total)
    
    # Ordena por data
    dias_ordenados = sorted(vendas_por_dia.items())
    
    # Calcula tendência (últimos 7 dias vs 7 dias anteriores)
    if len(dias_ordenados) >= 14:
        ultimos_7 = dias_ordenados[-7:]
        anteriores_7 = dias_ordenados[-14:-7]
        
        media_ultimos = sum([d[1]["total"] for d in ultimos_7]) / 7
        media_anteriores = sum([d[1]["total"] for d in anteriores_7]) / 7
        
        if media_anteriores > 0:
            crescimento = ((media_ultimos - media_anteriores) / media_anteriores) * 100
        else:
            crescimento = 0
    elif len(dias_ordenados) >= 7:
        ultimos_7 = dias_ordenados[-7:]
        media_ultimos = sum([d[1]["total"] for d in ultimos_7]) / 7
        crescimento = media_ultimos * 10  # Estimativa positiva se há dados
    else:
        crescimento = 0
    
    # 3. Previsão de estoque necessário (baseado em média de vendas)
    # Calcula média de vendas por produto nos últimos 7 dias
    produtos_estoque_previsao = []
    if len(dias_ordenados) >= 7:
        ultimos_7_dias = [d[0] for d in dias_ordenados[-7:]]
        vendas_ultimos_7 = []
        for v in vendas:
            data_venda = localtime(v.data).date()
            if data_venda in ultimos_7_dias:
                vendas_ultimos_7.append(v)
        
        vendas_por_produto = defaultdict(lambda: {"quantidade": 0, "dias": set()})
        for v in vendas_ultimos_7:
            produto = v.movimentacao.produto
            vendas_por_produto[produto.id]["quantidade"] += v.movimentacao.quantidade
            vendas_por_produto[produto.id]["dias"].add(localtime(v.data).date())
        
        for produto_id, dados in vendas_por_produto.items():
            produto = Produto.objects.get(id=produto_id)
            dias_com_vendas = len(dados["dias"])
            if dias_com_vendas > 0:
                media_diaria = dados["quantidade"] / dias_com_vendas
                # Previsão: 3 dias de estoque baseado na média
                estoque_recomendado = round(media_diaria * 3, 1)
                produtos_estoque_previsao.append({
                    "produto": produto.nome,
                    "estoque_atual": produto.estoque,
                    "estoque_recomendado": estoque_recomendado,
                    "media_diaria": round(media_diaria, 1),
                    "necessita_reposicao": produto.estoque < estoque_recomendado,
                })
    
    # 4. Ticket médio
    ticket_medio = float(receita) / total_vendas if total_vendas > 0 else 0
    
    # 5. Predição de receita futura (baseada em tendência)
    if len(dias_ordenados) >= 7:
        ultimos_7 = dias_ordenados[-7:]
        receita_media_diaria = sum([d[1]["receita"] for d in ultimos_7]) / 7
        # Predição para próximos 3 dias
        predicao_receita_3dias = round(receita_media_diaria * 3, 2)
    else:
        predicao_receita_3dias = 0
    
    # 6. Produtos em risco de estoque (baixo estoque vs demanda)
    produtos_risco = []
    for produto in Produto.objects.all():
        if produto.estoque > 0:
            # Calcula demanda média se houver vendas
            vendas_produto = Venda.objects.filter(
                movimentacao__produto=produto
            ).select_related('movimentacao')
            
            if vendas_produto.exists():
                total_vendido = sum([v.movimentacao.quantidade for v in vendas_produto])
                dias_com_vendas_set = set()
                for v in vendas_produto:
                    dias_com_vendas_set.add(localtime(v.data).date())
                dias_com_vendas = len(dias_com_vendas_set)
                if dias_com_vendas > 0:
                    demanda_media = total_vendido / dias_com_vendas
                    dias_estoque_restante = produto.estoque / demanda_media if demanda_media > 0 else 999
                    
                    if dias_estoque_restante < 3 and dias_estoque_restante > 0:
                        produtos_risco.append({
                            "produto": produto.nome,
                            "estoque_atual": produto.estoque,
                            "dias_restantes": round(dias_estoque_restante, 1),
                            "demanda_media": round(demanda_media, 1),
                        })
    
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
        # Dados de ML sobre reservas (mínimos)
        "reservas": {
            "total_pendentes": ReservaProduto.objects.filter(status='pendente', ficha__isnull=True).count(),
            "total_finalizadas": ReservaProduto.objects.filter(status='finalizada').count(),
            "taxa_conversao": round((ReservaProduto.objects.filter(status='finalizada').count() / max(ReservaProduto.objects.count(), 1)) * 100, 2) if ReservaProduto.objects.exists() else 0,
            "produtos_mais_reservados": [
                {
                    "produto": item["produto__nome"],
                    "total_reservas": item["total"]
                }
                for item in ReservaProduto.objects.values('produto__nome')
                .annotate(total=Count('id'))
                .order_by('-total')[:5]
            ],
            "tendencia_7dias": [
                {
                    "data": (now() - timedelta(days=i)).strftime("%d/%m"),
                    "pendentes": ReservaProduto.objects.filter(
                        status='pendente',
                        data_reserva__date=(now() - timedelta(days=i)).date()
                    ).count(),
                    "finalizadas": ReservaProduto.objects.filter(
                        status='finalizada',
                        data_confirmacao__date=(now() - timedelta(days=i)).date()
                    ).count()
                }
                for i in range(6, -1, -1)  # Últimos 7 dias
            ]
        }
    })
