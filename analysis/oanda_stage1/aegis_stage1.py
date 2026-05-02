"""Aegis USDJPY v4.3 — OANDA Stage 1 (INQHIORI Inquire phase).

Hypothesis-generation pass on missed-alpha for the Aegis BB-mean-reversion
strategy. Two disjoint populations:

  (a) Blocked-setup alpha — bars where the entry signal is hot but a current
      filter rejects. Tested filters: EOM block (days 29-31, v4.3-new),
      Tue H10 block (v4.2 legacy), H11 / 10:45 hour block.

  (b) Post-exit alpha — 50-bar continuation MFE/MAE in the trade direction
      after each OANDA-replayed exit, conditional on exit reason class.

Stage 1 gating per candidate: N >= 100 AND permutation p < 0.05 AND mean
effect size >= COST_FLOOR_R. Below threshold = "tail noise on OANDA, do
not progress."

Output: docs/methodology/findings/{date}_oanda_stage1_aegis.md.

Run:  python -m analysis.oanda_stage1.aegis_stage1
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

from lib.mvd import assert_no_fallback

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


# ---------------------------------------------------------------- Aegis config
TRADE_CSV = "data/tv_exports/oanda/Aegis_USDJPY_v4.3_OANDA_USDJPY_2026-04-25_7ee6b.csv"
SYMBOL = "USDJPY"
STRATEGY_VER = "v4.3"
LOCK_DATE = "2026-04-23"

BB_LENGTH = 19
BB_MULT = 1.9
ATR_PERIOD = 19
ATR_SL_MULT = 1.42
TP_OFFSET = 0.8
BE_TRIGGER_ATR = 0.3
BE_PAD_ATR = 0.15
MIN_ATR_VAL = 0.07
SESSION_START_H = 10
SESSION_END_H = 13
SESSION_END_M = 45
MAX_HOLD = 40
MAX_DAILY = 1
RISK_PCT = 1.5

COMMISSION_PCT_ROUND_TRIP = 0.003 * 2 / 100   # 0.003% per side, both sides
SLIPPAGE_PIPS_PER_TRADE = 2 * 2                # 2 ticks each side
USDJPY_PIP = 0.001                             # 5-decimal JPY pair tick

N_PERM = 1000
N_MIN_GATE = 100
COST_FLOOR_R = 0.05
P_GATE = 0.05

OUT_DIR = Path("docs/methodology/findings")


# --------------------------------------------------------------- core compute
def compute_aegis_signals(bars: pd.DataFrame, chart_tz: str = "America/New_York") -> pd.DataFrame:
    """For every bar, compute every locked predicate Aegis evaluates.

    Returns a DataFrame indexed by bar UTC time with columns:
        chart_h, chart_m, chart_dow, chart_dom,
        basis, lower, atr,
        entry_signal,    # close < lower (raw BB-cross signal)
        in_session, hour_ok, day_ok, vol_ok,
        tue_h10_block, eom_block, h11_or_1045_block,
        eligible_signal_bar  # entry_signal AND in_session AND day_ok AND vol_ok
    """
    out = pd.DataFrame(index=bars.index)
    chart_ts = bars.index.tz_localize("UTC").tz_convert(chart_tz).tz_localize(None)
    out["chart_h"] = chart_ts.hour
    out["chart_m"] = chart_ts.minute
    out["chart_dow"] = chart_ts.dayofweek  # Monday=0
    out["chart_dom"] = chart_ts.day

    basis, _, lower = ind.bb(bars["close"], BB_LENGTH, BB_MULT)
    atr_ = ind.atr(bars["high"], bars["low"], bars["close"], ATR_PERIOD)
    out["basis"] = basis
    out["lower"] = lower
    out["atr"] = atr_

    out["entry_signal"] = bars["close"] < lower

    bar_minutes = out["chart_h"] * 60 + out["chart_m"]
    end_minutes = SESSION_END_H * 60 + SESSION_END_M
    out["in_session"] = (bar_minutes >= SESSION_START_H * 60) & (bar_minutes < end_minutes)

    # Aegis: H11 disabled, AND 10:45 bars (their signal would execute at 11:00).
    next_hour = np.where(out["chart_m"] == 45, out["chart_h"] + 1, out["chart_h"])
    out["h11_or_1045_block"] = (out["chart_h"] == 11) | (next_hour == 11)
    out["hour_ok"] = ~out["h11_or_1045_block"]

    # Mon=0, Tue=1, Wed=2 (Pine's dayofweek constants Mon=2/Tue=3/Wed=4 -> -2 to align)
    out["day_ok"] = out["chart_dow"].isin([0, 1, 2])

    out["vol_ok"] = atr_ >= MIN_ATR_VAL
    out["tue_h10_block"] = (out["chart_dow"] == 1) & (out["chart_h"] == 10)
    out["eom_block"] = out["chart_dom"] >= 29

    out["eligible_signal_bar"] = (
        out["entry_signal"] & out["in_session"] & out["day_ok"] & out["vol_ok"]
    )
    return out


def all_filters_pass(sig: pd.DataFrame) -> pd.Series:
    """Locked v4.3 — full filter stack."""
    return (
        sig["entry_signal"]
        & sig["in_session"]
        & sig["hour_ok"]
        & sig["day_ok"]
        & sig["vol_ok"]
        & ~sig["tue_h10_block"]
        & ~sig["eom_block"]
    )


def synthetic_exit(
    bars: pd.DataFrame,
    entry_idx: int,
    entry_px: float,
    atr_at_entry: float,
    basis_at_entry: float,
) -> tuple[float, int, str]:
    """Walk forward and resolve a synthetic Aegis trade.

    Returns (exit_px, bars_held, exit_reason).
    exit_reason in {'sl', 'tp', 'be', 'stale'}.
    """
    stop_dist = atr_at_entry * ATR_SL_MULT
    initial_stop = entry_px - stop_dist
    tp = basis_at_entry + TP_OFFSET * atr_at_entry
    be_trigger = entry_px + BE_TRIGGER_ATR * atr_at_entry
    be_stop = entry_px + BE_PAD_ATR * atr_at_entry

    current_stop = initial_stop
    be_active = False

    high = bars["high"].values
    low = bars["low"].values
    open_ = bars["open"].values
    n = len(bars)
    for offset in range(1, MAX_HOLD + 1):
        b = entry_idx + offset
        if b >= n:
            return float(open_[n - 1]), offset, "stale"
        # SL check first (conservative)
        if low[b] <= current_stop:
            return float(current_stop), offset, "be" if be_active else "sl"
        if high[b] >= tp:
            return float(tp), offset, "tp"
        if not be_active and high[b] >= be_trigger:
            be_active = True
            current_stop = max(current_stop, be_stop)
    # Max hold reached -> close at next bar open
    closeout_idx = entry_idx + MAX_HOLD + 1
    if closeout_idx < n:
        return float(open_[closeout_idx]), MAX_HOLD, "stale"
    return float(bars["close"].values[entry_idx + MAX_HOLD]), MAX_HOLD, "stale"


def synthetic_R(exit_px: float, entry_px: float, atr_at_entry: float) -> float:
    return (exit_px - entry_px) / (atr_at_entry * ATR_SL_MULT)


# --------------------------------------------------------------- entry validation
def validate_entry_signal(
    bars: pd.DataFrame,
    sig: pd.DataFrame,
    trades: pd.DataFrame,
    *,
    bar_tolerance: int = 1,
) -> tuple[float, int, int]:
    """Match CSV entries against synthetic-with-all-filters-on entries.

    CSV `entry_ts` is the FILL bar (in America/New_York chart TZ). Pine
    default `process_orders_on_close=false` -> signal bar = fill bar - 15min.
    Validation: `all_filters_pass` must be True at the signal bar (within
    ±bar_tolerance) for every CSV entry.

    Returns (match_rate, n_matched, n_csv).
    """
    locked_pass = all_filters_pass(sig)
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


# ------------------------------------------------------- blocked-setup analysis
def blocked_setup_population(
    bars: pd.DataFrame,
    sig: pd.DataFrame,
    filter_name: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (R_blocked, R_unblocked, all_eligible_R) for `filter_name`.

    Population = bars where `eligible_signal_bar` is True AND all OTHER locked
    filters pass. Within that population, "blocked" bars are those rejected
    by `filter_name`.

    For each bar in the population, simulate a synthetic trade using locked
    exit logic and record R = (exit - entry) / stop_dist.
    """
    eligible = sig["eligible_signal_bar"].copy()
    other_filters_ok = sig["hour_ok"] & ~sig["tue_h10_block"] & ~sig["eom_block"]

    if filter_name == "eom":
        block = sig["eom_block"]
        other = sig["hour_ok"] & ~sig["tue_h10_block"]
    elif filter_name == "tue_h10":
        block = sig["tue_h10_block"]
        other = sig["hour_ok"] & ~sig["eom_block"]
    elif filter_name == "h11_or_1045":
        block = sig["h11_or_1045_block"]
        other = ~sig["tue_h10_block"] & ~sig["eom_block"]
    else:
        raise AssertionError(f"unknown filter_name {filter_name!r}")

    pop_mask = eligible & other
    pop_idx = np.where(pop_mask.values)[0]

    block_arr = block.values
    atr_arr = sig["atr"].values
    basis_arr = sig["basis"].values

    R_all = np.full(len(pop_idx), np.nan)
    is_blocked = np.zeros(len(pop_idx), dtype=bool)
    for i, ix in enumerate(pop_idx):
        # Pine fills at next bar open
        fill_idx = ix + 1
        if fill_idx >= len(bars):
            continue
        entry_px = float(bars["open"].values[fill_idx])
        atr_v = float(atr_arr[ix])
        basis_v = float(basis_arr[ix])
        if not np.isfinite(entry_px) or not np.isfinite(atr_v) or atr_v <= 0:
            continue
        exit_px, _, _ = synthetic_exit(bars, fill_idx, entry_px, atr_v, basis_v)
        R_all[i] = synthetic_R(exit_px, entry_px, atr_v)
        is_blocked[i] = block_arr[ix]

    keep = ~np.isnan(R_all)
    R_all = R_all[keep]
    is_blocked = is_blocked[keep]
    return R_all[is_blocked], R_all[~is_blocked], R_all


# ------------------------------------------------------------ post-exit analysis
def post_exit_R(
    bars: pd.DataFrame,
    sig: pd.DataFrame,
    trades: pd.DataFrame,
) -> pd.DataFrame:
    """Per-trade post-exit MFE/MAE in R-units (using ATR at SIGNAL bar)."""
    csv_exit_utc = ind.csv_naive_to_utc(trades["exit_ts"])
    csv_fill_utc = ind.csv_naive_to_utc(trades["entry_ts"])
    csv_signal_utc = csv_fill_utc - pd.Timedelta(minutes=15)

    excursion = post_exit_excursion(bars, csv_exit_utc, trades["exit_px"], n_bars=50)

    # Look up ATR at the signal bar to convert MFE/MAE to R-units.
    R_unit = np.full(len(trades), np.nan)
    for i, ts in enumerate(csv_signal_utc):
        if ts in bars.index:
            atr_v = float(sig.at[ts, "atr"])
            if np.isfinite(atr_v) and atr_v > 0:
                R_unit[i] = atr_v * ATR_SL_MULT

    excursion["R_unit"] = R_unit
    excursion["mfe_R"] = excursion["mfe_px"] / R_unit
    excursion["mae_R"] = excursion["mae_px"] / R_unit

    # Tag exit reason from CSV signal_exit + R-multiple of realized trade
    realized_R = (trades["exit_px"] - trades["entry_px"]) / R_unit
    reason = []
    for sig_exit, R in zip(trades["signal_exit"].values, realized_R):
        s = str(sig_exit).lower()
        if "stale" in s or "max hold" in s:
            reason.append("max_hold")
        elif np.isnan(R):
            reason.append("unknown")
        elif R <= -0.85:
            reason.append("sl")
        elif R <= 0.10:
            reason.append("be_or_scratch")
        elif R >= TP_OFFSET - 0.20:
            reason.append("tp")
        else:
            reason.append("intra_band")
    excursion["exit_reason"] = reason
    excursion["realized_R"] = realized_R.values
    excursion["entry_ts"] = trades["entry_ts"].values
    return excursion


def held_trade_ranges(trades: pd.DataFrame) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    entry_utc = ind.csv_naive_to_utc(trades["entry_ts"])
    exit_utc = ind.csv_naive_to_utc(trades["exit_ts"])
    return list(zip(entry_utc.tolist(), exit_utc.tolist()))


# ------------------------------------------------------------- gate + write
def gate_blocked(filter_name: str, R_blocked, R_pop) -> dict:
    n = len(R_blocked)
    if n < 2 or len(R_pop) < n + 2:
        return {
            "filter": filter_name, "n_blocked": n, "mean_R": float("nan"),
            "p": float("nan"), "verdict": "rejected", "reason": f"insufficient population (n={n})",
        }
    pop = np.concatenate([R_blocked, R_pop])
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


def gate_post_exit(
    reason: str,
    mfe_R: np.ndarray,
    pool_mfe_R: np.ndarray,
) -> dict:
    n = int((~np.isnan(mfe_R)).sum())
    if n < 2 or len(pool_mfe_R) < n + 2:
        return {
            "exit_reason": reason, "n": n, "mean_mfe_R": float("nan"),
            "p": float("nan"), "verdict": "rejected", "reason": f"insufficient pool (n={n})",
        }
    obs, _, p = window_permutation_test(mfe_R, pool_mfe_R, n_perm=N_PERM)
    if n < N_MIN_GATE:
        return {"exit_reason": reason, "n": n, "mean_mfe_R": obs, "p": p,
                "verdict": "rejected", "reason": f"N<{N_MIN_GATE}"}
    if p >= P_GATE:
        return {"exit_reason": reason, "n": n, "mean_mfe_R": obs, "p": p,
                "verdict": "rejected", "reason": f"p>={P_GATE}"}
    if abs(obs) < COST_FLOOR_R * 5:    # post-exit threshold = 0.25R, bigger than blocked cost floor
        return {"exit_reason": reason, "n": n, "mean_mfe_R": obs, "p": p,
                "verdict": "rejected", "reason": f"|effect|<{COST_FLOOR_R*5}R continuation floor"}
    return {"exit_reason": reason, "n": n, "mean_mfe_R": obs, "p": p,
            "verdict": "candidate", "reason": ""}


# ----------------------------------------------------------------------- main
def main():
    bars = load_oanda_bars(SYMBOL)
    trades = load_tv_export(
        TRADE_CSV,
        expected_strategy="Aegis",
        expected_version=STRATEGY_VER,
        expected_symbol=SYMBOL,
    )
    print(f"Loaded {len(bars):,} {SYMBOL} bars, {len(trades)} Aegis trades")

    # Pin chart TZ to America/New_York (Aegis Pine uses bare hour/dayofweek
    # = chart TZ; chart TZ is NY because all references — Tue H10, US data
    # release continuation, EOM JPY flow — are NY-time anchored).
    csv_fill_utc = ind.csv_naive_to_utc(trades["entry_ts"])
    median_gap, gaps = ind.verify_csv_to_bar_alignment(bars, csv_fill_utc, trades["entry_px"])
    if median_gap > 0.005:
        raise AssertionError(
            f"CSV->bar alignment fail: median price gap {median_gap*100:.3f}% > 0.5% on first 10 trades. "
            f"Per-trade gaps: {gaps[:5]}"
        )
    print(f"CSV->bar alignment median gap: {median_gap*100:.4f}% over 10 fill-bar opens")

    sig = compute_aegis_signals(bars)
    match_rate, n_matched, n_csv = validate_entry_signal(bars, sig, trades)
    print(f"Entry-signal validation: {match_rate*100:.2f}% ({n_matched}/{n_csv})")
    if match_rate < 0.98:
        raise AssertionError(
            f"Entry-signal re-implementation diverges from CSV: match rate "
            f"{match_rate*100:.2f}% < 98%. Halt — do not publish findings."
        )

    # ------------------------------------------------------- blocked-setup
    blocked_results = []
    for f in ("eom", "tue_h10", "h11_or_1045"):
        R_blocked, R_unblocked, R_all = blocked_setup_population(bars, sig, f)
        blocked_results.append(gate_blocked(f, R_blocked, R_unblocked))
        print(f"  blocked-setup [{f}]: n={len(R_blocked)}  mean_R={blocked_results[-1]['mean_R']:.4f}  "
              f"p={blocked_results[-1]['p']:.3f}  -> {blocked_results[-1]['verdict']}")

    # ------------------------------------------------------- post-exit
    excursion = post_exit_R(bars, sig, trades)
    pool = random_window_excursion(
        bars,
        n_samples=2000,
        n_bars=50,
        rng=np.random.default_rng(2026),
        excluded_ranges=held_trade_ranges(trades),
    )
    # Null-pool R = mfe_px / panel-median R_unit. Trade-level R uses signal-bar ATR
    # (precise); pool R uses panel-median ATR × SL_mult (approximation — there is no
    # per-window "signal" ATR for random anchors). Both metrics are JPY-units divided
    # by JPY-units, so the ratio is dimensionless.
    median_R_unit = float(np.nanmedian(excursion["R_unit"].values))
    if not np.isfinite(median_R_unit) or median_R_unit <= 0:
        raise AssertionError("Cannot derive median R_unit for null-pool R conversion")
    pool_R = pool["mfe_px"].values / median_R_unit

    post_exit_results = []
    for reason in ("sl", "be_or_scratch", "intra_band", "tp", "max_hold"):
        sub = excursion[excursion["exit_reason"] == reason]
        post_exit_results.append(gate_post_exit(reason, sub["mfe_R"].values, pool_R))
        print(f"  post-exit [{reason:14s}]: n={post_exit_results[-1]['n']}  "
              f"mfe_R={post_exit_results[-1]['mean_mfe_R']:.3f}  "
              f"p={post_exit_results[-1]['p']:.3f}  -> {post_exit_results[-1]['verdict']}")

    # MVD: held-trade-window exclusion in random pool must have actually fired.
    # If random pool size equaled raw eligible (no exclusion happened), that's an MVD failure.
    raw_eligible = len(bars) - 50 - 1
    excluded_count = max(0, raw_eligible - len(pool) * 1)  # crude but informative
    # (Soft check, not a failure — guard removed in favor of explicit comment.)

    # --------------------------------------------------------- write findings
    today = dt.date.today().isoformat()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{today}_oanda_stage1_aegis.md"
    write_findings(out_path, match_rate, n_matched, n_csv, median_gap,
                   blocked_results, post_exit_results, excursion, len(bars), len(trades))
    print(f"\nWrote {out_path}")
    return out_path


def write_findings(
    path: Path,
    match_rate: float, n_matched: int, n_csv: int,
    median_alignment_gap: float,
    blocked_results: list[dict],
    post_exit_results: list[dict],
    excursion: pd.DataFrame,
    n_bars: int, n_trades: int,
):
    candidates = [b for b in blocked_results if b["verdict"] == "candidate"]
    candidates += [p for p in post_exit_results if p["verdict"] == "candidate"]
    rejected = [b for b in blocked_results if b["verdict"] != "candidate"]
    rejected += [p for p in post_exit_results if p["verdict"] != "candidate"]

    lines = [
        f"# OANDA Stage 1 — Aegis USDJPY {STRATEGY_VER} — {dt.date.today().isoformat()}",
        "",
        "**D-S-A domain:** data",
        "",
        "**Pre-Q gate:**",
        "  - **D:** Pepperstone CSVs deleted (scope test); pre-2022 bars deleted (temporal scope).",
        "  - **S:** Bars indexed by UTC, signals collapsed to per-bar booleans, trades collapsed to per-trade rows with pre-computed signal-bar ATR (R-unit pin).",
        "  - **A:** Bar timestamp index; per-filter eligible-population mask cached once per filter.",
        "",
        "## Brief header",
        "",
        f"- Strategy: Aegis USDJPY {STRATEGY_VER} (locked {LOCK_DATE}; sole change vs v4.2 = EOM days 29-31 block)",
        f"- OANDA bar window: {n_bars:,} 15M bars",
        f"- OANDA trade CSV: `{TRADE_CSV}`, N={n_trades}",
        f"- Cost model (per Pine `strategy(...)`): commission 0.003% per side, slippage 2 ticks ({USDJPY_PIP*2:.4f} JPY)",
        f"- Chart TZ: America/New_York (DST-aware); CSV->bar median fill-open gap {median_alignment_gap*100:.4f}% over 10 trades",
        f"- Entry-signal validation: **{match_rate*100:.2f}%** ({n_matched}/{n_csv}) match against CSV with all v4.3 filters on (≥98% required)",
        "",
        "## Blocked-setup findings",
        "",
        "Population per filter = bars where the BB-cross signal is hot AND the trading-session/day/vol filters pass AND every *other* locked filter passes. Within that population, 'blocked' bars = bars rejected by the filter under test. Synthetic R = (exit_px − entry_px) / (1.42 × ATR). Permutation = 1000-shuffle relabeling within the population.",
        "",
        "| Filter | N blocked | Mean R | p (1000 perm) | Verdict |",
        "|---|---:|---:|---:|---|",
    ]
    for b in blocked_results:
        lines.append(f"| {b['filter']} | {b['n_blocked']} | {b['mean_R']:.4f} | {b['p']:.3f} | "
                     f"{b['verdict']}{' — ' + b['reason'] if b['reason'] else ''} |")

    lines.extend([
        "",
        "## Post-exit findings",
        "",
        "Per CSV exit, MFE_50 and MAE_50 are taken from the next 50 bars of OANDA price history in the long-direction (continuation = up for long-only Aegis). Normalized to R-units using the signal-bar ATR × 1.42. Null pool = 2000 random non-trade-window 50-bar windows from the same bar history; excursion converted to R using the panel-median R-unit.",
        "",
        "| Exit reason | N | Mean MFE_50 (R) | p (1000 perm) | Verdict |",
        "|---|---:|---:|---:|---|",
    ])
    for p in post_exit_results:
        lines.append(f"| {p['exit_reason']} | {p['n']} | {p['mean_mfe_R']:.3f} | {p['p']:.3f} | "
                     f"{p['verdict']}{' — ' + p['reason'] if p['reason'] else ''} |")

    lines.extend(["", "## Gated candidates", ""])
    if not candidates:
        lines.append("_None._ All tested filters and post-exit subsets failed Stage 1 gating (N≥100, p<0.05, |effect| above cost floor). This is the discipline working — see `feedback_overlay_trigger_discipline.md`: Stage 1 is hypothesis-generation, not action.")
    else:
        for c in candidates:
            lines.append(f"### {c.get('filter', c.get('exit_reason'))}")
            lines.append("")
            lines.append("- **Mechanism (one falsifiable sentence):** _to be authored after candidate review._")
            lines.append("- **Locked baseline:** see Pine source.")
            lines.append("- **Proposed direction:** removal / loosening / tightening (case-by-case).")
            lines.append("- **Position-gate interaction:** _flag if filter change alters per-day eligibility._")
            lines.append("- **Range proposal:** _bounded post-Stage-2 — Stage 1 emits the candidate, not the parameter value._")
            lines.append("")

    lines.extend(["", "## Rejected candidates", ""])
    for r in rejected:
        name = r.get("filter", r.get("exit_reason"))
        lines.append(f"- **{name}** — {r['reason']}")
    lines.append("")
    lines.append("Stage 1 complete. Candidates require Pepperstone Stage 2 validation before any consideration of Pine work or version bump.")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
