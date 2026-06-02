import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


class PsychologyRoutesTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.tmpdir.name) / "trading_journal.db"
        app.state.database_path = self.database_path
        self.client = TestClient(app)

    def tearDown(self):
        if hasattr(app.state, "database_path"):
            delattr(app.state, "database_path")
        self.tmpdir.cleanup()

    def create_trade(self, **overrides):
        payload = {
            "symbol": "ES",
            "direction": "long",
            "status": "closed",
            "pnl": 100,
        }
        payload.update(overrides)
        response = self.client.post("/trades", json=payload)
        self.assertEqual(response.status_code, 201)
        return response.json()

    def psychology_payload(self, **overrides):
        payload = {
            "confidence_score": 4,
            "fear_score": 2,
            "fomo_score": 1,
            "discipline_score": 5,
            "clarity_score": 4,
            "notes": "Stayed patient before entry.",
        }
        payload.update(overrides)
        return payload

    def test_create_update_get_delete_psychology_entry(self):
        trade = self.create_trade(symbol="NQ")

        created = self.client.post(f"/trades/{trade['id']}/psychology", json=self.psychology_payload())
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["trade_id"], trade["id"])
        self.assertEqual(created.json()["confidence_score"], 4)

        fetched = self.client.get(f"/trades/{trade['id']}/psychology")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["notes"], "Stayed patient before entry.")

        updated = self.client.put(
            f"/trades/{trade['id']}/psychology",
            json=self.psychology_payload(confidence_score=5, notes="Waited for confirmation."),
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["confidence_score"], 5)
        self.assertEqual(updated.json()["notes"], "Waited for confirmation.")

        deleted = self.client.delete(f"/trades/{trade['id']}/psychology")
        self.assertEqual(deleted.status_code, 204)
        missing = self.client.get(f"/trades/{trade['id']}/psychology")
        self.assertEqual(missing.status_code, 404)

    def test_score_range_validation(self):
        trade = self.create_trade()

        response = self.client.post(
            f"/trades/{trade['id']}/psychology",
            json=self.psychology_payload(confidence_score=6),
        )

        self.assertEqual(response.status_code, 422)

    def test_one_psychology_entry_per_trade(self):
        trade = self.create_trade()
        first = self.client.post(f"/trades/{trade['id']}/psychology", json=self.psychology_payload())
        duplicate = self.client.post(f"/trades/{trade['id']}/psychology", json=self.psychology_payload(notes="Second"))

        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(duplicate.json()["detail"], "trade already has a psychology entry")

    def test_deleting_psychology_entry_does_not_delete_trade(self):
        trade = self.create_trade(symbol="YM")
        self.client.post(f"/trades/{trade['id']}/psychology", json=self.psychology_payload())

        response = self.client.delete(f"/trades/{trade['id']}/psychology")
        still_exists = self.client.get(f"/trades/{trade['id']}")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(still_exists.status_code, 200)
        self.assertEqual(still_exists.json()["symbol"], "YM")

    def test_psychology_list_splits_trades_with_and_without_entries(self):
        with_entry = self.create_trade(symbol="CL")
        without_entry = self.create_trade(symbol="GC")
        self.client.post(f"/trades/{with_entry['id']}/psychology", json=self.psychology_payload())

        entries = self.client.get("/psychology")
        trades = self.client.get("/trades")

        entry_trade_ids = {entry["trade_id"] for entry in entries.json()}
        self.assertEqual(entries.status_code, 200)
        self.assertIn(with_entry["id"], entry_trade_ids)
        self.assertNotIn(without_entry["id"], entry_trade_ids)
        self.assertIn(without_entry["id"], {trade["id"] for trade in trades.json()})

    def test_no_new_analytics_tables_are_created(self):
        trade = self.create_trade()
        self.client.post(f"/trades/{trade['id']}/psychology", json=self.psychology_payload())

        with sqlite3.connect(self.database_path) as connection:
            tables = [
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
            ]

        self.assertFalse([table for table in tables if "analytics" in table or "summary" in table or "cache" in table])


if __name__ == "__main__":
    unittest.main()
