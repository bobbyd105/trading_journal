import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.db.init_db import initialize_database


class DatabaseInitializationTest(unittest.TestCase):
    def test_initializes_v1_lite_tables(self):
        expected_tables = {
            "accounts",
            "playbooks",
            "trades",
            "tags",
            "trade_tags",
            "attachments",
            "trade_attachments",
            "psychology_entries",
            "trade_reviews",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            database_path = Path(tmpdir) / "trading_journal.db"
            initialize_database(database_path)

            with sqlite3.connect(database_path) as connection:
                rows = connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                    """
                ).fetchall()

        self.assertEqual({row[0] for row in rows}, expected_tables)


if __name__ == "__main__":
    unittest.main()
