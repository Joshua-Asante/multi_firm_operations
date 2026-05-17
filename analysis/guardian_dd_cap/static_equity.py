"""
Static-equity recomputation: strip the TV compounding cascade.

TradingView's strategy tester uses strategy.equity (compounded) for sizing.
DXTrade live execution uses static initial capital ($200K) at the locked
0.34% risk per trade. So per the trade-csv-reconcile sub-rule on static
sizing, the CSV-implied dollar P&L overstates live $ on winning streaks
and understates on losing streaks.

The CSV's Net P&L % column is per-trade return on then-current equity —
that's the size-invariant per-trade signal we want. Sum of % returns
(without compounding) gives the static-equity-equivalent P&L.

If the +$144K compound advantage shrinks toward zero under static sizing,
the 2.6% > 1.6% claim collapses for the FXIFY use case.
"""
from __future__ import annotations
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

CSV_26 = Path(r"C:\Users\joshu\Downloads\Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-17_1a38a.csv")
CSV_16 = Path(r"C:\Users\joshu\Downloads\Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-17_90bb1.csv")
INITIAL_CAPITAL = 200_000.0
SPLIT_MIDPOINT = datetime(2024, 3, 1)
N_BOOTSTRAP = 10_000


def load_trades(path: Path) -> list[dict]:
    by_trade: dict[int, dict[str, list]] = defaultdict(lambda: {"entry": [], "exit": []})
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tnum = int(row["Trade #"])
            row_type = row["Type"]
            if row_type.startswith("Entry"):
                by_trade[tnum]["entry"].append(row)
            elif row_type.startswith("Exit"):
                by_trade[tnum]["exit"].append(row)
    trades = []
    for tnum in sorted(by_trade):
        legs = by_trade[tnum]
        exit_ = legs["exit"][0]
        entry = legs["entry"][0]
        trades.append({
            "trade_num": tnum,
            "entry_dt": datetime.strptime(entry["Date and time"], "%Y-%m-%d %H:%M"),
            "exit_dt": datetime.strptime(exit_["Date and time"], "%Y-%m-%d %H:%M"),
            "net_pnl": float(exit_["Net P&L USD"]),
            "net_pnl_pct": float(exit_["Net P&L %"]),  # % return on equity-at-entry
            "exit_signal": exit_["Signal"],
        })
    return trades


def static_metrics(trades: list[dict]) -> dict:
    """Compute static-equity-equivalent metrics: $ P&L = pct * $200K, no compounding."""
    # Each trade's P&L in dollars if account stayed at $200K
    static_pnl = np.array([t["net_pnl_pct"] / 100.0 * INITIAL_CAPITAL for t in trades])
    n = len(trades)
    wins = static_pnl[static_pnl > 0]
    losses = static_pnl[static_pnl <= 0]
    pf = wins.sum() / abs(losses.sum()) if len(losses) > 0 else float("inf")
    wr = len(wins) / n * 100
    net = static_pnl.sum()
    equity = INITIAL_CAPITAL + np.cumsum(static_pnl)
    equity_with_initial = np.concatenate(([INITIAL_CAPITAL], equity))
    peak = np.maximum.accumulate(equity_with_initial)
    dd_pct = (peak - equity_with_initial) / peak * 100
    dd_dollar = peak - equity_with_initial
    return {
        "n": n,
        "wr_pct": wr,
        "pf": pf,
        "net": net,
        "max_dd_pct": float(dd_pct.max()),
        "max_dd_dollar": float(dd_dollar.max()),
        "rf": net / dd_dollar.max() if dd_dollar.max() > 0 else float("inf"),
        "static_pnls": static_pnl,
    }


def main():
    trades_26 = load_trades(CSV_26)
    trades_16 = load_trades(CSV_16)
    m26 = static_metrics(trades_26)
    m16 = static_metrics(trades_16)

    print("=" * 72)
    print("Static-equity recomputation (per-trade % * $200K, no compounding)")
    print("=" * 72)
    print(f"{'Metric':<20}{'2.6% DD':>15}{'1.6% DD':>15}{'delta':>18}")
    print("-" * 68)
    for key, label in [("n", "N"), ("wr_pct", "WR %"), ("pf", "PF"),
                        ("net", "Net $ (static)"),
                        ("max_dd_pct", "Max DD %"),
                        ("max_dd_dollar", "Max DD $ (static)"),
                        ("rf", "RF")]:
        v26 = m26[key]
        v16 = m16[key]
        delta = v26 - v16
        if "pct" in key or key == "wr_pct":
            print(f"{label:<20}{v26:>15.2f}{v16:>15.2f}{delta:>+18.2f}")
        else:
            print(f"{label:<20}{v26:>15,.2f}{v16:>15,.2f}{delta:>+18,.2f}")

    print()
    print("Comparison to compounded TV values:")
    print(f"  Net (compounded)  delta = +$144,269 -> Net (static) delta = ${m26['net']-m16['net']:+,.0f}")
    print(f"  Pct compound contribution to headline delta: "
          f"{(144269 - (m26['net']-m16['net'])) / 144269 * 100:.1f}%")

    # Half-panel OOS on static-equity numbers
    print()
    print(f"Half-panel OOS (static-equity, split = {SPLIT_MIDPOINT.date()})")
    for label, midpoint_cmp in [("H1", lambda dt: dt < SPLIT_MIDPOINT),
                                  ("H2", lambda dt: dt >= SPLIT_MIDPOINT)]:
        t26 = [t for t in trades_26 if midpoint_cmp(t["exit_dt"])]
        t16 = [t for t in trades_16 if midpoint_cmp(t["exit_dt"])]
        m_h26 = static_metrics(t26)
        m_h16 = static_metrics(t16)
        print(f"\n--- {label} (n={len(t26)} vs {len(t16)}) ---")
        for key, label_m, favorable in [
            ("net", "Net $ (static)", "positive"),
            ("pf", "PF", "positive"),
            ("max_dd_pct", "Max DD %", "negative"),
        ]:
            v26 = m_h26[key]
            v16 = m_h16[key]
            delta = v26 - v16
            if favorable == "positive":
                direction = "OK (2.6% wins)" if delta > 0 else "FAIL"
            else:
                direction = "OK (2.6% wins)" if delta < 0 else "FAIL"
            if "net" in key or "dollar" in key:
                print(f"  {label_m:<20}{v26:>14,.0f}{v16:>14,.0f}{delta:>+14,.0f}  {direction}")
            else:
                print(f"  {label_m:<20}{v26:>14.3f}{v16:>14.3f}{delta:>+14.3f}  {direction}")

    # Bootstrap CI on static deltas
    print()
    print(f"Bootstrap CI on static-equity deltas (n_resamples={N_BOOTSTRAP})")
    rng_a = np.random.default_rng(20260517)
    rng_b = np.random.default_rng(20260518)
    n_a = len(trades_26)
    n_b = len(trades_16)
    pnls_a = m26["static_pnls"]
    pnls_b = m16["static_pnls"]
    # Net
    boot_net_a = np.array([pnls_a[rng_a.integers(0, n_a, size=n_a)].sum() for _ in range(N_BOOTSTRAP)])
    boot_net_b = np.array([pnls_b[rng_b.integers(0, n_b, size=n_b)].sum() for _ in range(N_BOOTSTRAP)])
    delta_net = boot_net_a - boot_net_b
    print(f"  Net (static) median delta=${np.median(delta_net):+,.0f}  "
          f"CI95=[${np.percentile(delta_net,2.5):+,.0f}, ${np.percentile(delta_net,97.5):+,.0f}]  "
          f"{'OK' if np.percentile(delta_net,2.5)>0 else 'FAIL (CI includes 0)'}")

    # PF
    rng_a = np.random.default_rng(20260517)
    rng_b = np.random.default_rng(20260518)
    def pf_boot(pnls, n, rng):
        out = np.empty(N_BOOTSTRAP)
        for i in range(N_BOOTSTRAP):
            s = pnls[rng.integers(0, n, size=n)]
            w = s[s > 0].sum()
            l = abs(s[s <= 0].sum())
            out[i] = w / l if l > 0 else float("inf")
        return out
    boot_pf_a = pf_boot(pnls_a, n_a, rng_a)
    boot_pf_b = pf_boot(pnls_b, n_b, rng_b)
    delta_pf = boot_pf_a - boot_pf_b
    finite_mask = np.isfinite(delta_pf)
    delta_pf_finite = delta_pf[finite_mask]
    print(f"  PF                  median delta={np.median(delta_pf_finite):+.3f}  "
          f"CI95=[{np.percentile(delta_pf_finite,2.5):+.3f}, {np.percentile(delta_pf_finite,97.5):+.3f}]  "
          f"{'OK' if np.percentile(delta_pf_finite,2.5)>0 else 'FAIL (CI includes 0)'}")


if __name__ == "__main__":
    main()
