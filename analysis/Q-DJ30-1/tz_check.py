"""Step 0b - timezone anchor check (revised after pyramid-leg discovery).

Hypothesis: CSV raw 'Date and time' is America/New_York (chart time), NOT UTC.

Test methodology:
- Base entries (Signal == 'Long') must fall in [13, 17) UTC after ET -> UTC
  conversion, since the Pine session window gates them.
- Pyramid legs (Signal == 'Long Add') get their own Trade # in TV exports
  but are NOT session-gated in the Pine - they fire on profit trigger
  (`profitAtr >= pyramidTrigger`) at any time the parent trade is open.
  They can legitimately appear after 17:00 UTC.

If ALL base-entry rows land in [13, 17) UTC after ET -> UTC, TZ assumption
is confirmed. Pyramid legs are reported separately for transparency.

Anchor trade: 2025-02-07 09:45 raw ET -> 14:45 UTC (winter EST = UTC-5).
NFP releases that day at 08:30 ET = 13:30 UTC. Distance: +75 min.
"""
from pathlib import Path
import csv
from datetime import datetime
from zoneinfo import ZoneInfo

CSV = Path("data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv")
ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

with CSV.open(newline="", encoding="utf-8-sig") as f:
    rows = [r for r in csv.DictReader(f) if r["Type"] == "Entry long"]

bases   = [r for r in rows if r["Signal"] == "Long"]
pyrs    = [r for r in rows if r["Signal"] == "Long Add"]

def to_utc(s):
    return datetime.strptime(s.strip(), "%Y-%m-%d %H:%M").replace(tzinfo=ET).astimezone(UTC)

base_out = [(r["Trade #"], r["Date and time"], to_utc(r["Date and time"]).strftime("%Y-%m-%d %H:%M"), to_utc(r["Date and time"]).hour)
            for r in bases if not (13 <= to_utc(r["Date and time"]).hour < 17)]
pyr_out  = [r for r in pyrs if not (13 <= to_utc(r["Date and time"]).hour < 17)]

print(f"Total entry-long rows : {len(rows)}")
print(f"Base entries          : {len(bases)}    (must all fall in [13, 17) UTC)")
print(f"Pyramid-leg entries   : {len(pyrs)}    (NOT session-gated - can fire any time)")
print()

if base_out:
    print(f"FAIL - {len(base_out)} base entries outside [13, 17) UTC after ET->UTC:")
    for t in base_out[:10]:
        print(f"  trade #{t[0]}  raw={t[1]}  utc={t[2]}  hour={t[3]}")
    print()
    print("VERDICT: TZ assumption WRONG - hand back to Joshua.")
else:
    print(f"PASS - all {len(bases)} base entries fall in DJ30 session window [13, 17) UTC.")

print()
print(f"Pyramid legs outside [13, 17) UTC: {len(pyr_out)} of {len(pyrs)}")
print("  (These are profit-triggered adds; not session-gated. Expected behavior.)")
print()

print("=== Anchor trade verification (2025-02-07 09:45) ===")
anchor = next(r for r in bases if r["Date and time"].strip() == "2025-02-07 09:45")
naive = datetime.strptime(anchor["Date and time"].strip(), "%Y-%m-%d %H:%M")
et_dt = naive.replace(tzinfo=ET)
utc_dt = et_dt.astimezone(UTC)
print(f"raw CSV time           : {anchor['Date and time']}")
print(f"ET-localized           : {et_dt}")
print(f"UTC                    : {utc_dt}")
print(f"net pnl                : ${float(anchor['Net P&L USD'].replace(',', '')):,.2f}")
print()

nfp = datetime(2025, 2, 7, 13, 30, tzinfo=UTC)
delta_min = int((utc_dt - nfp).total_seconds() / 60)
print(f"NFP 2025-02-07 08:30 ET = 13:30 UTC")
print(f"Distance entry - NFP   : {delta_min:+d} minutes")
print(f"Within +/-90 min       : {abs(delta_min) <= 90}")
print()

if abs(delta_min) <= 90 and not base_out:
    print("=== Step 0b VERDICT: TZ pipeline confirmed. PROCEED. ===")
else:
    print("=== Step 0b VERDICT: HAND BACK. ===")
