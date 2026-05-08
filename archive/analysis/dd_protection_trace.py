"""
dd_protection envelope trace — what would the rule have done on 2025-02-07?

Context. The 3.56% Striker single-trade outlier on 2025-02-07 is the
worst-observed single-strategy day in the OANDA panel. The reframed
forward-bucket question is whether this kind of outlier, combined with
realistic correlated-day pairings, sits inside `dd_protection`'s working
envelope. Three branches per the user's framing:

  (a) trigger fired *beforehand* and the live max would be lower than 3.56%
      (because Striker would have been sized at 0.40x that day)
  (b) trigger never engaged because cumulative DD didn't cross 1%, and the
      single-trade outlier passes through untouched
  (c) trigger engaged but post-cut residual was still material

Method. Use percent returns (loss / equity_at_entry) — invariant across
account contexts, so portable from each strategy's own-CSV compounded
sizing onto a unified combined-account simulator. Walk all trades by exit
date through a $200K combined-account model:

  1. At start of NY-tz day d: peak_d = max(peak[<d]), equity_d = equity[<d]
  2. dd_from_peak_d = max(0, (peak_d - equity_d) / peak_d)
  3. multiplier_d = 0.40 if dd_from_peak_d >= 0.010 else 1.00
  4. For each trade exiting on d: equity *= (1 + (pct_return/100) * multiplier_d)

This is a daily-cadence dd_protection simulator — fires once per day at
morning pre-market check, scales every trade that day. Reports the
trigger state on each day plus a focused trace through the 2025-02-07
window.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.mvd import assert_tv_export

INITIAL_CAPITAL = 200_000.0
NY_OFFSET = timedelta(hours=-5)
DD_TRIGGER = 0.010
DD_SCALE = 0.40

DATA_DIR = Path(__file__).parent.parent / "data" / "tv_exports" / "oanda"
FILES = {
    "guardian": DATA_DIR / "Guardian_Gold_v5.5_OANDA_XAUUSD_2026-04-25_9ae1f.csv",
    "striker": DATA_DIR / "Striker_DJ30_v4.4_OANDA_US30USD_2026-04-25_86e9d.csv",
    "aegis": DATA_DIR / "Aegis_USDJPY_v4.3_OANDA_USDJPY_2026-04-25_7ee6b.csv",
}
assert_tv_export(FILES["guardian"], expected_strategy="Guardian", expected_version="v5.5", expected_broker="OANDA", expected_symbol="XAUUSD")
assert_tv_export(FILES["striker"],  expected_strategy="Striker",  expected_version="v4.4", expected_broker="OANDA", expected_symbol="US30USD")
assert_tv_export(FILES["aegis"],    expected_strategy="Aegis",    expected_version="v4.3", expected_broker="OANDA", expected_symbol="USDJPY")


def parse_trades(name: str, csv_path: Path) -> list[dict]:
    trades: dict[int, dict] = {}
    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            tnum = int(row["Trade #"])
            t = trades.setdefault(tnum, {"strategy": name, "trade_num": tnum})
            kind = row["Type"].lower()
            if kind.startswith("entry"):
                t["entry_dt"] = row["Date and time"]
                t["entry_signal"] = row["Signal"]
            else:
                t["exit_dt"] = row["Date and time"]
                t["pnl"] = float(row["Net P&L USD"])
    out = sorted(trades.values(), key=lambda t: t["trade_num"])
    running = INITIAL_CAPITAL
    for t in out:
        t["equity_at_entry"] = running
        running += t["pnl"]
        t["pct_return"] = 100.0 * t["pnl"] / t["equity_at_entry"]
    return out


def ny_date(dt_str: str) -> str:
    return (datetime.strptime(dt_str, "%Y-%m-%d %H:%M") + NY_OFFSET).strftime("%Y-%m-%d")


def main() -> None:
    all_trades: list[dict] = []
    for name, path in FILES.items():
        all_trades.extend(parse_trades(name, path))

    # Order globally by exit datetime then by strategy for determinism.
    all_trades.sort(key=lambda t: (t["exit_dt"], t["strategy"]))

    # Group by NY-tz date.
    by_day: dict[str, list[dict]] = defaultdict(list)
    for t in all_trades:
        by_day[ny_date(t["exit_dt"])].append(t)

    days = sorted(by_day.keys())

    # Walk forward.
    equity = INITIAL_CAPITAL
    peak = INITIAL_CAPITAL
    daily_state: list[dict] = []  # one row per NY-tz day with at least one trade

    trigger_days = 0
    branch_a_days = []  # days where trigger fired AND a Striker single-trade loss > 2%-equivalent existed
    biggest_dd = 0.0
    biggest_dd_date = None

    for d in days:
        eq_start = equity
        peak_start = peak
        dd_from_peak = max(0.0, (peak_start - eq_start) / peak_start) if peak_start > 0 else 0.0
        triggered = dd_from_peak >= DD_TRIGGER
        multiplier = DD_SCALE if triggered else 1.0
        if triggered:
            trigger_days += 1
        if dd_from_peak > biggest_dd:
            biggest_dd = dd_from_peak
            biggest_dd_date = d

        # Apply each trade's % return to the combined-account equity, scaled by multiplier.
        per_strat_pct = {"guardian": 0.0, "striker": 0.0, "aegis": 0.0}
        for t in by_day[d]:
            scaled_pct = t["pct_return"] * multiplier
            equity *= 1 + scaled_pct / 100.0
            per_strat_pct[t["strategy"]] += scaled_pct

        if equity > peak:
            peak = equity

        daily_state.append({
            "date": d,
            "eq_start": eq_start,
            "peak_start": peak_start,
            "dd_from_peak_start": dd_from_peak,
            "triggered": triggered,
            "multiplier": multiplier,
            "n_trades": len(by_day[d]),
            "per_strat_pct": per_strat_pct,
            "eq_end": equity,
            "peak_end": peak,
        })

    # Summary header.
    print("=" * 100)
    print("dd_protection envelope trace — combined G+S+A account, daily-cadence simulator")
    print("=" * 100)
    print(f"Panel:         {days[0]}  ->  {days[-1]}  ({len(days)} trade-days)")
    print(f"Final equity:  ${equity:>14,.0f}  ({equity / INITIAL_CAPITAL:.2f}x initial)")
    print(f"Final peak:    ${peak:>14,.0f}")
    print(f"Trigger days:  {trigger_days} / {len(days)}  ({100.0 * trigger_days / len(days):.1f}%)")
    print(f"Biggest DD-from-peak (start-of-day): {100.0 * biggest_dd:.3f}%  on  {biggest_dd_date}")
    print()

    # Trace the 2025-02-07 window: ten trade-days before, the day itself, and after.
    print("Trace through 2025-02-07 vicinity (the 3.56% Striker outlier day):")
    print(f"  {'date':<12} {'eq_start':>13} {'peak_start':>13} {'dd%':>7}  trig  mult  "
          f"{'G%':>7}  {'S%':>7}  {'A%':>7}  {'eq_end':>13}")
    target = "2025-02-07"
    target_idx = next((i for i, r in enumerate(daily_state) if r["date"] == target), None)
    if target_idx is None:
        print(f"  Target date {target} not found in trade-day list (no trades that day).")
        # Fall back: nearest day with a Striker loss >2% combined.
    else:
        lo = max(0, target_idx - 10)
        hi = min(len(daily_state), target_idx + 5)
        for i in range(lo, hi):
            r = daily_state[i]
            mark = "  <-- TARGET" if r["date"] == target else ""
            print(
                f"  {r['date']:<12} ${r['eq_start']:>11,.0f} ${r['peak_start']:>11,.0f} "
                f"{100.0 * r['dd_from_peak_start']:>6.3f}%  "
                f"{'YES' if r['triggered'] else ' no':>4}  "
                f"{r['multiplier']:.2f}x  "
                f"{r['per_strat_pct']['guardian']:>+6.3f}%  "
                f"{r['per_strat_pct']['striker']:>+6.3f}%  "
                f"{r['per_strat_pct']['aegis']:>+6.3f}%  "
                f"${r['eq_end']:>11,.0f}{mark}"
            )

    # Branch determination for the target date.
    print()
    if target_idx is not None:
        r = daily_state[target_idx]
        print(f"2025-02-07 verdict:")
        print(f"  DD-from-peak at morning check : {100.0 * r['dd_from_peak_start']:.3f}%  "
              f"(trigger threshold: {100.0 * DD_TRIGGER:.1f}%)")
        print(f"  Trigger fired                  : {'YES (multiplier 0.40x)' if r['triggered'] else 'no (full risk)'}")
        striker_pct = r["per_strat_pct"]["striker"]
        # Reconstruct what the Striker trade pct would have been at full risk (un-scale).
        if r["multiplier"] > 0:
            striker_at_full = striker_pct / r["multiplier"]
        else:
            striker_at_full = striker_pct
        print(f"  Striker realized that day      : {striker_pct:+.3f}%  "
              f"(at {r['multiplier']:.2f}x; un-scaled = {striker_at_full:+.3f}%)")
        print()
        if r["triggered"]:
            print(f"  Branch (a): trigger fired beforehand. Live max on 2025-02-07 would have")
            print(f"  been the un-scaled Striker pct ({striker_at_full:+.3f}%) cut to "
                  f"{striker_pct:+.3f}% — actually realized loss is {abs(striker_pct):.3f}%, ")
            print(f"  not {abs(striker_at_full):.3f}%. dd_protection absorbed "
                  f"{abs(striker_at_full) - abs(striker_pct):.3f} percentage points of the outlier.")
        elif abs(striker_pct) > 2.0:
            print(f"  Branch (b): trigger never engaged at the morning of 2025-02-07. The")
            print(f"  full-strength {abs(striker_pct):.3f}% Striker loss passes through untouched.")
            print(f"  Daily DD floor consumed: {abs(striker_pct):.3f}% of {5.00:.2f}% available "
                  f"= {100 * abs(striker_pct) / 5.0:.1f}% of the budget.")
        else:
            print(f"  Branch (c): trigger engaged earlier but post-cut residual was still")
            print(f"  material (Striker still lost {abs(striker_pct):.3f}%).")

    # All days where any strategy lost > 2% in a single day, with the trigger state.
    print()
    print("All days with a single-strategy loss > 2.00% (trigger-state context):")
    print(f"  {'date':<12} {'dd%_start':>10}  trig  mult  "
          f"{'G%':>7}  {'S%':>7}  {'A%':>7}")
    for r in daily_state:
        biggest_strat_loss = -min(r["per_strat_pct"].values())  # positive number
        if biggest_strat_loss > 2.0:
            print(
                f"  {r['date']:<12} {100.0 * r['dd_from_peak_start']:>9.3f}%  "
                f"{'YES' if r['triggered'] else ' no':>4}  "
                f"{r['multiplier']:.2f}x  "
                f"{r['per_strat_pct']['guardian']:>+6.3f}%  "
                f"{r['per_strat_pct']['striker']:>+6.3f}%  "
                f"{r['per_strat_pct']['aegis']:>+6.3f}%"
            )


if __name__ == "__main__":
    main()
