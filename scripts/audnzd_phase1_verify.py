"""Phase 1.3 verification of the AUDNZD raw CSV.

Runs all checks the brief specifies:
  - bar count in [100k, 160k]
  - weekend gaps in [200, 240] (gaps > 60 min between consecutive bars)
  - spread sanity (median < 3 pips, p99 < 15 pips)
  - OHLC integrity (high >= low, high >= close, low <= close, both bid and ask)
  - 'complete' field tally (sanity check that complete=false rows are limited
    to the trailing edge of the dataset)

External-cross-reference (TradingView/Dukascopy match within 2 pips at three
dates) is performed in audnzd_phase1_xref.py — kept separate because it
requires a second data source and is the gating step.
"""
from __future__ import annotations

import csv
import pathlib
import sys
from datetime import datetime, timedelta

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW_CSV = REPO_ROOT / "data" / "audnzd_oanda_m15_2022-01-01_to_2026-04-26_raw.csv"


def parse_iso(s: str) -> datetime:
    # OANDA returns nanosecond precision; truncate to microseconds for fromisoformat
    s = s.replace("Z", "+00:00")
    if "." in s:
        head, frac = s.rsplit(".", 1)
        # frac like '000000000+00:00' -> need to truncate fractional digits to <=6
        if "+" in frac:
            digits, tz = frac.split("+", 1)
            digits = digits[:6]
            s = f"{head}.{digits}+{tz}"
        elif "-" in frac and frac.find("-") > 0:
            digits, tz = frac.split("-", 1)
            digits = digits[:6]
            s = f"{head}.{digits}-{tz}"
    return datetime.fromisoformat(s)


def main() -> int:
    if not RAW_CSV.exists():
        print(f"FAIL: missing raw CSV at {RAW_CSV}")
        return 1

    rows = []
    with RAW_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    n = len(rows)
    print(f"bar_count: {n}")
    bar_ok = 100_000 <= n <= 160_000
    print(f"  range_check [100000,160000]: {'PASS' if bar_ok else 'FAIL'}")

    # Parse times once
    times = [parse_iso(r["datetime_utc"]) for r in rows]

    # Weekend gap check: gaps > 60 min between consecutive bars
    gaps_min = []
    for i in range(1, n):
        delta = (times[i] - times[i - 1]).total_seconds() / 60.0
        gaps_min.append(delta)
    weekend_gaps = [g for g in gaps_min if g > 60]
    print(f"weekend_gaps (>60 min): {len(weekend_gaps)}")
    wg_ok = 200 <= len(weekend_gaps) <= 240
    print(f"  range_check [200,240]: {'PASS' if wg_ok else 'FAIL'}")
    if gaps_min:
        # quick percentile
        sg = sorted(gaps_min)
        median_gap = sg[len(sg) // 2]
        max_gap = sg[-1]
        print(f"  median_gap_min={median_gap:.2f} max_gap_min={max_gap:.2f}")

    # Spread profile
    spreads_pips = []
    for r in rows:
        try:
            cb = float(r["close_bid"])
            ca = float(r["close_ask"])
            spreads_pips.append((ca - cb) * 10000.0)
        except (TypeError, ValueError):
            continue
    spreads_pips.sort()
    if spreads_pips:
        med = spreads_pips[len(spreads_pips) // 2]
        p99 = spreads_pips[int(len(spreads_pips) * 0.99)]
        smin = spreads_pips[0]
        smax = spreads_pips[-1]
        print(f"spread_pips: median={med:.3f} p99={p99:.3f} min={smin:.3f} max={smax:.3f}")
        sp_med_ok = med < 3.0
        sp_p99_ok = p99 < 15.0
        print(f"  median<3.0 : {'PASS' if sp_med_ok else 'FAIL'}")
        print(f"  p99<15.0   : {'PASS' if sp_p99_ok else 'FAIL'}")
    else:
        sp_med_ok = sp_p99_ok = False
        print("spread_pips: no parseable spreads")

    # OHLC integrity (bid + ask)
    bad_bid_hl = bad_bid_hc = bad_bid_lc = 0
    bad_ask_hl = bad_ask_hc = bad_ask_lc = 0
    for r in rows:
        try:
            obh, obl, obc = float(r["high_bid"]), float(r["low_bid"]), float(r["close_bid"])
            oah, oal, oac = float(r["high_ask"]), float(r["low_ask"]), float(r["close_ask"])
        except (TypeError, ValueError):
            continue
        if obh < obl: bad_bid_hl += 1
        if obh < obc: bad_bid_hc += 1
        if obl > obc: bad_bid_lc += 1
        if oah < oal: bad_ask_hl += 1
        if oah < oac: bad_ask_hc += 1
        if oal > oac: bad_ask_lc += 1
    ohlc_ok = (bad_bid_hl + bad_bid_hc + bad_bid_lc + bad_ask_hl + bad_ask_hc + bad_ask_lc) == 0
    print(
        f"ohlc_integrity: bid(hl={bad_bid_hl} hc={bad_bid_hc} lc={bad_bid_lc}) "
        f"ask(hl={bad_ask_hl} hc={bad_ask_hc} lc={bad_ask_lc}) "
        f"=> {'PASS' if ohlc_ok else 'FAIL'}"
    )

    # complete flag tally
    completes = sum(1 for r in rows if str(r.get("complete", "")).lower() == "true")
    incompletes = n - completes
    print(f"complete=true: {completes}  complete!=true: {incompletes}")

    # Position of incomplete rows (should be at the trailing edge)
    incomplete_indices = [i for i, r in enumerate(rows) if str(r.get("complete", "")).lower() != "true"]
    if incomplete_indices:
        first = incomplete_indices[0]
        last = incomplete_indices[-1]
        print(
            f"  incomplete_pos: first_idx={first} last_idx={last} "
            f"first_time={rows[first]['datetime_utc']} last_time={rows[last]['datetime_utc']}"
        )

    # NaN OHLC count (any of the 8 OHLC fields missing or non-numeric)
    nan_ohlc = 0
    for r in rows:
        try:
            for k in ("open_bid","high_bid","low_bid","close_bid","open_ask","high_ask","low_ask","close_ask"):
                float(r[k])
        except (TypeError, ValueError, KeyError):
            nan_ohlc += 1
    print(f"nan_ohlc_rows: {nan_ohlc}")

    # zero-volume tally (do not auto-delete; surface for review)
    zero_vol = sum(1 for r in rows if str(r.get("volume", "")).strip() in ("0", ""))
    print(f"zero_volume_rows: {zero_vol}")

    # Window endpoints
    print(f"first_bar_utc: {rows[0]['datetime_utc']}")
    print(f"last_bar_utc:  {rows[-1]['datetime_utc']}")

    # Overall verdict on programmatic checks
    all_ok = bar_ok and wg_ok and sp_med_ok and sp_p99_ok and ohlc_ok and nan_ohlc == 0
    print()
    print(f"PROGRAMMATIC_VERIFICATION: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
