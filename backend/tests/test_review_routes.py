import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


class ReviewRoutesTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.tmpdir.name) / "trading_journal.db"
        app.state.database_path = self.database_path
        self.client = TestClient(app)

    def tearDown(self):
        if hasattr(app.state, "database_path"):
            delattr(app.state, "database_path")
        self.tmpdir.cleanup()

    def create_trade(self, symbol="AAPL", status="closed"):
        response = self.client.post(
            "/trades",
            json={"symbol": symbol, "direction": "long", "status": status},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def review_payload(self, **overrides):
        payload = {
            "review_status": "in_progress",
            "summary": "Followed plan with room for cleaner execution.",
            "setup_quality_score": 4,
            "entry_quality_score": 3,
            "exit_quality_score": 4,
            "risk_management_score": 5,
            "discipline_score": 4,
            "followed_playbook": "partial",
            "what_went_well": "Waited for confirmation.",
            "what_to_improve": "Tighten entry timing.",
            "lesson_learned": "Patience improves the trade location.",
            "reviewed_at": "2026-06-02T10:00:00",
        }
        payload.update(overrides)
        return payload

    def test_review_crud_and_one_review_per_trade(self):
        trade = self.create_trade()
        created = self.client.post(f"/trades/{trade['id']}/review", json=self.review_payload())
        self.assertEqual(created.status_code, 201)
        review = created.json()
        self.assertEqual(review["trade_id"], trade["id"])
        self.assertEqual(review["review_status"], "in_progress")
        self.assertEqual(review["lesson_learned"], "Patience improves the trade location.")

        duplicate = self.client.post(f"/trades/{trade['id']}/review", json=self.review_payload())
        self.assertEqual(duplicate.status_code, 400)

        by_trade = self.client.get(f"/trades/{trade['id']}/review")
        self.assertEqual(by_trade.status_code, 200)
        self.assertEqual(by_trade.json()["id"], review["id"])

        updated = self.client.put(
            f"/reviews/{review['id']}",
            json=self.review_payload(summary="Updated summary", review_status="in_progress"),
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["summary"], "Updated summary")

        deleted = self.client.delete(f"/reviews/{review['id']}")
        self.assertEqual(deleted.status_code, 204)
        missing = self.client.get(f"/reviews/{review['id']}")
        self.assertEqual(missing.status_code, 404)

    def test_review_status_validation(self):
        trade = self.create_trade()
        response = self.client.post(
            f"/trades/{trade['id']}/review",
            json=self.review_payload(review_status="blocked"),
        )
        self.assertEqual(response.status_code, 422)

    def test_score_range_validation(self):
        trade = self.create_trade()
        low_score = self.client.post(
            f"/trades/{trade['id']}/review",
            json=self.review_payload(setup_quality_score=0),
        )
        self.assertEqual(low_score.status_code, 422)

        high_score = self.client.post(
            f"/trades/{trade['id']}/review",
            json=self.review_payload(entry_quality_score=6),
        )
        self.assertEqual(high_score.status_code, 422)

    def test_completed_review_updates_trade_status_and_review_lists(self):
        needs_review_trade = self.create_trade(symbol="NEED")
        reviewed_trade = self.create_trade(symbol="DONE")

        initial_needs_review = self.client.get("/trades/reviews/needs-review")
        self.assertEqual(initial_needs_review.status_code, 200)
        self.assertEqual(
            {trade["id"] for trade in initial_needs_review.json()},
            {needs_review_trade["id"], reviewed_trade["id"]},
        )

        review = self.client.post(
            f"/trades/{reviewed_trade['id']}/review",
            json=self.review_payload(review_status="complete"),
        )
        self.assertEqual(review.status_code, 201)

        refreshed_trade = self.client.get(f"/trades/{reviewed_trade['id']}")
        self.assertEqual(refreshed_trade.status_code, 200)
        self.assertEqual(refreshed_trade.json()["status"], "reviewed")

        needs_review = self.client.get("/trades/reviews/needs-review").json()
        self.assertEqual([trade["id"] for trade in needs_review], [needs_review_trade["id"]])

        reviewed = self.client.get("/trades/reviews/reviewed").json()
        self.assertEqual([trade["id"] for trade in reviewed], [reviewed_trade["id"]])
        self.assertEqual(reviewed[0]["review"]["id"], review.json()["id"])

    def test_changing_completed_review_to_in_progress_returns_trade_to_closed(self):
        trade = self.create_trade()
        review = self.client.post(
            f"/trades/{trade['id']}/review",
            json=self.review_payload(review_status="complete"),
        ).json()
        self.assertEqual(self.client.get(f"/trades/{trade['id']}").json()["status"], "reviewed")

        updated = self.client.put(
            f"/reviews/{review['id']}",
            json=self.review_payload(review_status="in_progress"),
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["review_status"], "in_progress")

        refreshed_trade = self.client.get(f"/trades/{trade['id']}")
        self.assertEqual(refreshed_trade.status_code, 200)
        self.assertEqual(refreshed_trade.json()["status"], "closed")

    def test_delete_completed_review_returns_trade_to_closed_without_deleting_trade(self):
        trade = self.create_trade()
        review = self.client.post(
            f"/trades/{trade['id']}/review",
            json=self.review_payload(review_status="complete"),
        ).json()
        self.assertEqual(self.client.get(f"/trades/{trade['id']}").json()["status"], "reviewed")

        deleted = self.client.delete(f"/reviews/{review['id']}")
        self.assertEqual(deleted.status_code, 204)

        existing_trade = self.client.get(f"/trades/{trade['id']}")
        self.assertEqual(existing_trade.status_code, 200)
        self.assertEqual(existing_trade.json()["id"], trade["id"])
        self.assertEqual(existing_trade.json()["status"], "closed")

    def test_delete_review_does_not_delete_trade(self):
        trade = self.create_trade()
        review = self.client.post(f"/trades/{trade['id']}/review", json=self.review_payload()).json()

        deleted = self.client.delete(f"/reviews/{review['id']}")
        self.assertEqual(deleted.status_code, 204)

        existing_trade = self.client.get(f"/trades/{trade['id']}")
        self.assertEqual(existing_trade.status_code, 200)
        self.assertEqual(existing_trade.json()["id"], trade["id"])
