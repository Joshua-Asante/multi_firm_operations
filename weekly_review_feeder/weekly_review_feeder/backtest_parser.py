"""Pepperstone backtest CSV parser — week-range filter and aggregation.

These CSVs are the canonical 'List of trades' exports from TradingView for each
locked strategy, on Pepperstone feed. Convention: per-strategy file at
data/tv_exports/pepperstone/{strategy}.csv.

TradingView 'List of trades' format typically has paired Entry/Exit rows. We
group by Trade # and compute per-trade P&L from the Exit row's Net P&L.
"""
from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from .config import INTERNAL_STRATEGY_KEYS, Paths


# Common column aliases seen across TV exports
DATETIME_COL_ALIASES = ("Date and time", "Date/Time", "DateTime", "Date")
NET_PNL_COL_ALIASES = ("Net P&L USD", "Net P&L $", "Net P&L", "P&L")
TRADE_NUM_COL_ALIASES = ("Trade #", "Trade", "Trade number")
TYPE_COL_ALIASES = ("Type", "Side")
PRICE_COL_ALIASES = ("Price USD", "Price $", "Price")
SIZE_COL_ALIASES = ("Quantity", "Position size", "Size", "Contracts")


def _resolve_col(df: pd.DataFrame, aliases: tuple[str, ...]) -> str | None:
    for a in aliases:
        if a in df.columns:
            return a
    return None


def _to_float(series: pd.Series) -> pd.Series:
    """Coerce a possibly-string column with currency suffixes to float."""
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace(" USD", "", regex=False)
        .str.replace("USD", "", regex=False)
        .str.strip()
        .replace({"": None, "—": None, "-": None, "nan": None}),
        errors="coerce",
    )


def parse_pepperstone_csv(path: str) -> pd.DataFrame:
    """Parse a Pepperstone backtest CSV. Returns one row per trade (paired exits).

    Columns: trade_num, entry_time, exit_time, entry_price, exit_price,
             size, net_pnl
    Missing columns gracefully degrade (price/size NaN, net_pnl 0).
    """
    df = pd.read_csv(path)

    dt_col = _resolve_col(df, DATETIME_COL_ALIASES)
    pnl_col = _resolve_col(df, NET_PNL_COL_ALIASES)
    trade_col = _resolve_col(df, TRADE_NUM_COL_ALIASES)
    type_col = _resolve_col(df, TYPE_COL_ALIASES)
    price_col = _resolve_col(df, PRICE_COL_ALIASES)
    size_col = _resolve_col(df, SIZE_COL_ALIASES)

    if dt_col is None or pnl_col is None or trade_col is None or type_col is None:
        raise ValueError(
            f"Backtest CSV {path!r} missing required columns. "
            f"Have: {list(df.columns)}. "
            f"Need at least one of each: {DATETIME_COL_ALIASES}, "
            f"{NET_PNL_COL_ALIASES}, {TRADE_NUM_COL_ALIASES}, {TYPE_COL_ALIASES}"
        )

    df = df.copy()
    df["_ts"] = pd.to_datetime(df[dt_col], errors="coerce")
    df["_pnl"] = _to_float(df[pnl_col])
    df["_type_norm"] = df[type_col].astype(str).str.strip().str.lower()
    if price_col:
        df["_price"] = _to_float(df[price_col])
    else:
        df["_price"] = float("nan")
    if size_col:
        df["_size"] = _to_float(df[size_col])
    else:
        df["_size"] = float("nan")

    entries = df[
        df["_type_norm"].str.startswith("entry")
        | df["_type_norm"].isin(["long", "short", "buy", "sell"])
    ]
    exits = df[df["_type_norm"].str.startswith("exit")]

    if not exits.empty:
        # Two-row format: pair by trade_num
        e = entries[[trade_col, "_ts", "_price", "_size"]].rename(
            columns={"_ts": "entry_time", "_price": "entry_price", "_size": "size"}
        )
        x = exits[[trade_col, "_ts", "_pnl", "_price"]].rename(
            columns={"_ts": "exit_time", "_pnl": "net_pnl", "_price": "exit_price"}
        )
        merged = e.merge(x, on=trade_col, how="outer")
        merged.rename(columns={trade_col: "trade_num"}, inplace=True)
    else:
        # Single-row format
        merged = pd.DataFrame({
            "trade_num": df[trade_col],
            "entry_time": df["_ts"],
            "exit_time": df["_ts"],
            "entry_price": df["_price"],
            "exit_price": df["_price"],
            "size": df["_size"],
            "net_pnl": df["_pnl"],
        })

    # Fill missing P&L with 0 (entries-only rows)
    merged["net_pnl"] = merged["net_pnl"].fillna(0.0)
    return merged


def filter_to_week(
    df: pd.DataFrame, week_start: date, week_end: date, by: str = "entry_time"
) -> pd.DataFrame:
    """Filter trades to those whose entry_time (default) falls in the week."""
    if by not in df.columns or df.empty:
        return df.iloc[0:0]
    start = pd.Timestamp(week_start)
    end = pd.Timestamp(week_end) + pd.Timedelta(days=1)
    return df[(df[by] >= start) & (df[by] < end)].copy()


def sum_pnl(df: pd.DataFrame) -> float:
    """Sum net_pnl over the trades."""
    if "net_pnl" not in df.columns or df.empty:
        return 0.0
    return float(df["net_pnl"].fillna(0.0).sum())


def count_signals(df: pd.DataFrame) -> int:
    """Number of distinct trade_nums (= signals fired in the period)."""
    if "trade_num" not in df.columns or df.empty:
        return 0
    return int(df["trade_num"].nunique())


def all_strategies_backtest(
    paths: Paths, week_start: date, week_end: date
) -> dict[str, dict[str, Any]]:
    """Read all 4 strategy backtest CSVs, filter to week, return per-strategy summary."""
    out: dict[str, dict[str, Any]] = {}
    for k in INTERNAL_STRATEGY_KEYS:
        path = paths.backtest_csv(k)
        try:
            full = parse_pepperstone_csv(path)
            week = filter_to_week(full, week_start, week_end)
            out[k] = {
                "trades": week,
                "pnl": sum_pnl(week),
                "signals_fired": count_signals(week),
            }
        except FileNotFoundError:
            out[k] = {
                "trades": pd.DataFrame(),
                "pnl": 0.0,
                "signals_fired": 0,
                "_warning": f"Backtest CSV not found at {path}",
            }
    return out
