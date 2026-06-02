import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.db.init_db import initialize_database


class DatabaseInitializationTest(unittest.TestCase):
    def test_initializes_v1_lite_tables(self):
        expected_tables = {
            "accounts",
            "instruments",
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

    def test_trades_preserve_symbol_with_optional_instrument_reference(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            database_path = Path(tmpdir) / "trading_journal.db"
            initialize_database(database_path)

            with sqlite3.connect(database_path) as connection:
                trade_columns = {
                    row[1]: row
                    for row in connection.execute("PRAGMA table_info(trades)").fetchall()
                }
                trade_foreign_keys = {
                    row[3]: (row[2], row[4], row[6])
                    for row in connection.execute("PRAGMA foreign_key_list(trades)").fetchall()
                }

        self.assertIn("symbol", trade_columns)
        self.assertEqual(trade_columns["symbol"][3], 1)
        self.assertIn("instrument_id", trade_columns)
        self.assertEqual(trade_columns["instrument_id"][3], 0)
        self.assertEqual(
            trade_foreign_keys["instrument_id"],
            ("instruments", "id", "SET NULL"),
        )


if __name__ == "__main__":
    unittest.main()
