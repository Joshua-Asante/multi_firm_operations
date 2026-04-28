"""
Validation harness for Guardian v5.5 candidate on Pepperstone basis.
Re-uses portfolio_mc internals; does NOT modify any locked artifact.
Targets per Notion brief 34adc0b53c118181b12eff8a18f131c6 (incl. UPDATE 2026-04-21).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(r"C:\Users\joshu\prop_firm_pipeline")
sys.path.insert(0, str(REPO))

from portfolio_mc import (  # noqa: E402
    ALLOCATIONS,
    SEEDS,
    SIMS_PER_SEED,
    HORIZON_DAYS,
    STARTING_EQUITY,
    STRATS,
    build_daily_panel,
    build_week_blocks,
    implied_1r,
    load_trades,
    run_seed,
)
from dd_protection import DD_TRIGGER, DD_SCALE  # noqa: E402

PEP_DIR = REPO / "data" / "tv_exports" / "pepperstone"

EXPECTED = {
    "guardian": {  # v5.5 -- updated per UPDATE 2026-04-21
        "trades": 190, "net": 352_870.85, "pf": 3.5327,
        "win_rate": 0.2211,  # 42/190
        "file": "guardian.csv",
    },
    "guardian_v54": {
        "trades": 215, "net": 347_730.08, "pf": 3.1609,
        "win_rate": 0.2000,  # 43/215
        "file": "guardian_v5.4.csv",
    },
}


def per_trade_records(path: Path) -> pd.DataFrame:
    """Return per-trade records (one row per trade) with exit_date, pnl, hour, dow, year."""
    df = pd.read_csv(path, encoding="utf-8-sig")
    exits = df[df["Type"].astype(str).str.startswith("Exit")].copy()
    exits["dt"] = pd.to_datetime(exits["Date and time"])
    exits["pnl"] = pd.to_numeric(exits["Net P&L USD"], errors="coerce")
    exits["hour"] = exits["dt"].dt.hour
    exits["dow"] = exits["dt"].dt.day_name()
    exits["year"] = exits["dt"].dt.year
    return exits[["dt", "pnl", "hour", "dow", "year"]].dropna().sort_values("dt").reset_index(drop=True)


def headline(df: pd.DataFrame) -> dict:
    pnl = df["pnl"]
    cum = pnl.cumsum()
    running_max = cum.cummax()
    dd_dollar = (cum - running_max).min()  # most negative = worst DD in dollars
    # max DD% relative to peak equity ($200K starting) -- match Pine convention
    starting_eq = STARTING_EQUITY
    eq_curve = starting_eq + cum
    peak_curve = eq_curve.cummax()
    dd_pct = ((eq_curve - peak_curve) / peak_curve).min()
    rf = (pnl.sum() / abs(dd_dollar)) if dd_dollar < 0 else float("inf")

    # max consecutive loss streak
    sign = (pnl < 0).astype(int).values
    max_streak = 0
    cur = 0
    for s in sign:
        if s:
            cur += 1
            if cur > max_streak:
                max_streak = cur
        else:
            cur = 0

    return {
        "trades": int(len(pnl)),
        "net": float(pnl.sum()),
        "gross_win": float(pnl[pnl > 0].sum()),
        "gross_loss": float(-pnl[pnl < 0].sum()),
        "pf": float(pnl[pnl > 0].sum() / -pnl[pnl < 0].sum()) if (pnl < 0).any() else float("inf"),
        "wins": int((pnl > 0).sum()),
        "losses": int((pnl < 0).sum()),
        "win_rate": float((pnl > 0).mean()),
        "avg_win": float(pnl[pnl > 0].mean()) if (pnl > 0).any() else 0.0,
        "avg_loss": float(pnl[pnl < 0].mean()) if (pnl < 0).any() else 0.0,
        "avg_trade": float(pnl.mean()),
        "dd_dollar": float(dd_dollar),
        "dd_pct": float(dd_pct),
        "rf": float(rf),
        "max_loss_streak": int(max_streak),
        "first": df["dt"].min(),
        "last": df["dt"].max(),
    }


def reconcile(label: str, path: Path, expected: dict | None) -> tuple[dict, pd.DataFrame, bool]:
    df = per_trade_records(path)
    s = headline(df)
    print(f"--- {label}  ({path.name}) ---")
    print(f"  trades  : {s['trades']:>10,}")
    print(f"  net P&L : ${s['net']:>12,.2f}")
    print(f"  PF      : {s['pf']:>10.4f}    win_rate: {s['win_rate']:.2%}")
    print(f"  max DD  : ${s['dd_dollar']:>12,.2f}  ({s['dd_pct']:.2%} of peak eq)")
    print(f"  RF      : {s['rf']:>10.2f}    avg_trade: ${s['avg_trade']:>9,.2f}")
    print(f"  max consec losers: {s['max_loss_streak']}")
    print(f"  span    : {s['first'].date()} -> {s['last'].date()}")

    halted = False
    if expected:
        for key in ("trades", "net", "pf", "win_rate"):
            want = expected[key]
            got = s[key]
            tol = 0.005
            denom = abs(want) if want else 1.0
            err = abs(got - want) / denom
            mark = "OK " if err <= tol else "!! HALT"
            print(f"  reconcile {key:<10}: want {want:>14.4f}  got {got:>14.4f}  err={err:.4%} {mark}")
            if err > tol and key in ("trades", "net", "pf"):
                halted = True
    print()
    return s, df, halted


def year_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("year").agg(
        trades=("pnl", "count"),
        net=("pnl", "sum"),
        wins=("pnl", lambda x: (x > 0).sum()),
    )
    g["win_rate"] = g["wins"] / g["trades"]
    return g.reset_index()


def dd_episode(df: pd.DataFrame) -> dict:
    """Identify the worst drawdown episode: window, trade count, losers, DOW/hour mix."""
    pnl = df["pnl"].values
    cum = np.cumsum(pnl)
    eq = STARTING_EQUITY + cum
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / peak
    trough_idx = int(np.argmin(dd))
    # find peak before trough (last index where eq == peak[trough])
    peak_before = trough_idx
    while peak_before > 0 and eq[peak_before] != peak[trough_idx]:
        peak_before -= 1
    # window from peak_before+1 to trough_idx
    window = df.iloc[peak_before + 1: trough_idx + 1]
    if len(window) == 0:
        window = df.iloc[trough_idx: trough_idx + 1]
    losers = window[window["pnl"] < 0]
    return {
        "start": window["dt"].min(),
        "end": window["dt"].max(),
        "n_trades": int(len(window)),
        "n_losers": int(len(losers)),
        "loser_dow": losers["dow"].value_counts().to_dict(),
        "loser_hour": losers["hour"].value_counts().sort_index().to_dict(),
        "dd_pct": float(dd[trough_idx]),
        "dd_dollar": float(eq[trough_idx] - peak[trough_idx]),
    }


def mc_run(label: str, guardian_csv: Path) -> dict:
    print("=" * 70)
    print(f"Portfolio MC -- {label}  (Pepperstone basis)")
    print("=" * 70)
    trades_by_strat = {
        "guardian": load_trades(guardian_csv),
        "striker": load_trades(PEP_DIR / "striker.csv"),
        "aegis": load_trades(PEP_DIR / "aegis.csv"),
    }
    panel, scale_info = build_daily_panel(trades_by_strat, ALLOCATIONS)
    blocks = build_week_blocks(panel)
    print("Scale factors:")
    for s, info in scale_info.items():
        print(f"  {s:<9} 1R=${info['implied_1r']:>9,.2f}  scale={info['scale']:>6.3f}  n={info['n_trades']}")
    print(f"Panel: {panel.index.min().date()} -> {panel.index.max().date()}  "
          f"({len(panel)} bdays, {len(blocks)} week-blocks)")
    print(f"DD config: trigger={DD_TRIGGER}, scale={DD_SCALE}, sims={SIMS_PER_SEED:,}x{len(SEEDS)}")
    print()

    results = [run_seed(seed, SIMS_PER_SEED, blocks, DD_TRIGGER, DD_SCALE) for seed in SEEDS]
    per = SIMS_PER_SEED
    pass_r = [r["outcomes"]["pass"] / per for r in results]
    bd_r   = [r["outcomes"]["bust_daily"] / per for r in results]
    bs_r   = [r["outcomes"]["bust_static"] / per for r in results]
    to_r   = [r["outcomes"]["timeout"] / per for r in results]
    bust_r = [d + s for d, s in zip(bd_r, bs_r)]
    all_dds = [d for r in results for d in r["max_dds"]]
    attrib = {s: sum(r["bust_attribution"][s] for r in results) for s in STRATS}
    total_busts = sum(attrib.values())

    print(f"Pass:        {np.mean(pass_r):>7.2%}  (sigma {np.std(pass_r):.2%})")
    print(f"Bust:        {np.mean(bust_r):>7.2%}  (sigma {np.std(bust_r):.2%})")
    print(f"  daily:     {np.mean(bd_r):>7.2%}")
    print(f"  static:    {np.mean(bs_r):>7.2%}")
    print(f"Timeout:     {np.mean(to_r):>7.2%}")
    print(f"p50 DD:      {np.percentile(all_dds, 50):.2%}")
    print(f"p95 DD:      {np.percentile(all_dds, 95):.2%}")
    print(f"p99 DD:      {np.percentile(all_dds, 99):.2%}")
    print("Bust attribution:")
    if total_busts > 0:
        for s in ("aegis", "striker", "guardian"):
            print(f"  {s.capitalize():<10} {attrib[s] / total_busts:>6.1%}")
    else:
        print("  (no busts)")
    print()
    return {
        "pass": float(np.mean(pass_r)),
        "pass_sigma": float(np.std(pass_r)),
        "bust": float(np.mean(bust_r)),
        "bust_sigma": float(np.std(bust_r)),
        "bust_daily": float(np.mean(bd_r)),
        "bust_static": float(np.mean(bs_r)),
        "timeout": float(np.mean(to_r)),
        "p50": float(np.percentile(all_dds, 50)),
        "p95": float(np.percentile(all_dds, 95)),
        "p99": float(np.percentile(all_dds, 99)),
        "attrib": {s: (attrib[s] / total_busts if total_busts else 0.0) for s in STRATS},
        "total_busts": int(total_busts),
        "n_paths": per * len(SEEDS),
    }


def main():
    print("=" * 70)
    print("Guardian v5.5 Pepperstone validation -- 2026-04-21 (RESUMED)")
    print("=" * 70)
    print()

    # ── Task A: reconcile ──
    g55, g55_df, h1 = reconcile("Guardian v5.5", PEP_DIR / "guardian.csv", EXPECTED["guardian"])
    g54, g54_df, h2 = reconcile("Guardian v5.4", PEP_DIR / "guardian_v5.4.csv", EXPECTED["guardian_v54"])
    striker, striker_df, _ = reconcile("Striker v4.4", PEP_DIR / "striker.csv", None)
    aegis, aegis_df, _ = reconcile("Aegis v4.2", PEP_DIR / "aegis.csv", None)

    if h1 or h2:
        print("\n!! HALT at Task A reconciliation -- not running MC. Request human review.")
        sys.exit(2)

    # ── Task B: v5.5 vs v5.4 diff ──
    print("=" * 70)
    print("Guardian v5.5 vs v5.4 -- isolated diff")
    print("=" * 70)
    print()
    print(f"{'metric':<22} {'v5.4':>14} {'v5.5':>14} {'delta':>14}")
    for k, fmt in [("trades", "d"), ("net", ".2f"), ("pf", ".4f"), ("win_rate", ".4f"),
                   ("dd_dollar", ".2f"), ("dd_pct", ".4f"), ("rf", ".2f"),
                   ("avg_trade", ".2f"), ("avg_win", ".2f"), ("avg_loss", ".2f"),
                   ("max_loss_streak", "d")]:
        a, b = g54[k], g55[k]
        d = b - a
        if fmt == "d":
            print(f"{k:<22} {a:>14d} {b:>14d} {d:>+14d}")
        else:
            print(f"{k:<22} {a:>14.4f} {b:>14.4f} {d:>+14.4f}")
    print()

    g54_year = year_breakdown(g54_df)
    g55_year = year_breakdown(g55_df)
    print("Year-by-year stability:")
    print(f"{'year':<6} | {'v5.4 trades':>12} {'v5.4 net':>14} {'v5.4 WR':>9} | {'v5.5 trades':>12} {'v5.5 net':>14} {'v5.5 WR':>9}")
    years = sorted(set(g54_year['year']).union(set(g55_year['year'])))
    profitable = {"v5.4": True, "v5.5": True}
    yearly_rows = []
    for y in years:
        r4 = g54_year[g54_year['year'] == y].iloc[0] if (g54_year['year'] == y).any() else None
        r5 = g55_year[g55_year['year'] == y].iloc[0] if (g55_year['year'] == y).any() else None
        t4 = int(r4['trades']) if r4 is not None else 0
        n4 = float(r4['net']) if r4 is not None else 0.0
        w4 = float(r4['win_rate']) if r4 is not None else 0.0
        t5 = int(r5['trades']) if r5 is not None else 0
        n5 = float(r5['net']) if r5 is not None else 0.0
        w5 = float(r5['win_rate']) if r5 is not None else 0.0
        if n4 < 0:
            profitable["v5.4"] = False
        if n5 < 0:
            profitable["v5.5"] = False
        print(f"{y:<6} | {t4:>12} ${n4:>12,.0f} {w4:>9.2%} | {t5:>12} ${n5:>12,.0f} {w5:>9.2%}")
        yearly_rows.append((y, t4, n4, w4, t5, n5, w5))
    print(f"Profitable every year? v5.4={profitable['v5.4']}  v5.5={profitable['v5.5']}")
    print()

    g54_ep = dd_episode(g54_df)
    g55_ep = dd_episode(g55_df)
    print("Worst DD episode:")
    print(f"  v5.4: {g54_ep['start'].date()} -> {g54_ep['end'].date()}  "
          f"trades={g54_ep['n_trades']} losers={g54_ep['n_losers']}  "
          f"dd=${g54_ep['dd_dollar']:,.0f} ({g54_ep['dd_pct']:.2%})")
    print(f"        DOW losers : {g54_ep['loser_dow']}")
    print(f"        Hour losers: {g54_ep['loser_hour']}")
    print(f"  v5.5: {g55_ep['start'].date()} -> {g55_ep['end'].date()}  "
          f"trades={g55_ep['n_trades']} losers={g55_ep['n_losers']}  "
          f"dd=${g55_ep['dd_dollar']:,.0f} ({g55_ep['dd_pct']:.2%})")
    print(f"        DOW losers : {g55_ep['loser_dow']}")
    print(f"        Hour losers: {g55_ep['loser_hour']}")
    print()

    # ── Task C: MC ──
    mc_v54 = mc_run("v5.4 BASELINE", PEP_DIR / "guardian_v5.4.csv")
    mc_v55 = mc_run("v5.5 CANDIDATE", PEP_DIR / "guardian.csv")

    # Alchemy-baseline drift flag (informational)
    alch_pass, alch_bust = 0.9921, 0.0003
    pass_drift = mc_v54["pass"] - alch_pass
    bust_drift = mc_v54["bust"] - alch_bust
    print("Alchemy-baseline drift check (informational, not gating):")
    print(f"  Run1 pass {mc_v54['pass']:.2%} vs Alchemy {alch_pass:.2%}  drift={pass_drift:+.2%}  "
          f"flag={'YES' if abs(pass_drift) > 0.02 else 'no'}")
    print(f"  Run1 bust {mc_v54['bust']:.4%} vs Alchemy {alch_bust:.4%}  drift={bust_drift:+.4%}  "
          f"flag={'YES' if abs(bust_drift) > 0.0025 else 'no'}")
    print()

    # ── Task D: gates per UPDATE-revised definitions ──
    print("=" * 70)
    print("SHIP GATES")
    print("=" * 70)
    gates = []

    # Gate 1: Run2 pass >= Run1 pass - 0.5pp
    g1 = mc_v55["pass"] >= mc_v54["pass"] - 0.005
    print(f"  Gate 1 (MC pass: v5.5 >= v5.4 - 0.5pp):  "
          f"v5.4={mc_v54['pass']:.2%}  v5.5={mc_v55['pass']:.2%}  "
          f"threshold={mc_v54['pass'] - 0.005:.2%}  {'PASS' if g1 else 'FAIL'}")
    gates.append(("Gate 1: MC pass rate", g1))

    # Gate 2: Run2 bust <= Run1 bust + 0.07pp
    g2 = mc_v55["bust"] <= mc_v54["bust"] + 0.0007
    print(f"  Gate 2 (MC bust: v5.5 <= v5.4 + 0.07pp):  "
          f"v5.4={mc_v54['bust']:.4%}  v5.5={mc_v55['bust']:.4%}  "
          f"threshold={mc_v54['bust'] + 0.0007:.4%}  {'PASS' if g2 else 'FAIL'}")
    gates.append(("Gate 2: MC bust rate", g2))

    # Gate 3: Guardian isolated 4yr DD% <= 6.44%
    g3 = abs(g55["dd_pct"]) <= 0.0644
    print(f"  Gate 3 (Guardian iso 4yr DD% <= 6.44%):  "
          f"v5.5 DD%={abs(g55['dd_pct']):.2%}  {'PASS' if g3 else 'FAIL'}")
    gates.append(("Gate 3: Guardian iso DD%", g3))

    # Gate 4: Aegis bust share <= 30%
    aegis_share = mc_v55["attrib"]["aegis"]
    g4 = aegis_share <= 0.30
    print(f"  Gate 4 (Aegis bust share <= 30%):  "
          f"v5.5 share={aegis_share:.1%}  {'PASS' if g4 else 'FAIL'}")
    gates.append(("Gate 4: Aegis bust share", g4))

    # Gate 5: Guardian 4yr net >= $313K
    g5 = g55["net"] >= 313_000.0
    print(f"  Gate 5 (Guardian 4yr net >= $313K):  "
          f"v5.5 net=${g55['net']:,.0f}  {'PASS' if g5 else 'FAIL'}")
    gates.append(("Gate 5: Guardian 4yr net", g5))

    print()
    n_pass = sum(1 for _, ok in gates if ok)
    if n_pass == len(gates):
        verdict = "SHIP"
    elif n_pass >= len(gates) - 1:
        verdict = "NEEDS HUMAN REVIEW"
    else:
        verdict = "BLOCK"
    print(f"OVERALL: {verdict}   ({n_pass}/{len(gates)} gates pass)")

    # Persist machine-readable summary
    summary = {
        "verdict": verdict,
        "guardian_v55": g55, "guardian_v54": g54, "striker": striker, "aegis": aegis,
        "guardian_v55_episode": {**g55_ep, "start": str(g55_ep["start"]), "end": str(g55_ep["end"])},
        "guardian_v54_episode": {**g54_ep, "start": str(g54_ep["start"]), "end": str(g54_ep["end"])},
        "mc_v54": mc_v54, "mc_v55": mc_v55,
        "alchemy_drift": {"pass": pass_drift, "bust": bust_drift,
                          "pass_flagged": abs(pass_drift) > 0.02,
                          "bust_flagged": abs(bust_drift) > 0.0025},
        "gates": [{"name": n, "pass": ok} for n, ok in gates],
        "yearly_rows": yearly_rows,
        "profitable": profitable,
    }
    out_json = REPO / ".claude" / "worktrees" / "vibrant-payne-873bec" / "results_2026-04-21.json"
    # JSON-friendly: convert datetime to str
    for k in ("guardian_v55", "guardian_v54", "striker", "aegis"):
        summary[k]["first"] = str(summary[k]["first"])
        summary[k]["last"] = str(summary[k]["last"])
    out_json.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\nJSON summary -> {out_json}")


if __name__ == "__main__":
    main()
