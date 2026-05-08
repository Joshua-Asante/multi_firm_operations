"""Diagnose which 7 trades have no matching gap row and why.

Per pre-reg §5.3 halt protocol — investigate before deciding to substitute / delete / proceed.
"""
from pathlib import Path
import csv
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

CSV_TRADES = Path("data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv")
CSV_GAP = Path("analysis/Q-DJ30-3/dj30_daily_gap.csv")

# --- Load gap dates ---
with CSV_GAP.open(newline="", encoding="utf-8") as f:
    gap_dates = {r["date"] for r in csv.DictReader(f)}

print(f"Gap-panel dates: {len(gap_dates)}  (range: {min(gap_dates)} -> {max(gap_dates)})")
print()

# --- Load trades ---
with CSV_TRADES.open(newline="", encoding="utf-8-sig") as f:
    rows = [r for r in csv.DictReader(f) if r["Type"] == "Entry long"]

missing = []
for r in rows:
    et_dt = datetime.strptime(r["Date and time"].strip(), "%Y-%m-%d %H:%M").replace(tzinfo=ET)
    utc_dt = et_dt.astimezone(UTC)
    utc_date = utc_dt.date().isoformat()
    if utc_date not in gap_dates:
        missing.append({
            "trade_num": r["Trade #"],
            "signal": r["Signal"],
            "et_time": r["Date and time"],
            "utc_dt": utc_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "utc_date": utc_date,
            "weekday": utc_dt.strftime("%a"),
            "net_pnl": float(r["Net P&L USD"].replace(",", "")) if r["Net P&L USD"] else 0.0,
        })

print(f"=== {len(missing)} trades without matching gap row ===")
for m in missing:
    print(f"  #{m['trade_num']:>3}  {m['signal']:<10}  ET {m['et_time']}  ->  UTC {m['utc_dt']} ({m['weekday']})  pnl=${m['net_pnl']:,.2f}")

# Cross-check: are these dates in the calendar-day OHLC at all?
from collections import Counter
print()
print("=== Distribution of missing trades by weekday ===")
print(Counter(m["weekday"] for m in missing))
print()
print("=== Earliest gap-panel date vs earliest trade ===")
print(f"  earliest gap date     : {min(gap_dates)}")
earliest_trade_date = min(m["utc_date"] for m in missing) if missing else None
print(f"  earliest missing-trade date: {earliest_trade_date}")
