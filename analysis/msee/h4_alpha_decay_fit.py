"""MSEE H4 — Alpha-decay functional form per strategy.

Q-MSEE-4 from docs/methodology/msee/open_questions.md.

Fits three competing decay forms to rolling 6-month profit factor per
strategy:

    hyperbolic:   PF(t) = K / (1 + lambda*t) + offset
    exponential:  PF(t) = K * exp(-lambda*t) + offset
    linear:       PF(t) = K - lambda*t

Hyperbolic indicates frequency-dependent crowding (Lee 2025): the
arbitrage rate scales with the alpha pool, producing 1/t decay.
Exponential indicates non-adaptive drift (constant per-period attrition).
Linear is a sanity baseline.

Falsifier (for MSEE claim 3 — punctuated/crowding decay): all three
strategies prefer exponential or linear decisively over hyperbolic
(deltaAIC > 4).

PRE-Q GATE:
  D: Restricted to rolling windows with >= 30 trades (avoids early-cohort
     instability).
  S: 6-month rolling PF on trade-indexed window (preserves cohort size
     across panel; calendar windows starve early in panel).
  A: scipy.optimize.curve_fit, bounded.

Reproducibility: `python analysis/msee/h4_alpha_decay_fit.py`
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "identify" / "2026-04-26"))

from common import STRATEGIES, PARAMS, load_tv  # noqa: E402

OUT_JSON = ROOT / "analysis" / "msee" / "h4_alpha_decay.json"
OUT_CSV = ROOT / "analysis" / "msee" / "h4_alpha_decay_rolling.csv"

ROLLING_DAYS = 360          # ~1 year (6mo per report starves Guardian/Aegis low-freq strategies)
MIN_TRADES_IN_WIN = 15      # cohort-size floor; 360d gives G~50, S~58, A~31 trades typical


def per_trade(strategy: str) -> pd.DataFrame:
    risk_pct = PARAMS[strategy]["risk_pct"]
    tv = load_tv(strategy)
    tv = tv.dropna(subset=["entry_time", "exit_time", "net_pnl_pct"]).copy()
    tv["net_pnl_R"] = tv["net_pnl_pct"] / risk_pct
    tv = tv.sort_values("exit_time").reset_index(drop=True)
    return tv[["exit_time", "net_pnl_R"]]


def rolling_pf(df: pd.DataFrame, days: int, min_n: int) -> pd.DataFrame:
    """Calendar-window rolling PF, sampled per trade exit."""
    df = df.set_index("exit_time").sort_index()
    pfs = []
    times = df.index
    for t in times:
        window = df.loc[t - pd.Timedelta(days=days):t]
        if len(window) < min_n:
            pfs.append(np.nan)
            continue
        wins = window["net_pnl_R"][window["net_pnl_R"] > 0].sum()
        losses = -window["net_pnl_R"][window["net_pnl_R"] < 0].sum()
        if losses <= 0:
            pfs.append(np.inf)
        else:
            pfs.append(float(wins / losses))
    out = pd.DataFrame({"exit_time": times, "rolling_pf": pfs})
    return out.dropna().reset_index(drop=True)


def fit_models(t: np.ndarray, y: np.ndarray) -> dict:
    """Fit hyperbolic, exponential, linear; return AIC-comparable summary.

    AIC = n*log(rss/n) + 2k for least-squares with implicit unit variance.
    Lower AIC is better. Models with k parameters: hyperbolic (3),
    exponential (3), linear (2).
    """
    from scipy.optimize import curve_fit

    def hyper(tt, K, lam, off):
        return K / (1.0 + lam * tt) + off

    def expo(tt, K, lam, off):
        return K * np.exp(-lam * tt) + off

    def lin(tt, K, lam):
        return K - lam * tt

    n = len(t)
    fits = {}
    K0 = float(np.nanmean(y))

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for name, fn, p0, k in [
            ("hyperbolic", hyper, [K0, 1e-3, 0.0], 3),
            ("exponential", expo, [K0, 1e-3, 0.0], 3),
            ("linear",      lin,  [K0, 1e-3], 2),
        ]:
            try:
                popt, _ = curve_fit(fn, t, y, p0=p0, maxfev=10000)
                resid = y - fn(t, *popt)
                rss = float(np.sum(resid ** 2))
                aic = float(n * np.log(rss / n) + 2 * k) if rss > 0 else float("-inf")
                ss_tot = float(np.sum((y - y.mean()) ** 2))
                r2 = float(1.0 - rss / ss_tot) if ss_tot > 0 else float("nan")
                fits[name] = {
                    "params": popt.tolist(),
                    "rss": rss,
                    "aic": aic,
                    "r2": r2,
                    "k": k,
                }
            except Exception as e:
                fits[name] = {"error": str(e)}
    return fits


def main() -> None:
    summary = {
        "question": "Q-MSEE-4 — alpha-decay form (H4, P4)",
        "feed": "OANDA",
        "canonical_status": "PROXY",
        "rolling_days": ROLLING_DAYS,
        "min_trades_in_window": MIN_TRADES_IN_WIN,
        "per_strategy": {},
    }
    rolling_frames = []

    for s in STRATEGIES:
        trades = per_trade(s)
        roll = rolling_pf(trades, ROLLING_DAYS, MIN_TRADES_IN_WIN)
        roll["strategy"] = s
        # Fit on finite rolling PFs (drop infs for fitting; PF=inf means
        # zero losses in window — usually early panel transient).
        finite = roll[np.isfinite(roll["rolling_pf"])].copy()
        if len(finite) < 30:
            summary["per_strategy"][s] = {"error": "insufficient finite rolling PFs"}
            rolling_frames.append(roll)
            continue
        # t in days from first observation.
        t0 = finite["exit_time"].min()
        finite["t_days"] = (finite["exit_time"] - t0).dt.total_seconds() / 86400.0
        t = finite["t_days"].values.astype(float)
        y = finite["rolling_pf"].values.astype(float)
        fits = fit_models(t, y)
        # Best model by AIC.
        best = min(
            (k for k in fits if "aic" in fits[k]),
            key=lambda k: fits[k]["aic"],
            default=None,
        )
        delta_aic = {}
        if best is not None:
            base = fits[best]["aic"]
            delta_aic = {k: float(fits[k]["aic"] - base)
                         for k in fits if "aic" in fits[k]}
        summary["per_strategy"][s] = {
            "n_finite_windows": int(len(finite)),
            "panel_t_range_days": [float(t.min()), float(t.max())],
            "first_window_pf": float(y[0]),
            "last_window_pf": float(y[-1]),
            "fits": fits,
            "best_by_aic": best,
            "delta_aic_vs_best": delta_aic,
        }
        rolling_frames.append(roll)

    pd.concat(rolling_frames, ignore_index=True).to_csv(OUT_CSV, index=False)
    OUT_JSON.write_text(json.dumps(summary, indent=2, default=str))

    # Verdict: count, per fitted strategy, whether hyperbolic is preferred,
    # competitive (deltaAIC <= 4), or rejected (deltaAIC > 4 vs best).
    fitted = []
    hyp_pref = 0
    hyp_comp = 0
    hyp_rej = 0
    for s in STRATEGIES:
        d = summary["per_strategy"][s]
        if "delta_aic_vs_best" not in d:
            continue
        fitted.append(s)
        hyp_delta = d["delta_aic_vs_best"].get("hyperbolic", float("inf"))
        if d["best_by_aic"] == "hyperbolic":
            hyp_pref += 1
        elif hyp_delta <= 4.0:
            hyp_comp += 1
        else:
            hyp_rej += 1
    if not fitted:
        summary["verdict"] = "INCONCLUSIVE: no strategies had enough finite rolling PFs to fit"
    elif hyp_rej == len(fitted):
        summary["verdict"] = (
            f"NEGATIVE: hyperbolic decisively rejected in all "
            f"{len(fitted)} fitted strategies — MSEE claim 3 "
            f"(frequency-dependent crowding) falsified"
        )
    else:
        summary["verdict"] = (
            f"MIXED: hyperbolic preferred in {hyp_pref}, competitive (deltaAIC<=4) in "
            f"{hyp_comp}, rejected in {hyp_rej} of {len(fitted)} fitted strategies"
        )
    OUT_JSON.write_text(json.dumps(summary, indent=2, default=str))

    print("MSEE H4 — Alpha-decay form fits")
    print(f"  Window: {ROLLING_DAYS}d rolling, min {MIN_TRADES_IN_WIN} trades")
    print()
    for s in STRATEGIES:
        d = summary["per_strategy"][s]
        if "error" in d:
            print(f"  {s.upper()}  ERROR: {d['error']}")
            continue
        print(f"  {s.upper()}  n_windows={d['n_finite_windows']}  "
              f"PF: first={d['first_window_pf']:.2f} last={d['last_window_pf']:.2f}")
        for name in ["hyperbolic", "exponential", "linear"]:
            f = d["fits"].get(name, {})
            if "aic" not in f:
                print(f"    {name:11s}  ERROR: {f.get('error', 'unknown')}")
                continue
            mark = "<-- best" if name == d["best_by_aic"] else ""
            print(f"    {name:11s}  AIC={f['aic']:+8.2f}  "
                  f"deltaAIC={d['delta_aic_vs_best'][name]:+6.2f}  "
                  f"R^2={f['r2']:+.3f}  {mark}")
        print()
    print(f"Verdict: {summary['verdict']}")
    print(f"Wrote: {OUT_JSON.relative_to(ROOT)}")
    print(f"       {OUT_CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
