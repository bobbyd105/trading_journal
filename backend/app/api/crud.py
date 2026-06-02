"""Phase 2 V1-Lite CRUD endpoints for local trade logging."""

from __future__ import annotations

import sqlite3
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.session import open_database

router = APIRouter()

TradeStatus = Literal["draft", "closed", "reviewed", "archived"]
Direction = Literal["long", "short"]
AttachmentType = Literal["before_screenshot", "after_screenshot"]


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


class AttachmentPayload(BaseModel):
    """Metadata-only screenshot attachment payload."""

    model_config = ConfigDict(extra="forbid")

    id: int | None = None
    attachment_type: AttachmentType | None = None
    file_name: str = Field(..., min_length=1)
    file_path: str | None = None
    content_type: str | None = None
    notes: str | None = None


class AttachmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trade_id: int | None = None
    attachment_type: AttachmentType
    file_name: str = Field(..., min_length=1)
    file_path: str | None = None
    content_type: str | None = None
    notes: str | None = None


class AttachmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trade_id: int | None = None
    attachment_type: AttachmentType | None = None
    file_name: str | None = Field(default=None, min_length=1)
    file_path: str | None = None
    content_type: str | None = None
    notes: str | None = None


class PlaybookPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    description: str | None = None
    is_active: bool = True


class TagPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)


class TradePayload(BaseModel):
    """User-entered trade fields; symbol is preserved exactly as submitted."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(..., min_length=1)
    direction: Direction
    entry_price: float | None = None
    exit_price: float | None = None
    quantity: float | None = None
    pnl: float | None = None
    risk: float | None = None
    playbook_id: int | None = None
    status: TradeStatus = "draft"
    tags: list[int] = Field(default_factory=list)
    notes: str | None = None
    before_screenshot: AttachmentPayload | None = None
    after_screenshot: AttachmentPayload | None = None

    @field_validator("tags")
    @classmethod
    def dedupe_tags(cls, value: list[int]) -> list[int]:
        return list(dict.fromkeys(value))


def ensure_playbook_exists(connection: sqlite3.Connection, playbook_id: int | None) -> None:
    if playbook_id is None:
        return
    row = connection.execute("SELECT id FROM playbooks WHERE id = ?", (playbook_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=400, detail="playbook_id does not exist")


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


def sync_trade_tags(connection: sqlite3.Connection, trade_id: int, tag_ids: list[int]) -> None:
    connection.execute("DELETE FROM trade_tags WHERE trade_id = ?", (trade_id,))
    connection.executemany(
        "INSERT INTO trade_tags (trade_id, tag_id) VALUES (?, ?)",
        [(trade_id, tag_id) for tag_id in tag_ids],
    )


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


@router.get("/playbooks")
def list_playbooks(request: Request) -> list[dict[str, Any]]:
    with open_database(request) as connection:
        rows = connection.execute(
            "SELECT * FROM playbooks ORDER BY name"
        ).fetchall()
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
