"""Q15 — Inquire-phase: Aegis monthly count/PF vs USDJPY vol compression.

QUESTION (from notice_phase/findings_2026-04-26.md §I2):
  "Compute Aegis monthly trade count and PF over the panel; correlate
   against monthly USDJPY ret_std and ATR(14) from O6. If Aegis trade rate
   and PF both move with USDJPY vol in the expected direction (more signals
   + tighter edge in higher-vol months), vol compression is a known regime
   substrate and the locked parameters' robustness is the answer. If Aegis
   behavior is decoupled from USDJPY vol, the lock-decision MC may underweight
   the late-panel vol-compression regime in its sampling."

PRE-Q GATE (per anthropic-skills:inqhiori-algorithm §3):
  D: Deleted months with no Aegis trades from the PF computation (PF
     undefined when no trades). Cardinality test (permitted §5). Did NOT
     delete low-vol or high-vol months from either side — the *whole point*
     is to test the coupling across the vol distribution. Forbidden-D-test
     self-check: passed.
  S: Compressed to per-month (Aegis_count, Aegis_PF, Aegis_meanR,
     USDJPY_atr14_mean, USDJPY_ret_std). 4-yr panel × 1 month = ~52 rows.
     Loses per-trade granularity but preserves the question's coupling.
  A: None — small panel.

  Forbidden-D-test self-check #2: I am NOT pre-classifying months as
  "compression regime" vs "expansion regime" — I correlate continuously
  across the panel. Discrete regime classification would encode my
  hypothesis ("late-panel is vol compression"); continuous correlation
  lets the data answer.

SCOPE BINDING:
  - Source: docs/methodology/identify_corpus/2026-04-26/ (OANDA proxy).
  - No production touch.
  - Outcome routes Closed (vol-coupled, locked params absorb the substrate)
    or Forward (decoupled, MC may underweight late-panel regime — gated on
    Pepperstone re-verification per amendment).

REPRODUCIBILITY: `python analysis/q15_aegis_vol_coupling.py`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "identify" / "2026-04-26"))

from common import STRATEGIES, PARAMS, load_tv  # noqa: E402

CORPUS = ROOT / "docs" / "methodology" / "identify_corpus" / "2026-04-26"
OUT_CSV = ROOT / "analysis" / "q15_aegis_monthly_vs_vol.csv"
OUT_JSON = ROOT / "analysis" / "q15_aegis_vol_coupling.json"


def aegis_monthly() -> pd.DataFrame:
    """Per-month Aegis trade count, win/loss aggregates, PF, mean R."""
    risk_pct = PARAMS["aegis"]["risk_pct"]
    tv = load_tv("aegis")
    tv = tv.dropna(subset=["exit_time", "net_pnl_pct"]).copy()
    tv["month"] = tv["exit_time"].dt.to_period("M")
    tv["net_pnl_R"] = tv["net_pnl_pct"] / risk_pct
    tv["is_win"] = (tv["net_pnl_pct"] > 0).astype(int)

    agg = tv.groupby("month").agg(
        n_trades=("net_pnl_R", "size"),
        n_wins=("is_win", "sum"),
        gross_profit_R=("net_pnl_R", lambda x: x[x > 0].sum()),
        gross_loss_R=("net_pnl_R", lambda x: -x[x < 0].sum()),  # positive magnitude
        mean_R=("net_pnl_R", "mean"),
        sum_R=("net_pnl_R", "sum"),
    )
    agg["win_rate"] = agg["n_wins"] / agg["n_trades"]
    agg["pf"] = agg["gross_profit_R"] / agg["gross_loss_R"].replace(0, np.nan)
    agg = agg.reset_index()
    agg["month"] = agg["month"].astype(str)
    return agg


def usdjpy_monthly() -> pd.DataFrame:
    df = pd.read_csv(CORPUS / "O6_regime_features_USDJPY.csv")
    return df[["month", "atr14_mean", "atr14_median", "ret_std",
               "range_exp_freq", "session_gap_p95"]]


def correlations(df: pd.DataFrame) -> dict:
    """Pearson and Spearman between Aegis metrics and USDJPY vol metrics."""
    pairs = [
        ("n_trades", "ret_std"),
        ("n_trades", "atr14_mean"),
        ("pf", "ret_std"),
        ("pf", "atr14_mean"),
        ("mean_R", "ret_std"),
        ("mean_R", "atr14_mean"),
        ("win_rate", "ret_std"),
        ("win_rate", "atr14_mean"),
    ]
    out = {}
    for a, b in pairs:
        sub = df[[a, b]].dropna()
        if len(sub) < 5:
            out[f"{a}_vs_{b}"] = {"n": len(sub), "pearson": None, "spearman": None, "p_pearson": None}
            continue
        x = sub[a].values
        y = sub[b].values
        # Manual Pearson (no scipy required for r; p needs scipy)
        x_mean, y_mean = x.mean(), y.mean()
        cov = ((x - x_mean) * (y - y_mean)).mean()
        sx, sy = x.std(ddof=0), y.std(ddof=0)
        pearson_r = float(cov / (sx * sy)) if sx > 0 and sy > 0 else None
        # Spearman via ranks
        rx = pd.Series(x).rank().values
        ry = pd.Series(y).rank().values
        rx_m, ry_m = rx.mean(), ry.mean()
        cov_r = ((rx - rx_m) * (ry - ry_m)).mean()
        srx, sry = rx.std(ddof=0), ry.std(ddof=0)
        spearman_r = float(cov_r / (srx * sry)) if srx > 0 and sry > 0 else None
        # p-value via t-test on Pearson (approx) if scipy available
        try:
            from scipy.stats import pearsonr, spearmanr
            pr, p_pr = pearsonr(x, y)
            sr, p_sr = spearmanr(x, y)
            out[f"{a}_vs_{b}"] = {
                "n": len(sub),
                "pearson": float(pr),
                "p_pearson": float(p_pr),
                "spearman": float(sr),
                "p_spearman": float(p_sr),
            }
        except ImportError:
            out[f"{a}_vs_{b}"] = {
                "n": len(sub),
                "pearson": pearson_r,
                "p_pearson": None,
                "spearman": spearman_r,
                "p_spearman": None,
            }
    return out


def main():
    aegis = aegis_monthly()
    usdjpy = usdjpy_monthly()

    df = usdjpy.merge(aegis, on="month", how="left")
    # months with no Aegis trades: n_trades = NaN; keep for trade-count corr
    df["n_trades_filled"] = df["n_trades"].fillna(0)

    # Trade-count correlation uses the filled-zero series (months with 0 trades are
    # data, not missing). PF/mean_R correlations use only months with trades (PF
    # undefined otherwise — D step in the gate).
    df_for_count = df.copy()
    df_for_count["n_trades"] = df_for_count["n_trades_filled"]
    corr_count = correlations(df_for_count)

    df_for_pf = df.dropna(subset=["pf"]).copy()
    corr_pf = correlations(df_for_pf)

    # Late vs early panel split — informational, not a D-test
    df["year"] = df["month"].str[:4].astype(int)
    early = df[df["year"] <= 2023]
    late = df[df["year"] >= 2025]
    early_avg = {
        "n_trades_per_mo": float(early["n_trades_filled"].mean()),
        "pf": float(early["pf"].mean(skipna=True)) if early["pf"].notna().any() else None,
        "mean_R": float(early["mean_R"].mean(skipna=True)) if early["mean_R"].notna().any() else None,
        "win_rate": float(early["win_rate"].mean(skipna=True)) if early["win_rate"].notna().any() else None,
        "ret_std_avg": float(early["ret_std"].mean()),
        "atr14_avg": float(early["atr14_mean"].mean()),
    }
    late_avg = {
        "n_trades_per_mo": float(late["n_trades_filled"].mean()),
        "pf": float(late["pf"].mean(skipna=True)) if late["pf"].notna().any() else None,
        "mean_R": float(late["mean_R"].mean(skipna=True)) if late["mean_R"].notna().any() else None,
        "win_rate": float(late["win_rate"].mean(skipna=True)) if late["win_rate"].notna().any() else None,
        "ret_std_avg": float(late["ret_std"].mean()),
        "atr14_avg": float(late["atr14_mean"].mean()),
    }

    # Verdict — informal scoring
    # "Vol-coupled in expected direction" = positive corr (count or PF) with vol
    expected_signs = {
        "n_trades_vs_ret_std": "pos",
        "n_trades_vs_atr14_mean": "pos",
        "pf_vs_ret_std": "pos",
        "pf_vs_atr14_mean": "pos",
    }
    coupled_count = 0
    decoupled_count = 0
    inverse_count = 0
    detail = {}
    for k, expected in expected_signs.items():
        # Pull from whichever source has the value
        src = corr_count if k.startswith("n_trades") else corr_pf
        d = src[k]
        r = d.get("pearson")
        p = d.get("p_pearson")
        if r is None:
            decoupled_count += 1
            verdict = "no-data"
        elif p is not None and p > 0.10:
            decoupled_count += 1
            verdict = "no significant correlation"
        elif (expected == "pos" and r > 0) or (expected == "neg" and r < 0):
            coupled_count += 1
            verdict = f"expected direction (r={r:+.3f}, p={p})"
        else:
            inverse_count += 1
            verdict = f"INVERSE direction (r={r:+.3f}, p={p})"
        detail[k] = {"expected": expected, "verdict": verdict, **d}

    summary = {
        "question": "Aegis monthly count/PF vs USDJPY vol — coupled or decoupled?",
        "feed": "OANDA",
        "panel_window": "2022-01-02_2026-04-19",
        "canonical_status": "PROXY",
        "n_months_total": int(len(df)),
        "n_months_with_aegis_trade": int(df["n_trades"].notna().sum()),
        "n_months_with_pf_defined": int(df["pf"].notna().sum()),
        "early_panel_2022_2023_avg": early_avg,
        "late_panel_2025_2026_avg": late_avg,
        "correlations": detail,
        "summary_counts": {
            "coupled_in_expected_direction": coupled_count,
            "no_significant_correlation": decoupled_count,
            "inverse_direction": inverse_count,
        },
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2))

    # Save merged table for reproducibility
    df.to_csv(OUT_CSV, index=False)

    # Stdout
    print("=" * 72)
    print("Q15 — Aegis monthly count/PF vs USDJPY vol")
    print("=" * 72)
    print()
    print(f"Months total:               {len(df)}")
    print(f"Months with Aegis trade:    {df['n_trades'].notna().sum()}")
    print(f"Months with PF defined:     {df['pf'].notna().sum()}")
    print()
    print(f"Early panel (2022-2023): n_trades/mo = {early_avg['n_trades_per_mo']:.2f}, "
          f"PF = {early_avg['pf']:.2f}, ret_std = {early_avg['ret_std_avg']:.5f}, ATR = {early_avg['atr14_avg']:.4f}")
    print(f"Late panel  (2025-2026): n_trades/mo = {late_avg['n_trades_per_mo']:.2f}, "
          f"PF = {late_avg['pf']:.2f}, ret_std = {late_avg['ret_std_avg']:.5f}, ATR = {late_avg['atr14_avg']:.4f}")
    print()
    print("Correlations (Pearson r, p):")
    for k, d in detail.items():
        if d["pearson"] is None:
            continue
        p_str = f"{d['p_pearson']:.4f}" if d["p_pearson"] is not None else "n/a"
        print(f"  {k:30s}  r = {d['pearson']:+.3f},  p = {p_str},  verdict: {d['verdict']}")
    print()
    print(f"Summary: {coupled_count} coupled, {decoupled_count} decoupled, {inverse_count} inverse")
    print()
    print(f"Wrote: {OUT_CSV.name}, {OUT_JSON.name}")


if __name__ == "__main__":
    main()
