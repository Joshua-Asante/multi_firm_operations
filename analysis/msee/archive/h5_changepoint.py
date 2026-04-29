"""MSEE H5 — Changepoint analysis on rolling Sharpe per strategy.

Q-MSEE-5 from docs/methodology/msee/open_questions.md.

Eldredge & Gould (1972) punctuated equilibrium predicts long stretches
of stationary morphological state punctuated by brief sharp transitions,
not gradual drift. Mapped to strategy edge: rolling Sharpe should show
few discrete breaks per 4yr panel rather than continuous drift.

Test: PELT (Pruned Exact Linear Time, Killick 2012) with L2 cost on
rolling 30-day Sharpe per strategy. Penalty calibrated by BIC.

  * < 5 breaks per 4yr   => punctuated signature (P5 supported)
  * 5-10 breaks          => transitional / mixed
  * > 10 breaks          => continuous-drift signature (P5 falsified)
  *   0 breaks           => frozen-edge signature (also a falsifier in
                            the opposite direction — no regime structure)

Cross-check: predicted breakpoint dates should align with known events
(e.g., 2022 inflation regime onset, 2024 election period). Spurious
alignment with no event = artefact.

PRE-Q GATE:
  D: Rolling Sharpe restricted to days where the strategy traded
     (zero-fill days do not contribute Sharpe info).
  S: 30-day calendar window. Alternatives (60d, trade-indexed) noted
     for follow-up if PELT is sensitive to window choice.
  A: ruptures.Pelt with L2 cost; O(n log n).

Reproducibility: `python analysis/msee/h5_changepoint.py`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import ruptures as rpt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "identify" / "2026-04-26"))

from common import STRATEGIES, PARAMS  # noqa: E402

DAILY_CSV = ROOT / "analysis" / "msee" / "daily_strategy_returns.csv"
OUT_JSON = ROOT / "analysis" / "msee" / "h5_changepoint.json"
OUT_CSV = ROOT / "analysis" / "msee" / "h5_rolling_sharpe.csv"

ROLLING_DAYS_PRIMARY = 90  # primary report window; sweep over (30, 90, 180)
ROLLING_DAYS_SWEEP = (30, 90, 180)
ANNUALIZE = np.sqrt(252)
ALLOC = {s: PARAMS[s]["risk_pct"] / 100.0 for s in STRATEGIES}
KNOWN_EVENTS = [
    ("2022-02-24", "Russia/Ukraine"),
    ("2022-06-15", "Fed 75bp hike (inflation regime)"),
    ("2023-03-10", "SVB collapse"),
    ("2023-10-07", "Israel/Hamas"),
    ("2024-08-05", "Yen-carry unwind / global vol spike"),
    ("2024-11-05", "US election"),
    ("2025-04-02", "Tariff announcement"),
    ("2026-04-16", "Iran/Hormuz overlay window onset (per CLAUDE.md)"),
]


def rolling_sharpe(daily: pd.DataFrame, strategy: str,
                   window_days: int, allocations: dict) -> pd.DataFrame:
    """Rolling annualized Sharpe of the strategy's daily PORTFOLIO
    contribution on a full business-day axis (Mon-Fri).

    Daily contribution r_t = R_t * w_strategy on trade-days, 0 on
    non-trade business days. Rolling mean/std over window_days of
    business days. Annualized via sqrt(252). This is a true daily
    Sharpe at portfolio scale and corresponds to operational
    portfolio behavior (a non-trading strategy contributes 0 P&L
    that day).
    """
    df = daily[["exit_date_ny", f"{strategy}_R", f"{strategy}_n_trades"]].copy()
    df = df.rename(columns={f"{strategy}_R": "R", f"{strategy}_n_trades": "n_trades"})
    df = df.set_index("exit_date_ny").sort_index()

    # Full business-day axis spanning the panel.
    bdays = pd.bdate_range(df.index.min(), df.index.max())
    full = df.reindex(bdays).fillna(0.0)
    full.index.name = "date"
    w = allocations[strategy]
    contrib = full["R"] * w
    mu = contrib.rolling(window=window_days, min_periods=window_days).mean()
    sd = contrib.rolling(window=window_days, min_periods=window_days).std()
    sharpe = (mu / sd.replace(0.0, np.nan)) * ANNUALIZE
    out = pd.DataFrame({
        "date": contrib.index,
        "daily_contrib": contrib.values,
        "rolling_sharpe": sharpe.values,
    }).dropna(subset=["rolling_sharpe"]).reset_index(drop=True)
    out["strategy"] = strategy
    return out


def detect_changepoints(y: np.ndarray, penalty: float) -> list[int]:
    """PELT with L2 cost; returns 0-indexed changepoint positions
    (excluding the trailing index n)."""
    algo = rpt.Pelt(model="l2", min_size=10, jump=1).fit(y.reshape(-1, 1))
    raw = algo.predict(pen=penalty)
    # ruptures appends n as last element; strip it.
    return [int(c) for c in raw if c < len(y)]


def main() -> None:
    daily = pd.read_csv(DAILY_CSV, parse_dates=["exit_date_ny"])
    summary = {
        "question": "Q-MSEE-5 — punctuated-equilibrium changepoint analysis (H5, P5)",
        "feed": "OANDA",
        "canonical_status": "PROXY",
        "rolling_window_sweep_business_days": list(ROLLING_DAYS_SWEEP),
        "primary_window_business_days": ROLLING_DAYS_PRIMARY,
        "annualize_factor": float(ANNUALIZE),
        "allocations": ALLOC,
        "per_strategy": {},
        "known_events": KNOWN_EVENTS,
    }
    rolling_frames = []

    def classify(n_breaks: int) -> str:
        if n_breaks == 0:
            return "FROZEN-EDGE: 0 changepoints — no regime structure"
        if n_breaks < 5:
            return f"PUNCTUATED: {n_breaks} changepoints — P5 supported"
        if n_breaks <= 10:
            return f"TRANSITIONAL: {n_breaks} changepoints"
        return f"CONTINUOUS-DRIFT: {n_breaks} changepoints — P5 falsified at this window"

    for s in STRATEGIES:
        per_s = {"sweep": {}}
        primary_rs = None
        for w in ROLLING_DAYS_SWEEP:
            rs = rolling_sharpe(daily, s, w, ALLOC)
            y = rs["rolling_sharpe"].values.astype(float)
            sigma2 = float(np.var(y, ddof=1))
            n = len(y)
            # BIC-style: 2 * sigma^2 * log(n) (per-segment penalty).
            penalty = float(2.0 * sigma2 * np.log(n))
            cps_idx = detect_changepoints(y, penalty=penalty)
            per_s["sweep"][w] = {
                "n_rolling_obs": int(n),
                "rolling_sharpe_var": sigma2,
                "pelt_penalty": penalty,
                "n_changepoints": int(len(cps_idx)),
                "changepoint_dates": [rs["date"].iloc[i].strftime("%Y-%m-%d")
                                      for i in cps_idx],
                "verdict": classify(len(cps_idx)),
            }
            if w == ROLLING_DAYS_PRIMARY:
                primary_rs = rs
                primary_cps = cps_idx
                primary_segments = []
                bounds = [0] + cps_idx + [n]
                for a, b in zip(bounds[:-1], bounds[1:]):
                    primary_segments.append({
                        "start_date": rs["date"].iloc[a].strftime("%Y-%m-%d"),
                        "end_date": rs["date"].iloc[b - 1].strftime("%Y-%m-%d"),
                        "n_obs": int(b - a),
                        "mean_sharpe": float(np.mean(y[a:b])),
                    })
        rolling_frames.append(primary_rs.assign(window=ROLLING_DAYS_PRIMARY))

        # Event-alignment for primary window.
        cps_dates = per_s["sweep"][ROLLING_DAYS_PRIMARY]["changepoint_dates"]
        event_aligned = []
        for cp_d_str in cps_dates:
            cp_d = pd.Timestamp(cp_d_str)
            for ed_str, label in KNOWN_EVENTS:
                ed = pd.Timestamp(ed_str)
                if abs((cp_d - ed).days) <= 10:
                    event_aligned.append({
                        "changepoint": cp_d_str,
                        "event": label,
                        "event_date": ed_str,
                        "delta_days": int((cp_d - ed).days),
                    })
        per_s["primary_segments"] = primary_segments
        per_s["primary_event_alignment"] = event_aligned
        summary["per_strategy"][s] = per_s

    pd.concat(rolling_frames, ignore_index=True).to_csv(OUT_CSV, index=False)
    OUT_JSON.write_text(json.dumps(summary, indent=2, default=str))

    print("MSEE H5 — Changepoint analysis on rolling Sharpe")
    print(f"  Daily portfolio contribution series (R*w, 0 on non-trade days)")
    print(f"  Window sweep: {ROLLING_DAYS_SWEEP} business days; "
          f"primary={ROLLING_DAYS_PRIMARY}d")
    print()
    print(f"  Sensitivity table (changepoints by window):")
    print(f"  {'strategy':10s}  " + "  ".join(f"{w}d" for w in ROLLING_DAYS_SWEEP))
    for s in STRATEGIES:
        per_s = summary["per_strategy"][s]
        cells = "  ".join(
            f"{per_s['sweep'][w]['n_changepoints']:3d}"
            for w in ROLLING_DAYS_SWEEP
        )
        print(f"  {s:10s}  {cells}")
    print()
    for s in STRATEGIES:
        per_s = summary["per_strategy"][s]
        primary = per_s["sweep"][ROLLING_DAYS_PRIMARY]
        print(f"  {s.upper()}  (primary {ROLLING_DAYS_PRIMARY}d window: "
              f"n_obs={primary['n_rolling_obs']}, penalty={primary['pelt_penalty']:.3f})")
        print(f"    {primary['verdict']}")
        if primary["changepoint_dates"]:
            print(f"    Changepoint dates: {', '.join(primary['changepoint_dates'])}")
        print(f"    Segment Sharpes:")
        for seg in per_s["primary_segments"]:
            print(f"      {seg['start_date']} -> {seg['end_date']}  "
                  f"(n={seg['n_obs']:3d})  Sharpe={seg['mean_sharpe']:+6.2f}")
        if per_s["primary_event_alignment"]:
            print(f"    Event alignment (+/-10 days):")
            for ev in per_s["primary_event_alignment"]:
                print(f"      {ev['changepoint']} ~~ {ev['event']} "
                      f"({ev['event_date']}, delta={ev['delta_days']:+d}d)")
        print()
    print(f"Wrote: {OUT_JSON.relative_to(ROOT)}")
    print(f"       {OUT_CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
