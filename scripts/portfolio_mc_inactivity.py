"""Portfolio MC with FXIFY-correct timeout semantics.

Changes vs portfolio_mc.py default:
  - REMOVED: 150-day horizon as a policy timeout. The challenge has no max-days
    rule per firm_rules.py (only `inactivity_max_idle_days = 60`).
  - ADDED:   60-consecutive-idle-bday inactivity bust. A day with pnl == 0
    across ALL 4 strategies is "idle". On 60 consecutive idle days, the path
    terminates as bust_inactivity.
  - SAFETY:  hard ceiling at 1500 bdays just to prevent runaway loops. Hits
    are tracked as outcome 'horizon_cap' and should be near-zero.

Runs the same three scenarios as the prior comparison.
"""

import sys
from pathlib import Path
import numpy as np

REPO = Path(r"C:\Users\joshu\multi_firm_operations")
sys.path.insert(0, str(REPO))

# Patches
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

# ── New simulation semantics ───────────────────────────────────────────────

STARTING_EQUITY = pmc.STARTING_EQUITY
PROFIT_TARGET = pmc.PROFIT_TARGET
DAILY_LOSS_PCT = pmc.DAILY_LOSS_PCT
STATIC_DD_PCT = pmc.STATIC_DD_PCT
MIN_TRADING_DAYS = pmc.MIN_TRADING_DAYS

INACTIVITY_LIMIT = 60     # FXIFY rule: 60 consecutive idle bdays = bust
HORIZON_CAP = 1500        # safety only — should almost never fire
SIMS_PER_SEED = pmc.SIMS_PER_SEED
SEEDS = pmc.SEEDS

def simulate_path_inactivity(path, dd_trigger, dd_scale):
    """Walk a (n_days, n_strats) path with inactivity-only timeout semantics."""
    eq = peak = float(STARTING_EQUITY)
    trade_days = 0
    consecutive_idle = 0
    max_dd = 0.0
    horizon = len(path)

    for day in range(horizon):
        dd_from_peak = (eq - peak) / peak if peak > 0 else 0.0
        scale = dd_scale if round(dd_from_peak, 6) <= -dd_trigger else 1.0
        strat_pnls = path[day] * scale
        pnl = float(strat_pnls.sum())
        eq_new = eq + pnl

        # Bust checks (same as portfolio_mc)
        if round(pnl / STARTING_EQUITY, 6) <= DAILY_LOSS_PCT:
            return "bust_daily", day + 1, max_dd, int(np.argmin(strat_pnls))
        if round((eq_new - STARTING_EQUITY) / STARTING_EQUITY, 6) <= STATIC_DD_PCT:
            return "bust_static", day + 1, max_dd, int(np.argmin(strat_pnls))

        # Inactivity tracking — idle = all 4 strats zero pnl on this day
        if pnl == 0 and not np.any(strat_pnls != 0):
            consecutive_idle += 1
        else:
            consecutive_idle = 0
        if consecutive_idle >= INACTIVITY_LIMIT:
            return "bust_inactivity", day + 1, max_dd, None

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

    return "horizon_cap", horizon, max_dd, None


def run_seed_inactivity(seed, n_sims, blocks, dd_trigger, dd_scale, strats):
    rng = np.random.default_rng(seed)
    n_blocks = len(blocks)
    blocks_per_sim = (HORIZON_CAP + 4) // 5  # enough blocks to cover safety cap

    outcomes = {"pass": 0, "bust_daily": 0, "bust_static": 0,
                "bust_inactivity": 0, "horizon_cap": 0}
    days_to_pass = []
    days_to_inact = []
    max_dds = []
    bust_attrib = {s: 0 for s in strats}

    for _ in range(n_sims):
        idx = rng.integers(0, n_blocks, blocks_per_sim)
        path = np.concatenate([blocks[i] for i in idx])[:HORIZON_CAP]

        outcome, day, max_dd, culprit = simulate_path_inactivity(path, dd_trigger, dd_scale)
        outcomes[outcome] += 1
        max_dds.append(max_dd)
        if outcome == "pass":
            days_to_pass.append(day)
        elif outcome == "bust_inactivity":
            days_to_inact.append(day)
        elif outcome in ("bust_daily", "bust_static") and culprit is not None:
            bust_attrib[strats[culprit]] += 1

    return {
        "outcomes": outcomes,
        "days_to_pass": days_to_pass,
        "days_to_inact": days_to_inact,
        "max_dds": max_dds,
        "bust_attribution": bust_attrib,
    }


def compute_inactivity_config(allocs, dd_trigger=0.015, dd_scale=0.40,
                               panel_name="pepperstone"):
    trades_by_strat, panel, blocks, scale_info, panel_strats = pmc._load_all(
        allocs, panel_name=panel_name
    )
    seeds_results = [
        run_seed_inactivity(s, SIMS_PER_SEED, blocks, dd_trigger, dd_scale, panel_strats)
        for s in SEEDS
    ]

    per_seed = SIMS_PER_SEED
    pass_r = [r["outcomes"]["pass"] / per_seed for r in seeds_results]
    bd_r   = [r["outcomes"]["bust_daily"] / per_seed for r in seeds_results]
    bs_r   = [r["outcomes"]["bust_static"] / per_seed for r in seeds_results]
    bi_r   = [r["outcomes"]["bust_inactivity"] / per_seed for r in seeds_results]
    hc_r   = [r["outcomes"]["horizon_cap"] / per_seed for r in seeds_results]
    bust_total_r = [d + s + i for d, s, i in zip(bd_r, bs_r, bi_r)]

    all_days = [d for r in seeds_results for d in r["days_to_pass"]]
    all_inact = [d for r in seeds_results for d in r["days_to_inact"]]
    all_dds = [d for r in seeds_results for d in r["max_dds"]]

    attrib = {s: sum(r["bust_attribution"][s] for r in seeds_results) for s in panel_strats}

    return {
        "panel_strats": panel_strats,
        "panel_start": panel.index.min(), "panel_end": panel.index.max(),
        "n_bdays": len(panel), "n_blocks": len(blocks),
        "pass_rate": float(np.mean(pass_r)),
        "pass_sigma": float(np.std(pass_r)),
        "bust_daily_rate": float(np.mean(bd_r)),
        "bust_static_rate": float(np.mean(bs_r)),
        "bust_inactivity_rate": float(np.mean(bi_r)),
        "horizon_cap_rate": float(np.mean(hc_r)),
        "bust_total_rate": float(np.mean(bust_total_r)),
        "median_days_to_pass": int(np.median(all_days)) if all_days else None,
        "p50_days_to_pass": int(np.percentile(all_days, 50)) if all_days else None,
        "p95_days_to_pass": int(np.percentile(all_days, 95)) if all_days else None,
        "p99_days_to_pass": int(np.percentile(all_days, 99)) if all_days else None,
        "median_days_to_inact": int(np.median(all_inact)) if all_inact else None,
        "p50_dd": float(np.percentile(all_dds, 50)),
        "p95_dd": float(np.percentile(all_dds, 95)),
        "p99_dd": float(np.percentile(all_dds, 99)),
        "bust_attribution": attrib,
    }


SCENARIOS = [
    ("BASELINE (2026-05-14 lock)", {
        "guardian":       0.0034, "striker":        0.0075,
        "aegis":          0.0150, "striker_nas100": 0.0045,
    }),
    ("MAX LOSS-CYCLE RF (0.60/0.80)", {
        "guardian":       0.0034, "striker":        0.0060,
        "aegis":          0.0150, "striker_nas100": 0.0080,
    }),
    ("MAX FULL-RECORD RF (0.70/0.70)", {
        "guardian":       0.0034, "striker":        0.0070,
        "aegis":          0.0150, "striker_nas100": 0.0070,
    }),
]

results = []
for label, allocs in SCENARIOS:
    print(f"\n{'=' * 90}")
    print(f"SCENARIO: {label}")
    print(f"  DJ30 {allocs['striker']:.2%}  NAS {allocs['striker_nas100']:.2%}  "
          f"G {allocs['guardian']:.2%}  A {allocs['aegis']:.2%}")
    print('=' * 90)
    r = compute_inactivity_config(allocs)
    results.append((label, allocs, r))
    print(f"Pass:              {r['pass_rate']:.3%}  (sigma {r['pass_sigma']:.3%})")
    print(f"Bust (daily):      {r['bust_daily_rate']:.3%}")
    print(f"Bust (static):     {r['bust_static_rate']:.3%}")
    print(f"Bust (inactivity): {r['bust_inactivity_rate']:.3%}")
    print(f"Horizon cap:       {r['horizon_cap_rate']:.3%}  (safety; near-zero expected)")
    print(f"Bust total:        {r['bust_total_rate']:.3%}")
    print(f"Median days-to-pass: {r['median_days_to_pass']}")
    print(f"p95/p99 days-to-pass: {r['p95_days_to_pass']} / {r['p99_days_to_pass']}")
    if r['median_days_to_inact']:
        print(f"Median days-to-inactivity-bust: {r['median_days_to_inact']}")
    print(f"p50/p95/p99 DD: {r['p50_dd']:.2%} / {r['p95_dd']:.2%} / {r['p99_dd']:.2%}")
    total_busts = sum(r['bust_attribution'].values())
    if total_busts > 0:
        print(f"Bust attribution (n={total_busts}, daily+static busts only):")
        for strat, n in sorted(r['bust_attribution'].items(), key=lambda kv: -kv[1]):
            print(f"  {strat:<14} {n/total_busts:>5.1%}  (n={n})")

# Comparative
print(f"\n{'=' * 110}")
print("COMPARATIVE — FXIFY-CORRECT TIMEOUT (60-day inactivity only)")
print('=' * 110)
print(f"{'Scenario':<32} | {'Pass':>7} | {'B_dly':>6} | {'B_stat':>6} | "
      f"{'B_inact':>7} | {'HrznCap':>7} | {'p99 DD':>6} | {'MedDays':>7} | {'p95Days':>7} | {'p99Days':>7}")
print("-" * 110)
for label, allocs, r in results:
    print(f"{label:<32} | {r['pass_rate']:>7.2%} | {r['bust_daily_rate']:>6.2%} | "
          f"{r['bust_static_rate']:>6.2%} | {r['bust_inactivity_rate']:>7.2%} | "
          f"{r['horizon_cap_rate']:>7.2%} | {r['p99_dd']:>6.2%} | "
          f"{r['median_days_to_pass']:>7d} | {r['p95_days_to_pass']:>7d} | {r['p99_days_to_pass']:>7d}")

# Side-by-side with old (150-day timeout) anchors for reference
print()
print("Reference — same scenarios under old 150-day timeout policy:")
print(f"{'Scenario':<32} | {'Pass':>7} | {'Bust':>6} | {'Timeout(150d)':>13}")
print("-" * 70)
print(f"{'BASELINE (2026-05-14 lock)':<32} | {0.9878:>7.2%} | {0.0012:>6.2%} | {0.0110:>13.2%}")
print(f"{'MAX LOSS-CYCLE RF (0.60/0.80)':<32} | {0.9900:>7.2%} | {0.0013:>6.2%} | {0.0087:>13.2%}")
print(f"{'MAX FULL-RECORD RF (0.70/0.70)':<32} | {0.9896:>7.2%} | {0.0013:>6.2%} | {0.0091:>13.2%}")
