"""
1R diagnosis — equity-normalized 1R recompute for Guardian v5.5.

Hypothesis: realized 1R median 0.58% / mean 0.66% of fixed $200K vs designed 0.34%
is an equity-compounding normalization artefact. Pine sizes off strategy.equity
(contemporaneous), so $ losses scale with equity growth. Normalizing those $ losses
to fixed $200K systematically inflates the realized risk %.

Confirmation: compute realized_loss / equity_at_entry (and equity_at_close) per
losing trade. If median ≈ 0.34%, hypothesis confirmed.

Inputs:
  data/tv_exports/oanda/Guardian_Gold_v5.5_OANDA_XAUUSD_2026-04-25_9ae1f.csv

Pine sizing block (verbatim, guardian_gold_v5.5.txt:192-194):
    calcSize(stopDist) =>
        risk = strategy.equity * (riskPerTrade / 100)
        stopDist > 0 ? risk / stopDist : 0
"""

from __future__ import annotations

import csv
import statistics
from pathlib import Path

INITIAL_CAPITAL = 200_000.0
DESIGNED_RISK_PCT = 0.34  # Guardian risk locked 2026-04-23
CSV_PATH = (
    Path(__file__).parent.parent
    / "data"
    / "tv_exports"
    / "oanda"
    / "Guardian_Gold_v5.5_OANDA_XAUUSD_2026-04-25_9ae1f.csv"
)


def parse_trades(csv_path: Path) -> list[dict]:
    """Collapse the Entry+Exit pairs into one row per trade, ordered by Trade #."""
    trades: dict[int, dict] = {}
    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            tnum = int(row["Trade #"])
            entry = trades.setdefault(tnum, {"trade_num": tnum})
            kind = row["Type"].lower()
            if kind.startswith("entry"):
                entry["entry_price"] = float(row["Price USD"])
                entry["entry_dt"] = row["Date and time"]
            else:  # exit
                entry["exit_price"] = float(row["Price USD"])
                entry["exit_dt"] = row["Date and time"]
                entry["qty"] = float(row["Size (qty)"])
                entry["size_value"] = float(row["Size (value)"])
                entry["pnl"] = float(row["Net P&L USD"])
                entry["pnl_pct_notional"] = float(row["Net P&L %"])
                entry["cum_pnl"] = float(row["Cumulative P&L USD"])
                entry["signal"] = row["Signal"]
    out = sorted(trades.values(), key=lambda t: t["trade_num"])
    return out


def reconstruct_equity(trades: list[dict]) -> None:
    """Add equity_at_entry and equity_at_close to each trade in place.

    Pine sizes at entry, so equity_at_entry is the relevant denominator;
    equity_at_close is reported for completeness as the brief specifies.
    """
    running = INITIAL_CAPITAL
    for t in trades:
        t["equity_at_entry"] = running
        running += t["pnl"]
        t["equity_at_close"] = running


def summarize(values: list[float], label: str) -> dict:
    return {
        "label": label,
        "n": len(values),
        "median": statistics.median(values),
        "mean": statistics.mean(values),
        "min": min(values),
        "max": max(values),
        "p25": statistics.quantiles(values, n=4)[0],
        "p75": statistics.quantiles(values, n=4)[2],
    }


def fmt(stats: dict) -> str:
    return (
        f"{stats['label']:<40} n={stats['n']:>3} "
        f"median={stats['median']:.4f}%  mean={stats['mean']:.4f}%  "
        f"p25={stats['p25']:.4f}%  p75={stats['p75']:.4f}%  "
        f"min={stats['min']:.4f}%  max={stats['max']:.4f}%"
    )


def main() -> None:
    trades = parse_trades(CSV_PATH)
    reconstruct_equity(trades)

    total = len(trades)
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] < 0]
    breakevens = [t for t in trades if t["pnl"] == 0]

    print("=" * 88)
    print("Guardian v5.5 -- 1R diagnosis on OANDA panel (2022-01-11 -> 2026-04-23)")
    print("=" * 88)
    print(f"Total trades:     {total}")
    print(f"Wins (pnl > 0):   {len(wins)}")
    print(f"Losses (pnl < 0): {len(losses)}")
    print(f"Breakevens (pnl == 0): {len(breakevens)}")
    print(f"Win rate (wins / total):   {100.0 * len(wins) / total:.2f}%")
    print(f"Win rate (wins / decided): {100.0 * len(wins) / (len(wins) + len(losses)):.2f}%")
    print()

    # 1R measurements — three normalizations, all on the same loss panel.
    losses_abs_usd = [abs(t["pnl"]) for t in losses]
    losses_pct_initial = [100.0 * abs(t["pnl"]) / INITIAL_CAPITAL for t in losses]
    losses_pct_entry = [
        100.0 * abs(t["pnl"]) / t["equity_at_entry"] for t in losses
    ]
    losses_pct_close = [
        100.0 * abs(t["pnl"]) / t["equity_at_close"] for t in losses
    ]

    print("Loss magnitude in $:")
    s = {
        "label": "abs(loss) USD",
        "n": len(losses_abs_usd),
        "median": statistics.median(losses_abs_usd),
        "mean": statistics.mean(losses_abs_usd),
        "min": min(losses_abs_usd),
        "max": max(losses_abs_usd),
        "p25": statistics.quantiles(losses_abs_usd, n=4)[0],
        "p75": statistics.quantiles(losses_abs_usd, n=4)[2],
    }
    print(
        f"  median=${s['median']:>9,.0f}  mean=${s['mean']:>9,.0f}  "
        f"p25=${s['p25']:>9,.0f}  p75=${s['p75']:>9,.0f}  "
        f"min=${s['min']:>9,.0f}  max=${s['max']:>9,.0f}"
    )
    print()

    print("1R as percent (three normalizations):")
    print(f"  designed risk per trade: {DESIGNED_RISK_PCT:.2f}%")
    print()
    print(fmt(summarize(losses_pct_initial, "loss / fixed $200K (current doc)")))
    print(fmt(summarize(losses_pct_entry, "loss / equity_at_entry (Pine sizes here)")))
    print(fmt(summarize(losses_pct_close, "loss / equity_at_close")))
    print()

    # Equity-growth context.
    final_equity = trades[-1]["equity_at_close"] if trades else INITIAL_CAPITAL
    avg_entry_equity = statistics.mean(t["equity_at_entry"] for t in trades)
    print("Equity context:")
    print(f"  Initial capital:        ${INITIAL_CAPITAL:>12,.0f}")
    print(f"  Final equity:           ${final_equity:>12,.0f}  ({final_equity / INITIAL_CAPITAL:.2f}x)")
    print(f"  Avg equity-at-entry:    ${avg_entry_equity:>12,.0f}  ({avg_entry_equity / INITIAL_CAPITAL:.2f}x)")
    print()

    # Trade-count reconciliation (A.3).
    canonical_trades = 201
    canonical_wr = 20.40
    canonical_wins = round(canonical_trades * canonical_wr / 100.0)
    canonical_losses = canonical_trades - canonical_wins
    print("A.3 — trade-count reconciliation:")
    print(f"  CSV total / wins / losses / BE: {total} / {len(wins)} / {len(losses)} / {len(breakevens)}")
    print(
        f"  Canonical (201 trades, 20.40% WR): "
        f"{canonical_trades} / {canonical_wins} / {canonical_losses} / 0"
    )
    print(f"  Δ trades:  {total - canonical_trades:+d}")
    print(f"  Δ wins:    {len(wins) - canonical_wins:+d}")
    print(f"  Δ losses:  {len(losses) - canonical_losses:+d}")
    print(f"  Δ BE:      {len(breakevens) - 0:+d}")
    print()

    # Sanity — Pine sizes risk = equity * 0.34%; expected $ at risk per trade.
    print("Sanity — Pine designed risk vs realized loss in $:")
    expected_risk_at_initial = INITIAL_CAPITAL * DESIGNED_RISK_PCT / 100.0
    expected_risk_at_avg_entry = avg_entry_equity * DESIGNED_RISK_PCT / 100.0
    print(f"  designed $ risk @ initial $200K equity:   ${expected_risk_at_initial:,.0f}")
    print(f"  designed $ risk @ avg entry equity:       ${expected_risk_at_avg_entry:,.0f}")
    print(f"  realized median loss:                     ${statistics.median(losses_abs_usd):,.0f}")
    print(f"  realized mean   loss:                     ${statistics.mean(losses_abs_usd):,.0f}")


if __name__ == "__main__":
    main()
