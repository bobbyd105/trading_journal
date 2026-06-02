"""SQLite connection helpers."""

import sqlite3
from pathlib import Path

from app.config import DEFAULT_DATABASE_PATH


def get_connection(database_path: Path = DEFAULT_DATABASE_PATH) -> sqlite3.Connection:
    """Create a SQLite connection with foreign keys enabled."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
