"""O1 — Rejected-universe diagnostic for Notice 2026-04-27 (OANDA-proxy).

For each strategy filter sub-cohort with n>=10 (Rule 1 floor), compute:
  - PF on sim_R (positive_sum / |negative_sum|)
  - Mean sim_R
  - Cohort N
Then compare to accepted-cohort PF and mean realized R from the TV export.

Anomaly rule: rejected sub-cohort with mean sim_R that materially differs from
the accepted-cohort mean realized R (delta > 0.5 R, magnitude floor — the per-
strategy panel sigma for sub-cohort means). Flag top 3 by |delta| across all
strategies × filters.

Per brief: anomalies are described, not explained. No mechanism claims.
"""
from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS = REPO_ROOT / "docs" / "methodology" / "identify_corpus" / "2026-04-26"
TV_DIR = REPO_ROOT / "data" / "tv_exports" / "oanda"

STRATEGIES = {
    "guardian": {
        "rejected": "O1_rejected_trades_guardian.csv",
        "tv_export": "Guardian_Gold_v5.5_OANDA_XAUUSD_2026-04-25_9ae1f.csv",
        "risk_pct": 0.34,
    },
    "striker": {
        "rejected": "O1_rejected_trades_striker.csv",
        "tv_export": "Striker_DJ30_v4.4_OANDA_US30USD_2026-04-25_86e9d.csv",
        "risk_pct": 1.00,
    },
    "aegis": {
        "rejected": "O1_rejected_trades_aegis.csv",
        "tv_export": "Aegis_USDJPY_v4.3_OANDA_USDJPY_2026-04-25_7ee6b.csv",
        "risk_pct": 1.50,
    },
}

THIN_FLOOR = 10


def pf(values: pd.Series) -> float:
    pos = values[values > 0].sum()
    neg = values[values < 0].sum()
    if neg == 0:
        return float("inf") if pos > 0 else float("nan")
    return float(pos / abs(neg))


def accepted_metrics(tv_path: Path, risk_pct: float) -> dict:
    df = pd.read_csv(tv_path)
    df.columns = [c.strip("﻿").strip() for c in df.columns]
    # Pair entries+exits: closed trades = rows with Net P&L %
    pnl_col = "Net P&L %"
    closed = df[df["Type"].astype(str).str.contains("Exit", na=False)].copy()
    closed[pnl_col] = pd.to_numeric(closed[pnl_col], errors="coerce")
    closed = closed.dropna(subset=[pnl_col])
    realized_R = closed[pnl_col] / risk_pct
    return {
        "n": len(closed),
        "mean_R": float(realized_R.mean()),
        "PF": pf(realized_R),
        "win_rate": float((realized_R > 0).mean()),
    }


def main():
    out = {
        "scope": "O1 rejected-universe diagnostic — Notice 2026-04-27",
        "feed": "OANDA",
        "canonical_status": "PROXY",
        "thin_floor_n": THIN_FLOOR,
        "magnitude_floor_R": 0.5,
        "per_strategy": {},
    }
    all_anomalies = []

    for strat, info in STRATEGIES.items():
        rejected = pd.read_csv(CORPUS / info["rejected"])
        accepted = accepted_metrics(TV_DIR / info["tv_export"], info["risk_pct"])

        block_cols = [c for c in rejected.columns if c.startswith("block_") and not c.endswith("_cohort_n")]
        block_cols = [c for c in block_cols if c not in ("block_day", "block_session", "block_hour")]
        # block_day/session/hour are union flags; per-filter flags are the rest

        per_filter = []
        for col in block_cols:
            sub = rejected[rejected[col] == 1]
            n = len(sub)
            row = {
                "filter": col,
                "n": n,
                "thin": n < THIN_FLOOR,
                "rejected_mean_R": None,
                "rejected_PF": None,
                "accepted_mean_R": accepted["mean_R"],
                "accepted_PF": accepted["PF"],
                "delta_mean_R": None,
            }
            if n >= THIN_FLOOR:
                m = float(sub["sim_R"].mean())
                p = pf(sub["sim_R"])
                row["rejected_mean_R"] = m
                row["rejected_PF"] = p
                row["delta_mean_R"] = m - accepted["mean_R"]
            per_filter.append(row)

        out["per_strategy"][strat] = {
            "accepted": accepted,
            "per_filter": per_filter,
        }

        for r in per_filter:
            if r["thin"]:
                continue
            if abs(r["delta_mean_R"]) >= 0.5:
                all_anomalies.append({
                    "strategy": strat,
                    "filter": r["filter"],
                    "n": r["n"],
                    "rejected_mean_R": r["rejected_mean_R"],
                    "rejected_PF": r["rejected_PF"],
                    "accepted_mean_R": r["accepted_mean_R"],
                    "accepted_PF": r["accepted_PF"],
                    "delta_mean_R": r["delta_mean_R"],
                    "abs_delta": abs(r["delta_mean_R"]),
                })

    all_anomalies.sort(key=lambda d: -d["abs_delta"])
    out["flagged_top3"] = all_anomalies[:3]
    out["total_above_floor"] = len(all_anomalies)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
