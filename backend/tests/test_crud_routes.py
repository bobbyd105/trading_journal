import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


class CrudRoutesTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.tmpdir.name) / "trading_journal.db"
        app.state.database_path = self.database_path
        self.client = TestClient(app)

    def tearDown(self):
        if hasattr(app.state, "database_path"):
            delattr(app.state, "database_path")
        self.tmpdir.cleanup()

    def test_playbook_tag_trade_crud_preserves_entered_values(self):
        playbook = self.client.post(
            "/playbooks",
            json={"name": "Opening range", "description": "ORB setup", "is_active": True},
        )
        self.assertEqual(playbook.status_code, 201)
        playbook_id = playbook.json()["id"]
        self.assertEqual(self.client.get(f"/playbooks/{playbook_id}").json()["name"], "Opening range")

        tag = self.client.post("/tags", json={"name": "A+"})
        self.assertEqual(tag.status_code, 201)
        tag_id = tag.json()["id"]
        self.assertEqual(self.client.get(f"/tags/{tag_id}").json()["name"], "A+")

        trade_payload = {
            "symbol": " es  Jun26 ",
            "direction": "long",
            "entry_price": 5312.25,
            "exit_price": 5321.0,
            "quantity": 2,
            "pnl": 437.5,
            "risk": 125.0,
            "playbook_id": playbook_id,
            "status": "closed",
            "tags": [tag_id],
            "notes": "Kept the exact user-entered symbol spacing.",
            "before_screenshot": {
                "file_name": "before.png",
                "file_path": "/screens/before.png",
                "content_type": "image/png",
                "notes": "premarket plan",
            },
            "after_screenshot": {
                "file_name": "after.png",
                "file_path": "/screens/after.png",
                "content_type": "image/png",
                "notes": "exit review",
            },
        }
        created = self.client.post("/trades", json=trade_payload)
        self.assertEqual(created.status_code, 201)
        created_trade = created.json()
        self.assertEqual(created_trade["symbol"], " es  Jun26 ")
        self.assertEqual(created_trade["instrument_id"], None)
        self.assertEqual(created_trade["status"], "closed")
        self.assertEqual(created_trade["tags"], [{"id": tag_id, "name": "A+"}])
        self.assertEqual(created_trade["before_screenshot"]["file_name"], "before.png")
        self.assertEqual(created_trade["after_screenshot"]["file_name"], "after.png")

        trade_id = created_trade["id"]
        updated_payload = {
            **trade_payload,
            "symbol": "NQ-Micro.Custom",
            "direction": "short",
            "status": "reviewed",
            "tags": [],
            "before_screenshot": None,
            "after_screenshot": {
                "file_name": "after-edited.png",
                "content_type": "image/png",
            },
        }
        updated = self.client.put(f"/trades/{trade_id}", json=updated_payload)
        self.assertEqual(updated.status_code, 200)
        updated_trade = updated.json()
        self.assertEqual(updated_trade["symbol"], "NQ-Micro.Custom")
        self.assertEqual(updated_trade["direction"], "short")
        self.assertEqual(updated_trade["status"], "reviewed")
        self.assertEqual(updated_trade["tags"], [])
        self.assertIsNone(updated_trade["before_screenshot"])
        self.assertEqual(updated_trade["after_screenshot"]["file_name"], "after-edited.png")

        listed = self.client.get("/trades")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()), 1)

        deleted = self.client.delete(f"/trades/{trade_id}")
        self.assertEqual(deleted.status_code, 204)
        missing = self.client.get(f"/trades/{trade_id}")
        self.assertEqual(missing.status_code, 404)

    def test_attachment_metadata_crud(self):
        trade = self.client.post(
            "/trades",
            json={"symbol": "AAPL", "direction": "long", "status": "draft"},
        ).json()

        attachment = self.client.post(
            "/attachments",
            json={
                "trade_id": trade["id"],
                "attachment_type": "before_screenshot",
                "file_name": "setup.jpg",
                "file_path": "/local/setup.jpg",
                "content_type": "image/jpeg",
            },
        )
        self.assertEqual(attachment.status_code, 201)
        attachment_id = attachment.json()["id"]
        self.assertEqual(self.client.get(f"/attachments/{attachment_id}").json()["file_name"], "setup.jpg")

        listed = self.client.get("/attachments")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()[0]["trade_id"], trade["id"])

        updated = self.client.put(
            f"/attachments/{attachment_id}",
            json={"attachment_type": "after_screenshot", "file_name": "result.jpg"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["attachment_type"], "after_screenshot")
        self.assertEqual(updated.json()["file_name"], "result.jpg")

        deleted = self.client.delete(f"/attachments/{attachment_id}")
        self.assertEqual(deleted.status_code, 204)

    def test_rejects_unsupported_trade_status_and_missing_relationships(self):
        bad_status = self.client.post(
            "/trades",
            json={"symbol": "MSFT", "direction": "long", "status": "open"},
        )
        self.assertEqual(bad_status.status_code, 422)

        missing_playbook = self.client.post(
            "/trades",
            json={"symbol": "MSFT", "direction": "long", "playbook_id": 999},
        )
        self.assertEqual(missing_playbook.status_code, 400)

        missing_tag = self.client.post(
            "/trades",
            json={"symbol": "MSFT", "direction": "long", "tags": [999]},
        )
        self.assertEqual(missing_tag.status_code, 400)

    def test_schema_integrity_for_statuses_and_cascading_metadata(self):
        playbook = self.client.post("/playbooks", json={"name": "Breakout"}).json()
        tag = self.client.post("/tags", json={"name": "momentum"}).json()
        trade = self.client.post(
            "/trades",
            json={
                "symbol": "TSLA",
                "direction": "short",
                "playbook_id": playbook["id"],
                "tags": [tag["id"]],
                "before_screenshot": {"file_name": "before.png"},
            },
        ).json()

        with sqlite3.connect(self.database_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            invalid_status = None
            try:
                connection.execute(
                    "INSERT INTO trades (symbol, direction, status) VALUES (?, ?, ?)",
                    ("TSLA", "short", "open"),
                )
            except sqlite3.IntegrityError as exc:
                invalid_status = exc
            self.assertIsNotNone(invalid_status)

            connection.execute("DELETE FROM trades WHERE id = ?", (trade["id"],))
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM trade_tags WHERE trade_id = ?", (trade["id"],)).fetchone()[0],
                0,
            )
            self.assertEqual(
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM attachments
                    JOIN trade_attachments ON trade_attachments.attachment_id = attachments.id
                    WHERE trade_attachments.trade_id = ?
                    """,
                    (trade["id"],),
                ).fetchone()[0],
                0,
            )


if __name__ == "__main__":
    unittest.main()
