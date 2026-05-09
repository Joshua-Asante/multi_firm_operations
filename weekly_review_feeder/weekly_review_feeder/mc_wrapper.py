"""portfolio_mc.py wrapper — composed Pattern A.

Returns the panel-wide weekly-P&L band ({p10, p50, p90}) from the locked
Pepperstone Jan 2022 – Apr 2026 panel by composing existing portfolio_mc helpers:

    load_trades(panel_csv) per strategy
        -> build_daily_panel(trades_by_strat, allocations)
        -> build_week_blocks(panel)            # (n_blocks, 5, n_strats)
        -> blocks.sum(axis=(1, 2))             # weekly P&L vector
        -> np.percentile([10, 50, 90])

Why composed instead of import-callable or subprocess:
    portfolio_mc.py exposes no week-range query (no `weekly_band(...)` function,
    no `--week-start`/`--week-end` CLI flags) and emits only full-history
    aggregates (pass/bust rates, p50/p95/p99 DD). The needed weekly-P&L band
    is not part of its current output surface, so the wrapper composes the
    existing public helpers rather than modifying portfolio_mc.

Why the band is panel-wide (week_start/week_end accepted but not filtered):
    The locked MC anchor is calibrated against the 52-month Pepperstone panel
    (~220 Mon-anchored 5-day blocks). Per-week conditioning would require
    same-week-of-year subsetting, which yields ~4 blocks per calendar week —
    too thin for stable percentiles. The (week_start, week_end) signature is
    preserved for forward compatibility (per-week conditioning + provenance);
    the current implementation ignores them. A test in tests/test_mc_wrapper.py
    pins this contract so any future re-introduction of week-filtering trips
    the test loudly.

1R-fallback guard:
    Mirrors compute_default_config's assertion (portfolio_mc.py:358). If any
    strategy's implied_1r falls back to median-loss (n<5 full stops), the band
    is silently miscalibrated by ~10pp (per user memory
    `portfolio_mc_1r_fallback_trap.md`). We refuse to return a band in that case.
"""
# WIRED 2026-05-09 against portfolio_mc.py SHA 8ad8921
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

import portfolio_mc  # noqa: E402  (loads dd_protection MVD pin at import)


def get_mc_band_for_week(
    week_start: date, week_end: date
) -> dict[str, float]:
    """Return {p10, p50, p90} of weekly P&L from the locked Pepperstone panel.

    The band is panel-wide (Pepperstone Jan 2022 – Apr 2026). week_start and
    week_end are accepted for signature stability and provenance; the current
    implementation does not filter blocks by date. See module docstring.
    """
    panels = portfolio_mc.PEPPERSTONE_PANELS
    panel_strats = tuple(panels.keys())

    trades_by_strat = {s: portfolio_mc.load_trades(panels[s]) for s in panel_strats}
    panel_allocs = {s: portfolio_mc.ALLOCATIONS[s] for s in panel_strats}

    panel, scale_info = portfolio_mc.build_daily_panel(trades_by_strat, panel_allocs)

    fellback = [s for s, info in scale_info.items() if info["fell_back"]]
    if fellback:
        raise RuntimeError(
            f"portfolio_mc implied_1r fell back to median for {fellback}; "
            f"band would be silently miscalibrated by ~10pp. "
            f"See user memory portfolio_mc_1r_fallback_trap.md."
        )

    blocks = portfolio_mc.build_week_blocks(panel)
    if blocks.size == 0:
        raise RuntimeError(
            f"build_week_blocks returned empty array; panel has "
            f"{len(panel)} bdays starting {panel.index.min()}."
        )

    weekly_pnl = blocks.sum(axis=(1, 2))
    p10, p50, p90 = np.percentile(weekly_pnl, [10, 50, 90])
    return {"p10": float(p10), "p50": float(p50), "p90": float(p90)}
