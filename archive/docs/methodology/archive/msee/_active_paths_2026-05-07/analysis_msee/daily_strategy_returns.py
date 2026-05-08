"""MSEE Phase 0 — per-strategy daily P&L matrix on a common date axis.

Builds the foundational data primitive every downstream MSEE hypothesis
(H1–H10) needs: a wide-format daily frame keyed on exit_date_ny with one
column-set per strategy. Existing analysis/q14_daily_portfolio.csv only
carries the joint sum (total_pnl_R) — useful for portfolio-level work but
not for per-strategy regime decomposition, geometric uplift attribution,
alpha-decay fits, conditional correlations, or community-matrix estimation.

Output: analysis/msee/daily_strategy_returns.csv with columns:
    exit_date_ny,
    guardian_R, striker_R, aegis_R,                 # daily R sum per strategy
    guardian_pnl_usd, striker_pnl_usd, aegis_pnl_usd,
    guardian_n_trades, striker_n_trades, aegis_n_trades,
    portfolio_R                                     # = sum of three R cols

Convention: rows are the union of trade-exit dates across all three
strategies. Strategies that did not trade on a given row carry 0 for R,
USD, and n_trades. Callers wanting a full business-day axis should
left-join to a calendar (e.g., for H2 regime-feature work). 0 here means
"no trade taken", not "trade with zero P&L".

PRE-Q GATE (per anthropic-skills:inqhiori-algorithm §3):
  D: Restricted scope to closed (entry+exit) trades on the OANDA-proxy
     panels. Did NOT delete any cohort by P&L sign, by day-of-week, or by
     "doesn't-fit-narrative" criterion. Forbidden D-test self-check passed.
  S: Compressed to per-(date, strategy) frame. Loses intra-day trade
     ordering and pyramid-leg structure but preserves the per-day R sum
     that all downstream hypotheses operate on. Pyramid decomposition
     remains available via existing analysis/striker_pyramid_decomposition.py.
  A: None needed — three CSV loads + one pivot, O(seconds).

  Regression invariant (verifies S didn't lose information): per-day sum
  of (guardian_R + striker_R + aegis_R) MUST equal q14_daily_portfolio.csv
  total_pnl_R within 1e-6 on every row. Asserted in main().

SCOPE BINDING:
  - Source: data/tv_exports/oanda/{Guardian,Striker,Aegis}*.csv
  - Canonical status: PROXY (OANDA panel, per AMENDMENT_oanda_rescope.md).
    No finding from this primitive can authorize Action without Pepperstone
    re-fit (gated separately).
  - No production touch. Read-only on locked TV exports.

Reproducibility: `python analysis/msee/daily_strategy_returns.py`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "identify" / "2026-04-26"))
sys.path.insert(0, str(ROOT / "lib"))

from common import STRATEGIES, PARAMS, load_tv  # noqa: E402
from mvd import (  # noqa: E402
    assert_min_rows,
    assert_window,
    assert_tv_export,
    assert_reconciled,
)

OUT_CSV = ROOT / "analysis" / "msee" / "daily_strategy_returns.csv"
OUT_JSON = ROOT / "analysis" / "msee" / "daily_strategy_returns.json"
Q14_DAILY = ROOT / "analysis" / "q14_daily_portfolio.csv"

EXPECTED = {
    "guardian": ("Guardian", "v5.5", "OANDA", "XAUUSD"),
    "striker":  ("Striker",  "v4.4", "OANDA", "US30USD"),
    "aegis":    ("Aegis",    "v4.3", "OANDA", "USDJPY"),
}


def per_strategy_daily(strategy: str) -> pd.DataFrame:
    """Daily R, USD P&L, and trade count for one strategy.

    R := net_pnl_pct / risk_pct, summed per exit_date_ny.
    """
    info = STRATEGIES[strategy]
    tv_path = ROOT / "data" / "tv_exports" / "oanda" / info["tv"]
    expected = EXPECTED[strategy]
    assert_tv_export(
        tv_path,
        expected_strategy=expected[0],
        expected_version=expected[1],
        expected_broker=expected[2],
        expected_symbol=expected[3],
    )
    tv = load_tv(strategy)
    tv = tv.dropna(subset=["entry_time", "exit_time", "net_pnl_pct"]).copy()

    # MVD cardinality + window — same floors as portfolio_mc loader.
    assert_min_rows(len(tv), 100, label=f"MSEE TV-load {strategy}")
    assert_window(
        tv["exit_time"].min().to_pydatetime(),
        tv["exit_time"].max().to_pydatetime(),
        expected_min_days=4 * 365,
        label=f"MSEE TV-load {strategy}",
        tolerance_days=60,
    )

    risk_pct = PARAMS[strategy]["risk_pct"]
    tv["exit_date_ny"] = tv["exit_time"].dt.date
    tv["net_pnl_R"] = tv["net_pnl_pct"] / risk_pct

    daily = tv.groupby("exit_date_ny").agg(
        R=("net_pnl_R", "sum"),
        pnl_usd=("net_pnl_usd", "sum"),
        n_trades=("net_pnl_R", "size"),
    ).reset_index()
    daily.columns = [
        "exit_date_ny",
        f"{strategy}_R",
        f"{strategy}_pnl_usd",
        f"{strategy}_n_trades",
    ]
    return daily


def main() -> None:
    frames = [per_strategy_daily(s) for s in STRATEGIES]

    # Outer-join on exit_date_ny — union of all trading dates.
    wide = frames[0]
    for f in frames[1:]:
        wide = wide.merge(f, on="exit_date_ny", how="outer")

    # 0-fill non-trading-strategy slots. Document: 0 = no trade taken.
    fill_cols = [c for c in wide.columns if c != "exit_date_ny"]
    wide[fill_cols] = wide[fill_cols].fillna(0)
    int_cols = [c for c in wide.columns if c.endswith("_n_trades")]
    wide[int_cols] = wide[int_cols].astype(int)
    wide = wide.sort_values("exit_date_ny").reset_index(drop=True)

    # Portfolio R sum (matches q14 total_pnl_R definition: sum of per-trade
    # net_pnl_R across all strategies on the day).
    wide["portfolio_R"] = (
        wide["guardian_R"] + wide["striker_R"] + wide["aegis_R"]
    )

    # MVD reconcile — regression invariant against existing q14 daily file.
    # If this assertion fires, either an upstream TV export changed, the R
    # definition drifted, or q14 needs to be re-run. Either way, downstream
    # MSEE work must not proceed on a silently divergent foundation.
    q14 = pd.read_csv(Q14_DAILY)
    q14["exit_date_ny"] = pd.to_datetime(q14["exit_date_ny"]).dt.date
    joined = wide.merge(q14[["exit_date_ny", "total_pnl_R"]], on="exit_date_ny",
                        how="inner")
    n_join = len(joined)
    n_q14 = len(q14)
    n_wide = len(wide)
    if abs(n_wide - n_q14) > 5:
        raise AssertionError(
            f"MSEE Phase 0: row-count drift vs q14: wide={n_wide}, q14={n_q14}, "
            f"joined={n_join} (tolerance ±5)"
        )
    # Per-row reconciliation, every joined row.
    diff = (joined["portfolio_R"] - joined["total_pnl_R"]).abs()
    worst = float(diff.max())
    if worst > 1e-6:
        bad = joined.loc[diff > 1e-6, ["exit_date_ny", "portfolio_R",
                                       "total_pnl_R"]].head(10)
        raise AssertionError(
            f"MSEE Phase 0: per-row R reconcile failed; worst |Δ|={worst:.2e}\n"
            f"Sample divergences:\n{bad}"
        )

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    wide.to_csv(OUT_CSV, index=False)

    # Summary stats for the json artefact.
    summary = {
        "primitive": "per-strategy daily R, USD, trade-count on common date axis",
        "feed": "OANDA",
        "canonical_status": "PROXY",
        "panel_window": [
            wide["exit_date_ny"].min().isoformat(),
            wide["exit_date_ny"].max().isoformat(),
        ],
        "n_trade_dates": int(n_wide),
        "q14_reconcile": {
            "rows_joined": int(n_join),
            "worst_abs_diff_R": worst,
            "tolerance_R": 1e-6,
        },
        "per_strategy": {
            s: {
                "n_trade_dates": int((wide[f"{s}_n_trades"] > 0).sum()),
                "n_trades_total": int(wide[f"{s}_n_trades"].sum()),
                "sum_R": float(wide[f"{s}_R"].sum()),
                "sum_pnl_usd": float(wide[f"{s}_pnl_usd"].sum()),
            }
            for s in STRATEGIES
        },
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2))

    # Stdout: brief, scannable. ASCII-only for Windows cp1252 consoles.
    print(f"MSEE daily strategy returns: {wide['exit_date_ny'].min()} -> "
          f"{wide['exit_date_ny'].max()}  ({n_wide} trade-dates)")
    print(f"  q14 reconcile: {n_join} rows joined, worst |dR| = {worst:.2e}")
    for s in STRATEGIES:
        per = summary["per_strategy"][s]
        print(f"  {s:9s}  trade-dates={per['n_trade_dates']:4d}  "
              f"trades={per['n_trades_total']:4d}  "
              f"sum_R={per['sum_R']:+8.2f}  "
              f"sum_$={per['sum_pnl_usd']:+12,.0f}")
    print(f"Wrote: {OUT_CSV.relative_to(ROOT)}")
    print(f"       {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
