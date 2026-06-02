"""CRUD endpoints for local trade logging and Phase 3 reviews."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, Request, status
from fastapi.responses import FileResponse

from app.api.schemas import (
    AttachmentCreate,
    AttachmentPayload,
    AttachmentUpdate,
    PlaybookPayload,
    ReviewPayload,
    TagPayload,
    TradePayload,
)
from app.db.session import open_database
from app.repositories.attachments import (
    attachment_storage_dir,
    delete_app_managed_file,
    get_trade_attachment_by_type,
    is_app_managed_attachment_path,
    list_trade_attachments,
    store_attachment_file,
    upsert_trade_attachment,
)
from app.repositories.common import row_to_dict
from app.repositories.playbooks import ensure_playbook_exists
from app.repositories.reviews import (
    create_review as create_trade_review,
    delete_review as delete_trade_review,
    fetch_review,
    fetch_review_for_trade,
    list_reviewed_trades,
    list_trades_needing_review,
    update_review as update_trade_review,
)
from app.repositories.tags import ensure_tags_exist, sync_trade_tags
from app.repositories.trades import hydrate_trade

router = APIRouter()


@router.get("/playbooks")
def list_playbooks(request: Request) -> list[dict[str, Any]]:
    with open_database(request) as connection:
        rows = connection.execute("SELECT * FROM playbooks ORDER BY name").fetchall()
        return [dict(row) for row in rows]


@router.get("/playbooks/{playbook_id}")
def get_playbook(playbook_id: int, request: Request) -> dict[str, Any]:
    with open_database(request) as connection:
        playbook = row_to_dict(connection.execute("SELECT * FROM playbooks WHERE id = ?", (playbook_id,)).fetchone())
        if playbook is None:
            raise HTTPException(status_code=404, detail="playbook not found")
        return playbook


@router.post("/playbooks", status_code=status.HTTP_201_CREATED)
def create_playbook(payload: PlaybookPayload, request: Request) -> dict[str, Any]:
    with open_database(request) as connection:
        try:
            cursor = connection.execute(
                """
                INSERT INTO playbooks (name, description, is_active)
                VALUES (?, ?, ?)
                """,
                (payload.name, payload.description, int(payload.is_active)),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=400, detail="playbook name must be unique") from exc
        return row_to_dict(connection.execute("SELECT * FROM playbooks WHERE id = ?", (cursor.lastrowid,)).fetchone())


@router.put("/playbooks/{playbook_id}")
def update_playbook(playbook_id: int, payload: PlaybookPayload, request: Request) -> dict[str, Any]:
    with open_database(request) as connection:
        try:
            cursor = connection.execute(
                """
                UPDATE playbooks
                SET name = ?, description = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (payload.name, payload.description, int(payload.is_active), playbook_id),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=400, detail="playbook name must be unique") from exc
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="playbook not found")
        return row_to_dict(connection.execute("SELECT * FROM playbooks WHERE id = ?", (playbook_id,)).fetchone())


@router.delete("/playbooks/{playbook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_playbook(playbook_id: int, request: Request) -> None:
    with open_database(request) as connection:
        cursor = connection.execute("DELETE FROM playbooks WHERE id = ?", (playbook_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="playbook not found")


@router.get("/tags")
def list_tags(request: Request) -> list[dict[str, Any]]:
    with open_database(request) as connection:
        rows = connection.execute("SELECT * FROM tags ORDER BY name").fetchall()
        return [dict(row) for row in rows]


@router.get("/tags/{tag_id}")
def get_tag(tag_id: int, request: Request) -> dict[str, Any]:
    with open_database(request) as connection:
        tag = row_to_dict(connection.execute("SELECT * FROM tags WHERE id = ?", (tag_id,)).fetchone())
        if tag is None:
            raise HTTPException(status_code=404, detail="tag not found")
        return tag


@router.post("/tags", status_code=status.HTTP_201_CREATED)
def create_tag(payload: TagPayload, request: Request) -> dict[str, Any]:
    with open_database(request) as connection:
        try:
            cursor = connection.execute("INSERT INTO tags (name) VALUES (?)", (payload.name,))
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=400, detail="tag name must be unique") from exc
        return row_to_dict(connection.execute("SELECT * FROM tags WHERE id = ?", (cursor.lastrowid,)).fetchone())


@router.put("/tags/{tag_id}")
def update_tag(tag_id: int, payload: TagPayload, request: Request) -> dict[str, Any]:
    with open_database(request) as connection:
        try:
            cursor = connection.execute("UPDATE tags SET name = ? WHERE id = ?", (payload.name, tag_id))
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=400, detail="tag name must be unique") from exc
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="tag not found")
        return row_to_dict(connection.execute("SELECT * FROM tags WHERE id = ?", (tag_id,)).fetchone())


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: int, request: Request) -> None:
    with open_database(request) as connection:
        cursor = connection.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="tag not found")


@router.get("/trades")
def list_trades(request: Request) -> list[dict[str, Any]]:
    with open_database(request) as connection:
        rows = connection.execute("SELECT id FROM trades ORDER BY created_at DESC, id DESC").fetchall()
        return [hydrate_trade(connection, row["id"]) for row in rows]


@router.post("/trades", status_code=status.HTTP_201_CREATED)
def create_trade(payload: TradePayload, request: Request) -> dict[str, Any]:
    with open_database(request) as connection:
        ensure_playbook_exists(connection, payload.playbook_id)
        ensure_tags_exist(connection, payload.tags)
        cursor = connection.execute(
            """
            INSERT INTO trades (
                symbol, direction, entry_price, exit_price, quantity, pnl, risk,
                playbook_id, status, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.symbol,
                payload.direction,
                payload.entry_price,
                payload.exit_price,
                payload.quantity,
                payload.pnl,
                payload.risk,
                payload.playbook_id,
                payload.status,
                payload.notes,
            ),
        )
        trade_id = cursor.lastrowid
        sync_trade_tags(connection, trade_id, payload.tags)
        upsert_trade_attachment(connection, trade_id, "before_screenshot", payload.before_screenshot)
        upsert_trade_attachment(connection, trade_id, "after_screenshot", payload.after_screenshot)
        return hydrate_trade(connection, trade_id)


@router.get("/trades/reviews/needs-review")
def get_trades_needing_review(request: Request) -> list[dict[str, Any]]:
    with open_database(request) as connection:
        return list_trades_needing_review(connection)


@router.get("/trades/reviews/reviewed")
def get_reviewed_trades(request: Request) -> list[dict[str, Any]]:
    with open_database(request) as connection:
        return list_reviewed_trades(connection)


@router.get("/trades/{trade_id}")
def get_trade(trade_id: int, request: Request) -> dict[str, Any]:
    with open_database(request) as connection:
        return hydrate_trade(connection, trade_id)


@router.put("/trades/{trade_id}")
def update_trade(trade_id: int, payload: TradePayload, request: Request) -> dict[str, Any]:
    with open_database(request) as connection:
        hydrate_trade(connection, trade_id)
        ensure_playbook_exists(connection, payload.playbook_id)
        ensure_tags_exist(connection, payload.tags)
        connection.execute(
            """
            UPDATE trades
            SET symbol = ?, direction = ?, entry_price = ?, exit_price = ?, quantity = ?,
                pnl = ?, risk = ?, playbook_id = ?, status = ?, notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                payload.symbol,
                payload.direction,
                payload.entry_price,
                payload.exit_price,
                payload.quantity,
                payload.pnl,
                payload.risk,
                payload.playbook_id,
                payload.status,
                payload.notes,
                trade_id,
            ),
        )
        sync_trade_tags(connection, trade_id, payload.tags)
        upsert_trade_attachment(connection, trade_id, "before_screenshot", payload.before_screenshot)
        upsert_trade_attachment(connection, trade_id, "after_screenshot", payload.after_screenshot)
        return hydrate_trade(connection, trade_id)


@router.delete("/trades/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trade(trade_id: int, request: Request) -> None:
    with open_database(request) as connection:
        cursor = connection.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="trade not found")


@router.get("/trades/{trade_id}/attachments")
def get_trade_attachments(trade_id: int, request: Request) -> list[dict[str, Any]]:
    with open_database(request) as connection:
        hydrate_trade(connection, trade_id)
        return list_trade_attachments(connection, trade_id)


@router.put("/trades/{trade_id}/attachments/{attachment_type}/file")
def upload_trade_attachment_file(
    trade_id: int,
    attachment_type: str,
    request: Request,
    file_name: str = Query(..., min_length=1),
    content_type: str | None = Query(default=None),
    notes: str | None = Query(default=None),
    content: bytes = Body(..., media_type="application/octet-stream"),
) -> dict[str, Any]:
    if attachment_type not in {"before_screenshot", "after_screenshot"}:
        raise HTTPException(status_code=422, detail="unsupported attachment type")

    with open_database(request) as connection:
        hydrate_trade(connection, trade_id)
        storage_dir = attachment_storage_dir(request)
        existing = get_trade_attachment_by_type(connection, trade_id, attachment_type)
        stored_path = store_attachment_file(storage_dir, file_name, content)
        payload = AttachmentPayload(
            attachment_type=attachment_type,
            file_name=file_name,
            file_path=str(stored_path),
            content_type=content_type,
            notes=notes,
        )
        attachment_id = upsert_trade_attachment(connection, trade_id, attachment_type, payload)
        delete_app_managed_file(storage_dir, existing["file_path"] if existing else None)
        return row_to_dict(connection.execute("SELECT * FROM attachments WHERE id = ?", (attachment_id,)).fetchone())


@router.get("/trades/{trade_id}/review")
def get_review_for_trade(trade_id: int, request: Request) -> dict[str, Any]:
    with open_database(request) as connection:
        hydrate_trade(connection, trade_id)
        return fetch_review_for_trade(connection, trade_id)


@router.post("/trades/{trade_id}/review", status_code=status.HTTP_201_CREATED)
def create_review(trade_id: int, payload: ReviewPayload, request: Request) -> dict[str, Any]:
    with open_database(request) as connection:
        return create_trade_review(connection, trade_id, payload)


@router.get("/reviews/{review_id}")
def get_review(review_id: int, request: Request) -> dict[str, Any]:
    with open_database(request) as connection:
        return fetch_review(connection, review_id)


@router.put("/reviews/{review_id}")
def update_review(review_id: int, payload: ReviewPayload, request: Request) -> dict[str, Any]:
    with open_database(request) as connection:
        return update_trade_review(connection, review_id, payload)


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(review_id: int, request: Request) -> None:
    with open_database(request) as connection:
        delete_trade_review(connection, review_id)


@router.get("/attachments")
def list_attachments(request: Request) -> list[dict[str, Any]]:
    with open_database(request) as connection:
        rows = connection.execute(
            """
            SELECT attachments.*, trade_attachments.trade_id
            FROM attachments
            LEFT JOIN trade_attachments ON trade_attachments.attachment_id = attachments.id
            ORDER BY attachments.created_at DESC, attachments.id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]


@router.get("/attachments/{attachment_id}/file")
def get_attachment_file(attachment_id: int, request: Request) -> FileResponse:
    with open_database(request) as connection:
        attachment = row_to_dict(connection.execute("SELECT * FROM attachments WHERE id = ?", (attachment_id,)).fetchone())
        if attachment is None:
            raise HTTPException(status_code=404, detail="attachment not found")
        storage_dir = attachment_storage_dir(request)
        attachment_path = attachment.get("file_path")
        if (
            not attachment_path
            or not is_app_managed_attachment_path(storage_dir, attachment_path)
            or not Path(attachment_path).exists()
        ):
            raise HTTPException(status_code=404, detail="attachment file not found")
        return FileResponse(
            attachment["file_path"],
            media_type=attachment.get("content_type") or "application/octet-stream",
            filename=attachment.get("file_name") or None,
        )


@router.get("/attachments/{attachment_id}")
def get_attachment(attachment_id: int, request: Request) -> dict[str, Any]:
    with open_database(request) as connection:
        attachment = row_to_dict(connection.execute("SELECT * FROM attachments WHERE id = ?", (attachment_id,)).fetchone())
        if attachment is None:
            raise HTTPException(status_code=404, detail="attachment not found")
        return attachment


@router.post("/attachments", status_code=status.HTTP_201_CREATED)
def create_attachment(payload: AttachmentCreate, request: Request) -> dict[str, Any]:
    with open_database(request) as connection:
        if payload.trade_id is not None:
            hydrate_trade(connection, payload.trade_id)
        cursor = connection.execute(
            """
            INSERT INTO attachments (attachment_type, file_name, file_path, content_type, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (payload.attachment_type, payload.file_name, payload.file_path, payload.content_type, payload.notes),
        )
        if payload.trade_id is not None:
            connection.execute(
                "INSERT INTO trade_attachments (trade_id, attachment_id) VALUES (?, ?)",
                (payload.trade_id, cursor.lastrowid),
            )
        return row_to_dict(connection.execute("SELECT * FROM attachments WHERE id = ?", (cursor.lastrowid,)).fetchone())


@router.put("/attachments/{attachment_id}")
def update_attachment(attachment_id: int, payload: AttachmentUpdate, request: Request) -> dict[str, Any]:
    with open_database(request) as connection:
        current = row_to_dict(connection.execute("SELECT * FROM attachments WHERE id = ?", (attachment_id,)).fetchone())
        if current is None:
            raise HTTPException(status_code=404, detail="attachment not found")
        if payload.trade_id is not None:
            hydrate_trade(connection, payload.trade_id)
        connection.execute(
            """
            UPDATE attachments
            SET attachment_type = ?, file_name = ?, file_path = ?, content_type = ?, notes = ?
            WHERE id = ?
            """,
            (
                payload.attachment_type or current["attachment_type"],
                payload.file_name if payload.file_name is not None else current["file_name"],
                payload.file_path if payload.file_path is not None else current["file_path"],
                payload.content_type if payload.content_type is not None else current["content_type"],
                payload.notes if payload.notes is not None else current["notes"],
                attachment_id,
            ),
        )
        if payload.trade_id is not None:
            connection.execute("DELETE FROM trade_attachments WHERE attachment_id = ?", (attachment_id,))
            connection.execute(
                "INSERT INTO trade_attachments (trade_id, attachment_id) VALUES (?, ?)",
                (payload.trade_id, attachment_id),
            )
        return row_to_dict(connection.execute("SELECT * FROM attachments WHERE id = ?", (attachment_id,)).fetchone())


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(attachment_id: int, request: Request) -> None:
    with open_database(request) as connection:
        cursor = connection.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="attachment not found")
