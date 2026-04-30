"""O3 — Setup-to-fire conversion funnel per strategy.

Static funnel (count + conversion rate per stage) and rolling 90-day
conversion rate to expose drift.

Stages applied IN ORDER (each stage's count is conditioned on all prior
stages passing):

  Guardian: signal (EMA cross + bullTrend) → day → session → hour-block
  Striker:  signal (raw breakout) → ATR expanding → session → warmup → DOW
            → body+prev_bullish
  Aegis:    signal (BB touch) → in_session → hour_ok → day_ok → vol_ok
            → not Tue-H10 → not EOM

Scope guard (per parent brief): conversion-rate drift is a regime-change
candidate signal, not a parameter signal. Routes Notice. Under amendment:
OANDA-proxy only.
"""
from __future__ import annotations

import pandas as pd

from common import STRATEGIES, OUT_DIR, load_bars, add_meta_cols
from filters import EVAL


# Funnel stage order per strategy. Each stage is a column name from the eval'd df.
STAGES = {
    "guardian": ["signal_raw", "day_pass", "session_pass", "hour_pass"],
    "striker": ["signal_raw", "atr_expanding", "session_pass", "warmup_pass",
                "dow_pass", "body_pass", "prev_bullish"],
    "aegis": ["signal_raw", "in_session", "hour_pass", "day_pass", "vol_pass",
              "block_TueH10", "block_EOM"],
}


def funnel_static(df: pd.DataFrame, stages: list[str], strategy: str) -> pd.DataFrame:
    """Count cumulative pass at each stage. For Aegis block_* stages, the
    'pass' is the negation (1 - block)."""
    rows = []
    cum = pd.Series(True, index=df.index)
    n_total = len(df)
    rows.append({
        "stage": "universe",
        "stage_idx": 0,
        "count": n_total,
        "rate_vs_universe": 1.0,
        "rate_vs_prev_stage": 1.0,
    })
    prev_count = n_total
    for i, stage in enumerate(stages, start=1):
        if stage.startswith("block_"):
            stage_pass = (df[stage] == 0)
            stage_label = f"not_{stage}"
        else:
            stage_pass = (df[stage] == 1)
            stage_label = stage
        cum = cum & stage_pass
        c = int(cum.sum())
        rows.append({
            "stage": stage_label,
            "stage_idx": i,
            "count": c,
            "rate_vs_universe": c / n_total if n_total > 0 else 0.0,
            "rate_vs_prev_stage": c / prev_count if prev_count > 0 else 0.0,
        })
        prev_count = c
    out = pd.DataFrame(rows)
    out["strategy"] = strategy
    return add_meta_cols(out)


def funnel_rolling(df: pd.DataFrame, stages: list[str], strategy: str,
                   window_days: int = 90) -> pd.DataFrame:
    """Per-day rolling pass-count per stage; rolling 90-day conv rate."""
    daily = []
    cum = pd.Series(True, index=df.index)
    daily_uni = df.groupby(df.index.date).size().rename("universe")
    daily.append(daily_uni)
    for i, stage in enumerate(stages, start=1):
        if stage.startswith("block_"):
            stage_pass = (df[stage] == 0)
            stage_label = f"not_{stage}"
        else:
            stage_pass = (df[stage] == 1)
            stage_label = stage
        cum = cum & stage_pass
        s = cum.astype(int).groupby(df.index.date).sum().rename(f"s{i}_{stage_label}")
        daily.append(s)
    daily_df = pd.concat(daily, axis=1).fillna(0)
    daily_df.index = pd.to_datetime(daily_df.index)
    rolled = daily_df.rolling(f"{window_days}D", min_periods=10).sum()

    # Long-format rolling conversion rate
    out_rows = []
    stage_cols = [c for c in rolled.columns if c != "universe"]
    for date, row in rolled.iterrows():
        prev = row["universe"]
        for sc in stage_cols:
            cur = row[sc]
            rate = (cur / prev) if prev > 0 else None
            if pd.isna(cur) or pd.isna(prev):
                continue
            out_rows.append({
                "date": date.date().isoformat(),
                "stage": sc,
                "rolling_pass_count": int(cur),
                "rolling_universe_count": int(prev),
                "rolling_rate": rate,
            })
    out = pd.DataFrame(out_rows)
    out["strategy"] = strategy
    return add_meta_cols(out, window_days=window_days)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for s in STRATEGIES:
        bars = load_bars(STRATEGIES[s]["bar_symbol"])
        evald = EVAL[s](bars)
        stages = STAGES[s]

        static = funnel_static(evald, stages, s)
        out_s = OUT_DIR / f"O3_conversion_funnel_{s}.csv"
        static.to_csv(out_s, index=False)
        print(f"[O3] {s} static: {len(static)} stages → {out_s.name}", flush=True)

        rolling = funnel_rolling(evald, stages, s)
        out_r = OUT_DIR / f"O3_conversion_rolling_{s}.csv"
        rolling.to_csv(out_r, index=False)
        print(f"[O3] {s} rolling: {len(rolling)} (date,stage) rows → {out_r.name}", flush=True)


if __name__ == "__main__":
    main()
