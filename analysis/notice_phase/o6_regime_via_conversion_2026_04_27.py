"""O6 — Regime detection via conversion-rate change, Notice 2026-04-27.

For each strategy, take the FINAL funnel-stage rolling pass rate (trades-taken
/ universe) and aggregate to 6-month periods. Compute period-over-period
delta and z-score (delta normalized by std of all deltas). Flag windows where
>=2 strategies have |z| > 1.0 in OPPOSITE directions.

Per brief: O6 does NOT propose a classifier or overlay. It reports candidate
regime-boundary windows only.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS = REPO_ROOT / "docs" / "methodology" / "identify_corpus" / "2026-04-26"

PANEL_START = pd.Timestamp("2022-01-01")
PERIOD_MONTHS = 6
THIN_FLOOR = 30  # inherits O3's per-stage floor

FINAL_STAGES = {
    "guardian": "s4_hour_pass",
    "striker": "s7_prev_bullish",
    "aegis": "s7_not_block_EOM",
}


def period_label(date: pd.Timestamp) -> int:
    months = (date.year - PANEL_START.year) * 12 + (date.month - PANEL_START.month)
    return months // PERIOD_MONTHS


def period_label_to_window(p: int) -> str:
    start = PANEL_START + pd.DateOffset(months=p * PERIOD_MONTHS)
    end = start + pd.DateOffset(months=PERIOD_MONTHS)
    return f"{start.date()}..{end.date()}"


def per_strategy_period_rates(strat: str) -> pd.DataFrame:
    df = pd.read_csv(CORPUS / f"O3_conversion_rolling_{strat}.csv", parse_dates=["date"])
    df = df[df["stage"] == FINAL_STAGES[strat]].copy()
    df["period"] = df["date"].apply(period_label)
    out = df.groupby("period").agg(
        mean_rate=("rolling_rate", "mean"),
        mean_universe=("rolling_universe_count", "mean"),
        n_obs=("rolling_rate", "size"),
    ).reset_index()
    out["thin"] = out["mean_universe"] < THIN_FLOOR
    return out


def main():
    per_strat = {s: per_strategy_period_rates(s) for s in FINAL_STAGES}

    # Build aligned period × strategy table
    periods = sorted(set().union(*[set(df["period"]) for df in per_strat.values()]))
    table = pd.DataFrame({"period": periods})
    for s, df in per_strat.items():
        col_rate = f"{s}_rate"
        col_thin = f"{s}_thin"
        merged = table.merge(df[["period", "mean_rate", "thin"]], on="period", how="left")
        table[col_rate] = merged["mean_rate"].values
        table[col_thin] = merged["thin"].values

    # Period-over-period delta per strategy
    for s in FINAL_STAGES:
        table[f"{s}_delta"] = table[f"{s}_rate"].diff()

    # Z-score within each strategy's delta distribution
    for s in FINAL_STAGES:
        d = table[f"{s}_delta"].dropna()
        sigma = d.std(ddof=0)
        table[f"{s}_z"] = table[f"{s}_delta"] / sigma if sigma > 0 else np.nan

    # Flag windows where >=2 strategies have |z| > 1.0 with opposite signs
    flagged = []
    for _, row in table.iterrows():
        if pd.isna(row[f"guardian_delta"]):
            continue
        zs = {s: row[f"{s}_z"] for s in FINAL_STAGES}
        thins = {s: row[f"{s}_thin"] for s in FINAL_STAGES}
        # Skip thin
        valid = {s: zs[s] for s in FINAL_STAGES if not thins[s] and not pd.isna(zs[s])}
        if len(valid) < 2:
            continue
        # find pairs with opposite signs and both |z| > 1
        names = list(valid.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = names[i], names[j]
                za, zb = valid[a], valid[b]
                if abs(za) > 1.0 and abs(zb) > 1.0 and np.sign(za) != np.sign(zb):
                    flagged.append({
                        "period": int(row["period"]),
                        "window": period_label_to_window(int(row["period"])),
                        "strategy_a": a,
                        "z_a": float(za),
                        "rate_a": float(row[f"{a}_rate"]),
                        "strategy_b": b,
                        "z_b": float(zb),
                        "rate_b": float(row[f"{b}_rate"]),
                        "magnitude": min(abs(za), abs(zb)),
                    })

    flagged.sort(key=lambda d: -d["magnitude"])

    out = {
        "scope": "O6 conversion-rate regime-boundary candidates — Notice 2026-04-27",
        "feed": "OANDA",
        "canonical_status": "PROXY",
        "final_stages": FINAL_STAGES,
        "period_months": PERIOD_MONTHS,
        "z_threshold": 1.0,
        "thin_floor_universe": THIN_FLOOR,
        "table": table.to_dict("records"),
        "flagged_top3": flagged[:3],
        "total_flagged": len(flagged),
        "explicit_brief_constraint": "O6 reports candidate boundaries; does NOT propose classifier/overlay",
    }
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
