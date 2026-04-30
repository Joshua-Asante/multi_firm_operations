"""Per-strategy bar-level filter and signal evaluators.

Reconstructs the locked Pine logic for Guardian v5.5 / Striker v4.4 / Aegis v4.3
at the bar level. Used by O3 (conversion funnel), O5 (filter forensics), O1
(counterfactual rejected-trade simulation).

TZ semantics (verified by Phase 0 + Pine code reads):
  - Guardian: chart-TZ NY ('hour', 'dayofweek' in Pine bare → chart TZ)
  - Striker:  UTC explicit ('hour(time, "UTC")', 'dayofweek(time, "UTC")')
  - Aegis:    chart-TZ NY (bare 'hour', 'dayofweek', 'dayofmonth')

NB: CLAUDE.md describes Guardian session as "0800-1600 UTC", but Pine bare
'hour' uses chart-TZ. Phase 0 empirically resolves chart-TZ = NY. **Doc/code
skew flagged in README — Notice-bound observation, not actioned in this loop.**
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import compute_atr, PARAMS


def add_local_time(bars: pd.DataFrame, tz: str) -> pd.DataFrame:
    """Add local-TZ columns (hour, minute, dayofweek 0=Mon..6=Sun, dayofmonth)
    matching Pine semantics (Pine dayofweek: Sun=1..Sat=7; we map to that)."""
    out = bars.copy()
    if tz == "UTC":
        local = out.index
    else:
        local = out.index.tz_convert(tz)
    out["lhour"] = local.hour
    out["lminute"] = local.minute
    out["ldom"] = local.day
    # Python: Mon=0..Sun=6. Pine: Sun=1..Sat=7. We use Pine convention here.
    pine_dow = (local.dayofweek + 1) % 7 + 1  # Mon(0)→2, Sun(6)→1, Sat(5)→7
    out["pdow"] = pine_dow  # Pine dayofweek scheme
    # Convenience flags (Pine names)
    out["is_mon"] = (out["pdow"] == 2).astype(int)
    out["is_tue"] = (out["pdow"] == 3).astype(int)
    out["is_wed"] = (out["pdow"] == 4).astype(int)
    out["is_thu"] = (out["pdow"] == 5).astype(int)
    out["is_fri"] = (out["pdow"] == 6).astype(int)
    return out


# ----------------------------------------------------------------------
# Guardian v5.5
# ----------------------------------------------------------------------
def guardian_eval(bars: pd.DataFrame) -> pd.DataFrame:
    """Returns bars with signal, filter-pass, and per-filter block columns.

    Locked: EMA 385/25, NY Extended 08-16 chart-TZ, day Mon/Tue/Thu, blocks
    Mon H08, Tue H08, Mon H09, all H12 (Mon/Tue/Thu via blockH12Day latch).
    """
    df = add_local_time(bars, "America/New_York")
    p = PARAMS["guardian"]
    df["atr"] = compute_atr(bars, p["atr_len"])
    df["ema_slow"] = bars["close"].ewm(span=385, adjust=False).mean()
    df["entry_ema"] = bars["close"].ewm(span=25, adjust=False).mean()

    df["bullTrendOK"] = (bars["close"] > df["ema_slow"]).astype(int)
    df["recoveryLong"] = (
        (bars["close"] > df["entry_ema"]) &
        (bars["close"].shift(1) <= df["entry_ema"].shift(1))
    ).astype(int)
    df["signal_raw"] = (df["bullTrendOK"] & df["recoveryLong"]).astype(int)

    # Day filter: Mon/Tue/Thu only
    df["day_pass"] = (df["is_mon"] | df["is_tue"] | df["is_thu"]).astype(int)

    # Session: 08:00-16:00 chart-TZ (NY Extended)
    df["session_pass"] = ((df["lhour"] >= 8) & (df["lhour"] < 16)).astype(int)

    # Hour blocks
    df["block_TueH08"] = ((df["is_tue"] == 1) & (df["lhour"] == 8)).astype(int)
    df["block_MonH08"] = ((df["is_mon"] == 1) & (df["lhour"] == 8)).astype(int)
    df["block_MonH09"] = ((df["is_mon"] == 1) & (df["lhour"] == 9)).astype(int)
    df["block_MonH12"] = ((df["is_mon"] == 1) & (df["lhour"] == 12)).astype(int)
    df["block_TueH12"] = ((df["is_tue"] == 1) & (df["lhour"] == 12)).astype(int)
    df["block_ThuH12"] = ((df["is_thu"] == 1) & (df["lhour"] == 12)).astype(int)
    df["any_hour_block"] = (
        df["block_TueH08"] | df["block_MonH08"] | df["block_MonH09"] |
        df["block_MonH12"] | df["block_TueH12"] | df["block_ThuH12"]
    ).astype(int)
    df["hour_pass"] = (1 - df["any_hour_block"]).astype(int)

    df["all_pass"] = (
        df["signal_raw"] & df["day_pass"] & df["session_pass"] & df["hour_pass"]
    ).astype(int)
    return df


# ----------------------------------------------------------------------
# Striker v4.4
# ----------------------------------------------------------------------
def striker_eval(bars: pd.DataFrame) -> pd.DataFrame:
    """Locked: rawBreakout > highest(15)[1], ATR(11) expansion 0.28× over MA(85),
    session 13-17 UTC, Tue/Fri only (UTC), warmup >3 bars in session,
    body ratio >=0.25, prev bar bullish."""
    df = add_local_time(bars, "UTC")
    p = PARAMS["striker"]
    df["atr"] = compute_atr(bars, p["atr_len"])
    df["atr_ma"] = df["atr"].rolling(85).mean()
    df["atr_expanding"] = (df["atr"] > df["atr_ma"] * 1.28).astype(int)

    df["highest_15"] = bars["high"].rolling(15).max().shift(1)
    df["raw_breakout"] = (bars["close"] > df["highest_15"]).astype(int)
    df["signal_raw"] = df["raw_breakout"]  # core breakout signal

    # Session 13-17 UTC, Tue or Fri
    df["session_pass"] = ((df["lhour"] >= 13) & (df["lhour"] < 17)).astype(int)
    df["dow_pass"] = ((df["is_tue"] == 1) | (df["is_fri"] == 1)).astype(int)

    # Warmup: >3 bars elapsed in current session window (per-day count of session bars)
    in_session = df["session_pass"].astype(bool)
    # bars-in-session counter: increments while in_session, resets when out
    grp = (~in_session).cumsum()
    df["bars_in_session"] = in_session.groupby(grp).cumsum()
    df["warmup_pass"] = (df["bars_in_session"] > 3).astype(int)

    # Body and prev-bar
    rng = bars["high"] - bars["low"]
    body = (bars["close"] - bars["open"]).abs()
    body_ratio = (body / rng).where(rng > 0, 0)
    df["body_pass"] = (body_ratio >= 0.25).astype(int)
    df["prev_bullish"] = (bars["close"].shift(1) > bars["open"].shift(1)).astype(int)

    df["all_pass"] = (
        df["signal_raw"] & df["atr_expanding"] & df["session_pass"] &
        df["dow_pass"] & df["warmup_pass"] & df["body_pass"] & df["prev_bullish"]
    ).astype(int)
    return df


# ----------------------------------------------------------------------
# Aegis v4.3
# ----------------------------------------------------------------------
def aegis_eval(bars: pd.DataFrame) -> pd.DataFrame:
    """Locked: BB(19, 1.9), close < lower BB, 10:00-13:45 chart-TZ NY,
    Mon/Tue/Wed only, hour != 11 AND next_hour != 11 (so 10:45 blocked),
    Tue H10 block, EOM block (day 29-31), min ATR(19) 0.07."""
    df = add_local_time(bars, "America/New_York")
    p = PARAMS["aegis"]
    df["atr"] = compute_atr(bars, p["atr_len"])

    # BB(19, 1.9)
    bb_basis = bars["close"].rolling(19).mean()
    bb_std = bars["close"].rolling(19).std(ddof=0)
    df["bb_basis"] = bb_basis
    df["bb_lower"] = bb_basis - 1.9 * bb_std
    df["bb_upper"] = bb_basis + 1.9 * bb_std
    df["bb_touch"] = (bars["close"] < df["bb_lower"]).astype(int)
    df["signal_raw"] = df["bb_touch"]

    # Session: 10:00-13:45 NY (minute-level end)
    bar_minutes = df["lhour"] * 60 + df["lminute"]
    df["in_session"] = ((bar_minutes >= 10 * 60) & (bar_minutes < 13 * 60 + 45)).astype(int)

    # Hour filter: hour != 11 AND next_hour (for :45 bars) != 11
    next_hour = np.where(df["lminute"] == 45, df["lhour"] + 1, df["lhour"])
    df["hour_pass"] = ((df["lhour"] != 11) & (next_hour != 11)).astype(int)

    df["day_pass"] = (df["is_mon"] | df["is_tue"] | df["is_wed"]).astype(int)
    df["vol_pass"] = (df["atr"] >= 0.07).astype(int)

    df["block_TueH10"] = ((df["is_tue"] == 1) & (df["lhour"] == 10)).astype(int)
    df["block_EOM"] = (df["ldom"] >= 29).astype(int)

    df["all_pass"] = (
        df["signal_raw"] & df["in_session"] & df["hour_pass"] & df["day_pass"] &
        df["vol_pass"] & (1 - df["block_TueH10"]) & (1 - df["block_EOM"])
    ).astype(int)
    return df


EVAL = {"guardian": guardian_eval, "striker": striker_eval, "aegis": aegis_eval}
