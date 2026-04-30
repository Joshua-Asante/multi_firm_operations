"""Q11 — Inquire-phase: Striker conversion-funnel drift decomposition.

QUESTION (from notice_phase/findings_2026-04-26.md §F1):
  "Decompose Striker `signal_raw` count by hour-of-day and by 6-month period.
   If hour-of-day distribution is stable and total count grew, the drift is
   volume-driven (more breakouts, evenly distributed). If hour-of-day
   distribution shifted toward 13-17 UTC, the drift is regime-driven
   (something is concentrating breakouts in the NY morning window)."

PRE-Q GATE (per anthropic-skills:inqhiori-algorithm §3):
  D: Deleted the post-filter cohort (bars where signal_raw==1 AND all_pass==1).
     Test applied: scope — we're asking about the *numerator distribution* of
     signal_raw across hours, not about the funnel composition. The downstream
     filter passes (atr_expanding, session, warmup, dow, body, prev_bullish)
     are not part of the question. Permitted scope D-test (§5).
  S: Compressed the panel to a 2D pivot: rows = hour-of-day (0..23 UTC),
     columns = 6-month period index (0..7), value = count of signal_raw==1
     bars. Loses the per-bar timestamp but preserves the distributional
     anomaly the question asks about. S-test passed: distribution preservation.
  A: No acceleration needed. Pivot is one pandas op; the dataset is one column
     of one bar series. Q-cost is O(seconds).

SCOPE BINDING:
  - Source: docs/methodology/identify_corpus/2026-04-26/ (OANDA proxy).
  - No production touch. No parameter change. No allocation, no dd_protection,
    no Pine modification.
  - Outcome routes either Closed (volume-driven, drift is benign) or Forward
    (regime-driven — escalate next question).

REPRODUCIBILITY: `python analysis/q11_striker_funnel_drift.py`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Reach into the Identify-corpus scripts dir for shared loaders
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "identify" / "2026-04-26"))

from common import load_bars, STRATEGIES  # noqa: E402
from filters import EVAL  # noqa: E402

OUT_DIR = ROOT / "analysis"
OUT_FILE_CSV = OUT_DIR / "q11_striker_funnel_decomp.csv"
OUT_FILE_JSON = OUT_DIR / "q11_striker_funnel_decomp.json"


def main():
    # 1) Bar load + Striker filter eval
    bars = load_bars(STRATEGIES["striker"]["bar_symbol"])
    df = EVAL["striker"](bars)
    sig = df.loc[df["signal_raw"] == 1].copy()

    # 2) Hour-of-day (UTC, since Striker's Pine uses hour(time, "UTC"))
    sig["hour_utc"] = sig.index.hour

    # 3) 6-month period index (0..N) anchored at 2022-01-01
    anchor = pd.Timestamp("2022-01-01", tz="UTC")
    sig["period"] = (
        ((sig.index - anchor).total_seconds() / (86400 * 30 * 6)).astype(int)
    )

    # 4) Pivot: hour × period → count
    pivot = sig.pivot_table(
        index="hour_utc", columns="period",
        values="signal_raw", aggfunc="count", fill_value=0,
    )
    # Ensure all hours 0..23 represented
    pivot = pivot.reindex(range(24), fill_value=0)
    pivot.columns = [f"P{p}" for p in pivot.columns]
    pivot.to_csv(OUT_FILE_CSV)

    # 5) Period totals
    period_totals = pivot.sum(axis=0)

    # 6) Hour-distribution per period (P(hour | signal in period))
    hour_dist = pivot.div(period_totals, axis=1)

    # 7) Fraction of signals in 13-17 UTC per period (Striker session window)
    in_session_hours = list(range(13, 17))
    frac_session = pivot.loc[in_session_hours].sum(axis=0) / period_totals
    frac_session = frac_session.round(4)

    # 8) KL divergence each period vs P0 (early reference)
    p0 = hour_dist.iloc[:, 0].values
    p0_safe = np.where(p0 == 0, 1e-12, p0)

    kl_vs_p0 = {}
    for col in hour_dist.columns:
        p = hour_dist[col].values
        p_safe = np.where(p == 0, 1e-12, p)
        kl = np.sum(p_safe * np.log(p_safe / p0_safe))
        kl_vs_p0[col] = float(kl)

    # 9) Statistical test: chi-square hour distribution P_last vs P_first
    last_col = hour_dist.columns[-1]
    first_col = hour_dist.columns[0]
    obs_last = pivot[last_col].values
    n_last = obs_last.sum()
    expected_under_first = (hour_dist[first_col].values * n_last)
    # Drop hours with expected < 5 to keep chi-square valid
    mask = expected_under_first >= 5
    if mask.sum() >= 2:
        chi2 = np.sum(
            (obs_last[mask] - expected_under_first[mask]) ** 2 /
            expected_under_first[mask]
        )
        df_chi = mask.sum() - 1
        # Crude p-value via scipy if available; otherwise leave as chi2 stat
        try:
            from scipy.stats import chi2 as chi2_dist
            p_chi = 1 - chi2_dist.cdf(chi2, df_chi)
        except ImportError:
            p_chi = None
    else:
        chi2, df_chi, p_chi = None, None, None

    # 10) Output summary
    summary = {
        "question": "Striker funnel drift — hour-of-day distribution decomposition",
        "feed": "OANDA",
        "panel_window": "2022-01-02_2026-04-19",
        "canonical_status": "PROXY",
        "instrument": "US30USD",
        "strategy": "Striker v4.4",
        "n_periods": len(period_totals),
        "period_totals": {c: int(v) for c, v in period_totals.items()},
        "frac_signals_in_13_17_utc_per_period": {c: float(v) for c, v in frac_session.items()},
        "kl_vs_p0_per_period": kl_vs_p0,
        "chi_square_last_vs_first": {
            "stat": float(chi2) if chi2 is not None else None,
            "df": int(df_chi) if df_chi is not None else None,
            "p_value": float(p_chi) if p_chi is not None else None,
            "valid_hours_n": int(mask.sum()) if mask is not None else None,
        },
        "interpretation_keys": {
            "frac_session_increase_means": "more signals concentrating in 13-17 UTC NY morning window",
            "kl_increasing_with_period": "hour-distribution shape diverging from early-panel reference",
            "chi_square_p_low": "shape difference is statistically significant",
        },
    }
    OUT_FILE_JSON.write_text(json.dumps(summary, indent=2))

    # Stdout report
    print("=" * 72)
    print("Q11 — Striker funnel drift decomposition")
    print("=" * 72)
    print(f"Total signal_raw bars across panel: {pivot.values.sum():,}")
    print()
    print("Per-period totals + frac in 13-17 UTC + KL vs P0:")
    print(f"  {'Period':<6} {'Total':>7} {'Frac_13-17_UTC':>16} {'KL_vs_P0':>10}")
    for col in pivot.columns:
        n = int(period_totals[col])
        f = float(frac_session[col])
        k = float(kl_vs_p0[col])
        print(f"  {col:<6} {n:>7} {f:>16.4f} {k:>10.4f}")
    print()
    print("Top-3 hours per period (where signals concentrate):")
    for col in pivot.columns:
        top3 = pivot[col].nlargest(3)
        top3_str = ", ".join(f"{h:02d}:{int(c)}" for h, c in top3.items())
        print(f"  {col}: {top3_str}")
    print()
    print(f"Chi-square last_period vs first_period hour-distribution:")
    print(f"  stat = {chi2:.2f}, df = {df_chi}, p = {p_chi:.6f}")
    print()
    print(f"Wrote: {OUT_FILE_CSV.name}, {OUT_FILE_JSON.name}")


if __name__ == "__main__":
    main()
