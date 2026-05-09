"""Notion Writer — create or update a Weekly Review row."""
from __future__ import annotations

import json
from datetime import date
from typing import Any

import requests

from .config import NOTION_WEEKLY_REVIEW_DB_ID


NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def find_existing_review(
    token: str, week_label: str, db_id: str = NOTION_WEEKLY_REVIEW_DB_ID
) -> str | None:
    """Find an existing Weekly Review row by Week title. Returns page_id or None."""
    body = {
        "filter": {
            "property": "Week",
            "title": {"equals": week_label},
        },
        "page_size": 1,
    }
    r = requests.post(
        f"{NOTION_API_BASE}/databases/{db_id}/query",
        headers=_headers(token),
        json=body,
        timeout=30,
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    if results:
        return results[0]["id"]
    return None


def _build_properties(payload: dict[str, Any]) -> dict[str, Any]:
    """Translate flat JSON payload (from compute) to Notion property updates."""
    props: dict[str, Any] = {
        "Week": {"title": [{"text": {"content": payload["week"]}}]},
        "Trading Days": {"number": payload["trading_days"]},
        "Realized P&L": {"number": payload["realized_pnl"]},
        "Backtest-Equiv P&L": {"number": payload["backtest_equiv_pnl"]},
        "MC P10": {"number": payload["mc_p10"]},
        "MC P50": {"number": payload["mc_p50"]},
        "MC P90": {"number": payload["mc_p90"]},
        "G P&L": {"number": payload["g_pnl"]},
        "DJ30 P&L": {"number": payload["dj30_pnl"]},
        "A P&L": {"number": payload["a_pnl"]},
        "NAS P&L": {"number": payload["nas_pnl"]},
        "Signals Fired": {"number": payload["signals_fired"]},
        "Signals Taken": {"number": payload["signals_taken"]},
        "Skip Count": {"number": payload["skip_count"]},
        "Avg Slippage": {"number": payload["avg_slippage"]},
        "DD Events": {"number": payload["dd_events"]},
        "MC Placement": {"select": {"name": payload["mc_placement"]}},
        "Week Start": {"date": {"start": payload["week_start"]}},
        "Week End": {"date": {"start": payload["week_end"]}},
    }
    if payload["edge_captured_ratio"] is not None:
        props["Edge-Captured Ratio"] = {"number": payload["edge_captured_ratio"]}

    return props


def create_or_update_weekly_review(
    token: str, payload: dict[str, Any], db_id: str = NOTION_WEEKLY_REVIEW_DB_ID
) -> dict[str, Any]:
    """Create the row if absent; update numeric fields if present.

    Returns: {action: 'created'|'updated', page_id: str, url: str}.
    """
    page_id = find_existing_review(token, payload["week"], db_id=db_id)
    properties = _build_properties(payload)

    if page_id:
        # Update existing page (PATCH /pages/{id})
        r = requests.patch(
            f"{NOTION_API_BASE}/pages/{page_id}",
            headers=_headers(token),
            json={"properties": properties},
            timeout=30,
        )
        r.raise_for_status()
        return {"action": "updated", "page_id": page_id, "url": r.json().get("url")}

    # Create new page
    r = requests.post(
        f"{NOTION_API_BASE}/pages",
        headers=_headers(token),
        json={
            "parent": {"database_id": db_id},
            "properties": properties,
        },
        timeout=30,
    )
    r.raise_for_status()
    body = r.json()
    return {"action": "created", "page_id": body.get("id"), "url": body.get("url")}
