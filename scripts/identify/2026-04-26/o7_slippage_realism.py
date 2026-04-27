"""O7 — Execution realism / slippage proxy.

For each realized entry and exit timestamp:
  - Bar-to-bar gap from prior close to fill price
  - Segmented by session-boundary type:
      intra      = no gap from prior bar
      reopen_w   = >2h gap (weekly Sunday-evening reopen)
      gap_minor  = >1 bar (15m) but <2h gap

Scope guard (per parent brief): O7 characterizes the *modeling* assumption,
not realised execution. DXTrade actuals are not in this corpus. Findings
route to Notice; re-MC trigger list unchanged.

Rule 1 (small-cell variance prior): every cell with n<10 is flagged via
the thin_cohort column.
"""
from __future__ import annotations

import pandas as pd

from common import (
    STRATEGIES, OUT_DIR, load_bars, load_tv, utc_from_tv, add_meta_cols,
)


def classify_gap(gap_minutes: float) -> str:
    if gap_minutes <= 16:    # one 15m bar (small slop)
        return "intra"
    if gap_minutes >= 120:
        return "reopen_w"
    return "gap_minor"


def slippage_for(strategy: str) -> pd.DataFrame:
    info = STRATEGIES[strategy]
    bars = load_bars(info["bar_symbol"])
    tv = load_tv(strategy)
    rows = []

    for _, t in tv.iterrows():
        for kind, ts_col, px_col in [
            ("entry", "entry_time", "entry_price"),
            ("exit",  "exit_time",  "exit_price"),
        ]:
            if pd.isna(t[ts_col]) or pd.isna(t[px_col]):
                continue
            tv_ts = pd.Series([t[ts_col]])
            utc = utc_from_tv(tv_ts).iloc[0].floor("15min")
            if utc not in bars.index:
                slot = bars.index.get_indexer([utc], method="nearest")[0]
                utc = bars.index[slot]
            bar = bars.loc[utc]
            # Find prior bar
            pos = bars.index.get_loc(utc)
            if pos == 0:
                continue
            prev_bar = bars.iloc[pos - 1]
            prev_bar_close = float(prev_bar["close"])
            prev_bar_time = bars.index[pos - 1]
            gap_minutes = (utc - prev_bar_time).total_seconds() / 60.0
            kind_tag = classify_gap(gap_minutes)

            fill_px = float(t[px_col])
            bar_open = float(bar["open"])
            bar_close = float(bar["close"])
            # Slippage proxies:
            #   vs_prev_close = fill - prev_close (gap component)
            #   vs_bar_open   = fill - bar_open   (intra-bar drift to fill)
            #   vs_bar_close  = fill - bar_close  (Pine fires on close; mismatch)
            rows.append({
                "trade_id": int(t["Trade #"]),
                "leg": kind,
                "utc": utc.isoformat(),
                "boundary": kind_tag,
                "gap_minutes": gap_minutes,
                "fill_price": fill_px,
                "prev_close": prev_bar_close,
                "bar_open": bar_open,
                "bar_close": bar_close,
                "delta_vs_prev_close": fill_px - prev_bar_close,
                "delta_vs_bar_open": fill_px - bar_open,
                "delta_vs_bar_close": fill_px - bar_close,
            })

    df = pd.DataFrame(rows)
    if df.empty:
        return add_meta_cols(df, strategy=strategy)

    # Rule 1 — flag small cohorts per (leg, boundary)
    counts = df.groupby(["leg", "boundary"]).size().rename("cell_n").reset_index()
    df = df.merge(counts, on=["leg", "boundary"], how="left")
    df["thin_cohort"] = (df["cell_n"] < 10).astype(int)
    return add_meta_cols(df, strategy=strategy)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for s in STRATEGIES:
        df = slippage_for(s)
        out = OUT_DIR / f"O7_slippage_realism_{s}.csv"
        df.to_csv(out, index=False)
        thin = int(df["thin_cohort"].sum()) if "thin_cohort" in df.columns else 0
        print(f"[O7] {s}: {len(df)} legs ({thin} in thin cohorts) → {out.name}", flush=True)


if __name__ == "__main__":
    main()
