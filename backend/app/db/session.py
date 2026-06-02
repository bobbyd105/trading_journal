"""Request-scoped SQLite session helpers."""

from pathlib import Path
import sqlite3

from fastapi import Request

from app.config import DEFAULT_DATABASE_PATH
from app.db.connection import get_connection
from app.db.init_db import initialize_database


def database_path_from_request(request: Request) -> Path:
    """Resolve the SQLite database path, allowing tests to override app state."""
    return Path(getattr(request.app.state, "database_path", DEFAULT_DATABASE_PATH))


def open_database(request: Request) -> sqlite3.Connection:
    """Open an initialized SQLite connection for the current request."""
    database_path = database_path_from_request(request)
    initialize_database(database_path)
    return get_connection(database_path)
