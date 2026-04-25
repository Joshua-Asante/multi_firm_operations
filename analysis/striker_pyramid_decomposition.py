"""
Striker pyramid decomposition.

Context. The 1R diagnosis (`analysis/1r_diagnosis.py`) found Guardian's mean
per-loss matches designed 0.34%. Striker mean per-loss = 1.17% vs designed
1.00% — a ~17% mean (not tail) inflation. User hypothesis: this is a mixture
of two very different distributions — single-entry trades hitting close to
1R and pyramid-extended trades spending >1R on the trade-group when a single
bar gaps through layer-1 protection and stops out the larger pyramid layer.

This script tests the hypothesis empirically. Two decomposition cuts:

  (1) Per-Trade-# loss%, split by signal class:
        Long / Short      = initial entry
        Long Add / Short Add = pyramid layer (Striker uses a 350% pyramid
        sizing parameter; layer-2 qty ~3-4x layer-1 qty)
      If the pyramid-layer distribution has a higher mean than the initial-
      entry distribution, the 17% Striker inflation is concentrated in the
      pyramid bucket and the framing should be "pyramid sizing model" not
      "Striker tail."

  (2) Per-trade-group loss%, where a "trade-group" is the set of contiguous
      Trade #s sharing an exit bar (initial + any pyramid layers that
      closed at the same time). Sum of group's per-Trade losses as % of
      equity at the group's first entry = total $ spent by that signal-
      rooted position. This is the metric that maps to "single bar
      stopping out layer 1 + layer 2 spends >1R."
"""

from __future__ import annotations

import csv
import statistics
from pathlib import Path

INITIAL_CAPITAL = 200_000.0
DESIGNED_RISK_PCT = 1.00  # Striker locked
CSV_PATH = (
    Path(__file__).parent.parent
    / "data"
    / "tv_exports"
    / "oanda"
    / "Striker_DJ30_v4.4_OANDA_US30USD_2026-04-25_86e9d.csv"
)


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
                t["entry_price"] = float(row["Price USD"])
                t["entry_signal"] = row["Signal"]
                t["qty"] = float(row["Size (qty)"])
            else:
                t["exit_dt"] = row["Date and time"]
                t["exit_price"] = float(row["Price USD"])
                t["pnl"] = float(row["Net P&L USD"])
                t["exit_signal"] = row["Signal"]
    out = sorted(trades.values(), key=lambda t: t["trade_num"])
    running = INITIAL_CAPITAL
    for t in out:
        t["equity_at_entry"] = running
        running += t["pnl"]
    return out


def is_pyramid_entry(signal: str) -> bool:
    return "Add" in signal


def summarize_pcts(values: list[float], label: str) -> None:
    if not values:
        print(f"  {label:<35} (empty)")
        return
    qs = statistics.quantiles(values, n=4) if len(values) >= 4 else (None, None, None)
    print(
        f"  {label:<35} n={len(values):>3} "
        f"mean={statistics.mean(values):.4f}%  "
        f"median={statistics.median(values):.4f}%  "
        f"p25={qs[0]:.4f}%  p75={qs[2]:.4f}%  "
        f"max={max(values):.4f}%"
    )


def main() -> None:
    trades = parse_trades(CSV_PATH)

    initial = [t for t in trades if not is_pyramid_entry(t["entry_signal"])]
    pyramid_layers = [t for t in trades if is_pyramid_entry(t["entry_signal"])]

    init_losses = [t for t in initial if t["pnl"] < 0]
    pyr_losses = [t for t in pyramid_layers if t["pnl"] < 0]

    print("=" * 100)
    print("Striker v4.4 -- pyramid decomposition (OANDA panel 2022-01-04 -> 2026-04-25)")
    print("=" * 100)
    print(f"Total Trade #s:           {len(trades)}")
    print(f"  Initial entries:        {len(initial)}  (signal: 'Long'/'Short')")
    print(f"  Pyramid layers:         {len(pyramid_layers)}  (signal: 'Long Add'/'Short Add')")
    print(f"  Pyramid penetration:    {100.0 * len(pyramid_layers) / len(initial):.1f}% of initials extended")
    print()
    print(f"Loss decomposition (loss / equity_at_entry, %):")
    print(f"  designed Striker risk per trade: {DESIGNED_RISK_PCT:.2f}%")
    print()
    init_pct = [100.0 * abs(t["pnl"]) / t["equity_at_entry"] for t in init_losses]
    pyr_pct = [100.0 * abs(t["pnl"]) / t["equity_at_entry"] for t in pyr_losses]
    summarize_pcts(init_pct, "Initial-entry losses")
    summarize_pcts(pyr_pct, "Pyramid-layer losses")
    print()
    print(f"  Initial mean inflation vs designed: {(statistics.mean(init_pct) / DESIGNED_RISK_PCT - 1) * 100:+.1f}%")
    if pyr_pct:
        print(f"  Pyramid mean inflation vs designed: {(statistics.mean(pyr_pct) / DESIGNED_RISK_PCT - 1) * 100:+.1f}%")

    # Pyramid qty multiplier sanity check.
    # For each pyramid layer, find the immediately-preceding initial in the same signal direction
    # (assumes pyramid layers are appended right after their root in trade order).
    print()
    print("Pyramid sizing multiplier (qty_pyramid / qty_initial):")
    multipliers = []
    for i, t in enumerate(trades):
        if is_pyramid_entry(t["entry_signal"]) and i > 0:
            prev = trades[i - 1]
            if not is_pyramid_entry(prev["entry_signal"]):
                if prev["qty"] > 0:
                    multipliers.append(t["qty"] / prev["qty"])
    if multipliers:
        summarize_pcts([m * 100 for m in multipliers], "pyramid_qty / initial_qty (x100)")
        print(f"  -> mean qty multiplier: {statistics.mean(multipliers):.2f}x  "
              f"(matches '350% pyramid' parameter? {abs(statistics.mean(multipliers) - 3.5) < 0.5})")

    # Trade-group decomposition: contiguous Trade #s sharing the same exit_dt.
    print()
    print("Trade-group decomposition (initial + same-bar pyramid exits collapsed):")
    groups: list[list[dict]] = []
    current: list[dict] = []
    for t in trades:
        if not is_pyramid_entry(t["entry_signal"]):
            if current:
                groups.append(current)
            current = [t]
        else:
            # Pyramid layer attaches to the most recent initial only if exit_dt aligns
            # AND it follows the initial in trade order without an intervening initial.
            if current and t["exit_dt"] == current[-1]["exit_dt"]:
                current.append(t)
            elif current:
                # Pyramid layer with different exit time — treat as part of current group anyway
                # (pyramid still attached to the initial, just exited at a different bar).
                current.append(t)
    if current:
        groups.append(current)

    group_sizes = [len(g) for g in groups]
    print(f"  Total groups: {len(groups)}")
    print(f"  Group-size distribution: "
          f"1-leg={sum(1 for s in group_sizes if s == 1)}  "
          f"2-leg={sum(1 for s in group_sizes if s == 2)}  "
          f"3-leg+={sum(1 for s in group_sizes if s >= 3)}")
    print()

    # Per-group summary by group size.
    for size in (1, 2, 3):
        subset = [g for g in groups if (len(g) == size if size < 3 else len(g) >= 3)]
        if not subset:
            continue
        # Total $ P&L per group, normalized by equity at first entry of the group.
        all_pcts = [
            100.0 * sum(t["pnl"] for t in g) / g[0]["equity_at_entry"]
            for g in subset
        ]
        loss_pcts = [100.0 * abs(sum(t["pnl"] for t in g)) / g[0]["equity_at_entry"]
                     for g in subset if sum(t["pnl"] for t in g) < 0]
        win_count = sum(1 for g in subset if sum(t["pnl"] for t in g) > 0)
        loss_count = sum(1 for g in subset if sum(t["pnl"] for t in g) < 0)
        be_count = len(subset) - win_count - loss_count
        label = f"{size}-leg" if size < 3 else "3+ leg"
        print(f"  Group size {label}: n={len(subset)}  W={win_count}/L={loss_count}/BE={be_count}")
        if loss_pcts:
            summarize_pcts(loss_pcts, f"  group-loss% ({label})")
        # Largest single-group loss for reporting.
        if loss_pcts:
            print(f"    max group-loss%:  {max(loss_pcts):.4f}%")
        print()

    # Re-cal trigger framing.
    print("Re-cal trigger candidacy framing:")
    init_mean = statistics.mean(init_pct)
    print(f"  Initial-entry mean         = {init_mean:.4f}% "
          f"({(init_mean / DESIGNED_RISK_PCT - 1) * 100:+.1f}% vs designed)")
    if pyr_pct:
        pyr_mean = statistics.mean(pyr_pct)
        print(f"  Pyramid-layer mean         = {pyr_mean:.4f}% "
              f"({(pyr_mean / DESIGNED_RISK_PCT - 1) * 100:+.1f}% vs designed)")
    all_loss_pct = init_pct + pyr_pct
    overall_mean = statistics.mean(all_loss_pct)
    print(f"  Combined per-Trade-# mean  = {overall_mean:.4f}% "
          f"({(overall_mean / DESIGNED_RISK_PCT - 1) * 100:+.1f}% vs designed) "
          "<- this is the 17% number")


if __name__ == "__main__":
    main()
