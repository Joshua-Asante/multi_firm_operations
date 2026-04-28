"""
Build data/macro/us_releases_1000et_2022_2026.csv.

Strategy: each indicator has a documented release rule (ISM = 1st/3rd business
day; Consumer Confidence = last Tuesday; etc). Generate candidate dates from
those rules across 2022-01 to 2026-04. All are historically 10:00 ET.

Rules are approximate for indicators with looser schedules (JOLTS, home sales,
inventories, factory orders). The report explicitly flags where precision is
limited. Notice phase is interested in IF a 10:00-ET release fell on the trade
day, not exact indicator identity — partial coverage still discriminates H#2.

US federal holidays (exchange + bank) are observed: if the rule-generated date
falls on one, it shifts to the next business day (BLS/Census/ISM convention).
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import csv

OUT = Path(__file__).resolve().parents[1] / "data" / "macro" / "us_releases_1000et_2022_2026.csv"

START = date(2022, 1, 1)
END = date(2026, 4, 15)

# Federal holidays observed (bank closures). Release dates shift off these.
US_HOLIDAYS = {
    # 2022
    date(2022, 1, 17), date(2022, 2, 21), date(2022, 5, 30), date(2022, 6, 20),
    date(2022, 7, 4), date(2022, 9, 5), date(2022, 10, 10), date(2022, 11, 11),
    date(2022, 11, 24), date(2022, 12, 26),
    # 2023
    date(2023, 1, 2), date(2023, 1, 16), date(2023, 2, 20), date(2023, 5, 29),
    date(2023, 6, 19), date(2023, 7, 4), date(2023, 9, 4), date(2023, 10, 9),
    date(2023, 11, 10), date(2023, 11, 23), date(2023, 12, 25),
    # 2024
    date(2024, 1, 1), date(2024, 1, 15), date(2024, 2, 19), date(2024, 5, 27),
    date(2024, 6, 19), date(2024, 7, 4), date(2024, 9, 2), date(2024, 10, 14),
    date(2024, 11, 11), date(2024, 11, 28), date(2024, 12, 25),
    # 2025
    date(2025, 1, 1), date(2025, 1, 20), date(2025, 2, 17), date(2025, 5, 26),
    date(2025, 6, 19), date(2025, 7, 4), date(2025, 9, 1), date(2025, 10, 13),
    date(2025, 11, 11), date(2025, 11, 27), date(2025, 12, 25),
    # 2026
    date(2026, 1, 1), date(2026, 1, 19), date(2026, 2, 16),
}


def is_business_day(d: date) -> bool:
    return d.weekday() < 5 and d not in US_HOLIDAYS


def nth_business_day(year: int, month: int, n: int) -> date:
    d = date(year, month, 1)
    count = 0
    while True:
        if is_business_day(d):
            count += 1
            if count == n:
                return d
        d += timedelta(days=1)


def last_weekday(year: int, month: int, weekday: int) -> date:
    """weekday: 0=Mon..6=Sun; last occurrence of that weekday in the month."""
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    offset = (last.weekday() - weekday) % 7
    return last - timedelta(days=offset)


def nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    offset = (weekday - d.weekday()) % 7
    return d + timedelta(days=offset + 7 * (n - 1))


def shift_off_holiday(d: date) -> date:
    while not is_business_day(d):
        d += timedelta(days=1)
    return d


def in_window(d: date) -> bool:
    return START <= d <= END


def gen_months():
    # iterate (year, month) over the window
    y, m = START.year, START.month
    while (y, m) <= (END.year, END.month):
        yield y, m
        m += 1
        if m == 13:
            m = 1
            y += 1


def main() -> None:
    rows: list[tuple[date, str, str, str]] = []

    for y, m in gen_months():
        # ISM Manufacturing PMI: 1st business day, 10:00 ET
        d = nth_business_day(y, m, 1)
        if in_window(d):
            rows.append((d, "10:00", "ISM Manufacturing PMI", "https://www.ismworld.org/"))

        # Construction Spending: historically 1st business day at 10:00 ET (Census)
        # Often co-released same day as ISM Mfg.
        d = nth_business_day(y, m, 1)
        if in_window(d):
            rows.append((d, "10:00", "Construction Spending", "https://www.census.gov/construction/c30/"))

        # ISM Services PMI: 3rd business day, 10:00 ET
        d = nth_business_day(y, m, 3)
        if in_window(d):
            rows.append((d, "10:00", "ISM Services PMI", "https://www.ismworld.org/"))

        # Factory Orders: typically ~5th business day, 10:00 ET (Census)
        d = nth_business_day(y, m, 5)
        if in_window(d):
            rows.append((d, "10:00", "Factory Orders", "https://www.census.gov/manufacturing/m3/"))

        # Wholesale Inventories (advance): typically ~7th business day, 10:00 ET
        d = nth_business_day(y, m, 7)
        if in_window(d):
            rows.append((d, "10:00", "Wholesale Inventories", "https://www.census.gov/wholesale/"))

        # Business Inventories: ~10th business day of month, 10:00 ET (Census)
        d = nth_business_day(y, m, 10)
        if in_window(d):
            rows.append((d, "10:00", "Business Inventories", "https://www.census.gov/mtis/"))

        # JOLTS: typically the last Tuesday of the month (releasing data 2 months prior)
        # In practice it lands within the last 5-7 business days of the month. 10:00 ET.
        d = last_weekday(y, m, 1)  # last Tuesday
        d = shift_off_holiday(d)
        if in_window(d):
            rows.append((d, "10:00", "JOLTS Job Openings", "https://www.bls.gov/jlt/"))

        # Existing Home Sales (NAR): typically 3rd or 4th week, released ~20th.
        # Use a rule of 3rd Wednesday as approx anchor point. 10:00 ET.
        d = shift_off_holiday(nth_weekday(y, m, 2, 3))  # 3rd Wednesday
        if in_window(d):
            rows.append((d, "10:00", "Existing Home Sales", "https://www.nar.realtor/research-and-statistics"))

        # New Home Sales (Census): typically 4th week, ~23rd-25th. 10:00 ET.
        # Use 4th Tuesday as approx anchor.
        d = shift_off_holiday(nth_weekday(y, m, 1, 4))  # 4th Tuesday
        if in_window(d):
            rows.append((d, "10:00", "New Home Sales", "https://www.census.gov/construction/nrs/"))

        # Pending Home Sales (NAR): typically 4th or last Thursday. 10:00 ET.
        d = last_weekday(y, m, 3)  # last Thursday
        d = shift_off_holiday(d)
        if in_window(d):
            rows.append((d, "10:00", "Pending Home Sales", "https://www.nar.realtor/research-and-statistics"))

        # Consumer Confidence (Conference Board): last Tuesday of month, 10:00 ET
        d = last_weekday(y, m, 1)
        d = shift_off_holiday(d)
        if in_window(d):
            rows.append((d, "10:00", "Consumer Confidence (CB)", "https://www.conference-board.org/topics/consumer-confidence"))

    rows.sort(key=lambda r: (r[0], r[2]))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["release_date", "release_time_et", "indicator", "source_url"])
        for d, t, ind, url in rows:
            w.writerow([d.isoformat(), t, ind, url])

    print(f"wrote {OUT}  rows={len(rows)}")


if __name__ == "__main__":
    main()
