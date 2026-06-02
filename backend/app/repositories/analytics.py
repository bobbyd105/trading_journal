"""Read-only analytics queries derived from canonical trade data."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.common import row_to_dict

ELIGIBLE_STATUSES = ("closed", "reviewed")


def _date_clause(start_date: str | None, end_date: str | None) -> tuple[str, list[str]]:
    clauses: list[str] = ["trades.status IN ('closed', 'reviewed')"]
    params: list[str] = []
    if start_date:
        clauses.append("date(trades.closed_at) >= date(?)")
        params.append(start_date)
    if end_date:
        clauses.append("date(trades.closed_at) <= date(?)")
        params.append(end_date)
    return " AND ".join(clauses), params


def list_analytics_trades(
    connection: sqlite3.Connection,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """Return closed/reviewed trade rows with review and playbook context."""
    where_sql, params = _date_clause(start_date, end_date)
    rows = connection.execute(
        f"""
        SELECT
            trades.id,
            trades.symbol,
            trades.direction,
            trades.status,
            trades.pnl,
            trades.risk,
            trades.playbook_id,
            playbooks.name AS playbook_name,
            trades.closed_at,
            trades.created_at,
            trade_reviews.followed_playbook,
            trade_reviews.discipline_score
        FROM trades
        LEFT JOIN playbooks ON playbooks.id = trades.playbook_id
        LEFT JOIN trade_reviews ON trade_reviews.trade_id = trades.id
        WHERE {where_sql}
        ORDER BY COALESCE(trades.closed_at, trades.created_at), trades.id
        """,
        params,
    ).fetchall()
    return [dict(row) for row in rows]


def list_trade_tags(connection: sqlite3.Connection, trade_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    """Return tags keyed by trade ID for the supplied trades."""
    if not trade_ids:
        return {}
    placeholders = ",".join("?" for _ in trade_ids)
    rows = connection.execute(
        f"""
        SELECT trade_tags.trade_id, tags.id, tags.name
        FROM trade_tags
        JOIN tags ON tags.id = trade_tags.tag_id
        WHERE trade_tags.trade_id IN ({placeholders})
        ORDER BY tags.name
        """,
        trade_ids,
    ).fetchall()
    tags_by_trade: dict[int, list[dict[str, Any]]] = {trade_id: [] for trade_id in trade_ids}
    for row in rows:
        tags_by_trade[row["trade_id"]].append({"id": row["id"], "name": row["name"]})
    return tags_by_trade


def database_table_names(connection: sqlite3.Connection) -> list[str]:
    """Return SQLite table names for schema safety tests."""
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name").fetchall()
    return [row["name"] for row in rows]
