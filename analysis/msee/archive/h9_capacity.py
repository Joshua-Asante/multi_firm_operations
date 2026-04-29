"""MSEE H9 — Capacity audit per strategy.

Q-MSEE-9 from docs/methodology/msee/open_questions.md.

The strict H9 design (progressively scale lot sizes until slippage-
adjusted PF falls 20%) requires a calibrated lot-dependent slippage
model. The o7_slippage_realism scaffold characterizes execution-gap
*types* (intra / gap_minor / reopen_w) but does not quantify lot-
dependent slippage. Without that calibration, the strict capacity
test would require pure speculation on slippage(lots) functional form.

This script therefore performs a capacity AUDIT rather than the strict
test:

  (a) per-strategy lot-size distribution from the OANDA TV exports
      (the lot size used is `Size (qty)` for shares/contracts, scaled
       to $200K account by the strategy's risk_pct convention),
  (b) MAE_pct distribution as a current-state slippage proxy
      (rising MAE_pct in good regimes is the H6 condition-2 proxy
       captured separately),
  (c) account-scaling extrapolation: at $200K, $500K, $1M, $2M what
      lot sizes would the locked Pine sizing produce (linearly scaled
      via the multiplier from cli.py),
  (d) a flag listing the slippage-model inputs required to run the
      strict capacity test.

Falsifier (for the prediction Aegis>Guardian>Striker capacity):
cannot be tested without a slippage model. The audit produces the
inputs that would be needed and flags the gap explicitly.

PRE-Q GATE:
  D: Restricted to current locked instruments and their TV-export lot
     records.
  S: Distribution + extrapolation only.
  A: Bounded; one-shot.

Reproducibility: `python analysis/msee/h9_capacity.py`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "identify" / "2026-04-26"))

from common import STRATEGIES, PARAMS, load_tv  # noqa: E402

OUT_JSON = ROOT / "analysis" / "msee" / "h9_capacity_audit.json"

ACCOUNT_SCALE_GRID = [200_000, 500_000, 1_000_000, 2_000_000, 5_000_000]
BASELINE_ACCOUNT = 200_000


def per_strategy_audit(strategy: str) -> dict:
    tv = load_tv(strategy)
    tv = tv.dropna(subset=["entry_time", "exit_time", "net_pnl_pct"]).copy()
    qty = tv["Size (qty)"].astype(float)
    mae = tv["mae_pct"].abs().fillna(0.0)
    return {
        "n_trades": int(len(tv)),
        "lot_qty_distribution": {
            "min": float(qty.min()),
            "p25": float(qty.quantile(0.25)),
            "median": float(qty.median()),
            "p75": float(qty.quantile(0.75)),
            "max": float(qty.max()),
        },
        "mae_pct_distribution_abs": {
            "median": float(mae.median()),
            "p75": float(mae.quantile(0.75)),
            "p95": float(mae.quantile(0.95)),
            "max": float(mae.max()),
        },
        "scaling_grid_lot_qty_at_account": {
            str(acct): {
                "multiplier": float(acct / BASELINE_ACCOUNT),
                "median_lot_qty": float(qty.median() * acct / BASELINE_ACCOUNT),
                "max_lot_qty": float(qty.max() * acct / BASELINE_ACCOUNT),
            }
            for acct in ACCOUNT_SCALE_GRID
        },
    }


def main() -> None:
    audits = {s: per_strategy_audit(s) for s in STRATEGIES}

    summary = {
        "question": "Q-MSEE-9 — capacity audit (H9; strict test deferred)",
        "feed": "OANDA",
        "canonical_status": "PROXY",
        "strict_test_status": "DEFERRED",
        "deferred_reason": (
            "The strict capacity test (progressively scale lots until "
            "slippage-adjusted PF falls 20%) requires a calibrated "
            "lot-dependent slippage model. The o7 slippage scaffold "
            "characterizes execution-gap types but does not quantify "
            "slippage(lots). Audit inputs produced; strict test gated on "
            "model availability."
        ),
        "required_inputs_for_strict_test": [
            "Lot-dependent slippage function slippage(lots, instrument, "
            "regime) calibrated to live DXTrade fills (not in scope of "
            "current OANDA-proxy corpus).",
            "Per-instrument depth-of-book or market-impact estimates for "
            "XAUUSD, US30USD, USDJPY at the user's broker (Pepperstone or "
            "FXIFY/Alchemy DXTrade).",
            "Threshold definition for 'PF falls 20%' as a hard bar vs a "
            "soft monotone decline.",
        ],
        "predicted_capacity_ordering": "Aegis > Guardian > Striker (per source report Part V)",
        "per_strategy": audits,
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2, default=str))

    print("MSEE H9 — Capacity audit (strict test DEFERRED — needs slippage model)")
    print()
    print(f"  Per-strategy lot-qty distribution (current $200K baseline panel):")
    for s in STRATEGIES:
        d = audits[s]
        ld = d["lot_qty_distribution"]
        m = d["mae_pct_distribution_abs"]
        print(f"    {s:10s}  n={d['n_trades']:3d}  lots: "
              f"min={ld['min']:.2f}  med={ld['median']:.2f}  "
              f"p75={ld['p75']:.2f}  max={ld['max']:.2f}")
        print(f"    {' ':10s}  MAE: med={m['median']*100:.3f}%  "
              f"p75={m['p75']*100:.3f}%  p95={m['p95']*100:.3f}%  "
              f"max={m['max']*100:.3f}%")
    print()
    print(f"  Account-scaling extrapolation (locked Pine sizing × multiplier):")
    print(f"    {'account':>11s}  " +
          "  ".join(f"{s+'_med':>13s}" for s in STRATEGIES))
    for acct in ACCOUNT_SCALE_GRID:
        cells = "  ".join(
            f"{audits[s]['scaling_grid_lot_qty_at_account'][str(acct)]['median_lot_qty']:>13,.2f}"
            for s in STRATEGIES
        )
        print(f"    ${acct:>10,d}  {cells}")
    print()
    print(f"  Strict test status: DEFERRED")
    print(f"  Required inputs: see {OUT_JSON.name}")
    print()
    print(f"Wrote: {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
