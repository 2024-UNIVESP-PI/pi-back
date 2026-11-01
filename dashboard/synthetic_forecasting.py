"""Event-level perishable demand forecast with a synthetic fallback."""

from collections.abc import Iterable, Mapping, Sequence
from functools import lru_cache
from typing import Any

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

from dashboard.synthetic_history import (
    CATEGORIES as HISTORY_CATEGORIES,
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


@lru_cache(maxsize=1)
def _trained_model() -> tuple[RandomForestRegressor, dict[str, Any]]:
    rows = generate_synthetic_event_history()
    model, metadata = train_event_forecast(rows, source="sintetica")
    return model, metadata["avaliacao"]


def synthetic_forecast_metadata() -> dict[str, Any]:
    _, evaluation = _trained_model()
    return _forecast_metadata("sintetica", evaluation)


def predict_product_demand(
    products: Iterable[Any],
    reservations_by_product: Mapping[int, Mapping[str, Any]] | None = None,
    history: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    products = list(products)
    if not products:
        return [], None

    if history is None:
        model, evaluation = _trained_model()
        metadata = _forecast_metadata("sintetica", evaluation)
    else:
        model, metadata = train_event_forecast(history)
    reservations_by_product = reservations_by_product or {}
    forecasts = []
    for product in products:
        reservation = reservations_by_product.get(product.id, {})
        reserved_quantity = int(reservation.get("quantidade", 0))
        reserved_people = int(reservation.get("pessoas", 0))
        forecast = 0

        for event_day in range(1, EVENT_DAYS + 1):
            for hour in EVENT_HOURS:
                forecast += max(0, model.predict([_features(
                    product.categoria,
                    float(product.preco or 0),
                    event_day,
                    hour,
                    reserved_quantity,
                    reserved_people,
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
