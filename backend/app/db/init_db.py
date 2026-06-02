"""Initialize the local SQLite database schema."""

from pathlib import Path

from app.config import DEFAULT_DATABASE_PATH
from app.db.connection import get_connection

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def initialize_database(database_path: Path = DEFAULT_DATABASE_PATH) -> Path:
    """Apply the Phase 1 schema and return the initialized database path."""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection(database_path) as connection:
        connection.executescript(schema)
    return database_path


if __name__ == "__main__":
    path = initialize_database()
    print(f"Initialized SQLite database at {path}")
