"""Playbook persistence helpers."""

from __future__ import annotations

import sqlite3

from fastapi import HTTPException


def ensure_playbook_exists(connection: sqlite3.Connection, playbook_id: int | None) -> None:
    if playbook_id is None:
        return
    row = connection.execute("SELECT id FROM playbooks WHERE id = ?", (playbook_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=400, detail="playbook_id does not exist")
