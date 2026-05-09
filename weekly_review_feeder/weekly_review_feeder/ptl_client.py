"""Notion Pre-Trade Log client — query entries by week range."""
from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

import requests

from .config import NOTION_PTL_DB_ID, PTL_STRATEGY_MAP


NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def query_ptl_for_week(
    token: str,
    week_start: date,
    week_end: date,
    db_id: str = NOTION_PTL_DB_ID,
) -> list[dict[str, Any]]:
    """Query Pre-Trade Log entries with Signal Time in [week_start, week_end].

    Returns list of normalized entry dicts:
      {page_id, signal_time, strategy_key, action, account, risk_pct,
       expected_r, outcome_r, edge_captured, linked_dxtrade_id, ...}
    """
    payload = {
        "filter": {
            "and": [
                {
                    "property": "Signal Time",
                    "date": {"on_or_after": week_start.isoformat()},
                },
                {
                    "property": "Signal Time",
                    "date": {"on_or_before": (week_end + timedelta(days=1)).isoformat()},
                },
            ]
        },
        "page_size": 100,
        "sorts": [{"property": "Signal Time", "direction": "ascending"}],
    }

    entries: list[dict[str, Any]] = []
    has_more = True
    cursor: str | None = None

    while has_more:
        body = dict(payload)
        if cursor:
            body["start_cursor"] = cursor
        r = requests.post(
            f"{NOTION_API_BASE}/databases/{db_id}/query",
            headers=_headers(token),
            json=body,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        for page in data.get("results", []):
            entries.append(_normalize_ptl_page(page))
        has_more = data.get("has_more", False)
        cursor = data.get("next_cursor")

    return entries


def _normalize_ptl_page(page: dict[str, Any]) -> dict[str, Any]:
    """Extract the fields we care about from a Notion page payload."""
    props = page.get("properties", {})

    def _select_name(prop_name: str) -> str | None:
        p = props.get(prop_name) or {}
        sel = p.get("select")
        return sel.get("name") if sel else None

    def _checkbox(prop_name: str) -> bool:
        p = props.get(prop_name) or {}
        return bool(p.get("checkbox"))

    def _number(prop_name: str) -> float | None:
        p = props.get(prop_name) or {}
        return p.get("number")

    def _date_start(prop_name: str) -> str | None:
        p = props.get(prop_name) or {}
        d = p.get("date") or {}
        return d.get("start")

    def _rich_text(prop_name: str) -> str:
        p = props.get(prop_name) or {}
        rt = p.get("rich_text") or []
        return "".join(seg.get("plain_text", "") for seg in rt)

    def _title(prop_name: str) -> str:
        p = props.get(prop_name) or {}
        t = p.get("title") or []
        return "".join(seg.get("plain_text", "") for seg in t)

    strategy_display = _select_name("Strategy") or ""
    return {
        "page_id": page.get("id"),
        "signal_time": _date_start("Signal Time"),
        "strategy_display": strategy_display,
        "strategy_key": PTL_STRATEGY_MAP.get(strategy_display),
        "action": _select_name("Action"),
        "account": _select_name("Account/Firm"),
        "behavioral_state": _select_name("Behavioral State"),
        "risk_pct": _number("Risk %"),
        "expected_r": _number("Expected R"),
        "outcome_r": _number("Outcome R"),
        "edge_captured": _checkbox("Edge Captured"),
        "linked_dxtrade_id": _rich_text("Linked DXTrade ID"),
        "outcome_notes": _rich_text("Outcome Notes"),
        "skip_reason": _rich_text("Skip / Override Reason"),
        "pre_outcome_rationale": _rich_text("Pre-Outcome Rationale"),
        "title": _title("Signal"),
    }


def signals_taken(entries: list[dict[str, Any]]) -> int:
    """Count PTL entries with Action == 'Taken'."""
    return sum(1 for e in entries if e.get("action") == "Taken")


def signals_skipped(entries: list[dict[str, Any]]) -> int:
    """Count PTL entries with Action == 'Skipped'."""
    return sum(1 for e in entries if e.get("action") == "Skipped")


def get_token() -> str:
    """Resolve Notion API token from env."""
    token = os.environ.get("NOTION_API_TOKEN")
    if not token:
        raise RuntimeError(
            "NOTION_API_TOKEN env var not set. "
            "Get an integration token at https://www.notion.so/my-integrations "
            "and share the relevant pages with the integration."
        )
    return token
