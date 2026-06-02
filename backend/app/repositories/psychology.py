"""Psychology entry persistence helpers."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import HTTPException, status

from app.api.schemas import PsychologyPayload
from app.repositories.common import row_to_dict
from app.repositories.trades import hydrate_trade

PSYCHOLOGY_FIELDS = (
    "confidence_score",
    "fear_score",
    "fomo_score",
    "discipline_score",
    "clarity_score",
    "notes",
)


def fetch_psychology_for_trade(connection: sqlite3.Connection, trade_id: int) -> dict[str, Any]:
    """Return the single psychology entry for a trade."""
    hydrate_trade(connection, trade_id)
    entry = row_to_dict(
        connection.execute(
            "SELECT * FROM psychology_entries WHERE trade_id = ?",
            (trade_id,),
        ).fetchone()
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="psychology entry not found")
    return entry


def list_psychology_entries(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """List psychology entries with minimal trade context for simple UI grouping."""
    rows = connection.execute(
        """
        SELECT
            psychology_entries.*,
            trades.symbol AS trade_symbol,
            trades.direction AS trade_direction,
            trades.status AS trade_status,
            trades.pnl AS trade_pnl
        FROM psychology_entries
        JOIN trades ON trades.id = psychology_entries.trade_id
        ORDER BY psychology_entries.created_at DESC, psychology_entries.id DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def create_psychology_entry(
    connection: sqlite3.Connection,
    trade_id: int,
    payload: PsychologyPayload,
) -> dict[str, Any]:
    """Create one psychology entry for a trade."""
    hydrate_trade(connection, trade_id)
    try:
        cursor = connection.execute(
            """
            INSERT INTO psychology_entries (
                trade_id, confidence_score, fear_score, fomo_score,
                discipline_score, clarity_score, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade_id,
                payload.confidence_score,
                payload.fear_score,
                payload.fomo_score,
                payload.discipline_score,
                payload.clarity_score,
                payload.notes,
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="trade already has a psychology entry",
        ) from exc
    return row_to_dict(connection.execute("SELECT * FROM psychology_entries WHERE id = ?", (cursor.lastrowid,)).fetchone())


def update_psychology_entry(
    connection: sqlite3.Connection,
    trade_id: int,
    payload: PsychologyPayload,
) -> dict[str, Any]:
    """Update the single psychology entry for a trade."""
    fetch_psychology_for_trade(connection, trade_id)
    connection.execute(
        """
        UPDATE psychology_entries
        SET confidence_score = ?, fear_score = ?, fomo_score = ?, discipline_score = ?,
            clarity_score = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE trade_id = ?
        """,
        (
            payload.confidence_score,
            payload.fear_score,
            payload.fomo_score,
            payload.discipline_score,
            payload.clarity_score,
            payload.notes,
            trade_id,
        ),
    )
    return fetch_psychology_for_trade(connection, trade_id)


def delete_psychology_entry(connection: sqlite3.Connection, trade_id: int) -> None:
    """Delete a psychology entry without deleting the linked trade."""
    hydrate_trade(connection, trade_id)
    cursor = connection.execute("DELETE FROM psychology_entries WHERE trade_id = ?", (trade_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="psychology entry not found")
