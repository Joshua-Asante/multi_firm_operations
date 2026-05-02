"""Phase 1 — USOIL M15 OANDA fetch.

Brief: 2026-05-02 USOIL 15min behavioral characterization.
Plan: ~/.claude/plans/usoil-15min-behavioral-composed-tower.md (Stage B step 8).

Endpoint: practice (101-prefix account); selected by lib.oanda.fetch_candles
          via the account-ID prefix recognition.
Auth: ~/.keys/oanda.txt via lib.oanda_creds.
Pricing: M (mid). USOIL Phase 1 characterization is descriptive-stats only;
         spread treatment is via the Alchemy reference in phase1_characterize,
         not via OANDA bid/ask.
Granularity: M15. Window: 2022-01-04 -> 2026-04-20 (UTC), 52-month panel
            matching portfolio MC calibration.

Output: data/bar_data/USOIL_oanda_m15_2022-01-04_to_2026-04-20_raw.csv
        Columns: time, open, high, low, close, volume
        (matches existing data/bar_data/{XAUUSD,USDJPY,US30USD}.csv schema)

Symbol locked at 2026-05-02 via probe: WTICO_USD.
"""
from __future__ import annotations

import csv
import hashlib
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from lib.oanda import fetch_candles  # noqa: E402

INSTRUMENT = "WTICO_USD"
GRANULARITY = "M15"
PRICE = "M"
START_ISO = "2022-01-04T00:00:00Z"
END_ISO = "2026-04-20T00:00:00Z"

OUT_DIR = REPO_ROOT / "data" / "bar_data"
HASH_DIR = REPO_ROOT / "data"
OUT_RAW = OUT_DIR / "USOIL_oanda_m15_2022-01-04_to_2026-04-20_raw.csv"
OUT_HASH = HASH_DIR / "USOIL_oanda_m15_2022-01-04_to_2026-04-20_raw.sha256"

FIELDS = ["time", "open", "high", "low", "close", "volume"]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    HASH_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Phase 1 fetch: {INSTRUMENT} {GRANULARITY} {START_ISO} -> {END_ISO}")
    rows = []
    for c in fetch_candles(INSTRUMENT, START_ISO, END_ISO, granularity=GRANULARITY, price=PRICE):
        rows.append(c)
        if len(rows) % 10000 == 0:
            print(f"  fetched {len(rows):,} candles, last={c['time']}")

    if not rows:
        print("FAIL: zero candles returned from OANDA")
        return 1

    print(f"Phase 1 fetch: total candles = {len(rows):,}")
    print(f"  first = {rows[0]['time']}")
    print(f"  last  = {rows[-1]['time']}")

    with OUT_RAW.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in FIELDS})

    h = hashlib.sha256()
    with OUT_RAW.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    digest = h.hexdigest()
    OUT_HASH.write_text(f"{digest}  {OUT_RAW.name}\n")

    print(f"raw csv:    {OUT_RAW}")
    print(f"raw sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
