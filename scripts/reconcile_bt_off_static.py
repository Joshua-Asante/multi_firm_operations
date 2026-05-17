"""Reconcile BT-OFF Pepperstone panels under static-equity recomputation.

Replaces the prior TV-CSV compounded headline (strategy.equity * risk%) with
the FXIFY-equivalent static-equity headline (sum of per-trade Net P&L % * $200K,
no compounding).

Pyramid-aware: groups by Trade #, attributes P&L from Exit rows only, counts
base vs pyramid_add entries via the Type/Signal columns. Per-strategy 1R uses
the trade-csv-reconcile skill's methodology table (Guardian=median loss,
all others=mean of |losses| > 1% of $200K with median fallback at n=0).

Usage:
    python scripts/reconcile_bt_off_static.py            # all 4 canonical panels
    python scripts/reconcile_bt_off_static.py guardian   # single strategy
"""
from __future__ import annotations
import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
PEPP = REPO / "data" / "tv_exports" / "pepperstone"
INITIAL = 200_000.0

# Canonical BT-OFF + static-equity panels (2026-05-17).
PANELS = {
    "guardian": {
        "csv": "Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-17_90bb1.csv",
        "label": "Guardian Gold v5.5",
        "instrument": "XAUUSD",
        "r_method": "median_loss",
        "prior_anchor": "Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-05_33781.csv",
    },
    "aegis": {
        "csv": "Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-05-17_836cc.csv",
        "label": "Aegis USDJPY v4.3",
        "instrument": "USDJPY",
        "r_method": "full_stop_mean",
        "prior_anchor": "Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-04-26_0bf1b.csv",
    },
    "striker_dj30": {
        "csv": "Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-17_c0b35.csv",
        "label": "Striker DJ30 v4.5",
        "instrument": "US30",
        "r_method": "full_stop_mean",
        "prior_anchor": "Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv",
    },
    "striker_nas100": {
        "csv": "Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-17_cd2b6.csv",
        "label": "Striker NAS100 v1",
        "instrument": "NAS100",
        "r_method": "full_stop_mean",
        "prior_anchor": "Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-05_7ca6f.csv",
    },
}


def load(path: Path) -> list[dict]:
    """Group by Trade #; attribute P&L from Exit rows; count base vs pyramid_add entries.

    Returns trades in chronological order by Trade # (which corresponds to TV's
    sequencing). Cumulative P&L USD on the last Exit row of trade N gives the
    equity-after-trade-N (relative to INITIAL); used downstream to reconstruct
    equity_at_entry_N for the static-equity recomputation.
    """
    by_trade: dict[int, dict] = defaultdict(lambda: {"entries": [], "exits": []})
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tnum = int(row["Trade #"])
            row_type = row["Type"]
            if row_type.startswith("Entry"):
                by_trade[tnum]["entries"].append(row)
            elif row_type.startswith("Exit"):
                by_trade[tnum]["exits"].append(row)
    trades = []
    cum_pnl_running = 0.0
    for tnum in sorted(by_trade):
        legs = by_trade[tnum]
        if not legs["entries"] or not legs["exits"]:
            raise ValueError(f"Trade {tnum} missing entry or exit leg in {path.name}")
        # New BT-OFF CSV format: each pyramid add is its own Trade #, not grouped under base
        # Identify pyramid adds via Signal column containing "Add"
        exit_pnl_usd = sum(float(e["Net P&L USD"]) for e in legs["exits"])
        last_exit = legs["exits"][-1]
        first_entry = legs["entries"][0]
        is_pyramid_add = "Add" in first_entry["Signal"]
        # equity_at_entry = INITIAL + cumulative P&L USD BEFORE this trade
        # NOTE: approximate for pyramid adds firing while base still open — TV's
        # strategy.equity includes unrealized P&L which this proxy doesn't capture.
        # Approximation acceptable for intraday-overlap pyramids (small unrealized).
        equity_at_entry = INITIAL + cum_pnl_running
        cum_pnl_running += exit_pnl_usd
        csv_cum = float(last_exit["Cumulative P&L USD"])
        assert abs(csv_cum - cum_pnl_running) < 0.50, (
            f"Trade {tnum} cum P&L mismatch: csv={csv_cum} computed={cum_pnl_running}"
        )
        trades.append({
            "trade_num": tnum,
            "exit_dt": datetime.strptime(last_exit["Date and time"], "%Y-%m-%d %H:%M"),
            "net_pnl_usd": exit_pnl_usd,
            "equity_at_entry": equity_at_entry,
            "entry_signal": first_entry["Signal"],
            "exit_signal": last_exit["Signal"],
            "is_pyramid_add": is_pyramid_add,
        })
    return trades


def static_metrics(trades: list[dict], r_method: str) -> dict:
    """Compute static-equity headline.

    Per-trade scale factor = INITIAL / equity_at_entry. Multiplying compounded
    Net P&L USD by this factor gives the dollar outcome if the position had
    been sized off the FIXED initial $200K (the FXIFY live-execution
    convention) instead of the compounded equity (the TV strategy.equity
    convention).

    Pine sizing line confirmed across all 4 strategies (2026-05-17, user):
        calcSize(stopDist) => risk = strategy.equity * (riskPerTrade / 100)
    """
    static_pnl = np.array([
        t["net_pnl_usd"] * (INITIAL / t["equity_at_entry"]) for t in trades
    ])
    n = len(trades)
    n_pyramid_adds = sum(1 for t in trades if t["is_pyramid_add"])
    n_base = n - n_pyramid_adds
    wins = static_pnl[static_pnl > 0]
    losses = static_pnl[static_pnl < 0]  # strict negative
    flat = static_pnl[static_pnl == 0]
    pf = wins.sum() / abs(losses.sum()) if len(losses) > 0 and abs(losses.sum()) > 0 else float("inf")
    wr = len(wins) / n * 100
    net = static_pnl.sum()
    equity = INITIAL + np.cumsum(static_pnl)
    with_init = np.concatenate(([INITIAL], equity))
    peak = np.maximum.accumulate(with_init)
    dd_pct_curve = (peak - with_init) / peak * 100
    dd_dollar_curve = peak - with_init
    max_dd_pct = float(dd_pct_curve.max())
    max_dd_dollar = float(dd_dollar_curve.max())
    rf = net / max_dd_dollar if max_dd_dollar > 0 else float("inf")
    # 1R per skill methodology
    if r_method == "median_loss":
        if len(losses) > 0:
            r_dollars = float(abs(np.median(losses)))
            r_note = f"median of {len(losses)} losses"
        else:
            r_dollars = float("nan")
            r_note = "no losses"
    elif r_method == "full_stop_mean":
        # Full stops = |loss| > 1% of $200K = $2000
        full_stops = losses[losses < -2000]
        if len(full_stops) > 0:
            r_dollars = float(abs(full_stops.mean()))
            r_note = f"mean of {len(full_stops)} full stops (>$2000)"
            if len(full_stops) < 5:
                r_note += " [COHORT WARNING n<5]"
        elif len(losses) > 0:
            r_dollars = float(abs(np.median(losses)))
            r_note = f"FALLBACK: median of {len(losses)} losses (no full stops)"
        else:
            r_dollars = float("nan")
            r_note = "no losses"
    else:
        raise ValueError(f"Unknown r_method: {r_method}")
    return {
        "n": n,
        "n_base": n_base,
        "n_pyramid_adds": n_pyramid_adds,
        "wr_pct": wr,
        "pf": pf,
        "net_static": net,
        "max_dd_pct": max_dd_pct,
        "max_dd_dollar": max_dd_dollar,
        "rf": rf,
        "r_dollars": r_dollars,
        "r_note": r_note,
        "n_wins": len(wins),
        "n_losses": len(losses),
        "n_flat": len(flat),
    }


def compounded_metrics(trades: list[dict]) -> dict:
    """Compounded headline (sum of Net P&L USD as TV reports it)."""
    pnls = np.array([t["net_pnl_usd"] for t in trades])
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    pf = wins.sum() / abs(losses.sum()) if len(losses) > 0 and abs(losses.sum()) > 0 else float("inf")
    net = pnls.sum()
    equity = INITIAL + np.cumsum(pnls)
    with_init = np.concatenate(([INITIAL], equity))
    peak = np.maximum.accumulate(with_init)
    dd_pct = (peak - with_init) / peak * 100
    return {
        "net": float(net),
        "pf": float(pf),
        "max_dd_pct": float(dd_pct.max()),
    }


def run_one(key: str) -> dict:
    panel = PANELS[key]
    path = PEPP / panel["csv"]
    print(f"\n{'=' * 78}")
    print(f"{panel['label']} — {panel['instrument']} — {panel['csv']}")
    print(f"{'=' * 78}")
    trades = load(path)
    static = static_metrics(trades, panel["r_method"])
    compounded = compounded_metrics(trades)

    print(f"Trade count                  : {static['n']}")
    print(f"  base entries               : {static['n_base']}")
    print(f"  pyramid adds               : {static['n_pyramid_adds']}")
    print(f"WR                           : {static['wr_pct']:.2f}%  "
          f"({static['n_wins']}W / {static['n_losses']}L / {static['n_flat']}F)")
    print()
    print(f"--- COMPOUNDED (TV strategy.equity) ---")
    print(f"Net P&L                      : ${compounded['net']:>14,.2f}")
    print(f"PF                           : {compounded['pf']:>16.3f}")
    print(f"Max DD %                     : {compounded['max_dd_pct']:>16.2f}%")
    print()
    print(f"--- STATIC-EQUITY (FXIFY-equivalent, per-trade % * $200K) ---")
    print(f"Net P&L (static)             : ${static['net_static']:>14,.2f}  "
          f"({static['net_static']/INITIAL*100:+.2f}% on $200K)")
    print(f"PF (static)                  : {static['pf']:>16.3f}")
    print(f"Max DD % (static)            : {static['max_dd_pct']:>16.2f}%")
    print(f"Max DD $ (static)            : ${static['max_dd_dollar']:>14,.2f}")
    print(f"RF (static)                  : {static['rf']:>16.2f}")
    print(f"1R (static)                  : ${static['r_dollars']:>14,.2f}   ({static['r_note']})")
    return {"key": key, "panel": panel, "static": static, "compounded": compounded, "trades": trades}


def main():
    keys = sys.argv[1:] if len(sys.argv) > 1 else list(PANELS)
    results = []
    for k in keys:
        if k not in PANELS:
            print(f"Unknown strategy: {k}. Choose from: {list(PANELS)}")
            sys.exit(1)
        results.append(run_one(k))

    # Summary table
    print()
    print("=" * 78)
    print("SUMMARY (static-equity canonical, BT-OFF Pepperstone, 2026-05-17)")
    print("=" * 78)
    print(f"{'Strategy':<22}{'N':>5}{'WR%':>7}{'PF':>7}{'Net$':>15}{'DD%':>7}{'DD$':>10}{'RF':>7}")
    print("-" * 78)
    for r in results:
        s = r["static"]
        print(f"{r['panel']['label']:<22}{s['n']:>5}{s['wr_pct']:>7.2f}{s['pf']:>7.2f}"
              f"{s['net_static']:>15,.0f}{s['max_dd_pct']:>7.2f}{s['max_dd_dollar']:>10,.0f}{s['rf']:>7.2f}")


if __name__ == "__main__":
    main()
