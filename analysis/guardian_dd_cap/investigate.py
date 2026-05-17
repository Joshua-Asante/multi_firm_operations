"""
Guardian v5.5 daily-DD cap investigation: 2.6% vs 1.6%.

Falsifiable H (declared 2026-05-17):
  H_alt: daily_dd_cap=2.6% Pareto-dominates 1.6% on Pepperstone 52mo panel
         with (a) both halves of chronological OOS split confirming direction
         on net, PF, and %DD, AND (b) bootstrap CI on deltas excluding zero
         for all three metrics.
  H_null: any of (net, PF, %DD) fails OOS direction check or fails to exclude
          zero in bootstrap CI.

Convention pin (per Q-CORR-1 §10 lesson — split convention must be declared
before evaluator runs):
  - Half-panel split = chronological midpoint of CALENDAR DATE range.
  - Date range: 2022-01-11 → 2026-04-20 = 1561 days → midpoint = 2024-03-01.
  - Trades whose Exit date is < midpoint → first half.
  - Trades whose Exit date is >= midpoint → second half.

Bootstrap convention:
  - Method: independent block bootstrap per CSV (block size = 1 trade,
    since Guardian's slow-trade regime ~4-day mean inter-trade interval
    makes serial correlation negligible at the per-trade level).
  - Resamples: 10,000.
  - CI: percentile method, 95% (2.5th and 97.5th).
  - Delta: 2.6% metric MINUS 1.6% metric.
    Favorable direction for H_alt: net > 0, PF > 0, %DD < 0.
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
SPLIT_MIDPOINT = datetime(2024, 3, 1)  # declared convention
N_BOOTSTRAP = 10_000
RNG_SEED = 20260517


def load_trades(path: Path) -> list[dict]:
    """Parse TV CSV, group by Trade #, return one dict per trade with Exit-row P&L."""
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
        if not legs["entry"] or not legs["exit"]:
            raise ValueError(f"Trade {tnum} missing entry or exit leg")
        # Guardian has no pyramids — exactly 1 entry + 1 exit per trade
        if len(legs["entry"]) != 1 or len(legs["exit"]) != 1:
            raise ValueError(
                f"Trade {tnum}: unexpected leg count entry={len(legs['entry'])} "
                f"exit={len(legs['exit'])}"
            )
        entry = legs["entry"][0]
        exit_ = legs["exit"][0]
        trades.append({
            "trade_num": tnum,
            "entry_dt": datetime.strptime(entry["Date and time"], "%Y-%m-%d %H:%M"),
            "exit_dt": datetime.strptime(exit_["Date and time"], "%Y-%m-%d %H:%M"),
            "entry_price": float(entry["Price USD"]),
            "exit_price": float(exit_["Price USD"]),
            "qty": float(exit_["Size (qty)"]),
            "size_value": float(exit_["Size (value)"]),
            "net_pnl": float(exit_["Net P&L USD"]),
            "net_pnl_pct": float(exit_["Net P&L %"]),
            "exit_signal": exit_["Signal"],
            "fav_excursion": float(exit_["Favorable excursion USD"]),
            "adv_excursion": float(exit_["Adverse excursion USD"]),
            "cum_pnl": float(exit_["Cumulative P&L USD"]),
        })
    return trades


def headline_metrics(trades: list[dict]) -> dict:
    """Compute N, WR, PF, Net, %DD, RF, 1R (median loss)."""
    pnls = np.array([t["net_pnl"] for t in trades])
    n = len(trades)
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]
    gross_win = wins.sum()
    gross_loss = abs(losses.sum())
    pf = gross_win / gross_loss if gross_loss > 0 else float("inf")
    wr = len(wins) / n * 100
    net = pnls.sum()
    # Equity curve on $200K initial
    equity = INITIAL_CAPITAL + np.cumsum(pnls)
    equity_with_initial = np.concatenate(([INITIAL_CAPITAL], equity))
    running_peak = np.maximum.accumulate(equity_with_initial)
    drawdowns_pct = (running_peak - equity_with_initial) / running_peak * 100
    drawdowns_dollar = running_peak - equity_with_initial
    max_dd_pct = drawdowns_pct.max()
    max_dd_dollar = drawdowns_dollar.max()
    rf = net / max_dd_dollar if max_dd_dollar > 0 else float("inf")
    # 1R = median loss (Guardian methodology per trade-csv-reconcile skill)
    r_dollars = float(abs(np.median(losses))) if len(losses) > 0 else float("nan")
    return {
        "n": n,
        "wr_pct": wr,
        "pf": pf,
        "net": net,
        "gross_win": gross_win,
        "gross_loss": gross_loss,
        "avg_win": float(wins.mean()) if len(wins) > 0 else 0.0,
        "avg_loss": float(losses.mean()) if len(losses) > 0 else 0.0,
        "max_dd_pct": max_dd_pct,
        "max_dd_dollar": max_dd_dollar,
        "rf": rf,
        "r_dollars": r_dollars,
        "n_losses": len(losses),
    }


def split_by_date(trades: list[dict], midpoint: datetime) -> tuple[list, list]:
    """Split trades into two halves by Exit date relative to midpoint."""
    h1 = [t for t in trades if t["exit_dt"] < midpoint]
    h2 = [t for t in trades if t["exit_dt"] >= midpoint]
    return h1, h2


def bootstrap_metric(trades: list[dict], metric_fn, n_resamples: int, rng: np.random.Generator) -> np.ndarray:
    """Block bootstrap (block=1 trade) — returns array of n_resamples metric values."""
    n = len(trades)
    pnls = np.array([t["net_pnl"] for t in trades])
    out = np.empty(n_resamples)
    for i in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        out[i] = metric_fn(pnls[idx])
    return out


def metric_net(pnls: np.ndarray) -> float:
    return float(pnls.sum())


def metric_pf(pnls: np.ndarray) -> float:
    wins = pnls[pnls > 0].sum()
    losses = abs(pnls[pnls <= 0].sum())
    return wins / losses if losses > 0 else float("inf")


def metric_max_dd_pct(pnls: np.ndarray) -> float:
    equity = INITIAL_CAPITAL + np.cumsum(pnls)
    equity_with_initial = np.concatenate(([INITIAL_CAPITAL], equity))
    running_peak = np.maximum.accumulate(equity_with_initial)
    drawdowns_pct = (running_peak - equity_with_initial) / running_peak * 100
    return float(drawdowns_pct.max())


def main():
    trades_26 = load_trades(CSV_26)
    trades_16 = load_trades(CSV_16)

    print("=" * 72)
    print("Step 1: Inventory and CSV reconciliation")
    print("=" * 72)
    print(f"2.6% DD CSV: n={len(trades_26)} trades")
    print(f"1.6% DD CSV: n={len(trades_16)} trades")
    print(f"2.6% first trade: #{trades_26[0]['trade_num']} entry={trades_26[0]['entry_dt']} pnl=${trades_26[0]['net_pnl']:,.2f}")
    print(f"1.6% first trade: #{trades_16[0]['trade_num']} entry={trades_16[0]['entry_dt']} pnl=${trades_16[0]['net_pnl']:,.2f}")
    print(f"2.6% last trade : #{trades_26[-1]['trade_num']} exit={trades_26[-1]['exit_dt']} cum=${trades_26[-1]['cum_pnl']:,.2f}")
    print(f"1.6% last trade : #{trades_16[-1]['trade_num']} exit={trades_16[-1]['exit_dt']} cum=${trades_16[-1]['cum_pnl']:,.2f}")

    print()
    print("=" * 72)
    print("Step 2: Headline metrics (full panel)")
    print("=" * 72)
    m26 = headline_metrics(trades_26)
    m16 = headline_metrics(trades_16)
    print(f"{'Metric':<20}{'2.6% DD':>15}{'1.6% DD':>15}{'delta (2.6-1.6)':>18}")
    print("-" * 65)
    for key, label in [("n", "N"), ("wr_pct", "WR %"), ("pf", "PF"),
                        ("net", "Net $"), ("avg_win", "Avg win $"),
                        ("avg_loss", "Avg loss $"), ("max_dd_pct", "Max DD %"),
                        ("max_dd_dollar", "Max DD $"), ("rf", "RF"),
                        ("r_dollars", "1R $ (median loss)")]:
        v26 = m26[key]
        v16 = m16[key]
        delta = v26 - v16
        if "pct" in key or "wr" in key:
            print(f"{label:<20}{v26:>15.2f}{v16:>15.2f}{delta:>+15.2f}")
        else:
            print(f"{label:<20}{v26:>15,.2f}{v16:>15,.2f}{delta:>+15,.2f}")

    # TV reconcile
    print()
    print("Reconcile vs TV screenshots:")
    print(f"  2.6% — TV: 201 / +$596,747.92 / PF 3.935 / 6.10% DD / 22.39% WR")
    print(f"  2.6% — CSV: {m26['n']} / +${m26['net']:,.2f} / PF {m26['pf']:.3f} / {m26['max_dd_pct']:.2f}% DD / {m26['wr_pct']:.2f}% WR")
    print(f"  1.6% — TV: 207 / +$452,478.53 / PF 3.457 / 7.86% DD / 22.71% WR")
    print(f"  1.6% — CSV: {m16['n']} / +${m16['net']:,.2f} / PF {m16['pf']:.3f} / {m16['max_dd_pct']:.2f}% DD / {m16['wr_pct']:.2f}% WR")

    print()
    print("=" * 72)
    print(f"Step 3: Half-panel OOS split (chronological midpoint = {SPLIT_MIDPOINT.date()})")
    print("=" * 72)
    h1_26, h2_26 = split_by_date(trades_26, SPLIT_MIDPOINT)
    h1_16, h2_16 = split_by_date(trades_16, SPLIT_MIDPOINT)
    print(f"H1 (< {SPLIT_MIDPOINT.date()}): 2.6%={len(h1_26)}t, 1.6%={len(h1_16)}t")
    print(f"H2 (>= {SPLIT_MIDPOINT.date()}): 2.6%={len(h2_26)}t, 1.6%={len(h2_16)}t")

    for label, t26, t16 in [("H1", h1_26, h1_16), ("H2", h2_26, h2_16)]:
        m_h26 = headline_metrics(t26)
        m_h16 = headline_metrics(t16)
        print()
        print(f"--- {label} ---")
        print(f"{'Metric':<15}{'2.6%':>14}{'1.6%':>14}{'delta':>14}{'Direction':>20}")
        for key, label_m, favorable in [
            ("net", "Net $", "positive"),
            ("pf", "PF", "positive"),
            ("max_dd_pct", "Max DD %", "negative"),
        ]:
            v26 = m_h26[key]
            v16 = m_h16[key]
            delta = v26 - v16
            if favorable == "positive":
                direction_ok = "OK (2.6% wins)" if delta > 0 else "FAIL"
            else:
                direction_ok = "OK (2.6% wins)" if delta < 0 else "FAIL"
            if key == "net":
                print(f"{label_m:<15}{v26:>14,.0f}{v16:>14,.0f}{delta:>+14,.0f}{direction_ok:>20}")
            else:
                print(f"{label_m:<15}{v26:>14.3f}{v16:>14.3f}{delta:>+14.3f}{direction_ok:>20}")

    print()
    print("=" * 72)
    print(f"Step 4: Bootstrap CI on deltas (n_resamples={N_BOOTSTRAP})")
    print("=" * 72)
    rng = np.random.default_rng(RNG_SEED)
    for metric_label, metric_fn, favorable in [
        ("Net $", metric_net, "positive"),
        ("PF", metric_pf, "positive"),
        ("Max DD %", metric_max_dd_pct, "negative"),
    ]:
        # Use independent seeds for the two CSVs to avoid spurious correlation
        rng_a = np.random.default_rng(RNG_SEED)
        rng_b = np.random.default_rng(RNG_SEED + 1)
        boot_26 = bootstrap_metric(trades_26, metric_fn, N_BOOTSTRAP, rng_a)
        boot_16 = bootstrap_metric(trades_16, metric_fn, N_BOOTSTRAP, rng_b)
        deltas = boot_26 - boot_16
        ci_low = np.percentile(deltas, 2.5)
        ci_high = np.percentile(deltas, 97.5)
        median_delta = np.median(deltas)
        if favorable == "positive":
            excludes_zero = ci_low > 0
            verdict = "OK (2.6% > 1.6% with 95% CI)" if excludes_zero else "FAIL (CI includes 0)"
        else:
            excludes_zero = ci_high < 0
            verdict = "OK (2.6% < 1.6% with 95% CI)" if excludes_zero else "FAIL (CI includes 0)"
        fmt = "{:>14,.0f}" if metric_label == "Net $" else "{:>14.3f}"
        print(f"{metric_label:<12}  median delta={fmt.format(median_delta)}  "
              f"CI95=[{fmt.format(ci_low)}, {fmt.format(ci_high)}]  {verdict}")

    print()
    print("=" * 72)
    print("Step 5: Mechanism decomposition")
    print("=" * 72)
    # Pair trades by Entry datetime (signal time) to see overlap
    entries_26 = {t["entry_dt"]: t for t in trades_26}
    entries_16 = {t["entry_dt"]: t for t in trades_16}
    common_keys = set(entries_26) & set(entries_16)
    only_26 = set(entries_26) - set(entries_16)
    only_16 = set(entries_16) - set(entries_26)
    print(f"Trades with same entry datetime in both CSVs: {len(common_keys)}")
    print(f"Trades only in 2.6%: {len(only_26)}")
    print(f"Trades only in 1.6%: {len(only_16)}")

    # P&L of incremental 1.6% trades
    incremental_16_pnl = [entries_16[k]["net_pnl"] for k in only_16]
    if incremental_16_pnl:
        arr = np.array(incremental_16_pnl)
        print(f"\nIncremental 1.6% trades P&L profile:")
        print(f"  count: {len(arr)}")
        print(f"  sum:   ${arr.sum():,.2f}")
        print(f"  mean:  ${arr.mean():,.2f}")
        print(f"  median:${float(np.median(arr)):,.2f}")
        print(f"  wins:  {(arr > 0).sum()}/{len(arr)} = {(arr > 0).mean()*100:.1f}%")
        print(f"  PF:    {arr[arr>0].sum() / abs(arr[arr<=0].sum()):.3f}" if (arr<=0).any() else "  PF:    inf (no losses)")
        print(f"  list:  {[(entries_16[k]['entry_dt'].strftime('%Y-%m-%d'), entries_16[k]['net_pnl'], entries_16[k]['exit_signal']) for k in sorted(only_16)]}")

    # P&L on common trades — same trade, different sizing because of equity compounding
    common_26_pnl = sum(entries_26[k]["net_pnl"] for k in common_keys)
    common_16_pnl = sum(entries_16[k]["net_pnl"] for k in common_keys)
    print(f"\nCommon-trade P&L (sized off each CSV's compounded equity):")
    print(f"  2.6%: ${common_26_pnl:,.2f}")
    print(f"  1.6%: ${common_16_pnl:,.2f}")
    print(f"  delta: ${common_26_pnl - common_16_pnl:,.2f}")
    print(f"  ratio: {common_26_pnl / common_16_pnl:.3f}x (this reflects compounding cascade, not signal quality)")

    # Exit-signal mix per CSV
    print(f"\nExit-signal distribution:")
    for csv_label, trades in [("2.6%", trades_26), ("1.6%", trades_16)]:
        sig_counts = defaultdict(int)
        sig_pnl = defaultdict(float)
        for t in trades:
            sig_counts[t["exit_signal"]] += 1
            sig_pnl[t["exit_signal"]] += t["net_pnl"]
        print(f"  {csv_label}:")
        for sig in sorted(sig_counts):
            print(f"    {sig:<20} n={sig_counts[sig]:>3}  sum=${sig_pnl[sig]:>+12,.0f}  mean=${sig_pnl[sig]/sig_counts[sig]:>+8,.0f}")


if __name__ == "__main__":
    main()
