#!/usr/bin/env python3
"""
live-execution-journal — signal-vs-fill reconciliation pipeline.

Compares a DXTrade fills export against backtest CSVs for the same window,
classifies each signal/fill pair (TAKEN-ON-SPEC / TAKEN-DISCRETIONARY /
SKIPPED / OFF-SPEC), and computes the edge-captured ratio.

The edge-captured ratio is the load-bearing metric — it makes the claim
"I'm trading the system" falsifiable. Below 80% on a clean-version window
is an execution problem; below 50% is an emergency. The 7-week 04-29
audit measured it at ~3% (~$500 captured of ~$18K fired).

Usage:
  python journal_review.py \\
    --dxtrade <dxtrade_export.csv> \\
    --backtest guardian:<csv> [striker_dj30:<csv> aegis:<csv> striker_nas:<csv>] \\
    --start YYYY-MM-DD --end YYYY-MM-DD \\
    [--account 200000] [--feed pepperstone] [--journal notion_export.csv]

Conventions enforced:
  - Backtest IS the FIRE alert log (no separate alert capture needed)
  - Pairing window: ±60 min on entry time, ±10% on size for ON-SPEC
  - Same-second multi-fill on Striker/NAS = pyramid, not split execution
  - Skip-with-rationale (from Notion journal) and skip-without-rationale
    are distinct in output
"""

from __future__ import annotations
import argparse
import sys
import re
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional, Iterable

import pandas as pd  # type: ignore
import numpy as np  # type: ignore


# ---------------------------------------------------------------------------
# DXTrade column alias map — autodetect common DXTrade export schemas.
# Add aliases as new export variants surface.
# ---------------------------------------------------------------------------

DXTRADE_COLUMN_ALIASES = {
    "order_id":    ["Order ID", "Order #", "Ticket", "OrderId", "Order Number"],
    "symbol":      ["Symbol", "Instrument", "Asset", "Ticker"],
    "side":        ["Side", "Direction", "Type", "B/S", "Buy/Sell"],
    "quantity":    ["Quantity", "Size", "Lots", "Volume", "Qty"],
    "open_time":   ["Open Time", "Open Date", "Entry Time", "Date Opened", "Opened"],
    "open_price":  ["Open Price", "Entry Price", "Open", "Buy Price"],
    "close_time":  ["Close Time", "Close Date", "Exit Time", "Date Closed", "Closed"],
    "close_price": ["Close Price", "Exit Price", "Close", "Sell Price"],
    "pnl":         ["Net P&L", "P&L", "Profit", "Net Profit", "Realized P&L", "P/L"],
    "commission":  ["Commission", "Fee", "Fees"],
    "swap":        ["Swap", "Rollover", "Overnight"],
}

# Symbol normalizer: strip separators and standardize common synonyms
SYMBOL_SYNONYMS = {
    "GOLD": "XAUUSD", "XAU/USD": "XAUUSD", "XAUUSD.A": "XAUUSD",
    "US30": "DJ30", "US30.CASH": "DJ30", "DJIA": "DJ30", "WALL": "DJ30",
    "USDJPY.A": "USDJPY", "USD/JPY": "USDJPY",
    "NAS100": "NAS100", "USTEC": "NAS100", "NDX": "NAS100", "US100": "NAS100",
}

STRATEGIES = {
    "guardian":     {"symbol": "XAUUSD", "risk_pct": 0.34, "pyramid": False, "label": "Guardian"},
    "striker_dj30": {"symbol": "DJ30",   "risk_pct": 1.00, "pyramid": True,  "label": "Striker DJ30"},
    "striker_nas":  {"symbol": "NAS100", "risk_pct": 0.40, "pyramid": True,  "label": "Striker NAS100"},
    "aegis":        {"symbol": "USDJPY", "risk_pct": 1.50, "pyramid": False, "label": "Aegis"},
}

# Embedded macro-event calendar for the macro-skip check.
# Extend by editing this list or by passing --macro-events via JSON.
# Sources: Fed FOMC schedule, BLS NFP/CPI release dates, BoJ schedule.
MACRO_EVENTS_2026 = [
    # Format: (date, label)
    ("2026-01-07", "NFP"), ("2026-01-13", "CPI"), ("2026-01-28", "FOMC"),
    ("2026-02-04", "NFP"), ("2026-02-12", "CPI"),
    ("2026-03-04", "NFP"), ("2026-03-12", "CPI"), ("2026-03-18", "FOMC"),
    ("2026-04-03", "NFP"), ("2026-04-10", "CPI"), ("2026-04-29", "FOMC"),
    ("2026-04-28", "BOJ"),
    ("2026-05-01", "NFP"), ("2026-05-13", "CPI"),
]

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Fill:
    """A live DXTrade fill."""
    order_id: str
    symbol: str          # normalized
    side: str            # 'long' or 'short'
    quantity: float
    open_time: pd.Timestamp
    open_price: float
    close_time: pd.Timestamp
    close_price: float
    pnl: float
    commission: float = 0.0
    swap: float = 0.0
    raw_index: int = -1


@dataclass
class Signal:
    """A backtest-fired signal (= what the FIRE alert told us to do)."""
    strategy: str
    symbol: str          # normalized
    side: str
    quantity: float      # backtest size
    entry_time: pd.Timestamp
    entry_price: float
    exit_time: pd.Timestamp
    exit_price: float
    pnl: float
    exit_reason: str = ""


@dataclass
class Pairing:
    """A signal/fill pair, classified."""
    classification: str  # TAKEN-ON-SPEC | TAKEN-DISCRETIONARY | SKIPPED | OFF-SPEC
    signal: Optional[Signal]
    fills: list[Fill]    # may be multiple for pyramid
    counterfactual_pnl: float
    realized_pnl: float
    gap: float           # realized - counterfactual
    notes: list[str] = field(default_factory=list)


@dataclass
class ReviewResult:
    window_start: date
    window_end: date
    fills: list[Fill]
    signals: list[Signal]
    pairings: list[Pairing]
    n_signals: int
    n_fills: int
    counts: dict
    pnl_realized: float
    pnl_counterfactual: float
    pnl_gap: float
    edge_captured_ratio: float
    leakage_skips: float
    leakage_discretion: float
    gain_offspec: float
    watchlist: list[str]
    version_mixed: bool


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def normalize_symbol(s: str) -> str:
    if not isinstance(s, str):
        return ""
    cleaned = re.sub(r"[^A-Z0-9]", "", s.upper())
    return SYMBOL_SYNONYMS.get(cleaned, cleaned)


def find_column(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    """Case-insensitive column-alias lookup."""
    lower_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


def parse_time(val) -> Optional[pd.Timestamp]:
    if pd.isna(val):
        return None
    try:
        return pd.to_datetime(val)
    except Exception:
        return None


def parse_side(val) -> str:
    if not isinstance(val, str):
        return "long"
    v = val.strip().upper()
    if v in ("BUY", "B", "LONG"):
        return "long"
    if v in ("SELL", "S", "SHORT"):
        return "short"
    return "long"  # default


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_dxtrade(path: str | Path) -> list[Fill]:
    """
    Load a DXTrade fills export. Schema-flexible — uses DXTRADE_COLUMN_ALIASES
    to detect column names. Surfaces missing required columns clearly.
    """
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [c.strip().replace("\ufeff", "") for c in df.columns]

    # Map logical names to actual column names
    col = {}
    for logical, candidates in DXTRADE_COLUMN_ALIASES.items():
        col[logical] = find_column(df, candidates)

    required = ["symbol", "quantity", "open_time", "open_price",
                "close_time", "close_price", "pnl"]
    missing = [k for k in required if col[k] is None]
    if missing:
        raise ValueError(
            f"DXTrade export missing required columns: {missing}. "
            f"Available: {list(df.columns)}. "
            f"Update DXTRADE_COLUMN_ALIASES if a new schema variant."
        )

    fills: list[Fill] = []
    for idx, row in df.iterrows():
        ot = parse_time(row[col["open_time"]])
        ct = parse_time(row[col["close_time"]])
        if ot is None or ct is None:
            continue  # open position or malformed row

        try:
            f = Fill(
                order_id=str(row[col["order_id"]]) if col["order_id"] else f"row{idx}",
                symbol=normalize_symbol(str(row[col["symbol"]])),
                side=parse_side(row[col["side"]]) if col["side"] else "long",
                quantity=float(row[col["quantity"]]),
                open_time=ot,
                open_price=float(row[col["open_price"]]),
                close_time=ct,
                close_price=float(row[col["close_price"]]),
                pnl=float(row[col["pnl"]]),
                commission=float(row[col["commission"]]) if col["commission"] else 0.0,
                swap=float(row[col["swap"]]) if col["swap"] else 0.0,
                raw_index=int(idx),
            )
            fills.append(f)
        except (ValueError, TypeError):
            continue

    return fills


def load_backtest(path: str | Path, strategy: str) -> list[Signal]:
    """
    Load a TradingView backtest CSV (Pepperstone/OANDA/Alchemy schema) and
    return Signal objects (backtest-fired entries paired with their exits).
    Reuses the same Entry/Exit pairing convention as trade-csv-reconcile.
    """
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [c.strip().replace("\ufeff", "") for c in df.columns]
    df["dt"] = pd.to_datetime(df["Date and time"], errors="coerce")

    spec_symbol = STRATEGIES[strategy]["symbol"]

    entries = df[df["Type"].str.startswith("Entry", na=False)].copy()
    exits = df[df["Type"].str.startswith("Exit", na=False)].copy()

    signals: list[Signal] = []
    for trade_num, exit_grp in exits.groupby("Trade #"):
        ent_grp = entries[entries["Trade #"] == trade_num]
        if ent_grp.empty:
            continue
        # First entry = base; pyramid adds aggregate to total qty
        first_entry = ent_grp.sort_values("dt").iloc[0]
        last_exit = exit_grp.sort_values("dt").iloc[-1]
        total_qty = float(ent_grp["Size (qty)"].astype(float).sum()) if "Size (qty)" in ent_grp else float(first_entry.get("Size (qty)", 0))
        side = "long" if "long" in str(first_entry["Type"]).lower() else "short"
        pnl = float(exit_grp["Net P&L USD"].astype(float).sum())

        signals.append(Signal(
            strategy=strategy,
            symbol=spec_symbol,
            side=side,
            quantity=total_qty,
            entry_time=first_entry["dt"],
            entry_price=float(first_entry["Price USD"]),
            exit_time=last_exit["dt"],
            exit_price=float(last_exit["Price USD"]),
            pnl=pnl,
            exit_reason=str(last_exit.get("Signal", "")),
        ))

    return signals


def filter_to_window(items, start: date, end: date, time_attr: str):
    """Filter list of Fill or Signal objects to inclusive [start, end] on time_attr."""
    out = []
    for it in items:
        t = getattr(it, time_attr)
        if t is None:
            continue
        d = t.date() if hasattr(t, "date") else t
        if start <= d <= end:
            out.append(it)
    return out


# ---------------------------------------------------------------------------
# Pairing & classification
# ---------------------------------------------------------------------------

PAIRING_WINDOW_MINUTES = 60
SIZE_TOLERANCE_PCT = 0.10  # ±10% for ON-SPEC


def pair_signals_to_fills(
    signals: list[Signal],
    fills: list[Fill],
) -> list[Pairing]:
    """
    Pair backtest signals to live fills. Each signal can claim 1+ fills
    (pyramid arch produces multi-fill matches). Each fill can be claimed
    only once.

    Algorithm:
      For each signal (sorted by entry_time):
        Find candidate fills: same normalized symbol, side match,
          fill.open_time within ±PAIRING_WINDOW_MINUTES of signal.entry_time,
          fill not yet claimed.
        Claim them. Classify:
          TAKEN-ON-SPEC if total_size matches signal.quantity within SIZE_TOLERANCE_PCT
          TAKEN-DISCRETIONARY otherwise.
        If no candidates: SKIPPED.

      Any unclaimed fill at the end: OFF-SPEC.
    """
    pairings: list[Pairing] = []
    claimed_indices: set[int] = set()

    # Sort signals chronologically
    signals_sorted = sorted(signals, key=lambda s: s.entry_time)

    for sig in signals_sorted:
        window_start = sig.entry_time - timedelta(minutes=PAIRING_WINDOW_MINUTES)
        window_end = sig.entry_time + timedelta(minutes=PAIRING_WINDOW_MINUTES)

        # Pyramid architectures: extend the pairing window to capture
        # subsequent pyramid legs, since pyramid adds happen during the
        # held position, not at signal time. Use the signal's exit time
        # as the upper bound for pyramid arch.
        is_pyramid = STRATEGIES[sig.strategy]["pyramid"]
        if is_pyramid:
            window_end = max(window_end, sig.exit_time + timedelta(minutes=PAIRING_WINDOW_MINUTES))

        candidates: list[Fill] = []
        for f in fills:
            if f.raw_index in claimed_indices:
                continue
            if f.symbol != sig.symbol:
                continue
            if f.side != sig.side:
                continue
            if not (window_start <= f.open_time <= window_end):
                continue
            candidates.append(f)

        if not candidates:
            pairings.append(Pairing(
                classification="SKIPPED",
                signal=sig,
                fills=[],
                counterfactual_pnl=sig.pnl,
                realized_pnl=0.0,
                gap=-sig.pnl,
            ))
            continue

        # Claim candidates
        for f in candidates:
            claimed_indices.add(f.raw_index)
        total_qty = sum(f.quantity for f in candidates)
        realized = sum(f.pnl for f in candidates)

        # ON-SPEC criteria: single fill (or pyramid-allowed multi-fill),
        # total size within ±10% of signal size, exit time within ±60min
        size_ok = (
            sig.quantity > 0
            and abs(total_qty - sig.quantity) / sig.quantity <= SIZE_TOLERANCE_PCT
        )
        # For non-pyramid arch: a multi-fill pairing is NOT on-spec
        # (Apr-15 Aegis pattern). Pyramid arch allows multi-fill.
        multi_fill_ok = is_pyramid or len(candidates) == 1

        last_close = max(f.close_time for f in candidates)
        exit_window_ok = abs((last_close - sig.exit_time).total_seconds()) <= 60 * 60

        notes = []
        if not size_ok:
            notes.append(f"size deviation: signal={sig.quantity:.2f}, actual={total_qty:.2f} ({(total_qty - sig.quantity) / sig.quantity * 100:+.1f}%)")
        if not multi_fill_ok:
            notes.append(f"multi-fill on non-pyramid arch ({len(candidates)} fills for one signal)")
        if not exit_window_ok:
            notes.append(f"exit time deviation: signal={sig.exit_time}, actual={last_close}")

        if size_ok and multi_fill_ok and exit_window_ok:
            cls = "TAKEN-ON-SPEC"
        else:
            cls = "TAKEN-DISCRETIONARY"

        pairings.append(Pairing(
            classification=cls,
            signal=sig,
            fills=candidates,
            counterfactual_pnl=sig.pnl,
            realized_pnl=realized,
            gap=realized - sig.pnl,
            notes=notes,
        ))

    # Unclaimed fills = OFF-SPEC
    for f in fills:
        if f.raw_index in claimed_indices:
            continue
        pairings.append(Pairing(
            classification="OFF-SPEC",
            signal=None,
            fills=[f],
            counterfactual_pnl=0.0,
            realized_pnl=f.pnl,
            gap=f.pnl,
            notes=[f"no matching backtest signal in window for {f.symbol}"],
        ))

    return pairings


# ---------------------------------------------------------------------------
# Pattern checks
# ---------------------------------------------------------------------------

def check_skip_cluster(pairings: list[Pairing]) -> Optional[str]:
    """3+ skips within any 5-trading-day window."""
    skips = sorted(
        [p for p in pairings if p.classification == "SKIPPED"],
        key=lambda p: p.signal.entry_time,
    )
    if len(skips) < 3:
        return None
    # Sliding 5-day window
    for i in range(len(skips) - 2):
        window_start = skips[i].signal.entry_time
        window_end = window_start + timedelta(days=5)
        in_window = sum(1 for s in skips[i:] if s.signal.entry_time <= window_end)
        if in_window >= 3:
            return (
                f"skip-cluster: {in_window} skips in 5-day window starting "
                f"{window_start.date()} — review for behavioral state "
                f"(post-loss, fatigue, macro-stress)"
            )
    return None


def check_skip_by_strategy(pairings: list[Pairing]) -> Optional[str]:
    """One strategy accounts for >60% of skips."""
    skips = [p for p in pairings if p.classification == "SKIPPED"]
    if len(skips) < 3:
        return None
    counts: dict[str, int] = {}
    for s in skips:
        counts[s.signal.strategy] = counts.get(s.signal.strategy, 0) + 1
    total = len(skips)
    for strat, n in counts.items():
        if n / total > 0.60:
            return (
                f"strategy-aversion: {STRATEGIES[strat]['label']} accounts for "
                f"{n}/{total} ({n/total*100:.0f}%) of skips — possible "
                f"single-strategy confidence problem"
            )
    return None


def check_discretion_on_largest(pairings: list[Pairing]) -> Optional[str]:
    """TAKEN-DISCRETIONARY concentrated on highest-allocation strategy (Aegis)."""
    discretionary = [p for p in pairings if p.classification == "TAKEN-DISCRETIONARY"]
    if not discretionary:
        return None
    largest_strat = max(STRATEGIES.keys(), key=lambda k: STRATEGIES[k]["risk_pct"])
    n_largest = sum(1 for p in discretionary if p.signal.strategy == largest_strat)
    if n_largest / len(discretionary) > 0.50 and n_largest >= 2:
        return (
            f"discretion-on-largest: {n_largest}/{len(discretionary)} discretionary "
            f"events on {STRATEGIES[largest_strat]['label']} (largest-risk leg at "
            f"{STRATEGIES[largest_strat]['risk_pct']}%) — Apr-15 Aegis pattern"
        )
    return None


def check_macro_skip(pairings: list[Pairing], macro_dates: set[date]) -> Optional[str]:
    """Skip rate elevates on tier-1 macro-event days."""
    skips = [p for p in pairings if p.classification == "SKIPPED"]
    if len(skips) < 2 or not macro_dates:
        return None

    # Compute baseline skip rate (skips / total signals across the window)
    total_signals = sum(1 for p in pairings if p.classification != "OFF-SPEC")
    if total_signals == 0:
        return None
    baseline_rate = len(skips) / total_signals

    # On-macro-day rate
    on_macro = [p for p in pairings if p.classification != "OFF-SPEC"
                and p.signal.entry_time.date() in macro_dates]
    if not on_macro:
        return None
    on_macro_skips = sum(1 for p in on_macro if p.classification == "SKIPPED")
    on_macro_rate = on_macro_skips / len(on_macro)

    if on_macro_rate > baseline_rate * 1.5 and on_macro_skips >= 2:
        return (
            f"macro-skip: skip rate on macro-event days ({on_macro_rate*100:.0f}%) "
            f"vs baseline ({baseline_rate*100:.0f}%) — recall Lesson E1 "
            f"(04-07 Guardian +$3,752 counterfactual on Iran-stress skip)"
        )
    return None


def detect_version_mixed(start: date, end: date) -> tuple[bool, list[str]]:
    """Flag review windows that span known version-iteration periods."""
    notes = []
    # Known stable-lock periods:
    # Aegis v4.3 from 2026-04-22
    # Striker DJ30 v4.4 from 2026-04-20, v4.5 from 2026-05-05
    # Guardian v5.5 from 2026-04-23
    # NAS100 v1 from 2026-05-05
    if start < date(2026, 4, 23):
        notes.append("window starts before 2026-04-23 — Guardian/Aegis pre-lock periods may have version drift")
    striker_v45_lock = date(2026, 5, 5)
    if start < striker_v45_lock <= end:
        notes.append(f"window spans Striker DJ30 v4.4→v4.5 transition ({striker_v45_lock}) — version-mixed")
    nas_v1_lock = date(2026, 5, 5)
    if start < nas_v1_lock <= end:
        notes.append(f"window spans Striker NAS100 v1 lock ({nas_v1_lock}) — pre-lock NAS data is research-only")
    mixed = bool(notes)
    return (mixed, notes)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def format_review(result: ReviewResult, journal_lookup: Optional[dict] = None) -> str:
    """Format the canonical review output per SKILL.md Step 7."""
    lines = []
    n_days = (result.window_end - result.window_start).days + 1
    lines.append(f"=== Execution Review : {result.window_start} → {result.window_end} ({n_days} calendar days) ===")
    lines.append("")

    if result.version_mixed:
        lines.append("*** VERSION-MIXED WINDOW — edge-captured ratio is unreliable ***")
        for n in result.counts.get("version_notes", []):
            lines.append(f"  - {n}")
        lines.append("")

    # Strategy breakdown of signals
    by_strat: dict[str, int] = {}
    for s in result.signals:
        by_strat[s.strategy] = by_strat.get(s.strategy, 0) + 1
    breakdown = " / ".join(
        f"{STRATEGIES[k]['label']} {v}" for k, v in sorted(by_strat.items())
    ) or "(none)"

    lines.append(f"Signals fired (backtest)   : {result.n_signals}     [{breakdown}]")
    lines.append(f"Fills executed (DXTrade)   : {result.n_fills}")
    lines.append("")
    lines.append("Classification:")
    lines.append(f"  TAKEN-ON-SPEC            : {result.counts.get('TAKEN-ON-SPEC', 0)}")
    lines.append(f"  TAKEN-DISCRETIONARY      : {result.counts.get('TAKEN-DISCRETIONARY', 0)}")
    lines.append(f"  SKIPPED                  : {result.counts.get('SKIPPED', 0)}")
    lines.append(f"  OFF-SPEC                 : {result.counts.get('OFF-SPEC', 0)}")
    lines.append("")
    lines.append("P&L:")
    lines.append(f"  Realized (DXTrade)       : ${result.pnl_realized:>12,.2f}")
    lines.append(f"  Counterfactual (per-spec): ${result.pnl_counterfactual:>12,.2f}")
    lines.append(f"  Execution leakage        : ${result.pnl_gap:>12,.2f}")
    if result.pnl_counterfactual != 0:
        lines.append(f"  Edge-captured ratio      : {result.edge_captured_ratio*100:>11.1f}%")
    else:
        lines.append(f"  Edge-captured ratio      : N/A (no counterfactual P&L in window)")
    lines.append("")

    if result.pnl_counterfactual != 0:
        cf = result.pnl_counterfactual
        lines.append("Leakage attribution:")
        lines.append(f"  From skips               : ${result.leakage_skips:>12,.2f}   ({result.leakage_skips/cf*100:+.1f}%)")
        lines.append(f"  From discretion          : ${result.leakage_discretion:>12,.2f}   ({result.leakage_discretion/cf*100:+.1f}%)")
        lines.append(f"  From off-spec fills      : ${result.gain_offspec:>12,.2f}   ({result.gain_offspec/cf*100:+.1f}%)")
        lines.append("")

    if result.watchlist:
        lines.append("Watchlist (pattern surfaces — review, do not auto-act):")
        for w in result.watchlist:
            lines.append(f"  - {w}")
        lines.append("")

    # Skipped detail
    skipped = [p for p in result.pairings if p.classification == "SKIPPED"]
    if skipped:
        lines.append("Skipped signals (review for rationale):")
        for p in sorted(skipped, key=lambda x: x.signal.entry_time):
            sig = p.signal
            rationale = "MISSING"
            if journal_lookup:
                rationale = journal_lookup.get(
                    (sig.entry_time.date(), sig.strategy), "MISSING"
                )
            lines.append(
                f"  {sig.entry_time.strftime('%Y-%m-%d %H:%M')} "
                f"{STRATEGIES[sig.strategy]['label']} {sig.symbol} "
                f"— counterfactual ${sig.pnl:>10,.2f}    [rationale: {rationale}]"
            )
        lines.append("")

    # Discretionary detail
    discretionary = [p for p in result.pairings if p.classification == "TAKEN-DISCRETIONARY"]
    if discretionary:
        lines.append("Discretionary modifications:")
        for p in sorted(discretionary, key=lambda x: x.signal.entry_time):
            sig = p.signal
            n_fills = len(p.fills)
            actual_qty = sum(f.quantity for f in p.fills)
            lines.append(
                f"  {sig.entry_time.strftime('%Y-%m-%d %H:%M')} "
                f"{STRATEGIES[sig.strategy]['label']} — "
                f"backtest {sig.quantity:.2f}lot ${sig.pnl:>10,.2f} | "
                f"actual {actual_qty:.2f}lot in {n_fills} fill(s) ${p.realized_pnl:>10,.2f} | "
                f"gap ${p.gap:>+10,.2f}"
            )
            for note in p.notes:
                lines.append(f"      - {note}")
        lines.append("")

    # Off-spec detail
    offspec = [p for p in result.pairings if p.classification == "OFF-SPEC"]
    if offspec:
        lines.append("Off-spec fills (no matching backtest signal — triage):")
        for p in offspec:
            f = p.fills[0]
            lines.append(
                f"  {f.open_time.strftime('%Y-%m-%d %H:%M')} {f.symbol} "
                f"{f.side} {f.quantity:.2f}lot — realized ${f.pnl:>10,.2f}"
            )
        lines.append("")

    # Edge-captured flag
    if (result.pnl_counterfactual > 0
            and result.edge_captured_ratio < 0.80
            and not result.version_mixed):
        lines.append("*** EXECUTION FLAG ***")
        lines.append(
            f"Edge-captured ratio is {result.edge_captured_ratio*100:.1f}% (below 80% threshold)."
        )
        lines.append(
            f"The locked design fired ${result.pnl_counterfactual:,.2f} of edge in this window;"
        )
        lines.append(
            f"${result.pnl_realized:,.2f} was captured. Review skipped signals and discretionary"
        )
        lines.append("modifications above before any methodology work this week.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate(
    pairings: list[Pairing],
    fills: list[Fill],
    signals: list[Signal],
    start: date,
    end: date,
    macro_dates: set[date],
) -> ReviewResult:
    counts: dict = {}
    for p in pairings:
        counts[p.classification] = counts.get(p.classification, 0) + 1

    pnl_realized = sum(p.realized_pnl for p in pairings)
    pnl_counterfactual = sum(p.counterfactual_pnl for p in pairings if p.signal is not None)
    pnl_gap = pnl_realized - pnl_counterfactual
    ratio = pnl_realized / pnl_counterfactual if pnl_counterfactual != 0 else 0.0

    leakage_skips = sum(p.gap for p in pairings if p.classification == "SKIPPED")
    leakage_discretion = sum(p.gap for p in pairings if p.classification == "TAKEN-DISCRETIONARY")
    gain_offspec = sum(p.realized_pnl for p in pairings if p.classification == "OFF-SPEC")

    watchlist: list[str] = []
    for check in (
        check_skip_cluster(pairings),
        check_skip_by_strategy(pairings),
        check_discretion_on_largest(pairings),
        check_macro_skip(pairings, macro_dates),
    ):
        if check:
            watchlist.append(check)

    version_mixed, version_notes = detect_version_mixed(start, end)
    counts["version_notes"] = version_notes

    return ReviewResult(
        window_start=start,
        window_end=end,
        fills=fills,
        signals=signals,
        pairings=pairings,
        n_signals=len(signals),
        n_fills=len(fills),
        counts=counts,
        pnl_realized=pnl_realized,
        pnl_counterfactual=pnl_counterfactual,
        pnl_gap=pnl_gap,
        edge_captured_ratio=ratio,
        leakage_skips=leakage_skips,
        leakage_discretion=leakage_discretion,
        gain_offspec=gain_offspec,
        watchlist=watchlist,
        version_mixed=version_mixed,
    )


# ---------------------------------------------------------------------------
# Journal (Notion export) lookup
# ---------------------------------------------------------------------------

def load_journal(path: str | Path) -> dict:
    """
    Load Notion Trade Journal export and build a (date, strategy) -> rationale map.
    Schema-flexible — looks for columns containing 'date'/'strategy'/'rationale' or 'note'.
    """
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    date_col = next((c for c in df.columns if "date" in c.lower()), None)
    strat_col = next((c for c in df.columns if "strategy" in c.lower()), None)
    note_col = next((c for c in df.columns
                     if any(k in c.lower() for k in ("rationale", "note", "reason", "comment"))), None)

    if not (date_col and strat_col and note_col):
        return {}

    out = {}
    for _, row in df.iterrows():
        try:
            d = pd.to_datetime(row[date_col]).date()
            s = str(row[strat_col]).strip().lower().replace(" ", "_")
            # Map common strategy-name variants
            s = {
                "guardian_gold": "guardian", "guardian": "guardian",
                "striker_dj30": "striker_dj30", "striker": "striker_dj30",
                "striker_nas100": "striker_nas", "striker_nas": "striker_nas",
                "aegis": "aegis", "aegis_reversion": "aegis",
            }.get(s, s)
            out[(d, s)] = str(row[note_col]).strip()
        except (ValueError, TypeError, KeyError):
            continue
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_backtest_args(args: list[str]) -> dict:
    """Parse --backtest entries of form 'strategy:csv_path'."""
    out = {}
    for arg in args:
        if ":" not in arg:
            raise ValueError(f"Backtest arg must be 'strategy:path', got: {arg}")
        strat, path = arg.split(":", 1)
        if strat not in STRATEGIES:
            raise ValueError(f"Unknown strategy: {strat}. Valid: {list(STRATEGIES.keys())}")
        out[strat] = path
    return out


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--dxtrade", required=True, help="DXTrade fills export CSV")
    ap.add_argument("--backtest", required=True, nargs="+",
                    help="One or more 'strategy:csv_path' entries (e.g. guardian:guard.csv)")
    ap.add_argument("--start", required=True, help="Window start date YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="Window end date YYYY-MM-DD")
    ap.add_argument("--account", type=float, default=200_000.0,
                    help="Account size for context (default $200,000)")
    ap.add_argument("--feed", choices=["pepperstone", "oanda", "alchemy"],
                    default="pepperstone",
                    help="Backtest feed source (informs counterfactual haircut warning)")
    ap.add_argument("--journal", default=None,
                    help="Notion Trade Journal CSV export for rationale lookup")
    ap.add_argument("--macro-events", default=None,
                    help="JSON file with [{'date':'YYYY-MM-DD','label':'...'},...]; otherwise embedded calendar")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args(argv)

    start_d = datetime.strptime(args.start, "%Y-%m-%d").date()
    end_d = datetime.strptime(args.end, "%Y-%m-%d").date()
    if start_d > end_d:
        print("ERROR: --start is after --end", file=sys.stderr)
        return 2

    backtest_paths = parse_backtest_args(args.backtest)

    # Load
    fills_all = load_dxtrade(args.dxtrade)
    signals_all: list[Signal] = []
    for strat, path in backtest_paths.items():
        signals_all.extend(load_backtest(path, strat))

    # Filter to window
    fills = filter_to_window(fills_all, start_d, end_d, "close_time")
    signals = filter_to_window(signals_all, start_d, end_d, "exit_time")

    # Macro dates
    if args.macro_events:
        macro = json.load(open(args.macro_events))
        macro_dates = {datetime.strptime(m["date"], "%Y-%m-%d").date() for m in macro}
    else:
        macro_dates = {datetime.strptime(d, "%Y-%m-%d").date()
                       for d, _ in MACRO_EVENTS_2026}

    # Pair, classify, aggregate
    pairings = pair_signals_to_fills(signals, fills)
    result = aggregate(pairings, fills, signals, start_d, end_d, macro_dates)

    # Optional journal lookup
    journal_lookup = None
    if args.journal:
        journal_lookup = load_journal(args.journal)

    if args.feed == "oanda":
        print("NOTE: OANDA backtest CSV — counterfactual P&L may be 16-29% above Alchemy "
              "live (Guardian stop-proximity). Aegis/USDJPY broker-uniform. Apply haircut "
              "before treating ratio as actionable.\n")

    if args.json:
        out = {
            "window_start": str(result.window_start),
            "window_end": str(result.window_end),
            "n_signals": result.n_signals,
            "n_fills": result.n_fills,
            "counts": {k: v for k, v in result.counts.items() if k != "version_notes"},
            "version_mixed": result.version_mixed,
            "pnl_realized": result.pnl_realized,
            "pnl_counterfactual": result.pnl_counterfactual,
            "pnl_gap": result.pnl_gap,
            "edge_captured_ratio": result.edge_captured_ratio,
            "leakage_skips": result.leakage_skips,
            "leakage_discretion": result.leakage_discretion,
            "gain_offspec": result.gain_offspec,
            "watchlist": result.watchlist,
        }
        print(json.dumps(out, indent=2, default=str))
    else:
        print(format_review(result, journal_lookup))

    # Exit code: non-zero if execution flag fires (CI-friendly)
    if (result.pnl_counterfactual > 0
            and result.edge_captured_ratio < 0.80
            and not result.version_mixed):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
