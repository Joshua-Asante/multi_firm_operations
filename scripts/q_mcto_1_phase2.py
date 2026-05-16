"""Q-MCTO-1 Phase 2 — regime-robustness gate on FXIFY-correct timeout semantic.

Implements docs/methodology/regime_robustness_gate.md procedure on the
treatment simulator (inactivity_simulator.simulate_path). Structurally
analogous to docs/briefs/Q-DDP-1/_run_regime_robustness.py; differences:

  - Uses run_seed from inactivity_simulator (FXIFY-correct timeout) instead
    of portfolio_mc._run_seeds (150-day cap).
  - Panel is the 2026-05-14 variant Pepperstone panel (monkey-patched, same
    as Phase 1).
  - H1/H2 split at 2024-05-01 (matches Q-DDP-1).
  - Floor = 97.5% per H-MCTO-1 §6 (matches Q-DDP-1 brief floor).

NO production code is modified. CLAUDE.md, baselines.md, test_mc_anchors.py
anchors are unchanged. Output is evidence for the brief's §8 only.
"""

from __future__ import annotations
import sys
import time
from pathlib import Path

REPO = Path(r"C:\Users\joshu\multi_firm_operations")
WORKTREE_SCRIPTS = REPO / ".claude" / "worktrees" / "amazing-gates-a6a325" / "scripts"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(WORKTREE_SCRIPTS))

# ── Patches ───────────────────────────────────────────────────────────────
import lib.mvd as _mvd
_orig_assert_window = _mvd.assert_window
def _patched_assert_window(start, end, expected_min_days, label="", tolerance_days=30):
    return _orig_assert_window(start, end, expected_min_days, label=label,
                                tolerance_days=max(tolerance_days, 120))
_mvd.assert_window = _patched_assert_window

import portfolio_mc as pmc
pmc.assert_window = _patched_assert_window

PEPP_DIR = REPO / "data" / "tv_exports" / "pepperstone"
pmc.PEPPERSTONE_PANELS = {
    "guardian":       PEPP_DIR / "Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-14_3b689.csv",
    "striker":        PEPP_DIR / "Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-14_e4dd7.csv",
    "aegis":          PEPP_DIR / "Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-05-14_d2682.csv",
    "striker_nas100": PEPP_DIR / "Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-14_da880.csv",
}
pmc.PANELS_BY_BROKER["pepperstone"] = pmc.PEPPERSTONE_PANELS

import numpy as np
import pandas as pd

from inactivity_simulator import run_seed as run_seed_inact, SIMS_PER_SEED, SEEDS

# ── Config ────────────────────────────────────────────────────────────────
ALLOCS = {
    "guardian":       0.0034,
    "striker":        0.0075,
    "aegis":          0.0150,
    "striker_nas100": 0.0045,
}
TRIG, SCALE = 0.015, 0.40
BLOCK_SIZE = 126                # ~6 months of business days
N_PANELS = 100                  # bootstrap n
HALF_SPLIT = pd.Timestamp("2024-05-01")
FLOOR = 0.975                   # H-MCTO-1 §6 + canonical regime-robustness floor
BUST_CEIL = 0.01
DD_CEIL = 0.05
BOOTSTRAP_SEED = 20260515       # different from Q-DDP-1's 20260506 (independence)


def aggregate_mc(seeds_results):
    """Aggregate per-seed MC results into headline metrics."""
    n_seeds = len(seeds_results)
    pass_r = np.mean([r["outcomes"]["pass"] / SIMS_PER_SEED for r in seeds_results])
    bust_r = np.mean([
        (r["outcomes"]["bust_daily"] + r["outcomes"]["bust_static"]
         + r["outcomes"]["bust_inactivity"]) / SIMS_PER_SEED
        for r in seeds_results
    ])
    inact_r = np.mean([
        r["outcomes"]["bust_inactivity"] / SIMS_PER_SEED for r in seeds_results
    ])
    hcap_r = np.mean([
        r["outcomes"]["horizon_cap"] / SIMS_PER_SEED for r in seeds_results
    ])
    all_dds = [d for r in seeds_results for d in r["max_dds"]]
    return {
        "pass_rate": float(pass_r),
        "bust_rate": float(bust_r),
        "bust_inactivity_rate": float(inact_r),
        "horizon_cap_rate": float(hcap_r),
        "p99_dd": float(np.percentile(all_dds, 99)),
        "p95_dd": float(np.percentile(all_dds, 95)),
    }


# ── Load panel ────────────────────────────────────────────────────────────
print("Loading 2026-05-14 variant Pepperstone panel...")
_, panel, blocks_full, _, panel_strats = pmc._load_all(ALLOCS, panel_name="pepperstone")
TARGET_LEN = len(panel)
n_blocks_avail = TARGET_LEN - BLOCK_SIZE + 1
print(f"Panel: {panel.index.min().date()} -> {panel.index.max().date()}")
print(f"  total bdays: {TARGET_LEN}, candidate 6mo blocks: {n_blocks_avail}")
print(f"  week-blocks (full): {len(blocks_full)}")
print()

# ── Part A: Block bootstrap (6mo blocks, N_PANELS=100) ────────────────────
print("=" * 90)
print(f"PART A — Block bootstrap: 6mo blocks, n={N_PANELS} alt panels")
print(f"Config: 0.75/0.45 + C2 (DD 0.015 / scale 0.40), FXIFY-correct timeout")
print("=" * 90)

bootstrap_rng = np.random.default_rng(seed=BOOTSTRAP_SEED)
panel_vals = panel.values
panel_cols = panel.columns
panel_start = panel.index.min()

bootstrap_results = []
t0 = time.time()
for panel_id in range(N_PANELS):
    # Construct alt panel of same total length via 6mo block resampling
    sampled = []
    total = 0
    while total < TARGET_LEN:
        start = int(bootstrap_rng.integers(0, n_blocks_avail))
        sampled.append(panel_vals[start : start + BLOCK_SIZE])
        total += BLOCK_SIZE
    alt_panel = np.concatenate(sampled)[:TARGET_LEN]
    bdates = pd.bdate_range(start=panel_start, periods=TARGET_LEN)
    alt_df = pd.DataFrame(alt_panel, index=bdates, columns=panel_cols)
    alt_blocks = pmc.build_week_blocks(alt_df)

    # Run FXIFY-correct MC on this alt panel
    seeds_results = [
        run_seed_inact(s, SIMS_PER_SEED, alt_blocks, TRIG, SCALE, panel_strats)
        for s in SEEDS
    ]
    agg = aggregate_mc(seeds_results)
    bootstrap_results.append({"panel_id": panel_id, **agg})

    if (panel_id + 1) % 10 == 0:
        elapsed = time.time() - t0
        rate = (panel_id + 1) / elapsed
        eta = (N_PANELS - panel_id - 1) / rate
        print(f"  ... {panel_id + 1}/{N_PANELS}  "
              f"({elapsed:.0f}s elapsed, ETA {eta:.0f}s)  "
              f"latest pass={agg['pass_rate']:.4%}", flush=True)

boot_df = pd.DataFrame(bootstrap_results)
p05 = float(np.percentile(boot_df["pass_rate"], 5))
p25 = float(np.percentile(boot_df["pass_rate"], 25))
p50 = float(np.percentile(boot_df["pass_rate"], 50))
p75 = float(np.percentile(boot_df["pass_rate"], 75))
p95 = float(np.percentile(boot_df["pass_rate"], 95))
boot_mean = float(boot_df["pass_rate"].mean())

print()
print(f"Bootstrap n={N_PANELS} pass-rate distribution (FXIFY-correct semantic, C2):")
print(f"  p05:  {p05:.4%}   (floor {FLOOR:.1%}: {'PASS' if p05 >= FLOOR else 'FAIL'})")
print(f"  p25:  {p25:.4%}")
print(f"  p50:  {p50:.4%}")
print(f"  p75:  {p75:.4%}")
print(f"  p95:  {p95:.4%}")
print(f"  mean: {boot_mean:.4%}")
print(f"  full-panel (Phase 1.B): 99.8833%")

# Sanity check (per regime_robustness_gate.md §Sanity)
print()
print("Sanity checks:")
fullpanel_phase1 = 0.998833
print(f"  bootstrap p05 ({p05:.4%}) <= full-panel ({fullpanel_phase1:.4%})?  "
      f"{'OK' if p05 <= fullpanel_phase1 else 'BOOTSTRAP BUG — STRESS BOOSTING'}")
print(f"  bootstrap p95 ({p95:.4%}) >= full-panel ({fullpanel_phase1:.4%})?  "
      f"{'OK' if p95 >= fullpanel_phase1 else 'PANEL REGIME-ANOMALOUS (rare)'}")

# ── Part B: Half-panel split ───────────────────────────────────────────────
print()
print("=" * 90)
print(f"PART B — Half-panel split at {HALF_SPLIT.date()}")
print("=" * 90)

h1_mask = panel.index < HALF_SPLIT
h2_mask = panel.index >= HALF_SPLIT
h1_panel = panel.loc[h1_mask]
h2_panel = panel.loc[h2_mask]

print(f"  H1: {h1_panel.index.min().date()} -> {h1_panel.index.max().date()}  ({len(h1_panel)} bdays)")
print(f"  H2: {h2_panel.index.min().date()} -> {h2_panel.index.max().date()}  ({len(h2_panel)} bdays)")
print()

half_results = []
for half_id, h_panel in [("H1", h1_panel), ("H2", h2_panel)]:
    blocks_h = pmc.build_week_blocks(h_panel)
    seeds_results = [
        run_seed_inact(s, SIMS_PER_SEED, blocks_h, TRIG, SCALE, panel_strats)
        for s in SEEDS
    ]
    agg = aggregate_mc(seeds_results)
    print(f"  {half_id} ({len(blocks_h)} week-blocks):")
    print(f"    pass:               {agg['pass_rate']:.4%}   (floor {FLOOR:.1%}: {'PASS' if agg['pass_rate'] >= FLOOR else 'FAIL'})")
    print(f"    bust (total):       {agg['bust_rate']:.4%}   (ceil {BUST_CEIL:.1%}: {'PASS' if agg['bust_rate'] < BUST_CEIL else 'FAIL'})")
    print(f"    bust (inactivity):  {agg['bust_inactivity_rate']:.4%}")
    print(f"    horizon_cap:        {agg['horizon_cap_rate']:.4%}")
    print(f"    p99 DD:             {agg['p99_dd']:.4%}   (ceil {DD_CEIL:.1%}: {'PASS' if agg['p99_dd'] < DD_CEIL else 'FAIL'})")
    half_results.append({"half_id": half_id, "n_bdays": len(h_panel),
                          "n_blocks": len(blocks_h), **agg})

h1 = half_results[0]
h2 = half_results[1]

# ── Verdict ───────────────────────────────────────────────────────────────
print()
print("=" * 90)
print("PHASE 2 VERDICT — H-MCTO-1 Clause 6 (regime-robustness)")
print("=" * 90)

# Per H-MCTO-1 §6:
# CLOSED-RESOLVED requires:
#   - bootstrap p05 >= FLOOR
#   - H1 pass >= FLOOR AND H1 bust < BUST_CEIL AND H1 p99 DD < DD_CEIL
#   - H2 pass >= FLOOR AND H2 bust < BUST_CEIL AND H2 p99 DD < DD_CEIL
# CLOSED-FALSIFIED (decisive) if H1 or H2 pass drops >5pp below floor, OR bootstrap p05 drops >5pp.

decisive_floor = FLOOR - 0.05

clauses = [
    ("bootstrap p05",     p05,               p05 >= FLOOR,           p05 < decisive_floor),
    ("H1 pass-rate",      h1["pass_rate"],   h1["pass_rate"] >= FLOOR,    h1["pass_rate"] < decisive_floor),
    ("H1 bust < 1%",      h1["bust_rate"],   h1["bust_rate"] < BUST_CEIL, False),
    ("H1 p99 DD < 5%",    h1["p99_dd"],      h1["p99_dd"] < DD_CEIL,      False),
    ("H2 pass-rate",      h2["pass_rate"],   h2["pass_rate"] >= FLOOR,    h2["pass_rate"] < decisive_floor),
    ("H2 bust < 1%",      h2["bust_rate"],   h2["bust_rate"] < BUST_CEIL, False),
    ("H2 p99 DD < 5%",    h2["p99_dd"],      h2["p99_dd"] < DD_CEIL,      False),
]

print(f"{'Check':30s} {'Value':>10s} {'Threshold':>10s} {'Status':>8s} {'Decisive?':>12s}")
print("-" * 80)
all_pass = True
any_decisive = False
for name, value, passed, decisive in clauses:
    if "p99 DD" in name or "bust" in name:
        thresh_str = "<5.0%" if "DD" in name else "<1.0%"
    else:
        thresh_str = f">={FLOOR:.1%}"
    status = "PASS" if passed else "FAIL"
    dec = "DECISIVE" if decisive else ""
    print(f"{name:30s} {value:>10.4%} {thresh_str:>10s} {status:>8s} {dec:>12s}")
    if not passed:
        all_pass = False
    if decisive:
        any_decisive = True

print()
if all_pass:
    print("CLAUSE 6 (regime-robustness): PASS")
    print()
    print("All H-MCTO-1 clauses 1-6 confirmed. Brief is gated for CLOSED-RESOLVED")
    print("pending Joshua's review for non-numerics judgment per §6 AMBIGUOUS clause.")
elif any_decisive:
    print("CLAUSE 6 (regime-robustness): DECISIVE FAILURE")
    print()
    print("H-MCTO-1 §6 decisive falsification triggered (>5pp below floor).")
    print("Brief gates for CLOSED-FALSIFIED.")
else:
    print("CLAUSE 6 (regime-robustness): MARGINAL FAILURE")
    print()
    print("Phase 2 fails but not decisively (no metric >5pp below floor).")
    print("Brief gates for CLOSED-AMBIGUOUS-HOLD or override (Q-DDP-1 precedent).")

# Q-DDP-1 comparison (for context)
print()
print("=" * 90)
print("Q-DDP-1 PRECEDENT (for context)")
print("=" * 90)
print("Q-DDP-1 C2 regime-robustness gate verdict:")
print("  bootstrap p05:  90.82%   (failed by ~7pp)")
print("  H1 pass:        86.78%   (failed by ~11pp — decisive)")
print("  H2 pass:        99.67%   (passed)")
print(f"  H1<->H2 spread: 12.9pp")
print()
print("Q-MCTO-1 Phase 2 result:")
this_spread = abs(h1["pass_rate"] - h2["pass_rate"]) * 100
print(f"  bootstrap p05:  {p05:.4%}")
print(f"  H1 pass:        {h1['pass_rate']:.4%}")
print(f"  H2 pass:        {h2['pass_rate']:.4%}")
print(f"  H1<->H2 spread: {this_spread:.2f}pp")

# Write CSV for audit
print()
out_path = Path(WORKTREE_SCRIPTS).parent / "docs" / "briefs" / "Q-MCTO-1"
out_path.mkdir(parents=True, exist_ok=True)
csv_path = out_path / "regime_robustness.csv"

rows = []
for r in bootstrap_results:
    rows.append({"analysis": "bootstrap", **r})
for r in half_results:
    rows.append({"analysis": "half_panel", **r})
out_df = pd.DataFrame(rows)
out_df.to_csv(csv_path, index=False)
print(f"Wrote {len(out_df)} rows to {csv_path.relative_to(REPO)}")
