"""Piloto real: janela global sem apagar movimentos financeiros nem testes."""
import asyncio
import sys
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from piloto_real import effective_cutoff, start_pilot_once, read_pilot_since


class FakeCursor:
    def __init__(self, items):
        self.items = items

    async def to_list(self, maximum):
        return self.items[:maximum]


class FakeCollection:
    def __init__(self, items=()):
        self.items = list(items)
        self.queries = []

    def find(self, query, projection):
        self.queries.append(query)
        if "$and" in query:
            limit = query["$and"][0]["date"]["$gte"]
            items = [x for x in self.items if x["date"] >= limit]
        else:
            dt_key = "created_at"
            items = [x for x in self.items if x.get("currency") == query["currency"]
                     and x[dt_key] >= query[dt_key]["$gte"]]
        return FakeCursor(items)


class FakeSettings:
    def __init__(self):
        self.record = None
        self.writes = 0

    async def find_one(self, query, projection):
        return self.record

    async def update_one(self, query, update, upsert):
        if self.record is None:
            self.record = {**query, **update["$setOnInsert"]}
            self.writes += 1


class PilotoRealTests(unittest.TestCase):
    def test_cutoff_separates_past_without_rewriting_records(self):
        now = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(effective_cutoff(30, "2026-10-25T11:55:00Z", now=now),
                         "2026-10-25T11:55:00+00:00")
        self.assertEqual(effective_cutoff(30, None, now=now),
                         "2026-09-25T12:00:00+00:00")
        with self.assertRaises(ValueError):
            effective_cutoff(30, "2026-10-25T11:55:00", now=now)

    def test_pilot_baseline_one_write_and_persists_across_reads(self):
        settings = FakeSettings()
        with patch.dict(sys.modules, {"pymongo.errors": SimpleNamespace(DuplicateKeyError=type("DuplicateKeyError", (Exception,), {})), "core": SimpleNamespace(
            db=SimpleNamespace(platform_settings=settings),
            now_iso=lambda: "2026-10-25T11:55:00+00:00"
        )}):
            first = asyncio.run(start_pilot_once("admin1"))
            second = asyncio.run(start_pilot_once("admin2"))
            current = asyncio.run(read_pilot_since())
        self.assertEqual(first, second)
        self.assertEqual(current, "2026-10-25T11:55:00+00:00")
        self.assertEqual(settings.writes, 1)
        self.assertEqual(settings.record["started_by"], "admin1")

    def test_director_excludes_unflagged_old_clicks_and_test_events(self):
        from diretor_estrategia import snapshot_currency

        old = "2026-10-24T09:00:00+00:00"
        fresh = "2026-10-25T12:01:00+00:00"
        claims = FakeCollection([
            {"date": old, "currency": "eur"} for _ in range(4)
        ] + [{"date": fresh, "currency": "eur", "is_test": True}])
        sessions = FakeCollection([
            {"created_at": old, "currency": "eur", "scanned_at": old},
            {"created_at": fresh, "currency": "eur", "scanned_at": fresh, "is_test": True},
        ])
        charges = FakeCollection([])
        transactions = FakeCollection([
            {"created_at": old, "currency": "eur", "payment_status": "paid", "kind": "coupon_pay"}
        ])
        fake_db = SimpleNamespace(coupon_claims=claims, p5_sessions=sessions,
                                  p5_charges=charges, payment_transactions=transactions)
        fake_policy = SimpleNamespace(currency_query=lambda query, currency: {"$and": [query, {"currency": currency}]})
        with patch.dict(sys.modules, {"core": SimpleNamespace(db=fake_db, NO_ID={"_id": 0}), "payment_policy": fake_policy}), \
                patch("diretor_estrategia.read_pilot_since", return_value="2026-10-25T12:00:00+00:00"):
            report = asyncio.run(snapshot_currency("eur"))
        self.assertEqual(report["funil_observado"]["aberturas_cupom"], 0)
        self.assertEqual(report["funil_observado"]["scans_p5"], 0)
        self.assertEqual(report["funil_observado"]["sessoes_p5"], 0)
        self.assertEqual(report["funil_observado"]["pagamentos_p5"], 0)
        self.assertEqual(transactions.items[0]["payment_status"], "paid")  # preservado


if __name__ == "__main__":
    unittest.main()
