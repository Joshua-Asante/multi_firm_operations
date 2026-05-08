"""Phase C Step 1 — tag DJ30 trades with day-level gap_atr_normalized.

Reads:
  data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv
  analysis/Q-DJ30-3/dj30_daily_gap.csv

Writes:
  analysis/Q-DJ30-3/per_trade_gap.csv

Mirrors analysis/Q-DJ30-1/tag_trades.py structure but swaps event-proximity
tagging for gap-quantile binary tagging. The conditioning variable is
day-level: all trades on date d (base + pyramid alike) inherit d's
|gap_atr_normalized|.
"""
from pathlib import Path
import csv
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

CSV_TRADES = Path("data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv")
CSV_GAP = Path("analysis/Q-DJ30-3/dj30_daily_gap.csv")
OUT = Path("analysis/Q-DJ30-3/per_trade_gap.csv")

QUANTILES = (0.80, 0.85, 0.90, 0.95)


def to_float(s):
    return float(s.replace(",", "").strip()) if s else 0.0


# --- Load gap panel ---
with CSV_GAP.open(newline="", encoding="utf-8") as f:
    gap_rows = list(csv.DictReader(f))

# Panel-level quantiles on |gap_atr_normalized|
abs_gaps_panel = sorted(float(r["abs_gap_atr"]) for r in gap_rows)
n_panel = len(abs_gaps_panel)


def quantile(sorted_vals, q):
    """Empirical quantile, lower-bound interpolation (matches Q-DJ30-1's panel-quantile semantics)."""
    idx = int(q * len(sorted_vals))
    if idx >= len(sorted_vals):
        idx = len(sorted_vals) - 1
    return sorted_vals[idx]


thresholds = {q: quantile(abs_gaps_panel, q) for q in QUANTILES}
print("=== Panel |gap_atr_normalized| quantile thresholds (n_panel = {}) ===".format(n_panel))
for q in QUANTILES:
    print(f"  p{int(q*100)} = {thresholds[q]:.4f}")
print()

# Index gap_rows by date
gap_by_date = {r["date"]: r for r in gap_rows}

# --- Load trades ---
with CSV_TRADES.open(newline="", encoding="utf-8-sig") as f:
    trade_rows = [r for r in csv.DictReader(f)]

entries = [r for r in trade_rows if r["Type"] == "Entry long"]

# Count entries per UTC date
from collections import Counter
entries_per_day = Counter()
for r in entries:
    et_dt = datetime.strptime(r["Date and time"].strip(), "%Y-%m-%d %H:%M").replace(tzinfo=ET)
    entries_per_day[et_dt.astimezone(UTC).date()] += 1

# --- Tag each trade ---
out_rows = []
missing_gap = 0
for r in entries:
    et_dt = datetime.strptime(r["Date and time"].strip(), "%Y-%m-%d %H:%M").replace(tzinfo=ET)
    utc_dt = et_dt.astimezone(UTC)
    utc_date = utc_dt.date().isoformat()

    gap_row = gap_by_date.get(utc_date)
    if gap_row is None:
        missing_gap += 1
        # Still emit a row with gap=0 / all-bin-False, marked sentinel — surfaces as halt below if ≥3
        gap_atr_signed = 0.0
        abs_gap = 0.0
        gap_present = False
    else:
        gap_atr_signed = float(gap_row["gap_atr_normalized"])
        abs_gap = float(gap_row["abs_gap_atr"])
        gap_present = True

    row = {
        "trade_num": r["Trade #"],
        "signal": r["Signal"],
        "entry_dt_utc": utc_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "entry_date_utc": utc_date,
        "net_pnl_usd": to_float(r["Net P&L USD"]),
        "n_entries_that_day": entries_per_day[utc_dt.date()],
        "gap_atr_signed": gap_atr_signed,
        "abs_gap_atr": abs_gap,
        "gap_present": gap_present,
    }
    for q in QUANTILES:
        row[f"in_gap_p{int(q*100)}"] = abs_gap >= thresholds[q] if gap_present else False
    out_rows.append(row)

# Sort by trade_num
out_rows.sort(key=lambda r: int(r["trade_num"]))

# --- Halt protocol per pre-reg §5.3: if missing-gap ≥ 3, surface ---
if missing_gap >= 3:
    raise SystemExit(
        f"HALT: {missing_gap} trades have no matching gap row in dj30_daily_gap.csv. "
        f"Pre-reg §5.3 forbids deletion without surfaced cause. Investigate."
    )
elif missing_gap > 0:
    print(f"  WARN: {missing_gap} trade(s) without gap data — under halt threshold (3); proceeding")

# --- Write ---
fieldnames = [
    "trade_num", "signal", "entry_dt_utc", "entry_date_utc", "net_pnl_usd",
    "n_entries_that_day", "gap_atr_signed", "abs_gap_atr", "gap_present",
] + [f"in_gap_p{int(q*100)}" for q in QUANTILES]

with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(out_rows)

print(f"Wrote {len(out_rows)} rows to {OUT}")
print(f"  base entries (Signal=Long)    : {sum(1 for r in out_rows if r['signal']=='Long')}")
print(f"  pyramid legs (Signal=Long Add): {sum(1 for r in out_rows if r['signal']=='Long Add')}")
print()

# --- Sanity ---
print("=== Sanity: anchor trade #168 ===")
anchor = next(r for r in out_rows if r["trade_num"] == "168")
print(f"  trade #{anchor['trade_num']}  signal={anchor['signal']}  entry_date_utc={anchor['entry_date_utc']}")
print(f"  net_pnl              : ${anchor['net_pnl_usd']:,.2f}")
print(f"  gap_atr_signed       : {anchor['gap_atr_signed']:+.4f}")
print(f"  |gap_atr|            : {anchor['abs_gap_atr']:.4f}")
for q in QUANTILES:
    key = f"in_gap_p{int(q*100)}"
    print(f"  {key:<14}      : {anchor[key]}")
print()

# Counts across 197 base only
bases = [r for r in out_rows if r["signal"] == "Long"]
print("=== In-bin counts (base entries n=197) ===")
for q in QUANTILES:
    key = f"in_gap_p{int(q*100)}"
    in_count = sum(1 for r in bases if r[key])
    print(f"  {key} : {in_count}/{len(bases)}  ({100*in_count/len(bases):.1f}%)")
