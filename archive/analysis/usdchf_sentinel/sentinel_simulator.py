"""Sentinel USDCHF H4 gate simulator (parent brief §6 deliverable).

Strategy spec (parent brief §6, no overlay, gate-only — NOT v2.0 build):
  - Symbol/TF:   USDCHF / H4
  - Direction:   short-only
  - Entry:       close < Donchian(20) lower of PRIOR 20 bars
                 AND close < EMA(50)
                 AND bar-open hour in [08, 17] UTC
                 AND bar-open weekday in Mon..Fri
                 AND currently flat (single-position)
  - SL / TP:     entry + 3.0 * ATR(14) / entry - 4.0 * ATR(14)
  - No trail, no max-hold, no vol gate, no regime overlay
  - Risk:        0.50% per trade
  - Costs:       1.0 pip RT (Pepperstone-Razor USDCHF H4 conservative estimate)

Indicator conventions match Pine v6 defaults:
  - ATR(14):     Wilder RMA of true-range
  - EMA(50):     ewm(span=50, adjust=False)
  - Donchian:    rolling lowest-low over prior 20 bars (shifted by 1)

Trade execution model:
  - Entry at signal-bar close.
  - Subsequent bars: SL first (conservative) if both could trigger same bar,
    i.e. within a single subsequent bar, SL hit takes priority over TP hit
    when high >= sl AND low <= tp.
  - Hold until SL or TP. No bar-cap; no trail.

Per-trade row schema (returned DataFrame):
  entry_ts, exit_ts, entry_px, exit_px, sl_px, tp_px, atr_at_entry,
  sl_pips, tp_pips, raw_pips, cost_pips, net_pips, R, pct_account,
  exit_reason, dow, atr_quartile

The simulator returns a per-trade DataFrame; PF / DD / report are computed
in run_sentinel_gate.py.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd


PIP = 0.0001
RISK_PCT = 0.005          # 0.50% per parent brief
SL_ATR_MULT = 3.0
TP_ATR_MULT = 4.0
ATR_LEN = 14
EMA_LEN = 50
DONCHIAN_LEN = 20
SESSION_HOUR_LO = 8       # 08:00 UTC inclusive
SESSION_HOUR_HI = 17      # 17:00 UTC inclusive
COST_RT_PIPS = 1.0        # round-trip cost; gate-conservative


@dataclass
class Trade:
    entry_ts: pd.Timestamp
    exit_ts: pd.Timestamp
    entry_px: float
    exit_px: float
    sl_px: float
    tp_px: float
    atr_at_entry: float
    sl_pips: float
    tp_pips: float
    raw_pips: float
    cost_pips: float
    net_pips: float
    R: float                  # raw R-multiple (excl. cost)
    net_R: float              # cost-adjusted R-multiple
    pct_account: float        # cost-adjusted % of account
    exit_reason: str          # 'sl' | 'tp'
    dow: int                  # Mon=0..Sun=6 of entry bar
    atr_quartile: int         # 1..4 (post-hoc diagnostic)


def _wilder_rma(s: pd.Series, n: int) -> pd.Series:
    """Wilder's smoothing (RMA), matches Pine v6 ta.rma(_, n)."""
    return s.ewm(alpha=1.0 / n, adjust=False).mean()


def _atr_wilder(bars: pd.DataFrame, n: int = ATR_LEN) -> pd.Series:
    """ATR with Wilder's RMA — matches Pine v6 ta.atr(n)."""
    h = bars["high"]
    l = bars["low"]
    pc = bars["close"].shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return _wilder_rma(tr, n)


def compute_indicators(bars: pd.DataFrame) -> pd.DataFrame:
    """Attach atr14, ema50, donchian_lower20_prior to the bar frame."""
    out = bars.copy()
    out["atr14"] = _atr_wilder(out, ATR_LEN)
    out["ema50"] = out["close"].ewm(span=EMA_LEN, adjust=False).mean()
    out["donchian_lower20_prior"] = out["low"].rolling(DONCHIAN_LEN).min().shift(1)
    return out


def _atr_quartile_lookup(atr_series: pd.Series) -> dict[pd.Timestamp, int]:
    """Map each timestamp to its panel-wide ATR quartile (1=lowest..4=highest).

    Quartiles computed over the full simulator panel (post-warmup), not per
    sub-window — diagnostic only, never a filter.
    """
    valid = atr_series.dropna()
    if valid.empty:
        return {}
    # qcut into 4 quartile bins; rank 1..4 (lowest to highest)
    q = pd.qcut(valid, 4, labels=[1, 2, 3, 4]).astype(int)
    return q.to_dict()


def _in_session(ts: pd.Timestamp) -> bool:
    return SESSION_HOUR_LO <= ts.hour <= SESSION_HOUR_HI and ts.weekday() <= 4


def signal_short(row) -> bool:
    """Sentinel short entry signal (no overlay)."""
    if pd.isna(row["donchian_lower20_prior"]) or pd.isna(row["ema50"]) or pd.isna(row["atr14"]):
        return False
    return (row["close"] < row["donchian_lower20_prior"]) and (row["close"] < row["ema50"])


def simulate(bars: pd.DataFrame) -> pd.DataFrame:
    """Run the Sentinel single-position bar-walker on USDCHF H4.

    `bars` must be tz-aware UTC indexed with columns open/high/low/close.
    Returns a per-trade DataFrame.
    """
    if bars.index.tz is None:
        raise ValueError("bars.index must be tz-aware UTC")

    panel = compute_indicators(bars)
    quartile_lookup = _atr_quartile_lookup(panel["atr14"])

    trades: list[Trade] = []
    in_position = False
    entry_ts = None
    entry_px = sl_px = tp_px = atr_at_entry = 0.0

    timestamps = panel.index
    closes = panel["close"].values
    highs = panel["high"].values
    lows = panel["low"].values

    for i, ts in enumerate(timestamps):
        if not in_position:
            if not _in_session(ts):
                continue
            row = panel.iloc[i]
            if not signal_short(row):
                continue
            entry_ts = ts
            entry_px = float(row["close"])
            atr_at_entry = float(row["atr14"])
            sl_px = entry_px + SL_ATR_MULT * atr_at_entry
            tp_px = entry_px - TP_ATR_MULT * atr_at_entry
            in_position = True
            continue

        # In position: check exit on this bar
        bar_h = highs[i]
        bar_l = lows[i]
        # SL first (conservative) if both could trigger
        if bar_h >= sl_px:
            exit_px = sl_px
            exit_reason = "sl"
        elif bar_l <= tp_px:
            exit_px = tp_px
            exit_reason = "tp"
        else:
            continue

        sl_pips = (sl_px - entry_px) / PIP        # positive (loss distance)
        tp_pips = (entry_px - tp_px) / PIP        # positive (profit distance)
        raw_pips = (entry_px - exit_px) / PIP     # short: positive when exit < entry
        net_pips = raw_pips - COST_RT_PIPS
        R = raw_pips / sl_pips                    # excl. cost
        net_R = net_pips / sl_pips
        pct_account = net_R * RISK_PCT
        dow = entry_ts.weekday()
        atr_q = quartile_lookup.get(entry_ts, 0)

        trades.append(Trade(
            entry_ts=entry_ts, exit_ts=ts,
            entry_px=entry_px, exit_px=exit_px,
            sl_px=sl_px, tp_px=tp_px,
            atr_at_entry=atr_at_entry,
            sl_pips=sl_pips, tp_pips=tp_pips,
            raw_pips=raw_pips, cost_pips=COST_RT_PIPS,
            net_pips=net_pips, R=R, net_R=net_R,
            pct_account=pct_account,
            exit_reason=exit_reason, dow=dow,
            atr_quartile=atr_q,
        ))
        in_position = False

    return pd.DataFrame([t.__dict__ for t in trades])


def candidate_entry_bars(bars: pd.DataFrame) -> pd.DataFrame:
    """Bars eligible for entry under (session, weekday) mask, post indicator-warmup.

    Used as the permutation-null candidate pool. A timestamp is eligible iff
    indicators are non-NaN at that bar AND it satisfies the session/weekday mask.
    Whether the strategy actually fires there is irrelevant — the pool defines
    the null distribution of "where could an entry have been placed."
    """
    panel = compute_indicators(bars)
    valid = panel.dropna(subset=["donchian_lower20_prior", "ema50", "atr14"])
    mask = valid.index.to_series().apply(_in_session)
    return valid.loc[mask.values]


if __name__ == "__main__":
    from analysis.usdchf_sentinel.bar_loader import load_usdchf_h4
    bars = load_usdchf_h4()
    trades = simulate(bars)
    print(f"Trades: {len(trades)}")
    if not trades.empty:
        print(f"  Wins:   {(trades['exit_reason'] == 'tp').sum()}")
        print(f"  Losses: {(trades['exit_reason'] == 'sl').sum()}")
        print(f"  Sum net_pips: {trades['net_pips'].sum():.1f}")
        print(f"  Sum pct_account: {trades['pct_account'].sum() * 100:.2f}%")
        print(trades[["entry_ts", "exit_ts", "exit_reason", "raw_pips", "net_pips", "net_R", "atr_quartile"]].head(5))
