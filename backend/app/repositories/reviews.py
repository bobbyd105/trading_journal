"""Review persistence helpers for the Phase 3 MVP."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import HTTPException

from app.api.schemas import ReviewPayload
from app.repositories.common import row_to_dict
from app.repositories.trades import hydrate_trade

REVIEW_COLUMNS = """
    id, trade_id, review_status, summary, setup_quality_score, entry_quality_score,
    exit_quality_score, risk_management_score, discipline_score, followed_playbook,
    what_went_well, what_to_improve, lesson_learned, reviewed_at, created_at, updated_at
"""


def review_payload_values(payload: ReviewPayload) -> tuple[Any, ...]:
    return (
        payload.review_status,
        payload.summary,
        payload.setup_quality_score,
        payload.entry_quality_score,
        payload.exit_quality_score,
        payload.risk_management_score,
        payload.discipline_score,
        payload.followed_playbook,
        payload.what_went_well,
        payload.what_to_improve,
        payload.lesson_learned,
        payload.reviewed_at,
    )


def fetch_review(connection: sqlite3.Connection, review_id: int) -> dict[str, Any]:
    review = row_to_dict(
        connection.execute(
            f"SELECT {REVIEW_COLUMNS} FROM trade_reviews WHERE id = ?",
            (review_id,),
        ).fetchone()
    )
    if review is None:
        raise HTTPException(status_code=404, detail="review not found")
    return review


def fetch_review_for_trade(connection: sqlite3.Connection, trade_id: int) -> dict[str, Any]:
    review = row_to_dict(
        connection.execute(
            f"SELECT {REVIEW_COLUMNS} FROM trade_reviews WHERE trade_id = ?",
            (trade_id,),
        ).fetchone()
    )
    if review is None:
        raise HTTPException(status_code=404, detail="review not found")
    return review


def create_review(connection: sqlite3.Connection, trade_id: int, payload: ReviewPayload) -> dict[str, Any]:
    hydrate_trade(connection, trade_id)
    try:
        cursor = connection.execute(
            """
            INSERT INTO trade_reviews (
                trade_id, review_status, summary, setup_quality_score, entry_quality_score,
                exit_quality_score, risk_management_score, discipline_score, followed_playbook,
                what_went_well, what_to_improve, lesson_learned, reviewed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (trade_id, *review_payload_values(payload)),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail="trade already has a review") from exc
    if payload.review_status == "complete":
        mark_trade_reviewed(connection, trade_id)
    return fetch_review(connection, cursor.lastrowid)


def update_review(connection: sqlite3.Connection, review_id: int, payload: ReviewPayload) -> dict[str, Any]:
    current = fetch_review(connection, review_id)
    connection.execute(
        """
        UPDATE trade_reviews
        SET review_status = ?, summary = ?, setup_quality_score = ?, entry_quality_score = ?,
            exit_quality_score = ?, risk_management_score = ?, discipline_score = ?,
            followed_playbook = ?, what_went_well = ?, what_to_improve = ?,
            lesson_learned = ?, reviewed_at = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (*review_payload_values(payload), review_id),
    )
    if payload.review_status == "complete":
        mark_trade_reviewed(connection, current["trade_id"])
    return fetch_review(connection, review_id)


def delete_review(connection: sqlite3.Connection, review_id: int) -> None:
    cursor = connection.execute("DELETE FROM trade_reviews WHERE id = ?", (review_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="review not found")


def mark_trade_reviewed(connection: sqlite3.Connection, trade_id: int) -> None:
    connection.execute(
        """
        UPDATE trades
        SET status = 'reviewed', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (trade_id,),
    )


def list_trades_needing_review(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT trades.id
        FROM trades
        LEFT JOIN trade_reviews ON trade_reviews.trade_id = trades.id
        WHERE trades.status = 'closed'
          AND (trade_reviews.id IS NULL OR trade_reviews.review_status != 'complete')
        ORDER BY trades.closed_at DESC, trades.created_at DESC, trades.id DESC
        """
    ).fetchall()
    return [hydrate_trade(connection, row["id"]) for row in rows]


def list_reviewed_trades(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT trades.id
        FROM trades
        JOIN trade_reviews ON trade_reviews.trade_id = trades.id
        WHERE trade_reviews.review_status = 'complete'
        ORDER BY trade_reviews.reviewed_at DESC, trade_reviews.updated_at DESC, trade_reviews.id DESC
        """
    ).fetchall()
    trades = []
    for row in rows:
        trade = hydrate_trade(connection, row["id"])
        trade["review"] = fetch_review_for_trade(connection, row["id"])
        trades.append(trade)
    return trades
