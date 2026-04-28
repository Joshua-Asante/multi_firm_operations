"""MSEE H10 — Senescence decomposition per strategy.

Q-MSEE-10 from docs/methodology/msee/open_questions.md.

Tracks rolling R-multiple-of-winners and rolling win-rate per strategy
over the 2022→2026 panel. Williams 1957 / Hamilton 1966 / Kirkwood 1977
senescence theory maps to alpha decay in two distinguishable modes:

  * Prey-shrink (R-of-winners declines, WR steady):
        the alpha pool the strategy harvests is shrinking — winning
        trades cash in for less per trade. Remediation: capacity
        management, instrument rotation.
  * Density-rise (WR declines, R steady):
        competition density on the strategy's setup is rising —
        more trades fail to fire correctly but those that do still pay.
        Remediation: filter tightening, signal refinement.

Falsifier: no interpretable trend in either component (consistent with
stationary edge so far — strengthens the framework's "lifecycle 3-7yr"
prediction by null result; not a true falsifier of the framework).

PRE-Q GATE:
  D: Per-trade frame from foundation TV-load only.
  S: Rolling 50-trade window (trade-indexed, not calendar) keeps cohort
     size stable while still resolving multi-quarter trends.
  A: Three rolling computations, O(seconds).

Reproducibility: `python analysis/msee/h10_senescence.py`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "identify" / "2026-04-26"))

from common import STRATEGIES, PARAMS, load_tv  # noqa: E402

OUT_JSON = ROOT / "analysis" / "msee" / "h10_senescence.json"
OUT_CSV = ROOT / "analysis" / "msee" / "h10_senescence_rolling.csv"

WINDOW = 50            # trades per rolling window
N_BOOTSTRAP = 2000     # for trend-slope CIs
SEED = 2026


def per_trade(strategy: str) -> pd.DataFrame:
    risk_pct = PARAMS[strategy]["risk_pct"]
    tv = load_tv(strategy)
    tv = tv.dropna(subset=["entry_time", "exit_time", "net_pnl_pct"]).copy()
    tv["net_pnl_R"] = tv["net_pnl_pct"] / risk_pct
    tv["is_win"] = (tv["net_pnl_R"] > 0).astype(int)
    tv = tv.sort_values("exit_time").reset_index(drop=True)
    tv["trade_idx"] = np.arange(len(tv))
    tv["strategy"] = strategy
    return tv[["strategy", "trade_idx", "exit_time", "net_pnl_R", "is_win"]]


def rolling_metrics(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """Rolling R-of-winners and WR over a sliding trade-index window."""
    out = df.copy()
    win_mean = out["net_pnl_R"].where(out["is_win"] == 1)
    out["roll_R_of_winners"] = (
        win_mean.rolling(window=window, min_periods=max(10, window // 5)).mean()
    )
    out["roll_win_rate"] = (
        out["is_win"].rolling(window=window, min_periods=max(10, window // 5)).mean()
    )
    return out


def trend_slope(y: np.ndarray, x: np.ndarray) -> float:
    """OLS slope of y vs x. Returns nan if too few finite points."""
    mask = np.isfinite(y) & np.isfinite(x)
    if mask.sum() < 5:
        return float("nan")
    return float(np.polyfit(x[mask], y[mask], 1)[0])


def bootstrap_slope_ci(y: np.ndarray, x: np.ndarray,
                       n: int, seed: int) -> tuple[float, float]:
    """Percentile bootstrap CI [2.5%, 97.5%] for the OLS slope."""
    rng = np.random.default_rng(seed)
    mask = np.isfinite(y) & np.isfinite(x)
    yy, xx = y[mask], x[mask]
    if len(yy) < 5:
        return (float("nan"), float("nan"))
    slopes = np.empty(n)
    idx_pool = np.arange(len(yy))
    for i in range(n):
        idx = rng.choice(idx_pool, size=len(yy), replace=True)
        slopes[i] = float(np.polyfit(xx[idx], yy[idx], 1)[0])
    return (float(np.percentile(slopes, 2.5)),
            float(np.percentile(slopes, 97.5)))


def classify_mode(slope_R: float, ci_R: tuple[float, float],
                  slope_WR: float, ci_WR: tuple[float, float]) -> str:
    """Senescence mode based on whether each slope's 95% CI excludes 0."""
    R_neg = ci_R[1] < 0
    R_pos = ci_R[0] > 0
    WR_neg = ci_WR[1] < 0
    WR_pos = ci_WR[0] > 0
    if R_neg and WR_neg:
        return "BOTH-DECLINE: capacity exhaustion + density-rise (advanced)"
    if R_neg and not WR_neg:
        return "PREY-SHRINK: R-of-winners declining, WR stable"
    if WR_neg and not R_neg:
        return "DENSITY-RISE: WR declining, R-of-winners stable"
    if R_pos or WR_pos:
        return "REJUVENATION: at least one component improving"
    return "NEUTRAL: no significant trend in either component"


def main() -> None:
    rolling_frames = []
    summary = {
        "question": "Q-MSEE-10 — senescence decomposition (H10)",
        "feed": "OANDA",
        "canonical_status": "PROXY",
        "window_trades": WINDOW,
        "n_bootstrap": N_BOOTSTRAP,
        "per_strategy": {},
    }

    for s in STRATEGIES:
        df = per_trade(s)
        df = rolling_metrics(df, WINDOW)
        rolling_frames.append(df)

        x = df["trade_idx"].values.astype(float)
        y_R = df["roll_R_of_winners"].values
        y_WR = df["roll_win_rate"].values

        slope_R = trend_slope(y_R, x)
        slope_WR = trend_slope(y_WR, x)
        ci_R = bootstrap_slope_ci(y_R, x, N_BOOTSTRAP, SEED)
        ci_WR = bootstrap_slope_ci(y_WR, x, N_BOOTSTRAP, SEED + 1)
        mode = classify_mode(slope_R, ci_R, slope_WR, ci_WR)

        summary["per_strategy"][s] = {
            "n_trades": int(len(df)),
            "trade_window": [df["exit_time"].min().isoformat(),
                             df["exit_time"].max().isoformat()],
            "R_of_winners": {
                "first_window_mean": float(np.nanmean(y_R[:WINDOW])),
                "last_window_mean": float(np.nanmean(y_R[-WINDOW:])),
                "trend_slope_per_trade": slope_R,
                "trend_slope_ci95": list(ci_R),
            },
            "win_rate": {
                "first_window_mean": float(np.nanmean(y_WR[:WINDOW])),
                "last_window_mean": float(np.nanmean(y_WR[-WINDOW:])),
                "trend_slope_per_trade": slope_WR,
                "trend_slope_ci95": list(ci_WR),
            },
            "mode": mode,
        }

    out = pd.concat(rolling_frames, ignore_index=True)
    out.to_csv(OUT_CSV, index=False)
    OUT_JSON.write_text(json.dumps(summary, indent=2, default=str))

    print("MSEE H10 — Senescence decomposition")
    print(f"  Window: {WINDOW} trades; bootstrap n={N_BOOTSTRAP}")
    print()
    for s in STRATEGIES:
        r = summary["per_strategy"][s]
        print(f"  {s.upper()}  ({r['n_trades']} trades)")
        rR = r["R_of_winners"]
        rW = r["win_rate"]
        sig_R = "" if rR["trend_slope_ci95"][0] <= 0 <= rR["trend_slope_ci95"][1] else " *"
        sig_W = "" if rW["trend_slope_ci95"][0] <= 0 <= rW["trend_slope_ci95"][1] else " *"
        print(f"    R-of-winners:  first={rR['first_window_mean']:.2f}R  "
              f"last={rR['last_window_mean']:.2f}R  "
              f"slope={rR['trend_slope_per_trade']:+.4f}/trade  "
              f"CI95=[{rR['trend_slope_ci95'][0]:+.4f},"
              f"{rR['trend_slope_ci95'][1]:+.4f}]{sig_R}")
        print(f"    Win rate:      first={rW['first_window_mean']:.3f}    "
              f"last={rW['last_window_mean']:.3f}    "
              f"slope={rW['trend_slope_per_trade']:+.5f}/trade  "
              f"CI95=[{rW['trend_slope_ci95'][0]:+.5f},"
              f"{rW['trend_slope_ci95'][1]:+.5f}]{sig_W}")
        print(f"    Mode: {r['mode']}")
        print()
    print(f"Wrote: {OUT_JSON.relative_to(ROOT)}")
    print(f"       {OUT_CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
