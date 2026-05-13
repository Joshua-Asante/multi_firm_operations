"""Daily Net P&L correlation helpers (Q-CORR gate semantics).

Aligned-calendar Pearson with **zero-fill** for non-trade days (Q-CORR-1.1 §7
amendment). Refactored from ``archive/analysis/eurusd_lnyo/correlation.py``,
which used ``pd.concat(..., join="inner")`` for conditional slices.

Exit-date attribution: only rows whose ``Type`` starts with ``Exit``;
``Net P&L USD`` summed per calendar day (normalized midnight).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def load_exit_date_daily_net(csv_path: str | Path) -> pd.Series:
    """Load TV trade-history CSV; return daily Net P&L indexed by exit date."""
    path = Path(csv_path)
    df = pd.read_csv(path, encoding="utf-8-sig")
    exits = df[df["Type"].astype(str).str.startswith("Exit")].copy()
    exits["exit_date"] = pd.to_datetime(exits["Date and time"]).dt.normalize()
    exits = exits.rename(columns={"Net P&L USD": "pnl"})
    out = exits.groupby("exit_date")["pnl"].sum()
    out.name = path.stem
    return out


def align_two_daily_series_zero_fill(
    a: pd.Series, b: pd.Series
) -> tuple[pd.Series, pd.Series]:
    """Reindex both series to all business days from min(date) to max(date), zero-fill."""
    start = min(a.index.min(), b.index.min())
    end = max(a.index.max(), b.index.max())
    idx = pd.bdate_range(start, end)
    a2 = a.reindex(idx).fillna(0.0).astype(float)
    b2 = b.reindex(idx).fillna(0.0).astype(float)
    return a2, b2


def pearson_daily_series(a: pd.Series, b: pd.Series) -> float:
    """Pearson r on aligned, zero-filled daily P&L (full union index)."""
    a2, b2 = align_two_daily_series_zero_fill(a, b)
    if len(a2) < 2:
        return float("nan")
    x = a2.values.astype(float)
    y = b2.values.astype(float)
    if np.std(x, ddof=0) == 0 or np.std(y, ddof=0) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def pearson_daily_pnl(csv_a: str | Path, csv_b: str | Path) -> float:
    """Pearson r between two TV-export CSVs on daily Net P&L (zero-filled)."""
    sa = load_exit_date_daily_net(csv_a)
    sb = load_exit_date_daily_net(csv_b)
    return pearson_daily_series(sa, sb)
