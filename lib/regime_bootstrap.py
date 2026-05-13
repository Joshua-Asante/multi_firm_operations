"""Block bootstrap + half-panel diagnostics for daily Net P&L series.

Cap-free generalization of ``archive/analysis/Q-DJ30-2/regime_bootstrap.py``:
operates on an **OOS-stitched** (or arbitrary) daily P&L ``pd.Series`` indexed
by date — no per-trade caps or DJ30-specific loaders.

Typical use: Q-CORR-1.2 regime gate on stitched OOS daily returns.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def compute_pf(pnls: np.ndarray | list[float]) -> float:
    arr = np.asarray(pnls, dtype=float)
    pos = arr[arr > 0].sum()
    neg = arr[arr < 0].sum()
    return float(pos / abs(neg)) if neg < 0 else float("inf")


def compute_p99_dd_pct(pnls: np.ndarray | list[float], *, notional: float) -> float:
    """Underwater curve vs running peak, as % of *notional* (DD gate style)."""
    eq = np.cumsum(np.asarray(pnls, dtype=float))
    peaks = np.maximum.accumulate(eq)
    dd = (peaks - eq) / float(notional)
    return float(np.percentile(dd, 99) * 100.0)


def _month_block_id(ts: pd.Timestamp, anchor: pd.Timestamp, block_months: int) -> int:
    months = (ts.year - anchor.year) * 12 + (ts.month - anchor.month)
    return int(months // block_months)


@dataclass
class RegimeBootstrapResult:
    full_pf: float
    full_p99_dd_pct: float
    p05_pf: float
    p50_pf: float
    p95_pf: float
    p05_p99_dd_pct: float
    p95_p99_dd_pct: float
    n_blocks: int
    n_days: int
    half_pf_low: float
    half_pf_high: float
    half_pf_spread_rel_pct: float


def regime_bootstrap_daily_pnl(
    daily_pnl: pd.Series,
    *,
    n_panels: int = 100,
    block_months: int = 6,
    seed: int = 42,
    notional: float = 200_000.0,
) -> RegimeBootstrapResult:
    """6-month block bootstrap on *daily* P&L (chronological index).

    Resamples whole calendar blocks with replacement until the concatenated
    series reaches ``n_days`` (length of input), then truncates — mirrors the
    trade-count bootstrap shape from Q-DJ30-2 but on daily bars.
    """
    s = daily_pnl.sort_index().astype(float)
    if not s.index.is_unique:
        s = s.groupby(level=0).sum()
    idx = pd.DatetimeIndex(s.index)
    s.index = idx
    n_days = int(len(s))
    if n_days < 2:
        raise ValueError("daily_pnl must contain at least 2 days")

    anchor = s.index.min()
    block_ids = np.array([_month_block_id(t, anchor, block_months) for t in s.index], dtype=int)
    unique_blocks = sorted({int(x) for x in block_ids.tolist()})
    block_to_pnls: dict[int, list[float]] = {}
    for b in unique_blocks:
        mask = block_ids == b
        block_to_pnls[b] = s.values[mask].tolist()

    n_blocks = len(unique_blocks)
    full_pnls = s.values.astype(float)
    full_pf = compute_pf(full_pnls)
    full_p99 = compute_p99_dd_pct(full_pnls, notional=notional)

    rng = np.random.default_rng(seed)
    boot_pf: list[float] = []
    boot_p99: list[float] = []
    for _ in range(n_panels):
        sampled: list[float] = []
        while len(sampled) < n_days:
            b = int(rng.choice(unique_blocks))
            sampled.extend(block_to_pnls[b])
        sampled = sampled[:n_days]
        boot_pf.append(compute_pf(np.asarray(sampled, dtype=float)))
        boot_p99.append(compute_p99_dd_pct(sampled, notional=notional))

    boot_pf_arr = np.asarray(boot_pf, dtype=float)
    boot_p99_arr = np.asarray(boot_p99, dtype=float)

    mid = n_days // 2
    h1 = full_pnls[:mid]
    h2 = full_pnls[mid:]
    pf_h1 = compute_pf(h1)
    pf_h2 = compute_pf(h2)
    spread_abs = abs(pf_h1 - pf_h2)
    mid_pf = (pf_h1 + pf_h2) / 2.0
    spread_rel_pct = float(100.0 * spread_abs / mid_pf) if mid_pf else 0.0

    return RegimeBootstrapResult(
        full_pf=full_pf,
        full_p99_dd_pct=full_p99,
        p05_pf=float(np.percentile(boot_pf_arr, 5)),
        p50_pf=float(np.percentile(boot_pf_arr, 50)),
        p95_pf=float(np.percentile(boot_pf_arr, 95)),
        p05_p99_dd_pct=float(np.percentile(boot_p99_arr, 5)),
        p95_p99_dd_pct=float(np.percentile(boot_p99_arr, 95)),
        n_blocks=n_blocks,
        n_days=n_days,
        half_pf_low=min(pf_h1, pf_h2),
        half_pf_high=max(pf_h1, pf_h2),
        half_pf_spread_rel_pct=spread_rel_pct,
    )
