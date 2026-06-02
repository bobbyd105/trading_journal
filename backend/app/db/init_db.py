"""Initialize the local SQLite database schema."""

from pathlib import Path

from app.config import DEFAULT_DATABASE_PATH
from app.db.connection import get_connection

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

REVIEW_COLUMN_MIGRATIONS = {
    "review_status": "TEXT NOT NULL DEFAULT 'not_started' CHECK (review_status IN ('not_started', 'in_progress', 'complete'))",
    "setup_quality_score": "INTEGER CHECK (setup_quality_score BETWEEN 1 AND 5)",
    "entry_quality_score": "INTEGER CHECK (entry_quality_score BETWEEN 1 AND 5)",
    "exit_quality_score": "INTEGER CHECK (exit_quality_score BETWEEN 1 AND 5)",
    "risk_management_score": "INTEGER CHECK (risk_management_score BETWEEN 1 AND 5)",
    "discipline_score": "INTEGER CHECK (discipline_score BETWEEN 1 AND 5)",
    "followed_playbook": "TEXT NOT NULL DEFAULT 'not_applicable' CHECK (followed_playbook IN ('yes', 'partial', 'no', 'not_applicable'))",
    "lesson_learned": "TEXT",
}

PSYCHOLOGY_COLUMN_MIGRATIONS = {
    "confidence_score": "INTEGER CHECK (confidence_score BETWEEN 1 AND 5)",
    "fear_score": "INTEGER CHECK (fear_score BETWEEN 1 AND 5)",
    "fomo_score": "INTEGER CHECK (fomo_score BETWEEN 1 AND 5)",
    "clarity_score": "INTEGER CHECK (clarity_score BETWEEN 1 AND 5)",
    "updated_at": "TEXT",
}


def migrate_review_columns(connection) -> None:
    """Add Phase 3 review columns to existing local databases."""
    existing_columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(trade_reviews)").fetchall()
    }
    for column_name, column_definition in REVIEW_COLUMN_MIGRATIONS.items():
        if column_name not in existing_columns:
            connection.execute(
                f"ALTER TABLE trade_reviews ADD COLUMN {column_name} {column_definition}"
            )


def migrate_psychology_columns(connection) -> None:
    """Add Psychology V1 columns to existing local databases."""
    existing_columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(psychology_entries)").fetchall()
    }
    for column_name, column_definition in PSYCHOLOGY_COLUMN_MIGRATIONS.items():
        if column_name not in existing_columns:
            connection.execute(
                f"ALTER TABLE psychology_entries ADD COLUMN {column_name} {column_definition}"
            )
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_psychology_entries_trade_id ON psychology_entries(trade_id)"
    )


def initialize_database(database_path: Path = DEFAULT_DATABASE_PATH) -> Path:
    """Apply the schema and return the initialized database path."""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection(database_path) as connection:
        connection.executescript(schema)
        migrate_review_columns(connection)
        migrate_psychology_columns(connection)
    return database_path


if __name__ == "__main__":
    path = initialize_database()
    print(f"Initialized SQLite database at {path}")
