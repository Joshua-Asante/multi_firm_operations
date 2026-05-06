"""
Q-DDP-1 Step 3 — regime-robustness gate on C2 (1.5% / 0.40x).

Block bootstrap (100 panels of 6mo contiguous blocks) + half-panel split.
Uses joblib parallel for the inner MC seed loop.

Writes docs/briefs/Q-DDP-1/regime_robustness.csv.
"""
from __future__ import annotations

import os
import sys
import time

# Force import of THIS worktree's portfolio_mc (not a stale sibling worktree's editable install)
_THIS_WORKTREE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, _THIS_WORKTREE)

import numpy as np
import pandas as pd

from portfolio_mc import (
    ALLOCATIONS,
    SEEDS,
    SIMS_PER_SEED,
    _load_all,
    _run_seeds,
    build_week_blocks,
)


def main():
    import portfolio_mc as _pmc
    print(f"Using portfolio_mc from: {_pmc.__file__}", flush=True)
    assert _THIS_WORKTREE.lower() in _pmc.__file__.lower(), (
        f"Wrong portfolio_mc loaded! Expected from {_THIS_WORKTREE}, got {_pmc.__file__}"
    )
    trades_by_strat, panel, blocks_full, scale_info, panel_strats = _load_all(
        ALLOCATIONS, panel_name="pepperstone"
    )
    print(
        f"Panel: {panel.index.min().date()} -> {panel.index.max().date()}  "
        f"({len(panel)} bdays, {len(blocks_full)} week-blocks)",
        flush=True,
    )

    TRIG, SCALE = 0.015, 0.40
    BLOCK_SIZE = 126  # ~6 months of business days
    N_PANELS = 100
    TARGET_LEN = len(panel)
    n_blocks_avail = TARGET_LEN - BLOCK_SIZE + 1

    print(
        f"\nBootstrap: block_size={BLOCK_SIZE}, n_panels={N_PANELS}, "
        f"target_len={TARGET_LEN}",
        flush=True,
    )

    bootstrap_rng = np.random.default_rng(seed=20260506)
    panel_vals = panel.values
    panel_cols = panel.columns

    bootstrap_results = []
    t0 = time.time()
    for panel_id in range(N_PANELS):
        sampled = []
        total_len = 0
        while total_len < TARGET_LEN:
            start = int(bootstrap_rng.integers(0, n_blocks_avail))
            block = panel_vals[start : start + BLOCK_SIZE]
            sampled.append(block)
            total_len += len(block)
        alt_panel = np.concatenate(sampled)[:TARGET_LEN]
        bdates = pd.bdate_range(start="2022-01-04", periods=TARGET_LEN)
        alt_df = pd.DataFrame(alt_panel, index=bdates, columns=panel_cols)
        alt_blocks = build_week_blocks(alt_df)
        seeds_results = _run_seeds(
            alt_blocks, TRIG, SCALE, parallel=True, strats=panel_strats
        )
        pass_rate = float(
            np.mean(
                [r["outcomes"]["pass"] / SIMS_PER_SEED for r in seeds_results]
            )
        )
        bootstrap_results.append(
            {"config_id": "C2", "panel_id": panel_id, "pass_rate": pass_rate}
        )
        if (panel_id + 1) % 5 == 0:
            elapsed = time.time() - t0
            est_total = elapsed * N_PANELS / (panel_id + 1)
            remaining = est_total - elapsed
            print(
                f"  ... {panel_id + 1}/{N_PANELS}  "
                f"(elapsed {elapsed:.0f}s, est remaining {remaining:.0f}s)",
                flush=True,
            )

    boot_df = pd.DataFrame(bootstrap_results)
    p05 = float(np.percentile(boot_df["pass_rate"], 5))
    p50 = float(np.percentile(boot_df["pass_rate"], 50))
    p95 = float(np.percentile(boot_df["pass_rate"], 95))
    mean = float(boot_df["pass_rate"].mean())
    print(f"\nBootstrap n={N_PANELS} C2 pass-rate distribution:", flush=True)
    print(f"  5th pctile:  {p05:.4%}", flush=True)
    print(f"  50th pctile: {p50:.4%}", flush=True)
    print(f"  95th pctile: {p95:.4%}", flush=True)
    print(f"  mean:        {mean:.4%}", flush=True)
    print(f"  full-panel C2: 98.0900%", flush=True)
    print(f"  Floor 97.5%: {'PASSES' if p05 >= 0.975 else 'FAILS'}", flush=True)
    print(f"  Floor 97.9%: {'PASSES' if p05 >= 0.979 else 'FAILS'}", flush=True)

    # Half-panel split
    print("\n=== Half-panel split ===", flush=True)
    h1_mask = panel.index < pd.Timestamp("2024-05-01")
    h2_mask = panel.index >= pd.Timestamp("2024-05-01")
    h1_panel = panel.loc[h1_mask]
    h2_panel = panel.loc[h2_mask]
    print(
        f"  H1: {h1_panel.index.min().date()} -> {h1_panel.index.max().date()}  "
        f"({len(h1_panel)} bdays)",
        flush=True,
    )
    print(
        f"  H2: {h2_panel.index.min().date()} -> {h2_panel.index.max().date()}  "
        f"({len(h2_panel)} bdays)",
        flush=True,
    )

    half_results = []
    for half_id, h_panel in [("H1", h1_panel), ("H2", h2_panel)]:
        blocks_h = build_week_blocks(h_panel)
        seeds_results = _run_seeds(
            blocks_h, TRIG, SCALE, parallel=True, strats=panel_strats
        )
        pass_rate = float(
            np.mean(
                [r["outcomes"]["pass"] / SIMS_PER_SEED for r in seeds_results]
            )
        )
        bust_rate = float(
            np.mean(
                [
                    (r["outcomes"]["bust_daily"] + r["outcomes"]["bust_static"])
                    / SIMS_PER_SEED
                    for r in seeds_results
                ]
            )
        )
        all_dds = [d for r in seeds_results for d in r["max_dds"]]
        p99_dd = float(np.percentile(all_dds, 99))
        print(
            f"  {half_id}: Pass {pass_rate:.4%}  Bust {bust_rate:.4%}  "
            f"p99 DD {p99_dd:.4%}  ({len(blocks_h)} week-blocks)",
            flush=True,
        )
        half_results.append(
            {
                "config_id": "C2",
                "half_id": half_id,
                "window_start": str(h_panel.index.min().date()),
                "window_end": str(h_panel.index.max().date()),
                "n_bdays": len(h_panel),
                "n_blocks": len(blocks_h),
                "pass_rate": pass_rate,
                "bust_rate": bust_rate,
                "p99_dd": p99_dd,
            }
        )

    all_rows = []
    for r in bootstrap_results:
        all_rows.append({"analysis": "bootstrap", **r})
    for r in half_results:
        all_rows.append({"analysis": "half_panel", **r})
    out_df = pd.DataFrame(all_rows)
    out_df.to_csv("docs/briefs/Q-DDP-1/regime_robustness.csv", index=False)
    print(
        f"\nWrote {len(out_df)} rows to docs/briefs/Q-DDP-1/regime_robustness.csv",
        flush=True,
    )

    print("\n=== Verdict for C2 (1.5% / 0.40x) ===", flush=True)
    half_min = min(half_results[0]["pass_rate"], half_results[1]["pass_rate"])
    print(f"  Bootstrap 5th pctile: {p05:.4%}", flush=True)
    print(f"  Half-panel min:       {half_min:.4%}", flush=True)
    print(
        f"  Both >= 97.5% (adj):  {(p05 >= 0.975) and (half_min >= 0.975)}",
        flush=True,
    )
    print(
        f"  Both >= 97.9% (orig): {(p05 >= 0.979) and (half_min >= 0.979)}",
        flush=True,
    )


if __name__ == "__main__":
    main()
    sys.stdout.flush()
