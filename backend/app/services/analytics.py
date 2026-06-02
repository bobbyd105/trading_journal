"""Analytics calculations derived from canonical trade, review, tag, and playbook data."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import Any

from app.repositories.analytics import list_analytics_trades, list_trade_tags

MetricValue = int | float | None


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 6)


def _pnl_values(trades: list[dict[str, Any]]) -> list[float]:
    return [float(trade["pnl"]) for trade in trades if trade.get("pnl") is not None]


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _counts(pnls: list[float]) -> dict[str, int]:
    return {
        "win_count": sum(1 for pnl in pnls if pnl > 0),
        "loss_count": sum(1 for pnl in pnls if pnl < 0),
        "breakeven_count": sum(1 for pnl in pnls if pnl == 0),
    }


def _trade_snapshot(trade: dict[str, Any] | None) -> dict[str, Any] | None:
    if trade is None:
        return None
    return {
        "id": trade["id"],
        "symbol": trade["symbol"],
        "direction": trade["direction"],
        "pnl": trade["pnl"],
        "risk": trade["risk"],
        "closed_at": trade["closed_at"],
    }


def calculate_summary(trades: list[dict[str, Any]]) -> dict[str, MetricValue | dict[str, Any]]:
    """Calculate summary metrics without mutating or persisting analytics data."""
    pnls = _pnl_values(trades)
    wins = [pnl for pnl in pnls if pnl > 0]
    losses = [pnl for pnl in pnls if pnl < 0]
    gross_profit = sum(wins)
    gross_loss = sum(losses)
    r_values = [
        float(trade["pnl"]) / float(trade["risk"])
        for trade in trades
        if trade.get("pnl") is not None and trade.get("risk") not in (None, 0)
    ]
    best_trade = max(
        (trade for trade in trades if trade.get("pnl") is not None),
        key=lambda trade: trade["pnl"],
        default=None,
    )
    worst_trade = min(
        (trade for trade in trades if trade.get("pnl") is not None),
        key=lambda trade: trade["pnl"],
        default=None,
    )
    counts = _counts(pnls)

    return {
        "total_trades": len(trades),
        "trades_with_pnl": len(pnls),
        **counts,
        "net_pnl": _round(sum(pnls)),
        "gross_pnl": _round(sum(abs(pnl) for pnl in pnls)) if pnls else None,
        "win_rate": _round(counts["win_count"] / len(pnls)) if pnls else None,
        "average_win": _round(_average(wins)),
        "average_loss": _round(_average(losses)),
        "profit_factor": _round(gross_profit / abs(gross_loss)) if gross_loss < 0 else None,
        "expectancy": _round(_average(pnls)),
        "average_r": _round(_average(r_values)),
        "best_trade": _trade_snapshot(best_trade),
        "worst_trade": _trade_snapshot(worst_trade),
    }


def performance_summary(
    connection: sqlite3.Connection,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    return calculate_summary(list_analytics_trades(connection, start_date, end_date))


def equity_curve(
    connection: sqlite3.Connection,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    trades = list_analytics_trades(connection, start_date, end_date)
    cumulative_pnl = 0.0
    points: list[dict[str, Any]] = []
    for index, trade in enumerate(trades, start=1):
        pnl = float(trade["pnl"]) if trade.get("pnl") is not None else 0.0
        cumulative_pnl += pnl
        points.append(
            {
                "sequence": index,
                "trade_id": trade["id"],
                "symbol": trade["symbol"],
                "closed_at": trade["closed_at"],
                "pnl": trade["pnl"],
                "cumulative_pnl": _round(cumulative_pnl),
            }
        )
    return points


def _discipline_score_band(score: int | None) -> str:
    if score is None:
        return "No review score"
    if score <= 2:
        return "1-2"
    if score == 3:
        return "3"
    return "4-5"


def _group_rows(
    trades: list[dict[str, Any]],
    labeler: Callable[[dict[str, Any]], str],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for trade in trades:
        grouped.setdefault(labeler(trade), []).append(trade)
    return [
        {"group": group, "metrics": calculate_summary(group_trades)}
        for group, group_trades in sorted(grouped.items(), key=lambda item: item[0].lower())
    ]


def grouped_performance(
    connection: sqlite3.Connection,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    trades = list_analytics_trades(connection, start_date, end_date)
    tags_by_trade = list_trade_tags(connection, [trade["id"] for trade in trades])

    tag_expanded: list[dict[str, Any]] = []
    for trade in trades:
        tags = tags_by_trade.get(trade["id"], [])
        if not tags:
            tag_expanded.append({**trade, "tag_name": "No tag"})
        for tag in tags:
            tag_expanded.append({**trade, "tag_name": tag["name"]})

    discipline_groups = (
        _group_rows(trades, lambda trade: _discipline_score_band(trade.get("discipline_score")))
        if any(trade.get("discipline_score") is not None for trade in trades)
        else []
    )

    return {
        "by_symbol": _group_rows(trades, lambda trade: trade.get("symbol") or "Unknown symbol"),
        "by_playbook": _group_rows(trades, lambda trade: trade.get("playbook_name") or "No playbook"),
        "by_direction": _group_rows(trades, lambda trade: trade.get("direction") or "Unknown direction"),
        "by_tag": _group_rows(tag_expanded, lambda trade: trade.get("tag_name") or "No tag"),
        "by_followed_playbook": _group_rows(trades, lambda trade: trade.get("followed_playbook") or "No review"),
        "by_discipline_score_band": discipline_groups,
    }
