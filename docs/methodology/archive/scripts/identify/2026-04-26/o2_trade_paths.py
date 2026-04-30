"""O2 — Intra-trade path (MFE/MAE) per realized trade.

For each trade, walks every 15min bar between entry and exit. Records MFE/MAE
in price, ATR-multiples, and R-multiples; time-to-MFE/MAE in bars.

Scope guard (per parent brief): diagnostic only. No trail/BE adjustment is
implied. Aegis BE accounts for ~41% of edge per locked validation.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from common import (
    STRATEGIES, PARAMS, OUT_DIR, META,
    load_bars, load_tv, utc_from_tv, compute_atr, add_meta_cols,
)


def trade_paths(strategy: str) -> pd.DataFrame:
    info = STRATEGIES[strategy]
    p = PARAMS[strategy]
    bars = load_bars(info["bar_symbol"])
    bars["atr"] = compute_atr(bars, p["atr_len"])

    tv = load_tv(strategy)
    tv = tv.dropna(subset=["entry_time", "exit_time"]).copy()
    tv["entry_utc"] = utc_from_tv(tv["entry_time"]).dt.floor("15min")
    tv["exit_utc"] = utc_from_tv(tv["exit_time"]).dt.floor("15min")

    rows = []
    for _, t in tv.iterrows():
        entry_utc = t["entry_utc"]
        exit_utc = t["exit_utc"]
        if entry_utc not in bars.index:
            # Try nearest bar (fill imperfections)
            slot = bars.index.get_indexer([entry_utc], method="nearest")[0]
            entry_utc = bars.index[slot]
        if exit_utc not in bars.index:
            slot = bars.index.get_indexer([exit_utc], method="nearest")[0]
            exit_utc = bars.index[slot]

        seg = bars.loc[entry_utc:exit_utc]
        if len(seg) == 0:
            continue
        entry_atr = float(bars.loc[entry_utc, "atr"]) if not pd.isna(bars.loc[entry_utc, "atr"]) else float("nan")
        entry_px = float(t["entry_price"])
        risk_pct = p["risk_pct"]

        # Long-only strategies — MFE = max high above entry, MAE = max low below entry
        max_high = float(seg["high"].max())
        min_low = float(seg["low"].min())

        mfe_price = max_high - entry_px
        mae_price = entry_px - min_low  # positive = adverse magnitude

        mfe_atr = mfe_price / entry_atr if entry_atr and entry_atr > 0 else float("nan")
        mae_atr = mae_price / entry_atr if entry_atr and entry_atr > 0 else float("nan")

        # R-multiple via TV's MFE/MAE % (cleanest — already equity-normalized)
        mfe_R = float(t["mfe_pct"]) / risk_pct if pd.notna(t["mfe_pct"]) else float("nan")
        mae_R = -float(t["mae_pct"]) / risk_pct if pd.notna(t["mae_pct"]) else float("nan")
        # mae_pct is negative in TV → mae_R positive magnitude

        time_to_mfe_bars = int(seg["high"].argmax())
        time_to_mae_bars = int(seg["low"].argmin())
        hold_bars = len(seg) - 1

        rows.append({
            "trade_id": int(t["Trade #"]),
            "entry_utc": entry_utc.isoformat(),
            "exit_utc": exit_utc.isoformat(),
            "entry_price": entry_px,
            "exit_price": float(t["exit_price"]),
            "exit_signal": t["exit_signal"],
            "entry_atr": entry_atr,
            "hold_bars": hold_bars,
            "mfe_price": mfe_price,
            "mae_price": mae_price,
            "mfe_atr": mfe_atr,
            "mae_atr": mae_atr,
            "mfe_R": mfe_R,
            "mae_R": mae_R,
            "time_to_mfe_bars": time_to_mfe_bars,
            "time_to_mae_bars": time_to_mae_bars,
            "net_pnl_pct": float(t["net_pnl_pct"]) if pd.notna(t["net_pnl_pct"]) else float("nan"),
            "net_pnl_R": (float(t["net_pnl_pct"]) / risk_pct) if pd.notna(t["net_pnl_pct"]) else float("nan"),
        })
    out = pd.DataFrame(rows)
    return add_meta_cols(out, strategy=strategy)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for s in STRATEGIES:
        df = trade_paths(s)
        out = OUT_DIR / f"O2_trade_paths_{s}.csv"
        df.to_csv(out, index=False)
        print(f"[O2] {s}: {len(df)} trades → {out.name}", flush=True)


if __name__ == "__main__":
    main()
