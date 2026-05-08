"""Q-DJ30-2 Phase B - baseline reproduction gate.

Reproduces v4.5 baseline metrics from the locked Pepperstone DJ30 CSV.
All gate lines must pass before Phase C can run.

Per pre-registration (analysis/Q-DJ30-2/verdict_pre_registration.md), as
amended 2026-05-06 (docs/methodology/gate_audits/2026-05-06_q-dj30-2_pre_reg_amend.md):
  - PF (n=224 all entries) within 0.5% of 2.7528
  - PF (n=197 base only) within 0.5% of 2.3294 (derived anchor)
  - Worst single-trade loss within 0.5% of -$11,871
  - Base trade count exactly 197
  - Pyramid trade count exactly 27
  - Pyramid contribution to total P&L within 0.5pp of 42.7%

Failure on any line = HALT, surface to Joshua, no Phase C.
"""
from pathlib import Path
import csv
import sys

CSV_TRADES = Path("data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv")

BASELINE_PF_ALL = 2.7528
BASELINE_PF_BASE = 2.3294
BASELINE_WORST_LOSS = -11871.0
BASELINE_BASE_N = 197
BASELINE_PYRAMID_N = 27
BASELINE_PYRAMID_PCT = 42.7
TOLERANCE = 0.005  # 0.5%
PCT_TOLERANCE_PP = 0.5  # absolute percentage points for pyramid-contribution check

NOMINAL_R_USD = 2000.0  # $200K x 1.00%


def to_float(s):
    return float(s.replace(",", "").strip()) if s else 0.0


def load_entries():
    """Filter CSV to Type=='Entry long' (one row per trade) per Q-DJ30-1 convention."""
    with CSV_TRADES.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if r["Type"] == "Entry long"]


def compute_pf(pnls):
    pos = sum(p for p in pnls if p > 0)
    neg = sum(p for p in pnls if p < 0)
    return pos / abs(neg) if neg else float("inf")


def main():
    entries = load_entries()
    bases = [r for r in entries if r["Signal"] == "Long"]
    pyramids = [r for r in entries if r["Signal"] == "Long Add"]

    n_total = len(entries)
    n_base = len(bases)
    n_pyramid = len(pyramids)

    all_pnls = [to_float(r["Net P&L USD"]) for r in entries]
    base_pnls = [to_float(r["Net P&L USD"]) for r in bases]
    pyr_pnls = [to_float(r["Net P&L USD"]) for r in pyramids]
    pf_all = compute_pf(all_pnls)
    pf_base = compute_pf(base_pnls)
    worst_loss = min(base_pnls)
    pyr_pct = 100.0 * sum(pyr_pnls) / sum(all_pnls)

    print(f"=== Q-DJ30-2 Phase B - baseline reproduction ===")
    print(f"CSV: {CSV_TRADES}")
    print(f"  Total entries (Type=='Entry long')        : {n_total}")
    print(f"  Base entries (Signal=='Long')             : {n_base}")
    print(f"  Pyramid entries (Signal=='Long Add')      : {n_pyramid}")
    print(f"  PF all entries (n=224)                    : {pf_all:.4f}")
    print(f"  PF base only (n=197)                      : {pf_base:.4f}")
    print(f"  Base worst single-trade loss              : ${worst_loss:,.2f}")
    print(f"  Pyramid contribution to total P&L         : {pyr_pct:.2f}%")
    print()

    pf_all_drift = abs(pf_all - BASELINE_PF_ALL) / BASELINE_PF_ALL
    pf_base_drift = abs(pf_base - BASELINE_PF_BASE) / BASELINE_PF_BASE
    worst_drift = abs(worst_loss - BASELINE_WORST_LOSS) / abs(BASELINE_WORST_LOSS)
    pyr_pct_drift = abs(pyr_pct - BASELINE_PYRAMID_PCT)

    gates = [
        ("Base count == 197", n_base == BASELINE_BASE_N, f"got {n_base}"),
        ("Pyramid count == 27", n_pyramid == BASELINE_PYRAMID_N, f"got {n_pyramid}"),
        ("PF (n=224) within 0.5% of 2.7528", pf_all_drift <= TOLERANCE, f"PF={pf_all:.4f}, drift={pf_all_drift*100:.2f}%"),
        ("PF (n=197 base) within 0.5% of 2.3294", pf_base_drift <= TOLERANCE, f"PF={pf_base:.4f}, drift={pf_base_drift*100:.2f}%"),
        ("Worst loss within 0.5% of -$11,871", worst_drift <= TOLERANCE, f"loss=${worst_loss:,.2f}, drift={worst_drift*100:.2f}%"),
        ("Pyramid contribution within 0.5pp of 42.7%", pyr_pct_drift <= PCT_TOLERANCE_PP, f"pct={pyr_pct:.2f}%, drift={pyr_pct_drift:.2f}pp"),
    ]

    print(f"=== Gate results ===")
    all_pass = True
    for name, passed, detail in gates:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}  ({detail})")
        if not passed:
            all_pass = False
    print()

    if not all_pass:
        print("HALT: reproduction gate failed. Surface to Joshua before any Phase C work.")
        print("CSV / brief snapshot mismatch is a question, not something to paper over.")
        sys.exit(1)

    print("=== Top 20 worst base trades (entry rows) ===")
    print(f"{'rank':>4} {'trade#':>7} {'date':>17} {'pnl_usd':>12} {'pnl_R':>7} {'mae_usd':>12} {'mae_R':>7}")
    sorted_bases = sorted(bases, key=lambda r: to_float(r["Net P&L USD"]))
    for i, r in enumerate(sorted_bases[:20], 1):
        pnl = to_float(r["Net P&L USD"])
        mae = to_float(r["Adverse excursion USD"])
        # MAE in TV is reported as positive magnitude; sign is implicit (against position)
        print(f"  {i:>2}. {r['Trade #']:>4}  {r['Date and time']:>17}  "
              f"${pnl:>10,.2f}  {pnl/NOMINAL_R_USD:>+6.2f}  ${-abs(mae):>10,.2f}  {-abs(mae)/NOMINAL_R_USD:>+6.2f}")
    print()
    print("Phase B PASS. Proceed to Phase C.")


if __name__ == "__main__":
    main()
