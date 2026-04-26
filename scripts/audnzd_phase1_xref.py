"""Phase 1.3 external cross-reference — Dukascopy vs OANDA for three M15 closes.

Brief: confirm OANDA closes match a second source within 2 pips at:
  2024-08-05 (yen-carry-unwind day)
  2025-04-02 (RBA decision day)
  2026-01-15 (quiet day baseline)

Each date is checked at 16:00 UTC = London close (consistent across DST regimes).
The M15 bar starting at 15:45 UTC closes at 16:00 UTC, so we compare:
  - OANDA: close_bid / close_ask of the bar whose datetime_utc starts at 15:45 UTC
  - Dukascopy: last tick in the hour file 15h_ticks.bi5 for that date
                (= the tick immediately preceding 16:00 UTC)

Dukascopy bi5 format: LZMA-compressed; each tick = 20 bytes big-endian:
  uint32 ms_offset_in_hour, uint32 ask*1e5, uint32 bid*1e5,
  float32 ask_vol_millions, float32 bid_vol_millions.
URL: https://datafeed.dukascopy.com/datafeed/{INSTR}/{YYYY}/{MM-1:02d}/{DD:02d}/{HH:02d}h_ticks.bi5
"""
from __future__ import annotations

import csv
import lzma
import pathlib
import struct
import sys
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW_CSV = REPO_ROOT / "data" / "audnzd_oanda_m15_2022-01-01_to_2026-04-26_raw.csv"

# (year, month_1_indexed, day, hour_utc) — the hour file containing 16:00 UTC close
DATES = [
    (2024, 8, 5, 15, "yen-carry-unwind"),
    (2025, 4, 2, 15, "RBA decision day"),
    (2026, 1, 15, 15, "quiet day baseline"),
]
TOLERANCE_PIPS = 2.0
DUKAS_BASE = "https://datafeed.dukascopy.com/datafeed/AUDNZD"


def fetch_duka_hour(year: int, month: int, day: int, hour: int, max_attempts: int = 5) -> bytes:
    import time
    url = f"{DUKAS_BASE}/{year:04d}/{month-1:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except Exception as e:
            last_err = e
            if attempt < max_attempts:
                time.sleep(2 + attempt * 2)
    raise RuntimeError(f"dukascopy fetch failed after {max_attempts} attempts: {last_err}")


def decode_bi5(data: bytes) -> list[tuple[int, float, float]]:
    """Return list of (ms_offset, ask, bid) decoded from a Dukascopy bi5 file."""
    if not data:
        return []
    raw = lzma.decompress(data)
    ticks = []
    for i in range(0, len(raw), 20):
        chunk = raw[i:i + 20]
        if len(chunk) != 20:
            break
        ms, ask_i, bid_i = struct.unpack(">III", chunk[:12])
        ticks.append((ms, ask_i / 100000.0, bid_i / 100000.0))
    return ticks


def find_oanda_close(rows: list[dict], date_str: str) -> dict | None:
    """Find the OANDA bar with datetime_utc == {date}T15:45:00... (the bar that closes at 16:00)."""
    target_prefix = f"{date_str}T15:45:00"
    for r in rows:
        if r["datetime_utc"].startswith(target_prefix):
            return r
    return None


def main() -> int:
    if not RAW_CSV.exists():
        print(f"FAIL: missing raw CSV at {RAW_CSV}")
        return 1

    rows = []
    with RAW_CSV.open(newline="", encoding="utf-8") as f:
        rows.extend(csv.DictReader(f))

    print(f"OANDA rows loaded: {len(rows)}")
    print(f"Tolerance: {TOLERANCE_PIPS} pips on mid-price")
    print()

    overall_ok = True
    results = []

    for year, month, day, hour, tag in DATES:
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        print(f"=== {date_str} ({tag}) ===")

        # OANDA side
        oanda_row = find_oanda_close(rows, date_str)
        if oanda_row is None:
            print(f"  OANDA: NO BAR at {date_str}T15:45:00 — investigate")
            overall_ok = False
            results.append((date_str, tag, None, None, None, "no oanda bar"))
            continue
        cb = float(oanda_row["close_bid"])
        ca = float(oanda_row["close_ask"])
        oanda_mid = (cb + ca) / 2.0
        print(f"  OANDA bar 15:45-16:00 UTC: bid={cb:.5f} ask={ca:.5f} mid={oanda_mid:.5f}")

        # Dukascopy side
        try:
            data = fetch_duka_hour(year, month, day, hour)
        except Exception as e:
            print(f"  Dukascopy fetch failed: {type(e).__name__}: {e}")
            results.append((date_str, tag, oanda_mid, None, None, f"duka_fetch_err:{e}"))
            overall_ok = False
            continue

        ticks = decode_bi5(data)
        if not ticks:
            print(f"  Dukascopy: empty/no ticks in hour file ({len(data)} bytes raw)")
            results.append((date_str, tag, oanda_mid, None, None, "duka_empty"))
            overall_ok = False
            continue

        # Last tick in the hour = closest to 16:00 UTC = M15 close
        last_ms, last_ask, last_bid = ticks[-1]
        duka_mid = (last_ask + last_bid) / 2.0
        diff_pips = abs(oanda_mid - duka_mid) * 10000.0
        verdict = "PASS" if diff_pips <= TOLERANCE_PIPS else "FAIL"
        if verdict == "FAIL":
            overall_ok = False

        print(
            f"  Dukascopy last tick @ {last_ms/1000.0:.2f}s into {hour:02d}:00 UTC: "
            f"bid={last_bid:.5f} ask={last_ask:.5f} mid={duka_mid:.5f} "
            f"(n_ticks={len(ticks)})"
        )
        print(f"  diff_mid_pips={diff_pips:.3f}  -> {verdict}")
        results.append((date_str, tag, oanda_mid, duka_mid, diff_pips, verdict))
        print()

    print("=" * 60)
    print("Summary:")
    for date_str, tag, om, dm, dp, v in results:
        if om is None:
            print(f"  {date_str} ({tag}): {v}")
        elif dm is None:
            print(f"  {date_str} ({tag}): OANDA mid={om:.5f}  Dukascopy=N/A  ({v})")
        else:
            print(f"  {date_str} ({tag}): OANDA={om:.5f}  Duka={dm:.5f}  diff={dp:.3f}p  {v}")
    print()
    print(f"XREF_VERDICT: {'PASS' if overall_ok else 'FAIL'}")
    return 0 if overall_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
