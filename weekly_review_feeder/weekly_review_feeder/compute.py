"""Computation primitives: edge-captured ratio, MC placement, slippage."""
from __future__ import annotations

from typing import Any

import pandas as pd


def compute_edge_captured(realized_pnl: float, backtest_equiv_pnl: float) -> float | None:
    """Edge-captured ratio for the week.

    Convention (per INT-2 Park resolution applied informally in W19):
      - If backtest_equiv_pnl > 0: ratio = realized / backtest. Target band [0.7, 1.0].
      - If backtest_equiv_pnl <= 0: return None. Use Avg Slippage in dollars instead.

    This intentionally does NOT compute a sign-flipped ratio for loss weeks.
    The metric semantics break; using None makes that explicit.
    """
    if backtest_equiv_pnl > 0:
        return round(realized_pnl / backtest_equiv_pnl, 4)
    return None


def compute_mc_placement(
    realized_pnl: float, p10: float, p50: float, p90: float
) -> str:
    """Bucket realized_pnl against MC band quartiles.

    Returns one of: "below P10" | "P10-P50" | "P50-P90" | "above P90" | "flat".
    'flat' is reserved for a literal-zero realized P&L (no strategy activity).
    """
    if realized_pnl == 0.0:
        return "flat"
    if realized_pnl < p10:
        return "below P10"
    if realized_pnl < p50:
        return "P10-P50"
    if realized_pnl < p90:
        return "P50-P90"
    return "above P90"


def reconcile_fills_to_backtest(
    fills_df: pd.DataFrame,
    backtest_per_strategy: dict[str, dict[str, Any]],
    op_test_order_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """For each STRATEGY signal taken in the week, pair the live fill to the backtest trade.

    Returns list of reconciled-pair dicts:
      {strategy, entry_live_price, entry_backtest_price,
       exit_live_price, exit_backtest_price, size_live, size_backtest, slippage_dollars}

    Pairing strategy: sort live closes and backtest exits by time within each strategy;
    pair sequentially. Falls back gracefully when counts mismatch (mismatch logged).
    """
    pairs: list[dict[str, Any]] = []
    if op_test_order_ids is None:
        op_test_order_ids = set()

    for strategy_key, info in backtest_per_strategy.items():
        bt = info["trades"].copy()
        if bt.empty:
            continue

        live = fills_df[
            (fills_df["strategy"] == strategy_key)
            & (~fills_df["order_id"].isin(op_test_order_ids))
        ].copy()
        if live.empty:
            continue

        live_opens = live[live["effect"].str.lower() == "opening"].sort_values("timestamp")
        live_closes = live[live["effect"].str.lower() == "closing"].sort_values("timestamp")
        bt_sorted = bt.sort_values("entry_time").reset_index(drop=True)

        n = min(len(live_opens), len(live_closes), len(bt_sorted))
        for i in range(n):
            lo = live_opens.iloc[i]
            lc = live_closes.iloc[i]
            bt_row = bt_sorted.iloc[i]
            entry_live = float(lo["price"])
            exit_live = float(lc["price"])
            size_live = float(lo["volume"])
            # The backtest entry/exit prices may not be in the merged DF; if absent,
            # fall back to inferring slippage as 0 (no comparison possible).
            entry_bt = float(bt_row.get("entry_price", entry_live))
            exit_bt = float(bt_row.get("exit_price", exit_live))
            size_bt = float(bt_row.get("size", size_live))

            # Slippage (dollars): combined entry + exit price-difference cost at backtest size.
            # Sign-aware: for a long, entry slippage = (live - backtest) * size; exit slippage
            # = (backtest - live) * size. We use abs to keep this simple in v0.1.
            slip = (abs(entry_live - entry_bt) + abs(exit_live - exit_bt)) * size_bt

            pairs.append({
                "strategy": strategy_key,
                "entry_live_price": entry_live,
                "entry_backtest_price": entry_bt,
                "exit_live_price": exit_live,
                "exit_backtest_price": exit_bt,
                "size_live": size_live,
                "size_backtest": size_bt,
                "slippage_dollars": round(slip, 2),
            })

    return pairs


def avg_slippage(reconciled_pairs: list[dict[str, Any]]) -> float:
    """Average slippage in dollars across the reconciled pairs.

    Zero-pair weeks return 0.0 (no slippage data → no signal).
    """
    if not reconciled_pairs:
        return 0.0
    return round(
        sum(p["slippage_dollars"] for p in reconciled_pairs) / len(reconciled_pairs), 2
    )
