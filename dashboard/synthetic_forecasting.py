"""Event-level perishable demand forecast with a synthetic fallback."""

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from functools import lru_cache
from typing import Any

from django.db.models import Sum
from django.utils.timezone import localtime
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

from movimentacao.models import ReservaProduto
from dashboard.synthetic_history import (
    CATEGORIES as HISTORY_CATEGORIES,
    EVENT_DAYS,
    EVENT_HOURS,
    generate_synthetic_event_history,
)


SYNTHETIC_SOURCE_LABEL = (
    "Dados sintéticos de demonstração; previsões não validadas em eventos reais."
)
EVENT_DAYS = 3
CATEGORIES = (*HISTORY_CATEGORIES, "jogos")
MIN_TRAINING_EVENTS = 3
HOLDOUT_EVENT_COUNT = 2
OPERATIONAL_SOURCE = "operacional"
OPERATIONAL_EVENT_PREFIX = "operacional"


def _features(
    category: str,
    price: float,
    event_day: int,
    hour: int,
    reservations: int,
    fichas: int,
) -> list[float]:
    category_features = [float(category == value) for value in CATEGORIES]
    return category_features + [
        float(price or 0),
        float(event_day),
        float(hour),
        float(reservations),
        float(fichas),
    ]


def _row_features(row: Mapping[str, Any]) -> list[float]:
    return _features(
        row["category"], row["price"], row["event_day"], row["hour"],
        row["reservations"], row["fichas"],
    )


def _split_event_history(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]], list[str]]:
    """Split complete events so no event contributes to both train and holdout."""
    event_ids = sorted({str(row["event_id"]) for row in rows})
    if len(event_ids) < MIN_TRAINING_EVENTS:
        raise ValueError("At least three events are required for event-level holdout.")

    holdout_events = set(event_ids[-HOLDOUT_EVENT_COUNT:])
    train_rows = [row for row in rows if str(row["event_id"]) not in holdout_events]
    holdout_rows = [row for row in rows if str(row["event_id"]) in holdout_events]
    return train_rows, holdout_rows, event_ids


def _fit_model(rows: Sequence[Mapping[str, Any]]) -> RandomForestRegressor:
    parameters = {
        "n_estimators": 60,
        "max_depth": 8,
        "min_samples_leaf": 3,
        "random_state": 42,
        "n_jobs": 1,
    }
    model = RandomForestRegressor(**parameters)
    model.fit(
        [_row_features(row) for row in rows],
        [row["sales_units"] for row in rows],
    )
    return model


def _train_and_evaluate(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[RandomForestRegressor, dict[str, Any]]:
    train_rows, holdout_rows, event_ids = _split_event_history(rows)
    train_x = [_row_features(row) for row in train_rows]
    train_y = [row["sales_units"] for row in train_rows]
    holdout_x = [_row_features(row) for row in holdout_rows]
    holdout_y = [row["sales_units"] for row in holdout_rows]

    evaluation_model = _fit_model(train_rows)
    holdout_prediction = evaluation_model.predict(holdout_x)
    baseline_prediction = [sum(train_y) / len(train_y)] * len(holdout_y)

    return _fit_model(rows), {
        "metrica": "MAE em unidades por faixa horária",
        "mae_holdout": round(mean_absolute_error(holdout_y, holdout_prediction), 2),
        "mae_baseline": round(mean_absolute_error(holdout_y, baseline_prediction), 2),
        "eventos_treino": len(event_ids) - HOLDOUT_EVENT_COUNT,
        "eventos_holdout": HOLDOUT_EVENT_COUNT,
        "particao": "eventos completos mantidos fora do treino",
    }


def _forecast_metadata(source: str, evaluation: dict[str, Any]) -> dict[str, Any]:
    is_synthetic = source == "sintetica"
    return {
        "modelo": "RandomForestRegressor",
        "fonteDados": source,
        "aviso": SYNTHETIC_SOURCE_LABEL if is_synthetic else (
            "Histórico anonimizado de eventos; MAE avaliado em eventos completos."
        ),
        "validacaoReal": not is_synthetic,
        "premissa": "Evento de três dias, das 16h às 22h.",
        "avaliacao": evaluation,
    }


def train_event_forecast(
    history: Sequence[Mapping[str, Any]] | None = None,
    *,
    source: str = "real",
) -> tuple[RandomForestRegressor, dict[str, Any]]:
    """Train from event-level history, falling back to explicit synthetic data.

    Args:
        history: Rows matching the synthetic history schema, or ``None``.
        source: Metadata label for a supplied non-synthetic history.

    Returns:
        The fitted model and response metadata.
    """
    rows = list(history or ())
    event_count = len({str(row["event_id"]) for row in rows})
    if event_count < MIN_TRAINING_EVENTS:
        rows = generate_synthetic_event_history()
        source = "sintetica"

    model, evaluation = _train_and_evaluate(rows)
    return model, _forecast_metadata(source, evaluation)


def _operational_events(
    days: Sequence[Any],
    event_days: int = EVENT_DAYS,
) -> list[list[Any]]:
    """Group consecutive operational days into complete event windows."""
    groups: list[list[Any]] = []
    current: list[Any] = []
    for day in sorted(set(days)):
        if current and (day - current[-1]).days > 1:
            groups.append(current)
            current = []
        current.append(day)
    if current:
        groups.append(current)

    events: list[list[Any]] = []
    for group in groups:
        for start in range(0, len(group) - event_days + 1, event_days):
            events.append(list(group[start:start + event_days]))
    return events


def build_operational_history(
    vendas: Sequence[Any],
    event_days: int = EVENT_DAYS,
) -> list[dict[str, Any]]:
    """Build event-level history rows from real operational sales.

    Consecutive days of sales are grouped into complete events of
    ``event_days`` consecutive days, mirroring the synthetic event shape.
    """
    vendas_por_dia: dict[Any, list[Any]] = defaultdict(list)
    for venda in vendas:
        vendas_por_dia[localtime(venda.data).date()].append(venda)

    products_by_id = {
        venda.movimentacao.produto_id: venda.movimentacao.produto
        for venda in vendas
    }

    rows: list[dict[str, Any]] = []
    events = _operational_events(list(vendas_por_dia), event_days)
    for event_number, days in enumerate(events, start=1):
        event_id = f"{OPERATIONAL_EVENT_PREFIX}-{event_number:02d}"
        event_start = days[0]

        vendas_evento = sorted(
            [venda for day in days for venda in vendas_por_dia.get(day, [])],
            key=lambda venda: (
                localtime(venda.data).date(),
                localtime(venda.data).hour,
                venda.movimentacao.produto_id,
                venda.id,
            ),
        )
        vendas_por_produto: dict[int, int] = defaultdict(int)
        fichas_por_produto: dict[int, set[int]] = defaultdict(set)
        vendas_por_chave: dict[tuple[int, Any, int], int] = defaultdict(int)

        for venda in vendas_evento:
            produto = venda.movimentacao.produto
            stamp = localtime(venda.data)
            vendas_por_produto[produto.id] += venda.movimentacao.quantidade
            fichas_por_produto[produto.id].add(venda.ficha.numero)
            vendas_por_chave[(produto.id, stamp.date(), stamp.hour)] += venda.movimentacao.quantidade

        stock_inicial: dict[int, int] = {
            produto_id: max(1, unidades_totais)
            for produto_id, unidades_totais in vendas_por_produto.items()
        }
        stock_restante = dict(stock_inicial)
        product_numbers: dict[int, int] = defaultdict(int)

        reservas_por_produto = {
            produto_id: (
                ReservaProduto.objects.filter(
                    produto_id=produto_id,
                    status__in=["pendente", "confirmada"],
                    data_reserva__date__gte=event_start,
                    data_reserva__date__lte=days[-1],
                ).aggregate(total=Sum("quantidade"))["total"]
                or 0
            )
            for produto_id in vendas_por_produto
        }

        for (produto_id, day, hour), unidades in sorted(
            vendas_por_chave.items(),
            key=lambda item: (item[0][1], item[0][2], item[0][0]),
        ):
            produto = products_by_id[produto_id]
            categoria = produto.categoria or "comidas_tipicas"
            day_offset = (day - event_start).days + 1
            fichas = len(fichas_por_produto[produto_id])
            reservas = int(reservas_por_produto[produto_id])

            rows.append({
                "event_id": event_id,
                "product": produto.nome,
                "product_number": product_numbers[produto_id],
                "category": categoria,
                "day": day_offset,
                "event_day": day_offset,
                "hour": hour,
                "price": float(produto.preco or 0),
                "stock": int(stock_inicial[produto_id]),
                "stock_available": int(max(0, stock_restante[produto_id])),
                "active_reservations": reservas,
                "reservations": reservas,
                "issued_fichas": fichas,
                "fichas": fichas,
                "sales_units": unidades,
            })
            stock_restante[produto_id] -= unidades
            product_numbers[produto_id] += 1

    return rows


@lru_cache(maxsize=1)
def _trained_model() -> tuple[RandomForestRegressor, dict[str, Any]]:
    rows = generate_synthetic_event_history()
    model, metadata = train_event_forecast(rows, source="sintetica")
    return model, metadata["avaliacao"]


def synthetic_forecast_metadata() -> dict[str, Any]:
    _, evaluation = _trained_model()
    return _forecast_metadata("sintetica", evaluation)


def _history_slots(
    history_rows: Sequence[Mapping[str, Any]],
    product: Any,
) -> dict[tuple[int, int], Mapping[str, Any]]:
    """Index history rows by (event_day, hour) for a given product."""
    slots: dict[tuple[int, int], Mapping[str, Any]] = {}
    for row in history_rows:
        if str(row.get("category")) != str(product.categoria):
            continue
        if abs(float(row.get("price") or 0) - float(product.preco or 0)) > 0.01:
            continue
        slots[(int(row["event_day"]), int(row["hour"]))] = row
    return slots


def predict_product_demand(
    products: Iterable[Any],
    reservations_by_product: Mapping[int, Mapping[str, Any]] | None = None,
    history: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    products = list(products)
    if not products:
        return [], None

    history_rows = list(history) if history is not None else []
    source = "sintetica"
    if history_rows:
        model, metadata = train_event_forecast(history_rows, source=OPERATIONAL_SOURCE)
        source = metadata["fonteDados"]
        if source == "sintetica":
            model, evaluation = _trained_model()
            metadata = _forecast_metadata("sintetica", evaluation)
    else:
        model, evaluation = _trained_model()
        metadata = _forecast_metadata("sintetica", evaluation)

    reservations_by_product = reservations_by_product or {}
    forecasts = []
    for product in products:
        reservation = reservations_by_product.get(product.id, {})
        reserved_quantity = int(reservation.get("quantidade", 0))
        reserved_people = int(reservation.get("pessoas", 0))
        forecast = 0
        slots = _history_slots(history_rows, product) if history_rows else {}

        for event_day in range(1, EVENT_DAYS + 1):
            for hour in EVENT_HOURS:
                row = slots.get((event_day, hour))
                slot_reservations = int(row.get("reservations") or 0) if row is not None else reserved_quantity
                slot_fichas = int(row.get("fichas") or 0) if row is not None else reserved_people
                forecast += max(0, model.predict([_features(
                    product.categoria,
                    float(product.preco or 0),
                    event_day,
                    hour,
                    slot_reservations,
                    slot_fichas,
                )])[0])

        demand = max(0, round(forecast))
        forecasts.append({
            "produtoId": product.id,
            "produto": product.nome,
            "categoria": product.categoria,
            "demandaPrevista3Dias": demand,
            "reservasAtivas": reserved_quantity,
            "fichasRelacionadas": reserved_people,
            "estoqueAtual": product.estoque,
            "producaoSugerida": max(0, demand - product.estoque),
        })

    forecasts.sort(key=lambda item: item["demandaPrevista3Dias"], reverse=True)
    return forecasts, metadata
