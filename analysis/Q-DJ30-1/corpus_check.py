"""Step 0a — corpus equivalence check on canonical Pepperstone DJ30 v4.5 panel.

Compare _12175 (canonical) against the 4 web-brief observations from _25172.
"""
from pathlib import Path
import csv
from datetime import datetime

CSV = Path("data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv")

rows = []
with CSV.open(newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)

entries = [r for r in rows if r["Type"] == "Entry long"]
exits   = [r for r in rows if r["Type"] == "Exit long"]

n_entry_long = len(entries)

# Net P&L per trade — entry rows already carry the trade's net P&L (matches exit row)
def to_float(s):
    return float(s.replace(",", "").strip()) if s else 0.0

pnls = [to_float(r["Net P&L USD"]) for r in entries]
sum_pnl = sum(pnls)

# Worst single trade
worst_idx = pnls.index(min(pnls))
worst_entry = entries[worst_idx]
worst_dt = worst_entry["Date and time"]
worst_pnl = pnls[worst_idx]

# Span
def parse_dt(s):
    return datetime.strptime(s.strip(), "%Y-%m-%d %H:%M")

dts = [parse_dt(e["Date and time"]) for e in entries]
first_dt = min(dts)
last_dt = max(dts)

print(f"=== Corpus equivalence check: {CSV.name} ===")
print(f"n_entry_long      : {n_entry_long}            (web brief expects 224)")
print(f"sum_pnl_entries   : ${sum_pnl:,.2f}    (web brief expects $363,113 ±$50)")
print(f"worst_trade_dt    : {worst_dt}    (web brief expects 2025-02-07)")
print(f"worst_trade_pnl   : ${worst_pnl:,.2f}    (web brief expects ~ -$11,870.65)")
print(f"first_entry_dt    : {first_dt}    (web brief expects 2022-01-04)")
print(f"last_entry_dt     : {last_dt}    (web brief expects 2026-04-2X)")
print()
print("=== Equivalence verdict ===")
checks = {
    "n_entry_long == 224": n_entry_long == 224,
    "sum_pnl within +/-$50 of $363,113": abs(sum_pnl - 363_113) <= 50,
    "worst trade dt is 2025-02-07": worst_dt.startswith("2025-02-07"),
    "worst trade pnl approx -$11,870.65": abs(worst_pnl - (-11_870.65)) <= 1.0,
    "first entry dt is 2022-01-04": first_dt.strftime("%Y-%m-%d") == "2022-01-04",
    "last entry month is 2026-04": last_dt.strftime("%Y-%m") == "2026-04",
}
for label, ok in checks.items():
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
print()
all_ok = all(checks.values())
print(f"OVERALL: {'EQUIVALENT — proceed' if all_ok else 'DIVERGENT — hand back'}")
