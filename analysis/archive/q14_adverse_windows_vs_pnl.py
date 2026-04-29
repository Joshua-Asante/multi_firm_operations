"""Q14 — Inquire-phase: simultaneous-adverse 1σ windows vs strategy P&L.

QUESTION (from notice_phase/findings_2026-04-26.md §G2):
  "Cross-tabulate the 213 simultaneous-adverse 1σ windows against actual
   strategy-P&L on each respective trading day. If the windows align with
   realized loss days for multiple strategies, this is a portfolio-DD
   signal hiding inside the bar panel. If they distribute neutrally across
   P&L outcomes, the bar-level co-movement is not propagating to executed
   trades."

PRE-Q GATE (per anthropic-skills:inqhiori-algorithm §3):
  D: Deleted bars from O4 outside the joined trading-date set (i.e., adverse
     windows on weekends or holidays where no strategy could trade). Test:
     scope (permitted §5) — the question is "co-locate with strategy P&L",
     so windows on no-trade dates are out of the question's universe. Did
     NOT delete any low-magnitude adverse windows or any "doesn't fit my
     model" cohort (forbidden D-test self-check passed).
  S: Compressed to per-(date, strategy) frame: one row per trade with
     (exit_date_NY, strategy, net_pnl_R, adverse_windows_today).
     Loses bar-level granularity but preserves the question's binary.
  A: None needed — three small CSV joins, O(seconds).

  Forbidden-D-test self-check: I am NOT testing "does P&L correlate with
  adverse windows in the way I expect"; I run two-sided distribution tests
  on the per-trade P&L by adverse-day flag and let the data answer.

SCOPE BINDING:
  - Source: docs/methodology/identify_corpus/2026-04-26/ (OANDA proxy).
  - No production touch. No parameter change.
  - Outcome routes Closed (P&L independent of adverse-window days) or
    re-Forward with refined sub-question (correlated → potential
    portfolio-DD signal worth deeper investigation).

REPRODUCIBILITY: `python analysis/q14_adverse_windows_vs_pnl.py`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "identify" / "2026-04-26"))

from common import STRATEGIES, PARAMS, load_tv, utc_from_tv  # noqa: E402

CORPUS = ROOT / "docs" / "methodology" / "identify_corpus" / "2026-04-26"
OUT_CSV_TRADES = ROOT / "analysis" / "q14_trades_with_adverse_flag.csv"
OUT_CSV_DAILY = ROOT / "analysis" / "q14_daily_portfolio.csv"
OUT_JSON = ROOT / "analysis" / "q14_adverse_vs_pnl.json"


def load_adverse_windows() -> pd.DataFrame:
    df = pd.read_csv(CORPUS / "O4_simultaneous_adverse_windows.csv")
    df["utc_window"] = pd.to_datetime(df["utc_window"], utc=True)
    # Trading date = NY-local date (matches strategy TZ semantics)
    df["date_ny"] = df["utc_window"].dt.tz_convert("America/New_York").dt.date
    return df


def load_strategy_trades(strategy: str) -> pd.DataFrame:
    """Per-trade frame with NY-local exit date and net_pnl_R."""
    p = PARAMS[strategy]
    tv = load_tv(strategy)
    tv = tv.dropna(subset=["entry_time", "exit_time", "net_pnl_pct"]).copy()

    # exit_time is NY-local naive; convert to NY-local date
    tv["exit_date_ny"] = tv["exit_time"].dt.date
    tv["entry_date_ny"] = tv["entry_time"].dt.date
    tv["net_pnl_R"] = tv["net_pnl_pct"] / p["risk_pct"]
    tv["strategy"] = strategy
    return tv[[
        "Trade #", "strategy", "entry_date_ny", "exit_date_ny",
        "net_pnl_pct", "net_pnl_R",
    ]].rename(columns={"Trade #": "trade_id"})


def two_sample_test(a: np.ndarray, b: np.ndarray) -> dict:
    """Mann-Whitney U + summary stats, no scipy dependency required."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    a = a[~np.isnan(a)]
    b = b[~np.isnan(b)]
    if len(a) == 0 or len(b) == 0:
        return {"n_a": int(len(a)), "n_b": int(len(b)), "mean_a": None,
                "mean_b": None, "diff": None, "mw_u": None, "mw_p": None}
    res = {
        "n_a": int(len(a)),
        "n_b": int(len(b)),
        "mean_a": float(a.mean()),
        "mean_b": float(b.mean()),
        "median_a": float(np.median(a)),
        "median_b": float(np.median(b)),
        "diff_mean": float(a.mean() - b.mean()),
        "diff_median": float(np.median(a) - np.median(b)),
        "loss_rate_a": float((a < 0).mean()),
        "loss_rate_b": float((b < 0).mean()),
    }
    try:
        from scipy.stats import mannwhitneyu
        u, p = mannwhitneyu(a, b, alternative="two-sided")
        res["mw_u"] = float(u)
        res["mw_p"] = float(p)
    except ImportError:
        res["mw_u"], res["mw_p"] = None, None
    return res


def main():
    adv = load_adverse_windows()
    adv_per_day = adv.groupby("date_ny").size().rename("adverse_windows_today").reset_index()
    print(f"Adverse-window days: {len(adv_per_day)} distinct trading dates "
          f"(of {adv['date_ny'].nunique()} unique calendar dates)")

    # Build trade frames
    all_trades = []
    for s in STRATEGIES:
        all_trades.append(load_strategy_trades(s))
    trades = pd.concat(all_trades, ignore_index=True)

    # Join adverse-window count by exit date
    trades = trades.merge(adv_per_day, left_on="exit_date_ny", right_on="date_ny",
                          how="left")
    trades["adverse_windows_today"] = trades["adverse_windows_today"].fillna(0).astype(int)
    trades["has_adverse_today"] = (trades["adverse_windows_today"] > 0).astype(int)
    trades.to_csv(OUT_CSV_TRADES, index=False)

    print(f"\nTotal trades joined: {len(trades)}")
    print(f"  on adverse-window days: {(trades['has_adverse_today'] == 1).sum()}")
    print(f"  on non-adverse days:    {(trades['has_adverse_today'] == 0).sum()}")

    # Per-strategy two-sample test on net_pnl_R
    per_strat = {}
    for s in STRATEGIES:
        sub = trades[trades["strategy"] == s]
        a = sub.loc[sub["has_adverse_today"] == 1, "net_pnl_R"].values
        b = sub.loc[sub["has_adverse_today"] == 0, "net_pnl_R"].values
        per_strat[s] = two_sample_test(a, b)

    # Per-day portfolio aggregation: sum net_pnl_R across all strategies per date
    daily = trades.groupby("exit_date_ny").agg(
        total_pnl_R=("net_pnl_R", "sum"),
        n_trades=("net_pnl_R", "size"),
        n_strategies=("strategy", "nunique"),
        any_adverse_today=("has_adverse_today", "max"),
        adverse_windows_today=("adverse_windows_today", "max"),
    ).reset_index()
    daily.to_csv(OUT_CSV_DAILY, index=False)

    portfolio_test = two_sample_test(
        daily.loc[daily["any_adverse_today"] == 1, "total_pnl_R"].values,
        daily.loc[daily["any_adverse_today"] == 0, "total_pnl_R"].values,
    )

    # Multi-strategy concurrent-loss test: how often do >=2 strategies lose on the same day?
    multi_loss = trades.groupby("exit_date_ny").apply(
        lambda g: (g["net_pnl_R"] < 0).sum(), include_groups=False
    ).rename("n_losing")
    multi_loss = multi_loss.reset_index()
    multi_loss = multi_loss.merge(adv_per_day, left_on="exit_date_ny", right_on="date_ny", how="left")
    multi_loss["adverse_windows_today"] = multi_loss["adverse_windows_today"].fillna(0).astype(int)
    multi_loss["has_adverse_today"] = (multi_loss["adverse_windows_today"] > 0).astype(int)

    n_total_days = len(multi_loss)
    multi_loss_days = (multi_loss["n_losing"] >= 2)
    multi_loss_rate_overall = float(multi_loss_days.mean())
    multi_loss_rate_adverse = float(multi_loss_days[multi_loss["has_adverse_today"] == 1].mean()) if (multi_loss["has_adverse_today"] == 1).any() else None
    multi_loss_rate_nonadv = float(multi_loss_days[multi_loss["has_adverse_today"] == 0].mean()) if (multi_loss["has_adverse_today"] == 0).any() else None

    # Concentration of adverse windows on actual trading days
    n_adv_unique_dates = adv["date_ny"].nunique()
    n_adv_unique_trade_dates = trades.loc[trades["has_adverse_today"] == 1, "exit_date_ny"].nunique()

    summary = {
        "question": "Simultaneous-adverse 1σ windows vs strategy P&L",
        "feed": "OANDA",
        "panel_window": "2022-01-02_2026-04-19",
        "canonical_status": "PROXY",
        "n_adverse_windows_total": int(len(adv)),
        "n_adverse_dates_total": int(n_adv_unique_dates),
        "n_adverse_dates_with_trade": int(n_adv_unique_trade_dates),
        "per_strategy_two_sample_test": per_strat,
        "portfolio_per_day_test": portfolio_test,
        "multi_strategy_loss_test": {
            "n_total_trading_days": int(n_total_days),
            "rate_2plus_strategies_losing_overall": multi_loss_rate_overall,
            "rate_2plus_strategies_losing_on_adverse_days": multi_loss_rate_adverse,
            "rate_2plus_strategies_losing_on_nonadverse_days": multi_loss_rate_nonadv,
        },
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2))

    # Stdout
    print()
    print("=" * 72)
    print("Per-strategy two-sample test (adverse-day vs non-adverse-day trades)")
    print("=" * 72)
    print(f"{'Strategy':10s} {'n_adv':>6} {'n_norm':>7} {'meanR_adv':>10} {'meanR_norm':>11} {'diff':>8} {'lossR_adv':>10} {'lossR_norm':>11} {'MW_p':>7}")
    for s, r in per_strat.items():
        mw_p = f"{r['mw_p']:.4f}" if r['mw_p'] is not None else "n/a"
        print(f"{s:10s} {r['n_a']:>6} {r['n_b']:>7} {r['mean_a']:>+10.3f} {r['mean_b']:>+11.3f} "
              f"{r['diff_mean']:>+8.3f} {r['loss_rate_a']:>10.3f} {r['loss_rate_b']:>11.3f} {mw_p:>7}")

    print()
    print("=" * 72)
    print("Per-day portfolio sum_R (across strategies trading that day)")
    print("=" * 72)
    r = portfolio_test
    mw_p = f"{r['mw_p']:.4f}" if r['mw_p'] is not None else "n/a"
    print(f"  Adverse days: n={r['n_a']}, mean_R={r['mean_a']:+.3f}, median_R={r['median_a']:+.3f}, loss_rate={r['loss_rate_a']:.3f}")
    print(f"  Normal days:  n={r['n_b']}, mean_R={r['mean_b']:+.3f}, median_R={r['median_b']:+.3f}, loss_rate={r['loss_rate_b']:.3f}")
    print(f"  Mann-Whitney p (two-sided): {mw_p}")

    print()
    print("=" * 72)
    print("Multi-strategy concurrent loss (>=2 strategies losing on same day)")
    print("=" * 72)
    print(f"  Total trading days: {n_total_days}")
    print(f"  Overall multi-loss rate: {multi_loss_rate_overall:.3f}")
    print(f"  On adverse days:        {multi_loss_rate_adverse:.3f}")
    print(f"  On non-adverse days:    {multi_loss_rate_nonadv:.3f}")

    print()
    print(f"Adverse calendar dates total: {n_adv_unique_dates}; that overlap a strategy trade exit date: {n_adv_unique_trade_dates}")
    print()
    print(f"Wrote: {OUT_CSV_TRADES.name}, {OUT_CSV_DAILY.name}, {OUT_JSON.name}")


if __name__ == "__main__":
    main()
