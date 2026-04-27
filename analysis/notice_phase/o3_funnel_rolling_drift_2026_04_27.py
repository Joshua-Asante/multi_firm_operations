"""O3 — Conversion-funnel rolling drift for Notice 2026-04-27 (OANDA-proxy).

Anomaly criterion (per brief):
  - Rolling 6-month conversion rate at any funnel stage that exhibits
    monotonic drift > 30% across the panel, OR
  - A discontinuity (single 6-month window > 2sigma from rolling mean).
Thin-cohort floor: rolling universe count >= 30 per 6-month period.

Per-strategy: aggregate the 90d rolling daily values into 9 non-overlapping
6-month periods (matching the Q11/Q12 04-26 panel split), average within
period, then test monotonic drift and discontinuity.

Note: this brief explicitly does NOT carry forward 04-26 verdicts. We re-run
on the same OANDA corpus with this brief's thresholds. Aegis specifically
flagged per Q15 residual (late-panel improvement uncharacterized).
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS = REPO_ROOT / "docs" / "methodology" / "identify_corpus" / "2026-04-26"

PANEL_START = pd.Timestamp("2022-01-01")
PANEL_END = pd.Timestamp("2026-04-19")
PERIOD_MONTHS = 6
THIN_FLOOR = 30


def period_label(date: pd.Timestamp) -> int:
    months = (date.year - PANEL_START.year) * 12 + (date.month - PANEL_START.month)
    return months // PERIOD_MONTHS


def analyze_strategy(strat: str) -> dict:
    df = pd.read_csv(CORPUS / f"O3_conversion_rolling_{strat}.csv", parse_dates=["date"])
    df["period"] = df["date"].apply(period_label)

    out_per_stage = {}
    for stage, sub in df.groupby("stage"):
        per_period = sub.groupby("period").agg(
            mean_rate=("rolling_rate", "mean"),
            mean_universe=("rolling_universe_count", "mean"),
            n_obs=("rolling_rate", "size"),
            min_universe=("rolling_universe_count", "min"),
        ).reset_index()
        per_period["thin"] = per_period["mean_universe"] < THIN_FLOOR

        valid = per_period[~per_period["thin"]].copy()
        if len(valid) < 2:
            out_per_stage[stage] = {
                "thin_all": True,
                "per_period": per_period.to_dict("records"),
            }
            continue

        # Drift: first full period vs last full period (drop partial period >7 if last has <90 days obs)
        # Period 8 = 2026-Q1+ partial (panel ends 2026-04-19; period 8 covers 2026-01..2026-06)
        # Use periods with n_obs >= 60 days (~2/3 of a 6-month bucket)
        full = valid[valid["n_obs"] >= 60].copy()
        if len(full) < 2:
            full = valid

        first_rate = float(full["mean_rate"].iloc[0])
        last_rate = float(full["mean_rate"].iloc[-1])
        rel_drift = (last_rate - first_rate) / first_rate if first_rate > 0 else float("nan")

        # Sustained-direction check: split panel into thirds; verify first-vs-last
        # endpoint change matches first-third vs last-third aggregate change in sign
        # AND last-third differs from first-third by > 20% (drift not endpoint-only).
        n = len(full)
        third = max(1, n // 3)
        first_third_mean = float(full["mean_rate"].iloc[:third].mean())
        last_third_mean = float(full["mean_rate"].iloc[-third:].mean())
        thirds_rel_change = ((last_third_mean - first_third_mean) / first_third_mean
                              if first_third_mean > 0 else float("nan"))
        sustained = (
            np.sign(last_rate - first_rate) == np.sign(last_third_mean - first_third_mean)
            and abs(thirds_rel_change) > 0.20
        )

        # Discontinuity: any single period > 2sigma from cross-period mean
        rates = valid["mean_rate"].values
        mu = rates.mean()
        sigma = rates.std(ddof=0)
        discontinuity = []
        if sigma > 0:
            for _, r in valid.iterrows():
                z = (r["mean_rate"] - mu) / sigma
                if abs(z) > 2:
                    discontinuity.append({
                        "period": int(r["period"]),
                        "mean_rate": float(r["mean_rate"]),
                        "z": float(z),
                    })

        out_per_stage[stage] = {
            "thin_all": False,
            "per_period": per_period.to_dict("records"),
            "first_period_rate": first_rate,
            "last_period_rate": last_rate,
            "relative_drift": rel_drift,
            "first_third_mean": first_third_mean,
            "last_third_mean": last_third_mean,
            "thirds_rel_change": thirds_rel_change,
            "sustained": sustained,
            "discontinuities_2sigma": discontinuity,
            "drift_anomaly": (abs(rel_drift) > 0.30 and sustained),
            "discontinuity_anomaly": bool(discontinuity),
        }
    return out_per_stage


def main():
    out = {
        "scope": "O3 conversion-funnel rolling drift — Notice 2026-04-27",
        "feed": "OANDA",
        "canonical_status": "PROXY",
        "period_months": PERIOD_MONTHS,
        "thin_floor_universe": THIN_FLOOR,
        "drift_threshold_relative": 0.30,
        "discontinuity_threshold_z": 2.0,
        "per_strategy": {},
    }
    flagged = []
    for strat in ["guardian", "striker", "aegis"]:
        per_stage = analyze_strategy(strat)
        out["per_strategy"][strat] = per_stage
        for stage, info in per_stage.items():
            if info.get("thin_all"):
                continue
            if info["drift_anomaly"]:
                flagged.append({
                    "strategy": strat,
                    "stage": stage,
                    "type": "monotonic_drift",
                    "first_rate": info["first_period_rate"],
                    "last_rate": info["last_period_rate"],
                    "rel_drift": info["relative_drift"],
                })
            if info["discontinuity_anomaly"]:
                for d in info["discontinuities_2sigma"]:
                    flagged.append({
                        "strategy": strat,
                        "stage": stage,
                        "type": "discontinuity_2sigma",
                        "period": d["period"],
                        "rate": d["mean_rate"],
                        "z": d["z"],
                    })

    flagged.sort(key=lambda d: -abs(d.get("rel_drift") or d.get("z") or 0))
    out["flagged_top3"] = flagged[:3]
    out["total_flagged"] = len(flagged)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
