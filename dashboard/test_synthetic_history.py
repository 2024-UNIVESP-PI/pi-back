"""Sanity checks for the deterministic festa junina history fixture."""

import json
import unittest
from collections import defaultdict
from pathlib import Path

from dashboard.synthetic_history import (
    CATEGORIES,
    EVENT_DAYS,
    EVENT_HOURS,
    SCHEMA_FIELDS,
    build_synthetic_fixture,
    generate_synthetic_event_history,
)


class TestSyntheticHistory(unittest.TestCase):
    def test_history_is_repeatable_and_complete(self):
        first = generate_synthetic_event_history(seed=7, event_count=4)
        second = generate_synthetic_event_history(seed=7, event_count=4)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 4 * 4 * len(EVENT_DAYS) * len(EVENT_HOURS))
        self.assertEqual({row["event_id"] for row in first}, {
            "synthetic-event-01",
            "synthetic-event-02",
            "synthetic-event-03",
            "synthetic-event-04",
        })

    def test_history_has_sane_dimensions_values_and_categories(self):
        rows = generate_synthetic_event_history(seed=7, event_count=4)
        self.assertEqual({row["category"] for row in rows}, set(CATEGORIES))
        self.assertTrue(all(set(SCHEMA_FIELDS) <= row.keys() for row in rows))
        self.assertTrue(all(
            row["sales_units"] >= 0 and isinstance(row["sales_units"], int)
            for row in rows
        ))
        self.assertTrue(all(
            row["price"] > 0
            and row["stock"] >= 0
            and row["stock_available"] >= 0
            for row in rows
        ))
        self.assertTrue(all("cpf" not in row and "nome" not in row for row in rows))

        dimensions = {
            (row["event_id"], row["product"]): {
                (item["day"], item["hour"])
                for item in rows
                if (
                    item["event_id"] == row["event_id"]
                    and item["product"] == row["product"]
                )
            }
            for row in rows
        }
        expected_dimensions = {
            (day, hour) for day in EVENT_DAYS for hour in EVENT_HOURS
        }
        self.assertTrue(
            all(values == expected_dimensions for values in dimensions.values())
        )

    def test_distributions_reflect_documented_priors_and_holdout_readiness(self):
        rows = generate_synthetic_event_history(seed=7, event_count=6)
        sales_by_category = defaultdict(int)
        sales_by_hour = defaultdict(list)
        for row in rows:
            sales_by_category[row["category"]] += row["sales_units"]
            sales_by_hour[row["hour"]].append(row["sales_units"])

        self.assertGreater(sales_by_category["salgados"], sales_by_category["doces"])
        self.assertGreater(
            sales_by_category["bebidas"], sales_by_category["comidas_tipicas"]
        )
        opening = sum(sum(sales_by_hour[hour]) for hour in (16, 17))
        evening = sum(sum(sales_by_hour[hour]) for hour in (19, 20, 21))
        self.assertGreater(evening, opening)

        event_ids = sorted({row["event_id"] for row in rows})
        holdout = set(event_ids[-2:])
        self.assertTrue(holdout)
        self.assertTrue(holdout.isdisjoint(set(event_ids[:-2])))
        self.assertTrue(all(row["event_id"] == event_ids[-1]
                            for row in rows if row["event_id"] == event_ids[-1]))

    def test_checked_in_fixture_matches_seeded_generator(self):
        fixture_path = (
            Path(__file__).with_name("fixtures") / "synthetic_event_history.json"
        )
        fixture = json.loads(fixture_path.read_text())
        expected = build_synthetic_fixture()

        self.assertEqual(fixture, expected)
        self.assertEqual(fixture["metadata"]["evaluation"]["holdout_unit"], "event_id")
        self.assertIn("partner school", fixture["metadata"]["source"])
