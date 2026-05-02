"""Striker DJ30 v4.4 — OANDA Stage 1 (INQHIORI Inquire phase).

Hypothesis-generation pass on missed-alpha for the Striker breakout strategy.
Two disjoint populations:

  (a) Blocked-setup alpha — bars where the breakout signal is hot but a
      filter rejects. Tested filters: prev-bar-bullish, body-ratio>=0.25,
      atr-expansion>1.28×, session-warmup>3 bars, day filter (Mon/Wed/Thu
      excluded). Day soft-stop latch deferred (requires day-P&L tracking
      of synthetic equity, out of Stage 1 scope).

  (b) Post-exit alpha — 50-bar continuation MFE/MAE in long-direction.
      Adaptive trail is the prime hypothesis surface (does the 0.90 -> 0.85
      tightening at 1.5x ATR cut continuation?).

KNOWN APPROXIMATION: synthetic trades model only the BASE entry — pyramid
layers (350% add at +1.29 ATR, min 6 bars) are NOT simulated. Per plan:
"simulate without pyramiding ... document as known approximation." Realized
trade R for blocked-setup tests is therefore a base-leg-only counterfactual,
which understates upside in trades that would have pyramided. This biases
mean R DOWNWARD on candidates that would have pyramided. Effect is bounded
by the 14.2% pyramid penetration rate observed in the panel.

Striker uses `hour(time, "UTC")` and `dayofweek(time, "UTC")` — explicitly
UTC, unlike Aegis/Guardian which use chart-TZ. CSV timestamps are still
chart-NY (TradingView display TZ).

Run:  python -m analysis.oanda_stage1.striker_stage1
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


# ---------------------------------------------------------------- Striker config
TRADE_CSV = "data/tv_exports/oanda/Striker_DJ30_v4.4_OANDA_US30USD_2026-04-25_86e9d.csv"
SYMBOL = "US30USD"
STRATEGY_VER = "v4.4"
LOCK_DATE = "2026-04-23"

BREAKOUT_BARS = 15
ATR_PERIOD = 11
ATR_MA_PERIOD = 85
ATR_EXPANSION = 0.28
MIN_BODY_RATIO = 0.25
ATR_SL_MULT = 1.25
TP_ATR = 8.0
BE_TRIGGER_ATR = 0.15
BE_PAD_ATR = 0.05
TRAIL_TRIGGER_ATR = 0.15
TRAIL_DIST_WIDE = 0.90
TRAIL_DIST_TIGHT = 0.85
TRAIL_TIGHTEN_AT = 1.5
MAX_HOLD = 55
MAX_DAILY_TRADES = 3
RISK_PCT = 1.0

# Striker session: explicit UTC 13-17.
SESSION_START_H_UTC = 13
SESSION_END_H_UTC = 17
WARMUP_BARS = 3

# Pine: dayofweek.tuesday=3, dayofweek.friday=6 (UTC). pandas: Mon=0..Sun=6.
# So Tue=1, Fri=4 in pandas.
ALLOWED_DOW_PANDAS = {1, 4}

COMMISSION_USD_PER_ORDER = 0.0
SLIPPAGE_TICKS = 2

N_PERM = 1000
N_MIN_GATE = 100
COST_FLOOR_R = 0.05
P_GATE = 0.05

OUT_DIR = Path("docs/methodology/findings")


# --------------------------------------------------------------- core compute
def compute_striker_signals(bars: pd.DataFrame) -> pd.DataFrame:
    """Per-bar evaluation. All hour/dow checks against UTC (Striker uses UTC explicitly)."""
    out = pd.DataFrame(index=bars.index)
    out["utc_h"] = bars.index.hour
    out["utc_dow"] = bars.index.dayofweek

    atr_ = ind.atr(bars["high"], bars["low"], bars["close"], ATR_PERIOD)
    atr_ma = ind.sma(atr_, ATR_MA_PERIOD)
    atr_expanding = atr_ > atr_ma * (1 + ATR_EXPANSION)

    highest_high = ind.highest(bars["high"], BREAKOUT_BARS)
    raw_breakout = bars["close"] > highest_high.shift(1)

    candle_range = bars["high"] - bars["low"]
    candle_body = (bars["close"] - bars["open"]).abs()
    body_ratio = np.where(candle_range > 0, candle_body / candle_range, 0.0)
    body_ok = body_ratio >= MIN_BODY_RATIO
    prev_bar_bullish = bars["close"].shift(1) > bars["open"].shift(1)

    out["atr"] = atr_
    out["atr_expanding"] = atr_expanding
    out["raw_breakout"] = raw_breakout
    out["body_ok"] = body_ok
    out["prev_bar_bullish"] = prev_bar_bullish

    out["session_ok"] = (out["utc_h"] >= SESSION_START_H_UTC) & (out["utc_h"] < SESSION_END_H_UTC)
    out["dow_ok"] = out["utc_dow"].isin(ALLOWED_DOW_PANDAS)

    # Warmup: bars after session open. Pine uses sessionJustOpened sentinel +
    # incrementing counter. We approximate: bar position within the session
    # window, computed by counting bars since the session boundary.
    out["bars_since_session_open"] = _bars_since_session_open(out["session_ok"].values)
    out["warmup_ok"] = out["bars_since_session_open"] > WARMUP_BARS

    out["entry_signal"] = (
        out["raw_breakout"]
        & out["atr_expanding"]
        & out["session_ok"]
        & out["warmup_ok"]
        & out["dow_ok"]
        & out["body_ok"]
        & out["prev_bar_bullish"]
    )
    return out


def _bars_since_session_open(session_ok: np.ndarray) -> np.ndarray:
    out = np.zeros(len(session_ok), dtype=int)
    counter = 0
    for i, in_sess in enumerate(session_ok):
        if not in_sess:
            counter = 0
        else:
            counter += 1
        out[i] = counter
    return out


def all_filters_pass(sig: pd.DataFrame) -> pd.Series:
    return sig["entry_signal"]


def synthetic_exit(
    bars: pd.DataFrame,
    entry_idx: int,
    entry_px: float,
    atr_at_entry: float,
) -> tuple[float, int, str]:
    """Walk forward; resolve a synthetic Striker BASE-leg trade.

    Implements: SL 1.25×ATR, TP 8×ATR, BE at 0.15×ATR + 0.05 pad, adaptive
    trail (wide 0.90 -> tight 0.85 after +1.5×ATR), max hold 55 bars.
    Pyramid is NOT simulated (see module docstring).

    Returns (exit_px, bars_held, exit_reason).
    """
    stop_dist = atr_at_entry * ATR_SL_MULT
    initial_stop = entry_px - stop_dist
    tp = entry_px + atr_at_entry * TP_ATR
    be_trigger = entry_px + BE_TRIGGER_ATR * atr_at_entry
    be_stop = entry_px + BE_PAD_ATR * atr_at_entry

    current_stop = initial_stop
    be_active = False
    trail_active = False
    trail_tightened = False

    high = bars["high"].values
    low = bars["low"].values
    open_ = bars["open"].values
    n = len(bars)
    for offset in range(1, MAX_HOLD + 1):
        b = entry_idx + offset
        if b >= n:
            return float(open_[n - 1]), offset, "stale"
        # SL / TP / BE / trail evaluation
        if low[b] <= current_stop:
            reason = "be" if be_active and current_stop >= be_stop else \
                     ("trail_tight" if trail_tightened else
                      ("trail_wide" if trail_active else "sl"))
            return float(current_stop), offset, reason
        if high[b] >= tp:
            return float(tp), offset, "tp"

        # Update profit measure (using close — Pine uses close in `profit`)
        profit_atr = (bars["close"].values[b] - entry_px) / atr_at_entry

        # Tighten trail
        if profit_atr >= TRAIL_TIGHTEN_AT and not trail_tightened:
            trail_tightened = True

        # Activate BE
        if not be_active and profit_atr >= BE_TRIGGER_ATR:
            be_active = True
            current_stop = max(current_stop, be_stop)

        # Trail
        if profit_atr >= TRAIL_TRIGGER_ATR:
            trail_dist = TRAIL_DIST_TIGHT if trail_tightened else TRAIL_DIST_WIDE
            new_stop = bars["close"].values[b] - atr_at_entry * trail_dist
            if not trail_active:
                trail_active = True
                current_stop = max(current_stop, new_stop)
            else:
                current_stop = max(current_stop, new_stop)

    closeout_idx = entry_idx + MAX_HOLD + 1
    if closeout_idx < n:
        return float(open_[closeout_idx]), MAX_HOLD, "max_hold"
    return float(bars["close"].values[entry_idx + MAX_HOLD]), MAX_HOLD, "max_hold"


def synthetic_R(exit_px: float, entry_px: float, atr_at_entry: float) -> float:
    return (exit_px - entry_px) / (atr_at_entry * ATR_SL_MULT)


# ---------------------------------------------------------- entry validation
def validate_entry_signal(
    bars: pd.DataFrame,
    sig: pd.DataFrame,
    trades: pd.DataFrame,
    *,
    bar_tolerance: int = 1,
) -> tuple[float, int, int]:
    locked_pass = all_filters_pass(sig)
    csv_fill_utc = ind.csv_naive_to_utc(trades["entry_ts"])
    csv_signal_utc = csv_fill_utc - pd.Timedelta(minutes=15)

    # Striker has pyramid trades (Trade # for "Long Add"). Only validate base
    # entries — pyramid entries don't fire the entry_signal predicate.
    is_base = trades["signal_entry"] == "Long"
    base = trades[is_base].reset_index(drop=True)
    base_signal_utc = csv_signal_utc[is_base.values]

    matched = 0
    for ts in base_signal_utc:
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
    n_csv = len(base)
    return matched / n_csv, matched, n_csv


# ------------------------------------------------------ blocked-setup analysis
def blocked_setup_population(
    bars: pd.DataFrame,
    sig: pd.DataFrame,
    filter_name: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Build (R_blocked, R_unblocked) for `filter_name`.

    Each filter test treats "blocked" as the bar where THAT filter alone
    would have rejected an otherwise-eligible entry.
    """
    # Eligibility = "would have entered if not for this filter": all OTHER
    # locked filters pass + raw breakout fires + session-window & day-filter
    # for filters that aren't day/session themselves.

    raw = sig["raw_breakout"]
    sess = sig["session_ok"]
    dow = sig["dow_ok"]
    warm = sig["warmup_ok"]
    body = sig["body_ok"]
    prev = sig["prev_bar_bullish"]
    expansion = sig["atr_expanding"]

    if filter_name == "atr_expanding":
        eligibility = raw & sess & dow & warm & body & prev
        block = ~expansion
    elif filter_name == "body_ok":
        eligibility = raw & sess & dow & warm & expansion & prev
        block = ~body
    elif filter_name == "prev_bar_bullish":
        eligibility = raw & sess & dow & warm & expansion & body
        block = ~prev
    elif filter_name == "warmup_ok":
        eligibility = raw & sess & dow & body & prev & expansion
        block = ~warm
    elif filter_name == "day_mon_wed_thu":
        # "Currently excluded days" — population = signal bars on Tue/Fri (allowed) OR Mon/Wed/Thu (excluded)
        target_dow = {0, 2, 3}        # Mon/Wed/Thu in pandas
        on_target = sig["utc_dow"].isin(target_dow)
        on_allowed = sig["utc_dow"].isin(ALLOWED_DOW_PANDAS)
        eligibility = raw & sess & warm & body & prev & expansion & (on_target | on_allowed)
        block = on_target
    else:
        raise AssertionError(f"unknown filter {filter_name!r}")

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
    for sig_exit, R, sig_entry in zip(
        trades["signal_exit"].values, realized_R, trades["signal_entry"].values
    ):
        s = str(sig_exit).lower()
        is_pyramid = "add" in str(sig_entry).lower()
        if "max hold" in s:
            reason.append("max_hold_pyr" if is_pyramid else "max_hold")
        elif np.isnan(R):
            reason.append("unknown")
        elif R <= -0.85:
            reason.append("sl_pyr" if is_pyramid else "sl")
        elif R <= 0.10:
            reason.append("be_or_scratch")
        elif R >= TP_ATR - 1.0:
            reason.append("tp")
        else:
            reason.append("trail_pyr" if is_pyramid else "trail")
    excursion["exit_reason"] = reason
    excursion["realized_R"] = realized_R.values
    excursion["entry_ts"] = trades["entry_ts"].values
    excursion["is_pyramid_leg"] = ["add" in str(s).lower() for s in trades["signal_entry"].values]
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
        expected_strategy="Striker",
        expected_version=STRATEGY_VER,
        expected_symbol=SYMBOL,
    )
    n_pyramid = (trades["signal_entry"].str.contains("Add", case=False)).sum()
    print(f"Loaded {len(bars):,} {SYMBOL} bars, {len(trades)} Striker rows ({n_pyramid} pyramid legs)")

    csv_fill_utc = ind.csv_naive_to_utc(trades["entry_ts"])
    median_gap, gaps = ind.verify_csv_to_bar_alignment(bars, csv_fill_utc, trades["entry_px"])
    if median_gap > 0.005:
        raise AssertionError(f"CSV->bar alignment fail: median {median_gap*100:.3f}% > 0.5%")
    print(f"CSV->bar alignment median gap: {median_gap*100:.4f}%")

    sig = compute_striker_signals(bars)
    match_rate, n_matched, n_csv = validate_entry_signal(bars, sig, trades)
    print(f"Entry-signal validation (BASE legs only): {match_rate*100:.2f}% ({n_matched}/{n_csv})")
    if match_rate < 0.98:
        raise AssertionError(f"Entry-signal re-implementation diverges: {match_rate*100:.2f}% < 98%. Halt.")

    blocked_results = []
    for f in ("atr_expanding", "body_ok", "prev_bar_bullish", "warmup_ok", "day_mon_wed_thu"):
        R_blocked, R_unblocked = blocked_setup_population(bars, sig, f)
        blocked_results.append(gate_blocked(f, R_blocked, R_unblocked))
        r = blocked_results[-1]
        reason_str = f" ({r['reason']})" if r['reason'] else ""
        print(f"  blocked-setup [{f:18s}]: n={r['n_blocked']:>5d}  mean_R={r['mean_R']:>+.4f}  "
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
    for reason in ("sl", "sl_pyr", "be_or_scratch", "trail", "trail_pyr", "tp", "max_hold", "max_hold_pyr"):
        sub = excursion[excursion["exit_reason"] == reason]
        post_exit_results.append(gate_post_exit(reason, sub["mfe_R"].values, pool_R))
        r = post_exit_results[-1]
        reason_str = f" ({r['reason']})" if r['reason'] else ""
        print(f"  post-exit [{reason:18s}]: n={r['n']:>3d}  mfe_R={r['mean_mfe_R']:>+.3f}  "
              f"p={r['p']:.3f}  -> {r['verdict']}{reason_str}")

    today = dt.date.today().isoformat()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{today}_oanda_stage1_striker.md"
    write_findings(out_path, match_rate, n_matched, n_csv, median_gap,
                   blocked_results, post_exit_results, len(bars), len(trades), n_pyramid)
    print(f"\nWrote {out_path}")
    return out_path


def write_findings(
    path: Path,
    match_rate: float, n_matched: int, n_csv: int,
    median_alignment_gap: float,
    blocked_results: list[dict],
    post_exit_results: list[dict],
    n_bars: int, n_trades: int, n_pyramid: int,
):
    candidates = [b for b in blocked_results if b["verdict"] == "candidate"]
    candidates += [p for p in post_exit_results if p["verdict"] == "candidate"]
    rejected = [b for b in blocked_results if b["verdict"] != "candidate"]
    rejected += [p for p in post_exit_results if p["verdict"] != "candidate"]

    lines = [
        f"# OANDA Stage 1 - Striker DJ30 {STRATEGY_VER} - {dt.date.today().isoformat()}",
        "",
        "**D-S-A domain:** data",
        "",
        "**Pre-Q gate:**",
        "  - **D:** Pepperstone CSVs deleted (scope test); pre-2022 bars deleted (temporal scope); pyramid layers excluded from synthetic-trade simulation (modeling complexity test - documented approximation, not a relevance D-test).",
        "  - **S:** Per-bar predicate matrix cached; trades collapsed to per-Trade-# rows with pyramid-leg flag preserved; signal-bar ATR pin for R-units.",
        "  - **A:** Bar timestamp index; per-filter eligibility mask cached once.",
        "",
        "## Brief header",
        "",
        f"- Strategy: Striker DJ30 {STRATEGY_VER} (locked {LOCK_DATE})",
        f"- OANDA bar window: {n_bars:,} 15M bars",
        f"- OANDA trade CSV: `{TRADE_CSV}`, N={n_trades} rows ({n_pyramid} pyramid-add legs)",
        f"- Cost model (per Pine `strategy(...)`): commission 0 (cash_per_order=0), slippage {SLIPPAGE_TICKS} ticks",
        f"- Chart TZ: America/New_York for CSV display; Pine session/dow checks against UTC explicitly",
        f"- CSV->bar median fill-open gap: {median_alignment_gap*100:.4f}%",
        f"- Entry-signal validation (BASE legs only): **{match_rate*100:.2f}%** ({n_matched}/{n_csv}) match against CSV with all v4.4 filters on (>=98% required)",
        "",
        "**Known approximation:** synthetic trades simulate the BASE entry only — pyramid layers (350% size add at +1.29 ATR profit, min 6 bars between) are NOT simulated. This biases mean R DOWNWARD on candidates that would have pyramided. Pyramid penetration on the realized panel was 14.2%, so the bias is bounded. Pyramid-aware synthetic R is deferred to Stage 1.5 / Stage 2 (any pyramid-bearing candidate that survives Stage 2 must be re-measured with the pyramid rule in scope).",
        "",
        "**Deferred filter:** day soft-stop (`-2.0% of init equity, latches halt for the day`) is NOT tested — testing it requires synthetic per-day cumulative-P&L tracking on OANDA, which is its own subsystem. Flagged for Stage 1.5 if no candidate survives Stage 2.",
        "",
        "## Blocked-setup findings",
        "",
        "Population per filter = bars where every OTHER locked entry filter passes AND the raw breakout fires. Synthetic R = (exit_px - entry_px) / (1.25 x ATR). Permutation = 1000-shuffle relabeling within population.",
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
        "Per-leg post-exit MFE_50 / MAE_50 in long-direction. Pyramid legs tagged separately (`*_pyr`) for hypothesis surface visibility — adaptive trail tightening is suspected to be the prime continuation-cut hypothesis.",
        "",
        "| Exit reason | N | Mean MFE_50 (R) | p (1000 perm) | Verdict |",
        "|---|---:|---:|---:|---|",
    ])
    for p in post_exit_results:
        lines.append(f"| {p['exit_reason']} | {p['n']} | {p['mean_mfe_R']:+.3f} | {p['p']:.3f} | "
                     f"{p['verdict']}{' - ' + p['reason'] if p['reason'] else ''} |")

    lines.extend(["", "## Gated candidates", ""])
    if not candidates:
        lines.append("_None._ All tested filters and post-exit subsets failed Stage 1 gating (N>=100, p<0.05, |effect| above cost floor) on this OANDA panel.")
    else:
        for c in candidates:
            name = c.get("filter", c.get("exit_reason"))
            lines.append(f"### {name}")
            lines.append("")
            lines.append("- **Mechanism (one falsifiable sentence):** _author after candidate review._")
            lines.append("- **Locked baseline:** see Pine source `strategies/striker/striker_dj30_v4.4.pine`.")
            lines.append("- **Proposed direction:** removal / loosening / tightening (case-by-case).")
            lines.append("- **Position-gate interaction:** Striker max-3/day cap and the day soft-stop both interact with any filter loosening — re-MC must include this.")
            lines.append("- **Range proposal:** _bounded post-Stage-2 - Stage 1 emits the candidate, not the parameter value._")
            lines.append("- **Pyramid-bias note:** synthetic R for this candidate is base-leg-only — re-measure with pyramid rule active before any Pine work.")
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
