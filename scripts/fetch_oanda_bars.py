"""Fetch OANDA M15 candles and write to data/bar_data/<NAME>.csv.

Thin shell over lib/oanda.fetch_candles (oandapyV20 SDK). Auth via
lib/oanda_creds.load() (~/.keys/oanda.txt) — endpoint (practice vs live)
selected from the account-ID prefix.

Behavior change vs the prior urllib version: previously read the OANDA
token from env var `OANDA` and hard-coded the practice host. Now uses
~/.keys/oanda.txt for both token and account ID, and selects host from
account prefix (101 → practice, 001 → live). Output schema and on-disk
location are unchanged.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from lib.oanda import fetch_candles


GRANULARITY = "M15"
PRICE = "M"  # midpoint OHLC

# (output_filename_stem, OANDA instrument code)
INSTRUMENTS = [
    ("USDJPY", "USD_JPY"),
    ("XAUUSD", "XAU_USD"),
    ("US30USD", "US30_USD"),
]

START = "2022-01-01T00:00:00Z"
END = "2026-04-20T00:00:00Z"

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "bar_data"


def main() -> int:
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
            for row in fetch_candles(instrument, START, END,
                                     granularity=GRANULARITY, price=PRICE):
                writer.writerow(row)
                n += 1
        print(f"=== {instrument}: wrote {n} rows ===", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
