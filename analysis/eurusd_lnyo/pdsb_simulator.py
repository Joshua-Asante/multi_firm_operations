"""H-PDSB single-config event simulator.

Hypothesis (parent brief §4): on EURUSD M15, fade the first-bar overshoot
following a high-impact 08:30 ET US release within a 30-min fade window.

Literature-default parameters (per parent brief §5 #9):
  - Event days from data/external/us_high_impact_0830et_2022_2026.csv
    (NFP, CPI, PCE, RetailSales, GDP_Advance)
  - "First-bar overshoot" = the 08:30 ET M15 bar (08:30-08:44 ET)
    Direction = sign(close - open) of that bar
  - Fade entry = at the close of the 08:30 ET bar, OPPOSITE the bar direction
  - Fade window = 08:35 -> 09:00 ET (30 min as parent brief specifies; we
    use 08:30 close + next two bars 08:45 + 09:00, ie up to 09:00 ET bar)
  - SL = the bar's extreme on the breakout side (high if bar bullish, low if bearish)
  - TP = the bar's open (mean-revert target — undo the impulse)
  - Time stop = 09:00 ET bar close (end of 30-min fade window)

Costs: per-fill, applied at entry and exit, sourced from
analysis.eurusd_lnyo.pepperstone_spread, with optional spread multiplier.

Output per trade matches nyfbo_simulator.py schema for compat.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from analysis.eurusd_lnyo import pepperstone_spread
from analysis.eurusd_lnyo.event_calendar import event_dates as _event_dates_loader

ET = ZoneInfo("America/New_York")

# Literature defaults
EVENT_BAR_HOUR_ET = 8
EVENT_BAR_MIN_ET = 30        # 08:30 ET = the event bar
WINDOW_END_HOUR_ET = 9
WINDOW_END_MIN_ET = 0        # 09:00 ET = end of 30-min fade window (last bar 08:45)
PIP = 0.0001


@dataclass
class SimConfig:
    event_bar_hour_et: int = EVENT_BAR_HOUR_ET
    event_bar_min_et: int = EVENT_BAR_MIN_ET
    window_end_hour_et: int = WINDOW_END_HOUR_ET
    window_end_min_et: int = WINDOW_END_MIN_ET
    spread_multiplier: float = 1.0   # 1.0 baseline; 1.25 for sensitivity


@dataclass
class Trade:
    et_date: dt.date
    event_type: str
    entry_et: pd.Timestamp
    exit_et: pd.Timestamp
    direction: int    # +1 long fade (bar was bearish) / -1 short fade (bar was bullish)
    entry_px: float
    exit_px: float
    bar_open: float
    bar_high: float
    bar_low: float
    bar_close: float
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


def _add_mid_ohlc(bars: pd.DataFrame) -> pd.DataFrame:
    out = bars.copy()
    for c in ["open", "high", "low", "close"]:
        out[f"mid_{c}"] = (out[f"bid_{c}"] + out[f"ask_{c}"]) / 2
    return out


def simulate_h_pdsb(
    bars: pd.DataFrame,
    *,
    cfg: SimConfig | None = None,
    spread_cfg: pepperstone_spread.SpreadConfig | None = None,
    event_dates: set[dt.date] | None = None,
    event_type_lookup: dict[dt.date, str] | None = None,
) -> pd.DataFrame:
    """Run H-PDSB single-config simulation.

    `bars` must be tz-aware UTC indexed with bid_*/ask_* columns.
    `event_dates` filters to only ET dates with a high-impact 08:30 release.
    `cfg.spread_multiplier` scales the per-fill cost (1.0 default; 1.25 sensitivity).
    """
    cfg = cfg or SimConfig()
    spread_cfg = spread_cfg or pepperstone_spread.SpreadConfig()

    if bars.index.tz is None:
        raise ValueError("bars.index must be tz-aware UTC")
    bars = _add_mid_ohlc(bars)

    et_idx = bars.index.tz_convert(ET)
    bars = bars.assign(
        et_date=et_idx.date,
        et_hour=et_idx.hour,
        et_minute=et_idx.minute,
        et_dow=et_idx.dayofweek,
    )

    if event_dates is None:
        from analysis.eurusd_lnyo.event_calendar import load_calendar
        cal = load_calendar()
        event_dates = set(d for d, _ in cal)
        event_type_lookup = {}
        for d, ev in cal:
            event_type_lookup.setdefault(d, ev)
    elif event_type_lookup is None:
        event_type_lookup = {d: "Event" for d in event_dates}

    trades: list[Trade] = []

    by_date = bars.groupby("et_date", sort=True)
    for et_date, day_bars in by_date:
        if not isinstance(et_date, dt.date):
            continue
        if et_date.weekday() >= 5:
            continue
        if et_date not in event_dates:
            continue
        dow = et_date.weekday()

        day_bars = day_bars.sort_index()
        # Locate 08:30 ET bar
        event_mask = (day_bars["et_hour"] == cfg.event_bar_hour_et) & \
                     (day_bars["et_minute"] == cfg.event_bar_min_et)
        if not event_mask.any():
            continue
        event_bar = day_bars[event_mask].iloc[0]
        event_ts_utc = day_bars[event_mask].index[0]

        bar_open = float(event_bar["mid_open"])
        bar_high = float(event_bar["mid_high"])
        bar_low = float(event_bar["mid_low"])
        bar_close = float(event_bar["mid_close"])

        # Direction-of-bar: sign of (close - open). If 0, skip.
        if bar_close == bar_open:
            continue
        bar_direction = 1 if bar_close > bar_open else -1
        # Fade: enter OPPOSITE direction
        direction = -bar_direction
        entry_px = bar_close
        # SL = breakout extreme on direction-of-bar side
        sl_px = bar_high if bar_direction == 1 else bar_low
        # TP = bar_open (undo the impulse)
        tp_px = bar_open

        entry_et = event_ts_utc.astimezone(ET)

        # Walk forward bars 08:45 ET and 09:00 ET (covers up to end of fade window)
        post_mask = (
            (day_bars.index > event_ts_utc)
            & (
                ((day_bars["et_hour"] == cfg.event_bar_hour_et) & (day_bars["et_minute"] >= 45))
                | ((day_bars["et_hour"] == cfg.window_end_hour_et) & (day_bars["et_minute"] <= cfg.window_end_min_et))
            )
        )
        post = day_bars[post_mask].sort_index()

        exit_px = None
        exit_reason = "time"
        exit_ts_utc = post.index[-1] if len(post) else event_ts_utc

        for ts, b in post.iterrows():
            mh = float(b["mid_high"])
            ml = float(b["mid_low"])
            mc = float(b["mid_close"])
            # SL first (conservative)
            if direction == -1:  # short fade — bar was bullish, SL = high
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
            else:  # long fade — bar was bearish, SL = low
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
            if len(post):
                exit_px = float(post.iloc[-1]["mid_close"])
                exit_ts_utc = post.index[-1]
            else:
                exit_px = entry_px
                exit_ts_utc = event_ts_utc
            exit_reason = "time"

        exit_et = exit_ts_utc.astimezone(ET)
        raw_pips = direction * (exit_px - entry_px) / PIP
        cost_pips = pepperstone_spread.per_trade_cost_pips(entry_et, exit_et, spread_cfg) \
            * cfg.spread_multiplier
        net_pips = raw_pips - cost_pips

        trades.append(Trade(
            et_date=et_date,
            event_type=event_type_lookup.get(et_date, "Event"),
            entry_et=entry_et,
            exit_et=exit_et,
            direction=direction,
            entry_px=entry_px,
            exit_px=exit_px,
            bar_open=bar_open,
            bar_high=bar_high,
            bar_low=bar_low,
            bar_close=bar_close,
            raw_pips=raw_pips,
            cost_pips=cost_pips,
            net_pips=net_pips,
            exit_reason=exit_reason,
            et_dow=dow,
            regime=assign_regime(et_date),
        ))

    return pd.DataFrame([t.__dict__ for t in trades])


def daily_pnl_pips(trades: pd.DataFrame) -> pd.Series:
    if trades.empty:
        return pd.Series(dtype=float, name="net_pips")
    out = trades.groupby("et_date")["net_pips"].sum()
    out.index = pd.to_datetime(out.index)
    out.name = "net_pips"
    return out


if __name__ == "__main__":
    from analysis.eurusd_lnyo.dukascopy_loader import load_eurusd_m15_bidask
    bars = load_eurusd_m15_bidask()
    print(f"Loaded {len(bars):,} M15 bars")
    trades = simulate_h_pdsb(bars)
    print(f"Trades: {len(trades)}")
    if not trades.empty:
        print(trades[["et_date", "event_type", "direction", "raw_pips", "cost_pips", "net_pips", "exit_reason", "regime"]].head(10))
        print()
        print("Per-regime mean net_pips:")
        print(trades.groupby("regime")["net_pips"].agg(["count", "mean", "std"]))
