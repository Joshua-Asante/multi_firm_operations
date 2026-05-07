"""H-NYFBO Inquire-phase orchestrator.

Runs the single-config falsification per parent brief
docs/methodology/findings/2026-05-02_eurusd_m15_lnyo_notice.md and
emits results.json + a markdown summary at:
  analysis/archive/eurusd_lnyo/results/h_nyfbo_g1.json

G1 stage gate evaluation (parent brief §4 + §6) — six kill criteria, any
one fires => KILL:
  1. Net per-trade edge < 1.5 pips in any of the three regimes
  2. Daily P&L correlation with G/S/A composite > 0.30 conditional on
     G/S/A-active days
  3. Striker-specific signed correlation > 0.20 on Tue+Fri
     (Friday-only sub-test recorded separately)
  4. Trade-day concentration > 75%
  5. 2024-07-01 -> 2026-04-20 contributes < 25% of total edge
  6. N (full panel) < 100 OR permutation p >= 0.05; Rule 1 inflation
     applied if any regime n < 25

Usage:
  python -m analysis.eurusd_lnyo.run_h_nyfbo
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.eurusd_lnyo import (
    correlation,
    dukascopy_loader,
    nyfbo_simulator,
    pepperstone_spread,
    permutation,
)
from analysis.eurusd_lnyo import dxy_loader as dxy

REPO_ROOT = Path(__file__).parent.parent.parent
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_JSON = RESULTS_DIR / "h_nyfbo_g1.json"

# Kill thresholds (parent brief §4)
KILL_EDGE_PIPS = 1.5
KILL_GSA_CORR = 0.30
KILL_STRIKER_CORR = 0.20
KILL_CONCENTRATION = 0.75
KILL_RECENCY_FLOOR = 0.25
KILL_N_FLOOR = 100
KILL_PERM_P = 0.05
KILL_DXY_CORR = 0.30

REGIMES = ["hike_2022", "hold_2023_24", "ease_2024_26"]
RECENCY_REGIME = "ease_2024_26"


@dataclass
class GateResult:
    name: str
    passed: bool
    measured: float
    threshold: float
    note: str = ""


def evaluate_kill_1_edge(trades: pd.DataFrame) -> list[GateResult]:
    """Per-regime net per-trade edge >= 1.5 pips."""
    results = []
    for r in REGIMES:
        sub = trades[trades["regime"] == r]
        n = len(sub)
        edge = float(sub["net_pips"].mean()) if n else float("nan")
        passed = (n > 0) and (edge >= KILL_EDGE_PIPS)
        note = f"n={n}"
        results.append(GateResult(
            name=f"kill_1_edge[{r}]",
            passed=passed,
            measured=edge,
            threshold=KILL_EDGE_PIPS,
            note=note,
        ))
    return results


def evaluate_kill_2_gsa(slices: dict[str, correlation.CorrSlice]) -> GateResult:
    s = slices["gsa_composite_active"]
    abs_r = abs(s.pearson_r) if not np.isnan(s.pearson_r) else float("nan")
    passed = (not np.isnan(abs_r)) and (abs_r <= KILL_GSA_CORR)
    return GateResult(
        name="kill_2_gsa_composite",
        passed=passed,
        measured=s.pearson_r,
        threshold=KILL_GSA_CORR,
        note=f"n={s.n} (|r|={abs_r:.3f})",
    )


def evaluate_kill_3_striker(slices: dict[str, correlation.CorrSlice]) -> list[GateResult]:
    out = []
    s = slices["striker_active_TueFri"]
    abs_r = abs(s.pearson_r) if not np.isnan(s.pearson_r) else float("nan")
    out.append(GateResult(
        name="kill_3_striker_active",
        passed=(not np.isnan(abs_r)) and (abs_r <= KILL_STRIKER_CORR),
        measured=s.pearson_r,
        threshold=KILL_STRIKER_CORR,
        note=f"Tue+Fri n={s.n}",
    ))
    sf = slices["striker_friday_only"]
    abs_rf = abs(sf.pearson_r) if not np.isnan(sf.pearson_r) else float("nan")
    out.append(GateResult(
        name="kill_3_striker_friday_only",
        passed=(not np.isnan(abs_rf)) and (abs_rf <= KILL_STRIKER_CORR),
        measured=sf.pearson_r,
        threshold=KILL_STRIKER_CORR,
        note=f"Friday-only n={sf.n} (sub-test, recorded separately)",
    ))
    return out


def evaluate_kill_4_concentration(trades: pd.DataFrame) -> GateResult:
    """Trade-day concentration > 75% means most edge concentrated on a small
    fraction of trade days. Operational definition: top X% of days
    contributing >75% of total positive edge => concentration.

    Use a clean Lorenz-style: sort daily P&L descending, find what fraction
    of days contributes 75% of total positive sum. Concentration ratio =
    (75% positive contribution) / (total positive trade days).
    Lower ratio => more concentrated.
    Threshold: if top-25% of days contribute > 75% => concentration triggered.
    """
    if trades.empty:
        return GateResult(name="kill_4_concentration", passed=False,
                          measured=float("nan"), threshold=KILL_CONCENTRATION,
                          note="no trades")
    daily = trades.groupby("et_date")["net_pips"].sum()
    pos_daily = daily[daily > 0].sort_values(ascending=False)
    if pos_daily.empty:
        return GateResult(name="kill_4_concentration", passed=True,
                          measured=0.0, threshold=KILL_CONCENTRATION,
                          note="no positive trade days (edge<0)")
    total_pos = pos_daily.sum()
    cum = pos_daily.cumsum() / total_pos
    # fraction of positive days needed to reach 75% of edge
    frac_days = (cum.searchsorted(0.75) + 1) / len(pos_daily)
    # If top 25% of days give >=75% of edge => concentrated.
    concentrated = frac_days <= (1 - KILL_CONCENTRATION)
    measured = 1.0 - frac_days  # share of "tail" days providing concentration
    return GateResult(
        name="kill_4_concentration",
        passed=not concentrated,
        measured=measured,
        threshold=KILL_CONCENTRATION,
        note=f"top {frac_days:.1%} of positive days hold 75% of edge",
    )


def evaluate_kill_5_recency(trades: pd.DataFrame) -> GateResult:
    """2024-07-01 onward must contribute >= 25% of total edge."""
    if trades.empty:
        return GateResult(name="kill_5_recency", passed=False,
                          measured=float("nan"), threshold=KILL_RECENCY_FLOOR,
                          note="no trades")
    total_edge = trades["net_pips"].sum()
    if total_edge == 0:
        return GateResult(name="kill_5_recency", passed=False,
                          measured=float("nan"), threshold=KILL_RECENCY_FLOOR,
                          note="zero total edge")
    recent_edge = trades.loc[trades["regime"] == RECENCY_REGIME, "net_pips"].sum()
    share = float(recent_edge / total_edge) if total_edge != 0 else float("nan")
    # If total edge is negative, recency condition is moot — flag as failed
    # for documentation
    if total_edge < 0:
        return GateResult(name="kill_5_recency", passed=False,
                          measured=share, threshold=KILL_RECENCY_FLOOR,
                          note=f"total edge negative; recency share = {share:.2%}")
    passed = share >= KILL_RECENCY_FLOOR
    return GateResult(
        name="kill_5_recency",
        passed=passed,
        measured=share,
        threshold=KILL_RECENCY_FLOOR,
        note=f"ease_2024_26 contributes {share:.1%} of total edge",
    )


def evaluate_kill_6_perm(trades: pd.DataFrame, perm_p: float, n_total: int,
                          rule1_regimes: list[str]) -> GateResult:
    n_ok = n_total >= KILL_N_FLOOR
    p_ok = perm_p < KILL_PERM_P
    passed = n_ok and p_ok
    note = f"N={n_total} (>={KILL_N_FLOOR}? {n_ok}); perm_p={perm_p:.4f} (<{KILL_PERM_P}? {p_ok})"
    if rule1_regimes:
        note += f"; Rule-1 inflation: {','.join(rule1_regimes)}"
    return GateResult(
        name="kill_6_n_perm",
        passed=passed,
        measured=perm_p,
        threshold=KILL_PERM_P,
        note=note,
    )


def evaluate_dxy_guardrail(slices: dict[str, correlation.CorrSlice]) -> GateResult:
    if "dxy_guardian_dow" not in slices:
        return GateResult(name="guardrail_6_dxy", passed=True,
                          measured=float("nan"), threshold=KILL_DXY_CORR,
                          note="DXY data unavailable; check skipped")
    s = slices["dxy_guardian_dow"]
    abs_r = abs(s.pearson_r) if not np.isnan(s.pearson_r) else float("nan")
    passed = (not np.isnan(abs_r)) and (abs_r <= KILL_DXY_CORR)
    return GateResult(
        name="guardrail_6_dxy",
        passed=passed,
        measured=s.pearson_r,
        threshold=KILL_DXY_CORR,
        note=f"n={s.n}; |r|={abs_r:.3f}",
    )


def hurst_log_returns(close_prices: pd.Series, n_lags: int = 20) -> float:
    """R/S Hurst on log-returns (NOT log prices — memory feedback_hurst_rs_log_prices_trap).

    Log returns => H ≈ 0.5 expected for random walk.
    """
    log_ret = np.log(close_prices).diff().dropna().values
    if len(log_ret) < n_lags * 2:
        return float("nan")
    lags = list(range(2, n_lags + 1))
    rs = []
    for lag in lags:
        n = len(log_ret) // lag * lag
        x = log_ret[:n].reshape(-1, lag)
        means = x.mean(axis=1, keepdims=True)
        z = (x - means).cumsum(axis=1)
        r = z.max(axis=1) - z.min(axis=1)
        s = x.std(axis=1, ddof=1)
        valid = s > 0
        if valid.sum() == 0:
            continue
        rs.append((lag, np.mean(r[valid] / s[valid])))
    if len(rs) < 5:
        return float("nan")
    log_lags = np.log([x[0] for x in rs])
    log_rs = np.log([x[1] for x in rs])
    h = float(np.polyfit(log_lags, log_rs, 1)[0])
    return h


# --- Main pipeline -----------------------------------------------------------

def run() -> dict:
    print("=" * 72)
    print(" H-NYFBO Inquire-phase falsification (single-config, literature-default)")
    print("=" * 72)
    print()

    # 1. Load Dukascopy bid+ask M15
    print("[1/8] Loading Dukascopy EURUSD M15 bid+ask...")
    bars = dukascopy_loader.load_eurusd_m15_bidask()
    print(f"      {len(bars):,} bars; range UTC {bars.index.min()} -> {bars.index.max()}")
    bid_le_ask = float((bars["bid_close"] <= bars["ask_close"]).mean())
    print(f"      bid<=ask invariant: {bid_le_ask:.4%}")

    # 2. DST sanity (parent brief §5 #4)
    print()
    print("[2/8] DST sanity — 09:00 ET on transition-adjacent days...")
    bars_et = dukascopy_loader.add_et_columns(bars)
    dst_check = []
    for dst_date in dukascopy_loader.DST_TRANSITIONS:
        for offset_d in [-1, +1]:
            target = dst_date + dt.timedelta(days=offset_d)
            mask = (bars_et["et_date"] == target) & (bars_et["et_hour"] == 9) & (bars_et["et_minute"] == 0)
            sub = bars[mask]
            if len(sub):
                utc_h = int(sub.index[0].hour)
                dst_check.append({"et_date": str(target), "dst_anchor": str(dst_date),
                                   "offset": offset_d, "utc_hour": utc_h})
    for c in dst_check[:8]:
        print(f"      {c['et_date']} (DST {c['dst_anchor']}, {c['offset']:+d}d): 09:00 ET = {c['utc_hour']:02d}:00 UTC")

    # 3. Run NYFBO simulator
    print()
    print("[3/8] NYFBO simulation (literature defaults)...")
    trades = nyfbo_simulator.simulate_h_nyfbo(bars)
    print(f"      Trades: {len(trades)}")
    if len(trades) == 0:
        print("      No trades produced — pipeline cannot evaluate kill criteria.")
        return {"verdict": "no_trades", "n_trades": 0}

    # Per-regime stats
    print()
    print(f"      {'Regime':<18} {'n':>5} {'mean_net':>10} {'median':>9} {'sum':>10}")
    regime_stats = {}
    for r in REGIMES:
        sub = trades[trades["regime"] == r]
        if len(sub):
            mean_p = float(sub["net_pips"].mean())
            med_p = float(sub["net_pips"].median())
            sum_p = float(sub["net_pips"].sum())
        else:
            mean_p = med_p = sum_p = float("nan")
        regime_stats[r] = {"n": int(len(sub)), "mean_net_pips": mean_p,
                           "median_net_pips": med_p, "sum_net_pips": sum_p}
        print(f"      {r:<18} {len(sub):>5d} {mean_p:>10.3f} {med_p:>9.3f} {sum_p:>10.1f}")

    # 4. Aggregate to daily
    print()
    print("[4/8] Aggregating to daily P&L (NYFBO and G/S/A panel)...")
    nyfbo_daily = nyfbo_simulator.daily_pnl_pips(trades)
    print(f"      NYFBO daily series: {len(nyfbo_daily)} non-zero days, "
          f"sum={float(nyfbo_daily.sum()):.1f} pips")
    panel = correlation.load_gsa_daily_panel()
    print(f"      G/S/A panel: {panel.index.min().date()} -> {panel.index.max().date()}")

    # 5. DXY load
    print()
    print("[5/8] Loading DXY for guardrail #6...")
    try:
        dxy_df = dxy.load_dxy()
        dxy_daily = dxy_df["dxy_chg"]
        print(f"      DXY: {len(dxy_df)} days")
    except FileNotFoundError:
        dxy_daily = None
        print("      DXY not found - guardrail #6 will be skipped")

    # 6. Conditional correlations
    print()
    print("[6/8] Conditional correlations...")
    slices = correlation.all_correlation_slices(nyfbo_daily, panel, dxy_daily=dxy_daily)
    summary = correlation.summarize_slices(slices)
    print(summary.to_string(index=False))

    # 7. Permutation gating + Rule 1
    print()
    print("[7/8] Permutation gating (>=1000 shuffles)...")
    edge_perm = permutation.edge_permutation_pvalue(
        trades["net_pips"].values, n_perm=1000, seed=42
    )
    print(f"      Edge perm: observed_mean={edge_perm.observed:.3f} pips, p={edge_perm.p_two_sided:.4f}, n={edge_perm.n}")

    # Per-regime Rule-1 flags
    rule1_flags = []
    for r in REGIMES:
        n_r = regime_stats[r]["n"]
        if n_r < permutation.RULE1_THRESHOLD and n_r > 0:
            rule1_flags.append(f"{r}(n={n_r})")
    if rule1_flags:
        print(f"      Rule 1 small-cell flags: {rule1_flags}")
    else:
        print(f"      Rule 1: all regimes n>={permutation.RULE1_THRESHOLD} (no inflation needed)")

    # 8. G1 evaluation
    print()
    print("[8/8] G1 stage gate evaluation...")
    gates: list[GateResult] = []
    gates.extend(evaluate_kill_1_edge(trades))
    gates.append(evaluate_kill_2_gsa(slices))
    gates.extend(evaluate_kill_3_striker(slices))
    gates.append(evaluate_kill_4_concentration(trades))
    gates.append(evaluate_kill_5_recency(trades))
    gates.append(evaluate_kill_6_perm(trades, edge_perm.p_two_sided, len(trades), rule1_flags))
    gates.append(evaluate_dxy_guardrail(slices))

    print()
    print(f"      {'criterion':<32} {'pass':>6} {'measured':>10} {'thresh':>8}  note")
    for g in gates:
        flag = "PASS" if g.passed else "FAIL"
        m_str = f"{g.measured:.4f}" if not (g.measured is None or (isinstance(g.measured, float) and np.isnan(g.measured))) else "NaN"
        print(f"      {g.name:<32} {flag:>6} {m_str:>10} {g.threshold:>8.3f}  {g.note}")

    # Hurst sanity (parent brief §9 + memory feedback_hurst_rs_log_prices_trap)
    print()
    print("Hurst sanity (log-returns — NOT log-prices):")
    for r in REGIMES:
        # Use mid_close from the regime's date range
        bars_with_mid = bars.assign(mid_close=(bars["bid_close"] + bars["ask_close"]) / 2)
        if r == "hike_2022":
            mask = (bars_with_mid.index.date <= dt.date(2022, 12, 30))
        elif r == "hold_2023_24":
            mask = (bars_with_mid.index.date >= dt.date(2023, 1, 1)) & (bars_with_mid.index.date <= dt.date(2024, 6, 30))
        else:
            mask = (bars_with_mid.index.date >= dt.date(2024, 7, 1))
        h = hurst_log_returns(bars_with_mid.loc[mask, "mid_close"])
        print(f"  {r}: H={h:.3f}")

    # Verdict
    any_kill = any(not g.passed for g in gates if g.name.startswith("kill_"))
    verdict = "KILL" if any_kill else "PASS_TO_VERIFY"
    print()
    print("=" * 72)
    print(f"  VERDICT: {verdict}")
    print("=" * 72)

    # Persist
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = {
        "verdict": verdict,
        "panel": {
            "n_bars": int(len(bars)),
            "utc_start": str(bars.index.min()),
            "utc_end": str(bars.index.max()),
            "bid_le_ask_invariant": bid_le_ask,
        },
        "dst_check": dst_check,
        "n_trades": int(len(trades)),
        "regime_stats": regime_stats,
        "edge_perm": {
            "observed_mean_pips": edge_perm.observed,
            "p_two_sided": edge_perm.p_two_sided,
            "n": edge_perm.n,
            "n_perm": edge_perm.n_perm,
        },
        "rule1_inflated_regimes": rule1_flags,
        "correlation_slices": [
            {"key": k, "label": v.label, "n": v.n, "pearson_r": v.pearson_r}
            for k, v in slices.items()
        ],
        "gates": [
            {"name": g.name, "passed": g.passed, "measured": g.measured,
             "threshold": g.threshold, "note": g.note}
            for g in gates
        ],
        "spread_calibration": "PARAMETRIC (Pepperstone Razor literature defaults; no MT5 sample). "
                              "Survival verdict requires MT5 calibration before Verify. "
                              "Kill on cost grounds robust only if edge fails by wide margin.",
    }
    RESULTS_JSON.write_text(json.dumps(out, indent=2, default=str))
    print(f"Results -> {RESULTS_JSON}")
    return out


if __name__ == "__main__":
    run()
