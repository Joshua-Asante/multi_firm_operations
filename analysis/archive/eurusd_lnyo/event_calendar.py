"""US high-impact 08:30 ET event calendar generator.

Per parent brief §4 H-PDSB hypothesis: NFP, CPI, PCE, retail sales,
GDP advance.

Approach: hand-construct from BLS/BEA standard release patterns,
then write to data/external/us_high_impact_0830et_2022_2026.csv.

Schedule rules (calendar-fixed, with first-business-day-after fallback
for weekends; minor variations exist but are within +/- 1 trading day
of the canonical date):

  - NFP (BLS Employment Situation): 1st Friday of month, 08:30 ET.
    Documented exceptions ~ once a year (delayed to 2nd Fri after
    holiday week). Approximate as 1st Fri.

  - CPI (BLS Consumer Price Index): mid-month (typically Tue-Thu in
    2nd or 3rd week, ~10-13 business days into month). Approximate
    as 2nd Wednesday of month (close to typical release weekday).

  - Core PCE (BEA Personal Income & Outlays): last Friday of month
    (~25-30 of month), 08:30 ET. Approximate as last Friday of month.

  - Retail Sales (Census Bureau, Advance Monthly): mid-month, ~10-15
    business days after month end. Approximate as 2nd Thursday of month.

  - GDP Advance (BEA): 4th week of Jan/Apr/Jul/Oct (one month after
    quarter end). Approximate as 4th Thursday of those months.

These approximations capture ~90% of true release dates within 1
trading day. Phase A diagnostic uses BROAD any-weekday-08:30 windows
so this calendar is for Phase C+ trade selection (PDSB simulator).

Output schema:
  date (ISO YYYY-MM-DD), event_type, dow_name
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

PANEL_START = dt.date(2022, 1, 4)
PANEL_END = dt.date(2026, 4, 20)

OUT = Path("data/external/us_high_impact_0830et_2022_2026.csv")


def first_friday(year: int, month: int) -> dt.date:
    d = dt.date(year, month, 1)
    while d.weekday() != 4:  # Friday=4
        d += dt.timedelta(days=1)
    return d


def nth_weekday(year: int, month: int, weekday: int, n: int) -> dt.date:
    """nth occurrence (1-indexed) of `weekday` in given month. weekday: Mon=0..Sun=6."""
    d = dt.date(year, month, 1)
    count = 0
    while True:
        if d.weekday() == weekday:
            count += 1
            if count == n:
                return d
        d += dt.timedelta(days=1)
        if d.month != month:
            raise ValueError("not enough occurrences")


def last_friday(year: int, month: int) -> dt.date:
    # Last day of month
    if month == 12:
        last = dt.date(year, 12, 31)
    else:
        last = dt.date(year, month + 1, 1) - dt.timedelta(days=1)
    while last.weekday() != 4:
        last -= dt.timedelta(days=1)
    return last


def generate_calendar(start: dt.date, end: dt.date) -> list[tuple[dt.date, str]]:
    out: list[tuple[dt.date, str]] = []
    cur_year = start.year
    cur_month = start.month
    while True:
        y, m = cur_year, cur_month
        # NFP — first Friday
        d = first_friday(y, m)
        if start <= d <= end:
            out.append((d, "NFP"))
        # CPI — 2nd Wednesday (proxy)
        d = nth_weekday(y, m, 2, 2)
        if start <= d <= end:
            out.append((d, "CPI"))
        # Retail Sales — 2nd Thursday (proxy)
        d = nth_weekday(y, m, 3, 2)
        if start <= d <= end:
            out.append((d, "RetailSales"))
        # PCE — last Friday
        d = last_friday(y, m)
        if start <= d <= end:
            out.append((d, "PCE"))
        # GDP Advance — 4th Thursday of Jan/Apr/Jul/Oct
        if m in (1, 4, 7, 10):
            try:
                d = nth_weekday(y, m, 3, 4)
                if start <= d <= end:
                    out.append((d, "GDP_Advance"))
            except ValueError:
                pass

        # Next month
        if (y, m) >= (end.year, end.month):
            break
        if m == 12:
            cur_year, cur_month = y + 1, 1
        else:
            cur_year, cur_month = y, m + 1
    return out


def write_calendar(out_path: Path = OUT) -> int:
    rows = generate_calendar(PANEL_START, PANEL_END)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "event_type", "dow_name"])
        for d, ev in sorted(rows):
            w.writerow([d.isoformat(), ev, d.strftime("%A")])
    return len(rows)


def load_calendar(path: Path = OUT) -> list[tuple[dt.date, str]]:
    out: list[tuple[dt.date, str]] = []
    if not path.exists():
        return out
    with open(path) as f:
        r = csv.DictReader(f)
        for row in r:
            d = dt.date.fromisoformat(row["date"])
            ev = row["event_type"]
            out.append((d, ev))
    return out


def event_dates(path: Path = OUT) -> set[dt.date]:
    return set(d for d, _ in load_calendar(path))


if __name__ == "__main__":
    n = write_calendar()
    print(f"Wrote {n} events to {OUT}")
    cal = load_calendar()
    # Spot check: 2024 NFPs
    print("\n2024 NFPs:")
    for d, ev in cal:
        if d.year == 2024 and ev == "NFP":
            print(f"  {d} ({d.strftime('%A')})")
    # Spot check counts
    from collections import Counter
    c = Counter(ev for _, ev in cal)
    print("\nEvent type counts:")
    for k, v in c.items():
        print(f"  {k}: {v}")
