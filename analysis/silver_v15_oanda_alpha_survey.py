"""Q-CORR-1.2-adjacent forensic + descriptive analysis (2026-05-13).

Scope:
  (A) Decompose Guardian Silver v1.5 (_82815) Pepperstone panel by exit reason
      and time, surfacing where the v1.5 hint's drag concentrates.
  (B) Half-panel split predictor for Q-CORR-1.2 §14 Gate 10, computed on the
      full ex-WFO panel (PREDICTOR, not gate verdict — real Gate 10 reads on
      OOS-stitched daily Net P&L from Path B per-fold aggregation).
  (C) Cross-check the same split on the locked Gold v5.5 XAUUSD anchor
      (_33781) and the Q-CORR-1.2 §14 Gate-12 comparator export (_13fad).
  (D) Characterize OANDA XAGUSD m15 bars descriptively — return distribution,
      vol regime, intra-week / intra-day shape. Context only; no per-bar PnL
      inference; no overlay implication.

Out of scope (forbidden / hazardous mid-Q-CORR-1.2):
  - Bar-level "what trade would v1.5 have taken on OANDA" reconstruction.
    Cross-feed signal divergence on XAGUSD (analogous to XAUUSD ~16-29% haircut)
    would mix feed artifact with strategy artifact.
  - Any candidate-zone shortlist that pre-shapes the 250-config Pepperstone grid.
  - Overlay proposals (no live-PnL gap; v1.5 not deployed).

Inputs are gitignored under vendor-data public-clone posture; this script
skips with a clear message if any input is missing on a fresh clone.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SILVER = REPO / "data/tv_exports/pepperstone/Guardian_Silver_v1.5_PEPPERSTONE_XAGUSD_2026-05-13_82815.csv"
GOLD_DC = REPO / "data/tv_exports/pepperstone/Guardian_Gold_v5.5_PEPPERSTONE_XAGUSD_2026-05-13_dc6a3.csv"
GOLD_33781 = REPO / "data/tv_exports/pepperstone/Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-05_33781.csv"
GOLD_13FAD = REPO / "data/tv_exports/pepperstone/Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-12_13fad.csv"
BARS = REPO / "data/bar_data/XAGUSD.csv"
NOTIONAL = 200_000.0


def load_trades(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    # Standard TV pepperstone export columns; pair entry+exit by Trade #
    df["Date and time"] = pd.to_datetime(df["Date and time"])
    entries = df[df["Type"].str.startswith("Entry")].copy()
    exits = df[df["Type"].str.startswith("Exit")].copy()
    entries = entries.rename(columns={
        "Date and time": "entry_ts", "Price USD": "entry_px",
    })[["Trade #", "entry_ts", "entry_px", "Type"]]
    exits = exits.rename(columns={
        "Date and time": "exit_ts", "Price USD": "exit_px",
        "Net P&L USD": "net_pnl_usd", "Net P&L %": "net_pnl_pct",
        "Favorable excursion USD": "mfe_usd",
        "Adverse excursion USD": "mae_usd",
        "Signal": "exit_signal",
    })[["Trade #", "exit_ts", "exit_px", "net_pnl_usd", "net_pnl_pct",
        "mfe_usd", "mae_usd", "exit_signal"]]
    t = entries.merge(exits, on="Trade #")
    t["bars_held_approx"] = (t["exit_ts"] - t["entry_ts"]).dt.total_seconds() / (15 * 60)
    return t.sort_values("exit_ts").reset_index(drop=True)


def panel_summary(t: pd.DataFrame, label: str) -> None:
    n = len(t)
    wins = (t["net_pnl_usd"] > 0).sum()
    wr = 100.0 * wins / n
    gp = t.loc[t["net_pnl_usd"] > 0, "net_pnl_usd"].sum()
    gl = t.loc[t["net_pnl_usd"] < 0, "net_pnl_usd"].sum()
    pf = gp / abs(gl) if gl < 0 else float("nan")
    net = t["net_pnl_usd"].sum()
    eq = t["net_pnl_usd"].cumsum()
    peak = eq.cummax()
    dd_notional = float(((peak - eq) / NOTIONAL).max() * 100)
    rf = net / (NOTIONAL * dd_notional / 100) if dd_notional > 0 else float("nan")
    # MFE/MAE
    mfe_sum = t["mfe_usd"].sum()
    mae_sum = t["mae_usd"].abs().sum()
    print(f"\n=== {label} ===")
    print(f"  N        : {n}")
    print(f"  WR       : {wr:.2f}%   ({wins}/{n})")
    print(f"  PF       : {pf:.3f}")
    print(f"  Net $    : ${net:,.0f}")
    print(f"  DD%      : {dd_notional:.2f}%  (static $200K notional)")
    print(f"  RF       : {rf:.2f}")
    print(f"  GP / |GL|: ${gp:,.0f} / ${abs(gl):,.0f}")
    print(f"  MFE / MAE: ${mfe_sum:,.0f} / ${mae_sum:,.0f}  ratio={mfe_sum/max(mae_sum,1e-9):.2f}")
    print(f"  Span     : {t['exit_ts'].min().date()} -> {t['exit_ts'].max().date()}")


def exit_reason_breakdown(t: pd.DataFrame, label: str) -> pd.DataFrame:
    rows = []
    total_n = len(t)
    total_pnl = t["net_pnl_usd"].sum()
    for sig, g in t.groupby("exit_signal", dropna=False):
        n = len(g)
        wins = (g["net_pnl_usd"] > 0).sum()
        wr = 100 * wins / n
        gp = g.loc[g["net_pnl_usd"] > 0, "net_pnl_usd"].sum()
        gl = g.loc[g["net_pnl_usd"] < 0, "net_pnl_usd"].sum()
        pf = gp / abs(gl) if gl < 0 else float("inf")
        net = g["net_pnl_usd"].sum()
        # Captured ratio: realized PnL vs MFE for winners (how much of the favorable excursion was kept)
        wins_g = g[g["net_pnl_usd"] > 0]
        capture = (wins_g["net_pnl_usd"].sum() / wins_g["mfe_usd"].sum()) if len(wins_g) and wins_g["mfe_usd"].sum() > 0 else float("nan")
        rows.append({
            "exit_signal": sig,
            "n": n,
            "share_n_%": 100 * n / total_n,
            "WR_%": wr,
            "PF": pf,
            "Net_$": net,
            "share_pnl_%": 100 * net / total_pnl if total_pnl else float("nan"),
            "avg_$": net / n,
            "capture_of_MFE_wins_%": capture * 100 if capture == capture else float("nan"),
            "median_bars_held": g["bars_held_approx"].median(),
        })
    out = pd.DataFrame(rows).sort_values("Net_$", ascending=False)
    print(f"\n--- {label} — Exit-reason breakdown ---")
    print(out.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    return out


def stale_drag_diagnostic(t: pd.DataFrame, label: str) -> None:
    """For exit_signal == 'Stale': how much MFE was left on table relative to net?
    This is an architectural-drag indicator — Stale is the time-based exit, so
    high MFE-vs-net on Stale-cohort suggests the time-stop is biting into runners.
    Not a parameter the Q-CORR-1.2 grid sweeps."""
    stale = t[t["exit_signal"] == "Stale"]
    if stale.empty:
        return
    n = len(stale)
    stale_net = stale["net_pnl_usd"].sum()
    stale_mfe = stale["mfe_usd"].sum()
    stale_mae = stale["mae_usd"].abs().sum()
    winners = stale[stale["net_pnl_usd"] > 0]
    print(f"\n--- {label} — Stale-exit forensic ---")
    print(f"  N(Stale)            : {n}")
    print(f"  Net               $ : ${stale_net:,.0f}")
    print(f"  Sum MFE           $ : ${stale_mfe:,.0f}    (peak unrealized seen)")
    print(f"  MFE / Net (winners) : {(winners['mfe_usd'].sum() / max(winners['net_pnl_usd'].sum(),1e-9)):.2f}x")
    print(f"  Note: high MFE/Net on Stale cohort = time-stop biting runners.")
    print(f"        Architectural-class drag — outside the 4D Q-CORR-1.2 grid.")


def dd_limit_diagnostic(t: pd.DataFrame, label: str) -> None:
    """For exit_signal == 'DD Limit': risk-control exits. Are they
    pre-emptive (followed by recovery) or appropriate (followed by deeper bar
    drawdown)? We can't tell without bar data — flag scope only."""
    dd = t[t["exit_signal"] == "DD Limit"]
    if dd.empty:
        print(f"\n--- {label} — DD Limit cohort: none ---")
        return
    n = len(dd)
    print(f"\n--- {label} — DD Limit forensic ---")
    print(f"  N(DD Limit)         : {n}")
    print(f"  Net               $ : ${dd['net_pnl_usd'].sum():,.0f}")
    print(f"  WR%                 : {100 * (dd['net_pnl_usd']>0).sum() / n:.1f}%")
    print(f"  Note: DD-Limit is dd_protection.py-driven, not strategy-driven.")
    print(f"        Tightly coupled to portfolio-level C2 lock (1.5%/0.40x).")


def time_shape(t: pd.DataFrame, label: str) -> None:
    """How is alpha distributed across time? Year / DoW / hour-of-entry."""
    t = t.copy()
    t["year"] = t["exit_ts"].dt.year
    t["entry_hour"] = pd.to_datetime(t["entry_ts"]).dt.hour
    t["entry_dow"] = pd.to_datetime(t["entry_ts"]).dt.day_name()
    print(f"\n--- {label} — Time-shape ---")
    print("  By year:")
    for y, g in t.groupby("year"):
        n = len(g)
        net = g["net_pnl_usd"].sum()
        wr = 100 * (g["net_pnl_usd"] > 0).sum() / n
        print(f"    {y}: n={n:3d}  WR={wr:5.1f}%  Net=${net:>10,.0f}")
    print("  By entry-hour (UTC, 15m bars rounded):")
    by_h = t.groupby("entry_hour").agg(n=("net_pnl_usd", "size"), net=("net_pnl_usd", "sum"))
    for h, row in by_h.iterrows():
        print(f"    {h:02d}: n={int(row['n']):3d}  Net=${row['net']:>10,.0f}")


def half_panel_split(t: pd.DataFrame, label: str) -> None:
    """Q-CORR-1.2 §14 Gate 10 pre-flight: PF ratio (H1/H2) ∈ [0.7, 1.3] on OOS
    stitched daily Net P&L. We compute on the full ex-WFO panel — this is a
    PREDICTOR of expected Gate 10 verdict, not a gate verdict. Real Gate 10
    reads on OOS stitched daily Net P&L from the actual WFO run.

    Two split conventions for cross-validation:
      (A) by trade count — first N/2 vs last N/2 trades, indexed by exit_ts
      (B) by time — chronological midpoint of [min(exit_ts), max(exit_ts)]
    """
    def pf_block(g: pd.DataFrame) -> tuple[float, float, float, int, float, float]:
        n = len(g)
        if n == 0:
            return float("nan"), float("nan"), 0.0, 0, float("nan"), float("nan")
        gp = float(g.loc[g["net_pnl_usd"] > 0, "net_pnl_usd"].sum())
        gl = float(g.loc[g["net_pnl_usd"] < 0, "net_pnl_usd"].sum())
        pf = gp / abs(gl) if gl < 0 else float("inf")
        wr = 100 * float((g["net_pnl_usd"] > 0).sum()) / n
        net = float(g["net_pnl_usd"].sum())
        avg = net / n
        return pf, wr, net, n, avg, gp / max(abs(gl), 1e-9)

    t = t.sort_values("exit_ts").reset_index(drop=True)
    print(f"\n--- {label} — Gate 10 pre-flight (PF ratio H1/H2, target [0.7, 1.3]) ---")

    # (A) by trade count
    mid_n = len(t) // 2
    h1a = t.iloc[:mid_n]
    h2a = t.iloc[mid_n:]
    pf1a, wr1a, net1a, n1a, *_ = pf_block(h1a)
    pf2a, wr2a, net2a, n2a, *_ = pf_block(h2a)
    ratio_a = pf1a / pf2a if (pf2a and pf2a == pf2a and pf2a != 0) else float("nan")
    print(f"  (A) by trade-count midpoint (mid at n={mid_n}):")
    print(f"    H1 [{h1a['exit_ts'].min().date()} .. {h1a['exit_ts'].max().date()}]: n={n1a}  PF={pf1a:.3f}  WR={wr1a:.2f}%  Net=${net1a:,.0f}")
    print(f"    H2 [{h2a['exit_ts'].min().date()} .. {h2a['exit_ts'].max().date()}]: n={n2a}  PF={pf2a:.3f}  WR={wr2a:.2f}%  Net=${net2a:,.0f}")
    print(f"    H1/H2 PF ratio = {ratio_a:.3f}    Gate 10 verdict: {'PASS' if 0.7 <= ratio_a <= 1.3 else 'FAIL'}")

    # (B) by time midpoint
    t0 = t["exit_ts"].min()
    t1 = t["exit_ts"].max()
    t_mid = t0 + (t1 - t0) / 2
    h1b = t[t["exit_ts"] <= t_mid]
    h2b = t[t["exit_ts"] > t_mid]
    pf1b, wr1b, net1b, n1b, *_ = pf_block(h1b)
    pf2b, wr2b, net2b, n2b, *_ = pf_block(h2b)
    ratio_b = pf1b / pf2b if (pf2b and pf2b == pf2b and pf2b != 0) else float("nan")
    print(f"  (B) by time midpoint ({t_mid.date()}):")
    print(f"    H1 [{h1b['exit_ts'].min().date()} .. {h1b['exit_ts'].max().date()}]: n={n1b}  PF={pf1b:.3f}  WR={wr1b:.2f}%  Net=${net1b:,.0f}")
    print(f"    H2 [{h2b['exit_ts'].min().date()} .. {h2b['exit_ts'].max().date()}]: n={n2b}  PF={pf2b:.3f}  WR={wr2b:.2f}%  Net=${net2b:,.0f}")
    print(f"    H1/H2 PF ratio = {ratio_b:.3f}    Gate 10 verdict: {'PASS' if 0.7 <= ratio_b <= 1.3 else 'FAIL'}")

    # (C) Fold-window split: §13 train (2022-01-11 → 2025-05-10) vs OOS (2025-05-11 → 2026-04-20)
    train_end = pd.Timestamp("2025-05-10 23:59:59")
    h1c = t[t["exit_ts"] <= train_end]
    h2c = t[t["exit_ts"] > train_end]
    pf1c, wr1c, net1c, n1c, *_ = pf_block(h1c)
    pf2c, wr2c, net2c, n2c, *_ = pf_block(h2c)
    ratio_c = pf1c / pf2c if (pf2c and pf2c == pf2c and pf2c != 0) else float("nan")
    print(f"  (C) Section 13 fold split (train <=2025-05-10 vs OOS >=2025-05-11) - diagnostic, not Gate 10:")
    print(f"    train: n={n1c}  PF={pf1c:.3f}  WR={wr1c:.2f}%  Net=${net1c:,.0f}")
    print(f"    OOS  : n={n2c}  PF={pf2c:.3f}  WR={wr2c:.2f}%  Net=${net2c:,.0f}")
    print(f"    train/OOS PF ratio = {ratio_c:.3f}")
    print(f"  Note: Gate 10 ACTUALLY reads on OOS-stitched daily Net P&L from Path B's")
    print(f"        per-fold OOS aggregation. This full-panel split is a PREDICTOR — if the")
    print(f"        winning grid config inherits v1.5's regime-concentration profile, expect FAIL.")


def oanda_bars_descriptive() -> None:
    """Descriptive characterization of OANDA XAGUSD m15 over fold-aligned window.
    Reports only; no overlay implication; no per-bar PnL inference."""
    bars = pd.read_csv(BARS, parse_dates=["time"])
    bars = bars.sort_values("time").reset_index(drop=True)
    bars["ret_15m"] = np.log(bars["close"]).diff()
    bars["abs_ret_15m"] = bars["ret_15m"].abs()
    bars["true_range"] = bars["high"] - bars["low"]
    bars["hour_utc"] = bars["time"].dt.hour
    bars["dow"] = bars["time"].dt.day_name()
    bars["year"] = bars["time"].dt.year
    print(f"\n=== OANDA XAGUSD m15 — descriptive ===")
    print(f"  Bars              : {len(bars):,}")
    print(f"  Span              : {bars['time'].min().date()} -> {bars['time'].max().date()}")
    print(f"  Mean |ret| / bar  : {1e4 * bars['abs_ret_15m'].mean():.2f} bp")
    print(f"  Std ret / bar     : {1e4 * bars['ret_15m'].std():.2f} bp")
    print(f"  Mean true range   : ${bars['true_range'].mean():.4f}  (median ${bars['true_range'].median():.4f})")
    print(f"  Skew (15m log-ret): {bars['ret_15m'].skew():.3f}")
    print(f"  Kurt (15m log-ret): {bars['ret_15m'].kurt():.2f}  (Gaussian=0; high -> fat tails)")
    # Vol regime by year
    print("\n  Realised vol by year (annualised from 15m, sqrt(96*252)):")
    for y, g in bars.groupby("year"):
        rv = g["ret_15m"].std() * np.sqrt(96 * 252)
        print(f"    {y}: ann_vol={rv*100:6.2f}%   n_bars={len(g):,}")
    # Top mover hours UTC
    print("\n  Mean |ret| by hour UTC (top 8):")
    by_h = bars.groupby("hour_utc")["abs_ret_15m"].mean().sort_values(ascending=False).head(8)
    for h, v in by_h.items():
        print(f"    {h:02d}: {1e4*v:5.2f} bp")
    # DoW
    print("\n  Mean |ret| by DoW (ranked):")
    by_d = bars.groupby("dow")["abs_ret_15m"].mean().sort_values(ascending=False)
    for d, v in by_d.items():
        print(f"    {d:9s}: {1e4*v:5.2f} bp")


def main() -> None:
    print("=" * 70)
    print("Q-CORR-1.2-adjacent forensic + descriptive survey")
    print("=" * 70)

    missing = [p for p in (SILVER, GOLD_DC, GOLD_33781, GOLD_13FAD, BARS) if not p.exists()]
    if missing:
        print("\nMissing vendor inputs (public-clone posture; this is expected on a fresh clone):")
        for p in missing:
            print(f"  - {p.relative_to(REPO)}")
        print("\nRestore via the canonical paths (TV exports + scripts/fetch_oanda_bars.py)")
        print("and re-run.")
        return

    t_silver = load_trades(SILVER)
    t_gold = load_trades(GOLD_DC)
    t_gold_xau_33781 = load_trades(GOLD_33781)
    t_gold_xau_13fad = load_trades(GOLD_13FAD)

    panel_summary(t_silver, "Silver v1.5 (_82815) - Pepperstone XAGUSD")
    panel_summary(t_gold,   "Gold v5.5 on XAGUSD (_dc6a3) - Pepperstone (Q-CORR-1.1 sec 7 anchor)")
    panel_summary(t_gold_xau_33781, "Gold v5.5 XAUUSD (_33781) - Pepperstone (CLAUDE.md lock anchor 2026-05-05)")
    panel_summary(t_gold_xau_13fad, "Gold v5.5 XAUUSD (_13fad) - Pepperstone (Q-CORR-1.2 sec 14 Gate-12 comparator 2026-05-12)")

    exit_reason_breakdown(t_silver, "v1.5 (_82815)")
    exit_reason_breakdown(t_gold,   "v5.5-on-XAGUSD (_dc6a3)")

    stale_drag_diagnostic(t_silver, "v1.5")
    dd_limit_diagnostic(t_silver, "v1.5")
    time_shape(t_silver, "v1.5")
    half_panel_split(t_silver, "v1.5 (_82815) XAGUSD")
    half_panel_split(t_gold,   "v5.5-on-XAGUSD (_dc6a3)")
    half_panel_split(t_gold_xau_33781, "v5.5 XAUUSD (_33781) - locked Gold anchor")
    half_panel_split(t_gold_xau_13fad, "v5.5 XAUUSD (_13fad) - Gate-12 comparator export")

    oanda_bars_descriptive()


if __name__ == "__main__":
    main()
