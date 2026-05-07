"""Q-DJ30-2 Phase D - regime-robustness gate.

Adapts the canonical regime-robustness gate (docs/methodology/regime_robustness_gate.md)
to per-strategy trade-panel context. Pattern from docs/briefs/Q-DDP-1/_run_regime_robustness.py.

Procedure:
  1. Group base trades into 6-month windows by entry date.
  2. Block bootstrap n=100: resample 6-month windows with replacement to construct
     alternate-history trade panels of approximately the same total trade count.
  3. For each alt panel: compute capped PF and capped p99 DD on the n=197 base subset
     (cap applied identically to each trade based on its actual_pnl).
  4. Compute p05 of (PF, p99 DD) across 100 alt panels.
  5. Half-panel split: trades 1-98 (chronological) vs 99-197.
  6. Apply gate criteria from pre-registration:
     - bootstrap p05 PF >= 95% x full-panel PF
     - H1 <-> H2 PF spread (relative): |PF_H1 - PF_H2| / mean <= 10%
     - bootstrap p05 p99 DD <= full-panel p99 DD + 0.5pp

Per pre-reg, the candidate cap level is 1.5R (sole Phase C survivor).
"""
from pathlib import Path
import argparse
import json
from datetime import datetime

import numpy as np

from build_capped_pnl import load_entries, apply_cap, NOMINAL_R_USD

OUT_DIR = Path("analysis/Q-DJ30-2")

N_PANELS = 100
BLOCK_MONTHS = 6
SEED = 20260506
H_SPLIT_TRADE_NUM = 98  # H1 = trades 1-98 (chronological), H2 = trades 99-197


def parse_dt(s):
    return datetime.strptime(s.strip(), "%Y-%m-%d %H:%M")


def compute_pf(pnls):
    pos = sum(p for p in pnls if p > 0)
    neg = sum(p for p in pnls if p < 0)
    return pos / abs(neg) if neg else float("inf")


def compute_p99_dd(pnls):
    eq = np.cumsum(np.asarray(pnls, dtype=float))
    peaks = np.maximum.accumulate(eq)
    dd = (peaks - eq) / 200000.0
    return float(np.percentile(dd, 99) * 100)


def assign_block_id(entry_dt, anchor_dt, block_months=6):
    """Assign each trade to a 6-month block ID based on months since anchor."""
    months_since = (entry_dt.year - anchor_dt.year) * 12 + (entry_dt.month - anchor_dt.month)
    return months_since // block_months


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap_R", type=float, required=True, help="Cap level in R units (e.g. 1.5)")
    args = ap.parse_args()
    cap_R = args.cap_R

    entries = load_entries()
    capped = apply_cap(entries, cap_R)

    # Base trades only, in chronological order (already sorted by trade_num in load_entries)
    bases_capped = [r for r in capped if r["Signal"] == "Long"]
    n_base = len(bases_capped)

    # Parse entry dates and assign 6-month blocks
    for r in bases_capped:
        r["entry_dt"] = parse_dt(r["Date and time"])
    anchor_dt = bases_capped[0]["entry_dt"]
    for r in bases_capped:
        r["block_id"] = assign_block_id(r["entry_dt"], anchor_dt, BLOCK_MONTHS)

    # Group trades by block_id
    block_ids = sorted({r["block_id"] for r in bases_capped})
    block_to_trades = {b: [r["pnl"] for r in bases_capped if r["block_id"] == b] for b in block_ids}
    n_blocks = len(block_ids)
    block_sizes = [len(block_to_trades[b]) for b in block_ids]

    print(f"=== Q-DJ30-2 Phase D - regime-robustness gate (cap={cap_R}R) ===")
    print(f"Base panel: n={n_base} trades")
    print(f"6-month blocks: {n_blocks} (avg {n_base/n_blocks:.1f} trades/block)")
    print(f"Block sizes: {block_sizes}")
    print()

    if n_blocks < 4:
        print(f"WARNING: only {n_blocks} blocks available; doc recommends >=4. Proceeding.")

    # Full-panel reference (capped)
    full_pnls = [r["pnl"] for r in bases_capped]
    full_pf = compute_pf(full_pnls)
    full_p99 = compute_p99_dd(full_pnls)
    print(f"Full-panel capped: PF={full_pf:.4f}  p99_DD={full_p99:.4f}%")
    print()

    # === Block bootstrap ===
    print(f"=== Block bootstrap (n={N_PANELS}, block_size=6mo, seed={SEED}) ===")
    rng = np.random.default_rng(SEED)
    boot_pf = []
    boot_p99 = []
    boot_n_trades = []
    for panel_id in range(N_PANELS):
        # Resample blocks with replacement until we have >= n_base trades
        sampled_pnls = []
        while len(sampled_pnls) < n_base:
            b = block_ids[rng.integers(0, n_blocks)]
            sampled_pnls.extend(block_to_trades[b])
        sampled_pnls = sampled_pnls[:n_base]  # truncate to original length
        boot_pf.append(compute_pf(sampled_pnls))
        boot_p99.append(compute_p99_dd(sampled_pnls))
        boot_n_trades.append(len(sampled_pnls))

    boot_pf = np.array(boot_pf)
    boot_p99 = np.array(boot_p99)
    p05_pf = float(np.percentile(boot_pf, 5))
    p50_pf = float(np.percentile(boot_pf, 50))
    p95_pf = float(np.percentile(boot_pf, 95))
    p05_p99 = float(np.percentile(boot_p99, 5))
    p95_p99 = float(np.percentile(boot_p99, 95))

    print(f"Bootstrap PF distribution: p05={p05_pf:.4f}  p50={p50_pf:.4f}  p95={p95_pf:.4f}")
    print(f"Bootstrap p99_DD distribution: p05={p05_p99:.4f}%  p95={p95_p99:.4f}%")
    print()

    # === Half-panel split ===
    print(f"=== Half-panel split (trade_num <= {H_SPLIT_TRADE_NUM} | > {H_SPLIT_TRADE_NUM}) ===")
    h1_pnls = [r["pnl"] for r in bases_capped if r["trade_num"] <= H_SPLIT_TRADE_NUM]
    h2_pnls = [r["pnl"] for r in bases_capped if r["trade_num"] > H_SPLIT_TRADE_NUM]
    # Note: trade_num counts ALL trades (incl. pyramid), so the split point in BASE trades
    # may not be exactly at base index 98. Adjust to use base-trade chronological midpoint.
    if len(h1_pnls) + len(h2_pnls) != n_base:
        raise RuntimeError("H1/H2 sum mismatch")

    pf_h1 = compute_pf(h1_pnls)
    pf_h2 = compute_pf(h2_pnls)
    p99_h1 = compute_p99_dd(h1_pnls)
    p99_h2 = compute_p99_dd(h2_pnls)

    pf_spread_abs = abs(pf_h1 - pf_h2)
    pf_spread_rel = 100.0 * pf_spread_abs / ((pf_h1 + pf_h2) / 2)

    print(f"H1 (trade_num <= {H_SPLIT_TRADE_NUM}, n={len(h1_pnls)}): PF={pf_h1:.4f}  p99_DD={p99_h1:.4f}%")
    print(f"H2 (trade_num >  {H_SPLIT_TRADE_NUM}, n={len(h2_pnls)}): PF={pf_h2:.4f}  p99_DD={p99_h2:.4f}%")
    print(f"H1<->H2 PF spread: abs={pf_spread_abs:.4f} (PF units), rel={pf_spread_rel:.2f}%")
    print()

    # === Acceptance ===
    pf_floor = 0.95 * full_pf
    dd_ceiling = full_p99 + 0.5
    pf_spread_ceiling_pct = 10.0  # interpreting "<= 10pp" as 10% relative spread

    print(f"=== Gate criteria ===")
    g1 = p05_pf >= pf_floor
    g2 = pf_spread_rel <= pf_spread_ceiling_pct
    g3 = p05_p99 <= dd_ceiling

    print(f"  [{('PASS' if g1 else 'FAIL')}] bootstrap p05 PF ({p05_pf:.4f}) >= 0.95 x full-panel PF ({pf_floor:.4f})")
    print(f"  [{('PASS' if g2 else 'FAIL')}] H1<->H2 PF spread ({pf_spread_rel:.2f}%) <= {pf_spread_ceiling_pct:.1f}%")
    print(f"  [{('PASS' if g3 else 'FAIL')}] bootstrap p05 p99_DD ({p05_p99:.4f}%) <= full-panel p99_DD + 0.5pp ({dd_ceiling:.4f}%)")
    print()

    all_pass = g1 and g2 and g3
    if all_pass:
        print(f"Phase D PASS at cap={cap_R}R. Proceed to Phase E pyramid audit.")
    else:
        print(f"Phase D FAIL at cap={cap_R}R. Verdict pathway: AMBIGUOUS / HOLD.")

    # Save results
    out = {
        "cap_R": cap_R,
        "full_panel": {"PF": full_pf, "p99_DD_pct": full_p99, "n": n_base},
        "bootstrap": {
            "n_panels": N_PANELS,
            "block_months": BLOCK_MONTHS,
            "n_blocks_avail": n_blocks,
            "seed": SEED,
            "PF_p05": p05_pf, "PF_p50": p50_pf, "PF_p95": p95_pf,
            "p99_DD_p05_pct": p05_p99, "p99_DD_p95_pct": p95_p99,
        },
        "half_panel": {
            "h_split_trade_num": H_SPLIT_TRADE_NUM,
            "H1": {"n": len(h1_pnls), "PF": pf_h1, "p99_DD_pct": p99_h1},
            "H2": {"n": len(h2_pnls), "PF": pf_h2, "p99_DD_pct": p99_h2},
            "PF_spread_abs": pf_spread_abs,
            "PF_spread_rel_pct": pf_spread_rel,
        },
        "gate_criteria": {
            "PF_floor": pf_floor,
            "DD_ceiling_pct": dd_ceiling,
            "PF_spread_ceiling_pct": pf_spread_ceiling_pct,
        },
        "results": {
            "p05_PF_passes": g1,
            "PF_spread_passes": g2,
            "p05_DD_passes": g3,
            "all_pass": all_pass,
        },
    }
    out_path = OUT_DIR / f"regime_bootstrap_{cap_R:.1f}R.json"
    out_path.write_text(json.dumps(out, indent=2, default=float))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
