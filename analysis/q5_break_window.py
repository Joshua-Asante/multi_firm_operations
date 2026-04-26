"""
Q5 — Break-window P&L falsification (second pre-Q gate test).

Question: did per-strategy and portfolio P&L during the 2025-10-30 -> 2026-01-27
break window (89 cal days, 64 trading days, ~12.8 weeks) land within the
unconditional 89-day-window distribution? If yes, signal layer absorbed B2's
bar-level correlation drift; Q3 (full pairwise correlation) does not need to
run. If no, Q3 escalates with the failing leg as prime suspect.

Brief: https://www.notion.so/34edc0b53c11811c9914cf95677420c4

Operationalization (Q5.4 decision rule): empirical p-value vs unconditional
distribution, NOT band-membership. The window was selected by B2 because
correlation broke there, so it is a conditional draw; the appropriate test is
the p-value against the marginal distribution of all 89-day windows. Two-sided
p > 0.05 = absorbed; p <= 0.05 = breakdown signal -> escalate to Q3.

Method-consistency:
  - Both realized and bootstrap sides use the allocation-scaled daily panel
    produced by `portfolio_mc.build_daily_panel()`. Same scaling, same panel
    handling, same week-block construction.
  - Bootstrap is Mon-anchored non-overlapping 5-day blocks per
    `portfolio_mc.build_week_blocks()` (line 127).
  - blocks_per_sim = (horizon + 4) // 5 per `portfolio_mc.run_seed()` (line 179).
  - Seeds (42, 123, 2026) match `portfolio_mc.SEEDS`.
  - Q5.4 primary comparison runs WITHOUT dd_protection on either side.
    dd_protection is a Python overlay (not in Pine), and the question is
    "did the strategies themselves absorb." Q5.5 is a conditional sensitivity
    that re-runs with dd_protection on if Q5.4 escalates.

Partial-D's (declared in brief, used here as one-line provenance citations):
  - B2 (window provenance): window = 2025-10-30 -> 2026-01-27 because
    `analysis/notice_phase/B2_event_vs_pervasive.json` identified joint
    correlation drift in 2026 YTD (US30<->USDJPY shifted from +0.13 to -0.40
    between calibration and 2026 YTD).
  - Q1 (1R reconciliation): Pine sizes contemporaneous-equity; portfolio_mc
    consumes raw realized $; the realized-vs-bootstrap comparison is
    apples-to-apples on scaled $.

Out of scope: live signal-layer absorption (window predates live deployment;
no journal data exists). This script tests locked-version backtest robustness
in the window only.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

# Import the bootstrap and scaling utilities directly so any future drift in
# portfolio_mc is automatically inherited (or surfaced as a test failure).
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import portfolio_mc as pmc

# OANDA panels (locked version snapshot, dated 2026-04-25).
OANDA_DIR = Path(__file__).parent.parent / "data" / "tv_exports" / "oanda"
CSVS: Dict[str, Path] = {
    "guardian": OANDA_DIR / "Guardian_Gold_v5.5_OANDA_XAUUSD_2026-04-25_9ae1f.csv",
    "striker":  OANDA_DIR / "Striker_DJ30_v4.4_OANDA_US30USD_2026-04-25_86e9d.csv",
    "aegis":    OANDA_DIR / "Aegis_USDJPY_v4.3_OANDA_USDJPY_2026-04-25_7ee6b.csv",
}

WINDOW_START = pd.Timestamp("2025-10-30")
WINDOW_END   = pd.Timestamp("2026-01-27")

# Trading days in the window (inclusive both ends, weekday-only). Becomes the
# bootstrap horizon so realized and bootstrap samples have the same length.
WINDOW_BDAYS = pd.bdate_range(WINDOW_START, WINDOW_END)
HORIZON = len(WINDOW_BDAYS)  # = 64

DISCRETENESS_FLOOR = 3  # n trades <= floor -> defer to portfolio-level p-value


def load_and_scale() -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, dict]]:
    """Returns (scaled_panel_daily, scaled_panel_window, scale_info)."""
    trades_by_strat = {s: pmc.load_trades(CSVS[s]) for s in pmc.STRATS}
    panel, scale_info = pmc.build_daily_panel(trades_by_strat, pmc.ALLOCATIONS)
    window = panel.loc[WINDOW_START:WINDOW_END]
    return panel, window, scale_info


def realized_window_stats(window_panel: pd.DataFrame,
                          trades_by_strat: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Realized P&L per leg and portfolio over the window, both:
      - scaled $ (canonical for vs-bootstrap comparison)
      - raw $ trade count for the discreteness flag
    """
    rows = []
    for strat in pmc.STRATS:
        scaled_pnl = float(window_panel[strat].sum())
        raw_trades = trades_by_strat[strat]
        in_win = raw_trades[(raw_trades["exit_date"] >= WINDOW_START) &
                            (raw_trades["exit_date"] <= WINDOW_END)]
        n_in_win = len(in_win)
        rows.append({
            "leg": strat,
            "n_trades_in_window": n_in_win,
            "realized_scaled_$": scaled_pnl,
            "realized_pct_of_200K": 100.0 * scaled_pnl / pmc.STARTING_EQUITY,
            "discreteness_flag": n_in_win <= DISCRETENESS_FLOOR,
        })
    portfolio_scaled = float(window_panel.values.sum())
    rows.append({
        "leg": "portfolio",
        "n_trades_in_window": sum(r["n_trades_in_window"] for r in rows),
        "realized_scaled_$": portfolio_scaled,
        "realized_pct_of_200K": 100.0 * portfolio_scaled / pmc.STARTING_EQUITY,
        "discreteness_flag": False,
    })
    return pd.DataFrame(rows)


def bootstrap_window_distribution(panel: pd.DataFrame,
                                  horizon: int = HORIZON,
                                  sims_per_seed: int = pmc.SIMS_PER_SEED,
                                  seeds: tuple = pmc.SEEDS) -> Dict[str, np.ndarray]:
    """Mon-anchored week-block bootstrap. Returns dict of leg -> array of
    `len(seeds) * sims_per_seed` cumulative-$ samples over `horizon` trading days.
    Uses the exact methodology from `portfolio_mc.build_week_blocks` and
    `portfolio_mc.run_seed`'s sampler.
    """
    blocks = pmc.build_week_blocks(panel)  # shape (n_blocks, 5, n_strats)
    n_blocks = len(blocks)
    blocks_per_sim = (horizon + 4) // 5

    samples = {s: [] for s in pmc.STRATS}
    samples["portfolio"] = []

    for seed in seeds:
        rng = np.random.default_rng(seed)
        for _ in range(sims_per_seed):
            idx = rng.integers(0, n_blocks, blocks_per_sim)
            path = np.concatenate([blocks[i] for i in idx])[:horizon]  # (horizon, n_strats)
            for j, s in enumerate(pmc.STRATS):
                samples[s].append(float(path[:, j].sum()))
            samples["portfolio"].append(float(path.sum()))

    return {k: np.asarray(v) for k, v in samples.items()}


def pvalues(realized: float, dist: np.ndarray) -> Tuple[float, float, float]:
    """Empirical (lower, upper, two-sided) p-values."""
    n = len(dist)
    p_lower = float(np.mean(dist <= realized))
    p_upper = float(np.mean(dist >= realized))
    p_two   = min(2.0 * min(p_lower, p_upper), 1.0)
    return p_lower, p_upper, p_two


def apply_dd_protection_per_leg(daily_path: np.ndarray,
                                dd_trigger: float = 0.010,
                                dd_scale: float = 0.40,
                                starting_equity: float = pmc.STARTING_EQUITY) -> Tuple[float, np.ndarray]:
    """Walk a (n_days, n_strats) daily-PnL path applying single-tier DD
    protection (same semantics as portfolio_mc._simulate_path:148-150 but
    without the bust-termination so the full window cumulative is returned).
    Returns (portfolio_post_protection_cumulative, per_leg_post_protection_cumulative).
    """
    eq = peak = float(starting_equity)
    per_leg = np.zeros(daily_path.shape[1])
    for day in range(daily_path.shape[0]):
        dd_from_peak = (eq - peak) / peak if peak > 0 else 0.0
        scale = dd_scale if dd_from_peak <= -dd_trigger else 1.0
        strat_pnls = daily_path[day] * scale
        per_leg += strat_pnls
        eq = eq + float(strat_pnls.sum())
        if eq > peak:
            peak = eq
    return float(per_leg.sum()), per_leg


def bootstrap_window_distribution_protected(panel: pd.DataFrame,
                                            horizon: int = HORIZON,
                                            sims_per_seed: int = pmc.SIMS_PER_SEED,
                                            seeds: tuple = pmc.SEEDS,
                                            dd_trigger: float = 0.010,
                                            dd_scale: float = 0.40) -> Dict[str, np.ndarray]:
    """Same Mon-anchored block sampler as bootstrap_window_distribution, but
    each sample's daily path is walked through dd_protection (matching
    portfolio_mc._simulate_path semantics minus bust-termination)."""
    blocks = pmc.build_week_blocks(panel)
    n_blocks = len(blocks)
    blocks_per_sim = (horizon + 4) // 5

    samples = {s: [] for s in pmc.STRATS}
    samples["portfolio"] = []

    for seed in seeds:
        rng = np.random.default_rng(seed)
        for _ in range(sims_per_seed):
            idx = rng.integers(0, n_blocks, blocks_per_sim)
            path = np.concatenate([blocks[i] for i in idx])[:horizon]
            port, per_leg = apply_dd_protection_per_leg(path, dd_trigger, dd_scale)
            for j, s in enumerate(pmc.STRATS):
                samples[s].append(float(per_leg[j]))
            samples["portfolio"].append(port)

    return {k: np.asarray(v) for k, v in samples.items()}


def main() -> dict:
    print("=" * 92)
    print("Q5 -- Break-window P&L falsification")
    print(f"Window: {WINDOW_START.date()} -> {WINDOW_END.date()} "
          f"({HORIZON} trading days, ~{HORIZON/5:.2f} weeks)")
    print(f"Bootstrap: Mon-anchored 5-day blocks (portfolio_mc.build_week_blocks:127);"
          f" {len(pmc.SEEDS)} seeds x {pmc.SIMS_PER_SEED:,} sims = "
          f"{len(pmc.SEEDS) * pmc.SIMS_PER_SEED:,} samples")
    print(f"Allocations: G {pmc.ALLOCATIONS['guardian']:.2%} / "
          f"S {pmc.ALLOCATIONS['striker']:.2%} / A {pmc.ALLOCATIONS['aegis']:.2%} "
          "(matches portfolio_mc.ALLOCATIONS)")
    print(f"Inputs: OANDA locked panels (G v5.5, S v4.4, A v4.3), per Q5.1")
    print("=" * 92)

    panel, window_panel, scale_info = load_and_scale()
    print()
    print("Scale factors (allocation-normalized to $200K-1R basis):")
    for s in pmc.STRATS:
        info = scale_info[s]
        tag = "  [fallback: median]" if info["fell_back"] else ""
        print(f"  {s:<9} 1R=${info['implied_1r']:>9,.2f}  scale={info['scale']:>6.3f}  n_panel={info['n_trades']}{tag}")
    print(f"Panel range: {panel.index.min().date()} -> {panel.index.max().date()} "
          f"({len(panel)} bdays, {len(pmc.build_week_blocks(panel))} week-blocks)")
    print()

    # --- Q5.2 Realized window P&L ---
    trades_by_strat = {s: pmc.load_trades(CSVS[s]) for s in pmc.STRATS}
    realized = realized_window_stats(window_panel, trades_by_strat)
    print("Q5.2 -- Realized window P&L (allocation-scaled to $200K basis):")
    print(realized.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print()
    discreteness_legs = realized[realized["discreteness_flag"]]["leg"].tolist()
    if discreteness_legs:
        print(f"  Discreteness flag: {discreteness_legs} (n <= {DISCRETENESS_FLOOR}); "
              "individual p-value will be discreteness-dominated; portfolio-level p-value is primary.")
    else:
        print(f"  No discreteness flag (all legs n > {DISCRETENESS_FLOOR}). Individual p-values informative.")
    print()

    # --- Q5.3 Bootstrap distribution ---
    print(f"Q5.3 -- Generating bootstrap distribution ({len(pmc.SEEDS)} seeds x "
          f"{pmc.SIMS_PER_SEED:,} sims)...")
    samples = bootstrap_window_distribution(panel)
    print(f"  Generated {len(samples['portfolio']):,} bootstrap samples per leg + portfolio.")
    print()
    print("Bootstrap distribution (89-day-window cumulative scaled $, % of $200K):")
    rows = []
    for leg in list(pmc.STRATS) + ["portfolio"]:
        d = samples[leg]
        rows.append({
            "leg": leg,
            "boot_p5_pct":  100.0 * np.percentile(d, 5)  / pmc.STARTING_EQUITY,
            "boot_p25_pct": 100.0 * np.percentile(d, 25) / pmc.STARTING_EQUITY,
            "boot_med_pct": 100.0 * np.median(d)         / pmc.STARTING_EQUITY,
            "boot_p75_pct": 100.0 * np.percentile(d, 75) / pmc.STARTING_EQUITY,
            "boot_p95_pct": 100.0 * np.percentile(d, 95) / pmc.STARTING_EQUITY,
        })
    boot_df = pd.DataFrame(rows)
    print(boot_df.to_string(index=False, float_format=lambda x: f"{x:>+7.4f}"))
    print()

    # --- Q5.4 p-values ---
    print("Q5.4 -- p-values (realized vs unconditional 89-day distribution):")
    rows = []
    for leg in list(pmc.STRATS) + ["portfolio"]:
        realized_dollars = float(realized[realized["leg"] == leg]["realized_scaled_$"].iloc[0])
        p_lower, p_upper, p_two = pvalues(realized_dollars, samples[leg])
        rows.append({
            "leg": leg,
            "realized_pct": 100.0 * realized_dollars / pmc.STARTING_EQUITY,
            "p_lower (P[boot<=real])": p_lower,
            "p_upper (P[boot>=real])": p_upper,
            "p_two_sided": p_two,
            "decision": ("ESCALATE-Q3" if p_two <= 0.05 else "absorbed"),
        })
    pval_df = pd.DataFrame(rows)
    print(pval_df.to_string(index=False, float_format=lambda x: f"{x:>+8.4f}"))
    print()

    escalate = pval_df[pval_df["p_two_sided"] <= 0.05]
    if len(escalate) == 0:
        print("Q5.4 DECISION: All four two-sided p > 0.05. Signal layer absorbed B2's "
              "bar-level shift. Q3 NOT escalated. Q5.5 dd_protection sensitivity SKIPPED.")
        result = "absorbed"
        return {
            "realized": realized,
            "bootstrap_samples": samples,
            "pvalues": pval_df,
            "decision": result,
        }
    else:
        legs = escalate["leg"].tolist()
        print(f"Q5.4 DECISION: ESCALATE Q3. Failing legs (two-sided p <= 0.05): {legs}.")
        print()

    # --- Q5.5 dd_protection sensitivity ---
    print("Q5.5 -- dd_protection sensitivity (DD trigger 1.0% / scale 0.40x):")
    print("  Walking realized window panel through dd_protection logic "
          "(matches portfolio_mc._simulate_path:148-150 minus bust termination)...")
    realized_path = window_panel.values  # (n_days, 3) scaled $ per day per leg
    realized_port_p, realized_per_leg_p = apply_dd_protection_per_leg(realized_path)
    print(f"  Realized portfolio (pre-protection):  ${float(window_panel.values.sum()):>+10,.2f}  "
          f"({100.0 * window_panel.values.sum() / pmc.STARTING_EQUITY:>+7.4f}% of $200K)")
    print(f"  Realized portfolio (post-protection): ${realized_port_p:>+10,.2f}  "
          f"({100.0 * realized_port_p / pmc.STARTING_EQUITY:>+7.4f}% of $200K)")
    delta = realized_port_p - float(window_panel.values.sum())
    print(f"  Delta from protection: ${delta:>+10,.2f}  ({100.0*delta/pmc.STARTING_EQUITY:>+7.4f}pp)")
    print()

    print(f"  Generating dd_protection-on bootstrap distribution "
          f"({len(pmc.SEEDS)} seeds x {pmc.SIMS_PER_SEED:,} sims)...")
    samples_p = bootstrap_window_distribution_protected(panel)
    print(f"  Generated {len(samples_p['portfolio']):,} samples per leg + portfolio.")
    print()

    rows = []
    for leg in list(pmc.STRATS) + ["portfolio"]:
        d = samples_p[leg]
        rows.append({
            "leg": leg,
            "boot_p5_pct":  100.0 * np.percentile(d, 5)  / pmc.STARTING_EQUITY,
            "boot_p25_pct": 100.0 * np.percentile(d, 25) / pmc.STARTING_EQUITY,
            "boot_med_pct": 100.0 * np.median(d)         / pmc.STARTING_EQUITY,
            "boot_p75_pct": 100.0 * np.percentile(d, 75) / pmc.STARTING_EQUITY,
            "boot_p95_pct": 100.0 * np.percentile(d, 95) / pmc.STARTING_EQUITY,
        })
    print("Bootstrap distribution WITH dd_protection (89-day cumulative scaled $, % of $200K):")
    print(pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f"{x:>+7.4f}"))
    print()

    print("p-values (post-dd_protection on both sides):")
    rows = []
    realized_per_leg_p_dict = dict(zip(pmc.STRATS, realized_per_leg_p))
    for leg in list(pmc.STRATS) + ["portfolio"]:
        if leg == "portfolio":
            realized_dollars = realized_port_p
        else:
            realized_dollars = float(realized_per_leg_p_dict[leg])
        p_lower, p_upper, p_two = pvalues(realized_dollars, samples_p[leg])
        rows.append({
            "leg": leg,
            "realized_pct_post_p": 100.0 * realized_dollars / pmc.STARTING_EQUITY,
            "p_lower (P[boot<=real])": p_lower,
            "p_upper (P[boot>=real])": p_upper,
            "p_two_sided": p_two,
            "decision": ("ESCALATE-Q3" if p_two <= 0.05 else "absorbed"),
        })
    pval_p_df = pd.DataFrame(rows)
    print(pval_p_df.to_string(index=False, float_format=lambda x: f"{x:>+8.4f}"))
    print()

    persists = pval_p_df[pval_p_df["p_two_sided"] <= 0.05]
    print("Q5.5 SUMMARY:")
    if len(persists) == 0:
        print("  Breakdown signal ATTENUATED by dd_protection — no leg or portfolio "
              "remains at p <= 0.05 after both sides are protected.")
    else:
        legs_p = persists["leg"].tolist()
        print(f"  Breakdown signal PERSISTS through dd_protection on: {legs_p}.")
        # Compare pre/post protection p-values to characterize the attenuation
        pre = dict(zip(pval_df["leg"], pval_df["p_two_sided"]))
        for leg in legs_p:
            post = float(persists[persists["leg"] == leg]["p_two_sided"].iloc[0])
            arrow = "WORSE" if post < pre[leg] else ("BETTER" if post > pre[leg] else "same")
            print(f"    {leg:<10}: p_two pre={pre[leg]:.4f}  post={post:.4f}  ({arrow})")

    result = "escalate"
    return {
        "realized": realized,
        "bootstrap_samples": samples,
        "pvalues": pval_df,
        "samples_protected": samples_p,
        "pvalues_protected": pval_p_df,
        "decision": result,
    }


if __name__ == "__main__":
    main()
