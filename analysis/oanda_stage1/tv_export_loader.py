"""TradingView strategy-export CSV loader.

The TV export emits two rows per trade (one Entry long, one Exit long, paired
by Trade #). This module pairs them and returns a per-trade DataFrame.

Pyramid-aware (Striker NAS100 v1+): pyramid add legs receive their own Trade #
in the TV export. They pair the same way as base trades; the `leg_type` column
distinguishes `base` from `pyramid_add` via the Signal text ("Long" vs "Long Add").

Columns returned:
    trade_num, signal_entry, signal_exit, side, leg_type,
    entry_ts, entry_px, exit_ts, exit_px, qty,
    net_pnl_usd, net_pnl_pct, mfe_usd, mfe_pct, mae_usd, mae_pct,
    cum_pnl_usd, cum_pnl_pct

`side` is +1 for long, -1 for short. All four locked strategies are long-only
at v5.5 / v4.5 / v4.3 / v1 — short rows would be a load-bearing surprise.

Identity gates via `lib.mvd.assert_tv_export` are applied at the public
loader entry point.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from lib.mvd import assert_min_rows, assert_tv_export


PRICE_COL_BY_INSTRUMENT = {
    "USDJPY":  "Price JPY",
    "XAUUSD":  "Price USD",
    "XAGUSD":  "Price USD",
    "US30USD": "Price USD",
    "US30":    "Price USD",
    "NAS100":  "Price USD",
}


def pair_tv_export_dataframe(
    raw: pd.DataFrame,
    *,
    expected_symbol: str,
    min_raw_rows: int = 100,
    source_label: str = "",
) -> pd.DataFrame:
    """Pair Entry/Exit TV rows into per-trade rows without filename identity checks.

    Used by WFO ``ingest`` for custom ``Silver_*`` filenames while reusing the same
    column contract as :func:`load_tv_export`.
    """
    label = source_label or "TV-export"
    assert_min_rows(len(raw), min_raw_rows, label=f"{label} rows")

    price_col = PRICE_COL_BY_INSTRUMENT[expected_symbol]
    if price_col not in raw.columns:
        raise AssertionError(
            f"TV-export schema fail [{label}]: expected price column '{price_col}' "
            f"for symbol {expected_symbol}, columns={list(raw.columns)}"
        )

    raw = raw.copy()
    raw["Date and time"] = pd.to_datetime(raw["Date and time"])

    entries = raw[raw["Type"].str.startswith("Entry")].copy()
    exits = raw[raw["Type"].str.startswith("Exit")].copy()
    if len(entries) != len(exits):
        raise AssertionError(
            f"TV-export pairing fail [{label}]: "
            f"{len(entries)} entries vs {len(exits)} exits"
        )

    entries = entries.set_index("Trade #")
    exits = exits.set_index("Trade #")
    if not entries.index.equals(exits.index):
        raise AssertionError(
            f"TV-export pairing fail [{label}]: "
            f"Trade # index mismatch between entry and exit rows"
        )

    side = entries["Type"].map(lambda t: 1 if "long" in t.lower() else -1)
    if (side != 1).any():
        raise AssertionError(
            f"TV-export side fail [{label}]: non-long entries present"
        )

    leg_type = entries["Signal"].map(
        lambda s: "pyramid_add" if "add" in str(s).lower() else "base"
    )

    out = pd.DataFrame({
        "trade_num":     entries.index,
        "signal_entry":  entries["Signal"].values,
        "signal_exit":   exits["Signal"].values,
        "side":          side.values,
        "leg_type":      leg_type.values,
        "entry_ts":      entries["Date and time"].values,
        "entry_px":      entries[price_col].values,
        "exit_ts":       exits["Date and time"].values,
        "exit_px":       exits[price_col].values,
        "qty":           entries["Size (qty)"].values,
        "net_pnl_usd":   entries["Net P&L USD"].values,
        "net_pnl_pct":   entries["Net P&L %"].values,
        "mfe_usd":       entries["Favorable excursion USD"].values,
        "mfe_pct":       entries["Favorable excursion %"].values,
        "mae_usd":       entries["Adverse excursion USD"].values,
        "mae_pct":       entries["Adverse excursion %"].values,
        "cum_pnl_usd":   entries["Cumulative P&L USD"].values,
        "cum_pnl_pct":   entries["Cumulative P&L %"].values,
    })
    return out.reset_index(drop=True)


def load_tv_export(
    csv_path: str | Path,
    *,
    expected_strategy: str,
    expected_version: str,
    expected_symbol: str,
    expected_broker: str = "OANDA",
) -> pd.DataFrame:
    """Load a TV export, pair entry/exit rows, return a per-trade DataFrame.

    Identity (filename → strategy/version/broker/symbol) is asserted via
    `lib.mvd.assert_tv_export` before any rows are read.
    """
    csv_path = Path(csv_path)
    assert_tv_export(
        csv_path,
        expected_strategy=expected_strategy,
        expected_version=expected_version,
        expected_broker=expected_broker,
        expected_symbol=expected_symbol,
    )

    raw = pd.read_csv(csv_path, encoding="utf-8-sig")
    return pair_tv_export_dataframe(
        raw,
        expected_symbol=expected_symbol,
        min_raw_rows=100,
        source_label=csv_path.name,
    )
