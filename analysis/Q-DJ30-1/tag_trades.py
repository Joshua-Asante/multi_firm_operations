"""Step 2 - Tag DJ30 trades with macro-event proximity.

Reads:
  data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv
  analysis/Q-DJ30-1/event_calendar.csv

Writes:
  analysis/Q-DJ30-1/per_trade_proximity.csv

Methodology:
  - Filter Type=='Entry long'. 224 rows total = 197 base ('Long') + 27 pyramid
    legs ('Long Add'). Both reported; downstream analysis uses base-only as
    primary (clean signal-time question), all-rows as sensitivity (matches
    brief's pre-registered n).
  - Localize raw CSV time as America/New_York, convert to UTC (per Step 0b).
  - For each trade, find nearest event by abs(minutes); record signed minutes,
    type, and in_window booleans for windows {30, 60, 90, 120, 180}.
"""
from pathlib import Path
import csv
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

CSV_TRADES = Path("data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv")
CSV_CAL    = Path("analysis/Q-DJ30-1/event_calendar.csv")
OUT        = Path("analysis/Q-DJ30-1/per_trade_proximity.csv")

WINDOWS = (30, 60, 90, 120, 180)

# --- Load trades ---
with CSV_TRADES.open(newline="", encoding="utf-8-sig") as f:
    trade_rows = [r for r in csv.DictReader(f)]

entries = [r for r in trade_rows if r["Type"] == "Entry long"]

# Count how many entry rows fired on each calendar date (for n_entries_that_day)
from collections import Counter
entries_per_day = Counter()
for r in entries:
    raw = r["Date and time"].strip()
    et_dt = datetime.strptime(raw, "%Y-%m-%d %H:%M").replace(tzinfo=ET)
    entries_per_day[et_dt.date()] += 1

# --- Load event calendar ---
with CSV_CAL.open(newline="", encoding="utf-8") as f:
    cal_rows = list(csv.DictReader(f))

events = []
for r in cal_rows:
    dt_utc = datetime.fromisoformat(r["event_dt_utc"])
    events.append((dt_utc, r["event_type"]))
events.sort()

# --- Tag each trade ---
def to_float(s):
    return float(s.replace(",", "").strip()) if s else 0.0

out_rows = []
for r in entries:
    raw = r["Date and time"].strip()
    et_dt = datetime.strptime(raw, "%Y-%m-%d %H:%M").replace(tzinfo=ET)
    utc_dt = et_dt.astimezone(UTC)

    # Find nearest event by abs(minutes)
    best = None
    best_abs = None
    for e_dt, e_type in events:
        delta_sec = (utc_dt - e_dt).total_seconds()
        delta_min = int(round(delta_sec / 60))
        if best_abs is None or abs(delta_min) < best_abs:
            best_abs = abs(delta_min)
            best = (delta_min, e_type)

    nearest_min, nearest_type = best

    row = {
        "trade_num": r["Trade #"],
        "signal": r["Signal"],
        "entry_dt_utc": utc_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "net_pnl_usd": to_float(r["Net P&L USD"]),
        "n_entries_that_day": entries_per_day[et_dt.date()],
        "nearest_event_minutes_signed": nearest_min,
        "nearest_event_type": nearest_type if abs(nearest_min) <= 240 else "none",
    }
    for w in WINDOWS:
        row[f"in_window_{w}"] = abs(nearest_min) <= w
    out_rows.append(row)

# Sort by trade_num for stable output
out_rows.sort(key=lambda r: int(r["trade_num"]))

# --- Write ---
fieldnames = [
    "trade_num", "signal", "entry_dt_utc", "net_pnl_usd", "n_entries_that_day",
    "nearest_event_minutes_signed", "nearest_event_type",
] + [f"in_window_{w}" for w in WINDOWS]

with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(out_rows)

print(f"Wrote {len(out_rows)} rows to {OUT}")
print()

# --- Sanity ---
print("=== Sanity check: 2025-02-07 anchor trade (worst single loss) ===")
anchor = next(r for r in out_rows if r["trade_num"] == "168")
print(f"  trade #{anchor['trade_num']}  signal={anchor['signal']}")
print(f"  entry_dt_utc        : {anchor['entry_dt_utc']}")
print(f"  net_pnl             : ${anchor['net_pnl_usd']:,.2f}")
print(f"  nearest_event_min   : {anchor['nearest_event_minutes_signed']:+d}")
print(f"  nearest_event_type  : {anchor['nearest_event_type']}")
print(f"  in_window_90        : {anchor['in_window_90']}")
print()

# Distribution of nearest-event types
from collections import Counter
type_dist = Counter(r["nearest_event_type"] for r in out_rows)
print("Nearest-event-type distribution (all 224 entries):")
for k in sorted(type_dist):
    print(f"  {k:<12} : {type_dist[k]}")

# In-window counts at primary 90-min window
in_w90 = sum(1 for r in out_rows if r["in_window_90"])
print()
print(f"in_window_90 count (all 224)  : {in_w90} ({100*in_w90/len(out_rows):.1f}%)")

# Base only
bases = [r for r in out_rows if r["signal"] == "Long"]
in_w90_base = sum(1 for r in bases if r["in_window_90"])
print(f"in_window_90 count (base 197) : {in_w90_base} ({100*in_w90_base/len(bases):.1f}%)")
