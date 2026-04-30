"""MSEE Phase 8 — Watch-list digest generator.

Computes current values for the indicators listed in
docs/methodology/archive/msee/watch_list.md and writes a dated digest at
analysis/msee/watch_{date}.md plus a JSON sidecar. Designed to run
weekly aligned with the cli.py update cadence.

No Action authorization. Crossings route Forward per
docs/methodology/observation_routing.md.

Reproducibility: `python scripts/msee_watchlist.py [--lookback-quarters N]`
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "identify" / "2026-04-26"))

from common import STRATEGIES, PARAMS, load_bars  # noqa: E402

DAILY_CSV = ROOT / "analysis" / "msee" / "daily_strategy_returns.csv"
OUT_DIR = ROOT / "analysis" / "msee"

ALLOC = {s: PARAMS[s]["risk_pct"] / 100.0 for s in STRATEGIES}
INSTRUMENT_BAR = {
    "guardian": "XAUUSD",
    "striker": "US30USD",
    "aegis": "USDJPY",
}


def joint_loss_days(daily: pd.DataFrame) -> dict:
    """Days where ALL three strategies traded AND all three had R<0."""
    all_traded = (
        (daily["guardian_n_trades"] > 0)
        & (daily["striker_n_trades"] > 0)
        & (daily["aegis_n_trades"] > 0)
    )
    all_loss = (
        (daily["guardian_R"] < 0)
        & (daily["striker_R"] < 0)
        & (daily["aegis_R"] < 0)
    )
    days = daily[all_traded & all_loss]
    return {
        "n_days_all_three_traded": int(all_traded.sum()),
        "n_joint_loss_days": int(len(days)),
        "dates": [d.strftime("%Y-%m-%d") for d in days["exit_date_ny"]],
        "threshold_first_occurrence": 1,
        "crossed": bool(len(days) >= 1),
    }


def stress_corr_GA(daily: pd.DataFrame) -> dict:
    """G/A correlation on most recent rolling 6-month stress slice."""
    out = None
    for s, sym in INSTRUMENT_BAR.items():
        bars = load_bars(sym)
        bars["date"] = bars.index.normalize().date
        cl = bars.groupby("date")["close"].last()
        ret = cl.pct_change().rename(f"{s}_idx_ret")
        out = ret.to_frame() if out is None else out.join(ret, how="outer")
    out["stress_proxy"] = out.abs().max(axis=1)
    out = out.dropna(subset=["stress_proxy"]).reset_index().rename(
        columns={"index": "date"}
    )
    out["date"] = pd.to_datetime(out["date"]).dt.date

    # Trailing 6-month window for stress-flag calibration AND correlation.
    cutoff_d = daily["exit_date_ny"].max().date()
    window_start = cutoff_d - timedelta(days=180)
    daily_w = daily[daily["exit_date_ny"].dt.date >= window_start].copy()
    daily_w["date"] = daily_w["exit_date_ny"].dt.date
    out_w = out[(out["date"] >= window_start) & (out["date"] <= cutoff_d)]

    if len(out_w) == 0 or len(daily_w) == 0:
        return {"window_start": str(window_start), "window_end": str(cutoff_d),
                "stress_threshold": None, "n_stress_days": 0,
                "G_A_stress_corr": None, "crossed": False}
    threshold = float(np.nanpercentile(out_w["stress_proxy"], 95))
    out_w = out_w.assign(is_stress=(out_w["stress_proxy"] >= threshold).astype(int))
    merged = daily_w.merge(out_w[["date", "is_stress"]], on="date", how="left")
    merged["is_stress"] = merged["is_stress"].fillna(0).astype(int)
    stress = merged[merged["is_stress"] == 1]
    n_stress = len(stress)
    if n_stress < 5:
        ga_corr = None
    else:
        x = stress["guardian_R"].values
        y = stress["aegis_R"].values
        if np.std(x) == 0 or np.std(y) == 0:
            ga_corr = None
        else:
            ga_corr = float(np.corrcoef(x, y)[0, 1])
    return {
        "window_start": str(window_start),
        "window_end": str(cutoff_d),
        "stress_threshold": threshold,
        "n_stress_days": int(n_stress),
        "G_A_stress_corr": ga_corr,
        "threshold": 0.30,
        "crossed": bool(ga_corr is not None and ga_corr > 0.30),
    }


def portfolio_quarter_dd(daily: pd.DataFrame) -> dict:
    """Realized portfolio max DD in the most recent calendar quarter."""
    cutoff = daily["exit_date_ny"].max()
    q_start = cutoff - pd.Timedelta(days=90)
    q = daily[daily["exit_date_ny"] >= q_start].copy()
    contrib = sum(q[f"{s}_R"] * ALLOC[s] for s in STRATEGIES)
    cum = contrib.cumsum().values
    peak = np.maximum.accumulate(cum)
    dd = float((peak - cum).max()) if len(cum) > 0 else 0.0
    return {
        "window_start": str(q_start.date()),
        "window_end": str(cutoff.date()),
        "n_trade_dates": int(len(q)),
        "quarter_max_dd_pct": float(dd),
        "soft_warn_threshold": 0.04,
        "hard_warn_threshold": 0.045,
        "soft_warn_crossed": bool(dd > 0.04),
        "hard_warn_crossed": bool(dd > 0.045),
    }


def per_strategy_rolling(daily: pd.DataFrame, strategy: str,
                         window: int) -> dict:
    """Rolling 50-trade WR and R-of-winners for the given strategy.
    Returns {current value, threshold, crossed}."""
    s_only = daily[daily[f"{strategy}_n_trades"] > 0].copy()
    s_only = s_only.sort_values("exit_date_ny").reset_index(drop=True)
    n = len(s_only)
    if n < window:
        return {"n_trade_dates": int(n), "skipped": True,
                "current_WR": None, "current_R_winners": None,
                "WR_threshold": None, "WR_crossed": False}
    last = s_only.tail(window)
    R = last[f"{strategy}_R"]
    wr = float((R > 0).mean())
    R_win = R[R > 0]
    rw = float(R_win.mean()) if len(R_win) > 0 else float("nan")
    # Per-strategy thresholds from watch_list.md.
    wr_thresh = {"guardian": 0.10, "striker": 0.60, "aegis": 0.34}[strategy]
    return {
        "n_trade_dates": int(n),
        "current_WR_last_{}".format(window): wr,
        "current_R_of_winners_last_{}".format(window): rw,
        "WR_threshold": wr_thresh,
        "WR_crossed": bool(wr < wr_thresh),
    }


def aegis_hurst(window_days: int = 90) -> dict:
    """Hurst exponent on USDJPY 15m log-returns over rolling window.
    Uses R/S analysis on log-returns (per memory: applying R/S to log
    PRICES gives spurious H~1; must use returns/increments)."""
    bars = load_bars("USDJPY")
    bars = bars.tail(window_days * 96)  # 96 15m bars per day
    log_returns = np.log(bars["close"]).diff().dropna().values
    if len(log_returns) < 100:
        return {"window_days": window_days, "n_obs": len(log_returns),
                "hurst_H": None, "threshold": 0.55, "crossed": False}
    H = rs_hurst(log_returns)
    return {
        "window_days": window_days,
        "n_obs": int(len(log_returns)),
        "hurst_H": float(H),
        "threshold": 0.55,
        "crossed": bool(H > 0.55),
    }


def rs_hurst(x: np.ndarray) -> float:
    """Standard R/S Hurst exponent on increments x. Powers-of-2 scales."""
    n = len(x)
    if n < 32:
        return float("nan")
    sizes = []
    rs = []
    s = 8
    while s <= n // 4:
        chunks = n // s
        rs_vals = []
        for i in range(chunks):
            seg = x[i * s:(i + 1) * s]
            mu = seg.mean()
            cum = (seg - mu).cumsum()
            R = cum.max() - cum.min()
            S = seg.std(ddof=1)
            if S > 0:
                rs_vals.append(R / S)
        if rs_vals:
            sizes.append(s)
            rs.append(np.mean(rs_vals))
        s *= 2
    if len(sizes) < 3:
        return float("nan")
    log_sizes = np.log(sizes)
    log_rs = np.log(rs)
    slope, _ = np.polyfit(log_sizes, log_rs, 1)
    return float(slope)


def cluster_2_count_quarter(daily: pd.DataFrame) -> dict:
    """Cluster-2 (XAU crash/risk-off) day count this quarter — proxy
    by computing same per-day max-|index-move| and counting top-5%
    days in last 90d."""
    bars_g = load_bars("XAUUSD")
    bars_g["date"] = bars_g.index.normalize().date
    cl = bars_g.groupby("date")["close"].last()
    ret = cl.pct_change()
    cutoff = daily["exit_date_ny"].max().date()
    q_start = cutoff - timedelta(days=90)
    q_ret = ret.loc[(pd.Series(ret.index) >= q_start).values]
    extreme_threshold = 0.040  # 4% absolute XAU daily move = "cluster-2-like" (top-1% of historical XAU daily |ret|)
    n_extreme = int((ret.loc[(pd.Series(ret.index) >= q_start).values].abs()
                     >= extreme_threshold).sum())
    return {
        "window_start": str(q_start),
        "window_end": str(cutoff),
        "n_extreme_xau_days": n_extreme,
        "extreme_threshold_pct": extreme_threshold,
        "info_threshold": 1,
        "info_crossed": bool(n_extreme >= 1),
    }


def main() -> None:
    p = argparse.ArgumentParser(prog="msee_watchlist")
    p.add_argument("--lookback-quarters", type=int, default=1,
                   help="Quarters to look back for portfolio DD (default 1)")
    args = p.parse_args()

    daily = pd.read_csv(DAILY_CSV, parse_dates=["exit_date_ny"])

    digest = {
        "generated": datetime.now().isoformat(),
        "data_panel_window": [str(daily["exit_date_ny"].min().date()),
                              str(daily["exit_date_ny"].max().date())],
        "n_trade_dates": int(len(daily)),
        "indicators": {
            "joint_loss_days": joint_loss_days(daily),
            "G_A_stress_correlation": stress_corr_GA(daily),
            "portfolio_quarter_DD": portfolio_quarter_dd(daily),
            "guardian_rolling_50": per_strategy_rolling(daily, "guardian", 50),
            "striker_rolling_50": per_strategy_rolling(daily, "striker", 50),
            "aegis_rolling_50": per_strategy_rolling(daily, "aegis", 50),
            "aegis_hurst_90d": aegis_hurst(90),
            "cluster_2_quarter_count": cluster_2_count_quarter(daily),
        },
    }
    crossings = []
    for k, ind in digest["indicators"].items():
        if ind.get("crossed", False) or ind.get("hard_warn_crossed", False):
            crossings.append({"indicator": k, "severity": (
                "HARD" if ind.get("hard_warn_crossed", False) else "STD"
            )})
        elif ind.get("soft_warn_crossed", False):
            crossings.append({"indicator": k, "severity": "SOFT"})
        elif ind.get("info_crossed", False):
            crossings.append({"indicator": k, "severity": "INFO"})
    digest["crossings"] = crossings

    today = datetime.now().strftime("%Y-%m-%d")
    json_out = OUT_DIR / f"watch_{today}.json"
    md_out = OUT_DIR / f"watch_{today}.md"
    json_out.write_text(json.dumps(digest, indent=2, default=str))

    md = []
    md.append(f"# MSEE watch-list digest — {today}\n")
    md.append(f"Panel: {digest['data_panel_window'][0]} -> "
              f"{digest['data_panel_window'][1]}  ({digest['n_trade_dates']} trade-dates)\n")
    md.append(f"Generator: `scripts/msee_watchlist.py` per "
              f"`docs/methodology/archive/msee/watch_list.md`\n")
    md.append(f"Routing: no Action authorization from this digest.\n\n")
    if crossings:
        md.append(f"## Crossings ({len(crossings)})\n\n")
        for c in crossings:
            md.append(f"- **{c['severity']}** — {c['indicator']}\n")
        md.append("\n")
    else:
        md.append(f"## Crossings: NONE\n\n")
    md.append("## Indicators\n\n")
    for k, ind in digest["indicators"].items():
        md.append(f"### {k}\n\n")
        md.append("```json\n")
        md.append(json.dumps(ind, indent=2, default=str))
        md.append("\n```\n\n")
    md_out.write_text("".join(md), encoding="utf-8")

    print(f"MSEE watch-list digest — {today}")
    print(f"  panel {digest['data_panel_window'][0]} -> "
          f"{digest['data_panel_window'][1]}  "
          f"({digest['n_trade_dates']} trade-dates)")
    print(f"  crossings: {len(crossings)}")
    for c in crossings:
        print(f"    [{c['severity']}] {c['indicator']}")
    print()
    for k, ind in digest["indicators"].items():
        flags = []
        if ind.get("crossed"):
            flags.append("CROSSED")
        if ind.get("hard_warn_crossed"):
            flags.append("HARD")
        if ind.get("soft_warn_crossed"):
            flags.append("SOFT")
        if ind.get("info_crossed"):
            flags.append("INFO")
        flag_str = (" [" + ",".join(flags) + "]") if flags else ""
        print(f"  {k}{flag_str}")
    print()
    print(f"Wrote: {md_out.relative_to(ROOT)}")
    print(f"       {json_out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
