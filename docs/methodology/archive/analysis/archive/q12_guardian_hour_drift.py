"""Q12 — Inquire-phase: Guardian hour-block drift decomposition.

QUESTION (from notice_phase/findings_2026-04-26.md §F2):
  "Decompose Guardian rejected-by-hour-block count by year. If the hour-block
   rejection count is stable in absolute terms but the pre-hour funnel grew,
   the drift is denominator-side. If hour-block rejections fell, the drift
   is numerator-side (hour distribution genuinely shifted)."

PRE-Q GATE (per anthropic-skills:inqhiori-algorithm §3):
  D: Deleted bars not in the pre-hour-stage pool. The cohort of interest is
     {signal_raw==1 AND day_pass==1 AND session_pass==1}; everything else is
     out of scope for this binary. Test: scope (permitted §5).
  S: Compressed to per-year aggregates: (pre_hour_pool_count,
     hour_block_rejected_count, per-block decomposition). Loses per-bar
     granularity but preserves the binary the question asks.
  A: None needed. Two pandas groupby ops, O(seconds).

  Forbidden-D-test self-check: I am NOT applying "the rejected count must
  be lower because that's what the hypothesis predicts" — I run the count
  both ways and let the data answer. The numerator-side and denominator-side
  hypotheses are symmetric in the gate; neither is privileged.

SCOPE BINDING:
  - Source: docs/methodology/identify_corpus/2026-04-26/ (OANDA proxy).
  - No production touch. No parameter change. No allocation, no dd_protection,
    no Pine modification.
  - Outcome routes either Closed (denominator-side, mechanical growth) or
    re-Forward with refined sub-question (numerator-side, real hour shift).

REPRODUCIBILITY: `python analysis/q12_guardian_hour_drift.py`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "identify" / "2026-04-26"))

from common import load_bars, STRATEGIES  # noqa: E402
from filters import EVAL  # noqa: E402

OUT_FILE_CSV = ROOT / "analysis" / "q12_guardian_hour_decomp.csv"
OUT_FILE_JSON = ROOT / "analysis" / "q12_guardian_hour_decomp.json"


HOUR_BLOCK_COLS = [
    "block_TueH08", "block_MonH08", "block_MonH09",
    "block_MonH12", "block_TueH12", "block_ThuH12",
]


def main():
    bars = load_bars(STRATEGIES["guardian"]["bar_symbol"])
    df = EVAL["guardian"](bars)

    # Pre-hour pool: signals that have passed signal_raw + day + session
    # (= bars where the hour-block stage is the next gate)
    pre_hour = (df["signal_raw"] == 1) & (df["day_pass"] == 1) & (df["session_pass"] == 1)
    df["pre_hour"] = pre_hour.astype(int)
    df["hour_rejected"] = (pre_hour & (df["any_hour_block"] == 1)).astype(int)
    df["hour_passed"] = (pre_hour & (df["hour_pass"] == 1)).astype(int)

    # Per-year aggregation
    df["year"] = df.index.year
    yearly = df.groupby("year").agg(
        pre_hour_n=("pre_hour", "sum"),
        hour_rejected_n=("hour_rejected", "sum"),
        hour_passed_n=("hour_passed", "sum"),
        **{
            f"{c}_n": (f"{c}_pre_hour_only", "sum")
            for c in HOUR_BLOCK_COLS
        }
    ) if False else None  # placeholder; we'll build manually below

    # Per-year, per-block decomposition (rebuild cleanly)
    rows = []
    for yr, g in df.groupby("year"):
        gpre = g[pre_hour.loc[g.index]]
        row = {
            "year": int(yr),
            "pre_hour_n": int(g["pre_hour"].sum()),
            "hour_rejected_n": int(g["hour_rejected"].sum()),
            "hour_passed_n": int(g["hour_passed"].sum()),
            "hour_pass_rate": float(g["hour_passed"].sum() / max(g["pre_hour"].sum(), 1)),
        }
        for bc in HOUR_BLOCK_COLS:
            # Count bars where this specific block fired AND the bar was in pre_hour pool
            row[f"{bc}_n"] = int((gpre[bc] == 1).sum())
        rows.append(row)
    yearly_df = pd.DataFrame(rows).sort_values("year")

    yearly_df.to_csv(OUT_FILE_CSV, index=False)

    # Compare first vs last full year
    full_years = yearly_df[(yearly_df["pre_hour_n"] >= 50)].copy()
    if len(full_years) >= 2:
        first = full_years.iloc[0]
        last = full_years.iloc[-1]
        # 2026 may be partial — note it but use 2025 as the "last full year"
        years_full = yearly_df[yearly_df["year"] < 2026]
        if len(years_full) >= 2:
            first = years_full.iloc[0]
            last = years_full.iloc[-1]

        pre_hour_change_pct = (last["pre_hour_n"] - first["pre_hour_n"]) / first["pre_hour_n"] * 100
        rej_change_pct = (last["hour_rejected_n"] - first["hour_rejected_n"]) / first["hour_rejected_n"] * 100 if first["hour_rejected_n"] > 0 else None
        rate_first = first["hour_pass_rate"]
        rate_last = last["hour_pass_rate"]
    else:
        pre_hour_change_pct = rej_change_pct = rate_first = rate_last = None

    # Verdict logic
    # If pre_hour grew significantly more than hour_rejected → denominator-side
    # If hour_rejected fell or stayed flat while pre_hour stable → numerator-side
    # If both grew at similar rates → mechanical (no shift)
    if pre_hour_change_pct is not None and rej_change_pct is not None:
        gap = pre_hour_change_pct - rej_change_pct
        if abs(gap) < 15:
            verdict = "BOTH grew/shrank at similar rates — pass-rate change is small / proportional"
        elif pre_hour_change_pct > rej_change_pct + 15:
            verdict = "DENOMINATOR-side: pre-hour pool grew faster than hour-block rejections"
        else:
            verdict = "NUMERATOR-side: hour-block rejections grew slower than pool, OR fell"
    else:
        verdict = "Insufficient data for verdict"

    summary = {
        "question": "Guardian hour-block drift — denominator vs numerator side",
        "feed": "OANDA",
        "panel_window": "2022-01-02_2026-04-19",
        "canonical_status": "PROXY",
        "instrument": "XAUUSD",
        "strategy": "Guardian v5.5",
        "yearly_table": yearly_df.to_dict("records"),
        "first_full_year": int(first["year"]) if pre_hour_change_pct is not None else None,
        "last_full_year": int(last["year"]) if pre_hour_change_pct is not None else None,
        "pre_hour_change_pct_first_to_last": float(pre_hour_change_pct) if pre_hour_change_pct is not None else None,
        "hour_rejected_change_pct_first_to_last": float(rej_change_pct) if rej_change_pct is not None else None,
        "hour_pass_rate_first_full_year": float(rate_first) if rate_first is not None else None,
        "hour_pass_rate_last_full_year": float(rate_last) if rate_last is not None else None,
        "verdict": verdict,
    }
    OUT_FILE_JSON.write_text(json.dumps(summary, indent=2))

    print("=" * 72)
    print("Q12 — Guardian hour-block drift decomposition")
    print("=" * 72)
    print()
    print("Per-year table:")
    print(yearly_df.to_string(index=False))
    print()
    if pre_hour_change_pct is not None:
        print(f"First full year ({int(first['year'])}): pre_hour_n={int(first['pre_hour_n'])}, "
              f"rejected_n={int(first['hour_rejected_n'])}, pass_rate={rate_first:.4f}")
        print(f"Last full year  ({int(last['year'])}): pre_hour_n={int(last['pre_hour_n'])}, "
              f"rejected_n={int(last['hour_rejected_n'])}, pass_rate={rate_last:.4f}")
        print(f"  pre_hour change: {pre_hour_change_pct:+.1f}%")
        print(f"  rejected change: {rej_change_pct:+.1f}%")
    print()
    print(f"Verdict: {verdict}")
    print()
    print(f"Wrote: {OUT_FILE_CSV.name}, {OUT_FILE_JSON.name}")


if __name__ == "__main__":
    main()
