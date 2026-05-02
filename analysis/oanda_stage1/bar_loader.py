"""OANDA 15-minute bar loader.

Bar CSVs are UTC ISO-8601 timestamps (`...Z`), columns time/open/high/low/close/volume.
This loader returns a DataFrame indexed by tz-naive UTC datetimes for compatibility
with downstream timestamp arithmetic (TV CSVs are tz-naive; pinning both to the same
naive convention avoids tz-aware/naive comparison errors).

The ".15M only" assumption is checked: if the median diff is not 15 minutes the loader
fails fast.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from lib.mvd import assert_min_rows, assert_window


BAR_PATHS = {
    "USDJPY":  "data/bar_data/USDJPY.csv",
    "XAUUSD":  "data/bar_data/XAUUSD.csv",
    "US30USD": "data/bar_data/US30USD.csv",
}


def load_oanda_bars(symbol: str, repo_root: str | Path = ".") -> pd.DataFrame:
    """Load OANDA 15M bars for `symbol`. Returns DataFrame indexed by tz-naive UTC time."""
    if symbol not in BAR_PATHS:
        raise AssertionError(f"Unknown symbol {symbol!r}; expected one of {list(BAR_PATHS)}")
    path = Path(repo_root) / BAR_PATHS[symbol]
    df = pd.read_csv(path)
    assert_min_rows(len(df), 50_000, label=f"OANDA bars {symbol}")

    df["time"] = pd.to_datetime(df["time"], utc=True).dt.tz_convert(None)
    df = df.set_index("time").sort_index()

    span_days = (df.index.max() - df.index.min()).days
    assert_window(
        df.index.min().to_pydatetime(),
        df.index.max().to_pydatetime(),
        expected_min_days=4 * 365 - 60,
        label=f"OANDA bars {symbol}",
        tolerance_days=60,
    )

    diffs = df.index.to_series().diff().dropna()
    median_min = diffs.median().total_seconds() / 60
    if median_min != 15:
        raise AssertionError(
            f"OANDA bars {symbol}: median bar interval {median_min} min, expected 15 min"
        )

    return df
