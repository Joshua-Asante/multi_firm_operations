"""Notice-phase corpus scan.

Reads the seven O-artefacts and surfaces patterns/anomalies for routing
through the three-bucket gate (Closed / Action / Forward).

Per the OANDA amendment: NO Action routing on this corpus. Only Closed
or Forward. Forward findings carry the implicit dependency
"verify on Pepperstone before this question becomes decidable".

Notice does NOT pre-form hypotheses — it surfaces patterns worth questioning.
"""
from __future__ import annotations

import glob
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

CORPUS = Path(__file__).resolve().parents[3] / "docs" / "methodology" / "identify_corpus" / "2026-04-26"


def banner(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def scan_o1():
    banner("O1 — counterfactual rejected-trade simulation")
    for s in ["guardian", "striker", "aegis"]:
        d = pd.read_csv(CORPUS / f"O1_rejected_trades_{s}.csv")
        block_cols = [c for c in d.columns if c.startswith("block_") and not c.endswith("_cohort_n")]
        print(f"\n[{s}] n_total={len(d)}")
        # Per-gate: mean sim_R, mean MFE_R, exit-reason mix
        for bc in block_cols:
            sub = d[d[bc] == 1]
            if len(sub) < 10:
                continue
            tp_pct = (sub["exit_reason"] == "tp").mean() * 100
            stop_pct = (sub["exit_reason"].isin(["stop", "stop_or_be"])).mean() * 100
            stale_pct = (sub["exit_reason"] == "stale").mean() * 100
            print(f"  {bc}: n={len(sub):4d}  mean sim_R={sub['sim_R'].mean():+.3f}  "
                  f"mean MFE_R={sub['mfe_R'].mean():+.2f}  TP={tp_pct:4.1f}%  Stop/BE={stop_pct:4.1f}%  Stale={stale_pct:4.1f}%")


def scan_o2():
    banner("O2 — intra-trade MFE/MAE")
    for s in ["guardian", "striker", "aegis"]:
        d = pd.read_csv(CORPUS / f"O2_trade_paths_{s}.csv")
        # Distribution of MFE_R vs net_pnl_R
        d["realized_R_pct_of_MFE"] = (d["net_pnl_R"] / d["mfe_R"]).replace([np.inf, -np.inf], np.nan)
        give_back = (d["net_pnl_R"] < d["mfe_R"]).mean() * 100
        median_gb = d["realized_R_pct_of_MFE"].median()
        print(f"\n[{s}] n={len(d)}")
        print(f"  mean MFE_R={d['mfe_R'].mean():+.2f}, mean MAE_R={d['mae_R'].mean():.2f}, mean net_R={d['net_pnl_R'].mean():+.3f}")
        print(f"  median time_to_MFE bars={d['time_to_mfe_bars'].median():.0f}, time_to_MAE bars={d['time_to_mae_bars'].median():.0f}")
        print(f"  median hold bars={d['hold_bars'].median():.0f}")
        print(f"  give-back: {give_back:.1f}% trades ended below MFE peak; median realized/MFE={median_gb:.2%}")
        # Exit-signal mix
        for sig, n in d["exit_signal"].value_counts().items():
            print(f"  exit_signal '{sig}': {n}")


def scan_o3():
    banner("O3 — conversion funnel + rolling drift")
    for s in ["guardian", "striker", "aegis"]:
        # Static funnel
        st = pd.read_csv(CORPUS / f"O3_conversion_funnel_{s}.csv")
        print(f"\n[{s}] static funnel:")
        for _, r in st.iterrows():
            print(f"  {r['stage']:30s}  count={r['count']:7d}  rate_vs_uni={r['rate_vs_universe']:.4f}  rate_vs_prev={r['rate_vs_prev_stage']:.4f}")

        # Rolling drift: per-stage slope (early window vs recent window)
        rl = pd.read_csv(CORPUS / f"O3_conversion_rolling_{s}.csv")
        rl["date"] = pd.to_datetime(rl["date"])
        for stage in rl["stage"].unique():
            sub = rl[rl["stage"] == stage].dropna(subset=["rolling_rate"])
            if len(sub) < 200:
                continue
            sub_sorted = sub.sort_values("date")
            # Compare median of first 90 days vs last 90 days
            early = sub_sorted.iloc[:90]["rolling_rate"].median()
            late = sub_sorted.iloc[-90:]["rolling_rate"].median()
            mid = sub_sorted.iloc[len(sub_sorted)//2-45:len(sub_sorted)//2+45]["rolling_rate"].median()
            if pd.notna(early) and pd.notna(late) and early > 0:
                shift = (late - early) / early * 100
                if abs(shift) > 30:  # threshold for flagging drift
                    print(f"  ** drift: {stage} early_med={early:.4f}, mid_med={mid:.4f}, late_med={late:.4f} ({shift:+.1f}%)")


def scan_o4():
    banner("O4 — cross-instrument bar correlation")
    static = pd.read_csv(CORPUS / "O4_bar_corr_static.csv")
    print("\nStatic correlations:")
    print(static.to_string(index=False))

    # Rolling: identify regime shifts
    rl = pd.read_csv(CORPUS / "O4_bar_corr_rolling.csv")
    rl["utc"] = pd.to_datetime(rl["utc"])
    print("\nRolling 60d correlation min/max/last per pair:")
    for col in ["XAUUSD__US30USD", "XAUUSD__USDJPY", "US30USD__USDJPY"]:
        c = rl[col].dropna()
        print(f"  {col}: min={c.min():.3f}, max={c.max():.3f}, last={c.iloc[-1]:.3f}, range={c.max()-c.min():.3f}")

    # Simultaneous adverse windows
    adv = pd.read_csv(CORPUS / "O4_simultaneous_adverse_windows.csv")
    adv["utc_window"] = pd.to_datetime(adv["utc_window"])
    print(f"\nSimultaneous adverse 1σ windows: n={len(adv)}")
    # Time clustering: per-month count
    monthly = adv.groupby(adv["utc_window"].dt.to_period("M")).size()
    print(f"  Months with >5 events: {(monthly > 5).sum()} / {len(monthly)} months")
    print(f"  Top-5 months: ")
    for p, n in monthly.nlargest(5).items():
        print(f"    {p}: {n} events")


def scan_o5():
    banner("O5 — filter forensics: blocked vs unblocked feature comparison")
    for f in sorted(glob.glob(str(CORPUS / "O5_filter_forensics_*.csv"))):
        d = pd.read_csv(f)
        if d.empty or d["cohort"].nunique() < 2:
            continue
        b = d[d["cohort"] == "blocked"].iloc[0]
        u = d[d["cohort"] == "unblocked"].iloc[0]
        if u["n"] == 0:
            continue
        atr_ratio = b["atr_mean"] / u["atr_mean"] if u["atr_mean"] > 0 else float("nan")
        gap_ratio = (b["gap_freq_1xATR"] + 1e-9) / (u["gap_freq_1xATR"] + 1e-9)
        bull_diff = b["bullish_freq"] - u["bullish_freq"]
        range_diff = b["range_exp_freq"] - u["range_exp_freq"]
        flag = ""
        if abs(atr_ratio - 1) > 0.30 or gap_ratio > 2 or abs(bull_diff) > 0.06 or abs(range_diff) > 0.05:
            flag = " ** ANOMALY"
        name = os.path.basename(f).replace("O5_filter_forensics_", "").replace(".csv", "")
        print(f"  {name:42s} ATR_ratio={atr_ratio:.2f}  gap_ratio={gap_ratio:.2f}  bull_diff={bull_diff:+.3f}  rng_diff={range_diff:+.3f}{flag}")


def scan_o6():
    banner("O6 — regime features: per-instrument month drift")
    for sym in ["XAUUSD", "US30USD", "USDJPY"]:
        d = pd.read_csv(CORPUS / f"O6_regime_features_{sym}.csv")
        d["month"] = pd.to_datetime(d["month"])
        # Compare 2022 vs 2026 for ATR and ret_std
        early = d[d["month"].dt.year == 2022]
        late = d[d["month"].dt.year == 2026]
        if early.empty or late.empty:
            continue
        atr_early = early["atr14_mean"].mean()
        atr_late = late["atr14_mean"].mean()
        std_early = early["ret_std"].mean()
        std_late = late["ret_std"].mean()
        gap_early = early["session_gap_p95"].mean()
        gap_late = late["session_gap_p95"].mean()
        rexp_early = early["range_exp_freq"].mean()
        rexp_late = late["range_exp_freq"].mean()
        print(f"\n[{sym}] 2022 mean → 2026 YTD mean:")
        print(f"  ATR(14): {atr_early:.3f} → {atr_late:.3f}  ({(atr_late/atr_early - 1) * 100:+.1f}%)")
        print(f"  ret_std: {std_early:.5f} → {std_late:.5f}  ({(std_late/std_early - 1) * 100:+.1f}%)")
        print(f"  range_exp_freq: {rexp_early:.4f} → {rexp_late:.4f}  ({(rexp_late/rexp_early - 1) * 100:+.1f}%)")
        print(f"  session_gap_p95: {gap_early:.3f} → {gap_late:.3f}")


def scan_o7():
    banner("O7 — slippage realism: fill vs bar-close by boundary")
    for s in ["guardian", "striker", "aegis"]:
        d = pd.read_csv(CORPUS / f"O7_slippage_realism_{s}.csv")
        print(f"\n[{s}] n_legs={len(d)}")
        for (leg, boundary), grp in d.groupby(["leg", "boundary"]):
            n = len(grp)
            if n < 5:
                continue
            d_close_med = grp["delta_vs_bar_close"].median()
            d_close_mean = grp["delta_vs_bar_close"].mean()
            d_close_p95 = grp["delta_vs_bar_close"].abs().quantile(0.95)
            thin = " THIN" if n < 10 else ""
            print(f"  {leg:5s} {boundary:9s} n={n:3d}  delta_vs_close: med={d_close_med:+.3f} mean={d_close_mean:+.3f} |p95|={d_close_p95:.3f}{thin}")


if __name__ == "__main__":
    scan_o1()
    scan_o2()
    scan_o3()
    scan_o4()
    scan_o5()
    scan_o6()
    scan_o7()
