"""Phase 1 — AUDNZD M15 OANDA fetch (live endpoint).

Brief: 2026-04-26 AUDNZD candidate-strategy discovery (loop_2026-04-26_audnzd_discovery).
Out of scope: any modification of locked production code.

Endpoint: api-fxpractice.oanda.com (practice — live unavailable, deviation
authorized 2026-04-26; cross-reference check at 3 dates is the empirical guard).
Auth: bearer token loaded from ~/.keys/oanda.txt via lib.oanda_creds.
Pricing: BA (bid+ask both columns, never collapsed to mid).
Granularity: M15. Window: 2022-01-01 -> 2026-04-26 (UTC).
Alignment: dailyAlignment=17, alignmentTimezone=America/New_York
           (NY-close convention, matches Pepperstone/portfolio comparability).
"""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# Repo root on path so we can import lib.*
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from lib.oanda_creds import load as load_oanda_creds  # noqa: E402

START_ISO = "2022-01-01T00:00:00Z"
END_ISO = "2026-04-26T00:00:00Z"
INSTRUMENT = "AUD_NZD"
GRANULARITY = "M15"
PRICE = "BA"
DAILY_ALIGNMENT = 17
ALIGNMENT_TZ = "America/New_York"
COUNT_PER_REQUEST = 5000
REQUEST_DELAY_S = 0.2
RETRY_DELAY_S = 3.0
MAX_RETRIES = 3

OUT_DIR = REPO_ROOT / "data"
OUT_RAW = OUT_DIR / "audnzd_oanda_m15_2022-01-01_to_2026-04-26_raw.csv"
OUT_HASH = OUT_DIR / "audnzd_oanda_m15_2022-01-01_to_2026-04-26_raw.sha256"

FIELDS = [
    "datetime_utc", "datetime_ny",
    "open_bid", "high_bid", "low_bid", "close_bid",
    "open_ask", "high_ask", "low_ask", "close_ask",
    "volume", "complete",
]


def fetch_page(token: str, from_iso: str, count: int) -> dict:
    base = f"https://api-fxpractice.oanda.com/v3/instruments/{INSTRUMENT}/candles"
    params = {
        "granularity": GRANULARITY,
        "price": PRICE,
        "count": str(count),
        "from": from_iso,
        "smooth": "false",
        "dailyAlignment": str(DAILY_ALIGNMENT),
        "alignmentTimezone": ALIGNMENT_TZ,
        "includeFirst": "true",
    }
    url = f"{base}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept-Datetime-Format": "RFC3339",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    token, _account = load_oanda_creds()

    end_dt = parse_iso(END_ISO)
    cursor_iso = START_ISO
    last_time: str | None = None
    rows: list[dict] = []
    page = 0
    ny_tz = ZoneInfo("America/New_York")

    while True:
        page += 1
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                data = fetch_page(token, cursor_iso, COUNT_PER_REQUEST)
                break
            except Exception as e:
                sys.stderr.write(
                    f"page {page} attempt {attempt} failed at cursor {cursor_iso}: {e}\n"
                )
                if attempt == MAX_RETRIES:
                    raise
                time.sleep(RETRY_DELAY_S * attempt)
        else:
            raise SystemExit(f"page {page} exhausted retries")

        candles = data.get("candles", [])
        if not candles:
            sys.stderr.write(f"page {page}: empty response, stopping\n")
            break

        added = 0
        page_last_time: str | None = None
        for c in candles:
            t = c["time"]
            if t == last_time:
                continue
            t_dt = parse_iso(t)
            if t_dt >= end_dt:
                page_last_time = t
                break
            bid = c.get("bid", {})
            ask = c.get("ask", {})
            rows.append({
                "datetime_utc": t,
                "datetime_ny": t_dt.astimezone(ny_tz).isoformat(),
                "open_bid": bid.get("o"),
                "high_bid": bid.get("h"),
                "low_bid": bid.get("l"),
                "close_bid": bid.get("c"),
                "open_ask": ask.get("o"),
                "high_ask": ask.get("h"),
                "low_ask": ask.get("l"),
                "close_ask": ask.get("c"),
                "volume": c.get("volume"),
                "complete": c.get("complete"),
            })
            last_time = t
            page_last_time = t
            added += 1

        sys.stderr.write(
            f"page {page}: candles={len(candles)} added={added} total={len(rows)} "
            f"last={page_last_time}\n"
        )

        # Termination conditions
        if page_last_time is None:
            break
        page_last_dt = parse_iso(page_last_time)
        if page_last_dt >= end_dt:
            break
        # Short page = we caught up (likely current/incomplete tail)
        if len(candles) < COUNT_PER_REQUEST:
            break

        # Advance cursor past last candle (avoids the boundary-duplicate even though we dedup)
        cursor_iso = (page_last_dt + timedelta(seconds=1)).isoformat().replace(
            "+00:00", "Z"
        )
        time.sleep(REQUEST_DELAY_S)

    # Write CSV
    with OUT_RAW.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    # SHA256
    h = hashlib.sha256()
    with OUT_RAW.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    digest = h.hexdigest()
    OUT_HASH.write_text(f"{digest}  {OUT_RAW.name}\n")

    print(f"rows={len(rows)} pages={page} sha256={digest} path={OUT_RAW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
