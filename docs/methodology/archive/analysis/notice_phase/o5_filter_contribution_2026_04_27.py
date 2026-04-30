"""O5 — Filter forensics: per-filter contribution drift across panel thirds.

For each individually locked filter (per Pine versions v5.5/v4.4/v4.3), compute
the rejected-cohort sum sim_R per panel-third. Anomaly = sign reversal across
thirds (filter contribution flips between early/mid/late).

Thin-cohort floor: n>=10 per filter-cohort x panel-third. Below floor: Rule 1
flag, no contribution delta reported (per brief).

Note: the pre-computed O5 CSVs in the Identify corpus characterize bar-level
structure (atr/range/gap), not P&L contribution. P&L contribution must be
computed from O1 sim_R per rejected trade with timestamp_utc partitioning.
The pre-computed O5 covers the structural-cohort question (already in 04-26
H1-H5); this run answers the P&L-contribution question per brief.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS = REPO_ROOT / "docs" / "methodology" / "identify_corpus" / "2026-04-26"

PANEL_START = pd.Timestamp("2022-01-02", tz="UTC")
PANEL_END = pd.Timestamp("2026-04-19", tz="UTC")
THIRDS = [
    ("early", PANEL_START, PANEL_START + (PANEL_END - PANEL_START) / 3),
    ("mid",
     PANEL_START + (PANEL_END - PANEL_START) / 3,
     PANEL_START + 2 * (PANEL_END - PANEL_START) / 3),
    ("late", PANEL_START + 2 * (PANEL_END - PANEL_START) / 3, PANEL_END + pd.Timedelta(days=1)),
]
THIN_FLOOR = 10


def label_third(ts: pd.Timestamp) -> str:
    for name, start, end in THIRDS:
        if start <= ts < end:
            return name
    return "out_of_panel"


def analyze(strat: str) -> dict:
    df = pd.read_csv(CORPUS / f"O1_rejected_trades_{strat}.csv",
                     parse_dates=["timestamp_utc"])
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df["third"] = df["timestamp_utc"].apply(label_third)

    block_cols = [c for c in df.columns
                  if c.startswith("block_") and not c.endswith("_cohort_n")
                  and c not in ("block_day", "block_session", "block_hour")]

    per_filter = []
    for col in block_cols:
        sub = df[df[col] == 1]
        rec = {"filter": col, "per_third": {}, "sign_reversal": False, "thin_any_third": False}
        signs = []
        sums = {}
        for tname, _, _ in THIRDS:
            sub_t = sub[sub["third"] == tname]
            n_t = len(sub_t)
            if n_t < THIN_FLOOR:
                rec["per_third"][tname] = {"n": n_t, "thin": True,
                                           "sum_sim_R": None, "mean_sim_R": None}
                rec["thin_any_third"] = True
                continue
            sum_R = float(sub_t["sim_R"].sum())
            mean_R = float(sub_t["sim_R"].mean())
            rec["per_third"][tname] = {"n": n_t, "thin": False,
                                       "sum_sim_R": sum_R, "mean_sim_R": mean_R}
            signs.append(np.sign(sum_R))
            sums[tname] = sum_R
        if not rec["thin_any_third"] and len(set(signs)) > 1:
            rec["sign_reversal"] = True
            rec["sign_pattern"] = {tname: int(np.sign(sums[tname])) for tname in sums}
        per_filter.append(rec)

    return {"per_filter": per_filter}


def main():
    out = {
        "scope": "O5 filter contribution drift across thirds — Notice 2026-04-27",
        "feed": "OANDA",
        "canonical_status": "PROXY",
        "thin_floor_per_third": THIN_FLOOR,
        "panel_thirds": [{"name": n, "start": s.isoformat(), "end": e.isoformat()}
                         for n, s, e in THIRDS],
        "per_strategy": {},
    }
    flagged = []
    for strat in ["guardian", "striker", "aegis"]:
        res = analyze(strat)
        out["per_strategy"][strat] = res
        for f in res["per_filter"]:
            if f["sign_reversal"]:
                # Magnitude = max |sum_sim_R| across thirds
                mags = [abs(t["sum_sim_R"]) for t in f["per_third"].values()
                        if not t["thin"] and t["sum_sim_R"] is not None]
                flagged.append({
                    "strategy": strat,
                    "filter": f["filter"],
                    "sign_pattern": f["sign_pattern"],
                    "per_third_sum_R": {k: v["sum_sim_R"] for k, v in f["per_third"].items()},
                    "max_magnitude_R": max(mags) if mags else 0,
                })
    flagged.sort(key=lambda d: -d["max_magnitude_R"])
    out["flagged_top3"] = flagged[:3]
    out["total_flagged"] = len(flagged)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
