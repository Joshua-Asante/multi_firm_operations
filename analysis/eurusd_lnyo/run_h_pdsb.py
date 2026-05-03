"""H-PDSB Inquire-phase orchestrator (G2 gate).

Runs single-config H-PDSB falsification per parent brief
docs/methodology/findings/2026-05-02_eurusd_m15_lnyo_notice.md, brief
commit hash c3ef0448984f6fe11fba440285b5323b35209ca5, plus the G2 entry
stub additions:

  - 1.0x and 1.25x spread variants (stub §5)
  - per-regime decision matrix (stub §2: any per-regime FAIL = G2 FAIL)
  - Friday-only Striker sub-test recorded as diagnostic (does not rescue)
  - Brief commit hash embedded in results

Six kill criteria per parent brief §4 H-PDSB:
  1. Net per-trade edge < 2.5 pips in any of three regimes
  2. Any single trade > 1.5% account loss -> instant kill
  3. p99 single-trade DD on MC > 2.5% account
  4. Daily P&L correlation with Striker > 0.30 conditional Tue+Fri
  5. Event-day count < 60 over 4-year panel triggers Rule 1
  6. Pre-announcement spread x5+ widening on >25% event days (op unreliability)

Output:
  analysis/eurusd_lnyo/results/h_pdsb_g2.json (1.0x spread)
  analysis/eurusd_lnyo/results/h_pdsb_g2_spread125.json (1.25x sensitivity)
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
    pdsb_simulator,
    pepperstone_spread,
    permutation,
)
from analysis.eurusd_lnyo import dxy_loader as dxy
from analysis.eurusd_lnyo.event_calendar import load_calendar, OUT as CAL_OUT

REPO_ROOT = Path(__file__).parent.parent.parent
RESULTS_DIR = Path(__file__).parent / "results"

BRIEF_COMMIT = "c3ef0448984f6fe11fba440285b5323b35209ca5"

# Kill thresholds (parent brief §4 H-PDSB)
KILL_EDGE_PIPS = 2.5
KILL_SINGLE_TRADE_PCT = 0.015          # 1.5% account
KILL_P99_DD_PCT = 0.025                # 2.5% account
KILL_STRIKER_CORR = 0.30
KILL_EVENT_N_FLOOR = 60
KILL_SPREAD_WIDEN_FRAC = 0.25
KILL_N_FLOOR = 100                      # parent brief §4 #6 perm-power floor
KILL_PERM_P = 0.05

# Account size for % conversions — match dd_protection STARTING_EQUITY = $200K
# Pip value per micro-lot of EURUSD ~= $0.10 per pip. For 1 standard lot = $10/pip.
# Position-sizing semantics: convert per-trade pips into approx % at typical EURUSD
# vol / typical PDSB stop-distance assuming ~0.5% risk per trade and pip-stop:
# this is a screening estimate, NOT trade-level risk. We compute trade-level loss as:
#   pct_loss_per_trade_estimate = abs(net_pips) * 0.5% / typical_stop_pips
# Where typical_stop_pips = mean of |range| of event bar = mean(|bar_high - bar_low|)
# in pips. That is computed from the trade dataframe per-regime.

REGIMES = ["hike_2022", "hold_2023_24", "ease_2024_26"]
RECENCY_REGIME = "ease_2024_26"


@dataclass
class GateResult:
    name: str
    passed: bool
    measured: float
    threshold: float
    note: str = ""


def evaluate_kill_1_edge_per_regime(trades: pd.DataFrame) -> list[GateResult]:
    out = []
    for r in REGIMES:
        sub = trades[trades["regime"] == r]
        n = len(sub)
        edge = float(sub["net_pips"].mean()) if n else float("nan")
        passed = (n > 0) and (edge >= KILL_EDGE_PIPS)
        out.append(GateResult(
            name=f"kill_1_edge[{r}]",
            passed=passed,
            measured=edge,
            threshold=KILL_EDGE_PIPS,
            note=f"n={n}, mean={edge:.3f} pips",
        ))
    return out


def per_trade_pct_estimate(trades: pd.DataFrame) -> pd.Series:
    """Convert per-trade pip P&L to approx account-% at risk-per-trade=0.5%.

    Uses each trade's stop distance (bar_high - bar_low for short fade,
    or close - bar_low for long fade etc.). For PDSB, SL = bar_high (short)
    or bar_low (long); entry = bar_close. Stop distance in pips:
        short fade: (bar_high - bar_close) / PIP
        long fade:  (bar_close - bar_low) / PIP

    pct_loss_per_trade = (-net_pips / stop_pips) * risk_per_trade
    """
    PIP = 0.0001
    risk_per_trade = 0.005  # 0.5% — screening estimate (not allocation)
    out = pd.Series(0.0, index=trades.index)
    for i, row in trades.iterrows():
        if row["direction"] == -1:
            stop_pips = (row["bar_high"] - row["bar_close"]) / PIP
        else:
            stop_pips = (row["bar_close"] - row["bar_low"]) / PIP
        if stop_pips <= 0:
            stop_pips = 1.0  # floor to avoid div-by-0
        # convert net pips to fraction of stop, then to fraction of account
        out.loc[i] = (row["net_pips"] / stop_pips) * risk_per_trade
    return out


def evaluate_kill_2_single_trade(trades: pd.DataFrame) -> GateResult:
    pct = per_trade_pct_estimate(trades)
    worst_loss = float(pct.min())  # most negative
    passed = worst_loss > -KILL_SINGLE_TRADE_PCT
    return GateResult(
        name="kill_2_single_trade",
        passed=passed,
        measured=worst_loss,
        threshold=-KILL_SINGLE_TRADE_PCT,
        note=f"worst single-trade pct = {worst_loss*100:.3f}% (threshold > -1.5%)",
    )


def evaluate_kill_3_p99_dd(trades: pd.DataFrame, n_boot: int = 5000,
                            seed: int = 42) -> GateResult:
    """p99 single-trade DD via bootstrap on per-trade pct estimates."""
    pct = per_trade_pct_estimate(trades).values
    if len(pct) == 0:
        return GateResult("kill_3_p99_dd", False, float("nan"), -KILL_P99_DD_PCT,
                          "no trades")
    # Bootstrap "single-trade DD" = abs of worst (most negative) trade per resample
    rng = np.random.default_rng(seed)
    n = len(pct)
    worst_per_sample = np.empty(n_boot)
    for b in range(n_boot):
        sample = rng.choice(pct, size=n, replace=True)
        worst_per_sample[b] = sample.min()  # most negative
    p99_loss = float(np.percentile(worst_per_sample, 1))  # 1st pctile (since negative)
    passed = p99_loss > -KILL_P99_DD_PCT
    return GateResult(
        name="kill_3_p99_dd",
        passed=passed,
        measured=p99_loss,
        threshold=-KILL_P99_DD_PCT,
        note=f"p99 worst-trade DD = {p99_loss*100:.3f}% (threshold > -2.5%)",
    )


def evaluate_kill_4_striker(slices: dict[str, correlation.CorrSlice]) -> GateResult:
    s = slices.get("striker_active_TueFri")
    if s is None:
        return GateResult("kill_4_striker", False, float("nan"), KILL_STRIKER_CORR,
                          "Striker slice missing")
    abs_r = abs(s.pearson_r) if not np.isnan(s.pearson_r) else float("nan")
    passed = (not np.isnan(abs_r)) and (abs_r <= KILL_STRIKER_CORR)
    return GateResult(
        name="kill_4_striker",
        passed=passed,
        measured=s.pearson_r,
        threshold=KILL_STRIKER_CORR,
        note=f"Tue+Fri n={s.n} |r|={abs_r:.3f}",
    )


def evaluate_kill_5_event_n(n_events: int) -> GateResult:
    passed = n_events >= KILL_EVENT_N_FLOOR
    return GateResult(
        name="kill_5_event_n",
        passed=passed,
        measured=n_events,
        threshold=KILL_EVENT_N_FLOOR,
        note=f"event count = {n_events}",
    )


def evaluate_kill_6_spread_widening(trades: pd.DataFrame) -> GateResult:
    """% of event days where the cost was 5x baseline (data-release widening
    minute or NFP first-min). Threshold > 25% triggers operational unreliability.
    """
    PIP = 0.0001
    base_perfill = pepperstone_spread.PEPPERSTONE_RAZOR_BASELINE_PIPS
    # cost_pips per trade = entry-side + exit-side (roughly 0.7 baseline RT).
    # 5x baseline RT = 0.7 * 5 = 3.5 pips per trade.
    threshold_cost = base_perfill * 2 * 5
    if trades.empty:
        return GateResult("kill_6_spread_widen", False, float("nan"),
                          KILL_SPREAD_WIDEN_FRAC, "no trades")
    high_cost_frac = float((trades["cost_pips"] >= threshold_cost).mean())
    passed = high_cost_frac < KILL_SPREAD_WIDEN_FRAC
    return GateResult(
        name="kill_6_spread_widen",
        passed=passed,
        measured=high_cost_frac,
        threshold=KILL_SPREAD_WIDEN_FRAC,
        note=f"{high_cost_frac:.1%} of trades at 5x+ baseline RT cost (threshold {KILL_SPREAD_WIDEN_FRAC:.0%})",
    )


def per_regime_kill_matrix(trades: pd.DataFrame, slices: dict, n_events: int,
                           ) -> list[GateResult]:
    """Build the full per-regime decision matrix.

    Some kill criteria are global (kill #5 event-N is panel-level). Others
    can be evaluated per-regime (kill #1 edge, kill #2 worst-trade,
    kill #3 p99-DD, kill #6 spread-widen).
    Kill #4 (Striker correlation) needs Tue+Fri slice, which requires daily
    aggregation -- evaluated per-regime via subset of nyfbo_daily.
    """
    matrix: list[GateResult] = []
    matrix.extend(evaluate_kill_1_edge_per_regime(trades))
    # kill #2, #3, #6 per regime
    for r in REGIMES:
        sub = trades[trades["regime"] == r].reset_index(drop=True)
        if len(sub):
            matrix.append(GateResult(
                name=f"kill_2_single_trade[{r}]",
                **_unpack_gr(evaluate_kill_2_single_trade(sub), name=f"kill_2_single_trade[{r}]")
            ))
            matrix.append(GateResult(
                name=f"kill_3_p99_dd[{r}]",
                **_unpack_gr(evaluate_kill_3_p99_dd(sub), name=f"kill_3_p99_dd[{r}]")
            ))
            matrix.append(GateResult(
                name=f"kill_6_spread_widen[{r}]",
                **_unpack_gr(evaluate_kill_6_spread_widening(sub), name=f"kill_6_spread_widen[{r}]")
            ))
        else:
            for k in ["kill_2_single_trade", "kill_3_p99_dd", "kill_6_spread_widen"]:
                matrix.append(GateResult(
                    name=f"{k}[{r}]", passed=False, measured=float("nan"),
                    threshold=float("nan"), note=f"empty regime"
                ))
    # kill #4 (Striker corr) panel-level Tue+Fri
    matrix.append(evaluate_kill_4_striker(slices))
    # kill #5 event-N panel-level
    matrix.append(evaluate_kill_5_event_n(n_events))
    return matrix


def _unpack_gr(g: GateResult, name: str) -> dict:
    return {"passed": g.passed, "measured": g.measured, "threshold": g.threshold,
            "note": g.note}


def run_one_spread_variant(spread_mult: float, *, bars: pd.DataFrame,
                            panel: pd.DataFrame, dxy_daily: pd.Series | None,
                            event_dates: set[dt.date],
                            event_type_lookup: dict) -> dict:
    print()
    print("=" * 72)
    print(f" H-PDSB G2 — spread multiplier = {spread_mult}x")
    print("=" * 72)

    cfg = pdsb_simulator.SimConfig(spread_multiplier=spread_mult)
    trades = pdsb_simulator.simulate_h_pdsb(
        bars, cfg=cfg,
        event_dates=event_dates,
        event_type_lookup=event_type_lookup,
    )
    print(f"Trades: {len(trades)}")
    if trades.empty:
        return {"verdict": "no_trades", "n_trades": 0, "spread_multiplier": spread_mult}

    # Per-regime stats
    print()
    print(f"{'Regime':<15} {'n':>5} {'mean_net':>10} {'median':>9} {'sum':>10}")
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
        print(f"{r:<15} {len(sub):>5d} {mean_p:>10.3f} {med_p:>9.3f} {sum_p:>10.1f}")

    # Daily aggregation + correlation slices
    pdsb_daily = pdsb_simulator.daily_pnl_pips(trades)
    print()
    print(f"PDSB daily series: {len(pdsb_daily)} days, sum={float(pdsb_daily.sum()):.1f} pips")
    slices = correlation.all_correlation_slices(pdsb_daily, panel, dxy_daily=dxy_daily)
    summary = correlation.summarize_slices(slices)
    print(summary.to_string(index=False))

    # Permutation gating
    print()
    edge_perm = permutation.edge_permutation_pvalue(
        trades["net_pips"].values, n_perm=1000, seed=42)
    print(f"Edge perm: observed={edge_perm.observed:.3f} pips, p={edge_perm.p_two_sided:.4f}, n={edge_perm.n}")

    # Rule-1 flags
    rule1_flags = []
    for r in REGIMES:
        n_r = regime_stats[r]["n"]
        if 0 < n_r < permutation.RULE1_THRESHOLD:
            rule1_flags.append(f"{r}(n={n_r})")
    if rule1_flags:
        print(f"Rule 1 small-cell flags: {rule1_flags}")
    else:
        print(f"Rule 1: all regimes n>={permutation.RULE1_THRESHOLD}")

    # Per-regime decision matrix
    print()
    print("=== Per-regime decision matrix ===")
    matrix = per_regime_kill_matrix(trades, slices, n_events=len(trades))
    print(f"{'criterion':<35} {'pass':>6} {'measured':>12} {'thresh':>10}  note")
    for g in matrix:
        flag = "PASS" if g.passed else "FAIL"
        m = g.measured
        if m is None or (isinstance(m, float) and np.isnan(m)):
            m_str = "NaN"
        else:
            m_str = f"{m:.4f}"
        t = g.threshold
        if t is None or (isinstance(t, float) and np.isnan(t)):
            t_str = "NaN"
        else:
            t_str = f"{t:.3f}"
        print(f"{g.name:<35} {flag:>6} {m_str:>12} {t_str:>10}  {g.note}")

    # Per-regime FAIL = G2 FAIL (per stub §2)
    any_fail = any(not g.passed for g in matrix)
    verdict = "FAIL_G2" if any_fail else "PASS_TO_VERIFY"
    print()
    print(f"VERDICT (spread {spread_mult}x): {verdict}")

    return {
        "verdict": verdict,
        "spread_multiplier": spread_mult,
        "n_trades": int(len(trades)),
        "regime_stats": regime_stats,
        "edge_perm": {
            "observed_mean_pips": float(edge_perm.observed),
            "p_two_sided": float(edge_perm.p_two_sided),
            "n": int(edge_perm.n),
        },
        "rule1_inflated_regimes": rule1_flags,
        "correlation_slices": [
            {"key": k, "label": v.label, "n": v.n, "pearson_r": v.pearson_r}
            for k, v in slices.items()
        ],
        "matrix": [
            {"name": g.name, "passed": g.passed,
             "measured": (None if (isinstance(g.measured, float) and np.isnan(g.measured)) else g.measured),
             "threshold": (None if (isinstance(g.threshold, float) and np.isnan(g.threshold)) else g.threshold),
             "note": g.note}
            for g in matrix
        ],
    }


def main():
    print("=" * 72)
    print(f" H-PDSB G2 — brief commit {BRIEF_COMMIT[:8]}")
    print("=" * 72)

    # 1. Load Dukascopy
    print("[1/4] Loading Dukascopy panel...")
    bars = dukascopy_loader.load_eurusd_m15_bidask()
    print(f"      {len(bars):,} bars, {bars.index.min()} -> {bars.index.max()}")

    # 2. Event calendar
    print()
    print("[2/4] Event calendar...")
    cal = load_calendar()
    if not cal:
        raise RuntimeError("No event calendar found; run analysis/eurusd_lnyo/event_calendar.py first")
    event_dates = set(d for d, _ in cal)
    event_type_lookup = {}
    for d, ev in cal:
        event_type_lookup.setdefault(d, ev)
    print(f"      Events: {len(cal)}; types: NFP/CPI/RetailSales/PCE/GDP_Advance")

    # 3. G/S/A panel + DXY
    print()
    print("[3/4] G/S/A panel + DXY...")
    panel = correlation.load_gsa_daily_panel()
    print(f"      G/S/A panel: {panel.index.min().date()} -> {panel.index.max().date()}")
    try:
        dxy_df = dxy.load_dxy()
        dxy_daily = dxy_df["dxy_chg"]
        print(f"      DXY: {len(dxy_df)} days")
    except FileNotFoundError:
        dxy_daily = None
        print("      DXY missing")

    # 4. Run both spread variants
    print()
    print("[4/4] Running 1.0x and 1.25x spread variants...")
    out_10x = run_one_spread_variant(
        1.0, bars=bars, panel=panel, dxy_daily=dxy_daily,
        event_dates=event_dates, event_type_lookup=event_type_lookup,
    )
    out_125x = run_one_spread_variant(
        1.25, bars=bars, panel=panel, dxy_daily=dxy_daily,
        event_dates=event_dates, event_type_lookup=event_type_lookup,
    )

    # Routing per stub §2
    v10 = out_10x.get("verdict")
    v125 = out_125x.get("verdict")
    if v10 == "PASS_TO_VERIFY" and v125 == "PASS_TO_VERIFY":
        routing = "PASS"
    elif v10 == "PASS_TO_VERIFY" and v125 != "PASS_TO_VERIFY":
        routing = "CONDITIONAL_PASS_MT5_PREREQ"
    else:
        # FAIL — classify mode
        # Check whether any per-regime kill_1_edge fails badly (negative gross edge)
        # vs whether only operational kills (kill #2 single-trade, kill #6 spread)
        # vs only kill #5 N
        m = out_10x.get("matrix", [])
        edge_fails = [g for g in m if g["name"].startswith("kill_1_edge[") and not g["passed"]]
        op_only_fails = [g for g in m if (g["name"].startswith("kill_2_") or
                                           g["name"].startswith("kill_6_")) and not g["passed"]]
        n_fail = next((g for g in m if g["name"] == "kill_5_event_n" and not g["passed"]), None)
        non_op_fails = [g for g in m if not g["passed"] and not (
            g["name"].startswith("kill_2_") or g["name"].startswith("kill_6_") or
            g["name"] == "kill_5_event_n"
        )]
        if non_op_fails:
            routing = "FAIL_STRUCTURAL_G4"  # M15-FX stop-rule fires
        elif n_fail and not (op_only_fails or edge_fails):
            routing = "FAIL_SMALL_CELL_DEFER"
        elif op_only_fails and not edge_fails:
            routing = "FAIL_OPERATIONAL_G3"
        else:
            routing = "FAIL_STRUCTURAL_G4"

    print()
    print("=" * 72)
    print(f" G2 ROUTING: {routing}")
    print(f"   1.0x spread verdict: {v10}")
    print(f"   1.25x spread verdict: {v125}")
    print("=" * 72)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_10x["brief_commit_hash"] = BRIEF_COMMIT
    out_125x["brief_commit_hash"] = BRIEF_COMMIT
    out_10x["routing"] = routing
    out_125x["routing"] = routing
    (RESULTS_DIR / "h_pdsb_g2.json").write_text(json.dumps(out_10x, indent=2, default=str))
    (RESULTS_DIR / "h_pdsb_g2_spread125.json").write_text(json.dumps(out_125x, indent=2, default=str))
    print(f"Results -> {RESULTS_DIR / 'h_pdsb_g2.json'}")
    print(f"Results -> {RESULTS_DIR / 'h_pdsb_g2_spread125.json'}")

    return out_10x, out_125x


if __name__ == "__main__":
    main()
