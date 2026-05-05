from collections import defaultdict
from statistics import pstdev

from django.db.models import Count
from django.utils.timezone import localtime, now, timedelta

from movimentacao.models import Produto, ReservaProduto


def _hour_key(hour):
    return f"{hour:02d}h-{(hour + 1) % 24:02d}h"


def _weighted_average(values):
    if not values:
        return 0

    weights = list(range(1, len(values) + 1))
    weighted_total = sum(value * weight for value, weight in zip(values, weights))
    return weighted_total / sum(weights)


def _confidence(sample_size, variability):
    base = min(0.95, 0.35 + sample_size * 0.06)
    penalty = min(0.35, variability * 0.08)
    return round(max(0.2, base - penalty), 2)


def build_daily_sales(vendas):
    vendas_por_dia = defaultdict(lambda: {"total": 0, "receita": 0})
    for venda in vendas:
        data_venda = localtime(venda.data).date()
        vendas_por_dia[data_venda]["total"] += 1
        vendas_por_dia[data_venda]["receita"] += float(venda.valor_total or 0)
    return sorted(vendas_por_dia.items())


def predict_hourly_demand(vendas_por_horario, vendas, horizon=4):
    hourly_counts = [vendas_por_horario[_hour_key(hour)] for hour in range(24)]
    non_zero_hours = [value for value in hourly_counts if value > 0]
    overall_average = sum(hourly_counts) / 24 if hourly_counts else 0
    active_average = sum(non_zero_hours) / len(non_zero_hours) if non_zero_hours else 0
    variability = pstdev(non_zero_hours) if len(non_zero_hours) > 1 else 0
    sample_size = len(vendas)
    confidence = _confidence(sample_size, variability)

    predictions = {}
    current_hour = now().hour

    for offset in range(1, horizon + 1):
        hour = (current_hour + offset) % 24
        key = _hour_key(hour)
        previous_hours = [
            hourly_counts[(hour - 3) % 24],
            hourly_counts[(hour - 2) % 24],
            hourly_counts[(hour - 1) % 24],
        ]
        recency_signal = _weighted_average(previous_hours)
        same_hour_signal = hourly_counts[hour]
        baseline = active_average if active_average > 0 else overall_average
        prediction = (
            recency_signal * 0.45 +
            same_hour_signal * 0.35 +
            baseline * 0.20
        )
        predictions[key] = round(max(0, prediction), 1)

    return predictions, confidence


def calculate_growth(dias_ordenados):
    if len(dias_ordenados) >= 14:
        ultimos = dias_ordenados[-7:]
        anteriores = dias_ordenados[-14:-7]
    elif len(dias_ordenados) >= 2:
        midpoint = len(dias_ordenados) // 2
        anteriores = dias_ordenados[:midpoint]
        ultimos = dias_ordenados[midpoint:]
    else:
        return 0

    media_ultimos = sum(day[1]["total"] for day in ultimos) / len(ultimos)
    media_anteriores = sum(day[1]["total"] for day in anteriores) / len(anteriores)

    if media_anteriores <= 0:
        return 0

    return ((media_ultimos - media_anteriores) / media_anteriores) * 100


def predict_revenue(dias_ordenados, horizon_days=3):
    if not dias_ordenados:
        return 0, 0

    recent_days = dias_ordenados[-min(7, len(dias_ordenados)):]
    receitas = [day[1]["receita"] for day in recent_days]
    base = _weighted_average(receitas)
    confidence = _confidence(len(receitas), pstdev(receitas) / base if base else 0)

    return round(base * horizon_days, 2), confidence


def predict_stock_needs(vendas, days_window=7, safety_days=3):
    if not vendas:
        return [], []

    cutoff = now().date() - timedelta(days=days_window - 1)
    vendas_recentes = [
        venda for venda in vendas
        if localtime(venda.data).date() >= cutoff
    ]
    vendas_por_produto = defaultdict(lambda: {"quantidade": 0, "dias": set()})

    for venda in vendas_recentes:
        produto = venda.movimentacao.produto
        vendas_por_produto[produto.id]["quantidade"] += venda.movimentacao.quantidade
        vendas_por_produto[produto.id]["dias"].add(localtime(venda.data).date())

    produtos_estoque_previsao = []
    produtos_risco = []

    produtos = Produto.objects.in_bulk(vendas_por_produto.keys())
    for produto_id, dados in vendas_por_produto.items():
        produto = produtos.get(produto_id)
        if not produto:
            continue

        dias_com_vendas = max(1, len(dados["dias"]))
        media_diaria = dados["quantidade"] / dias_com_vendas
        margem_seguranca = 1.25 if dias_com_vendas < days_window else 1.15
        estoque_recomendado = round(media_diaria * safety_days * margem_seguranca, 1)
        dias_restantes = produto.estoque / media_diaria if media_diaria > 0 else 999
        confidence = _confidence(dias_com_vendas, 0)

        produtos_estoque_previsao.append({
            "produto": produto.nome,
            "estoque_atual": produto.estoque,
            "estoque_recomendado": estoque_recomendado,
            "media_diaria": round(media_diaria, 1),
            "necessita_reposicao": produto.estoque < estoque_recomendado,
            "confianca": confidence,
        })

        if 0 < dias_restantes < safety_days:
            produtos_risco.append({
                "produto": produto.nome,
                "estoque_atual": produto.estoque,
                "dias_restantes": round(dias_restantes, 1),
                "demanda_media": round(media_diaria, 1),
                "confianca": confidence,
            })

    produtos_estoque_previsao.sort(
        key=lambda produto: (
            not produto["necessita_reposicao"],
            produto["estoque_recomendado"] - produto["estoque_atual"],
        )
    )
    produtos_risco.sort(key=lambda produto: produto["dias_restantes"])

    return produtos_estoque_previsao[:10], produtos_risco[:5]


def build_reservation_insights():
    total_reservas = ReservaProduto.objects.count()
    total_finalizadas = ReservaProduto.objects.filter(status='finalizada').count()
    total_pendentes = ReservaProduto.objects.filter(status='pendente', ficha__isnull=True).count()

    return {
        "total_pendentes": total_pendentes,
        "total_finalizadas": total_finalizadas,
        "taxa_conversao": round((total_finalizadas / max(total_reservas, 1)) * 100, 2) if total_reservas else 0,
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
            for i in range(6, -1, -1)
        ]
    }
