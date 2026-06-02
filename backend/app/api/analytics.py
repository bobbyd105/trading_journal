"""Read-only analytics API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

from app.db.session import open_database
from app.services.analytics import equity_curve, grouped_performance, performance_summary

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/performance-summary")
def get_performance_summary(
    request: Request,
    start_date: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
) -> dict[str, Any]:
    with open_database(request) as connection:
        return performance_summary(connection, start_date, end_date)


@router.get("/equity-curve")
def get_equity_curve(
    request: Request,
    start_date: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
) -> list[dict[str, Any]]:
    with open_database(request) as connection:
        return equity_curve(connection, start_date, end_date)


@router.get("/grouped-performance")
def get_grouped_performance(
    request: Request,
    start_date: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
) -> dict[str, list[dict[str, Any]]]:
    with open_database(request) as connection:
        return grouped_performance(connection, start_date, end_date)
