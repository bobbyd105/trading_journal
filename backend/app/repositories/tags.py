"""Tag persistence helpers."""

from __future__ import annotations

import sqlite3

from fastapi import HTTPException


def ensure_tags_exist(connection: sqlite3.Connection, tag_ids: list[int]) -> None:
    if not tag_ids:
        return
    placeholders = ",".join("?" for _ in tag_ids)
    rows = connection.execute(
        f"SELECT id FROM tags WHERE id IN ({placeholders})", tag_ids
    ).fetchall()
    found = {row["id"] for row in rows}
    missing = sorted(set(tag_ids) - found)
    if missing:
        raise HTTPException(status_code=400, detail=f"tag ids do not exist: {missing}")


def sync_trade_tags(connection: sqlite3.Connection, trade_id: int, tag_ids: list[int]) -> None:
    connection.execute("DELETE FROM trade_tags WHERE trade_id = ?", (trade_id,))
    connection.executemany(
        "INSERT INTO trade_tags (trade_id, tag_id) VALUES (?, ?)",
        [(trade_id, tag_id) for tag_id in tag_ids],
    )
