"""Small, deterministic forecast prototype trained only on synthetic events."""

from functools import lru_cache

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


def _features(category, price, event_day, hour, reservations, fichas):
    category_features = [int(category == value) for value in CATEGORIES]
    return category_features + [
        float(price or 0),
        event_day,
        hour,
        reservations,
        fichas,
    ]


def _row_features(row):
    return _features(
        row["category"], row["price"], row["event_day"], row["hour"],
        row["reservations"], row["fichas"],
    )


@lru_cache(maxsize=1)
def _trained_model():
    # shortcut: synthetic cohorts only; replace them with event-scoped real data when available.
    rows = generate_synthetic_event_history()
    event_ids = sorted({row["event_id"] for row in rows})
    holdout_events = set(event_ids[-2:])
    train_rows = [row for row in rows if row["event_id"] not in holdout_events]
    holdout_rows = [row for row in rows if row["event_id"] in holdout_events]
    train_x = [_row_features(row) for row in train_rows]
    train_y = [row["sales_units"] for row in train_rows]
    holdout_x = [_row_features(row) for row in holdout_rows]
    holdout_y = [row["sales_units"] for row in holdout_rows]

    parameters = {
        "n_estimators": 60,
        "max_depth": 8,
        "min_samples_leaf": 3,
        "random_state": 42,
        "n_jobs": 1,
    }
    evaluation_model = RandomForestRegressor(**parameters)
    evaluation_model.fit(train_x, train_y)
    holdout_prediction = evaluation_model.predict(holdout_x)
    baseline_prediction = [sum(train_y) / len(train_y)] * len(holdout_y)

    model = RandomForestRegressor(**parameters)
    model.fit(
        [_row_features(row) for row in rows],
        [row["sales_units"] for row in rows],
    )
    evaluation = {
        "metrica": "MAE em unidades por faixa horária",
        "mae_holdout": round(mean_absolute_error(holdout_y, holdout_prediction), 2),
        "mae_baseline": round(mean_absolute_error(holdout_y, baseline_prediction), 2),
        "eventos_treino": len(event_ids) - len(holdout_events),
        "eventos_holdout": len(holdout_events),
        "particao": "eventos completos mantidos fora do treino",
    }
    return model, evaluation


def synthetic_forecast_metadata():
    _, evaluation = _trained_model()
    return {
        "modelo": "RandomForestRegressor",
        "fonteDados": "sintetica",
        "aviso": SYNTHETIC_SOURCE_LABEL,
        "premissa": "Evento de três dias, das 16h às 22h.",
        "avaliacao": evaluation,
    }


def predict_product_demand(products, reservations_by_product=None):
    products = list(products)
    if not products:
        return [], None

    model, _ = _trained_model()
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
    return forecasts, synthetic_forecast_metadata()
