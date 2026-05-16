"""
mc_silver_5strat_impact — exploratory 5-strategy MC

Adds Guardian Silver v1.5-sweep (2026-05-14, _98c95) to the locked 4-strategy
Pepperstone panel to characterize its impact on the portfolio bust/pass
distribution. Silver is a forensic comparator (Q-CORR-1.2), not a locked
strategy; this run quantifies hypothetical addition only.

Comparison ladder:
  A. ANCHOR_05_05 — 4-strategy on production-pinned 2026-05-05 CSVs
                    (must reproduce 98.09% / 0.36% / 4.73% p99 DD)
  B. REFRESH_05_14 — 4-strategy on fresh 2026-05-14 exports (refresh-only delta)
  C. SILVER_5STRAT — 5-strategy on 2026-05-14 + Silver, swept across {0.20%, 0.34%, 0.50%}

Silver is Guardian-archetype (pure trend-rider, no BE), so 1R = median loss.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

# Reuse production functions without touching them.
sys.path.insert(0, str(Path(__file__).parent))
from portfolio_mc import (  # noqa: E402
    SIMS_PER_SEED, SEEDS, HORIZON_DAYS,
    DD_TRIGGER, DD_SCALE, STARTING_EQUITY,
    load_trades, implied_1r, build_week_blocks, run_seed,
)

# ── Panels ────────────────────────────────────────────────────────────────
WORKTREE = Path(__file__).parent
# Pinned 05-05 CSVs are gitignored; read them from the main repo working tree.
PINNED_DIR = Path(r"C:/Users/joshu/multi_firm_operations") / "data" / "tv_exports" / "pepperstone"
FRESH_DIR = Path(r"C:/Users/joshu/Downloads")

PINNED_05_05 = {
    "guardian":       PINNED_DIR / "Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-05_33781.csv",
    "striker":        PINNED_DIR / "Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv",
    "aegis":          PINNED_DIR / "Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-04-26_0bf1b.csv",
    "striker_nas100": PINNED_DIR / "Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-05_7ca6f.csv",
}

FRESH_05_14 = {
    "guardian":       FRESH_DIR / "Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-14_49852.csv",
    "striker":        FRESH_DIR / "Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-14_cc921.csv",
    "aegis":          FRESH_DIR / "Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-05-14_9d3a2.csv",
    "striker_nas100": FRESH_DIR / "Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-14_95d01.csv",
}

SILVER_CSV = FRESH_DIR / "Guardian_Silver_v1.5-sweep_PEPPERSTONE_XAGUSD_2026-05-14_98c95.csv"

BASE_ALLOCS = {
    "guardian":       0.0034,
    "striker":        0.0100,
    "aegis":          0.0150,
    "striker_nas100": 0.0040,
}

# Silver uses Guardian-archetype 1R basis (median loss; pure trend-rider).
SILVER_1R_KEY = "guardian"


# ── Panel build (variant; same logic as portfolio_mc.build_daily_panel) ───

def build_panel(panels: Dict[str, Path], allocs: Dict[str, float],
                silver_csv: Path | None = None, silver_alloc: float | None = None
                ) -> Tuple[pd.DataFrame, np.ndarray, Tuple[str, ...], Dict[str, dict]]:
    """Load trades, scale per-strategy, aggregate to business-day panel.
    Returns (panel, week_blocks, strats_tuple, scale_info).
    """
    trades_by_strat: Dict[str, pd.DataFrame] = {}
    for s, path in panels.items():
        trades_by_strat[s] = load_trades(path)
    eff_allocs = dict(allocs)
    if silver_csv is not None and silver_alloc is not None:
        trades_by_strat["silver"] = load_trades(silver_csv)
        eff_allocs["silver"] = silver_alloc

    scale_info: Dict[str, dict] = {}
    series = []
    for s, trades in trades_by_strat.items():
        r1_strat = SILVER_1R_KEY if s == "silver" else s
        r1, fell_back = implied_1r(trades["pnl"], r1_strat)
        target_dollars = eff_allocs[s] * STARTING_EQUITY
        scale = target_dollars / r1 if r1 > 0 else 1.0
        scale_info[s] = {
            "implied_1r": r1, "scale": scale,
            "n_trades": len(trades), "fell_back": fell_back,
            "alloc": eff_allocs[s],
        }
        ser = trades.groupby("exit_date")["pnl"].sum() * scale
        ser.name = s
        series.append(ser)
    panel = pd.concat(series, axis=1, sort=True).fillna(0.0)
    bdays = pd.bdate_range(panel.index.min(), panel.index.max())
    panel = panel.reindex(bdays).fillna(0.0)
    blocks = build_week_blocks(panel)
    return panel, blocks, tuple(trades_by_strat.keys()), scale_info


# ── Aggregator ────────────────────────────────────────────────────────────

def run_config(label: str, panels: Dict[str, Path], allocs: Dict[str, float],
               silver_csv: Path | None = None, silver_alloc: float | None = None
               ) -> dict:
    panel, blocks, strats, scale_info = build_panel(panels, allocs, silver_csv, silver_alloc)

    print(f"\n=== {label} ===")
    print(f"Strategies: {strats}")
    print(f"Panel: {panel.index.min().date()} -> {panel.index.max().date()}  "
          f"({len(panel)} bdays, {len(blocks)} week-blocks)")
    print("Scale factors:")
    for s, info in scale_info.items():
        tag = "  [fallback: median]" if info["fell_back"] else ""
        print(f"  {s:<15} alloc={info['alloc']:.2%}  1R=${info['implied_1r']:>7,.2f}  "
              f"scale={info['scale']:>6.3f}  n={info['n_trades']}{tag}")

    seeds_results = [
        run_seed(seed, SIMS_PER_SEED, blocks, DD_TRIGGER, DD_SCALE,
                 strats=strats)
        for seed in SEEDS
    ]

    per_seed = SIMS_PER_SEED
    pass_r = [r["outcomes"]["pass"] / per_seed for r in seeds_results]
    bd_r   = [r["outcomes"]["bust_daily"] / per_seed for r in seeds_results]
    bs_r   = [r["outcomes"]["bust_static"] / per_seed for r in seeds_results]
    to_r   = [r["outcomes"]["timeout"] / per_seed for r in seeds_results]
    bust_r = [d + s for d, s in zip(bd_r, bs_r)]
    all_days = [d for r in seeds_results for d in r["days_to_pass"]]
    all_dds  = [d for r in seeds_results for d in r["max_dds"]]
    attrib = {s: sum(r["bust_attribution"][s] for r in seeds_results) for s in strats}

    result = {
        "label": label,
        "strats": strats,
        "panel_start": panel.index.min(), "panel_end": panel.index.max(),
        "n_bdays": len(panel), "n_blocks": len(blocks),
        "scale_info": scale_info,
        "pass_rate": float(np.mean(pass_r)), "pass_sigma": float(np.std(pass_r)),
        "bust_rate": float(np.mean(bust_r)), "bust_sigma": float(np.std(bust_r)),
        "bust_daily_rate": float(np.mean(bd_r)),
        "bust_static_rate": float(np.mean(bs_r)),
        "timeout_rate": float(np.mean(to_r)),
        "median_days_to_pass": int(np.median(all_days)) if all_days else None,
        "p50_dd": float(np.percentile(all_dds, 50)),
        "p95_dd": float(np.percentile(all_dds, 95)),
        "p99_dd": float(np.percentile(all_dds, 99)),
        "bust_attribution": attrib,
    }

    print(f"Pass:    {result['pass_rate']:>6.2%} (sigma {result['pass_sigma']:.2%})")
    print(f"Bust:    {result['bust_rate']:>6.2%} (sigma {result['bust_sigma']:.2%})  "
          f"[daily {result['bust_daily_rate']:.2%} / static {result['bust_static_rate']:.2%}]")
    print(f"Timeout: {result['timeout_rate']:>6.2%}")
    if result["median_days_to_pass"] is not None:
        print(f"Median days to pass: {result['median_days_to_pass']}")
    print(f"p50/p95/p99 DD: {result['p50_dd']:.2%} / {result['p95_dd']:.2%} / {result['p99_dd']:.2%}")
    total_busts = sum(attrib.values())
    if total_busts > 0:
        print("Bust attribution:")
        for s, n in sorted(attrib.items(), key=lambda kv: kv[1], reverse=True):
            print(f"  {s:<15} {n/total_busts:>5.1%}")
    return result


def main():
    print("Running 5-strategy MC impact study (Silver v1.5-sweep)")
    print(f"DD config: trigger={DD_TRIGGER}, scale={DD_SCALE}× (C2 locked 2026-05-08)")
    print(f"Sims: {SIMS_PER_SEED:,} × {len(SEEDS)} seeds, horizon {HORIZON_DAYS} days")

    results = {}

    # A. Anchor reproduction (production-pinned 05-05 panels)
    results["A_anchor_05_05"] = run_config(
        "A. ANCHOR — 4-strategy, 2026-05-05 pinned panels", PINNED_05_05, BASE_ALLOCS)

    # B. Refresh baseline (05-14 panels, no Silver)
    results["B_refresh_05_14"] = run_config(
        "B. REFRESH — 4-strategy, 2026-05-14 fresh panels", FRESH_05_14, BASE_ALLOCS)

    # C/D/E. Silver swept
    for silver_alloc in (0.0020, 0.0034, 0.0050):
        key = f"silver_at_{silver_alloc * 100:.2f}pct".replace(".", "_")
        results[key] = run_config(
            f"5-STRAT — 2026-05-14 + Silver @ {silver_alloc:.2%}",
            FRESH_05_14, BASE_ALLOCS,
            silver_csv=SILVER_CSV, silver_alloc=silver_alloc)

    # Delta summary
    print("\n" + "=" * 78)
    print("IMPACT SUMMARY (deltas vs B. REFRESH 4-strategy baseline @ 2026-05-14)")
    print("=" * 78)
    b = results["B_refresh_05_14"]
    print(f"{'Config':<42} {'Pass':>8} {'Bust':>8} {'p99 DD':>8} {'Med d':>6}")
    print(f"{'A. ANCHOR (05-05 pinned)':<42} "
          f"{results['A_anchor_05_05']['pass_rate']:>8.2%} "
          f"{results['A_anchor_05_05']['bust_rate']:>8.2%} "
          f"{results['A_anchor_05_05']['p99_dd']:>8.2%} "
          f"{results['A_anchor_05_05']['median_days_to_pass']:>6d}")
    print(f"{'B. REFRESH (05-14, 4-strat)':<42} "
          f"{b['pass_rate']:>8.2%} {b['bust_rate']:>8.2%} "
          f"{b['p99_dd']:>8.2%} {b['median_days_to_pass']:>6d}")
    print("-" * 78)
    for k, r in results.items():
        if not k.startswith("silver_at_"):
            continue
        dpass = r["pass_rate"] - b["pass_rate"]
        dbust = r["bust_rate"] - b["bust_rate"]
        ddd   = r["p99_dd"] - b["p99_dd"]
        dmed  = r["median_days_to_pass"] - b["median_days_to_pass"]
        print(f"{k:<42} "
              f"{r['pass_rate']:>8.2%} {r['bust_rate']:>8.2%} "
              f"{r['p99_dd']:>8.2%} {r['median_days_to_pass']:>6d}  "
              f"delta {dpass:+.2%} / {dbust:+.2%} / {ddd:+.2%} / {dmed:+d}d")


if __name__ == "__main__":
    main()
