"""Config: symbol→strategy mapping, Notion DB IDs, week-range helpers."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta

# ============================================================================
# Symbol → strategy mapping (Tier 1)
# ============================================================================
# Maps DXTrade fill symbols to internal strategy keys.
# Internal keys: G | DJ30 | A | NAS — used in JSON output and per-strategy P&L attribution.
# Pre-Trade Log "Strategy" field is the Tier 2 tiebreaker for symbol collisions.
SYMBOL_STRATEGY_MAP: dict[str, str] = {
    "XAUUSD": "G",
    "XAUUSD.A": "G",
    "XAUUSD.XX": "G",   # Seen on DXTrade fills export 2026-W19
    "US30": "DJ30",
    "US30.XX": "DJ30",
    "USDJPY": "A",
    "USDJPY.XX": "A",
    "NAS100": "NAS",
    "NAS100.XX": "NAS",
}

# Reverse mapping: PTL Strategy display name → internal key
PTL_STRATEGY_MAP: dict[str, str] = {
    "Guardian Gold v5.5": "G",
    "Striker DJ30 v4.5": "DJ30",
    "Aegis v4.3": "A",
    "Striker NAS100 v1": "NAS",
}

INTERNAL_STRATEGY_KEYS: tuple[str, ...] = ("G", "DJ30", "A", "NAS")


# ============================================================================
# Day-gate matrix (which strategies trade on which days)
# ============================================================================
# Source of truth from locked portfolio (2026-05-05 lock).
# Used by op-test heuristic in fills_parser to flag non-session-day trades.
DAY_GATE: dict[str, frozenset[str]] = {
    "Mon": frozenset({"G", "A", "NAS"}),
    "Tue": frozenset({"G", "DJ30", "A", "NAS"}),
    "Wed": frozenset({"A"}),
    "Thu": frozenset({"G"}),
    "Fri": frozenset({"DJ30"}),
    "Sat": frozenset(),
    "Sun": frozenset(),
}


# ============================================================================
# Notion DB / data source IDs
# ============================================================================
# These are stable identifiers from the user's CTA Track-Record Habits page.
# Override via env vars if needed (e.g. for staging workspace).
NOTION_PTL_DB_ID = os.environ.get(
    "NOTION_PTL_DB_ID", "e375125c-8c60-42ec-80ce-6dcb33122831"
)
NOTION_WEEKLY_REVIEW_DB_ID = os.environ.get(
    "NOTION_WEEKLY_REVIEW_DB_ID", "903516488cde49099a159822c5916eee"
)


# ============================================================================
# Risk-percent design (per locked portfolio)
# ============================================================================
# Used for sanity-checking PTL Risk% entries match design.
DESIGN_RISK_PCT: dict[str, float] = {
    "G": 0.0034,
    "DJ30": 0.0100,
    "A": 0.0150,
    "NAS": 0.0040,
}


# ============================================================================
# File-path conventions
# ============================================================================
# All paths are relative to repo root unless absolute.
# Override via env vars at runtime.
@dataclass(frozen=True)
class Paths:
    fills_dir: str = os.environ.get("WRF_FILLS_DIR", "data/fills")
    backtest_dir: str = os.environ.get(
        "WRF_BACKTEST_DIR", "data/tv_exports/pepperstone"
    )
    dd_log_path: str = os.environ.get("WRF_DD_LOG", "data/dd_protection.log")
    feeder_runs_dir: str = os.environ.get(
        "WRF_RUNS_DIR", "data/feeder_runs"
    )

    def backtest_csv(self, strategy_key: str) -> str:
        """Return convention path for a strategy's Pepperstone backtest CSV."""
        filenames = {
            "G": "guardian_gold_v5_5.csv",
            "DJ30": "striker_dj30_v4_5.csv",
            "A": "aegis_v4_3.csv",
            "NAS": "striker_nas100_v1.csv",
        }
        return os.path.join(self.backtest_dir, filenames[strategy_key])


# ============================================================================
# Week-range helpers
# ============================================================================

def iso_week_to_range(week_label: str) -> tuple[date, date]:
    """Convert ISO week label (e.g. '2026-W19') to trading-week date range.

    Trading week convention: Mon-Fri inclusive. Sat/Sun excluded.
    Returns (week_start_monday, week_end_friday).
    """
    if "-W" not in week_label:
        raise ValueError(f"Bad ISO week label: {week_label!r}. Expected 'YYYY-Wnn'.")
    year_str, wk_str = week_label.split("-W")
    year, wk = int(year_str), int(wk_str)
    monday = date.fromisocalendar(year, wk, 1)
    friday = monday + timedelta(days=4)
    return monday, friday


def date_to_iso_week(d: date) -> str:
    """Convert a date to its ISO week label."""
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def trading_days_in_range(week_start: date, week_end: date) -> int:
    """Count Mon-Fri days in the inclusive range."""
    n = 0
    cur = week_start
    while cur <= week_end:
        if cur.weekday() < 5:  # 0=Mon ... 4=Fri
            n += 1
        cur += timedelta(days=1)
    return n


def day_name(d: date) -> str:
    """Return three-letter day name (Mon, Tue, ...)."""
    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d.weekday()]
