"""Deterministic synthetic purchase history for festa junina forecasts.

The values in this module are simulated priors inspired by common school festa
junina buying patterns. They are not observations from the partner school.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any


DEFAULT_SEED = 20240624
EVENT_DAYS = (1, 2, 3)
EVENT_HOURS = (16, 17, 18, 19, 20, 21, 22)
EVENT_WINDOW = "16:00-22:00"
CATEGORIES = ("bebidas", "salgados", "doces", "comidas_tipicas")
SCHEMA_VERSION = "1.0"

HOUR_FACTORS = {
    16: 0.25,
    17: 0.50,
    18: 0.86,
    19: 1.14,
    20: 1.30,
    21: 1.08,
    22: 0.68,
}
DAY_FACTORS = {1: 0.86, 2: 1.00, 3: 0.93}


@dataclass(frozen=True)
class ProductProfile:
    """Distribution prior for one synthetic product."""

    product: str
    category: str
    price: float
    base_demand: float
    reservation_rate: float


PRODUCT_PROFILES = (
    ProductProfile("pastel", "salgados", 8.00, 44.0, 0.30),
    ProductProfile("refrigerante", "bebidas", 6.00, 42.0, 0.22),
    ProductProfile("pacoca", "doces", 3.00, 23.0, 0.12),
    ProductProfile("canjica", "comidas_tipicas", 7.00, 19.0, 0.16),
)

SCHEMA_FIELDS = (
    "event_id",
    "product",
    "product_number",
    "category",
    "day",
    "event_day",
    "hour",
    "price",
    "stock",
    "stock_available",
    "active_reservations",
    "reservations",
    "issued_fichas",
    "fichas",
    "sales_units",
)


def history_metadata(seed: int, event_count: int) -> dict[str, Any]:
    """Return reviewable assumptions and schema metadata for a generated set."""
    return {
        "schema_version": SCHEMA_VERSION,
        "seed": seed,
        "event_count": event_count,
        "event_days": len(EVENT_DAYS),
        "event_window": EVENT_WINDOW,
        "hours": [f"{hour:02d}:00-{hour + 1:02d}:00" for hour in EVENT_HOURS],
        "source": (
            "Simulated priors inspired by common festa junina buying patterns; "
            "not observations from the partner school."
        ),
        "privacy": "No CPF, names, or other personal records are generated.",
        "evaluation": {
            "holdout_unit": "event_id",
            "holdout_ready": True,
            "split_rule": "Keep all rows from whole events together.",
        },
        "assumptions": {
            "traffic_by_hour": {
                str(hour): factor for hour, factor in HOUR_FACTORS.items()
            },
            "day_factors": {str(day): factor for day, factor in DAY_FACTORS.items()},
            "category_demand_order": [
                "salgados",
                "bebidas",
                "doces",
                "comidas_tipicas",
            ],
            "reservation_rate_by_category": {
                category: round(sum(
                    profile.reservation_rate
                    for profile in PRODUCT_PROFILES
                    if profile.category == category
                ) / sum(
                    1 for profile in PRODUCT_PROFILES if profile.category == category
                ), 2)
                for category in CATEGORIES
            },
            "active_reservation_uplift": (
                "0.08 units per reservation times the hour factor"
            ),
            "issued_ficha_uplift": "0.006 units per issued ficha times the hour factor",
            "variation": "Event factor 0.90-1.12; day factors and 10% demand noise.",
            "stock": (
                "Initial stock is demand plus a 15% safety buffer, capped by sales."
            ),
        },
        "schema": list(SCHEMA_FIELDS),
    }


def generate_synthetic_event_history(
    seed: int = DEFAULT_SEED,
    event_count: int = 4,
) -> list[dict[str, Any]]:
    """Generate complete, reproducible event/product/day/hour observations.

    Args:
        seed: Seed for all random variation.
        event_count: Number of complete three-day events to generate.

    Raises:
        ValueError: If fewer than three events are requested, preventing a
            meaningful event-level holdout.
    """
    if event_count < 3:
        raise ValueError("At least three events are required for event-level holdout.")

    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    for event_number in range(event_count):
        event_id = f"synthetic-event-{event_number + 1:02d}"
        event_factor = 0.90 + (0.22 * rng.random())
        event_products: list[tuple[ProductProfile, int]] = []

        for profile in PRODUCT_PROFILES:
            reservations = max(
                0,
                round(24 * event_factor * profile.reservation_rate)
                + rng.randint(-1, 2),
            )
            event_products.append((profile, reservations))

        fichas = max(1, round(110 * event_factor) + rng.randint(-4, 4))
        for product_number, (profile, reservations) in enumerate(event_products):
            expected_total = sum(
                profile.base_demand
                * event_factor
                * DAY_FACTORS[day]
                * HOUR_FACTORS[hour]
                + reservations * 0.08 * HOUR_FACTORS[hour]
                + fichas * 0.006 * HOUR_FACTORS[hour]
                for day in EVENT_DAYS
                for hour in EVENT_HOURS
            )
            stock = max(1, round(expected_total * 1.15))
            remaining_stock = stock

            for day in EVENT_DAYS:
                for hour in EVENT_HOURS:
                    expected = (
                        profile.base_demand
                        * event_factor
                        * DAY_FACTORS[day]
                        * HOUR_FACTORS[hour]
                        + reservations * 0.08 * HOUR_FACTORS[hour]
                        + fichas * 0.006 * HOUR_FACTORS[hour]
                    )
                    noisy_sales = round(
                        expected + rng.gauss(0, max(0.5, expected * 0.10))
                    )
                    sales_units = min(remaining_stock, max(0, noisy_sales))
                    rows.append({
                        "event_id": event_id,
                        "product": profile.product,
                        "product_number": product_number,
                        "category": profile.category,
                        "day": day,
                        "event_day": day,
                        "hour": hour,
                        "price": profile.price,
                        "stock": stock,
                        "stock_available": remaining_stock,
                        "active_reservations": reservations,
                        "reservations": reservations,
                        "issued_fichas": fichas,
                        "fichas": fichas,
                        "sales_units": sales_units,
                    })
                    remaining_stock -= sales_units

    return rows


def build_synthetic_fixture(
    seed: int = DEFAULT_SEED,
    event_count: int = 3,
) -> dict[str, Any]:
    """Return the checked-in fixture shape with metadata and generated rows."""
    return {
        "metadata": history_metadata(seed, event_count),
        "rows": generate_synthetic_event_history(seed, event_count),
    }
