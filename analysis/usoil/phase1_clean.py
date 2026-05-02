"""Phase 1 — USOIL M15 cleaning + maintenance/holiday tagging.

Brief: 2026-05-02 USOIL 15min behavioral characterization.
Plan: ~/.claude/plans/usoil-15min-behavioral-composed-tower.md (Stage B step 9).

Permitted deletions per Pre-Q gate:
  D1: maintenance-window bars — TAGGED, RETAINED. Excluded only from
      return-distribution stats downstream. The Pre-Q gate explicitly
      forbids deleting them outright; we tag and let phase1_characterize
      decide per-stat.

Tags appended (no rows dropped vs raw):
  - is_maintenance: bar timestamp falls in 17:00-17:45 ET (CME Globex daily
                    settlement halt window for energy products), Mon-Fri.
                    Tagged regardless of whether OANDA returned a candle —
                    OANDA's CFD feed may or may not honor the underlying
                    halt; the tag is a clock-time rule, not a feed artefact
                    detector.
  - is_holiday_short: UTC trading day with substantially fewer bars than
                    expected (~92 bars/day for 23h session). Threshold: <80.
                    Catches Christmas Eve / day-after-Thanksgiving / etc.
  - dt_ny: chart-TZ (America/New_York, DST-aware) ISO timestamp.

D-test for D1: known measurement artefact with documented cause (CME daily
              settlement halt). Permitted per Pre-Q gate §1.

Output: data/bar_data/USOIL_oanda_m15_2022-01-04_to_2026-04-20_clean.csv
        Columns: time, open, high, low, close, volume,
                 dt_ny, is_maintenance, is_holiday_short
"""
from __future__ import annotations

import csv
import hashlib
import pathlib
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
RAW_CSV = DATA_DIR / "bar_data" / "USOIL_oanda_m15_2022-01-04_to_2026-04-20_raw.csv"
CLEAN_CSV = DATA_DIR / "bar_data" / "USOIL_oanda_m15_2022-01-04_to_2026-04-20_clean.csv"
CLEAN_HASH = DATA_DIR / "USOIL_oanda_m15_2022-01-04_to_2026-04-20_clean.sha256"

NY_TZ = ZoneInfo("America/New_York")

# CME Globex daily energy maintenance: 17:00-18:00 ET. Four 15min bars.
MAINTENANCE_HOURS_ET = {17}  # 17:00, 17:15, 17:30, 17:45 ET

# Holiday-short threshold: any UTC date with fewer bars than this is flagged.
# 23h session × 4 bars/h = 92 expected. Half-days run ~40-50 bars.
HOLIDAY_SHORT_THRESHOLD = 80


def _parse_oanda_ts(s: str) -> datetime:
    """OANDA ns-precision RFC3339 -> tz-aware UTC datetime."""
    s = s.replace("Z", "+00:00")
    if "." in s:
        head, frac = s.split(".", 1)
        if "+" in frac:
            digits, tz = frac.split("+", 1)
            digits = digits[:6]
            s = f"{head}.{digits}+{tz}"
    return datetime.fromisoformat(s)


def main() -> int:
    if not RAW_CSV.exists():
        print(f"FAIL: missing raw CSV {RAW_CSV}")
        return 1

    rows = []
    with RAW_CSV.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)

    print(f"Phase 1 clean: read {len(rows):,} raw rows")

    # First pass: parse timestamps, derive NY hour, count bars per UTC date
    bars_per_utc_date: dict = {}
    parsed = []
    for r in rows:
        ts_utc = _parse_oanda_ts(r["time"])
        ts_ny = ts_utc.astimezone(NY_TZ)
        utc_date = ts_utc.date()
        bars_per_utc_date[utc_date] = bars_per_utc_date.get(utc_date, 0) + 1
        parsed.append((ts_utc, ts_ny, r))

    # Second pass: tag and write
    n_maint = 0
    n_holiday = 0
    out_rows = []
    for ts_utc, ts_ny, r in parsed:
        is_maint = (ts_ny.hour in MAINTENANCE_HOURS_ET) and (ts_ny.weekday() < 5)
        is_holiday = bars_per_utc_date[ts_utc.date()] < HOLIDAY_SHORT_THRESHOLD
        if is_maint:
            n_maint += 1
        if is_holiday:
            n_holiday += 1
        out_rows.append({
            "time": r["time"],
            "open": r["open"],
            "high": r["high"],
            "low": r["low"],
            "close": r["close"],
            "volume": r["volume"],
            "dt_ny": ts_ny.isoformat(),
            "is_maintenance": "true" if is_maint else "false",
            "is_holiday_short": "true" if is_holiday else "false",
        })

    fields = ["time", "open", "high", "low", "close", "volume",
              "dt_ny", "is_maintenance", "is_holiday_short"]
    with CLEAN_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    h = hashlib.sha256()
    with CLEAN_CSV.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    digest = h.hexdigest()
    CLEAN_HASH.write_text(f"{digest}  {CLEAN_CSV.name}\n")

    print(f"Phase 1 clean: out_rows={len(out_rows):,} (no row deletions per Pre-Q gate)")
    print(f"  is_maintenance=true:   {n_maint:,} ({n_maint / max(1, len(out_rows)) * 100:.2f}%)")
    print(f"  is_holiday_short=true: {n_holiday:,} ({n_holiday / max(1, len(out_rows)) * 100:.2f}%)")
    print(f"clean csv:    {CLEAN_CSV}")
    print(f"clean sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
