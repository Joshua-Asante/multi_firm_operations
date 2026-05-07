"""Q-DJ30-2 Phase C - capped P&L builder.

Applies a hard dollar cap on base-entry stop loss. Pyramid legs untouched.

Cap formulation (per pre-registration):
    capped_pnl = max(actual_pnl, -cap_R * NOMINAL_R_USD)

The cap is a floor on dollar loss per ticket. No look-ahead; the actual
realized loss on a stop-through trade IS the deepest excursion (stop-out
behavior — the realized loss equals the slippage past the stop level).

Public API:
    load_entries() -> list of dict rows from the locked CSV (all 224 entries)
    apply_cap(entries, cap_R) -> list of dict rows with capped pnl on bases
    write_capped_csv(entries, cap_R, path) -> writes capped CSV to path
"""
from pathlib import Path
import csv

CSV_TRADES = Path("data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv")
NOMINAL_R_USD = 2000.0


def to_float(s):
    return float(s.replace(",", "").strip()) if s else 0.0


def load_entries():
    with CSV_TRADES.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    entries = [r for r in rows if r["Type"] == "Entry long"]
    for r in entries:
        r["pnl"] = to_float(r["Net P&L USD"])
        r["mae"] = to_float(r["Adverse excursion USD"])
        r["trade_num"] = int(r["Trade #"])
    entries.sort(key=lambda r: r["trade_num"])
    return entries


def apply_cap(entries, cap_R):
    """Return new list of dicts with capped pnl on base trades."""
    floor_dollars = -cap_R * NOMINAL_R_USD
    out = []
    for r in entries:
        new = dict(r)
        if r["Signal"] == "Long":
            new["pnl_uncapped"] = r["pnl"]
            new["pnl"] = max(r["pnl"], floor_dollars)
            new["cap_touched"] = r["pnl"] < floor_dollars
        else:
            new["pnl_uncapped"] = r["pnl"]
            new["cap_touched"] = False
        out.append(new)
    return out


def write_capped_csv(capped_entries, cap_R, out_path):
    fieldnames = [
        "trade_num", "signal", "date_and_time", "pnl_uncapped", "pnl",
        "cap_touched", "mae",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in capped_entries:
            w.writerow({
                "trade_num": r["trade_num"],
                "signal": r["Signal"],
                "date_and_time": r["Date and time"],
                "pnl_uncapped": f"{r['pnl_uncapped']:.4f}",
                "pnl": f"{r['pnl']:.4f}",
                "cap_touched": r["cap_touched"],
                "mae": f"{r['mae']:.4f}",
            })


if __name__ == "__main__":
    # Standalone: write one CSV per cap level for inspection
    OUT_DIR = Path("analysis/Q-DJ30-2")
    entries = load_entries()
    print(f"Loaded {len(entries)} entries from {CSV_TRADES}")
    for cap_R in (1.5, 2.0, 2.5, 3.0, 3.5):
        capped = apply_cap(entries, cap_R)
        n_touched = sum(1 for r in capped if r["cap_touched"])
        out = OUT_DIR / f"capped_pnl_{cap_R:.1f}R.csv"
        write_capped_csv(capped, cap_R, out)
        print(f"  cap={cap_R}R (floor=${-cap_R * NOMINAL_R_USD:,.0f}): "
              f"{n_touched} base trades touched -> {out}")
