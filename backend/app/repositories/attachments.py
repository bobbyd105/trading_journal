"""Attachment persistence helpers."""

from __future__ import annotations

import sqlite3

from fastapi import HTTPException

from app.api.schemas import AttachmentPayload, AttachmentType


def validate_attachment_type(payload: AttachmentPayload, expected_type: AttachmentType) -> None:
    if payload.attachment_type is not None and payload.attachment_type != expected_type:
        raise HTTPException(
            status_code=400,
            detail=f"{expected_type} field cannot contain {payload.attachment_type}",
        )


def upsert_trade_attachment(
    connection: sqlite3.Connection,
    trade_id: int,
    expected_type: AttachmentType,
    payload: AttachmentPayload | None,
) -> None:
    """Replace one screenshot slot with metadata only; no binary upload is handled."""
    existing = connection.execute(
        """
        SELECT attachments.id
        FROM attachments
        JOIN trade_attachments ON trade_attachments.attachment_id = attachments.id
        WHERE trade_attachments.trade_id = ? AND attachments.attachment_type = ?
        """,
        (trade_id, expected_type),
    ).fetchone()

    if payload is None:
        if existing is not None:
            connection.execute("DELETE FROM attachments WHERE id = ?", (existing["id"],))
        return

    validate_attachment_type(payload, expected_type)
    if existing is None:
        cursor = connection.execute(
            """
            INSERT INTO attachments (attachment_type, file_name, file_path, content_type, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (expected_type, payload.file_name, payload.file_path, payload.content_type, payload.notes),
        )
        connection.execute(
            "INSERT INTO trade_attachments (trade_id, attachment_id) VALUES (?, ?)",
            (trade_id, cursor.lastrowid),
        )
        return

    connection.execute(
        """
        UPDATE attachments
        SET file_name = ?, file_path = ?, content_type = ?, notes = ?
        WHERE id = ?
        """,
        (payload.file_name, payload.file_path, payload.content_type, payload.notes, existing["id"]),
    )
