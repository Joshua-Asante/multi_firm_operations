"""Phase 3 — strategy framework testing for AUDNZD M15.

Tests two frameworks (selected by Phase 2 structural fingerprint):
  1. Aegis-style BB+ATR mean reversion  (primary)
  2. Range-fade with ATR-expansion regime gate  (secondary)

Discipline (brief §3.2):
  - Train: 2022-01-01 -> 2024-12-31
  - OOS:   2025-01-01 -> 2026-04-26
  - Native parameter sweep only; no hand-tuning beyond it
  - Best train PF parameters frozen, OOS computed ONCE per framework
  - No reverse-engineering of OOS-good parameters back into train

Pass criteria (all required, brief §3.3):
  - Train PF >= 2.0
  - OOS   PF >= 1.8
  - OOS   mu/sigma >= 1.0
  - OOS   max DD <= 1.5x train max DD
  - >= 50 OOS trades
  - OOS Sharpe >= 0.7 * train Sharpe

Phase-1 caveats inherited:
  - Flat 2-pip per-trade slippage haircut (practice-feed spread optimism)
  - Hour 17 NY rollover is hard-excluded (broker artefact)
  - RBA/RBNZ decision days are hard-excluded (binary-event vol expansion)

Position sizing: constant 1R per trade so PF / mu-sigma metrics are clean.
1R = ATR(period) at entry * stop_multiplier (in price). PnL is recorded in R.
"""
from __future__ import annotations

import json
import pathlib
import sys
from dataclasses import dataclass, asdict
from itertools import product
from datetime import datetime, date

import numpy as np
import pandas as pd

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CLEAN_CSV = REPO_ROOT / "data" / "audnzd_oanda_m15_2022-01-01_to_2026-04-26_clean.csv"
EXPECTED_SHA = "6ff6cc3ce9f3f7ac825b2bae8e1d0cd82295564ca909ba6698f523606fba2d92"
FINDINGS_DIR = REPO_ROOT / "docs" / "methodology" / "findings"
RESULTS_JSON = FINDINGS_DIR / "2026-04-26_audnzd_phase3_results.json"

TRAIN_START = pd.Timestamp("2022-01-01", tz="UTC")
TRAIN_END   = pd.Timestamp("2025-01-01", tz="UTC")  # exclusive
OOS_START   = pd.Timestamp("2025-01-01", tz="UTC")
OOS_END     = pd.Timestamp("2026-04-27", tz="UTC")  # exclusive (covers through 2026-04-26)

SLIPPAGE_PIPS = 2.0
PIP = 0.0001
SLIPPAGE_PRICE = SLIPPAGE_PIPS * PIP


def set_slippage(pips: float) -> None:
    """Diagnostic helper: rerun with a different slippage assumption.

    Verdict-relevant run uses SLIPPAGE_PIPS = 2.0 per Phase 1 caveat.
    A no-slippage pass is informative for characterizing whether ANY
    underlying edge exists (i.e., distinguishing 'no edge' from
    'edge eaten by haircut').
    """
    global SLIPPAGE_PIPS, SLIPPAGE_PRICE
    SLIPPAGE_PIPS = pips
    SLIPPAGE_PRICE = pips * PIP

# Decision-day filter (from Phase 2)
RBA_DATES = [
    "2022-02-01","2022-03-01","2022-04-05","2022-05-03","2022-06-07","2022-07-05",
    "2022-08-02","2022-09-06","2022-10-04","2022-11-01","2022-12-06",
    "2023-02-07","2023-03-07","2023-04-04","2023-05-02","2023-06-06","2023-07-04",
    "2023-08-01","2023-09-05","2023-10-03","2023-11-07","2023-12-05",
    "2024-02-06","2024-03-19","2024-05-07","2024-06-18","2024-08-06","2024-09-24",
    "2024-11-05","2024-12-10",
    "2025-02-18","2025-04-01","2025-05-20","2025-07-08","2025-08-12","2025-09-30",
    "2025-11-04","2025-12-09",
    "2026-02-17","2026-04-01",
]
RBNZ_DATES = [
    "2022-02-23","2022-04-13","2022-05-25","2022-07-13","2022-08-17","2022-10-05","2022-11-23",
    "2023-02-22","2023-04-05","2023-05-24","2023-07-12","2023-08-16","2023-10-04","2023-11-29",
    "2024-02-28","2024-04-10","2024-05-22","2024-07-10","2024-08-14","2024-10-09","2024-11-27",
    "2025-02-19","2025-04-09","2025-05-28","2025-07-09","2025-08-20","2025-10-08","2025-11-26",
    "2026-02-25","2026-04-08",
]
DECISION_DATES = set(pd.to_datetime(RBA_DATES + RBNZ_DATES).date)
ROLLOVER_HOUR_NY = 17

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def verify_hash() -> None:
    import hashlib
    h = hashlib.sha256()
    with CLEAN_CSV.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    got = h.hexdigest()
    if got != EXPECTED_SHA:
        raise SystemExit(f"clean CSV hash mismatch: got {got}, expected {EXPECTED_SHA}")


def load_data() -> pd.DataFrame:
    df = pd.read_csv(CLEAN_CSV)
    df["dt_utc"] = pd.to_datetime(df["datetime_utc"].str.replace("Z", "+00:00", regex=False), utc=True)
    df = df.sort_values("dt_utc").reset_index(drop=True)
    df["open"]  = (df["open_bid"]  + df["open_ask"])  / 2.0
    df["high"]  = (df["high_bid"]  + df["high_ask"])  / 2.0
    df["low"]   = (df["low_bid"]   + df["low_ask"])   / 2.0
    df["close"] = (df["close_bid"] + df["close_ask"]) / 2.0
    df["dt_ny"] = df["dt_utc"].dt.tz_convert("America/New_York")
    df["hour_ny"] = df["dt_ny"].dt.hour
    df["date_utc"] = df["dt_utc"].dt.date
    df["is_decision"] = df["date_utc"].isin(DECISION_DATES)
    df["is_rollover"] = df["hour_ny"] == ROLLOVER_HOUR_NY
    return df


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------

def rolling_mean(arr: np.ndarray, n: int) -> np.ndarray:
    s = pd.Series(arr)
    return s.rolling(n, min_periods=n).mean().values


def rolling_std(arr: np.ndarray, n: int) -> np.ndarray:
    s = pd.Series(arr)
    return s.rolling(n, min_periods=n).std(ddof=0).values


def true_range(high: np.ndarray, low: np.ndarray, close_prev: np.ndarray) -> np.ndarray:
    return np.maximum.reduce([high - low, np.abs(high - close_prev), np.abs(low - close_prev)])


def add_indicators(df: pd.DataFrame, bb_period: int, bb_std: float,
                   atr_period: int, regime_atr_period: int = 96) -> pd.DataFrame:
    out = df.copy()
    close = out["close"].values
    high = out["high"].values
    low = out["low"].values
    cp = pd.Series(close).shift(1).values
    out["tr"] = true_range(high, low, np.where(np.isnan(cp), close, cp))
    out["atr"] = rolling_mean(out["tr"].values, atr_period)
    out["bb_mid"] = rolling_mean(close, bb_period)
    out["bb_sd"]  = rolling_std(close, bb_period)
    out["bb_up"]  = out["bb_mid"] + bb_std * out["bb_sd"]
    out["bb_lo"]  = out["bb_mid"] - bb_std * out["bb_sd"]
    # Regime ATR for range-fade gate (longer window)
    out["regime_atr"] = rolling_mean(out["tr"].values, regime_atr_period)
    out["regime_atr_med"] = pd.Series(out["regime_atr"]).rolling(
        regime_atr_period * 4, min_periods=regime_atr_period * 2).median().values
    return out


# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    entry_idx: int
    entry_time: pd.Timestamp
    side: int  # +1 long, -1 short
    entry_price: float
    stop_price: float
    target_price: float
    risk_price: float  # 1R in price units
    exit_idx: int = -1
    exit_time: pd.Timestamp = None
    exit_price: float = 0.0
    exit_reason: str = ""
    pnl_r: float = 0.0


def simulate(df: pd.DataFrame, params: dict, framework: str) -> list[Trade]:
    """Bar-by-bar simulation. Entry signal at bar close i, fill at bar i+1 open.
    Stop/target are checked intra-bar from i+1 onward.
    Hold time bounded by params['max_hold_bars'].
    Slippage of SLIPPAGE_PRICE is deducted from PnL at exit (regardless of exit type).
    """
    trades: list[Trade] = []
    in_pos = False
    pos: Trade | None = None

    bb_lo = df["bb_lo"].values
    bb_up = df["bb_up"].values
    bb_mid = df["bb_mid"].values
    atr = df["atr"].values
    regime_atr = df["regime_atr"].values
    regime_atr_med = df["regime_atr_med"].values
    close = df["close"].values
    open_ = df["open"].values
    high = df["high"].values
    low = df["low"].values
    is_decision = df["is_decision"].values
    is_rollover = df["is_rollover"].values
    hour_ny = df["hour_ny"].values
    dt_utc = df["dt_utc"].values
    dow_utc = df["dt_utc"].dt.dayofweek.values

    stop_atr_mult = params["stop_atr_mult"]
    target_r_mult = params["target_r_mult"]
    max_hold = params["max_hold_bars"]
    entry_hours = set(params["entry_hours_ny"])
    require_regime_calm = params.get("require_regime_calm", False)
    require_close_inside = params.get("require_close_inside", False)

    n = len(df)
    for i in range(n - 1):
        # Hard exclusions
        if is_decision[i]:
            in_pos_should_exit_event = in_pos and is_decision[i] and not is_decision[i-1] if i > 0 else False
            # If position open and we're entering a decision day, force-close at this bar's open
            if in_pos and pos is not None:
                fill = open_[i]
                pos.exit_idx = i
                pos.exit_time = dt_utc[i]
                pos.exit_price = fill
                pos.exit_reason = "decision_day_force_exit"
                pos.pnl_r = (fill - pos.entry_price) * pos.side / pos.risk_price - SLIPPAGE_PRICE / pos.risk_price
                trades.append(pos)
                pos = None
                in_pos = False

        # In-position handling: stop/target/time/rollover
        if in_pos and pos is not None:
            # Stop / TP intra-bar (bar i is the next bar after entry/last bar)
            stop_hit = False
            tp_hit = False
            exit_price = None
            exit_reason = ""

            if pos.side == +1:
                if low[i] <= pos.stop_price:
                    stop_hit = True
                    exit_price = pos.stop_price
                    exit_reason = "stop"
                elif high[i] >= pos.target_price:
                    tp_hit = True
                    exit_price = pos.target_price
                    exit_reason = "target"
            else:  # short
                if high[i] >= pos.stop_price:
                    stop_hit = True
                    exit_price = pos.stop_price
                    exit_reason = "stop"
                elif low[i] <= pos.target_price:
                    tp_hit = True
                    exit_price = pos.target_price
                    exit_reason = "target"

            # Time-based exit
            held = i - pos.entry_idx
            if not (stop_hit or tp_hit) and held >= max_hold:
                exit_price = close[i]
                exit_reason = "time"

            # Rollover hour force-exit (avoid sitting through rollover spread)
            if not (stop_hit or tp_hit or exit_reason):
                if is_rollover[i]:
                    exit_price = close[i]
                    exit_reason = "rollover_force_exit"

            if exit_price is not None:
                pos.exit_idx = i
                pos.exit_time = dt_utc[i]
                pos.exit_price = float(exit_price)
                pos.exit_reason = exit_reason
                pos.pnl_r = (exit_price - pos.entry_price) * pos.side / pos.risk_price - (SLIPPAGE_PRICE / pos.risk_price)
                trades.append(pos)
                pos = None
                in_pos = False

        if in_pos:
            continue

        # Entry signal at bar i (close), fill at bar i+1 open
        if i + 1 >= n:
            break

        # Skip entries on decision days, rollover hour, or if hour not in allowed set
        if is_decision[i] or is_rollover[i]:
            continue
        if hour_ny[i] not in entry_hours:
            continue
        if dow_utc[i] == 4 and hour_ny[i] >= 16:  # avoid Friday-late entries that don't have time to exit
            continue
        # Skip Sunday partial-session bars (DOW=6 in UTC = Sunday)
        if dow_utc[i] == 6:
            continue

        # Need indicators warm
        if np.isnan(bb_lo[i]) or np.isnan(atr[i]) or atr[i] <= 0:
            continue

        # Optional regime gate (range-fade): only enter when current ATR <= regime median
        if require_regime_calm:
            if np.isnan(regime_atr[i]) or np.isnan(regime_atr_med[i]):
                continue
            if regime_atr[i] > regime_atr_med[i]:
                continue

        # Aegis-style entry: previous close beyond band, current close back inside band
        # (mean-revert pattern). Or simpler: current close beyond band -> fade.
        signal = 0
        if require_close_inside:
            if i >= 1:
                prev_below = close[i-1] < bb_lo[i-1]
                prev_above = close[i-1] > bb_up[i-1]
                cur_inside_lo = close[i] >= bb_lo[i]
                cur_inside_up = close[i] <= bb_up[i]
                if prev_below and cur_inside_lo:
                    signal = +1  # long fade
                elif prev_above and cur_inside_up:
                    signal = -1  # short fade
        else:
            if close[i] < bb_lo[i]:
                signal = +1
            elif close[i] > bb_up[i]:
                signal = -1

        if signal == 0:
            continue

        # Fill at i+1 open with one-side spread cost (already in mid -> use mid)
        entry_price = float(open_[i+1])
        risk_price = stop_atr_mult * float(atr[i])
        if risk_price <= 0:
            continue
        stop_price = entry_price - signal * risk_price
        # Target: bb_mid OR target_r_mult * R from entry, whichever is closer for mean-reversion
        target_meanrev = float(bb_mid[i])
        target_rmult = entry_price + signal * target_r_mult * risk_price
        # Use whichever is in the favorable direction
        if signal == +1:
            target_price = max(target_meanrev, target_rmult)  # both above entry; pick higher
            # Actually for a long mean-revert we want the closer (more reachable) target
            target_price = min(target_meanrev, target_rmult) if target_meanrev > entry_price else target_rmult
        else:
            target_price = max(target_meanrev, target_rmult) if target_meanrev < entry_price else target_rmult

        # Sanity: target must be on correct side of entry
        if signal == +1 and target_price <= entry_price:
            target_price = entry_price + signal * target_r_mult * risk_price
        if signal == -1 and target_price >= entry_price:
            target_price = entry_price + signal * target_r_mult * risk_price

        pos = Trade(
            entry_idx=i+1,
            entry_time=dt_utc[i+1],
            side=signal,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            risk_price=risk_price,
        )
        in_pos = True

    # Close any open position at last bar
    if in_pos and pos is not None:
        last = len(df) - 1
        pos.exit_idx = last
        pos.exit_time = dt_utc[last]
        pos.exit_price = float(close[last])
        pos.exit_reason = "end_of_data"
        pos.pnl_r = (close[last] - pos.entry_price) * pos.side / pos.risk_price - SLIPPAGE_PRICE / pos.risk_price
        trades.append(pos)
    return trades


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(trades: list[Trade]) -> dict:
    if not trades:
        return {"n_trades": 0, "pf": None, "mu_sigma": None, "sharpe": None,
                "max_dd_r": None, "win_rate": None, "mean_r": None, "std_r": None,
                "total_r": 0.0}
    pnls = np.array([t.pnl_r for t in trades])
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    pf = (wins.sum() / -losses.sum()) if len(losses) > 0 and losses.sum() != 0 else None
    mu = pnls.mean()
    sd = pnls.std(ddof=1) if len(pnls) > 1 else None
    mu_sigma = (mu / sd) if sd and sd > 0 else None
    # Per-trade Sharpe (annualized via sqrt of trades-per-year)
    # Approximate: 252 trading days * trades_per_day rate. Use sqrt(n) for now.
    sharpe = (mu / sd) * np.sqrt(252) if sd and sd > 0 else None
    # Equity curve & max DD in R
    eq = np.cumsum(pnls)
    peaks = np.maximum.accumulate(np.concatenate([[0], eq]))
    dd = peaks[1:] - eq
    max_dd = float(dd.max()) if len(dd) > 0 else 0.0
    return {
        "n_trades": int(len(trades)),
        "pf": float(pf) if pf is not None else None,
        "mu_sigma": float(mu_sigma) if mu_sigma is not None else None,
        "sharpe": float(sharpe) if sharpe is not None else None,
        "max_dd_r": max_dd,
        "win_rate": float((pnls > 0).mean()),
        "mean_r": float(mu),
        "std_r": float(sd) if sd else None,
        "total_r": float(eq[-1]),
    }


# ---------------------------------------------------------------------------
# Frameworks: parameter sweeps
# ---------------------------------------------------------------------------

def sweep_aegis(df_train: pd.DataFrame) -> tuple[dict, dict, list[dict]]:
    """Return (best_params, best_metrics, all_results).

    Tests both standard BB+ATR entry variants:
      - 'touch'        : enter when close exceeds the band (immediate fade)
      - 'cross_inside' : enter when prev close was beyond band, current is back inside
    Both are 'native' to the framework family; the brief's 'no hand-tuning'
    discipline allows testing standard variants but not adding new conditions.
    """
    grid = {
        "bb_period":    [20, 30, 50],
        "bb_std":       [2.0, 2.5],
        "atr_period":   [14, 20],
        "stop_atr_mult":[1.5, 2.0],
        "target_r_mult":[1.0, 1.5, 2.0],
        "max_hold_bars":[16, 32],   # 4h, 8h
        "entry_variant":["touch", "cross_inside"],
    }
    entry_hours = list(range(18, 22))  # 18,19,20,21 NY (Asian peak)
    keys = list(grid.keys())
    combos = list(product(*[grid[k] for k in keys]))
    print(f"Aegis sweep: {len(combos)} combos")
    all_results = []
    best = None
    for combo in combos:
        p = dict(zip(keys, combo))
        p["entry_hours_ny"] = entry_hours
        p["require_close_inside"] = (p["entry_variant"] == "cross_inside")
        p["require_regime_calm"] = False
        df_ind = add_indicators(df_train, p["bb_period"], p["bb_std"], p["atr_period"])
        trades = simulate(df_ind, p, "aegis")
        m = compute_metrics(trades)
        m["params"] = p
        all_results.append(m)
        if m["n_trades"] >= 30 and m["pf"] is not None:
            if best is None or (m["pf"] > best["pf"]):
                best = m
    return (best["params"] if best else None, best, all_results)


def sweep_rangefade(df_train: pd.DataFrame) -> tuple[dict, dict, list[dict]]:
    grid = {
        "bb_period":    [20, 50],
        "bb_std":       [2.0, 2.5],
        "atr_period":   [14, 20],
        "stop_atr_mult":[1.5, 2.0],
        "target_r_mult":[1.0, 1.5],
        "max_hold_bars":[16, 32],
        "entry_variant":["touch", "cross_inside"],
    }
    entry_hours = list(range(18, 22))
    keys = list(grid.keys())
    combos = list(product(*[grid[k] for k in keys]))
    print(f"Range-fade sweep: {len(combos)} combos")
    all_results = []
    best = None
    for combo in combos:
        p = dict(zip(keys, combo))
        p["entry_hours_ny"] = entry_hours
        p["require_close_inside"] = (p["entry_variant"] == "cross_inside")
        p["require_regime_calm"] = True
        df_ind = add_indicators(df_train, p["bb_period"], p["bb_std"], p["atr_period"])
        trades = simulate(df_ind, p, "rangefade")
        m = compute_metrics(trades)
        m["params"] = p
        all_results.append(m)
        if m["n_trades"] >= 30 and m["pf"] is not None:
            if best is None or (m["pf"] > best["pf"]):
                best = m
    return (best["params"] if best else None, best, all_results)


# ---------------------------------------------------------------------------
# OOS evaluation
# ---------------------------------------------------------------------------

def evaluate_params(df_oos: pd.DataFrame, params: dict, framework: str) -> dict:
    df_ind = add_indicators(df_oos, params["bb_period"], params["bb_std"], params["atr_period"])
    trades = simulate(df_ind, params, framework)
    m = compute_metrics(trades)
    m["params"] = params
    m["trades"] = [
        {
            "entry_time": str(t.entry_time),
            "side": t.side,
            "exit_reason": t.exit_reason,
            "pnl_r": t.pnl_r,
        }
        for t in trades
    ]
    return m


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------

def verdict(train_m: dict, oos_m: dict) -> dict:
    if train_m is None or oos_m is None:
        return {"pass": False, "reasons": ["null metrics"]}
    fails = []
    if (train_m.get("pf") or 0) < 2.0:
        fails.append(f"train PF {train_m.get('pf'):.3f} < 2.0")
    if (oos_m.get("pf") or 0) < 1.8:
        fails.append(f"OOS PF {oos_m.get('pf')} < 1.8" if oos_m.get('pf') else "OOS PF undefined")
    if (oos_m.get("mu_sigma") or 0) < 1.0:
        fails.append(f"OOS mu/sigma {oos_m.get('mu_sigma')} < 1.0")
    if (oos_m.get("n_trades") or 0) < 50:
        fails.append(f"OOS n_trades {oos_m.get('n_trades')} < 50")
    if train_m.get("max_dd_r") and oos_m.get("max_dd_r") and oos_m["max_dd_r"] > 1.5 * train_m["max_dd_r"]:
        fails.append(
            f"OOS max DD {oos_m['max_dd_r']:.2f}R > 1.5x train DD {train_m['max_dd_r']:.2f}R"
        )
    if train_m.get("sharpe") and oos_m.get("sharpe"):
        if oos_m["sharpe"] < 0.7 * train_m["sharpe"]:
            fails.append(
                f"OOS Sharpe {oos_m['sharpe']:.2f} < 0.7 * train Sharpe {train_m['sharpe']:.2f}"
            )
    return {"pass": len(fails) == 0, "reasons": fails}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    FINDINGS_DIR.mkdir(parents=True, exist_ok=True)
    verify_hash()
    df = load_data()
    print(f"loaded {len(df):,} rows, {df['dt_utc'].min()} -> {df['dt_utc'].max()}")

    df_train = df[(df["dt_utc"] >= TRAIN_START) & (df["dt_utc"] < TRAIN_END)].reset_index(drop=True)
    df_oos   = df[(df["dt_utc"] >= OOS_START)   & (df["dt_utc"] < OOS_END)].reset_index(drop=True)
    print(f"train: {len(df_train):,} bars  ({df_train['dt_utc'].min()} -> {df_train['dt_utc'].max()})")
    print(f"oos:   {len(df_oos):,} bars   ({df_oos['dt_utc'].min()} -> {df_oos['dt_utc'].max()})")

    results: dict = {
        "data_hash": EXPECTED_SHA,
        "train_window": [str(TRAIN_START), str(TRAIN_END)],
        "oos_window":   [str(OOS_START), str(OOS_END)],
        "slippage_pips_verdict": 2.0,
        "filters": {
            "rollover_hour_ny_excluded": ROLLOVER_HOUR_NY,
            "decision_dates_excluded_count": len(DECISION_DATES),
            "sunday_partial_session_excluded": True,
        },
    }

    # Verdict-relevant run with 2-pip slippage
    set_slippage(2.0)
    print(f"\n### MAIN RUN (slippage = 2.0 pips, verdict-relevant) ###")

    # ---- Aegis-style ----
    print("\n=== Aegis-style BB+ATR mean reversion ===")
    aegis_best_params, aegis_train_m, aegis_all = sweep_aegis(df_train)
    if aegis_best_params is None:
        print("  no admissible parameters in train sweep (n_trades < 30 everywhere)")
        results["aegis"] = {"verdict": {"pass": False, "reasons": ["no admissible train params"]}}
    else:
        print(f"  best train PF: {aegis_train_m['pf']:.3f}  n_trades={aegis_train_m['n_trades']}  params={aegis_best_params}")
        aegis_oos_m = evaluate_params(df_oos, aegis_best_params, "aegis")
        print(f"  OOS    PF: {aegis_oos_m['pf']}  n_trades={aegis_oos_m['n_trades']}  mu/sigma={aegis_oos_m['mu_sigma']}")
        v = verdict(aegis_train_m, aegis_oos_m)
        print(f"  verdict: {'PASS' if v['pass'] else 'FAIL'} {v['reasons']}")
        results["aegis"] = {
            "best_params": aegis_best_params,
            "train_metrics": {k: v for k, v in aegis_train_m.items() if k != "trades"},
            "oos_metrics":   {k: v for k, v in aegis_oos_m.items() if k != "trades"},
            "verdict": v,
            "n_combos_evaluated": len(aegis_all),
            "n_admissible_train": sum(1 for r in aegis_all if r["n_trades"] >= 30),
        }

    # ---- Range-fade ----
    print("\n=== Range-fade with regime gate ===")
    rf_best_params, rf_train_m, rf_all = sweep_rangefade(df_train)
    if rf_best_params is None:
        print("  no admissible parameters in train sweep")
        results["rangefade"] = {"verdict": {"pass": False, "reasons": ["no admissible train params"]}}
    else:
        print(f"  best train PF: {rf_train_m['pf']:.3f}  n_trades={rf_train_m['n_trades']}  params={rf_best_params}")
        rf_oos_m = evaluate_params(df_oos, rf_best_params, "rangefade")
        print(f"  OOS    PF: {rf_oos_m['pf']}  n_trades={rf_oos_m['n_trades']}  mu/sigma={rf_oos_m['mu_sigma']}")
        v = verdict(rf_train_m, rf_oos_m)
        print(f"  verdict: {'PASS' if v['pass'] else 'FAIL'} {v['reasons']}")
        results["rangefade"] = {
            "best_params": rf_best_params,
            "train_metrics": {k: v for k, v in rf_train_m.items() if k != "trades"},
            "oos_metrics":   {k: v for k, v in rf_oos_m.items() if k != "trades"},
            "verdict": v,
            "n_combos_evaluated": len(rf_all),
            "n_admissible_train": sum(1 for r in rf_all if r["n_trades"] >= 30),
        }

    # Diagnostic no-slippage pass — characterizes whether any underlying
    # edge exists (NOT verdict-relevant; the verdict uses the 2-pip pass).
    set_slippage(0.0)
    print(f"\n### DIAGNOSTIC RUN (slippage = 0.0 pips, NOT verdict-relevant) ###")
    diag = {}
    for fw_name, sweep_fn in [("aegis", sweep_aegis), ("rangefade", sweep_rangefade)]:
        bp, btm, _ = sweep_fn(df_train)
        if bp is None:
            diag[fw_name] = {"verdict": "no admissible params"}
            continue
        oos_m = evaluate_params(df_oos, bp, fw_name)
        diag[fw_name] = {
            "best_params": bp,
            "train_pf": btm.get("pf"),
            "train_n": btm.get("n_trades"),
            "train_mean_r": btm.get("mean_r"),
            "oos_pf": oos_m.get("pf"),
            "oos_n": oos_m.get("n_trades"),
            "oos_mean_r": oos_m.get("mean_r"),
        }
        print(f"  {fw_name} no-slip: train PF={btm.get('pf'):.3f} OOS PF={oos_m.get('pf')}")
    results["diagnostic_no_slippage"] = diag

    RESULTS_JSON.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nresults written: {RESULTS_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
