"""Stage 0 — OANDA <-> Pepperstone feed reconciliation for USOIL 15min.

Brief: 2026-05-02 USOIL 15min behavioral characterization (§3 Stage 0).
Plan: ~/.claude/plans/usoil-15min-behavioral-composed-tower.md (Stage 0).

Hard precondition: a Pepperstone-exported USOIL 15min CSV must exist at
data/tv_exports/pepperstone/USOIL_pepperstone_m15_<from>_to_<to>.csv. Joshua
exports this from TradingView (broker-connected Pepperstone chart) before
this script runs. The script auto-discovers any matching file.

Diagnostics (per brief §3 Stage 0 table):
  1. Bar-timestamp alignment — must match within ±0 minutes after UTC normalization.
  2. Spearman rho(r_OANDA, r_Pepperstone) per 15min bin — must be >=0.95 every bin.
  3. Roll convention — both must use front-month continuous (or matching back-adj).
  4. Holiday calendar — cross-tab session presence Mon-Fri.
  5. Spread profile — median spread per 15min bin (informational).

Stop rule: alignment / correlation / roll-convention failure -> stop.

Output: docs/methodology/findings/2026-05-02_usoil_feed_reconciliation.md
        (verdict at top: PASS or FAIL with diagnostic detail)

Note: the OANDA pull for the overlap window happens here (not phase1_fetch),
because Stage 0 may pre-date the full 52-month Phase 1 pull.
"""
from __future__ import annotations

import json
import pathlib
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from lib.oanda import fetch_candles  # noqa: E402

OANDA_INSTRUMENT = "WTICO_USD"
GRANULARITY = "M15"
PRICE = "M"

# Overlap window: most recent 12 months of complete data. The Pepperstone
# export must cover at least this window. The script will trim both feeds to
# the intersection of their actual coverage.
OVERLAP_START = "2025-04-01T00:00:00Z"
OVERLAP_END = "2026-04-20T00:00:00Z"

PEPPERSTONE_GLOB = "USOIL_pepperstone_m15_*.csv"
PEPPERSTONE_DIR = REPO_ROOT / "data" / "tv_exports" / "pepperstone"
FINDINGS_DIR = REPO_ROOT / "docs" / "methodology" / "findings"
OUT_MD = FINDINGS_DIR / "2026-05-02_usoil_feed_reconciliation.md"

CORRELATION_FLOOR = 0.95
MAX_ALIGNMENT_DRIFT_MINUTES = 0


def _find_pepperstone_csv() -> pathlib.Path:
    matches = sorted(PEPPERSTONE_DIR.glob(PEPPERSTONE_GLOB))
    if not matches:
        raise SystemExit(
            f"Stage 0 PRECONDITION FAIL: no Pepperstone CSV at "
            f"{PEPPERSTONE_DIR / PEPPERSTONE_GLOB}. Joshua must export USOIL "
            f"15min from TradingView Pepperstone before this script runs."
        )
    if len(matches) > 1:
        print(f"Stage 0: multiple Pepperstone CSVs found, using newest: {matches[-1].name}")
    return matches[-1]


def _load_pepperstone(path: pathlib.Path) -> pd.DataFrame:
    """Load Pepperstone TV-exported bar CSV. Auto-detect schema.

    TradingView "Export chart data" emits one of two formats:
      A. time(ISO8601), open, high, low, close[, Volume]
      B. time(unix-seconds), open, high, low, close[, Volume]
    Both are supported. Output is normalized to columns
    [time_utc, open, high, low, close] with time_utc as tz-aware UTC.
    """
    df = pd.read_csv(path)
    cols = {c.lower(): c for c in df.columns}
    # Find the time column
    time_key = None
    for k in ("time", "datetime", "date", "timestamp"):
        if k in cols:
            time_key = cols[k]
            break
    if time_key is None:
        raise SystemExit(f"Pepperstone CSV {path.name} missing time column; cols={list(df.columns)}")
    # Detect unix vs ISO. numpy int dtypes are not Python int instances, so
    # check the column dtype directly rather than the scalar type.
    if pd.api.types.is_numeric_dtype(df[time_key]):
        df["time_utc"] = pd.to_datetime(df[time_key].astype("int64"), unit="s", utc=True)
    else:
        sample = df[time_key].iloc[0]
        if isinstance(sample, str) and sample.strip().isdigit():
            df["time_utc"] = pd.to_datetime(df[time_key].astype("int64"), unit="s", utc=True)
        else:
            df["time_utc"] = pd.to_datetime(df[time_key], utc=True)
    # Find OHLC columns
    ohlc = {}
    for k in ("open", "high", "low", "close"):
        if k in cols:
            ohlc[k] = cols[k]
        else:
            raise SystemExit(f"Pepperstone CSV {path.name} missing column '{k}'; cols={list(df.columns)}")
    out = pd.DataFrame({
        "time_utc": df["time_utc"],
        "open": df[ohlc["open"]].astype(float),
        "high": df[ohlc["high"]].astype(float),
        "low": df[ohlc["low"]].astype(float),
        "close": df[ohlc["close"]].astype(float),
    })
    out = out.sort_values("time_utc").drop_duplicates(subset=["time_utc"]).reset_index(drop=True)
    return out


def _fetch_oanda_overlap() -> pd.DataFrame:
    print(f"Stage 0: fetching OANDA {OANDA_INSTRUMENT} {GRANULARITY} {OVERLAP_START} -> {OVERLAP_END}")
    rows = list(fetch_candles(OANDA_INSTRUMENT, OVERLAP_START, OVERLAP_END,
                              granularity=GRANULARITY, price=PRICE))
    if not rows:
        raise SystemExit("Stage 0 FAIL: OANDA overlap pull returned zero candles")
    df = pd.DataFrame(rows)
    df["time_utc"] = pd.to_datetime(df["time"].str[:23] + "Z", format="%Y-%m-%dT%H:%M:%S.%fZ", utc=True)
    df = df[["time_utc", "open", "high", "low", "close"]].astype({
        "open": float, "high": float, "low": float, "close": float,
    })
    df = df.sort_values("time_utc").drop_duplicates(subset=["time_utc"]).reset_index(drop=True)
    print(f"Stage 0: OANDA {len(df):,} bars, {df['time_utc'].iloc[0]} -> {df['time_utc'].iloc[-1]}")
    return df


def _diagnostics(oanda: pd.DataFrame, pep: pd.DataFrame) -> dict:
    out = {}

    # Find the intersection of date ranges. Bars outside the intersection are
    # corpus-envelope mismatch (different export windows) — not feed disagreement —
    # and would conflate the alignment diagnostic if counted as drift.
    date_lo = max(oanda["time_utc"].min(), pep["time_utc"].min())
    date_hi = min(oanda["time_utc"].max(), pep["time_utc"].max())
    oanda_in = oanda[(oanda["time_utc"] >= date_lo) & (oanda["time_utc"] <= date_hi)].copy()
    pep_in = pep[(pep["time_utc"] >= date_lo) & (pep["time_utc"] <= date_hi)].copy()

    common = oanda_in.merge(pep_in, on="time_utc", how="inner", suffixes=("_o", "_p"))
    out["intersection_start"] = str(date_lo)
    out["intersection_end"] = str(date_hi)
    out["overlap_bars"] = int(len(common))
    out["oanda_bars_in_intersection"] = int(len(oanda_in))
    out["pepperstone_bars_in_intersection"] = int(len(pep_in))
    out["oanda_only_bars_in_intersection"] = int(len(oanda_in) - len(common))
    out["pepperstone_only_bars_in_intersection"] = int(len(pep_in) - len(common))
    # Out-of-intersection counts are informational
    out["oanda_outside_intersection"] = int(len(oanda) - len(oanda_in))
    out["pepperstone_outside_intersection"] = int(len(pep) - len(pep_in))

    # 1. Alignment (within intersection only — measures actual feed drift)
    drift_pct = (out["oanda_only_bars_in_intersection"] + out["pepperstone_only_bars_in_intersection"]) / max(1, len(oanda_in) + len(pep_in)) * 100
    out["bar_drift_pct"] = float(drift_pct)
    out["alignment_pass"] = drift_pct < 1.0  # <1% drift acceptable (holiday handling)

    # 2. Return correlation per 15min bin (96 bins)
    common["ret_o"] = common["close_o"].pct_change()
    common["ret_p"] = common["close_p"].pct_change()
    common["bin"] = common["time_utc"].dt.hour * 4 + common["time_utc"].dt.minute // 15
    rho_per_bin = {}
    failed_bins = []
    for b, g in common.dropna(subset=["ret_o", "ret_p"]).groupby("bin"):
        if len(g) < 30:
            rho_per_bin[int(b)] = {"rho": None, "n": int(len(g)), "note": "underpowered (n<30)"}
            continue
        rho, p = spearmanr(g["ret_o"], g["ret_p"])
        rho_per_bin[int(b)] = {"rho": float(rho), "n": int(len(g)), "p": float(p)}
        if rho < CORRELATION_FLOOR:
            failed_bins.append({"bin": int(b), "rho": float(rho), "n": int(len(g))})
    out["return_correlation_per_bin"] = rho_per_bin
    out["bins_below_floor"] = failed_bins
    out["correlation_pass"] = len(failed_bins) == 0

    # 3. Roll convention — proxy by checking for any single-bar price jumps >5% on either feed
    # in the overlap. CFD continuous-front-month rolls usually show as a small back-adjusted
    # gap, but a non-back-adjusted contract roll shows as a large discontinuity.
    big_jumps_o = (common["ret_o"].abs() > 0.05).sum()
    big_jumps_p = (common["ret_p"].abs() > 0.05).sum()
    out["big_bar_jumps_oanda"] = int(big_jumps_o)
    out["big_bar_jumps_pepperstone"] = int(big_jumps_p)
    out["roll_convention_pass"] = abs(int(big_jumps_o) - int(big_jumps_p)) <= 2

    # 4. Holiday cross-tab — bars present per UTC date
    bars_per_day_o = oanda.groupby(oanda["time_utc"].dt.date).size()
    bars_per_day_p = pep.groupby(pep["time_utc"].dt.date).size()
    days_only_o = set(bars_per_day_o.index) - set(bars_per_day_p.index)
    days_only_p = set(bars_per_day_p.index) - set(bars_per_day_o.index)
    out["days_oanda_only"] = sorted(str(d) for d in days_only_o)
    out["days_pepperstone_only"] = sorted(str(d) for d in days_only_p)

    # 5. Spread profile — informational. We don't have bid/ask in either feed (we're using
    # mid/close), so we report the high-low range per bin as a proxy for the bin's typical
    # excursion. Real spread comparison requires BA pricing, out of scope for this gate.
    common["range_o"] = common["high_o"] - common["low_o"]
    common["range_p"] = common["high_p"] - common["low_p"]
    range_by_bin = common.groupby("bin").agg(
        median_range_o=("range_o", "median"),
        median_range_p=("range_p", "median"),
    ).to_dict("index")
    out["bin_range_profile"] = {int(b): {k: float(v) for k, v in d.items()} for b, d in range_by_bin.items()}

    out["overall_pass"] = (
        out["alignment_pass"]
        and out["correlation_pass"]
        and out["roll_convention_pass"]
    )

    return out


def _write_report(diag: dict, oanda_path_label: str, pep_path: pathlib.Path) -> None:
    FINDINGS_DIR.mkdir(parents=True, exist_ok=True)
    verdict = "PASS" if diag["overall_pass"] else "FAIL"
    lines = []
    lines.append(f"# USOIL feed reconciliation (OANDA <-> Pepperstone) — Stage 0")
    lines.append("")
    lines.append(f"**Verdict:** {verdict}")
    lines.append("")
    lines.append(f"**Loop:** USOIL 15min behavioral characterization (2026-05-02)")
    lines.append(f"**Brief:** §3 Stage 0 (mandatory feed-equivalence pre-check)")
    lines.append(f"**Plan:** `~/.claude/plans/usoil-15min-behavioral-composed-tower.md`")
    lines.append("")
    lines.append("## Sources")
    lines.append("")
    lines.append(f"- **OANDA:** {OANDA_INSTRUMENT} {GRANULARITY} via `lib.oanda.fetch_candles`")
    lines.append(f"- **Pepperstone:** `{pep_path.relative_to(REPO_ROOT)}`")
    lines.append(f"- **OANDA pull window:** {OVERLAP_START} -> {OVERLAP_END}")
    lines.append(f"- **Intersection of feed coverage:** {diag['intersection_start']} -> {diag['intersection_end']}")
    lines.append(f"- **Common bars (within intersection):** {diag['overlap_bars']:,}")
    lines.append(f"  - OANDA bars in intersection: {diag['oanda_bars_in_intersection']:,}")
    lines.append(f"  - Pepperstone bars in intersection: {diag['pepperstone_bars_in_intersection']:,}")
    lines.append(f"  - OANDA-only bars within intersection: {diag['oanda_only_bars_in_intersection']:,}")
    lines.append(f"  - Pepperstone-only bars within intersection: {diag['pepperstone_only_bars_in_intersection']:,}")
    lines.append(f"  - OANDA bars OUTSIDE intersection (corpus envelope, informational): {diag['oanda_outside_intersection']:,}")
    lines.append(f"  - Pepperstone bars OUTSIDE intersection (corpus envelope, informational): {diag['pepperstone_outside_intersection']:,}")
    lines.append("")
    lines.append("## 1. Bar-timestamp alignment (within intersection of feed coverage)")
    lines.append(f"- bar_drift_pct: {diag['bar_drift_pct']:.4f}% (acceptable < 1%)")
    lines.append(f"- alignment_pass: **{diag['alignment_pass']}**")
    lines.append("")
    lines.append(f"## 2. Return correlation per 15min bin (Spearman rho >= {CORRELATION_FLOOR})")
    lines.append(f"- bins_below_floor: {len(diag['bins_below_floor'])} of {len(diag['return_correlation_per_bin'])} populated bins")
    if diag["bins_below_floor"]:
        lines.append("")
        lines.append("| bin (15min idx) | rho | n |")
        lines.append("|---:|---:|---:|")
        for fb in diag["bins_below_floor"]:
            lines.append(f"| {fb['bin']} | {fb['rho']:.4f} | {fb['n']} |")
    lines.append(f"- correlation_pass: **{diag['correlation_pass']}**")
    lines.append("")
    lines.append("## 3. Roll convention (proxy: single-bar |ret| > 5%)")
    lines.append(f"- big_bar_jumps_oanda: {diag['big_bar_jumps_oanda']}")
    lines.append(f"- big_bar_jumps_pepperstone: {diag['big_bar_jumps_pepperstone']}")
    lines.append(f"- roll_convention_pass: **{diag['roll_convention_pass']}**")
    lines.append("")
    lines.append("## 4. Holiday calendar cross-tab")
    lines.append(f"- days_oanda_only: {len(diag['days_oanda_only'])}")
    if diag["days_oanda_only"][:10]:
        lines.append(f"  - first 10: {diag['days_oanda_only'][:10]}")
    lines.append(f"- days_pepperstone_only: {len(diag['days_pepperstone_only'])}")
    if diag["days_pepperstone_only"][:10]:
        lines.append(f"  - first 10: {diag['days_pepperstone_only'][:10]}")
    lines.append("")
    lines.append("## 5. Bar-range profile by 15min bin (informational)")
    lines.append("")
    lines.append("Used as a proxy for spread comparison since neither feed contains BA pricing.")
    lines.append("Report only top-10 highest-divergence bins.")
    lines.append("")
    lines.append("| bin | median_range_oanda | median_range_pepperstone | ratio (p/o) |")
    lines.append("|---:|---:|---:|---:|")
    sorted_bins = sorted(
        diag["bin_range_profile"].items(),
        key=lambda kv: abs(kv[1]["median_range_p"] / max(kv[1]["median_range_o"], 1e-9) - 1.0),
        reverse=True,
    )[:10]
    for b, d in sorted_bins:
        ratio = d["median_range_p"] / max(d["median_range_o"], 1e-9)
        lines.append(f"| {b} | {d['median_range_o']:.4f} | {d['median_range_p']:.4f} | {ratio:.3f} |")
    lines.append("")
    lines.append("## Stop rule outcome")
    lines.append("")
    if diag["overall_pass"]:
        lines.append("All three load-bearing diagnostics (alignment, correlation, roll convention) PASS.")
        lines.append("Proceed to Stage B (Phase 1 fetch + clean + verify).")
    else:
        lines.append("**One or more load-bearing diagnostics FAILED.** Stage 0 stop rule fires.")
        lines.append("")
        lines.append("Resolve the divergence (re-symbol, re-bound, re-pull) before Phase 1 proceeds.")
        lines.append("If unresolvable, escalate to a separate methodology loop on feed-equivalence.")
        lines.append("")
        lines.append("Audit hook: `docs/methodology/gate_audits/2026-05-02_usoil_characterization.md`")
        lines.append("must be authored before any Phase 1 work.")
    lines.append("")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Stage 0 report: {OUT_MD}")
    print(f"Stage 0 verdict: {verdict}")


def main() -> int:
    print(f"Stage 0 reconciliation: USOIL OANDA <-> Pepperstone")
    pep_path = _find_pepperstone_csv()
    print(f"Stage 0: Pepperstone CSV = {pep_path.name}")
    pep = _load_pepperstone(pep_path)
    print(f"Stage 0: Pepperstone {len(pep):,} bars, {pep['time_utc'].iloc[0]} -> {pep['time_utc'].iloc[-1]}")
    oanda = _fetch_oanda_overlap()
    diag = _diagnostics(oanda, pep)
    _write_report(diag, OANDA_INSTRUMENT, pep_path)
    return 0 if diag["overall_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
