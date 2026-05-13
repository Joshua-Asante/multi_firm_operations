"""Per-trade TV panel metrics for WFO train selection (Q-CORR-1.2 §14 / §16)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def trade_panel_metrics(
    trades: pd.DataFrame,
    *,
    notional: float = 200_000.0,
) -> dict[str, float | int]:
    """PF, WR%, max DD% (vs notional), n_trades, MFE/MAE asymmetry from paired export."""
    if trades.empty:
        raise ValueError("empty trades frame")
    pnl = trades["net_pnl_usd"].astype(float)
    n = int(len(trades))
    wins = (pnl > 0).sum()
    wr_pct = 100.0 * float(wins) / float(n) if n else 0.0
    pos = float(pnl[pnl > 0].sum())
    neg = float(pnl[pnl < 0].sum())
    pf = pos / abs(neg) if neg < 0 else float("inf")

    t = trades.copy()
    t = t.sort_values("exit_ts")
    eq = t["net_pnl_usd"].astype(float).cumsum()
    peak = eq.cummax()
    dd_pct = float(((peak - eq) / float(notional)).max() * 100.0)

    mfe = float(trades["mfe_usd"].astype(float).sum())
    mae_abs = float(trades["mae_usd"].astype(float).abs().sum())
    denom = max(mae_abs, 1e-9)
    mfe_mae_ratio = mfe / denom

    return {
        "n_trades": n,
        "pf": float(pf) if np.isfinite(pf) else 0.0,
        "wr_pct": float(wr_pct),
        "max_dd_pct": float(dd_pct),
        "mfe_mae_ratio": float(mfe_mae_ratio),
    }
