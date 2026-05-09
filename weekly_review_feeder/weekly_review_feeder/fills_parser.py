"""DXTrade fills CSV parser + per-strategy P&L aggregation + op-test heuristic."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import pandas as pd

from .config import (
    DAY_GATE,
    INTERNAL_STRATEGY_KEYS,
    SYMBOL_STRATEGY_MAP,
    day_name,
)


# ----------------------------------------------------------------------------
# DXTrade CSV column convention
# ----------------------------------------------------------------------------
# Confirmed from W19 fills export screenshot. If DXTrade adjusts headers, update here.
EXPECTED_COLUMNS = [
    "Date and Time",  # also seen as "Date/Time"
    "Symbol",
    "Order ID",
    "Trade Code",
    "Side",
    "Position effect",
    "Trade Volume",
    "Trade Price",
    "Commission",
    "Closed P&L",
    "Net Closed P&L",
]

# Allow either "Date and Time" or "Date/Time" (variants seen in exports)
DATETIME_COLUMN_ALIASES = ("Date and Time", "Date/Time", "DateTime")


@dataclass(frozen=True)
class FillRow:
    """Normalized fill row, post-parse."""
    timestamp: datetime
    symbol: str
    order_id: str
    trade_code: str
    side: str          # "Buy" / "Sell"
    effect: str        # "Opening" / "Closing"
    volume: float
    price: float
    commission: float
    closed_pnl: float | None
    net_closed_pnl: float | None
    strategy: str | None  # G / DJ30 / A / NAS / None if unmapped


def parse_dxtrade_csv(path: str) -> pd.DataFrame:
    """Parse DXTrade fills CSV into a normalized DataFrame.

    Returns DataFrame with columns:
      timestamp (datetime64), symbol, order_id, trade_code, side, effect,
      volume, price, commission, closed_pnl, net_closed_pnl, strategy
    """
    df = pd.read_csv(path)

    # Find the datetime column
    dt_col = next((c for c in DATETIME_COLUMN_ALIASES if c in df.columns), None)
    if dt_col is None:
        raise ValueError(
            f"Could not find datetime column in fills CSV. "
            f"Expected one of: {DATETIME_COLUMN_ALIASES}. Got: {list(df.columns)}"
        )

    # DXTrade's date format from W19 sample: "07/05/26 11:52" (DD/MM/YY HH:MM)
    # Try common variants; fail loudly if no parse works.
    for fmt in ("%d/%m/%y %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            ts = pd.to_datetime(df[dt_col], format=fmt)
            break
        except (ValueError, TypeError):
            continue
    else:
        # Last-resort dateutil parse
        ts = pd.to_datetime(df[dt_col])

    # Normalize column names; tolerate "Closed P&L" and "Net Closed P&L" being absent
    # (e.g. on Opening fills where P&L isn't realized yet).
    out = pd.DataFrame({
        "timestamp": ts,
        "symbol": df["Symbol"].astype(str).str.strip().str.upper(),
        "order_id": df.get("Order ID", "").astype(str),
        "trade_code": df.get("Trade Code", "").astype(str),
        "side": df.get("Side", "").astype(str).str.strip(),
        "effect": df.get("Position effect", "").astype(str).str.strip(),
        "volume": pd.to_numeric(df.get("Trade Volume"), errors="coerce"),
        "price": pd.to_numeric(df.get("Trade Price"), errors="coerce"),
        "commission": pd.to_numeric(df.get("Commission"), errors="coerce").fillna(0.0),
        "closed_pnl": pd.to_numeric(df.get("Closed P&L"), errors="coerce"),
        "net_closed_pnl": pd.to_numeric(df.get("Net Closed P&L"), errors="coerce"),
    })

    # Strategy mapping
    out["strategy"] = out["symbol"].map(SYMBOL_STRATEGY_MAP)

    return out


def filter_to_week(df: pd.DataFrame, week_start: date, week_end: date) -> pd.DataFrame:
    """Filter fills to the inclusive [week_start, week_end] date range."""
    start = pd.Timestamp(week_start)
    end = pd.Timestamp(week_end) + pd.Timedelta(days=1)  # exclusive upper bound
    return df[(df["timestamp"] >= start) & (df["timestamp"] < end)].copy()


def per_strategy_pnl(
    df: pd.DataFrame, exclude_op_tests: bool = True, op_test_order_ids: set[str] | None = None
) -> dict[str, float]:
    """Sum Net Closed P&L per strategy. Closing fills only (Net Closed P&L is non-null only on closes).

    Op-test trades are excluded from per-strategy attribution by default.
    Returns dict with keys G, DJ30, A, NAS — zeros for strategies with no fills.
    """
    out = {k: 0.0 for k in INTERNAL_STRATEGY_KEYS}
    if exclude_op_tests and op_test_order_ids:
        df = df[~df["order_id"].isin(op_test_order_ids)]
    closes = df[df["effect"].str.lower() == "closing"]
    for strat, group in closes.groupby("strategy", dropna=True):
        if strat in out:
            out[strat] = float(group["net_closed_pnl"].fillna(0.0).sum())
    return out


def detect_op_test_order_ids(
    fills_df: pd.DataFrame,
    ptl_entries: list[dict[str, Any]],
) -> set[str]:
    """Heuristic op-test detection (v0.1, pre-INT-1).

    Flags a fill's order_id as op-test when ALL of:
      (a) No PTL entry references the same Linked DXTrade ID, AND
      (b) The fill is on a non-session day for the symbol's strategy.

    When INT-1 lands a signal_type field on PTL, this is replaced by direct
    field check. For now: conservative (over-excludes is safer than under-excludes).
    """
    ptl_dxtrade_ids: set[str] = {
        e.get("linked_dxtrade_id", "").strip()
        for e in ptl_entries
        if e.get("linked_dxtrade_id")
    }
    op_test_order_ids: set[str] = set()
    for _, row in fills_df.iterrows():
        order_id = str(row["order_id"]).strip()
        if not order_id:
            continue
        strategy = row["strategy"]
        if strategy is None or pd.isna(strategy):
            continue
        # If this order is referenced in PTL, it's a strategy signal — not op-test.
        if order_id in ptl_dxtrade_ids:
            continue
        # If we're on a session day for this strategy, default to strategy-attribution
        # (assume PTL entry just hasn't been linked yet).
        # If we're on a NON-session day, flag as op-test.
        ts = row["timestamp"]
        if isinstance(ts, pd.Timestamp):
            ts_date = ts.date()
        else:
            ts_date = ts
        dn = day_name(ts_date)
        if strategy not in DAY_GATE.get(dn, frozenset()):
            op_test_order_ids.add(order_id)
    return op_test_order_ids


def realized_pnl_total(
    df: pd.DataFrame, op_test_order_ids: set[str] | None = None
) -> float:
    """Total realized P&L for the week, excluding op-test trades."""
    if op_test_order_ids:
        df = df[~df["order_id"].isin(op_test_order_ids)]
    closes = df[df["effect"].str.lower() == "closing"]
    return float(closes["net_closed_pnl"].fillna(0.0).sum())


def op_test_summary(
    df: pd.DataFrame, op_test_order_ids: set[str]
) -> list[dict[str, Any]]:
    """Return summary of detected op-test ROUND-TRIP trades for provenance.

    A round-trip = open + close pair for the same symbol on the same calendar day.
    Aggregates net P&L from the closing fill(s); reports one entry per round-trip.
    """
    if not op_test_order_ids:
        return []
    flagged = df[df["order_id"].isin(op_test_order_ids)].copy()
    if flagged.empty:
        return []
    flagged["_date"] = flagged["timestamp"].apply(
        lambda x: x.date() if hasattr(x, "date") else x
    )
    out: list[dict[str, Any]] = []
    for (symbol, d), group in flagged.groupby(["symbol", "_date"], sort=True):
        opens = group[group["effect"].str.lower() == "opening"].sort_values("timestamp")
        closes = group[group["effect"].str.lower() == "closing"].sort_values("timestamp")
        first_ts = group["timestamp"].min()
        net_pnl = float(closes["net_closed_pnl"].fillna(0.0).sum())
        order_ids = sorted(group["order_id"].unique().tolist())
        out.append({
            "symbol": str(symbol),
            "date": d.isoformat(),
            "first_timestamp": first_ts.isoformat() if hasattr(first_ts, "isoformat") else str(first_ts),
            "order_ids": order_ids,
            "n_opens": int(len(opens)),
            "n_closes": int(len(closes)),
            "net_pnl": round(net_pnl, 2),
            "reason": "non-session day + no PTL link",
        })
    return out
