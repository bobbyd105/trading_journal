"""Trade persistence helpers."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import HTTPException

from app.repositories.common import row_to_dict


def hydrate_trade(connection: sqlite3.Connection, trade_id: int) -> dict[str, Any]:
    trade = row_to_dict(
        connection.execute(
            """
            SELECT trades.*, playbooks.name AS playbook_name
            FROM trades
            LEFT JOIN playbooks ON playbooks.id = trades.playbook_id
            WHERE trades.id = ?
            """,
            (trade_id,),
        ).fetchone()
    )
    if trade is None:
        raise HTTPException(status_code=404, detail="trade not found")

    tag_rows = connection.execute(
        """
        SELECT tags.id, tags.name
        FROM tags
        JOIN trade_tags ON trade_tags.tag_id = tags.id
        WHERE trade_tags.trade_id = ?
        ORDER BY tags.name
        """,
        (trade_id,),
    ).fetchall()
    trade["tags"] = [dict(row) for row in tag_rows]

    attachments = connection.execute(
        """
        SELECT attachments.*
        FROM attachments
        JOIN trade_attachments ON trade_attachments.attachment_id = attachments.id
        WHERE trade_attachments.trade_id = ?
        ORDER BY attachments.id
        """,
        (trade_id,),
    ).fetchall()
    trade["before_screenshot"] = None
    trade["after_screenshot"] = None
    for row in attachments:
        attachment = dict(row)
        trade[attachment["attachment_type"]] = attachment

    return trade
