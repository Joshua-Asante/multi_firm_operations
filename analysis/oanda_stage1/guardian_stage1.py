"""Guardian Gold v5.5 — OANDA Stage 1 (INQHIORI Inquire phase).

Hypothesis-generation pass on missed-alpha for the Guardian EMA-cross
trend-following strategy. Two disjoint populations:

  (a) Blocked-setup alpha — bars where the entry signal is hot but a current
      filter rejects. Tested filters: per-day H08 / H09 / H12 hour-blocks,
      blockH12Day latch (signal-day gate), Wed/Fri day exclusion.

  (b) Post-exit alpha — 50-bar continuation MFE/MAE in long-direction after
      each OANDA-replayed exit, conditional on exit reason. Guardian's TP =
      29×ATR is unlikely to hit on most trades (the prime hypothesis surface
      is therefore max-hold and trail-equivalent exits).

Run:  python -m analysis.oanda_stage1.guardian_stage1
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.oanda_stage1 import pine_indicators as ind
from analysis.oanda_stage1.bar_loader import load_oanda_bars
from analysis.oanda_stage1.permutation import (
    label_permutation_test,
    window_permutation_test,
)
from analysis.oanda_stage1.post_exit_excursion import (
    post_exit_excursion,
    random_window_excursion,
)
from analysis.oanda_stage1.tv_export_loader import load_tv_export


# ---------------------------------------------------------------- Guardian config
TRADE_CSV = "data/tv_exports/oanda/Guardian_Gold_v5.5_OANDA_XAUUSD_2026-04-25_9ae1f.csv"
SYMBOL = "XAUUSD"
STRATEGY_VER = "v5.5"
LOCK_DATE = "2026-04-23"

EMA_SLOW = 385
ENTRY_EMA = 25
ATR_PERIOD = 14
ATR_SL_MULT = 1.55
GRACE_STOP_MULT = 2.0
MIN_BARS_BEFORE_STOP = 1
TP_ATR = 29.0
MAX_HOLD = 850
MAX_DAILY_TRADES = 2
RISK_PCT = 0.34

# NY Extended session: 08:00-16:00 chart-TZ; chart-TZ is America/New_York for
# Guardian (same as Aegis, validated by CSV→bar timestamp alignment).
SESSION_START_H = 8
SESSION_END_H = 16

COMMISSION_USD_PER_ORDER = 0.0
SLIPPAGE_TICKS = 3

N_PERM = 1000
N_MIN_GATE = 100
COST_FLOOR_R = 0.05
P_GATE = 0.05

OUT_DIR = Path("docs/methodology/findings")


# --------------------------------------------------------------- core compute
def compute_guardian_signals(bars: pd.DataFrame, chart_tz: str = "America/New_York") -> pd.DataFrame:
    """Per-bar evaluation of every Guardian predicate."""
    out = pd.DataFrame(index=bars.index)
    chart_ts = bars.index.tz_localize("UTC").tz_convert(chart_tz).tz_localize(None)
    out["chart_h"] = chart_ts.hour
    out["chart_m"] = chart_ts.minute
    out["chart_dow"] = chart_ts.dayofweek  # Mon=0

    ema_slow = ind.ema(bars["close"], EMA_SLOW)
    entry_ema = ind.ema(bars["close"], ENTRY_EMA)
    atr_ = ind.atr(bars["high"], bars["low"], bars["close"], ATR_PERIOD)

    out["ema_slow"] = ema_slow
    out["entry_ema"] = entry_ema
    out["atr"] = atr_

    bull_trend = bars["close"] > ema_slow
    recovery_long = (bars["close"] > entry_ema) & (bars["close"].shift(1) <= entry_ema.shift(1))

    out["entry_signal"] = bull_trend & recovery_long

    # Session: 08:00-16:00 chart-TZ. Pine's `time(...,"0800-1600:23456")` returns
    # not-na for bars within session AND on Mon-Fri. We're checking by hour because
    # day_ok handles weekday separately.
    out["in_session"] = (out["chart_h"] >= SESSION_START_H) & (out["chart_h"] < SESSION_END_H)

    # Day filter: Mon=0 / Tue=1 / Thu=3 only (Wed=2 / Fri=4 excluded).
    out["day_ok"] = out["chart_dow"].isin([0, 1, 3])

    # Hour-block flags. These are evaluated at signal-bar time (chart TZ).
    out["block_tue_h08"] = (out["chart_dow"] == 1) & (out["chart_h"] == 8)
    out["block_mon_h08"] = (out["chart_dow"] == 0) & (out["chart_h"] == 8)
    out["block_thu_h08"] = (out["chart_dow"] == 3) & (out["chart_h"] == 8)   # default OFF in v5.5
    out["block_mon_h09"] = (out["chart_dow"] == 0) & (out["chart_h"] == 9)
    out["block_mon_h12"] = (out["chart_dow"] == 0) & (out["chart_h"] == 12)
    out["block_tue_h12"] = (out["chart_dow"] == 1) & (out["chart_h"] == 12)
    out["block_thu_h12"] = (out["chart_dow"] == 3) & (out["chart_h"] == 12)

    out["any_h12_block"] = out["block_mon_h12"] | out["block_tue_h12"] | out["block_thu_h12"]
    out["hour_ok"] = ~(
        out["block_tue_h08"] | out["block_mon_h08"] | out["block_mon_h09"] | out["any_h12_block"]
    )

    # eligible = signal + session + day + (vol always ok for Guardian — no MIN_ATR floor)
    out["eligible_signal_bar"] = out["entry_signal"] & out["in_session"] & out["day_ok"]
    return out


def compute_h12_signal_day_latch(sig: pd.DataFrame) -> pd.Series:
    """Reproduce blockH12Day latch.

    'When a valid trend-recovery signal would fire at H12 UTC on a day where
    that day's H12 is blocked, block ALL subsequent entries that day.'

    Returns a boolean Series aligned to bars: True iff the latch is engaged
    for the bar's chart-TZ trading day.
    """
    chart_date = sig.index.tz_localize("UTC").tz_convert("America/New_York").date
    chart_date = pd.Series(chart_date, index=sig.index)

    # H12 signal on a blocked-H12 day = entry_signal True + chart_h==12 + day with H12 blocked
    h12_signal_raw = (
        sig["entry_signal"]
        & (sig["chart_h"] == 12)
        & sig["in_session"]
        & sig["day_ok"]
        & sig["any_h12_block"]
    )

    latch = pd.Series(False, index=sig.index)
    triggered_dates = chart_date[h12_signal_raw].unique()
    triggered_set = set(triggered_dates)
    latch_mask = chart_date.isin(triggered_set).values

    # Latch only applies to bars AFTER the H12 signal in the same day. Pine's
    # latch sets to True at the H12 bar, blocking subsequent entries — earlier
    # entries that day already fired and are not retroactively blocked.
    latch_arr = np.zeros(len(sig), dtype=bool)
    for d in triggered_dates:
        day_mask = (chart_date.values == d)
        # Find the H12 signal bar position in the day
        day_signal_pos = np.where(day_mask & h12_signal_raw.values)[0]
        if len(day_signal_pos) == 0:
            continue
        first_h12_sig = day_signal_pos[0]
        # Latch at the H12 signal bar onward, same day
        post = day_mask & (np.arange(len(sig)) >= first_h12_sig)
        latch_arr |= post
    return pd.Series(latch_arr, index=sig.index)


def all_filters_pass(sig: pd.DataFrame, h12_latch: pd.Series) -> pd.Series:
    return (
        sig["entry_signal"]
        & sig["in_session"]
        & sig["day_ok"]
        & sig["hour_ok"]
        & ~h12_latch
    )


def synthetic_exit(
    bars: pd.DataFrame,
    entry_idx: int,
    entry_px: float,
    atr_at_entry: float,
) -> tuple[float, int, str]:
    """Walk forward, resolve a synthetic Guardian trade.

    Implements grace-stop (bar 1 only at 2.0×stop_dist), then normal stop,
    TP at 29×ATR, max-hold 850 bars.

    Returns (exit_px, bars_held, exit_reason).
    """
    stop_dist = atr_at_entry * ATR_SL_MULT
    normal_stop = entry_px - stop_dist
    grace_stop = entry_px - stop_dist * GRACE_STOP_MULT
    tp = entry_px + atr_at_entry * TP_ATR

    high = bars["high"].values
    low = bars["low"].values
    open_ = bars["open"].values
    n = len(bars)

    for offset in range(1, MAX_HOLD + 1):
        b = entry_idx + offset
        if b >= n:
            return float(open_[n - 1]), offset, "stale"
        # Grace window: first MIN_BARS_BEFORE_STOP bars use the wider grace stop
        active_stop = grace_stop if offset <= MIN_BARS_BEFORE_STOP else normal_stop
        if low[b] <= active_stop:
            return float(active_stop), offset, "grace_sl" if offset <= MIN_BARS_BEFORE_STOP else "sl"
        if high[b] >= tp:
            return float(tp), offset, "tp"
    closeout_idx = entry_idx + MAX_HOLD + 1
    if closeout_idx < n:
        return float(open_[closeout_idx]), MAX_HOLD, "stale"
    return float(bars["close"].values[entry_idx + MAX_HOLD]), MAX_HOLD, "stale"


def synthetic_R(exit_px: float, entry_px: float, atr_at_entry: float) -> float:
    return (exit_px - entry_px) / (atr_at_entry * ATR_SL_MULT)


# ---------------------------------------------------------- entry validation
def validate_entry_signal(
    bars: pd.DataFrame,
    sig: pd.DataFrame,
    h12_latch: pd.Series,
    trades: pd.DataFrame,
    *,
    bar_tolerance: int = 1,
) -> tuple[float, int, int]:
    locked_pass = all_filters_pass(sig, h12_latch)
    csv_fill_utc = ind.csv_naive_to_utc(trades["entry_ts"])
    csv_signal_utc = csv_fill_utc - pd.Timedelta(minutes=15)

    matched = 0
    for ts in csv_signal_utc:
        if pd.isna(ts) or ts not in bars.index:
            continue
        positions = bars.index.get_indexer([ts])
        if positions[0] == -1:
            continue
        center = positions[0]
        for off in range(-bar_tolerance, bar_tolerance + 1):
            j = center + off
            if 0 <= j < len(bars) and locked_pass.iloc[j]:
                matched += 1
                break
    n_csv = len(trades)
    return matched / n_csv, matched, n_csv


# ------------------------------------------------------ blocked-setup analysis
def blocked_setup_population(
    bars: pd.DataFrame,
    sig: pd.DataFrame,
    h12_latch: pd.Series,
    filter_name: str,
) -> tuple[np.ndarray, np.ndarray]:
    """For `filter_name`, build (R_blocked, R_unblocked).

    Population eligibility = entry_signal AND in_session AND day_ok AND
    EVERY OTHER locked filter passes. Within that, "blocked" = the filter
    under test rejected the bar.

    Filters supported: tue_h08, mon_h08, mon_h09, mon_h12, tue_h12, thu_h12,
    h12_day_latch, day_wed, day_fri.
    """
    block_map = {
        "tue_h08": sig["block_tue_h08"],
        "mon_h08": sig["block_mon_h08"],
        "mon_h09": sig["block_mon_h09"],
        "mon_h12": sig["block_mon_h12"],
        "tue_h12": sig["block_tue_h12"],
        "thu_h12": sig["block_thu_h12"],
        "h12_day_latch": h12_latch,
        "day_wed": sig["chart_dow"] == 2,
        "day_fri": sig["chart_dow"] == 4,
    }
    if filter_name not in block_map:
        raise AssertionError(f"unknown filter_name {filter_name!r}")
    block = block_map[filter_name]

    # Define eligibility = "would-have-fired-if-not-for-this-filter".
    # For hour-blocks: entry_signal + in_session + day_ok + (other hour-blocks pass) + (latch off).
    # For day_wed/day_fri: entry_signal + in_session + (NOT in locked dayAllowed) +
    # (hour_ok ignoring day-specific blocks) — for Wed/Fri there are no day-keyed hour blocks
    # that could conflict, so eligibility = entry_signal + in_session + that day.
    if filter_name.startswith("day_"):
        # Proper null for "would-have-fired-on-Wed/Fri": compare against signal
        # bars on currently-allowed days (Mon/Tue/Thu) under same hour-ok & latch-off.
        target_dow = 2 if filter_name == "day_wed" else 4
        on_target = sig["chart_dow"] == target_dow
        on_allowed = sig["day_ok"] & sig["hour_ok"] & ~h12_latch
        eligibility = sig["entry_signal"] & sig["in_session"] & (on_target | on_allowed)
        block = on_target  # blocked subset = currently-excluded day-of-week
    else:
        # Hour-block test: eligibility = standard signal + session + day_ok + every OTHER hour-block passes + latch off
        # Build hour_ok_excluding_test
        all_hour_blocks = {
            "tue_h08": sig["block_tue_h08"],
            "mon_h08": sig["block_mon_h08"],
            "mon_h09": sig["block_mon_h09"],
            "mon_h12": sig["block_mon_h12"],
            "tue_h12": sig["block_tue_h12"],
            "thu_h12": sig["block_thu_h12"],
        }
        if filter_name == "h12_day_latch":
            other_hour_ok = sig["hour_ok"]
            no_latch = pd.Series(True, index=sig.index)  # exclude the latch from "other"
        else:
            others = [v for k, v in all_hour_blocks.items() if k != filter_name]
            other_hour_block_or = others[0]
            for v in others[1:]:
                other_hour_block_or = other_hour_block_or | v
            other_hour_ok = ~other_hour_block_or
            no_latch = ~h12_latch
        eligibility = sig["entry_signal"] & sig["in_session"] & sig["day_ok"] & other_hour_ok & no_latch

    pop_idx = np.where(eligibility.values)[0]

    block_arr = block.values
    atr_arr = sig["atr"].values

    R_all = np.full(len(pop_idx), np.nan)
    is_blocked = np.zeros(len(pop_idx), dtype=bool)
    for i, ix in enumerate(pop_idx):
        fill_idx = ix + 1
        if fill_idx >= len(bars):
            continue
        entry_px = float(bars["open"].values[fill_idx])
        atr_v = float(atr_arr[ix])
        if not np.isfinite(entry_px) or not np.isfinite(atr_v) or atr_v <= 0:
            continue
        exit_px, _, _ = synthetic_exit(bars, fill_idx, entry_px, atr_v)
        R_all[i] = synthetic_R(exit_px, entry_px, atr_v)
        is_blocked[i] = block_arr[ix]

    keep = ~np.isnan(R_all)
    R_all = R_all[keep]
    is_blocked = is_blocked[keep]
    return R_all[is_blocked], R_all[~is_blocked]


# ------------------------------------------------------------ post-exit
def post_exit_R(bars: pd.DataFrame, sig: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    csv_exit_utc = ind.csv_naive_to_utc(trades["exit_ts"])
    csv_fill_utc = ind.csv_naive_to_utc(trades["entry_ts"])
    csv_signal_utc = csv_fill_utc - pd.Timedelta(minutes=15)

    excursion = post_exit_excursion(bars, csv_exit_utc, trades["exit_px"], n_bars=50)

    R_unit = np.full(len(trades), np.nan)
    for i, ts in enumerate(csv_signal_utc):
        if not pd.isna(ts) and ts in bars.index:
            atr_v = float(sig.at[ts, "atr"])
            if np.isfinite(atr_v) and atr_v > 0:
                R_unit[i] = atr_v * ATR_SL_MULT

    excursion["R_unit"] = R_unit
    excursion["mfe_R"] = excursion["mfe_px"] / R_unit
    excursion["mae_R"] = excursion["mae_px"] / R_unit

    realized_R = (trades["exit_px"] - trades["entry_px"]) / R_unit
    reason = []
    for sig_exit, R in zip(trades["signal_exit"].values, realized_R):
        s = str(sig_exit).lower()
        if "stale" in s:
            reason.append("max_hold")
        elif np.isnan(R):
            reason.append("unknown")
        elif R <= -1.5:
            reason.append("grace_sl")
        elif R <= -0.85:
            reason.append("sl")
        elif R <= 0.10:
            reason.append("scratch")
        elif R >= TP_ATR - 1.0:
            reason.append("tp")
        else:
            reason.append("trail_or_intra")
    excursion["exit_reason"] = reason
    excursion["realized_R"] = realized_R.values
    excursion["entry_ts"] = trades["entry_ts"].values
    return excursion


def held_trade_ranges(trades: pd.DataFrame) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    entry_utc = ind.csv_naive_to_utc(trades["entry_ts"])
    exit_utc = ind.csv_naive_to_utc(trades["exit_ts"])
    return list(zip(entry_utc.tolist(), exit_utc.tolist()))


# ------------------------------------------------------------- gate + write
def gate_blocked(filter_name: str, R_blocked, R_unblocked) -> dict:
    n = len(R_blocked)
    if n < 2 or len(R_unblocked) < 2:
        return {"filter": filter_name, "n_blocked": n, "mean_R": float("nan"),
                "p": float("nan"), "verdict": "rejected", "reason": f"insufficient pop (n={n})"}
    pop = np.concatenate([R_blocked, R_unblocked])
    obs, _, p = label_permutation_test(pop, n_blocked=n, n_perm=N_PERM)
    if n < N_MIN_GATE:
        return {"filter": filter_name, "n_blocked": n, "mean_R": obs, "p": p,
                "verdict": "rejected", "reason": f"N<{N_MIN_GATE}"}
    if p >= P_GATE:
        return {"filter": filter_name, "n_blocked": n, "mean_R": obs, "p": p,
                "verdict": "rejected", "reason": f"p>={P_GATE}"}
    if abs(obs) < COST_FLOOR_R:
        return {"filter": filter_name, "n_blocked": n, "mean_R": obs, "p": p,
                "verdict": "rejected", "reason": f"|effect|<{COST_FLOOR_R}R cost floor"}
    return {"filter": filter_name, "n_blocked": n, "mean_R": obs, "p": p,
            "verdict": "candidate", "reason": ""}


def gate_post_exit(reason: str, mfe_R: np.ndarray, pool_mfe_R: np.ndarray) -> dict:
    n = int((~np.isnan(mfe_R)).sum())
    if n < 2 or len(pool_mfe_R) < n + 2:
        return {"exit_reason": reason, "n": n, "mean_mfe_R": float("nan"),
                "p": float("nan"), "verdict": "rejected", "reason": f"insufficient pool (n={n})"}
    obs, _, p = window_permutation_test(mfe_R, pool_mfe_R, n_perm=N_PERM)
    if n < N_MIN_GATE:
        return {"exit_reason": reason, "n": n, "mean_mfe_R": obs, "p": p,
                "verdict": "rejected", "reason": f"N<{N_MIN_GATE}"}
    if p >= P_GATE:
        return {"exit_reason": reason, "n": n, "mean_mfe_R": obs, "p": p,
                "verdict": "rejected", "reason": f"p>={P_GATE}"}
    if abs(obs) < COST_FLOOR_R * 5:
        return {"exit_reason": reason, "n": n, "mean_mfe_R": obs, "p": p,
                "verdict": "rejected", "reason": f"|effect|<{COST_FLOOR_R*5}R continuation floor"}
    return {"exit_reason": reason, "n": n, "mean_mfe_R": obs, "p": p,
            "verdict": "candidate", "reason": ""}


# ----------------------------------------------------------------------- main
def main():
    bars = load_oanda_bars(SYMBOL)
    trades = load_tv_export(
        TRADE_CSV,
        expected_strategy="Guardian",
        expected_version=STRATEGY_VER,
        expected_symbol=SYMBOL,
    )
    print(f"Loaded {len(bars):,} {SYMBOL} bars, {len(trades)} Guardian trades")

    csv_fill_utc = ind.csv_naive_to_utc(trades["entry_ts"])
    median_gap, gaps = ind.verify_csv_to_bar_alignment(bars, csv_fill_utc, trades["entry_px"])
    if median_gap > 0.005:
        raise AssertionError(f"CSV->bar alignment fail: median {median_gap*100:.3f}% > 0.5%")
    print(f"CSV->bar alignment median gap: {median_gap*100:.4f}%")

    sig = compute_guardian_signals(bars)
    h12_latch = compute_h12_signal_day_latch(sig)
    match_rate, n_matched, n_csv = validate_entry_signal(bars, sig, h12_latch, trades)
    print(f"Entry-signal validation: {match_rate*100:.2f}% ({n_matched}/{n_csv})")
    if match_rate < 0.98:
        raise AssertionError(
            f"Entry-signal re-implementation diverges: {match_rate*100:.2f}% < 98%. Halt."
        )

    blocked_results = []
    for f in ("tue_h08", "mon_h08", "mon_h09", "mon_h12", "tue_h12", "thu_h12",
              "h12_day_latch", "day_wed", "day_fri"):
        R_blocked, R_unblocked = blocked_setup_population(bars, sig, h12_latch, f)
        blocked_results.append(gate_blocked(f, R_blocked, R_unblocked))
        r = blocked_results[-1]
        reason_str = f" ({r['reason']})" if r['reason'] else ""
        print(f"  blocked-setup [{f:14s}]: n={r['n_blocked']:>4d}  mean_R={r['mean_R']:>+.4f}  "
              f"p={r['p']:.3f}  -> {r['verdict']}{reason_str}")

    excursion = post_exit_R(bars, sig, trades)
    pool = random_window_excursion(
        bars, n_samples=2000, n_bars=50,
        rng=np.random.default_rng(2026),
        excluded_ranges=held_trade_ranges(trades),
    )
    median_R_unit = float(np.nanmedian(excursion["R_unit"].values))
    if not np.isfinite(median_R_unit) or median_R_unit <= 0:
        raise AssertionError("Cannot derive median R_unit for null-pool conversion")
    pool_R = pool["mfe_px"].values / median_R_unit

    post_exit_results = []
    for reason in ("grace_sl", "sl", "scratch", "trail_or_intra", "tp", "max_hold"):
        sub = excursion[excursion["exit_reason"] == reason]
        post_exit_results.append(gate_post_exit(reason, sub["mfe_R"].values, pool_R))
        r = post_exit_results[-1]
        print(f"  post-exit [{reason:16s}]: n={r['n']:>3d}  mfe_R={r['mean_mfe_R']:>+.3f}  "
              f"p={r['p']:.3f}  -> {r['verdict']}")

    today = dt.date.today().isoformat()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{today}_oanda_stage1_guardian.md"
    write_findings(out_path, match_rate, n_matched, n_csv, median_gap,
                   blocked_results, post_exit_results, len(bars), len(trades))
    print(f"\nWrote {out_path}")
    return out_path


def write_findings(
    path: Path,
    match_rate: float, n_matched: int, n_csv: int,
    median_alignment_gap: float,
    blocked_results: list[dict],
    post_exit_results: list[dict],
    n_bars: int, n_trades: int,
):
    candidates = [b for b in blocked_results if b["verdict"] == "candidate"]
    candidates += [p for p in post_exit_results if p["verdict"] == "candidate"]
    rejected = [b for b in blocked_results if b["verdict"] != "candidate"]
    rejected += [p for p in post_exit_results if p["verdict"] != "candidate"]

    lines = [
        f"# OANDA Stage 1 - Guardian Gold {STRATEGY_VER} - {dt.date.today().isoformat()}",
        "",
        "**D-S-A domain:** data",
        "",
        "**Pre-Q gate:**",
        "  - **D:** Pepperstone CSVs deleted (scope test); pre-2022 bars deleted (temporal scope).",
        "  - **S:** Per-bar predicate matrix (entry_signal, in_session, day_ok, every hour-block) cached once; trades collapsed to per-trade rows with signal-bar ATR (R-unit pin).",
        "  - **A:** Bar timestamp index; per-filter eligibility mask cached once; H12 day-latch precomputed.",
        "",
        "## Brief header",
        "",
        f"- Strategy: Guardian Gold {STRATEGY_VER} (locked {LOCK_DATE}; risk re-locked 0.30% -> 0.34% same day)",
        f"- OANDA bar window: {n_bars:,} 15M bars",
        f"- OANDA trade CSV: `{TRADE_CSV}`, N={n_trades}",
        f"- Cost model (per Pine `strategy(...)`): commission 0 (cash_per_order=0), slippage {SLIPPAGE_TICKS} ticks",
        f"- Chart TZ: America/New_York (DST-aware); CSV->bar median fill-open gap {median_alignment_gap*100:.4f}%",
        f"- Entry-signal validation: **{match_rate*100:.2f}%** ({n_matched}/{n_csv}) match against CSV with all v5.5 filters on (>=98% required)",
        "",
        "## Blocked-setup findings",
        "",
        "Population per filter = bars where the EMA-recovery signal is hot AND session/day filters pass AND every *other* locked filter passes. Synthetic R = (exit_px - entry_px) / (1.55 x ATR), with grace-stop bar-1 mechanic preserved. Permutation = 1000-shuffle relabeling within the population.",
        "",
        "| Filter | N blocked | Mean R | p (1000 perm) | Verdict |",
        "|---|---:|---:|---:|---|",
    ]
    for b in blocked_results:
        lines.append(f"| {b['filter']} | {b['n_blocked']} | {b['mean_R']:+.4f} | {b['p']:.3f} | "
                     f"{b['verdict']}{' - ' + b['reason'] if b['reason'] else ''} |")

    lines.extend([
        "",
        "## Post-exit findings",
        "",
        "Per CSV exit, MFE_50 / MAE_50 over the next 50 bars in long-direction. R-units use signal-bar ATR x 1.55. Null pool = 2000 random non-trade-window 50-bar windows, excursion R = mfe_px / panel-median R-unit (approximation since random anchors have no per-window signal-bar ATR).",
        "",
        "| Exit reason | N | Mean MFE_50 (R) | p (1000 perm) | Verdict |",
        "|---|---:|---:|---:|---|",
    ])
    for p in post_exit_results:
        lines.append(f"| {p['exit_reason']} | {p['n']} | {p['mean_mfe_R']:+.3f} | {p['p']:.3f} | "
                     f"{p['verdict']}{' - ' + p['reason'] if p['reason'] else ''} |")

    lines.extend(["", "## Gated candidates", ""])
    if not candidates:
        lines.append("_None._ All tested filters and post-exit subsets failed Stage 1 gating (N>=100, p<0.05, |effect| above cost floor). Working as the discipline expects: hypothesis-generation produced no actionable hypotheses on this OANDA panel.")
    else:
        for c in candidates:
            name = c.get("filter", c.get("exit_reason"))
            lines.append(f"### {name}")
            lines.append("")
            lines.append("- **Mechanism (one falsifiable sentence):** _author after candidate review._")
            lines.append("- **Locked baseline:** see Pine source `strategies/guardian/guardian_gold_v5.5.pine`.")
            lines.append("- **Proposed direction:** removal / loosening / tightening (case-by-case).")
            lines.append("- **Position-gate interaction:** _flag if candidate change alters per-day eligibility (Guardian max 2/day cap interacts with hour-block removal)._")
            lines.append("- **Range proposal:** _bounded post-Stage-2 - Stage 1 emits the candidate, not the parameter value._")
            lines.append("")

    lines.extend(["", "## Rejected candidates", ""])
    for r in rejected:
        name = r.get("filter", r.get("exit_reason"))
        lines.append(f"- **{name}** - {r['reason']}")
    lines.append("")
    lines.append("Stage 1 complete. Candidates require Pepperstone Stage 2 validation before any consideration of Pine work or version bump.")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
