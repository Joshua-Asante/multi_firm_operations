#!/usr/bin/env python3
"""§7.2-style acceptance: re-aggregate Silver TV-export vs Q-CORR-1.1 amendment §7 refs.

Set ``Q_CORR_SILVER_TV_CSV`` to a Guardian v5.5-on-Silver XAGUSD Pepperstone export.
CI skips when unset.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd


def main() -> int:
    p = os.environ.get("Q_CORR_SILVER_TV_CSV")
    if not p:
        print("SKIP: Q_CORR_SILVER_TV_CSV unset")
        return 0
    csv_path = Path(p)
    if not csv_path.is_file():
        print(f"FAIL: missing {csv_path}", file=sys.stderr)
        return 1

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    exits = df[df["Type"].astype(str).str.startswith("Exit")].copy()
    n_trades = len(exits)
    pnl = exits["Net P&L USD"].astype(float)
    wins = (pnl > 0).sum()
    wr = 100.0 * wins / n_trades if n_trades else 0.0
    pos = pnl[pnl > 0].sum()
    neg = pnl[pnl < 0].sum()
    pf = pos / abs(neg) if neg < 0 else float("inf")
    eq = pnl.cumsum()
    peak = eq.cummax()
    dd = float(((peak - eq) / 200_000.0).max() * 100.0)

    # Amendment §7 reference (brief §7.2): 238 trades / PF 1.613 / WR 11.34% / DD 14.99%.
    # DD-convention amendment 2026-05-13: reference DD was originally 11.52%
    # (TV's compounded-peak basis from the Q-CORR-1.1 amendment §7 panel);
    # corrected to 14.99% (static-equity notional $200K basis) to match this
    # implementation and the codebase's standing static-equity convention
    # (trade-csv-reconcile skill trap #9). Empirical: dc6a3 dump computes
    # DD = 11.52% compounded-peak = 14.99% notional.
    ref_n, ref_pf, ref_wr, ref_dd = 238, 1.613, 11.34, 14.99
    ok = (
        abs(n_trades - ref_n) <= 2
        and abs(pf - ref_pf) < 0.05
        and abs(wr - ref_wr) < 1.0
        and abs(dd - ref_dd) < 1.0
    )
    print(f"n_trades={n_trades} PF={pf:.3f} WR={wr:.2f}% maxDD%={dd:.2f}")
    if not ok:
        print("FAIL: outside tolerance vs amendment §7 reference", file=sys.stderr)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
