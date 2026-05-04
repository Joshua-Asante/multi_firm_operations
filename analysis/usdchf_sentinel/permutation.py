"""Sentinel gate permutation harness (parent brief §6).

Null specification (parent brief §6 + Q2 decision):
  Sample N entry timestamps from the (session × weekday) eligible pool
  without replacement; for each sampled timestamp, simulate the same
  short-entry / 3xATR-SL / 4xATR-TP / forward-walk semantics; aggregate
  trade outcomes; compute PF; repeat 1000x; derive empirical two-sided p
  on observed PF.

  This tests: "is the entry rule's PF distinguishable from random entry
  placement within the same session/weekday mask?"

Implementation:
  We precompute a per-bar "if-shorted-here" outcome (net_R) for every
  candidate bar in the pool. The permutation then samples N net_R values
  and recomputes PF — O(N x n_perm) with the heavy work amortized.

  Right-censored candidates (entry placed near panel-end whose forward
  walk does not terminate) are excluded from the pool, mirroring the
  actual strategy's behavior (all real trades closed by panel end).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

from analysis.usdchf_sentinel.sentinel_simulator import (
    PIP, RISK_PCT, SL_ATR_MULT, TP_ATR_MULT, COST_RT_PIPS,
    compute_indicators, candidate_entry_bars,
)


@dataclass
class PermutationResult:
    observed_pf: float
    n_real: int
    n_perm: int
    p_two_sided_pf: float
    null_pf_mean: float
    null_pf_p05: float
    null_pf_p50: float
    null_pf_p95: float
    pool_size: int
    censored_excluded: int


def precompute_pool_outcomes(bars: pd.DataFrame) -> pd.DataFrame:
    """For every candidate-pool bar, simulate the short trade that would
    result if Sentinel had entered there. Returns a DataFrame indexed by
    candidate-bar timestamp with columns ['net_R', 'net_pips', 'sl_pips',
    'exit_reason'].

    Right-censored entries (forward walk fails to terminate before panel
    end) are dropped.
    """
    panel = compute_indicators(bars)
    pool = candidate_entry_bars(bars)

    timestamps = panel.index
    highs = panel["high"].values
    lows = panel["low"].values

    ts_to_iloc = {ts: i for i, ts in enumerate(timestamps)}

    rows = []
    censored = 0
    for ts in pool.index:
        i = ts_to_iloc[ts]
        entry_px = float(panel["close"].iloc[i])
        atr = float(panel["atr14"].iloc[i])
        sl_px = entry_px + SL_ATR_MULT * atr
        tp_px = entry_px - TP_ATR_MULT * atr
        sl_pips = (sl_px - entry_px) / PIP
        # Forward walk
        exit_reason = None
        for j in range(i + 1, len(timestamps)):
            if highs[j] >= sl_px:
                raw_pips = (entry_px - sl_px) / PIP
                exit_reason = "sl"
                break
            if lows[j] <= tp_px:
                raw_pips = (entry_px - tp_px) / PIP
                exit_reason = "tp"
                break
        if exit_reason is None:
            censored += 1
            continue
        net_pips = raw_pips - COST_RT_PIPS
        net_R = net_pips / sl_pips
        rows.append({
            "ts": ts,
            "net_R": net_R,
            "net_pips": net_pips,
            "sl_pips": sl_pips,
            "exit_reason": exit_reason,
        })
    out = pd.DataFrame(rows).set_index("ts") if rows else pd.DataFrame(
        columns=["net_R", "net_pips", "sl_pips", "exit_reason"]
    )
    out.attrs["censored_excluded"] = censored
    return out


def _pf_from_R(net_R: np.ndarray) -> float:
    """Profit factor from net-R array. Returns inf when no losses."""
    wins = net_R[net_R > 0].sum()
    losses = -net_R[net_R < 0].sum()
    if losses == 0:
        return float("inf") if wins > 0 else float("nan")
    return float(wins / losses)


def permutation_test_pf(
    observed_R: np.ndarray,
    pool_R: np.ndarray,
    *,
    n_perm: int = 1000,
    seed: int = 42,
) -> PermutationResult:
    """Two-sided permutation p-value on profit factor.

    H0: observed PF could arise from drawing N entries uniformly without
    replacement from the (session × weekday) candidate pool. We compute
    the empirical PF distribution under H0 and report the fraction of
    null PFs >= observed (one-tailed upper) doubled for two-sided.
    """
    observed_R = np.asarray(observed_R, dtype=float)
    pool_R = np.asarray(pool_R, dtype=float)
    n = len(observed_R)
    if n < 2:
        raise AssertionError(f"permutation_test_pf: n={n} < 2")
    if len(pool_R) < n:
        raise AssertionError(
            f"permutation_test_pf: pool_size={len(pool_R)} < n={n}"
        )

    observed_pf = _pf_from_R(observed_R)
    rng = np.random.default_rng(seed)
    null_pf = np.empty(n_perm, dtype=float)
    for i in range(n_perm):
        sample_idx = rng.choice(len(pool_R), size=n, replace=False)
        null_pf[i] = _pf_from_R(pool_R[sample_idx])

    # One-tailed upper p; report two-sided as min(2p, 1) for symmetry-friendly output
    p_upper = float((null_pf >= observed_pf).mean())
    p_two = float(min(1.0, 2.0 * min(p_upper, 1.0 - p_upper)))

    finite = null_pf[np.isfinite(null_pf)]
    return PermutationResult(
        observed_pf=observed_pf,
        n_real=n,
        n_perm=n_perm,
        p_two_sided_pf=p_two,
        null_pf_mean=float(finite.mean()) if finite.size else float("nan"),
        null_pf_p05=float(np.percentile(finite, 5)) if finite.size else float("nan"),
        null_pf_p50=float(np.percentile(finite, 50)) if finite.size else float("nan"),
        null_pf_p95=float(np.percentile(finite, 95)) if finite.size else float("nan"),
        pool_size=len(pool_R),
        censored_excluded=0,
    )


if __name__ == "__main__":
    from analysis.usdchf_sentinel.bar_loader import load_usdchf_h4
    from analysis.usdchf_sentinel.sentinel_simulator import simulate

    bars = load_usdchf_h4()
    print(f"Loaded {len(bars)} bars; precomputing pool outcomes ...")
    pool = precompute_pool_outcomes(bars)
    print(f"Pool size: {len(pool)} (censored excluded: {pool.attrs['censored_excluded']})")

    trades = simulate(bars)
    print(f"Real trades: {len(trades)}")

    res = permutation_test_pf(
        trades["net_R"].values, pool["net_R"].values, n_perm=1000, seed=42,
    )
    print(f"Observed PF:    {res.observed_pf:.3f}")
    print(f"Null PF mean:   {res.null_pf_mean:.3f}")
    print(f"Null PF p05/p50/p95: {res.null_pf_p05:.3f} / {res.null_pf_p50:.3f} / {res.null_pf_p95:.3f}")
    print(f"p two-sided:    {res.p_two_sided_pf:.4f}")
