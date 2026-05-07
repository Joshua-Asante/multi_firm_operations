"""H-NYFBO single-config event simulator.

Per parent brief §5 guardrail #9 (literature defaults — no grid search):

  Opening range  = 09:00-09:14 ET 15-min bar (the FIRST bar of NY-open window)
  Failed-breakout signal = price breaks range high or low intrabar, then
                            closes back inside the range within the fade window
  Fade entry     = at the close of the bar that closes back inside range
  SL             = the breakout extreme (range_high if upside fake, range_low if down)
  TP             = range midpoint (first touch)
  Time stop      = 10:30 ET (end of fade window)
  ATR filter     = ATR(14) on M15 percentile rank > 25th (literature default)

Spread costs: per-fill, applied at entry and exit, sourced from
analysis.eurusd_lnyo.pepperstone_spread.

Output per trade:
    et_date           pd.Timestamp (date in ET)
    entry_et          pd.Timestamp (tz-aware ET)
    exit_et           pd.Timestamp (tz-aware ET)
    side              "long" (price closed back in from upside fake -> fade short)
                      or "short" (downside fake -> fade long ... wait, fade fades the breakout)
    direction         +1 (long) / -1 (short)
    entry_px          float (mid)
    exit_px           float (mid)
    range_high, range_low, range_mid
    raw_pips          gross pips (mid-to-mid, signed)
    cost_pips         spread cost (>0)
    net_pips          raw_pips - cost_pips
    exit_reason       "tp" | "sl" | "time"
    et_dow            int 0..4
    regime            "hike_2022" | "hold_2023_24" | "ease_2024_26"

Convention:
  An "upside failed breakout" means price broke above range_high then closed
  back inside the range. The fade entry is SHORT (we expect mean reversion
  back to range_mid). Direction = -1.

  A "downside failed breakout" means price broke below range_low then closed
  back inside. Fade entry is LONG (expect mean reversion up). Direction = +1.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from analysis.eurusd_lnyo import pepperstone_spread

ET = ZoneInfo("America/New_York")

# Literature defaults
RANGE_BAR_HOUR_ET = 9
RANGE_BAR_MIN_ET = 0       # 09:00 ET = first 15-min bar
RANGE_BAR_END_MIN_ET = 15  # 09:15 ET (end of opening range bar)
WINDOW_END_HOUR_ET = 10
WINDOW_END_MIN_ET = 30     # 10:30 ET = time stop / end of fade window
ATR_LEN = 14
ATR_PERCENTILE_GATE = 0.25

# Pip size for EURUSD: 0.0001
PIP = 0.0001


@dataclass
class SimConfig:
    range_bar_hour_et: int = RANGE_BAR_HOUR_ET
    range_bar_min_et: int = RANGE_BAR_MIN_ET
    window_end_hour_et: int = WINDOW_END_HOUR_ET
    window_end_min_et: int = WINDOW_END_MIN_ET
    atr_len: int = ATR_LEN
    atr_pct_gate: float = ATR_PERCENTILE_GATE


@dataclass
class Trade:
    et_date: dt.date
    entry_et: pd.Timestamp
    exit_et: pd.Timestamp
    direction: int   # +1 long fade, -1 short fade
    entry_px: float
    exit_px: float
    range_high: float
    range_low: float
    range_mid: float
    raw_pips: float
    cost_pips: float
    net_pips: float
    exit_reason: str   # 'tp' | 'sl' | 'time'
    et_dow: int
    regime: str


def assign_regime(d: dt.date) -> str:
    """Three-regime stratification per parent brief §5 #2."""
    if d <= dt.date(2022, 12, 30):
        return "hike_2022"
    if d <= dt.date(2024, 6, 30):
        return "hold_2023_24"
    return "ease_2024_26"


def _atr_m15(bars: pd.DataFrame, length: int) -> pd.Series:
    """Wilder ATR on M15 mid-OHLC."""
    h = bars["mid_high"]
    l = bars["mid_low"]
    c = bars["mid_close"]
    prev_c = c.shift(1)
    tr = pd.concat([(h - l), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / length, adjust=False).mean()


def _add_mid_ohlc(bars: pd.DataFrame) -> pd.DataFrame:
    """Compose mid OHLC from bid + ask. Mid = (bid + ask) / 2 column-wise."""
    out = bars.copy()
    for c in ["open", "high", "low", "close"]:
        out[f"mid_{c}"] = (out[f"bid_{c}"] + out[f"ask_{c}"]) / 2
    return out


def simulate_h_nyfbo(
    bars: pd.DataFrame,
    *,
    cfg: SimConfig | None = None,
    spread_cfg: pepperstone_spread.SpreadConfig | None = None,
) -> pd.DataFrame:
    """Run H-NYFBO single-config simulation over the bid+ask M15 panel.

    `bars` must be tz-aware UTC indexed with bid_*/ask_* columns
    (output of dukascopy_loader.load_eurusd_m15_bidask).

    Returns DataFrame of Trade rows.
    """
    cfg = cfg or SimConfig()
    spread_cfg = spread_cfg or pepperstone_spread.SpreadConfig()

    if bars.index.tz is None:
        raise ValueError("bars.index must be tz-aware UTC")
    bars = _add_mid_ohlc(bars)
    bars["atr_m15"] = _atr_m15(bars, cfg.atr_len)

    # Build ET-local view
    et_idx = bars.index.tz_convert(ET)
    bars = bars.assign(
        et_date=et_idx.date,
        et_hour=et_idx.hour,
        et_minute=et_idx.minute,
        et_dow=et_idx.dayofweek,
    )

    # ATR percentile gate — global percentile across panel, simple threshold
    atr_q = bars["atr_m15"].dropna()
    atr_threshold = float(np.quantile(atr_q.values, cfg.atr_pct_gate))

    trades: list[Trade] = []

    # Group by ET date (excluding weekends — no trading days)
    by_date = bars.groupby("et_date", sort=True)
    for et_date, day_bars in by_date:
        if not isinstance(et_date, dt.date):
            continue
        if et_date.weekday() >= 5:
            continue
        dow = et_date.weekday()

        day_bars = day_bars.sort_index()
        # Find the 09:00 ET range bar
        range_mask = (day_bars["et_hour"] == cfg.range_bar_hour_et) & \
                     (day_bars["et_minute"] == cfg.range_bar_min_et)
        if not range_mask.any():
            continue
        range_bar = day_bars[range_mask].iloc[0]

        # ATR gate at the range bar (must be at or above 25th pct percentile)
        if pd.isna(range_bar["atr_m15"]) or range_bar["atr_m15"] < atr_threshold:
            continue

        range_high = float(range_bar["mid_high"])
        range_low = float(range_bar["mid_low"])
        range_mid = (range_high + range_low) / 2

        # Subsequent bars in the fade window: 09:15 ET .. 10:30 ET (exclusive of 10:45)
        fade_mask = (
            ((day_bars["et_hour"] > cfg.range_bar_hour_et) |
             ((day_bars["et_hour"] == cfg.range_bar_hour_et) &
              (day_bars["et_minute"] >= cfg.range_bar_end_min_et if False else day_bars["et_minute"] >= 15)))
            & ((day_bars["et_hour"] < cfg.window_end_hour_et) |
               ((day_bars["et_hour"] == cfg.window_end_hour_et) &
                (day_bars["et_minute"] <= cfg.window_end_min_et)))
        )
        fade_bars = day_bars[fade_mask].sort_index()
        if fade_bars.empty:
            continue

        # Detect failed breakout: track which side broke first; entry on the
        # bar that closes back inside the range after a break.
        broke_high = False
        broke_low = False
        entry_bar = None
        direction = 0  # +1 long fade, -1 short fade
        for ts, b in fade_bars.iterrows():
            mh = float(b["mid_high"])
            ml = float(b["mid_low"])
            mc = float(b["mid_close"])
            # Update break flags by intrabar high/low
            if mh > range_high:
                broke_high = True
            if ml < range_low:
                broke_low = True
            # Closed-back-inside check (bar must close strictly inside range)
            if range_low < mc < range_high:
                if broke_high and not broke_low:
                    direction = -1  # upside fake -> short fade
                    entry_bar = (ts, b)
                    break
                if broke_low and not broke_high:
                    direction = +1  # downside fake -> long fade
                    entry_bar = (ts, b)
                    break
                # Two-sided breakout: ambiguous, skip
                if broke_high and broke_low:
                    break
        if entry_bar is None:
            continue

        entry_ts_utc, entry_b = entry_bar
        entry_et = entry_ts_utc.astimezone(ET)
        entry_px = float(entry_b["mid_close"])
        # SL = the breakout extreme (range_high for short fade, range_low for long fade)
        sl_px = range_high if direction == -1 else range_low
        # TP = range midpoint
        tp_px = range_mid

        # Walk forward bar by bar to find exit
        post_mask = (fade_bars.index > entry_ts_utc)
        post = fade_bars[post_mask].sort_index()

        exit_px: float | None = None
        exit_reason = "time"
        exit_ts_utc = post.index[-1] if len(post) else entry_ts_utc

        for ts, b in post.iterrows():
            mh = float(b["mid_high"])
            ml = float(b["mid_low"])
            # Check SL first (conservative: stop fills before TP if both reached)
            if direction == -1:
                if mh >= sl_px:
                    exit_px = sl_px
                    exit_reason = "sl"
                    exit_ts_utc = ts
                    break
                if ml <= tp_px:
                    exit_px = tp_px
                    exit_reason = "tp"
                    exit_ts_utc = ts
                    break
            else:  # +1 long fade
                if ml <= sl_px:
                    exit_px = sl_px
                    exit_reason = "sl"
                    exit_ts_utc = ts
                    break
                if mh >= tp_px:
                    exit_px = tp_px
                    exit_reason = "tp"
                    exit_ts_utc = ts
                    break

        if exit_px is None:
            # Time stop at last bar in fade window
            if len(post):
                exit_px = float(post.iloc[-1]["mid_close"])
                exit_ts_utc = post.index[-1]
            else:
                exit_px = entry_px
                exit_ts_utc = entry_ts_utc
            exit_reason = "time"

        exit_et = exit_ts_utc.astimezone(ET)

        # Raw pips (signed): direction * (exit - entry) / pip
        raw_pips = direction * (exit_px - entry_px) / PIP
        cost_pips = pepperstone_spread.per_trade_cost_pips(entry_et, exit_et, spread_cfg)
        net_pips = raw_pips - cost_pips

        trades.append(Trade(
            et_date=et_date,
            entry_et=entry_et,
            exit_et=exit_et,
            direction=direction,
            entry_px=entry_px,
            exit_px=exit_px,
            range_high=range_high,
            range_low=range_low,
            range_mid=range_mid,
            raw_pips=raw_pips,
            cost_pips=cost_pips,
            net_pips=net_pips,
            exit_reason=exit_reason,
            et_dow=dow,
            regime=assign_regime(et_date),
        ))

    return pd.DataFrame([t.__dict__ for t in trades])


def daily_pnl_pips(trades: pd.DataFrame) -> pd.Series:
    """Aggregate trades to daily net P&L in pips (ET dates).

    Returns a Series indexed by et_date with column net_pips_sum (zero on
    no-trade days... but only for days that appear in trades; caller should
    reindex onto full bdays if needed).
    """
    if trades.empty:
        return pd.Series(dtype=float, name="net_pips")
    out = trades.groupby("et_date")["net_pips"].sum()
    out.index = pd.to_datetime(out.index)
    out.name = "net_pips"
    return out


# --- Probe -------------------------------------------------------------------

def _probe(target_date: str | None = None):
    """Trace one event-rich day."""
    from analysis.eurusd_lnyo.dukascopy_loader import load_eurusd_m15_bidask
    bars = load_eurusd_m15_bidask()
    print(f"Loaded {len(bars):,} M15 bars")
    if target_date:
        d = pd.Timestamp(target_date).date()
        et_idx = bars.index.tz_convert(ET)
        sub = bars[(et_idx.date == d)]
        if sub.empty:
            print(f"No bars for ET date {d}")
            return
        trades = simulate_h_nyfbo(sub)
    else:
        trades = simulate_h_nyfbo(bars)
    print(f"Trades: {len(trades)}")
    if not trades.empty:
        print(trades.describe())
        print()
        print(trades.head(5))


if __name__ == "__main__":
    import sys
    target = None
    for arg in sys.argv[1:]:
        if arg.startswith("--probe"):
            parts = arg.split("=", 1)
            if len(parts) == 2:
                target = parts[1]
    _probe(target)
