#!/usr/bin/env python3
"""
Q-GUARDIAN-TRAIL-1 — Offline simulation of Option-A static partial-lock on
Guardian v5.5 backtest. Produces 4 distributions (MFE / giveback /
MFE-vs-PnL / bar-to-MFE) and a 21-point parameter grid (7 N_atr_trigger
values x 3 lock_pct values).

Inputs (read directly; no Pine source modifications):
  - Guardian v5.5 CSV: data/tv_exports/pepperstone/...2026-05-14_3b689.csv
  - XAUUSD 15m bars:    data/bar_data/XAUUSD.csv
  - ATR period:         14 (from Pine, verified via 2026-05-08 audit doc)

Convention pins:
  - DXTrade XAUUSD contractValue=100 -> "Size (qty)" * price_delta = USD P&L
  - ATR_at_entry = ATR(14) at bar immediately PRIOR to entry timestamp
    (Pine v6 strategy fill-at-next-open semantic)
  - Same-bar collision (long): bar reaches both trigger AND original_SL ->
    assume SL hits FIRST (conservative; standard backtest convention)
  - Static initial $200K (NOT compounded equity)
  - Realized P&L taken from CSV Exit rows only

Outputs:
  - Distributions printed to stdout in fixed-width text tables
  - 21-point grid as a flat sorted table
  - 5-trade sample trace if any grid point passes the §4 gate
  - Sidebar: any anomaly observed during walk
"""

import csv
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

# TV CSV chart-TZ for XAUUSD on Pepperstone is America/New_York (EST/EDT
# with DST). Verified via trade #183 entry @ $4992.53 on 2026-02-19 09:45:
#   UTC 09:45 bar:  low 4995.40, high 5005.46  -> entry OUTSIDE bar
#   UTC 14:45 bar:  low 4987.63, high 5010.44  -> entry INSIDE bar (= EST 09:45)
NY_TZ = ZoneInfo("America/New_York")

REPO_ROOT = Path("C:/Users/joshu/multi_firm_operations")
CSV_PATH = REPO_ROOT / "data/tv_exports/pepperstone/Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-14_3b689.csv"
BAR_PATH = REPO_ROOT / "data/bar_data/XAUUSD.csv"
ATR_PERIOD = 14
ACCOUNT = 200_000.0

N_GRID = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
LOCK_GRID = [0.30, 0.50, 0.70]

# --- Load XAUUSD 15m bars -----------------------------------------------

def parse_bar_ts(s: str) -> datetime:
    # Format: 2022-01-02T23:00:00.000000000Z -> UTC
    s2 = s.replace("Z", "").split(".")[0]
    return datetime.strptime(s2, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)

def parse_csv_ts(s: str) -> datetime:
    # Format: 2022-05-23 14:30 (TV CSV, NY local time with DST)
    # Convert to UTC for bar lookup.
    naive = datetime.strptime(s.strip(), "%Y-%m-%d %H:%M")
    return naive.replace(tzinfo=NY_TZ).astimezone(timezone.utc)

def load_bars():
    bars = []
    with open(BAR_PATH, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bars.append({
                "ts":    parse_bar_ts(row["time"]),
                "open":  float(row["open"]),
                "high":  float(row["high"]),
                "low":   float(row["low"]),
                "close": float(row["close"]),
            })
    bars.sort(key=lambda r: r["ts"])
    return bars

# Compute ATR(14) using RMA convention (TradingView ta.atr):
#   TR_i = max(h-l, |h-prev_close|, |l-prev_close|)
#   ATR_1..13 undefined; ATR_14 = SMA(TR, 14); ATR_i (i>14) = (ATR_{i-1}*13 + TR_i)/14
def compute_atr(bars, period=14):
    n = len(bars)
    atr = [None] * n
    if n < period + 1:
        return atr
    trs = [None] * n
    for i in range(1, n):
        h, l = bars[i]["high"], bars[i]["low"]
        pc = bars[i-1]["close"]
        trs[i] = max(h - l, abs(h - pc), abs(l - pc))
    # Seed ATR at index = period (so indices 1..period are TRs; SMA of those = seed)
    seed = sum(trs[1:period+1]) / period
    atr[period] = seed
    for i in range(period+1, n):
        atr[i] = (atr[i-1] * (period - 1) + trs[i]) / period
    return atr

# --- Load Guardian CSV trades -------------------------------------------

def load_trades():
    """Return list of dicts: trade_num, entry_ts, exit_ts, entry_price,
       exit_price, qty, signal_exit, realized_pnl, fav_excursion."""
    rows = []
    with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        cols = {c.strip().replace("﻿", ""): c for c in reader.fieldnames}
        # Normalize fieldnames
        for row in reader:
            rows.append({k: row[v].strip() for k, v in cols.items()})
    # Pair by Trade # — each Trade # has 1 Exit + 1 Entry row
    by_tnum = defaultdict(dict)
    for r in rows:
        tnum = int(r["Trade #"])
        ttype = r["Type"]
        rec = {
            "ts":     parse_csv_ts(r["Date and time"]),
            "price":  float(r["Price USD"]),
            "qty":    float(r["Size (qty)"]),
            "signal": r["Signal"],
            "pnl":    float(r["Net P&L USD"]),
            "fav":    float(r["Favorable excursion USD"]),
            "adv":    float(r["Adverse excursion USD"]),
        }
        if ttype.startswith("Entry"):
            by_tnum[tnum]["entry"] = rec
        elif ttype.startswith("Exit"):
            by_tnum[tnum]["exit"] = rec
    trades = []
    for tnum in sorted(by_tnum):
        e = by_tnum[tnum].get("entry"); x = by_tnum[tnum].get("exit")
        if e is None or x is None:
            continue  # unclosed trade — skip
        trades.append({
            "tnum":          tnum,
            "entry_ts":      e["ts"],
            "exit_ts":       x["ts"],
            "entry_price":   e["price"],
            "exit_price":    x["price"],
            "qty":           e["qty"],
            "exit_signal":   x["signal"],
            "realized_pnl":  x["pnl"],
            "csv_fav":       x["fav"],
            "csv_adv":       x["adv"],
        })
    return trades

# --- Bar walk: compute MFE/MAE/trigger detection ------------------------

def index_bars(bars):
    """ts -> index map for fast lookup."""
    return {b["ts"]: i for i, b in enumerate(bars)}

def find_entry_bar_idx(bars, ts_idx, entry_ts):
    """Find the bar whose timestamp == entry_ts (or first bar >= entry_ts)."""
    if entry_ts in ts_idx:
        return ts_idx[entry_ts]
    # Binary search for first bar >= entry_ts
    lo, hi = 0, len(bars) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if bars[mid]["ts"] < entry_ts:
            lo = mid + 1
        else:
            hi = mid
    return lo

def walk_trade(bars, atr, trade, entry_idx):
    """Walk bars from entry_bar+1 onward until exit_ts. Compute MFE/MAE
       (in ATR units, long-side) and store the trigger-eligible bar for
       each N_grid value.
       Returns dict with mfe_atr, mfe_bar_idx (offset from entry), mae_atr,
       and ATR_at_entry, plus full bar list for grid simulation.
    """
    entry_price = trade["entry_price"]
    exit_ts = trade["exit_ts"]
    # ATR_at_entry: use bar PRIOR to entry bar (Pine fill-at-next-open).
    # If entry bar index == 0 (impossible for our panel), fall back to entry bar.
    atr_ref_idx = entry_idx - 1 if entry_idx > 0 else entry_idx
    atr_at_entry = atr[atr_ref_idx]
    if atr_at_entry is None or atr_at_entry <= 0:
        return None

    # Walk forward through bars until ts > exit_ts. INCLUDE bars up to and
    # including the bar containing exit_ts (CSV exit price taken as canonical
    # truth, not bar OHLC at that timestamp).
    walked = []
    mfe_price = entry_price  # for long, MFE is max high
    mfe_bar_off = 0
    mae_price = entry_price
    i = entry_idx
    while i < len(bars):
        b = bars[i]
        if b["ts"] > exit_ts:
            break
        if i > entry_idx:  # exclude entry bar itself; trigger detection on subsequent bars
            walked.append((i - entry_idx, b))
        if b["high"] > mfe_price:
            mfe_price = b["high"]
            mfe_bar_off = i - entry_idx
        if b["low"] < mae_price:
            mae_price = b["low"]
        i += 1

    mfe_atr = (mfe_price - entry_price) / atr_at_entry
    mae_atr = (mae_price - entry_price) / atr_at_entry  # negative for long

    # Final realized exit in ATR units (signed by direction; long-only so positive=profit)
    final_exit_atr = (trade["exit_price"] - entry_price) / atr_at_entry

    return {
        "atr_at_entry": atr_at_entry,
        "mfe_atr": mfe_atr,
        "mfe_bar_off": mfe_bar_off,
        "mae_atr": mae_atr,
        "final_exit_atr": final_exit_atr,
        "walked": walked,
    }

# --- 21-point grid simulation -------------------------------------------

def simulate_partial_lock(trade, walk, N_trigger, lock_pct, original_sl_atr_mult=1.55):
    """Apply Option-A static partial-lock.
       Returns (simulated_pnl, triggered, partial_locked_out).

       Same-bar collision: if a bar's (low <= original_SL_price) AND
       (high >= trigger_price), assume SL fires first.
       After trigger: new SL is static at entry + lock_pct * N_trigger * ATR.
       Continue walking until: (a) new SL hit (long: low <= new_sl), or
       (b) reach the bar containing exit_ts -> use CSV realized_pnl.
    """
    entry_price = trade["entry_price"]
    atr = walk["atr_at_entry"]
    qty = trade["qty"]
    trigger_price = entry_price + N_trigger * atr
    new_sl_price  = entry_price + lock_pct * N_trigger * atr
    # For Guardian long-only, original SL is entry - 1.55*ATR (NOT the actual
    # exit price; CSV exit may be TP, grace, maxHold, or signal-based).
    original_sl_price = entry_price - original_sl_atr_mult * atr

    triggered = False
    locked_out = False
    sim_pnl = trade["realized_pnl"]  # default = unchanged

    for off, b in walk["walked"]:
        # Same-bar collision: SL before trigger
        if b["low"] <= original_sl_price:
            # Original SL would have hit on this bar — but per CSV, original
            # outcome already accounts for actual exit logic. We use this
            # check only to decide whether trigger fires BEFORE SL on the
            # same bar (conservative: it doesn't).
            # If the bar also touches trigger, trigger does NOT fire.
            if b["high"] >= trigger_price:
                # Both reached — SL first. Trigger never fires.
                # But trade exited via CSV path anyway. Just continue walk.
                # In practice, CSV exit is the ground truth.
                pass
            # Continue walking (CSV's actual exit logic is canonical truth)
            continue

        if not triggered and b["high"] >= trigger_price:
            triggered = True
            # Now walk forward looking for new SL hit
            # Replay from the NEXT bar after trigger
            for off2, b2 in walk["walked"]:
                if off2 <= off:
                    continue
                if b2["low"] <= new_sl_price:
                    # New SL hit
                    sim_pnl = (new_sl_price - entry_price) * qty
                    locked_out = True
                    break
            # If we exit the inner loop without locking out, sim_pnl stays
            # at realized_pnl (original CSV exit)
            break

    return sim_pnl, triggered, locked_out

# --- Distribution helpers -----------------------------------------------

def bucket(value, edges):
    for i, e in enumerate(edges):
        if value < e:
            return i
    return len(edges)

def fmt_dist(values, edges, labels):
    n = len(values)
    counts = [0] * (len(edges) + 1)
    for v in values:
        counts[bucket(v, edges)] += 1
    out = []
    for lbl, c in zip(labels, counts):
        pct = (c / n * 100) if n else 0
        bar = "#" * int(round(pct / 2))
        out.append(f"  {lbl:>12} | n={c:>3} ({pct:5.1f}%) {bar}")
    return "\n".join(out)

# --- DD computation -----------------------------------------------------

def max_dd_pct(pnls, account=ACCOUNT):
    eq = account; peak = eq; max_dd = 0.0; max_dd_pct = 0.0
    for x in pnls:
        eq += x
        if eq > peak:
            peak = eq
        d = peak - eq
        if d > max_dd:
            max_dd = d
            max_dd_pct = d / peak * 100
    return max_dd, max_dd_pct

# --- Main pipeline ------------------------------------------------------

def main():
    print("Loading bars...", file=sys.stderr)
    bars = load_bars()
    print(f"  bars: {len(bars):,}  range: {bars[0]['ts']}  to  {bars[-1]['ts']}", file=sys.stderr)

    print("Computing ATR(14)...", file=sys.stderr)
    atr = compute_atr(bars, ATR_PERIOD)

    ts_idx = index_bars(bars)
    print("Loading Guardian v5.5 trades...", file=sys.stderr)
    trades = load_trades()
    print(f"  trades: {len(trades)}", file=sys.stderr)

    # ---- Walk each trade, collect walk results ----
    walks = []
    skipped = []
    for t in trades:
        eidx = find_entry_bar_idx(bars, ts_idx, t["entry_ts"])
        # Sanity: bar timestamp at eidx should equal entry_ts
        if bars[eidx]["ts"] != t["entry_ts"]:
            skipped.append((t["tnum"], "entry_ts not in bars", t["entry_ts"]))
            continue
        w = walk_trade(bars, atr, t, eidx)
        if w is None:
            skipped.append((t["tnum"], "no ATR at entry", t["entry_ts"]))
            continue
        walks.append((t, w))

    print(f"  walks: {len(walks)} / {len(trades)}  skipped: {len(skipped)}", file=sys.stderr)
    for s in skipped[:5]:
        print(f"    SKIP trade={s[0]} reason={s[1]} ts={s[2]}", file=sys.stderr)

    # ===========================================================
    # STEP 2.2 — Phenomenon characterization
    # ===========================================================
    print("\n" + "=" * 70)
    print("STEP 2.2 — Phenomenon characterization (n={})".format(len(walks)))
    print("=" * 70)

    mfe_atr_vals = [w["mfe_atr"] for _, w in walks]
    mae_atr_vals = [w["mae_atr"] for _, w in walks]
    final_atr_vals = [w["final_exit_atr"] for _, w in walks]
    giveback_vals = [w["mfe_atr"] - max(0.0, w["final_exit_atr"]) for _, w in walks]
    bar_to_mfe_vals = [w["mfe_bar_off"] for _, w in walks]

    win_giveback = [(w["mfe_atr"] - max(0.0, w["final_exit_atr"]))
                    for t, w in walks if t["realized_pnl"] > 0]
    loss_giveback = [(w["mfe_atr"] - max(0.0, w["final_exit_atr"]))
                     for t, w in walks if t["realized_pnl"] <= 0]

    print("\n[1] MFE distribution (ATR units, long-side):")
    edges = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
    labels = ["<0", "0-0.5", "0.5-1.0", "1.0-1.5", "1.5-2.0", "2.0-2.5",
              "2.5-3.0", "3.0-4.0", "4.0-5.0", ">=5.0"]
    print(fmt_dist(mfe_atr_vals, edges, labels))
    mfe_sorted = sorted(mfe_atr_vals)
    median_mfe = mfe_sorted[len(mfe_sorted)//2]
    mean_mfe = sum(mfe_atr_vals)/len(mfe_atr_vals)
    print(f"  median MFE: {median_mfe:.3f} ATR")
    print(f"  mean   MFE: {mean_mfe:.3f} ATR")
    print(f"  max    MFE: {max(mfe_atr_vals):.3f} ATR")

    print("\n[2] Giveback distribution (MFE - max(0, final_exit_atr)):")
    edges2 = [0, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
    labels2 = ["<0", "0-0.25", "0.25-0.5", "0.5-1.0", "1.0-1.5",
               "1.5-2.0", "2.0-3.0", "3.0-5.0", ">=5.0"]
    print("  ALL:")
    print(fmt_dist(giveback_vals, edges2, labels2))
    print("  WINS only (n={}):".format(len(win_giveback)))
    print(fmt_dist(win_giveback, edges2, labels2))
    print("  LOSSES only (n={}):".format(len(loss_giveback)))
    print(fmt_dist(loss_giveback, edges2, labels2))
    if win_giveback:
        mean_win_gb = sum(win_giveback) / len(win_giveback)
        print(f"  mean giveback (winners only): {mean_win_gb:.3f} ATR")

    print("\n[3] MFE vs realized P&L (correlation):")
    # Pearson r
    xs = mfe_atr_vals
    ys = [t["realized_pnl"] for t, _ in walks]
    n = len(xs)
    mx = sum(xs)/n; my = sum(ys)/n
    sxx = sum((x-mx)**2 for x in xs)
    syy = sum((y-my)**2 for y in ys)
    sxy = sum((x-mx)*(y-my) for x,y in zip(xs, ys))
    r = sxy / math.sqrt(sxx*syy) if sxx*syy > 0 else 0
    print(f"  Pearson r (MFE_ATR vs realized_pnl): {r:.3f}")
    # Bucket-mean: per-MFE-bin avg realized P&L
    bin_pnl = defaultdict(list)
    for x, y in zip(xs, ys):
        bin_idx = bucket(x, edges)
        bin_pnl[bin_idx].append(y)
    print("  per-MFE-bin mean realized P&L (USD):")
    for i, lbl in enumerate(labels):
        if i in bin_pnl:
            v = bin_pnl[i]
            print(f"    {lbl:>10}: n={len(v):>3}  mean=${sum(v)/len(v):>10,.0f}")

    print("\n[4] Bar-to-MFE distribution:")
    edges4 = [1, 5, 10, 20, 50, 100, 250, 500]
    labels4 = ["0", "1-5", "5-10", "10-20", "20-50", "50-100",
               "100-250", "250-500", ">=500"]
    print(fmt_dist(bar_to_mfe_vals, edges4, labels4))
    bm_sorted = sorted(bar_to_mfe_vals)
    print(f"  median bar-to-MFE: {bm_sorted[len(bm_sorted)//2]} bars")

    # Reading paragraph
    pct_below_1atr_mfe = sum(1 for x in mfe_atr_vals if x < 1.0) / len(mfe_atr_vals) * 100
    pct_below_05atr_mfe = sum(1 for x in mfe_atr_vals if x < 0.5) / len(mfe_atr_vals) * 100
    print(f"\n[Reading] median MFE = {median_mfe:.2f} ATR; "
          f"{pct_below_1atr_mfe:.1f}% of trades MFE < 1 ATR; "
          f"{pct_below_05atr_mfe:.1f}% MFE < 0.5 ATR")
    if win_giveback:
        print(f"          mean giveback among winners = {mean_win_gb:.3f} ATR")
    print(f"          MFE-vs-PnL Pearson r = {r:.3f}")

    # ===========================================================
    # STEP 2.3 — 21-point grid simulation
    # ===========================================================
    print("\n" + "=" * 70)
    print("STEP 2.3 — 21-point grid simulation")
    print("=" * 70)

    baseline_pnls = [t["realized_pnl"] for t, _ in walks]
    baseline_net = sum(baseline_pnls)
    baseline_wins = sum(1 for p in baseline_pnls if p > 0)
    baseline_n = len(baseline_pnls)
    baseline_wr = baseline_wins / baseline_n * 100
    baseline_gw = sum(p for p in baseline_pnls if p > 0)
    baseline_gl = sum(p for p in baseline_pnls if p <= 0)
    baseline_pf = baseline_gw / abs(baseline_gl) if baseline_gl else float('inf')
    _, baseline_dd_pct = max_dd_pct(baseline_pnls)
    baseline_rf = baseline_net / (max_dd_pct(baseline_pnls)[0] or 1)

    print(f"\nBaseline (recomputed from CSV exits):")
    print(f"  N={baseline_n}  Net=${baseline_net:,.0f}  PF={baseline_pf:.3f}  "
          f"WR={baseline_wr:.2f}%  MaxDD%={baseline_dd_pct:.2f}%  RF={baseline_rf:.2f}")

    grid_rows = []
    for N_trig in N_GRID:
        for lp in LOCK_GRID:
            sim_pnls = []
            n_triggered = 0; n_locked = 0; n_unchanged = 0
            for t, w in walks:
                spnl, trig, lock = simulate_partial_lock(t, w, N_trig, lp)
                sim_pnls.append(spnl)
                if trig:
                    n_triggered += 1
                    if lock:
                        n_locked += 1
                    else:
                        n_unchanged += 1
            sim_net = sum(sim_pnls)
            sim_wins = sum(1 for p in sim_pnls if p > 0)
            sim_wr = sim_wins / baseline_n * 100
            sim_gw = sum(p for p in sim_pnls if p > 0)
            sim_gl = sum(p for p in sim_pnls if p <= 0)
            sim_pf = sim_gw / abs(sim_gl) if sim_gl else float('inf')
            _, sim_dd = max_dd_pct(sim_pnls)
            sim_rf = sim_net / (max_dd_pct(sim_pnls)[0] or 1)
            grid_rows.append({
                "N": N_trig, "lock_pct": lp,
                "n_triggered": n_triggered,
                "n_locked": n_locked,
                "n_unchanged": n_unchanged,
                "trig_share": n_triggered / baseline_n,
                "sim_net": sim_net,
                "delta_net": sim_net - baseline_net,
                "delta_net_pct": (sim_net - baseline_net) / baseline_net * 100,
                "sim_pf": sim_pf,
                "delta_pf": sim_pf - baseline_pf,
                "sim_wr": sim_wr,
                "delta_wr_pp": sim_wr - baseline_wr,
                "sim_dd_pct": sim_dd,
                "delta_dd_pp": sim_dd - baseline_dd_pct,
                "sim_rf": sim_rf,
                "delta_rf": sim_rf - baseline_rf,
            })

    # Sort by delta_net_pct desc
    grid_rows.sort(key=lambda r: -r["delta_net_pct"])

    print("\nGrid (sorted by delta_net_pct desc):")
    hdr = (f"| {'N':>3}  | {'lock':>4} | {'n_trig':>6} | {'%trig':>5} | "
           f"{'n_lock':>6} | {'dNet$':>10} | {'dNet%':>7} | "
           f"{'dPF':>6} | {'dWR_pp':>6} | {'dDD_pp':>6} | {'dRF':>6} |")
    sep = "|" + "-"*(len(hdr)-2) + "|"
    print(hdr)
    print(sep)
    for r in grid_rows:
        print(f"| {r['N']:>4.1f} | {int(r['lock_pct']*100):>3}%  | "
              f"{r['n_triggered']:>6} | {r['trig_share']*100:>4.1f}% | "
              f"{r['n_locked']:>6} | {r['delta_net']:>+10,.0f} | "
              f"{r['delta_net_pct']:>+6.2f}% | {r['delta_pf']:>+6.3f} | "
              f"{r['delta_wr_pp']:>+6.2f} | {r['delta_dd_pp']:>+6.2f} | "
              f"{r['delta_rf']:>+6.2f} |")

    # ---- Apply §4 gate ----
    print("\n[§4 Gate evaluation]")
    print("  (a) delta_net_pct >= +5.00")
    print("  (b) delta_pf      >= -0.10")
    print("  (c) delta_dd_pp   <= +0.50")
    print("  (d) trig_share    >= 0.20")
    resolved = []
    ambiguous = []
    for r in grid_rows:
        a = r["delta_net_pct"] >= 5.0
        b = r["delta_pf"] >= -0.10
        c = r["delta_dd_pp"] <= 0.50
        d = r["trig_share"] >= 0.20
        passes = [a, b, c, d]
        if all(passes):
            resolved.append(r)
        elif a and d and not (b and c):
            ambiguous.append((r, ["b" if not b else None, "c" if not c else None]))

    if resolved:
        print(f"\n  RESOLVED: {len(resolved)} grid point(s) pass all 4 gates")
        best = resolved[0]  # already sorted by delta_net_pct desc
        print(f"  BEST: N={best['N']} lock_pct={int(best['lock_pct']*100)}% "
              f"-> dNet={best['delta_net_pct']:+.2f}% "
              f"(${best['delta_net']:+,.0f}), "
              f"dPF={best['delta_pf']:+.3f}, dDD={best['delta_dd_pp']:+.2f}pp, "
              f"trig={best['trig_share']*100:.1f}%")
    elif ambiguous:
        print(f"\n  AMBIGUOUS: {len(ambiguous)} grid point(s) pass (a)+(d) but fail (b) or (c)")
    else:
        print("\n  FALSIFIED: no grid point passes all 4 gates")
        # near-miss: highest delta_net_pct
        nm = grid_rows[0]
        print(f"  Closest near-miss: N={nm['N']} lock_pct={int(nm['lock_pct']*100)}% "
              f"-> dNet={nm['delta_net_pct']:+.2f}% (a={'P' if nm['delta_net_pct']>=5 else 'F'}, "
              f"b={'P' if nm['delta_pf']>=-0.10 else 'F'}, "
              f"c={'P' if nm['delta_dd_pp']<=0.50 else 'F'}, "
              f"d={'P' if nm['trig_share']>=0.20 else 'F'})")

    # ---- 5-trade sample trace (if RESOLVED) ----
    if resolved:
        best = resolved[0]
        N_trig = best["N"]; lp = best["lock_pct"]
        deltas = []
        for t, w in walks:
            spnl, trig, lock = simulate_partial_lock(t, w, N_trig, lp)
            if trig:
                deltas.append((abs(spnl - t["realized_pnl"]), t, w, spnl, trig, lock))
        deltas.sort(key=lambda x: -x[0])
        print(f"\n[5-trade sample trace at N={N_trig} lock_pct={int(lp*100)}%]")
        print(f"{'Trade':>5} | {'Entry':<16} {'Entry$':>8} | {'MFE_bar':>7} {'MFE$':>8} | "
              f"{'Trig_bar':>8} {'Trig$':>8} | {'Orig_exit':>9} {'Orig$':>8} | "
              f"{'Sim_exit':>9} {'Sim$':>8} | {'d$':>9}")
        for i, (d, t, w, spnl, trig, lock) in enumerate(deltas[:5], 1):
            eidx = find_entry_bar_idx(bars, ts_idx, t["entry_ts"])
            mfe_off = w["mfe_bar_off"]
            mfe_bar = bars[eidx + mfe_off] if eidx + mfe_off < len(bars) else None
            mfe_price = mfe_bar["high"] if mfe_bar else float('nan')
            trig_price = t["entry_price"] + N_trig * w["atr_at_entry"]
            new_sl_price = t["entry_price"] + lp * N_trig * w["atr_at_entry"]
            # Find trigger bar offset
            trig_bar_off = None
            for off, b in w["walked"]:
                if b["high"] >= trig_price:
                    trig_bar_off = off
                    break
            sim_exit_kind = "new_SL" if lock else "orig"
            sim_exit_price = new_sl_price if lock else t["exit_price"]
            print(f"Trade {t['tnum']:>3}: {str(t['entry_ts'])[:16]:<16} ${t['entry_price']:>7.2f} | "
                  f"#{mfe_bar_off:>3}     ${mfe_price:>7.2f} | "
                  f"#{(trig_bar_off if trig_bar_off is not None else -1):>3}     ${trig_price:>7.2f} | "
                  f"{t['exit_signal']:>9} ${t['exit_price']:>7.2f} | "
                  f"{sim_exit_kind:>9} ${sim_exit_price:>7.2f} | "
                  f"${(spnl - t['realized_pnl']):>+8,.0f}")

    # ---- Sidebar: any anomalies ----
    print("\n[Sidebar / observations — not recommendations]")
    high_mfe = [m for m in mfe_atr_vals if m >= 5.0]
    print(f"  - Trades with MFE >= 5 ATR: n={len(high_mfe)} "
          f"(if numerous, suggests Guardian leaves significant edge in tail; "
          f"a multi-stage or time-decay trigger could in principle target these — NOT a recommendation, surface only)")
    low_mfe = sum(1 for m in mfe_atr_vals if m < 0.5)
    print(f"  - Trades with MFE < 0.5 ATR: n={low_mfe} ({low_mfe/len(walks)*100:.1f}%) — partial-lock irrelevant for these")
    if skipped:
        print(f"  - Skipped trades: {len(skipped)} (entry_ts not in bars or no ATR)")

if __name__ == "__main__":
    main()
