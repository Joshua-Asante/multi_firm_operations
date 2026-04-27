"""Shared utilities for the 2026-04-26 Identify-corpus extractions.

OANDA-proxy run per AMENDMENT_oanda_rescope.md. All artefacts produced by
scripts in this directory carry feed/panel/canonical_status metadata.
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pandas as pd

# Project root: walk up until we find data/bar_data/ (handles worktree case).
def find_project_root() -> Path:
    here = Path(__file__).resolve()
    for cand in [here.parent, *here.parents]:
        if (cand / "data" / "bar_data").exists():
            return cand
    # Fallback: parent of worktree
    here_parts = here.parts
    if ".claude" in here_parts:
        idx = here_parts.index(".claude")
        return Path(*here_parts[:idx])
    raise RuntimeError("Could not locate project root with data/bar_data/")

ROOT = find_project_root()
DATA = ROOT / "data"
BAR_DIR = DATA / "bar_data"
TV_DIR = ROOT / "data" / "tv_exports" / "oanda"

# Worktree-local for output (so corpus lands inside the worktree branch)
WORKTREE = Path(__file__).resolve().parents[3]
OUT_DIR = WORKTREE / "docs" / "methodology" / "identify_corpus" / "2026-04-26"
SCRIPT_DIR = WORKTREE / "scripts" / "identify" / "2026-04-26"

# Add lib/ to path for MVD
sys.path.insert(0, str(WORKTREE / "lib"))
sys.path.insert(0, str(ROOT / "lib"))

# Identity manifest
STRATEGIES = {
    "guardian": {
        "tv": "Guardian_Gold_v5.5_OANDA_XAUUSD_2026-04-25_9ae1f.csv",
        "bar_symbol": "XAUUSD",
        "version": "v5.5",
        "instrument": "Gold",
        "broker": "OANDA",
        "tv_symbol": "XAUUSD",
    },
    "striker": {
        "tv": "Striker_DJ30_v4.4_OANDA_US30USD_2026-04-25_86e9d.csv",
        "bar_symbol": "US30USD",
        "version": "v4.4",
        "instrument": "DJ30",
        "broker": "OANDA",
        "tv_symbol": "US30USD",
    },
    "aegis": {
        "tv": "Aegis_USDJPY_v4.3_OANDA_USDJPY_2026-04-25_7ee6b.csv",
        "bar_symbol": "USDJPY",
        "version": "v4.3",
        "instrument": "USDJPY",
        "broker": "OANDA",
        "tv_symbol": "USDJPY",
    },
}

# Canonical metadata for every output row
META = {
    "feed": "OANDA",
    "panel_window": "2022-01-02_2026-04-19",
    "canonical_status": "PROXY",
}

# Resolved per-strategy chart TZ. Phase 0 verified all three strategies use
# America/New_York chart-TZ (TV exports show NY-local timestamps; auto EST/EDT).
# - Striker: UTC 239pt diff vs EDT 0.20pt diff (decisive)
# - Aegis:   UTC 0.31  diff vs EDT 0.084 diff (decisive)
# - Guardian:UTC 4.07  diff vs EST 1.81  diff (marginal but consistent with
#            1r_estimation.md note "0/201 entries < 08:00 EST")
CHART_TZ = "America/New_York"


def load_resolved_tz() -> dict:
    import json
    f = OUT_DIR / "resolved_tz.json"
    return json.loads(f.read_text()) if f.exists() else {}


def load_bars(symbol: str) -> pd.DataFrame:
    """Load OANDA 15min bars; returns DataFrame indexed by tz-aware UTC time."""
    p = BAR_DIR / f"{symbol}.csv"
    df = pd.read_csv(p)
    df["time"] = pd.to_datetime(df["time"], utc=True, format="ISO8601")
    df = df.set_index("time").sort_index()
    return df


def load_tv(strategy: str) -> pd.DataFrame:
    """Load TV export. Returns one row per Trade #, with entry/exit fields paired.

    TV exports two rows per trade: Exit (newer) then Entry (older), sharing the
    same Trade #. We pivot to one row per trade with entry_*, exit_*, mfe_*,
    mae_*, net_pnl, etc. Times remain naive (chart-TZ); resolved_tz.json
    captures the offset to UTC.
    """
    info = STRATEGIES[strategy]
    p = TV_DIR / info["tv"]
    df = pd.read_csv(p, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]

    df["Date and time"] = pd.to_datetime(df["Date and time"], format="%Y-%m-%d %H:%M")

    entries = df[df["Type"] == "Entry long"].copy()
    exits = df[df["Type"] == "Exit long"].copy()

    entries = entries.rename(columns={
        "Date and time": "entry_time",
        "Price USD": "entry_price",
        "Price JPY": "entry_price",
        "Signal": "entry_signal",
    })
    exits = exits.rename(columns={
        "Date and time": "exit_time",
        "Price USD": "exit_price",
        "Price JPY": "exit_price",
        "Signal": "exit_signal",
    })

    # Price col name varies (USD vs JPY)
    price_col = "Price USD" if "Price USD" in df.columns else "Price JPY"
    entry_price_col = "Price USD" if "Price USD" in df[df["Type"] == "Entry long"].columns else "Price JPY"

    entries = df[df["Type"] == "Entry long"][[
        "Trade #", "Date and time", "Signal", price_col, "Size (qty)", "Size (value)",
    ]].rename(columns={
        "Date and time": "entry_time",
        "Signal": "entry_signal",
        price_col: "entry_price",
    })
    exits = df[df["Type"] == "Exit long"][[
        "Trade #", "Date and time", "Signal", price_col,
        "Net P&L USD", "Net P&L %",
        "Favorable excursion USD", "Favorable excursion %",
        "Adverse excursion USD", "Adverse excursion %",
        "Cumulative P&L USD",
    ]].rename(columns={
        "Date and time": "exit_time",
        "Signal": "exit_signal",
        price_col: "exit_price",
        "Net P&L USD": "net_pnl_usd",
        "Net P&L %": "net_pnl_pct",
        "Favorable excursion USD": "mfe_usd",
        "Favorable excursion %": "mfe_pct",
        "Adverse excursion USD": "mae_usd",
        "Adverse excursion %": "mae_pct",
        "Cumulative P&L USD": "cum_pnl_usd",
    })

    merged = entries.merge(exits, on="Trade #", how="outer")
    merged = merged.sort_values("Trade #").reset_index(drop=True)
    return merged


def add_meta_cols(df: pd.DataFrame, **extra) -> pd.DataFrame:
    """Stamp every row with the canonical OANDA-proxy metadata."""
    out = df.copy()
    for k, v in {**META, **extra}.items():
        out[k] = v
    return out


# Per-strategy locked params (read from Pine; see Phase 0 audit)
PARAMS = {
    "guardian": {"atr_len": 14, "stop_atr": 1.55, "tp_atr": 29.0, "risk_pct": 0.34, "max_hold": 850},
    "striker":  {"atr_len": 11, "stop_atr": 1.25, "tp_atr": 8.0,  "risk_pct": 1.00, "max_hold": 55},
    "aegis":    {"atr_len": 19, "stop_atr": 1.42, "tp_atr": None, "risk_pct": 1.50, "max_hold": 40,
                 "bb_len": 19, "bb_mult": 1.9, "tp_offset_atr": 0.8,
                 "be_trigger_atr": 0.3, "be_pad_atr": 0.15, "min_atr": 0.07},
}


def compute_atr(bars: pd.DataFrame, length: int) -> pd.Series:
    """Wilder ATR (RMA) — matches Pine's ta.atr()."""
    high, low, close = bars["high"], bars["low"], bars["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    # Wilder smoothing = EMA with alpha = 1/length
    return tr.ewm(alpha=1.0 / length, adjust=False).mean()


def utc_from_tv(tv_naive: pd.Series) -> pd.Series:
    """Convert naive chart-TZ (America/New_York) timestamps to UTC tz-aware.

    Auto-handles EST/EDT. nonexistent (DST spring-forward) → shift forward;
    ambiguous (fall-back) → assume daylight time (entry/exit logged in real time).
    """
    return (
        tv_naive.dt.tz_localize(CHART_TZ, nonexistent="shift_forward", ambiguous=True)
                .dt.tz_convert("UTC")
    )
