"""Fetch OANDA M15 candles and write to data/bar_data/<NAME>.csv.

Uses urllib (stdlib) to avoid requiring `requests`. Paginates with
`from` + `count=5000` (OANDA's per-request cap), advancing from the
last candle's timestamp + 1 second on each iteration.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_HOST = "https://api-fxpractice.oanda.com"
GRANULARITY = "M15"
PRICE = "M"  # midpoint OHLC
COUNT = 5000  # OANDA per-request cap

# (output_filename_stem, OANDA instrument code)
INSTRUMENTS = [
    ("USDJPY", "USD_JPY"),
    ("XAUUSD", "XAU_USD"),
    ("US30USD", "US30_USD"),
]

START = "2022-01-01T00:00:00Z"
END = "2026-04-20T00:00:00Z"

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "bar_data"


def _iso_to_epoch(s: str) -> float:
    # OANDA returns RFC3339 with nanoseconds, e.g. 2022-01-02T22:00:00.000000000Z
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    # Truncate fractional to microseconds for fromisoformat compatibility
    if "." in s:
        head, frac_tz = s.split(".", 1)
        # frac_tz like "000000000+00:00"
        if "+" in frac_tz:
            frac, tz = frac_tz.split("+", 1)
            tz = "+" + tz
        elif "-" in frac_tz:
            frac, tz = frac_tz.split("-", 1)
            tz = "-" + tz
        else:
            frac, tz = frac_tz, ""
        frac = frac[:6]
        s = f"{head}.{frac}{tz}"
    return datetime.fromisoformat(s).timestamp()


def _epoch_to_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_candles(token: str, instrument: str, start_iso: str, end_iso: str):
    end_epoch = _iso_to_epoch(end_iso)
    cursor_iso = start_iso
    last_ts_seen = None
    total = 0

    while True:
        params = {
            "granularity": GRANULARITY,
            "price": PRICE,
            "count": COUNT,
            "from": cursor_iso,
            "includeFirst": "true" if last_ts_seen is None else "false",
        }
        url = f"{API_HOST}/v3/instruments/{instrument}/candles?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})

        attempt = 0
        while True:
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                # Retry on 429/5xx
                if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                    sleep_s = 2 ** attempt
                    print(f"  HTTP {e.code}, retry in {sleep_s}s", file=sys.stderr)
                    time.sleep(sleep_s)
                    attempt += 1
                    continue
                raise

        candles = body.get("candles", [])
        raw_count = len(candles)
        if not candles:
            break

        kept = 0
        for c in candles:
            t_iso = c["time"]
            t_epoch = _iso_to_epoch(t_iso)
            if t_epoch >= end_epoch:
                # Past end — stop entirely
                yield from ()  # no-op
                return
            if not c.get("complete", False):
                # skip in-progress candle
                continue
            mid = c["mid"]
            yield {
                "time": t_iso,
                "open": mid["o"],
                "high": mid["h"],
                "low": mid["l"],
                "close": mid["c"],
                "volume": c.get("volume", 0),
            }
            last_ts_seen = t_epoch
            kept += 1
            total += 1

        if last_ts_seen is None:
            # Got a page but everything was incomplete; advance by 15min*5000 to avoid loop
            cursor_epoch = _iso_to_epoch(cursor_iso) + 15 * 60 * COUNT
            cursor_iso = _epoch_to_iso(cursor_epoch)
        else:
            cursor_iso = _epoch_to_iso(last_ts_seen + 1)

        print(f"  page: kept={kept} total={total} next_from={cursor_iso}", file=sys.stderr)

        if last_ts_seen is not None and last_ts_seen + 1 >= end_epoch:
            break
        # OANDA returns up to `count` candles; with includeFirst=false it returns
        # `count - 1`. So a short page is NOT a reliable EOF signal — only an
        # empty page is. We terminate via the empty-page check at the top of the
        # next iteration, or when no NEW candles were yielded this page.
        if kept == 0:
            break


def main() -> int:
    token = os.environ.get("OANDA")
    if not token:
        print("ERROR: OANDA env var not set", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for stem, instrument in INSTRUMENTS:
        out_path = OUT_DIR / f"{stem}.csv"
        print(f"=== {instrument} -> {out_path} ===", file=sys.stderr)
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["time", "open", "high", "low", "close", "volume"]
            )
            writer.writeheader()
            n = 0
            for row in fetch_candles(token, instrument, START, END):
                writer.writerow(row)
                n += 1
        print(f"=== {instrument}: wrote {n} rows ===", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
