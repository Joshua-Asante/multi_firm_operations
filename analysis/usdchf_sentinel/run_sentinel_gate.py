"""Sentinel USDCHF H4 gate orchestrator (parent brief §6).

Runs the gate end-to-end:
  1. Load Pepperstone H4 panel (bar_loader)
  2. Simulate Sentinel (no overlay)
  3. Compute N, PF, max DD, gross-profit/loss decomposition, ATR-quartile breakdown
  4. Permutation null on PF (1000 shuffles, session x weekday mask)
  5. Daily P&L correlation vs Guardian/Striker/Aegis (Pepperstone-locked)
  6. Decision-tree verdict per parent brief §8
  7. Emit JSON + single-page markdown report

Parent brief gate criteria (§4 H):
  (a) N >= 80
  (b) PF >= 2.0
  (c) max DD < 3.0%
  (d) permutation p < 0.05
  All four must clear simultaneously to authorize build.

Outputs:
  analysis/usdchf_sentinel/results/sentinel_gate.json
  docs/methodology/findings/2026-05-03_usdchf_h4_sentinel_gate.md
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.eurusd_lnyo.correlation import load_gsa_daily_panel
from analysis.usdchf_sentinel.bar_loader import load_usdchf_h4
from analysis.usdchf_sentinel.permutation import (
    permutation_test_pf, precompute_pool_outcomes,
)
from analysis.usdchf_sentinel.sentinel_simulator import (
    RISK_PCT, simulate,
)

REPO_ROOT = Path(__file__).parent.parent.parent
RESULTS_DIR = Path(__file__).parent / "results"
REPORT_PATH = REPO_ROOT / "docs" / "methodology" / "findings" / "2026-05-03_usdchf_h4_sentinel_gate.md"

# Gate thresholds
GATE_N_FLOOR = 80
GATE_PF_FLOOR = 2.0
GATE_MAX_DD_PCT = 0.03         # 3.0% max equity drawdown
GATE_PERM_P = 0.05
GATE_GSA_CORR = 0.30           # H3 park trigger (parent brief §5)


def gross_decomposition(trades: pd.DataFrame) -> dict:
    """Profit factor + numerator/denominator decomposition.

    Memory note: PF = gross_profit / gross_loss; flag when denominator-driven
    (gross_loss near zero -> PF inflation that's bootstrap-fragile).
    """
    if trades.empty:
        return {"pf": float("nan"), "gross_profit_R": 0.0, "gross_loss_R": 0.0,
                "n_wins": 0, "n_losses": 0, "win_rate": float("nan")}
    R = trades["net_R"].values
    gp = float(R[R > 0].sum())
    gl = -float(R[R < 0].sum())
    n_w = int((R > 0).sum())
    n_l = int((R < 0).sum())
    pf = (gp / gl) if gl > 0 else (float("inf") if gp > 0 else float("nan"))
    return {
        "pf": pf,
        "gross_profit_R": gp,
        "gross_loss_R": gl,
        "n_wins": n_w,
        "n_losses": n_l,
        "win_rate": (n_w / (n_w + n_l)) if (n_w + n_l) else float("nan"),
    }


def equity_max_drawdown(trades: pd.DataFrame) -> dict:
    """Compute max equity drawdown across the trade-by-trade equity curve.

    Equity curve: cumulative sum of pct_account, indexed by exit timestamp.
    max DD = max(peak - equity) over the curve, expressed as account fraction.
    """
    if trades.empty:
        return {"max_dd_pct": 0.0, "max_dd_at": None,
                "final_equity_pct": 0.0}
    seq = trades.sort_values("exit_ts").reset_index(drop=True)
    equity = seq["pct_account"].cumsum().values
    # Include starting equity 0
    equity_full = np.concatenate([[0.0], equity])
    peaks = np.maximum.accumulate(equity_full)
    dd = peaks - equity_full
    i_max = int(np.argmax(dd))
    max_dd = float(dd[i_max])
    if i_max == 0:
        max_dd_at = None
    else:
        max_dd_at = str(seq["exit_ts"].iloc[i_max - 1])
    return {
        "max_dd_pct": max_dd,
        "max_dd_at": max_dd_at,
        "final_equity_pct": float(equity[-1]),
    }


def atr_quartile_breakdown(trades: pd.DataFrame) -> dict:
    """Per-ATR-quartile PF / N / win-rate.

    Q2 decision (parent brief): regime tag stays as diagnostic, never a filter.
    Concentration in a single quartile -> denominator-driven PF risk -> watch
    item rather than build (per memory: PF numerator/denominator decomposition).
    """
    out = {}
    for q in [1, 2, 3, 4]:
        sub = trades[trades["atr_quartile"] == q]
        out[f"q{q}"] = gross_decomposition(sub)
        out[f"q{q}"]["n"] = int(len(sub))
    return out


def daily_correlations(trades: pd.DataFrame) -> dict:
    """Pearson correlation of Sentinel daily P&L vs G/S/A daily P&L.

    Sentinel P&L aggregated by EXIT date (when P&L crystallizes).
    G/S/A daily panel via analysis.eurusd_lnyo.correlation.load_gsa_daily_panel.
    Both series tz-naive at daily granularity to match panel convention.
    """
    if trades.empty:
        return {"guardian": float("nan"), "striker": float("nan"),
                "aegis": float("nan"), "n_days": 0}
    sentinel_daily = (
        trades.assign(exit_date=pd.to_datetime(trades["exit_ts"]).dt.tz_localize(None).dt.normalize())
        .groupby("exit_date")["pct_account"].sum()
    )
    panel = load_gsa_daily_panel()
    # Align to panel's bdate index; missing Sentinel days = 0 P&L
    aligned = pd.DataFrame(index=panel.index)
    aligned["sentinel"] = sentinel_daily.reindex(panel.index).fillna(0.0)
    aligned["guardian"] = panel["guardian"]
    aligned["striker"] = panel["striker"]
    aligned["aegis"] = panel["aegis"]
    overlap = aligned.dropna()

    def corr(a, b):
        if a.std(ddof=0) == 0 or b.std(ddof=0) == 0:
            return float("nan")
        return float(np.corrcoef(a, b)[0, 1])

    return {
        "guardian": corr(overlap["sentinel"], overlap["guardian"]),
        "striker": corr(overlap["sentinel"], overlap["striker"]),
        "aegis": corr(overlap["sentinel"], overlap["aegis"]),
        "n_days": int(len(overlap)),
    }


def decide_verdict(*, n: int, pf: float, max_dd: float, perm_p: float,
                   corr_gsa: dict) -> dict:
    """Apply the parent brief §8 decision tree.

    Returns a dict with verdict in {H1_BUILD, H3_PARK, H0_KILL, H2_KILL,
    DD_KILL, N_KILL} and a per-criterion pass/fail.
    """
    crit = {
        "a_n_floor":       {"passed": n >= GATE_N_FLOOR,
                            "measured": n, "threshold": GATE_N_FLOOR},
        "b_pf_floor":      {"passed": (not np.isnan(pf)) and pf >= GATE_PF_FLOOR,
                            "measured": pf, "threshold": GATE_PF_FLOOR},
        "c_max_dd":        {"passed": max_dd < GATE_MAX_DD_PCT,
                            "measured": max_dd, "threshold": GATE_MAX_DD_PCT},
        "d_perm_p":        {"passed": perm_p < GATE_PERM_P,
                            "measured": perm_p, "threshold": GATE_PERM_P},
    }
    fails = [k for k, v in crit.items() if not v["passed"]]

    if not fails:
        max_abs_corr = max(abs(corr_gsa.get(s, 0.0)) for s in ["guardian", "striker", "aegis"])
        if max_abs_corr > GATE_GSA_CORR:
            verdict = "H3_PARK"
            reason = f"all four clear but |corr|>{GATE_GSA_CORR} vs G/S/A"
        else:
            verdict = "H1_BUILD"
            reason = "all four clear; corr below park threshold"
    else:
        # Attribute failure mode per parent brief §8
        if "a_n_floor" in fails and len(fails) == 1:
            verdict = "N_KILL"
            reason = "N below floor; signal too rare on H4"
        elif "c_max_dd" in fails and len(fails) == 1:
            verdict = "DD_KILL"
            reason = "max DD breach even with PF clearing"
        elif "d_perm_p" in fails:
            verdict = "H2_KILL"
            reason = "entries indistinguishable from random within mask"
        else:
            verdict = "H0_KILL"
            reason = "edge absent or below threshold"

    return {"verdict": verdict, "reason": reason, "criteria": crit, "fails": fails}


def run() -> dict:
    print("=" * 72)
    print(" Sentinel USDCHF H4 gate")
    print("=" * 72)

    print("\n[1/5] Loading Pepperstone USDCHF H4 panel ...")
    bars = load_usdchf_h4()
    print(f"      {len(bars):,} bars  span {bars.index[0]} -> {bars.index[-1]}")

    print("\n[2/5] Simulating Sentinel (no overlay) ...")
    trades = simulate(bars)
    print(f"      Trades: {len(trades)}")

    print("\n[3/5] Stats: PF / max DD / ATR-quartile breakdown ...")
    decomp = gross_decomposition(trades)
    dd = equity_max_drawdown(trades)
    quartiles = atr_quartile_breakdown(trades)
    print(f"      N={len(trades)}  win_rate={decomp['win_rate']:.3f}")
    print(f"      PF={decomp['pf']:.3f}   gross_profit_R={decomp['gross_profit_R']:.2f}   "
          f"gross_loss_R={decomp['gross_loss_R']:.2f}")
    print(f"      max DD = {dd['max_dd_pct']*100:.3f}%   (at {dd['max_dd_at']})")
    print(f"      final equity = {dd['final_equity_pct']*100:.3f}%")
    print(f"      ATR quartiles (n / pf):")
    for q in [1, 2, 3, 4]:
        d = quartiles[f"q{q}"]
        pf_str = f"{d['pf']:.3f}" if not np.isnan(d['pf']) else "nan"
        print(f"        Q{q}: n={d['n']:3d}  pf={pf_str}  win_rate={d['win_rate']:.3f}"
              f"   gp_R={d['gross_profit_R']:.2f}  gl_R={d['gross_loss_R']:.2f}")

    print("\n[4/5] Permutation null (PF, 1000 shuffles, session x weekday mask) ...")
    pool = precompute_pool_outcomes(bars)
    print(f"      Pool size: {len(pool)}  (censored excluded: {pool.attrs['censored_excluded']})")
    perm = permutation_test_pf(
        trades["net_R"].values, pool["net_R"].values, n_perm=1000, seed=42,
    )
    print(f"      Observed PF: {perm.observed_pf:.3f}")
    print(f"      Null PF p05/p50/p95: {perm.null_pf_p05:.3f} / {perm.null_pf_p50:.3f} / {perm.null_pf_p95:.3f}")
    print(f"      p two-sided: {perm.p_two_sided_pf:.4f}")

    print("\n[5/5] Daily P&L correlation vs G/S/A ...")
    corr = daily_correlations(trades)
    print(f"      n_days overlap: {corr['n_days']}")
    print(f"      guardian: {corr['guardian']:+.3f}")
    print(f"      striker:  {corr['striker']:+.3f}")
    print(f"      aegis:    {corr['aegis']:+.3f}")

    verdict = decide_verdict(
        n=len(trades), pf=decomp["pf"], max_dd=dd["max_dd_pct"],
        perm_p=perm.p_two_sided_pf, corr_gsa=corr,
    )
    print()
    print("=" * 72)
    print(f" VERDICT: {verdict['verdict']}")
    print(f"   reason: {verdict['reason']}")
    print(f"   fails:  {verdict['fails']}")
    print("=" * 72)

    out = {
        "n_trades": int(len(trades)),
        "decomposition": decomp,
        "max_dd": dd,
        "atr_quartiles": quartiles,
        "permutation": asdict(perm),
        "corr_gsa": corr,
        "verdict": verdict,
        "config": {
            "risk_pct": RISK_PCT,
            "sl_atr_mult": 3.0, "tp_atr_mult": 4.0,
            "atr_len": 14, "ema_len": 50, "donchian_len": 20,
            "session_hours_utc": [8, 17],
            "cost_rt_pips": 1.0,
            "gate_thresholds": {
                "n_floor": GATE_N_FLOOR, "pf_floor": GATE_PF_FLOOR,
                "max_dd_pct": GATE_MAX_DD_PCT, "perm_p": GATE_PERM_P,
                "park_corr": GATE_GSA_CORR,
            },
        },
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "sentinel_gate.json").write_text(
        json.dumps(out, indent=2, default=str)
    )
    print(f"\nResults -> {RESULTS_DIR / 'sentinel_gate.json'}")
    return out


if __name__ == "__main__":
    run()
