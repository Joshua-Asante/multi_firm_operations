"""O1 — Counterfactual / opportunity-cost: rejected-trade simulation.

For each bar where the strategy's signal fired but at least one filter blocked
the entry, walk forward on the actual bar series with the locked SL/TP/BE/
maxHold logic and record what the trade would have been.

Tag each rejected entry with which gate(s) blocked it.

SIMPLIFICATIONS (declared explicitly per Rule 1 / forbidden-D-test discipline):
  - Striker: base-leg only — pyramid (1.29 ATR + 6 bars, 350% size) NOT
    simulated. This UNDERSTATES Striker's edge per locked Pine notes
    ("entire structural edge"). Trail logic also omitted (BE only).
  - Striker: day soft-stop (-2% init eq) NOT enforced (would require running
    sim sequentially with equity tracking; treats each rejected bar as
    independent open).
  - Guardian: grace-stop (2.0× until bar 1) IS modelled.
  - Aegis: BE @ 0.3 ATR + 0.15 pad IS modelled. TP at basis + 0.8×ATR (BB)
    requires basis at entry — captured.
  - All sims assume fill at signal-bar close (matches Pine's
    process_orders_on_close semantics for the entry bar).
  - Position size ignored (sim outputs R-multiples, not $ P&L; multiplying by
    locked risk_pct gives % equity).

Scope guard (per parent brief): counterfactual P&L is descriptive evidence,
not a parameter signal. Filters are locked; a high-PF rejected cohort does
not authorize relaxing a filter. Routes Notice. Under amendment: OANDA-proxy.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import STRATEGIES, OUT_DIR, PARAMS, load_bars, add_meta_cols
from filters import EVAL


def simulate_trade_guardian(bars: pd.DataFrame, entry_idx: int, atr_at_entry: float) -> dict:
    """Forward-walk Guardian sim: SL 1.55×ATR, TP 29×ATR, grace 2.0× until bar 1, maxHold 850."""
    p = PARAMS["guardian"]
    if entry_idx >= len(bars):
        return _empty_sim()
    entry = bars.iloc[entry_idx]
    entry_px = float(entry["close"])
    sl_dist = atr_at_entry * p["stop_atr"]
    grace_sl_dist = sl_dist * 2.0
    tp_dist = atr_at_entry * p["tp_atr"]
    sl = entry_px - sl_dist
    grace_sl = entry_px - grace_sl_dist
    tp = entry_px + tp_dist
    max_hold = p["max_hold"]
    bars_held = 0
    mfe = 0.0
    mae = 0.0
    for i in range(entry_idx + 1, min(entry_idx + 1 + max_hold, len(bars))):
        bar = bars.iloc[i]
        bars_held += 1
        cur_sl = grace_sl if bars_held < 1 else sl
        # Worst case on a bar: stop hit before TP if low <= sl
        # (Pine grace stop semantics: bar 0 = entry bar; minBarsBeforeStop=1)
        # bars_held=1 means the bar right after entry. minBarsBeforeStop=1 means
        # grace applies for bar 1. Let's use grace_sl when bars_held == 1.
        cur_sl = grace_sl if bars_held == 1 else sl
        mfe = max(mfe, float(bar["high"]) - entry_px)
        mae = max(mae, entry_px - float(bar["low"]))
        if bar["low"] <= cur_sl:
            return _exit("stop", cur_sl - entry_px, bars_held, atr_at_entry, mfe, mae, p["risk_pct"], sl_dist)
        if bar["high"] >= tp:
            return _exit("tp", tp - entry_px, bars_held, atr_at_entry, mfe, mae, p["risk_pct"], sl_dist)
    # Stale exit
    final = bars.iloc[min(entry_idx + max_hold, len(bars) - 1)]
    pnl = float(final["close"]) - entry_px
    return _exit("stale", pnl, bars_held, atr_at_entry, mfe, mae, p["risk_pct"], sl_dist)


def simulate_trade_striker(bars: pd.DataFrame, entry_idx: int, atr_at_entry: float) -> dict:
    """Forward-walk Striker sim: SL 1.25×ATR, TP 8×ATR, BE @ 0.15 ATR + 0.05 pad, maxHold 55.
    SIMPLIFICATION: no pyramid, no trail."""
    p = PARAMS["striker"]
    if entry_idx >= len(bars):
        return _empty_sim()
    entry = bars.iloc[entry_idx]
    entry_px = float(entry["close"])
    sl_dist = atr_at_entry * p["stop_atr"]
    tp_dist = atr_at_entry * p["tp_atr"]
    sl = entry_px - sl_dist
    tp = entry_px + tp_dist
    be_trigger = entry_px + atr_at_entry * 0.15
    be_stop = entry_px + atr_at_entry * 0.05
    be_active = False
    bars_held = 0
    mfe = 0.0
    mae = 0.0
    for i in range(entry_idx + 1, min(entry_idx + 1 + p["max_hold"], len(bars))):
        bar = bars.iloc[i]
        bars_held += 1
        if not be_active and float(bar["high"]) >= be_trigger:
            be_active = True
            sl = max(sl, be_stop)
        mfe = max(mfe, float(bar["high"]) - entry_px)
        mae = max(mae, entry_px - float(bar["low"]))
        if bar["low"] <= sl:
            return _exit("stop_or_be" if be_active else "stop",
                         sl - entry_px, bars_held, atr_at_entry, mfe, mae,
                         p["risk_pct"], sl_dist)
        if bar["high"] >= tp:
            return _exit("tp", tp - entry_px, bars_held, atr_at_entry, mfe, mae, p["risk_pct"], sl_dist)
    final = bars.iloc[min(entry_idx + p["max_hold"], len(bars) - 1)]
    pnl = float(final["close"]) - entry_px
    return _exit("stale", pnl, bars_held, atr_at_entry, mfe, mae, p["risk_pct"], sl_dist)


def simulate_trade_aegis(bars: pd.DataFrame, entry_idx: int, atr_at_entry: float,
                         bb_basis_at_entry: float) -> dict:
    """Forward-walk Aegis sim: SL 1.42×ATR, TP basis+0.8×ATR, BE @ 0.3 ATR + 0.15 pad, maxHold 40."""
    p = PARAMS["aegis"]
    if entry_idx >= len(bars):
        return _empty_sim()
    entry = bars.iloc[entry_idx]
    entry_px = float(entry["close"])
    sl_dist = atr_at_entry * p["stop_atr"]
    sl = entry_px - sl_dist
    tp = bb_basis_at_entry + p["tp_offset_atr"] * atr_at_entry
    be_trigger = entry_px + atr_at_entry * p["be_trigger_atr"]
    be_stop = entry_px + atr_at_entry * p["be_pad_atr"]
    be_active = False
    bars_held = 0
    mfe = 0.0
    mae = 0.0
    for i in range(entry_idx + 1, min(entry_idx + 1 + p["max_hold"], len(bars))):
        bar = bars.iloc[i]
        bars_held += 1
        if not be_active and float(bar["high"]) >= be_trigger:
            be_active = True
            sl = max(sl, be_stop)
        mfe = max(mfe, float(bar["high"]) - entry_px)
        mae = max(mae, entry_px - float(bar["low"]))
        if bar["low"] <= sl:
            return _exit("stop_or_be" if be_active else "stop",
                         sl - entry_px, bars_held, atr_at_entry, mfe, mae,
                         p["risk_pct"], sl_dist)
        if bar["high"] >= tp:
            return _exit("tp", tp - entry_px, bars_held, atr_at_entry, mfe, mae, p["risk_pct"], sl_dist)
    final = bars.iloc[min(entry_idx + p["max_hold"], len(bars) - 1)]
    pnl = float(final["close"]) - entry_px
    return _exit("stale", pnl, bars_held, atr_at_entry, mfe, mae, p["risk_pct"], sl_dist)


def _exit(reason, pnl_price, bars_held, atr, mfe, mae, risk_pct, sl_dist):
    sim_R = pnl_price / sl_dist if sl_dist > 0 else 0.0
    return {
        "exit_reason": reason,
        "pnl_price": pnl_price,
        "bars_held": bars_held,
        "atr_at_entry": atr,
        "mfe_price": mfe,
        "mae_price": mae,
        "mfe_R": (mfe / sl_dist) if sl_dist > 0 else 0.0,
        "mae_R": (mae / sl_dist) if sl_dist > 0 else 0.0,
        "sim_R": sim_R,
        "sim_pnl_pct": sim_R * risk_pct,
    }


def _empty_sim():
    return {"exit_reason": "no_data", "pnl_price": 0.0, "bars_held": 0,
            "atr_at_entry": 0.0, "mfe_price": 0.0, "mae_price": 0.0,
            "mfe_R": 0.0, "mae_R": 0.0, "sim_R": 0.0, "sim_pnl_pct": 0.0}


# Filters per strategy: signal fires but at least one filter blocked
def rejected_universe(strategy: str, df: pd.DataFrame) -> pd.DataFrame:
    """Return rows where signal_raw==1 AND all_pass==0 AND atr is valid."""
    sig = (df["signal_raw"] == 1) & (df["all_pass"] == 0) & df["atr"].notna() & (df["atr"] > 0)
    rej = df.loc[sig].copy()
    # Tag blocking gates per row
    if strategy == "guardian":
        rej["block_day"] = (rej["day_pass"] == 0).astype(int)
        rej["block_session"] = (rej["session_pass"] == 0).astype(int)
        rej["block_hour"] = (rej["hour_pass"] == 0).astype(int)
        rej["block_TueH08"] = rej.get("block_TueH08", 0)
        rej["block_MonH08"] = rej.get("block_MonH08", 0)
        rej["block_MonH09"] = rej.get("block_MonH09", 0)
        rej["block_MonH12"] = rej.get("block_MonH12", 0)
        rej["block_TueH12"] = rej.get("block_TueH12", 0)
        rej["block_ThuH12"] = rej.get("block_ThuH12", 0)
    elif strategy == "striker":
        rej["block_atr"] = (rej["atr_expanding"] == 0).astype(int)
        rej["block_session"] = (rej["session_pass"] == 0).astype(int)
        rej["block_dow"] = (rej["dow_pass"] == 0).astype(int)
        rej["block_warmup"] = (rej["warmup_pass"] == 0).astype(int)
        rej["block_body"] = (rej["body_pass"] == 0).astype(int)
        rej["block_prev_bullish"] = (rej["prev_bullish"] == 0).astype(int)
    elif strategy == "aegis":
        rej["block_session"] = (rej["in_session"] == 0).astype(int)
        rej["block_hour"] = (rej["hour_pass"] == 0).astype(int)
        rej["block_day"] = (rej["day_pass"] == 0).astype(int)
        rej["block_vol"] = (rej["vol_pass"] == 0).astype(int)
        rej["block_TueH10"] = rej.get("block_TueH10", 0)
        rej["block_EOM"] = rej.get("block_EOM", 0)
    return rej


def simulate(strategy: str) -> pd.DataFrame:
    info = STRATEGIES[strategy]
    bars = load_bars(info["bar_symbol"]).reset_index()
    bars_idx = bars.set_index("time")
    df = EVAL[strategy](bars_idx).reset_index()
    rej = rejected_universe(strategy, df)
    print(f"[O1] {strategy}: rejected universe n={len(rej)}", flush=True)

    # Map index of rejected bars in the bars array
    bar_pos = pd.Series(range(len(bars)), index=bars["time"])
    sims = []
    for _, row in rej.iterrows():
        ts = row["time"]
        atr = float(row["atr"])
        idx = int(bar_pos.loc[ts])
        if strategy == "guardian":
            sim = simulate_trade_guardian(bars, idx, atr)
        elif strategy == "striker":
            sim = simulate_trade_striker(bars, idx, atr)
        elif strategy == "aegis":
            bb_basis = float(row["bb_basis"])
            if pd.isna(bb_basis):
                continue
            sim = simulate_trade_aegis(bars, idx, atr, bb_basis)
        sim["timestamp_utc"] = ts.isoformat()
        # Carry block flags
        for col in row.index:
            if col.startswith("block_"):
                sim[col] = int(row[col]) if pd.notna(row[col]) else 0
        sim["strategy"] = strategy
        sims.append(sim)

    out = pd.DataFrame(sims)
    if not out.empty:
        # Cohort sizes per blocking gate
        block_cols = [c for c in out.columns if c.startswith("block_")]
        for bc in block_cols:
            n_in_cohort = int(out[bc].sum())
            out[f"{bc}_cohort_n"] = n_in_cohort
        out["thin_cohort_any"] = out[[f"{bc}_cohort_n" for bc in block_cols]].min(axis=1).lt(10).astype(int)
    out = add_meta_cols(out, simulation_simplifications=(
        "Striker: base-leg only (no pyramid, no trail, no day-soft-stop). "
        "Guardian: grace-stop modelled. Aegis: BE modelled. "
        "All exits assume entry at signal-bar close."))
    return out


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for s in STRATEGIES:
        df = simulate(s)
        out = OUT_DIR / f"O1_rejected_trades_{s}.csv"
        df.to_csv(out, index=False)
        print(f"[O1] {s}: {len(df)} rejected sims → {out.name}", flush=True)


if __name__ == "__main__":
    main()
