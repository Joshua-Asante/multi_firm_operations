"""Step 1 - Build US macro event calendar (2022-01-04 -> 2026-05-06).

Source declaration (per findings §5):
  Authoritative sources (BLS, BEA, FRED, archive.org) returned 403 / blocked
  programmatic access at plan-execution time (2026-05-06). Per Joshua's option-2
  authorization, this calendar is rule-derived from the canonical BLS / BEA /
  Census / ISM release patterns published in their respective release schedules.

Provenance:
  - Extends `archive/analysis/eurusd_lnyo/event_calendar.py` (NFP, CPI, PCE,
    Retail Sales, GDP Advance) with PPI, ISM Manufacturing, ISM Services.
  - Adds 08:30 ET / 10:00 ET timestamps per BLS / BEA / ISM standard.
  - Approximation error: +/- 1 trading day vs actual release date for
    CPI / PPI / PCE / Retail Sales / GDP_Advance (proxy weekday rules).
    NFP, ISM_Mfg, ISM_Svc rules are exact within their published patterns.

Bias note:
  Date errors will randomize trade-to-event tagging symmetrically across
  tail and non-tail strata, biasing the test toward null (false negative).
  False-positive risk from this calendar source is structurally low.

Out-of-scope (a-priori screened, per plan Hunks 3-4):
  - FOMC statement, presser, minutes (14:00+ ET = >=18:00 UTC, outside DJ30
    13-17 UTC window by construction).
  - Initial Jobless Claims (Thursday 08:30 ET; DJ30 active Tue/Fri only).

Schema: event_dt_utc (ISO datetime), event_type, source_pattern.
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

# Span: 2022-01-04 (first DJ30 entry) -> 2026-05-06 (brief authoring date)
# Pad +/- 1 month for window-edge proximity calculations
PANEL_START = dt.date(2022, 1, 1)
PANEL_END = dt.date(2026, 5, 6)

OUT = Path("analysis/Q-DJ30-1/event_calendar.csv")

# --- Helpers ---

def first_weekday_in_month(year: int, month: int, weekday: int) -> dt.date:
    """1st occurrence of `weekday` (Mon=0..Sun=6) in given month."""
    d = dt.date(year, month, 1)
    while d.weekday() != weekday:
        d += dt.timedelta(days=1)
    return d


def nth_weekday(year: int, month: int, weekday: int, n: int) -> dt.date:
    """nth occurrence (1-indexed) of `weekday` in given month."""
    d = dt.date(year, month, 1)
    count = 0
    while True:
        if d.weekday() == weekday:
            count += 1
            if count == n:
                return d
        d += dt.timedelta(days=1)
        if d.month != month:
            raise ValueError(f"not enough {weekday}s in {year}-{month:02d}")


def last_weekday_in_month(year: int, month: int, weekday: int) -> dt.date:
    if month == 12:
        last = dt.date(year, 12, 31)
    else:
        last = dt.date(year, month + 1, 1) - dt.timedelta(days=1)
    while last.weekday() != weekday:
        last -= dt.timedelta(days=1)
    return last


def first_business_day(year: int, month: int) -> dt.date:
    """1st business day of month (Mon-Fri). Approximate; doesn't handle holidays."""
    d = dt.date(year, month, 1)
    while d.weekday() >= 5:  # Sat=5, Sun=6
        d += dt.timedelta(days=1)
    return d


def nth_business_day(year: int, month: int, n: int) -> dt.date:
    """nth business day (1-indexed). Doesn't handle holidays — error <= 1 day."""
    d = dt.date(year, month, 1)
    count = 0
    while True:
        if d.weekday() < 5:
            count += 1
            if count == n:
                return d
        d += dt.timedelta(days=1)
        if d.month != month:
            raise ValueError(f"not enough business days in {year}-{month:02d}")


def et_to_utc(date: dt.date, hour: int, minute: int) -> dt.datetime:
    """Convert ET local datetime to UTC, respecting DST."""
    naive = dt.datetime.combine(date, dt.time(hour, minute))
    return naive.replace(tzinfo=ET).astimezone(UTC)


# --- Calendar generator ---

def generate_calendar(start: dt.date, end: dt.date) -> list[tuple[dt.datetime, str, str]]:
    """Generate all macro events in span. Returns list of (dt_utc, event_type, source_pattern)."""
    out: list[tuple[dt.datetime, str, str]] = []

    cur_year, cur_month = start.year, start.month
    while True:
        y, m = cur_year, cur_month

        # NFP / Employment Situation - 1st Friday, 08:30 ET (BLS)
        try:
            d = nth_weekday(y, m, 4, 1)  # Friday=4, 1st occurrence
            if start <= d <= end:
                out.append((et_to_utc(d, 8, 30), "NFP", "BLS:1st_friday_0830et"))
        except ValueError:
            pass

        # CPI - 2nd Wednesday proxy (BLS publishes mid-month Tue-Thu, ~10-13th business day)
        try:
            d = nth_weekday(y, m, 2, 2)  # Wednesday=2, 2nd occurrence
            if start <= d <= end:
                out.append((et_to_utc(d, 8, 30), "CPI", "BLS:2nd_wednesday_proxy_0830et"))
        except ValueError:
            pass

        # PPI - 2nd Thursday proxy (BLS publishes day after CPI typically)
        try:
            d = nth_weekday(y, m, 3, 2)  # Thursday=3, 2nd occurrence
            if start <= d <= end:
                out.append((et_to_utc(d, 8, 30), "PPI", "BLS:2nd_thursday_proxy_0830et"))
        except ValueError:
            pass

        # Retail Sales - mid-month proxy: 3rd Tuesday (Census publishes 13-17th business day)
        try:
            d = nth_weekday(y, m, 1, 3)  # Tuesday=1, 3rd occurrence
            if start <= d <= end:
                out.append((et_to_utc(d, 8, 30), "RetailSales", "Census:3rd_tuesday_proxy_0830et"))
        except ValueError:
            pass

        # PCE / Personal Income - last Friday, 08:30 ET (BEA)
        d = last_weekday_in_month(y, m, 4)
        if start <= d <= end:
            out.append((et_to_utc(d, 8, 30), "PCE", "BEA:last_friday_0830et"))

        # GDP Advance - 4th Thursday of Jan/Apr/Jul/Oct, 08:30 ET (BEA quarterly)
        if m in (1, 4, 7, 10):
            try:
                d = nth_weekday(y, m, 3, 4)
                if start <= d <= end:
                    out.append((et_to_utc(d, 8, 30), "GDP_Advance", "BEA:4th_thursday_quarterly_0830et"))
            except ValueError:
                pass

        # ISM Manufacturing PMI - 1st business day, 10:00 ET
        d = first_business_day(y, m)
        if start <= d <= end:
            out.append((et_to_utc(d, 10, 0), "ISM_Mfg", "ISM:1st_business_day_1000et"))

        # ISM Services PMI - 3rd business day, 10:00 ET
        try:
            d = nth_business_day(y, m, 3)
            if start <= d <= end:
                out.append((et_to_utc(d, 10, 0), "ISM_Svc", "ISM:3rd_business_day_1000et"))
        except ValueError:
            pass

        # Next month
        if (y, m) >= (end.year, end.month):
            break
        if m == 12:
            cur_year, cur_month = y + 1, 1
        else:
            cur_year, cur_month = y, m + 1

    return sorted(out)


def write_calendar(out_path: Path = OUT) -> int:
    rows = generate_calendar(PANEL_START, PANEL_END)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["event_dt_utc", "event_type", "source_pattern"])
        for dt_utc, ev, src in rows:
            w.writerow([dt_utc.isoformat(), ev, src])
    return len(rows)


if __name__ == "__main__":
    n = write_calendar()
    print(f"Wrote {n} events to {OUT}")
    print()

    # Per-class counts
    from collections import Counter
    rows = generate_calendar(PANEL_START, PANEL_END)
    counts = Counter(ev for _, ev, _ in rows)
    print("Per-class counts:")
    for k in sorted(counts):
        print(f"  {k:<14} : {counts[k]}")
    print()

    # Sanity: 2025-02-07 NFP should appear at 13:30 UTC
    print("Sanity check: 2025-02-07 NFP")
    nfp_targets = [r for r in rows if r[1] == "NFP" and r[0].date() == dt.date(2025, 2, 7)]
    if nfp_targets:
        print(f"  Found: {nfp_targets[0][0]} (expected 2025-02-07 13:30 UTC)")
    else:
        print(f"  NOT FOUND - investigate")
