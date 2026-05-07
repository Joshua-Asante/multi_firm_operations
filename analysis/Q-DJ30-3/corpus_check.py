"""Phase B Step 1 — corpus equivalence + cardinality reproduction.

Reads:  data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv
Writes: stdout only

Verifies the locked Pepperstone DJ30 trade panel is intact and matches the
v4.5 lock anchors. Halt protocol: any cardinality drift or anchor-trade
mismatch HALTs Phase C.
"""
from pathlib import Path
import csv

CSV = Path("data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv")

with CSV.open(newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

entries = [r for r in rows if r["Type"] == "Entry long"]
bases = [r for r in entries if r["Signal"] == "Long"]
pyramids = [r for r in entries if r["Signal"] == "Long Add"]


def to_float(s):
    return float(s.replace(",", "").strip()) if s else 0.0


pnls = [to_float(r["Net P&L USD"]) for r in entries]
worst_idx = min(range(len(pnls)), key=lambda i: pnls[i])
worst = entries[worst_idx]

print("=== Phase B corpus check (Q-DJ30-3) ===")
print(f"  CSV path                  : {CSV}")
print(f"  Total rows (incl. exits)  : {len(rows)}")
print(f"  Entry rows (Type=Entry long): {len(entries)}")
print(f"  Base entries (Signal=Long): {len(bases)}")
print(f"  Pyramid legs (Signal=Long Add): {len(pyramids)}")
print(f"  Worst trade               : #{worst['Trade #']}  {worst['Date and time']}  ${pnls[worst_idx]:,.2f}")
print()

ok = True
if len(entries) != 224:
    print(f"  FAIL: expected 224 entries, got {len(entries)}")
    ok = False
if len(bases) != 197:
    print(f"  FAIL: expected 197 base entries, got {len(bases)}")
    ok = False
if len(pyramids) != 27:
    print(f"  FAIL: expected 27 pyramid legs, got {len(pyramids)}")
    ok = False
if worst["Trade #"] != "168":
    print(f"  FAIL: expected worst trade #168, got #{worst['Trade #']}")
    ok = False
if abs(pnls[worst_idx] - (-11870.65)) > 0.5:
    print(f"  FAIL: expected worst pnl -$11,870.65, got ${pnls[worst_idx]:,.2f}")
    ok = False

if ok:
    print("  PASS — all 4 cardinality + anchor checks clear")
else:
    print("  HALT — cardinality / anchor mismatch; do not advance to Phase C")
    raise SystemExit(1)
