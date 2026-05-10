"""
portfolio_mc — challenge-outcome simulator (single-tier)
========================================================
Answers one question: given the locked strategies and DD-protection config,
what is the challenge pass/bust distribution?

Not in scope: per-strategy diagnostics, allocation tuning, live integration.
See the FINAL decision page: https://www.notion.so/346dc0b53c11816085bbf2292be934cc

Invocation (top-level module — pyproject declares flat py-modules, no
package namespace):
    python portfolio_mc.py                                 # default run (Pepperstone)
    python portfolio_mc.py --historical                    # deterministic
    python portfolio_mc.py --sensitivity                   # DD-trigger grid
    python portfolio_mc.py --panel oanda                   # pattern-spotting proxy
    python portfolio_mc.py --dd-trigger 0.01 --dd-scale 0.40
    python portfolio_mc.py --no-protection
    python portfolio_mc.py --guardian-risk 0.0025          # what-if at reduced Guardian risk
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

try:
    from .dd_protection import DD_TRIGGER, DD_SCALE
    from .lib.mvd import assert_min_rows, assert_window, assert_no_fallback, assert_tv_export
except ImportError:
    from dd_protection import DD_TRIGGER, DD_SCALE
    from lib.mvd import assert_min_rows, assert_window, assert_no_fallback, assert_tv_export

STARTING_EQUITY = 200_000
PROFIT_TARGET = 210_000
DAILY_LOSS_PCT = -0.05
STATIC_DD_PCT = -0.05
MIN_TRADING_DAYS = 5
HORIZON_DAYS = 150
SIMS_PER_SEED = 10_000
SEEDS = (42, 123, 2026)

ALLOCATIONS: Dict[str, float] = {
    "guardian":       0.0034,
    "striker":        0.0100,
    "aegis":          0.0150,
    "striker_nas100": 0.0040,
}
STRATS = tuple(ALLOCATIONS.keys())

# Filename token used by the MVD identity gate. Both Striker variants (DJ30 + NAS100)
# share the "Striker" strategy token; differentiation is via symbol (US30 vs NAS100).
STRATEGY_FILENAME_TOKEN: Dict[str, str] = {
    "guardian":       "Guardian",
    "striker":        "Striker",
    "aegis":          "Aegis",
    "striker_nas100": "Striker",
}

OANDA_DIR = Path(__file__).parent / "data" / "tv_exports" / "oanda"
OANDA_PANELS: Dict[str, Path] = {
    "guardian": OANDA_DIR / "Guardian_Gold_v5.5_OANDA_XAUUSD_2026-04-25_9ae1f.csv",
    "striker":  OANDA_DIR / "Striker_DJ30_v4.4_OANDA_US30USD_2026-04-25_86e9d.csv",
    "aegis":    OANDA_DIR / "Aegis_USDJPY_v4.3_OANDA_USDJPY_2026-04-25_7ee6b.csv",
    # No OANDA NAS100 panel — striker_nas100 is Pepperstone-only at the v1 add.
}

PEPPERSTONE_DIR = Path(__file__).parent / "data" / "tv_exports" / "pepperstone"
PEPPERSTONE_PANELS: Dict[str, Path] = {
    "guardian":       PEPPERSTONE_DIR / "Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-05_33781.csv",
    "striker":        PEPPERSTONE_DIR / "Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv",
    "aegis":          PEPPERSTONE_DIR / "Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-04-26_0bf1b.csv",
    "striker_nas100": PEPPERSTONE_DIR / "Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-05_7ca6f.csv",
}

# Pepperstone is the CLAUDE.md canonical lock anchor; OANDA is the pattern-spotting proxy
# (per 2026-04-26 commit 59dddb3 + two-tier canonical rule).
PANELS_BY_BROKER: Dict[str, Dict[str, Path]] = {
    "pepperstone": PEPPERSTONE_PANELS,
    "oanda":       OANDA_PANELS,
}

# Symbol field varies per broker (Pepperstone uses US30, OANDA uses US30USD for DJ30).
EXPECTED_SYMBOLS_BY_BROKER: Dict[str, Dict[str, str]] = {
    "pepperstone": {"guardian": "XAUUSD", "striker": "US30",    "aegis": "USDJPY", "striker_nas100": "NAS100"},
    "oanda":       {"guardian": "XAUUSD", "striker": "US30USD", "aegis": "USDJPY"},
}

# Version expectations vary per broker (Pepperstone migrated to DJ30 v4.5 on 2026-05-05;
# OANDA still on v4.4 until a fresh OANDA v4.5 fetch lands).
EXPECTED_VERSIONS_BY_BROKER: Dict[str, Dict[str, str]] = {
    "pepperstone": {"guardian": "v5.5", "striker": "v4.5", "aegis": "v4.3", "striker_nas100": "v1"},
    "oanda":       {"guardian": "v5.5", "striker": "v4.4", "aegis": "v4.3"},
}

DEFAULT_PANEL = "pepperstone"


# ── Data pipeline ─────────────────────────────────────────────────────────

def load_trades(path: Path) -> pd.DataFrame:
    """Load TV List-of-Trades CSV. Return DataFrame with ['exit_date', 'pnl']
    for exit rows only (P&L is carried identically on entry+exit; we use exit
    for timing)."""
    df = pd.read_csv(path, encoding="utf-8-sig")
    # MVD cardinality — catches OANDA short-fetch class (audit instance #2).
    # Floor at 100 raw rows: panels are entry+exit pairs, so 100 ≈ 50 trades,
    # well below any plausible 4yr canonical panel.
    assert_min_rows(len(df), 100, label=f"MC input panel {path.name}")
    exits = df[df["Type"].astype(str).str.startswith("Exit")].copy()
    exits["exit_date"] = pd.to_datetime(exits["Date and time"]).dt.normalize()
    exits = exits.rename(columns={"Net P&L USD": "pnl"})
    out = exits[["exit_date", "pnl"]].sort_values("exit_date").reset_index(drop=True)
    if not out.empty:
        # MVD window — catches "4yr panel actually 14mo" class (audit instance #8).
        assert_window(
            out["exit_date"].iloc[0].to_pydatetime(),
            out["exit_date"].iloc[-1].to_pydatetime(),
            expected_min_days=4 * 365,
            label=f"MC input panel {path.name}",
            tolerance_days=60,
        )
    return out


def implied_1r(pnl: pd.Series, strategy: str,
               account: float = STARTING_EQUITY) -> Tuple[float, bool]:
    """Implied 1R in dollars. Returns (r1, fell_back).

    Guardian: median loss (pure trend-rider, no BE) — by design, fell_back=False.
    Striker/Aegis: mean of |losses| > 1% of account (full-stop cohort).
    Falls back to median if fewer than 5 full stops — fell_back=True.

    The fallback path is the silent-trigger case named in audit instance #1
    (user memory `portfolio_mc_1r_fallback_trap.md`). It can swing MC by ~10pp.
    Callers must `assert_no_fallback` on the aggregated count for any
    canonical run.
    """
    abs_losses = pnl[pnl < 0].abs()
    if strategy == "guardian":
        return float(abs_losses.median()), False
    full_stops = abs_losses[abs_losses > 0.01 * account]
    if len(full_stops) < 5:
        return float(abs_losses.median()), True
    return float(full_stops.mean()), False


def build_daily_panel(trades_by_strat: Dict[str, pd.DataFrame],
                      allocations: Dict[str, float]) -> Tuple[pd.DataFrame, Dict[str, dict]]:
    """Scale each strategy's realized P&L so 1R maps to allocation × $200K, then
    aggregate to a business-day panel."""
    scale_info: Dict[str, dict] = {}
    series = []
    for strat, trades in trades_by_strat.items():
        r1, fell_back = implied_1r(trades["pnl"], strat)
        target_dollars = allocations[strat] * STARTING_EQUITY
        scale = target_dollars / r1 if r1 > 0 else 1.0
        scale_info[strat] = {
            "implied_1r": r1,
            "scale": scale,
            "n_trades": len(trades),
            "fell_back": fell_back,
        }
        s = trades.groupby("exit_date")["pnl"].sum() * scale
        s.name = strat
        series.append(s)
    panel = pd.concat(series, axis=1, sort=True).fillna(0.0)
    bdays = pd.bdate_range(panel.index.min(), panel.index.max())
    return panel.reindex(bdays).fillna(0.0), scale_info


def build_week_blocks(panel: pd.DataFrame) -> np.ndarray:
    """Mon-anchored non-overlapping 5-day blocks. Returns shape (n_blocks, 5, n_strats)."""
    vals = panel.values  # (n_days, n_strats)
    blocks = []
    for i, d in enumerate(panel.index):
        if d.weekday() == 0 and i + 5 <= len(panel):
            blocks.append(vals[i:i + 5])
    return np.array(blocks)


# ── Simulation ────────────────────────────────────────────────────────────

def _simulate_path(path: np.ndarray, dd_trigger: float, dd_scale: float,
                   horizon: int) -> Tuple[str, int, float, int | None]:
    """Run one deterministic sim over a (horizon, n_strats) path.
    Returns (outcome, day_terminated, max_dd, culprit_strat_idx)."""
    eq = peak = float(STARTING_EQUITY)
    trade_days = 0
    max_dd = 0.0

    for day in range(horizon):
        dd_from_peak = (eq - peak) / peak if peak > 0 else 0.0
        # ULP-precision rounding before threshold compare; see Q-MCFP-1
        scale = dd_scale if round(dd_from_peak, 6) <= -dd_trigger else 1.0
        strat_pnls = path[day] * scale
        pnl = float(strat_pnls.sum())
        eq_new = eq + pnl

        if round(pnl / STARTING_EQUITY, 6) <= DAILY_LOSS_PCT:
            return "bust_daily", day + 1, max_dd, int(np.argmin(strat_pnls))
        if round((eq_new - STARTING_EQUITY) / STARTING_EQUITY, 6) <= STATIC_DD_PCT:
            return "bust_static", day + 1, max_dd, int(np.argmin(strat_pnls))

        eq = eq_new
        if eq > peak:
            peak = eq
        dd_now = (peak - eq) / peak if peak > 0 else 0.0
        if dd_now > max_dd:
            max_dd = dd_now
        if pnl != 0:
            trade_days += 1

        if round(eq, 2) >= PROFIT_TARGET and trade_days >= MIN_TRADING_DAYS:
            return "pass", day + 1, max_dd, None

    return "timeout", horizon, max_dd, None


def run_seed(seed: int, n_sims: int, blocks: np.ndarray,
             dd_trigger: float, dd_scale: float, horizon: int = HORIZON_DAYS,
             strats: Tuple[str, ...] = STRATS) -> dict:
    """Run n_sims bootstrap simulations for one seed.

    `strats` labels the path's column axis for bust attribution. Defaults to
    the global 4-tuple but callers (via `_load_all`) pass the panel-specific
    tuple — Pepperstone gets all 4, OANDA gets 3.
    """
    rng = np.random.default_rng(seed)
    n_blocks = len(blocks)
    blocks_per_sim = (horizon + 4) // 5

    outcomes = {"pass": 0, "bust_daily": 0, "bust_static": 0, "timeout": 0}
    days_to_pass: list[int] = []
    max_dds: list[float] = []
    bust_attrib = {s: 0 for s in strats}

    for _ in range(n_sims):
        idx = rng.integers(0, n_blocks, blocks_per_sim)
        path = np.concatenate([blocks[i] for i in idx])[:horizon]

        outcome, day, max_dd, culprit = _simulate_path(path, dd_trigger, dd_scale, horizon)
        outcomes[outcome] += 1
        max_dds.append(max_dd)
        if outcome == "pass":
            days_to_pass.append(day)
        elif outcome in ("bust_daily", "bust_static") and culprit is not None:
            bust_attrib[strats[culprit]] += 1

    return {
        "outcomes": outcomes,
        "days_to_pass": days_to_pass,
        "max_dds": max_dds,
        "bust_attribution": bust_attrib,
    }


# ── Reporting ─────────────────────────────────────────────────────────────

def _fmt_config(dd_trigger: float, dd_scale: float, no_protection: bool) -> str:
    if no_protection:
        return "no protection (--no-protection)"
    return f"DD {dd_trigger:.1%} / {dd_scale}× (single-tier)"


_ALLOC_LABEL = {
    "guardian":       "G",
    "striker":        "S",
    "aegis":          "A",
    "striker_nas100": "N",
}


def _fmt_alloc(allocs: Dict[str, float]) -> str:
    parts = [f"{_ALLOC_LABEL.get(s, s)} {v:.2%}" for s, v in allocs.items()]
    return " / ".join(parts)


def _serial_grid_with_progress(blocks: np.ndarray, all_trigs: list,
                                dd_scale: float,
                                strats: Tuple[str, ...] = STRATS) -> dict:
    """Run the sensitivity-grid serial path with a Rich progress bar when
    Rich is installed; fall back to plain iteration otherwise.

    The bar advances per (trig, seed) cell — granular feedback during a
    multi-minute run. Numerically inert: same loop, same SEEDS, same numbers.
    """
    try:
        from rich.progress import (
            BarColumn,
            MofNCompleteColumn,
            Progress,
            TextColumn,
            TimeElapsedColumn,
        )
    except ImportError:
        return {
            trig: [run_seed(seed, SIMS_PER_SEED, blocks, trig, dd_scale, strats=strats) for seed in SEEDS]
            for trig in all_trigs
        }

    out: dict = {trig: [] for trig in all_trigs}
    total_cells = len(all_trigs) * len(SEEDS)
    columns = [
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
    ]
    with Progress(*columns, transient=True) as progress:
        task = progress.add_task("Sensitivity grid", total=total_cells)
        for trig in all_trigs:
            for seed in SEEDS:
                out[trig].append(run_seed(seed, SIMS_PER_SEED, blocks, trig, dd_scale, strats=strats))
                progress.update(task, advance=1)
    return out


def _run_seeds(blocks: np.ndarray, effective_trigger: float, dd_scale: float,
               seeds=SEEDS, parallel: bool = False,
               strats: Tuple[str, ...] = STRATS) -> list:
    """Run all seeds. Sequential by default; joblib-parallel when requested.

    Each seed is independent (RNG seeded inside run_seed) so the parallel
    path is byte-identical to the sequential path. The seeds list is preserved
    in order so downstream aggregation is deterministic regardless of mode.
    """
    if not parallel:
        return [run_seed(seed, SIMS_PER_SEED, blocks, effective_trigger, dd_scale, strats=strats)
                for seed in seeds]
    try:
        from joblib import Parallel, delayed
    except ImportError as e:
        raise ImportError(
            "--parallel requires joblib. Install with: pip install -e .[mc]"
        ) from e
    return list(Parallel(n_jobs=len(seeds), backend="loky")(
        delayed(run_seed)(seed, SIMS_PER_SEED, blocks, effective_trigger, dd_scale, strats=strats)
        for seed in seeds
    ))


def compute_default_config(dd_trigger: float, dd_scale: float, no_protection: bool,
                           allocs: Dict[str, float],
                           panel_name: str = DEFAULT_PANEL,
                           parallel: bool = False) -> dict:
    """Pure compute path for default MC mode. Returns aggregated metrics dict.

    Consumed by mode_default (printout layered on top) and by tests/test_mc_anchors.py
    (anchor pinning). Numerically deterministic given fixed SEEDS = (42, 123, 2026)
    regardless of `parallel` mode.
    """
    trades_by_strat, panel, blocks, scale_info, panel_strats = _load_all(allocs, panel_name=panel_name)

    fallback_count = sum(1 for info in scale_info.values() if info["fell_back"])
    assert_no_fallback(
        fallback_count,
        label="portfolio_mc implied_1r (Striker/Aegis full-stop cohort)",
    )

    effective_trigger = 10.0 if no_protection else dd_trigger
    seeds_results = _run_seeds(blocks, effective_trigger, dd_scale, parallel=parallel,
                               strats=panel_strats)

    per_seed = SIMS_PER_SEED
    pass_r = [r["outcomes"]["pass"] / per_seed for r in seeds_results]
    bd_r   = [r["outcomes"]["bust_daily"] / per_seed for r in seeds_results]
    bs_r   = [r["outcomes"]["bust_static"] / per_seed for r in seeds_results]
    to_r   = [r["outcomes"]["timeout"] / per_seed for r in seeds_results]
    bust_r = [d + s for d, s in zip(bd_r, bs_r)]

    all_days = [d for r in seeds_results for d in r["days_to_pass"]]
    all_dds  = [d for r in seeds_results for d in r["max_dds"]]

    attrib = {s: sum(r["bust_attribution"][s] for r in seeds_results) for s in panel_strats}

    return {
        "panel_name": panel_name,
        "panel_start": panel.index.min(),
        "panel_end": panel.index.max(),
        "n_bdays": len(panel),
        "n_blocks": len(blocks),
        "panel_strats": panel_strats,
        "scale_info": scale_info,
        "seeds_results": seeds_results,
        "pass_rate": float(np.mean(pass_r)),
        "pass_sigma": float(np.std(pass_r)),
        "bust_rate": float(np.mean(bust_r)),
        "bust_sigma": float(np.std(bust_r)),
        "bust_daily_rate": float(np.mean(bd_r)),
        "bust_static_rate": float(np.mean(bs_r)),
        "timeout_rate": float(np.mean(to_r)),
        "median_days_to_pass": int(np.median(all_days)) if all_days else None,
        "p50_dd": float(np.percentile(all_dds, 50)),
        "p95_dd": float(np.percentile(all_dds, 95)),
        "p99_dd": float(np.percentile(all_dds, 99)),
        "bust_attribution": attrib,
    }


def report_default(result: dict, dd_trigger: float, dd_scale: float,
                   allocs: Dict[str, float], no_protection: bool):
    """Print the default MC output block from a compute_default_config() result."""
    n_seeds = len(result["seeds_results"])
    per_seed = SIMS_PER_SEED

    panel_strats = result.get("panel_strats", tuple(allocs.keys()))
    panel_allocs = {s: allocs[s] for s in panel_strats}

    print("=== Portfolio MC ===")
    print(f"Config: {_fmt_config(dd_trigger, dd_scale, no_protection)}")
    print(f"Allocations: {_fmt_alloc(panel_allocs)}")
    print(f"Sims: {per_seed:,} × {n_seeds} seeds, horizon {HORIZON_DAYS} days")
    print()
    print(f"Pass:         {result['pass_rate']:>6.2%} (sigma {result['pass_sigma']:.2%})")
    print(f"Bust:         {result['bust_rate']:>6.2%} (sigma {result['bust_sigma']:.2%})")
    print(f"  Daily:      {result['bust_daily_rate']:>6.2%}")
    print(f"  Static:     {result['bust_static_rate']:>6.2%}")
    print(f"Timeout:      {result['timeout_rate']:>6.2%}")
    if result["median_days_to_pass"] is not None:
        print(f"Median days to pass: {result['median_days_to_pass']}")
    print(f"p50 DD:       {result['p50_dd']:.2%}")
    print(f"p95 DD:       {result['p95_dd']:.2%}")
    print(f"p99 DD:       {result['p99_dd']:.2%}")
    print()
    print("Bust attribution:")
    total_busts = sum(result["bust_attribution"].values())
    if total_busts > 0:
        # Print in descending share order so the marginal contributor reads first.
        ranked = sorted(result["bust_attribution"].items(), key=lambda kv: kv[1], reverse=True)
        for s, n in ranked:
            pct = n / total_busts
            print(f"  {s:<14} {pct:>5.1%}")
    else:
        print("  (no busts)")


# ── CLI modes ─────────────────────────────────────────────────────────────

def _load_all(allocs: Dict[str, float], panel_name: str = DEFAULT_PANEL):
    # MVD identity gate on each canonical broker panel — catches the
    # 'wrong CSV in load slot' class (e.g. v5.4 export when v5.5 is locked,
    # or a Striker file in Guardian's path).
    panels = PANELS_BY_BROKER[panel_name]
    expected_broker = panel_name.upper()
    expected_symbols = EXPECTED_SYMBOLS_BY_BROKER[panel_name]
    expected_versions = EXPECTED_VERSIONS_BY_BROKER[panel_name]
    # Panel-specific strategy set: Pepperstone has all 4; OANDA has 3 (no NAS panel).
    panel_strats = tuple(panels.keys())
    for s in panel_strats:
        assert_tv_export(
            panels[s],
            expected_strategy=STRATEGY_FILENAME_TOKEN[s],
            expected_version=expected_versions[s],
            expected_broker=expected_broker,
            expected_symbol=expected_symbols[s],
        )
    trades_by_strat = {s: load_trades(panels[s]) for s in panel_strats}
    panel_allocs = {s: allocs[s] for s in panel_strats}
    panel, scale_info = build_daily_panel(trades_by_strat, panel_allocs)
    blocks = build_week_blocks(panel)
    return trades_by_strat, panel, blocks, scale_info, panel_strats


def mode_default(dd_trigger: float, dd_scale: float, no_protection: bool,
                 allocs: Dict[str, float], panel_name: str = DEFAULT_PANEL,
                 parallel: bool = False, verbose: bool = True):
    result = compute_default_config(dd_trigger, dd_scale, no_protection, allocs,
                                    panel_name=panel_name, parallel=parallel)

    if verbose:
        print("Scale factors:")
        for s, info in result["scale_info"].items():
            tag = "  [fallback: median]" if info["fell_back"] else ""
            print(f"  {s:<9} 1R=${info['implied_1r']:>7,.2f}  scale={info['scale']:>6.3f}  n={info['n_trades']}{tag}")
        print(f"Panel ({result['panel_name']}): {result['panel_start'].date()} -> {result['panel_end'].date()}  "
              f"({result['n_bdays']} bdays, {result['n_blocks']} week-blocks)")
        print()

    report_default(result, dd_trigger, dd_scale, allocs, no_protection)


def mode_historical(dd_trigger: float, dd_scale: float, no_protection: bool,
                    allocs: Dict[str, float], panel_name: str = DEFAULT_PANEL):
    _, panel, _, scale_info, panel_strats = _load_all(allocs, panel_name=panel_name)
    path = panel.values

    effective_trigger = 10.0 if no_protection else dd_trigger
    outcome, day, max_dd, culprit = _simulate_path(path, effective_trigger, dd_scale, len(path))

    # Count protection trigger days across the walk
    eq = peak = float(STARTING_EQUITY)
    trigger_days = 0
    for i in range(min(day, len(path))):
        dd_from_peak = (eq - peak) / peak if peak > 0 else 0.0
        # ULP-precision rounding mirrors _simulate_path; see Q-MCFP-1
        if not no_protection and round(dd_from_peak, 6) <= -dd_trigger:
            trigger_days += 1
            scale = dd_scale
        else:
            scale = 1.0
        pnl = float((path[i] * scale).sum())
        eq = eq + pnl
        if eq > peak:
            peak = eq
        if outcome == "pass" and round(eq, 2) >= PROFIT_TARGET:
            break

    print("=== Portfolio MC — Historical (deterministic) ===")
    print(f"Config: {_fmt_config(dd_trigger, dd_scale, no_protection)}")
    print(f"Allocations: {_fmt_alloc({s: allocs[s] for s in panel_strats})}")
    print(f"Panel ({panel_name}): {panel.index.min().date()} -> {panel.index.max().date()}  ({len(panel)} bdays)")
    print()
    print(f"Outcome:         {outcome.upper()}")
    print(f"Day terminated:  {day} ({panel.index[min(day - 1, len(panel) - 1)].date()})")
    print(f"Max DD:          {max_dd:.2%}")
    print(f"DD tier trigger days (through terminating day): {trigger_days}")
    if culprit is not None:
        print(f"Bust culprit:    {panel_strats[culprit]}")


def mode_sensitivity(dd_scale: float, allocs: Dict[str, float],
                     panel_name: str = DEFAULT_PANEL,
                     parallel: bool = False):
    _, _, blocks, _, panel_strats = _load_all(allocs, panel_name=panel_name)
    grid = [0.005, 0.010, 0.015, 0.020, 0.025]
    NO_PROTECT_TRIG = 10.0
    all_trigs = grid + [NO_PROTECT_TRIG]

    print("=== Portfolio MC — Sensitivity grid ===")
    print(f"Panel: {panel_name}")
    print(f"Allocations: {_fmt_alloc({s: allocs[s] for s in panel_strats})}")
    print(f"Sims: {SIMS_PER_SEED:,} × {len(SEEDS)} seeds (DD_SCALE fixed at {dd_scale}×)")
    print()
    print(f"{'DD_TRIGGER':<12} {'Pass':>8} {'Bust':>8} {'Timeout':>9} {'p99 DD':>8}")
    print("-" * 48)

    # Compute all (trig, seed) cells. Order-stable: by_trig[trig] holds seed
    # results in SEEDS order regardless of execution mode.
    if parallel:
        try:
            from joblib import Parallel, delayed
        except ImportError as e:
            raise ImportError(
                "--parallel requires joblib. Install with: pip install -e .[mc]"
            ) from e
        pairs = [(trig, seed) for trig in all_trigs for seed in SEEDS]
        flat = list(Parallel(n_jobs=-1, backend="loky")(
            delayed(run_seed)(seed, SIMS_PER_SEED, blocks, trig, dd_scale, strats=panel_strats)
            for trig, seed in pairs
        ))
        by_trig: Dict[float, list] = {trig: [] for trig in all_trigs}
        for (trig, _seed), result in zip(pairs, flat):
            by_trig[trig].append(result)
    else:
        by_trig = _serial_grid_with_progress(blocks, all_trigs, dd_scale, strats=panel_strats)

    def _row(label: str, results: list) -> str:
        pass_r = np.mean([r["outcomes"]["pass"] / SIMS_PER_SEED for r in results])
        bust_r = np.mean([(r["outcomes"]["bust_daily"] + r["outcomes"]["bust_static"]) / SIMS_PER_SEED for r in results])
        to_r   = np.mean([r["outcomes"]["timeout"] / SIMS_PER_SEED for r in results])
        dds    = [d for r in results for d in r["max_dds"]]
        p99    = np.percentile(dds, 99)
        return f"{label:<12} {pass_r:>8.2%} {bust_r:>8.2%} {to_r:>9.2%} {p99:>8.2%}"

    for trig in grid:
        print(_row(f"{trig:.3%}", by_trig[trig]))
    print(_row("no-protect", by_trig[NO_PROTECT_TRIG]))


# ── Entry ─────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(prog="portfolio_mc",
                                description="Single-tier challenge-outcome simulator")
    p.add_argument("--dd-trigger", type=float, default=DD_TRIGGER,
                   help=f"DD trigger (default {DD_TRIGGER} from dd_protection.py)")
    p.add_argument("--dd-scale", type=float, default=DD_SCALE,
                   help=f"DD scale (default {DD_SCALE} from dd_protection.py)")
    p.add_argument("--no-protection", action="store_true",
                   help="Run without DD protection")
    p.add_argument("--historical", action="store_true",
                   help="Deterministic walk through the historical panel")
    p.add_argument("--sensitivity", action="store_true",
                   help="DD-trigger sensitivity grid")
    p.add_argument("--guardian-risk", type=float, default=None,
                   help="Override Guardian allocation for what-if MC (e.g. 0.0025 to simulate a reduced-risk overlay)")
    p.add_argument("--panel", choices=list(PANELS_BY_BROKER.keys()), default=DEFAULT_PANEL,
                   help=f"Broker panel to load (default: {DEFAULT_PANEL}, the CLAUDE.md canonical lock anchor)")
    p.add_argument("--parallel", action="store_true",
                   help="Parallelize seed loop with joblib (faster on multi-core; default: sequential).")
    args = p.parse_args()

    allocs = dict(ALLOCATIONS)
    if args.guardian_risk is not None:
        allocs["guardian"] = args.guardian_risk

    if args.sensitivity:
        mode_sensitivity(args.dd_scale, allocs, panel_name=args.panel, parallel=args.parallel)
    elif args.historical:
        mode_historical(args.dd_trigger, args.dd_scale, args.no_protection, allocs, panel_name=args.panel)
    else:
        mode_default(args.dd_trigger, args.dd_scale, args.no_protection, allocs,
                     panel_name=args.panel, parallel=args.parallel)


if __name__ == "__main__":
    main()
