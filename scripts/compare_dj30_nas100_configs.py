#!/usr/bin/env python3
"""One-off comparison: portfolio MC at LOCKED vs Pine-default config for
DJ30 + NAS100. Guardian and Aegis panels held constant in both runs.

LOCKED config (matches CLAUDE.md anchor):
  DJ30:   risk 1.00% / pyramid 350% / maxDailyDD 1.00%
  NAS100: risk 0.40% / pyramid 1000% / maxDailyDD 1.00%

TEST config (the Pine input.float defaults caught by validate_params.py):
  DJ30:   risk 0.70% / pyramid 750% / maxDailyDD 1.15%
  NAS100: risk 0.37% / pyramid 1000% / maxDailyDD 1.00%

Differences in pyramid / maxDailyDD are baked into the CSV panels (TV
re-export with the alternative settings). risk_pct is applied via the
ALLOCATIONS dict at MC time.

Holds constant in both runs: Guardian 0.34%, Aegis 1.50%, dd_protection
C2 (1.5% trigger / 0.40× scale), Pepperstone panel, 10K × 3 seeds.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import portfolio_mc as pmc  # noqa: E402
from dd_protection import DD_SCALE, DD_TRIGGER  # noqa: E402
PEPP = REPO_ROOT / "data" / "tv_exports" / "pepperstone"

GUARDIAN = PEPP / "Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-05_33781.csv"
AEGIS    = PEPP / "Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-04-26_0bf1b.csv"
# Pair retained for historical comparison after 2026-05-18 re-lock.
# "PRIOR" = the superseded 1.00% / 0.40% / 350 pyramid / 1.00 maxDD config.
# "CURRENT" = the now-canonical 0.70% / 0.37% / 750 pyramid / 1.15 maxDD config.
DJ30_PRIOR    = PEPP / "Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-18_2afad.csv"
DJ30_CURRENT  = PEPP / "Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-18_ca15e.csv"
NAS_PRIOR     = PEPP / "Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-18_ec660.csv"
NAS_CURRENT   = PEPP / "Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-18_d2c59.csv"
# Back-compat aliases for the original "default vs test" framing.
DJ30_DEF = DJ30_PRIOR
DJ30_TST = DJ30_CURRENT
NAS_DEF  = NAS_PRIOR
NAS_TST  = NAS_CURRENT

LOCKED_ALLOCS = {
    "guardian":       0.0034,
    "striker":        0.0100,   # 1.00%
    "aegis":          0.0150,
    "striker_nas100": 0.0040,   # 0.40%
}

TEST_ALLOCS = {
    "guardian":       0.0034,
    "striker":        0.0070,   # 0.70%
    "aegis":          0.0150,
    "striker_nas100": 0.0037,   # 0.37%
}


def _run(panels: dict, allocs: dict, label: str) -> dict:
    """Swap panel dict in place, run MC, restore. Returns the result dict."""
    saved = dict(pmc.PEPPERSTONE_PANELS)
    pmc.PEPPERSTONE_PANELS.clear()
    pmc.PEPPERSTONE_PANELS.update(panels)
    pmc.PANELS_BY_BROKER["pepperstone"] = pmc.PEPPERSTONE_PANELS
    try:
        print(f"\n=== Running: {label} ===")
        for s, p in panels.items():
            print(f"  {s:<15} {p.name}")
        result = pmc.compute_default_config(
            DD_TRIGGER, DD_SCALE, no_protection=False,
            allocs=allocs, panel_name="pepperstone",
        )
        return result
    finally:
        pmc.PEPPERSTONE_PANELS.clear()
        pmc.PEPPERSTONE_PANELS.update(saved)
        pmc.PANELS_BY_BROKER["pepperstone"] = pmc.PEPPERSTONE_PANELS


def _summarize(r: dict, label: str) -> dict:
    print(f"\n--- {label} ---")
    print(f"Pass:                {r['pass_rate']:.2%} (sigma {r['pass_sigma']:.2%})")
    print(f"Bust:                {r['bust_rate']:.2%} (daily {r['bust_daily_rate']:.2%} / static {r['bust_static_rate']:.2%})")
    print(f"Timeout:             {r['timeout_rate']:.2%}")
    print(f"Median days to pass: {r['median_days_to_pass']}")
    print(f"p50 / p95 / p99 DD:  {r['p50_dd']:.2%} / {r['p95_dd']:.2%} / {r['p99_dd']:.2%}")
    total_b = sum(r["bust_attribution"].values())
    if total_b > 0:
        print("Bust attribution:")
        for s, n in sorted(r["bust_attribution"].items(), key=lambda kv: -kv[1]):
            print(f"  {s:<15} {n/total_b:>6.1%}")
    print("Scale factors (1R, scale, n):")
    for s, info in r["scale_info"].items():
        tag = " [fallback]" if info["fell_back"] else ""
        print(f"  {s:<15} 1R=${info['implied_1r']:>7,.2f}  scale={info['scale']:>6.3f}  n={info['n_trades']}{tag}")
    return r


def main() -> int:
    print("Portfolio MC comparison — DJ30 + NAS100 config sweep")
    print(f"dd_protection: trigger={DD_TRIGGER:.3f} ({DD_TRIGGER:.1%}) / scale={DD_SCALE}")
    print(f"Guardian + Aegis panels: held constant")

    panels_locked = {
        "guardian":       GUARDIAN,
        "striker":        DJ30_DEF,
        "aegis":          AEGIS,
        "striker_nas100": NAS_DEF,
    }
    panels_test = {
        "guardian":       GUARDIAN,
        "striker":        DJ30_TST,
        "aegis":          AEGIS,
        "striker_nas100": NAS_TST,
    }

    locked = _run(panels_locked, LOCKED_ALLOCS, "LOCKED (1.00% DJ30 + 350 pyramid + 1.00 maxDD / 0.40% NAS100)")
    test   = _run(panels_test,   TEST_ALLOCS,   "TEST   (0.70% DJ30 + 750 pyramid + 1.15 maxDD / 0.37% NAS100)")

    _summarize(locked, "LOCKED")
    _summarize(test,   "TEST")

    # Side-by-side
    print("\n=== Side-by-side ===")
    print(f"{'Metric':<22}  {'LOCKED':>10}  {'TEST':>10}  {'delta':>10}")
    print("-" * 56)
    rows = [
        ("Pass rate",         locked["pass_rate"],         test["pass_rate"]),
        ("Bust rate",         locked["bust_rate"],         test["bust_rate"]),
        ("  Bust daily",      locked["bust_daily_rate"],   test["bust_daily_rate"]),
        ("  Bust static",     locked["bust_static_rate"],  test["bust_static_rate"]),
        ("Timeout",           locked["timeout_rate"],      test["timeout_rate"]),
        ("p50 DD",            locked["p50_dd"],            test["p50_dd"]),
        ("p95 DD",            locked["p95_dd"],            test["p95_dd"]),
        ("p99 DD",            locked["p99_dd"],            test["p99_dd"]),
    ]
    for name, a, b in rows:
        diff = b - a
        print(f"{name:<22}  {a:>9.2%}  {b:>9.2%}  {diff:>+9.2%}")
    days_a = locked["median_days_to_pass"]
    days_b = test["median_days_to_pass"]
    print(f"{'Median days to pass':<22}  {days_a:>10d}  {days_b:>10d}  {days_b - days_a:>+10d}")
    print()
    print("Lock criteria (bust < 1%, p99 DD < 5%):")
    for label, r in (("LOCKED", locked), ("TEST", test)):
        bust_ok = "PASS" if r["bust_rate"] < 0.01 else "FAIL"
        dd_ok   = "PASS" if r["p99_dd"] < 0.05 else "FAIL"
        print(f"  {label:<6}  bust {r['bust_rate']:.3%} [{bust_ok}]  /  p99 DD {r['p99_dd']:.3%} [{dd_ok}]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
