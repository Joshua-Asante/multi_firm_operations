"""
Regime-robustness gate — 5-strategy + Silver v1.5-sweep @ 0.20% allocation.

Adapted from docs/briefs/Q-DDP-1/_run_regime_robustness.py (canonical pattern).
Operates on the 5-strategy panel: 4-strategy 2026-05-14 fresh + Silver @ 0.20%.

Procedure (per docs/methodology/regime_robustness_gate.md):
  Part A — Block bootstrap: 100 alternate panels resampled from 6-month
            contiguous blocks (~126 bdays). Full MC at each.
  Part B — Half-panel split: H1 (2022-01 -> 2024-04) / H2 (2024-05 -> 2026-04).
  Part C — Acceptance: bootstrap p05 >= floor AND H1 >= floor AND H2 >= floor.

Floors reported:
  98.22% — 4-strategy 05-14 refresh baseline ("no regression vs status quo")
  97.50% — Q-DDP-1 historical floor (looser comparison)

Output: mc_runs/silver_regime_gate_results.csv
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from portfolio_mc import SEEDS, SIMS_PER_SEED, build_week_blocks, _run_seeds  # noqa: E402
from mc_silver_5strat_impact import (  # noqa: E402
    FRESH_05_14, SILVER_CSV, BASE_ALLOCS, build_panel,
)

TRIG, SCALE = 0.015, 0.40
BLOCK_SIZE = 126                    # ~6 months business days
N_PANELS = 100
SILVER_ALLOC = 0.0020
SPLIT_DATE = pd.Timestamp("2024-05-01")
FLOORS = [("baseline_98_22", 0.9822), ("historical_97_50", 0.9750)]

OUT_CSV = Path(__file__).parent / "mc_runs" / "silver_regime_gate_results.csv"


def main():
    import portfolio_mc as _pmc
    print(f"Using portfolio_mc from: {_pmc.__file__}", flush=True)

    panel, blocks_full, panel_strats, scale_info = build_panel(
        FRESH_05_14, BASE_ALLOCS, silver_csv=SILVER_CSV, silver_alloc=SILVER_ALLOC)
    print(f"5-strategy panel: {panel.index.min().date()} -> {panel.index.max().date()}"
          f"  ({len(panel)} bdays, {len(blocks_full)} week-blocks)", flush=True)
    print(f"Config: DD_TRIGGER={TRIG}, DD_SCALE={SCALE}x, Silver alloc={SILVER_ALLOC:.2%}",
          flush=True)
    print(f"Strats: {panel_strats}", flush=True)
    for s, info in scale_info.items():
        tag = "  [fallback]" if info["fell_back"] else ""
        print(f"  {s:<15} 1R=${info['implied_1r']:>7,.2f}  scale={info['scale']:>6.3f}  "
              f"n={info['n_trades']}{tag}", flush=True)

    # ── Part A — Block bootstrap ───────────────────────────────────────
    target_len = len(panel)
    n_blocks_avail = target_len - BLOCK_SIZE + 1
    print(f"\nBootstrap: block_size={BLOCK_SIZE}, n_panels={N_PANELS}, "
          f"target_len={target_len}", flush=True)

    rng = np.random.default_rng(seed=20260514)
    panel_vals = panel.values
    panel_cols = panel.columns

    bootstrap_results = []
    t0 = time.time()
    for panel_id in range(N_PANELS):
        sampled = []
        total = 0
        while total < target_len:
            start = int(rng.integers(0, n_blocks_avail))
            block = panel_vals[start:start + BLOCK_SIZE]
            sampled.append(block)
            total += len(block)
        alt_panel = np.concatenate(sampled)[:target_len]
        bdates = pd.bdate_range(start="2022-01-04", periods=target_len)
        alt_df = pd.DataFrame(alt_panel, index=bdates, columns=panel_cols)
        alt_blocks = build_week_blocks(alt_df)
        seeds_results = _run_seeds(alt_blocks, TRIG, SCALE, parallel=True,
                                    strats=panel_strats)
        pass_rate = float(np.mean(
            [r["outcomes"]["pass"] / SIMS_PER_SEED for r in seeds_results]))
        bust_rate = float(np.mean(
            [(r["outcomes"]["bust_daily"] + r["outcomes"]["bust_static"]) / SIMS_PER_SEED
             for r in seeds_results]))
        all_dds = [d for r in seeds_results for d in r["max_dds"]]
        p99_dd = float(np.percentile(all_dds, 99))
        bootstrap_results.append({
            "config_id": "silver_5strat_0_20",
            "panel_id": panel_id,
            "pass_rate": pass_rate,
            "bust_rate": bust_rate,
            "p99_dd": p99_dd,
        })
        if (panel_id + 1) % 10 == 0:
            elapsed = time.time() - t0
            est_total = elapsed * N_PANELS / (panel_id + 1)
            remain = est_total - elapsed
            print(f"  ... {panel_id + 1}/{N_PANELS}  "
                  f"(elapsed {elapsed:.0f}s, est remaining {remain:.0f}s)", flush=True)

    boot_df = pd.DataFrame(bootstrap_results)
    p05 = float(np.percentile(boot_df["pass_rate"], 5))
    p50 = float(np.percentile(boot_df["pass_rate"], 50))
    p95 = float(np.percentile(boot_df["pass_rate"], 95))
    mean = float(boot_df["pass_rate"].mean())
    print(f"\nBootstrap n={N_PANELS} pass-rate distribution (5-strat + Silver @ 0.20%):",
          flush=True)
    print(f"  5th pctile:  {p05:.4%}", flush=True)
    print(f"  50th pctile: {p50:.4%}", flush=True)
    print(f"  95th pctile: {p95:.4%}", flush=True)
    print(f"  mean:        {mean:.4%}", flush=True)
    print(f"  full-panel:  99.3500% (from mc_silver_5strat_impact.py)", flush=True)

    # ── Part B — Half-panel split ──────────────────────────────────────
    print("\n=== Half-panel split ===", flush=True)
    h1_panel = panel.loc[panel.index < SPLIT_DATE]
    h2_panel = panel.loc[panel.index >= SPLIT_DATE]
    print(f"  H1: {h1_panel.index.min().date()} -> {h1_panel.index.max().date()}  "
          f"({len(h1_panel)} bdays)", flush=True)
    print(f"  H2: {h2_panel.index.min().date()} -> {h2_panel.index.max().date()}  "
          f"({len(h2_panel)} bdays)", flush=True)

    half_results = []
    for half_id, h_panel in [("H1", h1_panel), ("H2", h2_panel)]:
        blocks_h = build_week_blocks(h_panel)
        seeds_results = _run_seeds(blocks_h, TRIG, SCALE, parallel=True, strats=panel_strats)
        pass_rate = float(np.mean(
            [r["outcomes"]["pass"] / SIMS_PER_SEED for r in seeds_results]))
        bust_rate = float(np.mean(
            [(r["outcomes"]["bust_daily"] + r["outcomes"]["bust_static"]) / SIMS_PER_SEED
             for r in seeds_results]))
        all_dds = [d for r in seeds_results for d in r["max_dds"]]
        p99_dd = float(np.percentile(all_dds, 99))
        all_days = [d for r in seeds_results for d in r["days_to_pass"]]
        med = int(np.median(all_days)) if all_days else None
        attrib = {s: sum(r["bust_attribution"][s] for r in seeds_results) for s in panel_strats}
        print(f"  {half_id}: Pass {pass_rate:.4%}  Bust {bust_rate:.4%}  "
              f"p99 DD {p99_dd:.4%}  median d {med}  ({len(blocks_h)} week-blocks)",
              flush=True)
        total_busts = sum(attrib.values())
        if total_busts > 0:
            attrib_str = " / ".join(
                f"{s}{n/total_busts:.0%}" for s, n in
                sorted(attrib.items(), key=lambda kv: kv[1], reverse=True))
            print(f"        bust attrib: {attrib_str}", flush=True)
        half_results.append({
            "config_id": "silver_5strat_0_20",
            "half_id": half_id,
            "window_start": str(h_panel.index.min().date()),
            "window_end":   str(h_panel.index.max().date()),
            "n_bdays": len(h_panel),
            "n_blocks": len(blocks_h),
            "pass_rate": pass_rate,
            "bust_rate": bust_rate,
            "p99_dd": p99_dd,
            "median_days": med,
        })

    # ── Part C — Acceptance ────────────────────────────────────────────
    print("\n=== Verdict ===", flush=True)
    h1_pass = half_results[0]["pass_rate"]
    h2_pass = half_results[1]["pass_rate"]
    half_min = min(h1_pass, h2_pass)
    print(f"  Bootstrap 5th pctile: {p05:.4%}", flush=True)
    print(f"  H1 pass-rate:         {h1_pass:.4%}", flush=True)
    print(f"  H2 pass-rate:         {h2_pass:.4%}", flush=True)
    print(f"  Half-panel min:       {half_min:.4%}", flush=True)
    spread = abs(h1_pass - h2_pass)
    print(f"  H1<->H2 spread:       {spread:.4%}", flush=True)

    for name, floor in FLOORS:
        boot_ok = p05 >= floor
        h1_ok = h1_pass >= floor
        h2_ok = h2_pass >= floor
        all_ok = boot_ok and h1_ok and h2_ok
        verdict = "PASS" if all_ok else "FAIL"
        print(f"\n  Floor {floor:.2%} ({name}):", flush=True)
        print(f"    Bootstrap p05 >= floor:  {boot_ok}  ({p05:.4%} vs {floor:.2%})", flush=True)
        print(f"    H1 >= floor:             {h1_ok}  ({h1_pass:.4%} vs {floor:.2%})", flush=True)
        print(f"    H2 >= floor:             {h2_ok}  ({h2_pass:.4%} vs {floor:.2%})", flush=True)
        print(f"    Verdict:                 {verdict}", flush=True)

    # Write results
    rows = []
    for r in bootstrap_results:
        rows.append({"analysis": "bootstrap", **r})
    for r in half_results:
        rows.append({"analysis": "half_panel", **r})
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT_CSV, index=False)
    print(f"\nWrote {len(rows)} rows to {OUT_CSV.relative_to(Path(__file__).parent)}",
          flush=True)


if __name__ == "__main__":
    main()
    sys.stdout.flush()
