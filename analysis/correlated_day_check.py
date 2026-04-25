"""
Correlated-day pressure test across G+S+A on the OANDA panels.

Brief context. The 1R diagnosis (`analysis/1r_diagnosis.py`) closed the per-trade
compounding question for Guardian: median full-stop loss ≈ 0.34% of contemporaneous
equity. The single-trade-max framing (max 0.6806%, ~2× designed) is the wrong frame
for FXIFY's 5% daily DD; what matters is correlated multi-strategy days. This
script aggregates per-strategy losses by NY-tz calendar date (UTC - 5 fixed
approximation; tz precision is not load-bearing for this metric — clusters are
robust to a few hours of bin drift) and reports the worst combined days as a
percent of contemporaneous equity.

Each strategy's "loss as percent of equity_at_entry" is computed from that
strategy's own single-strategy backtest. Summing across strategies on a given
day represents an upper bound on a "what if all three ran on independent
parallel accounts" basis — slightly conservative for "all three on one combined
account" since combined-equity compounding would make each strategy's per-trade
% slightly smaller during periods of net portfolio gain.

Inputs:
  data/tv_exports/oanda/Guardian_Gold_v5.5_OANDA_XAUUSD_2026-04-25_9ae1f.csv
  data/tv_exports/oanda/Striker_DJ30_v4.4_OANDA_US30USD_2026-04-25_86e9d.csv
  data/tv_exports/oanda/Aegis_USDJPY_v4.3_OANDA_USDJPY_2026-04-25_7ee6b.csv
"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

INITIAL_CAPITAL = 200_000.0
NY_OFFSET = timedelta(hours=-5)  # UTC -> NY (no DST handling; immaterial for clustering)

DATA_DIR = Path(__file__).parent.parent / "data" / "tv_exports" / "oanda"
FILES = {
    "guardian": DATA_DIR / "Guardian_Gold_v5.5_OANDA_XAUUSD_2026-04-25_9ae1f.csv",
    "striker": DATA_DIR / "Striker_DJ30_v4.4_OANDA_US30USD_2026-04-25_86e9d.csv",
    "aegis": DATA_DIR / "Aegis_USDJPY_v4.3_OANDA_USDJPY_2026-04-25_7ee6b.csv",
}


def parse_trades(csv_path: Path) -> list[dict]:
    trades: dict[int, dict] = {}
    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            tnum = int(row["Trade #"])
            t = trades.setdefault(tnum, {"trade_num": tnum})
            kind = row["Type"].lower()
            if kind.startswith("entry"):
                t["entry_dt"] = row["Date and time"]
            else:
                t["exit_dt"] = row["Date and time"]
                t["pnl"] = float(row["Net P&L USD"])
    out = sorted(trades.values(), key=lambda t: t["trade_num"])
    running = INITIAL_CAPITAL
    for t in out:
        t["equity_at_entry"] = running
        running += t["pnl"]
        t["equity_at_close"] = running
    return out


def ny_date(dt_str: str) -> str:
    """CSV timestamp -> NY calendar date (YYYY-MM-DD)."""
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    return (dt + NY_OFFSET).strftime("%Y-%m-%d")


def collect_losses(trades: list[dict]) -> list[dict]:
    out = []
    for t in trades:
        if t["pnl"] < 0:
            out.append(
                {
                    "exit_date": ny_date(t["exit_dt"]),
                    "loss_usd": abs(t["pnl"]),
                    "loss_pct": 100.0 * abs(t["pnl"]) / t["equity_at_entry"],
                    "equity_at_entry": t["equity_at_entry"],
                }
            )
    return out


def main() -> None:
    all_strategies = {name: collect_losses(parse_trades(p)) for name, p in FILES.items()}

    # Aggregate by NY date.
    daily = defaultdict(lambda: {"guardian": 0.0, "striker": 0.0, "aegis": 0.0,
                                  "guardian_n": 0, "striker_n": 0, "aegis_n": 0,
                                  "total_pct": 0.0})
    for strat, losses in all_strategies.items():
        for L in losses:
            d = daily[L["exit_date"]]
            d[strat] += L["loss_pct"]
            d[strat + "_n"] += 1
            d["total_pct"] += L["loss_pct"]

    # Top-N worst combined days.
    days_sorted = sorted(daily.items(), key=lambda kv: -kv[1]["total_pct"])

    print("=" * 100)
    print("Correlated-day pressure test (G+S+A on OANDA panels, NY-tz approx)")
    print("=" * 100)
    print(f"Per-strategy panel summary (full-stop and partial losses combined):")
    for strat, losses in all_strategies.items():
        total_loss_pct = sum(L["loss_pct"] for L in losses)
        n = len(losses)
        n_days_with_loss = len({L["exit_date"] for L in losses})
        print(
            f"  {strat:<10} n_losses={n:>4}  "
            f"n_loss_days={n_days_with_loss:>4}  "
            f"total_loss%_summed={total_loss_pct:>7.2f}%  "
            f"mean_per_loss={total_loss_pct / n:.4f}%"
        )

    print()
    print(f"Days with multi-strategy losses (count by # of strategies hit on same day):")
    multi_counts = {1: 0, 2: 0, 3: 0}
    for d, agg in daily.items():
        n_strats = sum(1 for s in ("guardian", "striker", "aegis") if agg[s + "_n"] > 0)
        multi_counts[n_strats] = multi_counts.get(n_strats, 0) + 1
    print(f"  1-strategy loss-days: {multi_counts[1]:>4}")
    print(f"  2-strategy loss-days: {multi_counts[2]:>4}")
    print(f"  3-strategy loss-days: {multi_counts[3]:>4}")
    print(f"  total loss-days     : {sum(multi_counts.values()):>4}")
    print()

    print("Top 15 worst combined days by total loss % of equity_at_entry:")
    print(f"  {'date':<12} {'total%':>8}  {'G%':>7}  {'S%':>7}  {'A%':>7}  "
          f"{'Gn':>3} {'Sn':>3} {'An':>3}")
    print(f"  {'-'*12} {'-'*8}  {'-'*7}  {'-'*7}  {'-'*7}  "
          f"{'-'*3} {'-'*3} {'-'*3}")
    for d, agg in days_sorted[:15]:
        print(
            f"  {d:<12} {agg['total_pct']:>7.4f}%  "
            f"{agg['guardian']:>6.4f}%  "
            f"{agg['striker']:>6.4f}%  "
            f"{agg['aegis']:>6.4f}%  "
            f"{agg['guardian_n']:>3} {agg['striker_n']:>3} {agg['aegis_n']:>3}"
        )

    # Distribution percentiles of total daily loss %.
    totals = sorted([agg["total_pct"] for agg in daily.values()])
    n = len(totals)

    def pct(q: float) -> float:
        i = int(q * (n - 1))
        return totals[i]

    print()
    print(f"Daily-total loss% distribution across {n} loss-days:")
    print(f"  p50  = {pct(0.50):.4f}%")
    print(f"  p75  = {pct(0.75):.4f}%")
    print(f"  p90  = {pct(0.90):.4f}%")
    print(f"  p95  = {pct(0.95):.4f}%")
    print(f"  p99  = {pct(0.99):.4f}%")
    print(f"  max  = {totals[-1]:.4f}%")
    print()

    # Reference checkpoints — FXIFY daily limit + dd_protection trigger.
    print("Pressure-test reference frame:")
    print(f"  FXIFY daily DD floor          : 5.00%")
    print(f"  dd_protection trigger         : 1.00% (drawdown from peak; cuts day's sizing 0.40x)")
    print(f"  portfolio_mc p99 DD (calibrated): 4.94% (full-portfolio trajectory, not single-day)")
    print(f"  observed worst combined day   : {totals[-1]:.4f}%  ({days_sorted[0][0]})")
    print(f"  observed p99 combined day     : {pct(0.99):.4f}%")


if __name__ == "__main__":
    main()
