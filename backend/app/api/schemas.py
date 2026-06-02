"""Pydantic payload schemas for CRUD endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TradeStatus = Literal["draft", "closed", "reviewed", "archived"]
Direction = Literal["long", "short"]
AttachmentType = Literal["before_screenshot", "after_screenshot"]
ReviewStatus = Literal["not_started", "in_progress", "complete"]
FollowedPlaybook = Literal["yes", "partial", "no", "not_applicable"]


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


class ReviewPayload(BaseModel):
    """Trade review fields for the Phase 3 MVP."""

    model_config = ConfigDict(extra="forbid")

    review_status: ReviewStatus = "not_started"
    summary: str | None = None
    setup_quality_score: int | None = Field(default=None, ge=1, le=5)
    entry_quality_score: int | None = Field(default=None, ge=1, le=5)
    exit_quality_score: int | None = Field(default=None, ge=1, le=5)
    risk_management_score: int | None = Field(default=None, ge=1, le=5)
    discipline_score: int | None = Field(default=None, ge=1, le=5)
    followed_playbook: FollowedPlaybook = "not_applicable"
    what_went_well: str | None = None
    what_to_improve: str | None = None
    lesson_learned: str | None = None
    reviewed_at: str | None = None
