"""Attachment persistence and local file storage helpers."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, Request

from app.api.schemas import AttachmentPayload, AttachmentType
from app.config import DEFAULT_ATTACHMENT_DIR

_SAFE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def validate_attachment_type(payload: AttachmentPayload, expected_type: AttachmentType) -> None:
    if payload.attachment_type is not None and payload.attachment_type != expected_type:
        raise HTTPException(
            status_code=400,
            detail=f"{expected_type} field cannot contain {payload.attachment_type}",
        )


def list_trade_attachments(connection: sqlite3.Connection, trade_id: int) -> list[dict]:
    rows = connection.execute(
        """
        SELECT attachments.*
        FROM attachments
        JOIN trade_attachments ON trade_attachments.attachment_id = attachments.id
        WHERE trade_attachments.trade_id = ?
        ORDER BY attachments.attachment_type, attachments.id
        """,
        (trade_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_trade_attachment_by_type(
    connection: sqlite3.Connection,
    trade_id: int,
    attachment_type: AttachmentType,
) -> dict | None:
    row = connection.execute(
        """
        SELECT attachments.*
        FROM attachments
        JOIN trade_attachments ON trade_attachments.attachment_id = attachments.id
        WHERE trade_attachments.trade_id = ? AND attachments.attachment_type = ?
        """,
        (trade_id, attachment_type),
    ).fetchone()
    return dict(row) if row is not None else None


def upsert_trade_attachment(
    connection: sqlite3.Connection,
    trade_id: int,
    expected_type: AttachmentType,
    payload: AttachmentPayload | None,
) -> int | None:
    """Replace one screenshot slot with metadata only; no binary data is stored in SQLite."""
    existing = get_trade_attachment_by_type(connection, trade_id, expected_type)

    if payload is None:
        if existing is not None:
            connection.execute("DELETE FROM attachments WHERE id = ?", (existing["id"],))
        return None

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
        return int(cursor.lastrowid)

    connection.execute(
        """
        UPDATE attachments
        SET file_name = ?, file_path = ?, content_type = ?, notes = ?
        WHERE id = ?
        """,
        (payload.file_name, payload.file_path, payload.content_type, payload.notes, existing["id"]),
    )
    return int(existing["id"])


def attachment_storage_dir(request: Request) -> Path:
    path = getattr(request.app.state, "attachment_dir", DEFAULT_ATTACHMENT_DIR)
    return Path(path)


def sanitize_file_name(file_name: str) -> str:
    clean_name = Path(file_name).name.strip().replace(" ", "_")
    clean_name = _SAFE_NAME_PATTERN.sub("_", clean_name)
    return clean_name or "attachment"


def store_attachment_file(storage_dir: Path, original_file_name: str, content: bytes) -> Path:
    if not content:
        raise HTTPException(status_code=400, detail="attachment file cannot be empty")
    storage_dir.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_file_name(original_file_name)
    destination = storage_dir / f"{uuid4().hex}_{safe_name}"
    destination.write_bytes(content)
    return destination


def is_app_managed_attachment_path(storage_dir: Path, file_path: str | None) -> bool:
    if not file_path:
        return False
    try:
        Path(file_path).resolve().relative_to(storage_dir.resolve())
    except ValueError:
        return False
    return True


def delete_app_managed_file(storage_dir: Path, file_path: str | None) -> None:
    if not is_app_managed_attachment_path(storage_dir, file_path):
        return
    Path(file_path).unlink(missing_ok=True)
