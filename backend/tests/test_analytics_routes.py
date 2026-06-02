import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


class AnalyticsRoutesTest(unittest.TestCase):
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
            "pnl": 0,
            "risk": 100,
        }
        payload.update(overrides)
        response = self.client.post("/trades", json=payload)
        self.assertEqual(response.status_code, 201)
        return response.json()

    def create_playbook(self, name):
        response = self.client.post("/playbooks", json={"name": name})
        self.assertEqual(response.status_code, 201)
        return response.json()

    def create_tag(self, name):
        response = self.client.post("/tags", json={"name": name})
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_analytics_uses_closed_and_reviewed_trades_only(self):
        self.create_trade(symbol="WIN", status="closed", pnl=100)
        reviewed = self.create_trade(symbol="REV", status="closed", pnl=50)
        self.client.post(
            f"/trades/{reviewed['id']}/review",
            json={"review_status": "complete", "followed_playbook": "yes"},
        )
        self.create_trade(symbol="DRAFT", status="draft", pnl=999)
        self.create_trade(symbol="ARCH", status="archived", pnl=999)

        summary = self.client.get("/analytics/performance-summary")

        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.json()["total_trades"], 2)
        self.assertEqual(summary.json()["net_pnl"], 150)

    def test_missing_pnl_and_risk_are_handled_gracefully(self):
        self.create_trade(symbol="NOPNL", pnl=None, risk=None)
        self.create_trade(symbol="NORISK", pnl=120, risk=None)
        self.create_trade(symbol="ZERORISK", pnl=-40, risk=0)

        summary = self.client.get("/analytics/performance-summary").json()
        curve = self.client.get("/analytics/equity-curve").json()

        self.assertEqual(summary["total_trades"], 3)
        self.assertEqual(summary["trades_with_pnl"], 2)
        self.assertEqual(summary["net_pnl"], 80)
        self.assertIsNone(summary["average_r"])
        self.assertEqual(curve[0]["cumulative_pnl"], 0)
        self.assertEqual(curve[-1]["cumulative_pnl"], 80)

    def test_win_loss_breakeven_profit_factor_and_expectancy_are_correct(self):
        self.create_trade(symbol="W1", pnl=100, risk=50)
        self.create_trade(symbol="W2", pnl=50, risk=100)
        self.create_trade(symbol="L1", pnl=-25, risk=50)
        self.create_trade(symbol="BE", pnl=0, risk=50)

        summary = self.client.get("/analytics/performance-summary").json()

        self.assertEqual(summary["win_count"], 2)
        self.assertEqual(summary["loss_count"], 1)
        self.assertEqual(summary["breakeven_count"], 1)
        self.assertEqual(summary["win_rate"], 0.5)
        self.assertEqual(summary["profit_factor"], 6)
        self.assertEqual(summary["expectancy"], 31.25)
        self.assertEqual(summary["average_win"], 75)
        self.assertEqual(summary["average_loss"], -25)
        self.assertEqual(summary["average_r"], 0.625)
        self.assertEqual(summary["best_trade"]["symbol"], "W1")
        self.assertEqual(summary["worst_trade"]["symbol"], "L1")

    def test_grouping_by_playbook_tag_symbol_and_direction(self):
        playbook = self.create_playbook("Opening Range")
        tag = self.create_tag("A+")
        first = self.create_trade(
            symbol="NQ",
            direction="long",
            pnl=100,
            playbook_id=playbook["id"],
            tags=[tag["id"]],
        )
        self.create_trade(symbol="ES", direction="short", pnl=-50)
        self.client.post(
            f"/trades/{first['id']}/review",
            json={"review_status": "complete", "followed_playbook": "yes", "discipline_score": 5},
        )

        grouped = self.client.get("/analytics/grouped-performance").json()

        symbol_groups = {row["group"]: row["metrics"] for row in grouped["by_symbol"]}
        playbook_groups = {row["group"]: row["metrics"] for row in grouped["by_playbook"]}
        direction_groups = {row["group"]: row["metrics"] for row in grouped["by_direction"]}
        tag_groups = {row["group"]: row["metrics"] for row in grouped["by_tag"]}
        followed_groups = {row["group"]: row["metrics"] for row in grouped["by_followed_playbook"]}
        discipline_groups = {row["group"]: row["metrics"] for row in grouped["by_discipline_score_band"]}

        self.assertEqual(symbol_groups["NQ"]["net_pnl"], 100)
        self.assertEqual(playbook_groups["Opening Range"]["total_trades"], 1)
        self.assertEqual(direction_groups["long"]["win_count"], 1)
        self.assertEqual(tag_groups["A+"]["total_trades"], 1)
        self.assertEqual(followed_groups["yes"]["total_trades"], 1)
        self.assertEqual(discipline_groups["4-5"]["total_trades"], 1)

    def test_no_analytics_tables_are_added(self):
        self.client.get("/analytics/performance-summary")
        with sqlite3.connect(self.database_path) as connection:
            tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()]
        self.assertFalse([table for table in tables if "analytics" in table or "summary" in table or "cache" in table])


if __name__ == "__main__":
    unittest.main()
