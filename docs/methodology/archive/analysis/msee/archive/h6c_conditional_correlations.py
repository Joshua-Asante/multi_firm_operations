"""MSEE H6c — Cross-strategy correlations conditional on stress regime.

Q-MSEE-6c from docs/methodology/msee/open_questions.md (also tests P2).

Khandani-Lo (2011) showed that crowded-strategy correlations rise sharply
during liquidity / unwind events even when normal-regime correlations are
near zero. The MSEE storage-effect mechanism predicts the opposite for
*niche-partitioned* strategies: correlations stay near zero in stress
regimes too, because the niche separation is along regime-orthogonal
axes.

Stress proxy (no VIX in panel): max(|XAUUSD daily ret|, |US30USD daily
ret|, |USDJPY daily ret|), with top-5% of that distribution flagged as
stress days. Two reads of pairwise correlations:

  (a) all-days, 0-fill: the operational view — non-trading strategies
      contribute 0 to portfolio that day. Biases correlations toward 0
      and is the right metric for portfolio P&L behavior.
  (b) both-traded-only: the latent joint return distribution; better
      reflects the "if both fired together, how would they co-move?"
      question that drives Khandani-Lo unwind.

Auto-Forward trigger: any pair correlation > 0.3 in stress slice (either
read) opens a Forward question on Khandani-Lo crowded-unwind risk. Does
NOT auto-route Action — Pepperstone re-fit + four-rules still required.

PRE-Q GATE:
  D: Restricted to 420 trade-dates joined to bar-derived stress flags.
  S: Single-day stress proxy from |daily ret|; alternatives logged for
     follow-up.
  A: Bootstrap CIs on Pearson; O(seconds).

Reproducibility: `python analysis/msee/h6c_conditional_correlations.py`
"""
from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "identify" / "2026-04-26"))

from common import STRATEGIES, load_bars  # noqa: E402

DAILY_CSV = ROOT / "analysis" / "msee" / "daily_strategy_returns.csv"
OUT_JSON = ROOT / "analysis" / "msee" / "h6c_conditional_correlations.json"

STRESS_PCTILE = 0.95   # top-5%
N_BOOTSTRAP = 2000
SEED = 2026
AUTO_FORWARD_THRESHOLD = 0.30

INSTRUMENT_BAR = {
    "guardian": "XAUUSD",
    "striker": "US30USD",
    "aegis": "USDJPY",
}


def daily_index_returns() -> pd.DataFrame:
    """Daily close-to-close pct returns for each strategy's underlying."""
    out = None
    for s, sym in INSTRUMENT_BAR.items():
        bars = load_bars(sym)
        # Close at last bar of each calendar day (UTC). Using NY-local axis
        # would be more correct for trade alignment but daily |ret| as a
        # stress proxy is robust to this.
        bars["date"] = bars.index.normalize().date
        daily_close = bars.groupby("date")["close"].last()
        ret = daily_close.pct_change().rename(f"{s}_idx_ret")
        out = ret.to_frame() if out is None else out.join(ret, how="outer")
    out.index.name = "date"
    return out.reset_index()


def stress_flag(idx_ret: pd.DataFrame, pctile: float) -> pd.DataFrame:
    cols = [c for c in idx_ret.columns if c.endswith("_idx_ret")]
    idx_ret["stress_proxy"] = idx_ret[cols].abs().max(axis=1)
    threshold = float(np.nanpercentile(idx_ret["stress_proxy"].dropna(), pctile * 100))
    idx_ret["is_stress"] = (idx_ret["stress_proxy"] >= threshold).astype(int)
    idx_ret.attrs["stress_threshold"] = threshold
    return idx_ret


def bootstrap_corr_ci(x: np.ndarray, y: np.ndarray, n: int, seed: int
                      ) -> tuple[float, tuple[float, float]]:
    """Pearson r with percentile bootstrap CI95."""
    rng = np.random.default_rng(seed)
    mask = np.isfinite(x) & np.isfinite(y)
    xx, yy = x[mask], y[mask]
    if len(xx) < 5:
        return float("nan"), (float("nan"), float("nan"))
    point = float(np.corrcoef(xx, yy)[0, 1])
    rs = np.empty(n)
    idx = np.arange(len(xx))
    for i in range(n):
        sample = rng.choice(idx, size=len(xx), replace=True)
        # Guard against zero-variance resamples.
        a, b = xx[sample], yy[sample]
        if np.std(a) == 0 or np.std(b) == 0:
            rs[i] = np.nan
            continue
        rs[i] = float(np.corrcoef(a, b)[0, 1])
    rs = rs[np.isfinite(rs)]
    if len(rs) < 10:
        return point, (float("nan"), float("nan"))
    return point, (float(np.percentile(rs, 2.5)), float(np.percentile(rs, 97.5)))


def correlations_on_slice(slice_df: pd.DataFrame, label: str) -> dict:
    out = {"label": label, "n_days": int(len(slice_df)), "pairs": {}}
    for a, b in combinations(STRATEGIES, 2):
        # All-days (0-fill) view
        x_all = slice_df[f"{a}_R"].values.astype(float)
        y_all = slice_df[f"{b}_R"].values.astype(float)
        r_all, ci_all = bootstrap_corr_ci(x_all, y_all, N_BOOTSTRAP, SEED)
        # Both-traded-only view
        mask = (slice_df[f"{a}_n_trades"] > 0) & (slice_df[f"{b}_n_trades"] > 0)
        x_b = slice_df.loc[mask, f"{a}_R"].values.astype(float)
        y_b = slice_df.loc[mask, f"{b}_R"].values.astype(float)
        r_both, ci_both = bootstrap_corr_ci(x_b, y_b, N_BOOTSTRAP, SEED + 1)
        out["pairs"][f"{a}_{b}"] = {
            "all_days_zerofill": {
                "n": int(len(x_all)),
                "r": r_all, "ci95": list(ci_all),
            },
            "both_traded": {
                "n": int(mask.sum()),
                "r": r_both, "ci95": list(ci_both),
            },
        }
    return out


def main() -> None:
    daily = pd.read_csv(DAILY_CSV, parse_dates=["exit_date_ny"])
    daily["date"] = daily["exit_date_ny"].dt.date

    idx = daily_index_returns()
    idx = stress_flag(idx, STRESS_PCTILE)
    threshold = idx.attrs["stress_threshold"]

    merged = daily.merge(idx[["date", "stress_proxy", "is_stress"]],
                         on="date", how="left")
    # Trade-dates with no bar match (none expected) get is_stress=0.
    merged["is_stress"] = merged["is_stress"].fillna(0).astype(int)

    full = correlations_on_slice(merged, "all_trade_dates")
    stress = correlations_on_slice(merged[merged["is_stress"] == 1], "stress_dates")
    calm = correlations_on_slice(merged[merged["is_stress"] == 0], "calm_dates")

    # Auto-Forward check.
    triggered = []
    for label, block in [("stress", stress), ("calm", calm), ("full", full)]:
        for pair, vals in block["pairs"].items():
            for view in ("all_days_zerofill", "both_traded"):
                r = vals[view]["r"]
                if r is not None and not np.isnan(r) and r > AUTO_FORWARD_THRESHOLD:
                    triggered.append({
                        "slice": label, "pair": pair, "view": view, "r": r,
                    })

    summary = {
        "question": "Q-MSEE-6c — stress-conditional correlations (P2, H6c)",
        "feed": "OANDA",
        "canonical_status": "PROXY",
        "stress_proxy": "max(|XAUUSD daily ret|, |US30USD daily ret|, |USDJPY daily ret|)",
        "stress_pctile": STRESS_PCTILE,
        "stress_threshold": threshold,
        "n_bootstrap": N_BOOTSTRAP,
        "auto_forward_threshold": AUTO_FORWARD_THRESHOLD,
        "auto_forward_triggers": triggered,
        "slices": {
            "full": full,
            "stress": stress,
            "calm": calm,
        },
        "verdict": (
            f"AUTO-FORWARD TRIGGERED: {len(triggered)} pair-views exceed "
            f"r>{AUTO_FORWARD_THRESHOLD} in some slice — Khandani-Lo "
            f"crowded-unwind Forward question opened (Pepperstone re-fit "
            f"required before Action)"
            if triggered
            else f"POSITIVE: no pair correlation exceeds r>{AUTO_FORWARD_THRESHOLD} "
            f"in any slice — storage-effect niche partitioning holds "
            f"under stress (P2 prediction supported)"
        ),
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2, default=str))

    print("MSEE H6c — Stress-conditional correlations")
    print(f"  Stress proxy: max(|G_idx|, |S_idx|, |A_idx|) daily |ret|")
    print(f"  Stress threshold (top-{(1-STRESS_PCTILE)*100:.0f}%): "
          f"{threshold:.4f} ({threshold*100:.2f}%)")
    print(f"  Trade-dates: {len(merged)} total, "
          f"{merged['is_stress'].sum()} stress, "
          f"{(merged['is_stress'] == 0).sum()} calm")
    print()
    for label, block in [("FULL", full), ("STRESS", stress), ("CALM", calm)]:
        print(f"  {label}  (n={block['n_days']})")
        for pair, vals in block["pairs"].items():
            ad = vals["all_days_zerofill"]
            bt = vals["both_traded"]
            print(f"    {pair:18s}  all-days:  r={ad['r']:+.3f}  "
                  f"CI=[{ad['ci95'][0]:+.3f},{ad['ci95'][1]:+.3f}] (n={ad['n']})")
            r_str = f"r={bt['r']:+.3f}" if not np.isnan(bt['r']) else "r=nan"
            ci_str = (f"CI=[{bt['ci95'][0]:+.3f},{bt['ci95'][1]:+.3f}]"
                      if not np.isnan(bt['ci95'][0]) else "CI=[nan,nan]")
            print(f"    {' ':18s}  both-tr:   {r_str}  {ci_str} (n={bt['n']})")
        print()
    print(f"  Verdict: {summary['verdict']}")
    print(f"Wrote: {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
