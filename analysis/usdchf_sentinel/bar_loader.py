"""USDCHF H4 bar loader for the Sentinel gate.

Sources data/bar_data/USDCHF_pepperstone_h4_2020-06-25_to_2026-05-03.csv
(Pepperstone TV export, mid-OHLC). Slices to the calibration window
2022-01-04 -> 2026-04-20 to match the locked-MC scope (parent brief
Pre-Q-D step). Drops the file's last bar — it was a forming bar at
export time (cross-validated against two redundant exports; only close
+ volume disagreed on the final timestamp).

MVD assertions:
  - rows >= 6000 in calibration window (4yr H4 weekday floor ~6500)
  - window span >= 1500 days (calibration window is 1567)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from lib.mvd import assert_min_rows, assert_window


REPO_ROOT = Path(__file__).parent.parent.parent
BAR_PATH = REPO_ROOT / "data" / "bar_data" / "USDCHF_pepperstone_h4_2020-06-25_to_2026-05-03.csv"

# Calibration-window scope (parent brief Pre-Q-D)
WINDOW_START = pd.Timestamp("2022-01-04", tz="UTC")
WINDOW_END = pd.Timestamp("2026-04-20 23:59:59", tz="UTC")


def load_usdchf_h4(
    *,
    path: Path = BAR_PATH,
    window_start: pd.Timestamp = WINDOW_START,
    window_end: pd.Timestamp = WINDOW_END,
) -> pd.DataFrame:
    """Load Pepperstone USDCHF H4 mid-OHLC bars sliced to the calibration window.

    Returns a DataFrame indexed by tz-aware UTC bar-open timestamp, columns
    ['open', 'high', 'low', 'close', 'volume']. Forming-bar (last row of
    raw file) is dropped.
    """
    raw = pd.read_csv(path)
    raw["ts"] = pd.to_datetime(raw["time"], unit="s", utc=True)
    raw = raw.rename(columns={"Volume": "volume"})

    # Drop forming bar (last row of raw export — verified at import time)
    raw = raw.iloc[:-1].copy()

    raw = raw.set_index("ts").sort_index()
    bars = raw.loc[(raw.index >= window_start) & (raw.index <= window_end),
                   ["open", "high", "low", "close", "volume"]]

    assert_min_rows(len(bars), 6000, label="USDCHF H4 calibration window")
    assert_window(
        bars.index[0].to_pydatetime(),
        bars.index[-1].to_pydatetime(),
        expected_min_days=1500,
        label="USDCHF H4 calibration window",
    )
    return bars


if __name__ == "__main__":
    bars = load_usdchf_h4()
    print(f"Loaded {len(bars):,} H4 bars")
    print(f"  span: {bars.index[0]} -> {bars.index[-1]}")
    print(f"  cols: {list(bars.columns)}")
    print(f"  head:")
    print(bars.head(3))
