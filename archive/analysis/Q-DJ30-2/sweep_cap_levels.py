"""Q-DJ30-2 Phase C - cap-level sweep.

For each cap level in {1.5R, 2.0R, 2.5R, 3.0R, 3.5R}, computes on the
n=197 primary base panel:
    PF, WR, expectancy/R, max consecutive-loss count, p99 DD, worst-loss/R,
    trades-touched count.

Single-pass acceptance gate (per pre-registration):
    Delta PF   >= -5%      (vs base-only baseline 2.3294)
    Delta p99 DD <= -1.0pp (cap reduces tail)
    Delta WR   >= -5pp

Survivors advance to Phase D (regime-robustness gate).

Writes:
    analysis/Q-DJ30-2/sweep_results.csv
    analysis/Q-DJ30-2/capped_pnl_{cap_R}.csv (one per cap)
"""
from pathlib import Path
import csv
import json

import numpy as np

from build_capped_pnl import load_entries, apply_cap, write_capped_csv, NOMINAL_R_USD

OUT_DIR = Path("analysis/Q-DJ30-2")

# Pre-registered baseline anchors (post-amendment 2026-05-06)
BASELINE_PF_BASE = 2.3294
PF_FLOOR = 0.95 * BASELINE_PF_BASE  # 2.213

# Pre-registered single-pass thresholds
DELTA_PF_MIN_PCT = -5.0       # ΔPF >= -5%
DELTA_P99_DD_MAX_PP = -1.0    # ΔDD <= -1.0pp (must REDUCE tail)
DELTA_WR_MIN_PP = -5.0        # ΔWR >= -5pp

CAP_LEVELS = (1.5, 2.0, 2.5, 3.0, 3.5)


def compute_pf(pnls):
    pos = sum(p for p in pnls if p > 0)
    neg = sum(p for p in pnls if p < 0)
    return pos / abs(neg) if neg else float("inf")


def compute_wr(pnls):
    return 100.0 * sum(1 for p in pnls if p > 0) / len(pnls)


def compute_expectancy_R(pnls):
    """Average pnl in R units across the cohort."""
    return float(np.mean(pnls)) / NOMINAL_R_USD


def max_consec_loss(pnls):
    """Longest run of consecutive losing trades (pnl < 0)."""
    longest = current = 0
    for p in pnls:
        if p < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def equity_curve(pnls):
    return np.cumsum(np.asarray(pnls, dtype=float))


def drawdown_series(eq):
    """DD at each trade as (peak - current) / max(peak, 1.0). Returns positive series."""
    peaks = np.maximum.accumulate(eq)
    # Use a constant baseline ($200K) to make DD a fraction of starting capital,
    # since equity curve is cumulative P&L not equity.
    # Strategy DD: (peak - current) in dollars, divided by $200K starting capital.
    return (peaks - eq) / 200000.0


def p99_dd(pnls):
    """99th percentile of the per-trade drawdown distribution, as percentage."""
    eq = equity_curve(pnls)
    dd = drawdown_series(eq)
    return float(np.percentile(dd, 99) * 100)


def worst_loss_R(pnls):
    return float(min(pnls)) / NOMINAL_R_USD


def metrics(pnls, n_touched):
    return {
        "n": len(pnls),
        "PF": compute_pf(pnls),
        "WR_pct": compute_wr(pnls),
        "expectancy_R": compute_expectancy_R(pnls),
        "max_consec_loss": max_consec_loss(pnls),
        "p99_DD_pct": p99_dd(pnls),
        "worst_loss_R": worst_loss_R(pnls),
        "n_cap_touched": n_touched,
    }


def main():
    entries = load_entries()
    bases = [r for r in entries if r["Signal"] == "Long"]
    base_pnls_uncapped = [r["pnl"] for r in bases]

    baseline = metrics(base_pnls_uncapped, 0)
    print("=== Q-DJ30-2 Phase C - cap-level sweep ===")
    print(f"Baseline (uncapped, n={baseline['n']}):")
    print(f"  PF={baseline['PF']:.4f}  WR={baseline['WR_pct']:.2f}%  "
          f"E[R]={baseline['expectancy_R']:+.4f}  max_cons_L={baseline['max_consec_loss']}  "
          f"p99_DD={baseline['p99_DD_pct']:.2f}%  worst={baseline['worst_loss_R']:.2f}R")
    print()

    rows = []
    rows.append({
        "cap_R": "uncapped",
        "n_touched": 0,
        "PF": f"{baseline['PF']:.4f}",
        "WR_pct": f"{baseline['WR_pct']:.2f}",
        "expectancy_R": f"{baseline['expectancy_R']:+.4f}",
        "max_consec_loss": baseline['max_consec_loss'],
        "p99_DD_pct": f"{baseline['p99_DD_pct']:.4f}",
        "worst_loss_R": f"{baseline['worst_loss_R']:+.4f}",
        "delta_PF_pct": "0.00",
        "delta_p99_DD_pp": "0.00",
        "delta_WR_pp": "0.00",
        "passes_C": "baseline",
    })

    print(f"{'cap':>5} {'n_touch':>8} {'PF':>7} {'dPF%':>8} {'WR%':>7} {'dWR':>7} "
          f"{'p99_DD%':>9} {'dDDpp':>8} {'worstR':>8} {'gate':>6}")

    survivors = []
    for cap_R in CAP_LEVELS:
        capped = apply_cap(entries, cap_R)
        # Write per-cap CSV
        out_csv = OUT_DIR / f"capped_pnl_{cap_R:.1f}R.csv"
        write_capped_csv(capped, cap_R, out_csv)

        capped_bases = [r for r in capped if r["Signal"] == "Long"]
        capped_pnls = [r["pnl"] for r in capped_bases]
        n_touched = sum(1 for r in capped_bases if r["cap_touched"])

        m = metrics(capped_pnls, n_touched)
        delta_pf_pct = 100.0 * (m["PF"] - baseline["PF"]) / baseline["PF"]
        delta_p99 = m["p99_DD_pct"] - baseline["p99_DD_pct"]
        delta_wr = m["WR_pct"] - baseline["WR_pct"]

        passes = (
            delta_pf_pct >= DELTA_PF_MIN_PCT
            and delta_p99 <= DELTA_P99_DD_MAX_PP
            and delta_wr >= DELTA_WR_MIN_PP
        )
        gate = "PASS" if passes else "FAIL"
        if passes:
            survivors.append(cap_R)

        print(f"{cap_R:>4.1f}R {n_touched:>7d}  {m['PF']:>6.4f} {delta_pf_pct:>+7.2f}%  "
              f"{m['WR_pct']:>6.2f}% {delta_wr:>+6.2f}pp "
              f"{m['p99_DD_pct']:>8.4f}% {delta_p99:>+7.4f}pp {m['worst_loss_R']:>+7.2f}R  {gate:>5}")

        rows.append({
            "cap_R": f"{cap_R:.1f}",
            "n_touched": n_touched,
            "PF": f"{m['PF']:.4f}",
            "WR_pct": f"{m['WR_pct']:.2f}",
            "expectancy_R": f"{m['expectancy_R']:+.4f}",
            "max_consec_loss": m['max_consec_loss'],
            "p99_DD_pct": f"{m['p99_DD_pct']:.4f}",
            "worst_loss_R": f"{m['worst_loss_R']:+.4f}",
            "delta_PF_pct": f"{delta_pf_pct:+.2f}",
            "delta_p99_DD_pp": f"{delta_p99:+.4f}",
            "delta_WR_pp": f"{delta_wr:+.2f}",
            "passes_C": "PASS" if passes else "FAIL",
        })

    # Write sweep_results.csv
    out_results = OUT_DIR / "sweep_results.csv"
    fieldnames = list(rows[0].keys())
    with out_results.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print()
    print(f"Wrote {out_results}")
    print()
    print("=== Phase C single-pass acceptance ===")
    print(f"  dPF >= -5% (PF >= 2.213)        : pass criterion 1")
    print(f"  dp99 DD <= -1.0pp               : pass criterion 2")
    print(f"  dWR >= -5pp                     : pass criterion 3")
    print()
    if survivors:
        print(f"Survivors -> Phase D regime-robustness gate: {survivors}")
    else:
        print("No survivors. Verdict skips to Phase G CLOSE / NULL.")

    # Save survivor list as JSON for downstream phases
    (OUT_DIR / "phase_c_survivors.json").write_text(
        json.dumps({"survivors_R": survivors, "baseline": baseline}, indent=2, default=float)
    )


if __name__ == "__main__":
    main()
