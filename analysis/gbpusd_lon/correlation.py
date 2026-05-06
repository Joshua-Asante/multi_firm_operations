"""Conditional Pearson correlation harness for H-LORB.

Loads Pepperstone TV-export trade-history CSVs for G/S/A (the existing canonical
lock anchor per portfolio_mc.py:58-78), aggregates to daily P&L, and computes
correlations conditional on per-strategy active-day masks.

Pepperstone CSV panels are STRATEGY-side, not pair-side, so they carry over
unchanged from the EURUSD predecessor port (parent Notice §5 #6 + entry stub §5).

Conditional masks (verified independently from Pine source):
  Striker-active  = Tue + Fri (strategies/striker/striker_dj30_v4.4.pine:109)
  Guardian-active = Mon/Tue/Thu (strategies/guardian/guardian_gold_v5.5.pine:78-82)
  Aegis-active    = Mon/Tue/Wed (strategies/aegis/aegis_usdjpy_v4.3.pine:190)
  Friday-only sub-test for Striker (parent Notice §5 #6 + kill #4 footnote).

Per parent Notice §4.3 H-LORB kill criteria:
  kill #4: |r| daily P&L vs Striker (Tue+Fri conditional) > 0.30 -> KILL
  kill #5: |r| daily P&L vs G/S/A composite > 0.20 -> KILL
  Friday-only sub-test recorded but does not rescue gate.

Per parent Notice §5 #7 (DXY anti-correlation):
  GBPUSD long P&L vs DXY change (negative correlation expected if not DXY-coupled);
  pooled and conditional on Guardian-active dow.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).parent.parent.parent
PEPPERSTONE_DIR = REPO_ROOT / "data" / "tv_exports" / "pepperstone"

# DOW masks (pandas dayofweek: Mon=0..Sun=6)
STRIKER_DOW = {1, 4}        # Tue, Fri
GUARDIAN_DOW = {0, 1, 3}    # Mon, Tue, Thu
AEGIS_DOW = {0, 1, 2}       # Mon, Tue, Wed
FRI_ONLY = {4}


PEPPERSTONE_PANELS = {
    "guardian": PEPPERSTONE_DIR / "Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-05_33781.csv",
    "striker":  PEPPERSTONE_DIR / "Striker_DJ30_v4.4_PEPPERSTONE_US30_2026-04-26_3eea0.csv",
    "aegis":    PEPPERSTONE_DIR / "Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-04-26_0bf1b.csv",
}


def _load_strategy_daily(path: Path) -> pd.Series:
    """Load TV trade-history CSV; return daily P&L series indexed by date."""
    df = pd.read_csv(path, encoding="utf-8-sig")
    exits = df[df["Type"].astype(str).str.startswith("Exit")].copy()
    exits["exit_date"] = pd.to_datetime(exits["Date and time"]).dt.normalize()
    exits = exits.rename(columns={"Net P&L USD": "pnl"})
    out = exits.groupby("exit_date")["pnl"].sum()
    out.name = path.stem
    return out


def load_gsa_daily_panel() -> pd.DataFrame:
    """Load the three Pepperstone strategies into a daily P&L panel."""
    series = {}
    for s, path in PEPPERSTONE_PANELS.items():
        series[s] = _load_strategy_daily(path)
    panel = pd.concat(series, axis=1).fillna(0.0)
    panel.columns = list(series.keys())
    bdays = pd.bdate_range(panel.index.min(), panel.index.max())
    return panel.reindex(bdays).fillna(0.0)


@dataclass
class CorrSlice:
    label: str
    n: int
    pearson_r: float
    pvalue: float | None


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2 or x.std(ddof=0) == 0 or y.std(ddof=0) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def conditional_correlation(
    h_lorb_daily: pd.Series,
    other_daily: pd.Series,
    *,
    dow_mask: set[int] | None,
    label: str,
) -> CorrSlice:
    """Compute conditional Pearson correlation on aligned dates."""
    aligned = pd.concat([h_lorb_daily, other_daily], axis=1, join="inner")
    aligned.columns = ["h_lorb", "other"]
    if dow_mask is not None:
        aligned = aligned[aligned.index.dayofweek.isin(list(dow_mask))]
    aligned = aligned.dropna()
    n = len(aligned)
    if n < 2:
        return CorrSlice(label=label, n=n, pearson_r=float("nan"), pvalue=None)
    r = _pearson(aligned["h_lorb"].values, aligned["other"].values)
    return CorrSlice(label=label, n=n, pearson_r=r, pvalue=None)


def composite_gsa(panel: pd.DataFrame) -> pd.Series:
    """Equal-weight per-strategy z-score composite."""
    z_cols = []
    for s in panel.columns:
        col = panel[s].copy()
        nz = col[col != 0]
        sigma = nz.std(ddof=0) if len(nz) > 1 else 1.0
        if sigma == 0:
            sigma = 1.0
        z_cols.append(col / sigma)
    z = pd.concat(z_cols, axis=1)
    return z.sum(axis=1).rename("gsa_composite")


def all_correlation_slices(
    h_lorb_daily: pd.Series,
    panel: pd.DataFrame,
    *,
    dxy_daily: pd.Series | None = None,
) -> dict[str, CorrSlice]:
    """Compute all per-criterion conditional correlations for G1.

    Slices:
      striker_active_TueFri    — kill #4 (threshold 0.30)
      striker_friday_only      — kill #4 sub-test (diagnostic only)
      striker_pooled           — diagnostic only
      guardian_active_MonTueThu— kill #5 contributor
      aegis_active_MonTueWed   — kill #5 contributor
      gsa_composite_active     — kill #5 (G/S/A composite, threshold 0.20)
      dxy_guardian_dow         — guardrail #7 (DXY anti-correlation, threshold 0.30)
      dxy_pooled               — guardrail #7 pooled
    """
    out: dict[str, CorrSlice] = {}
    out["striker_pooled"] = conditional_correlation(
        h_lorb_daily, panel["striker"], dow_mask=None, label="Striker pooled (diagnostic)"
    )
    out["striker_active_TueFri"] = conditional_correlation(
        h_lorb_daily, panel["striker"], dow_mask=STRIKER_DOW,
        label="Striker | Tue+Fri (kill #4)"
    )
    out["striker_friday_only"] = conditional_correlation(
        h_lorb_daily, panel["striker"], dow_mask=FRI_ONLY,
        label="Striker | Friday-only sub-test"
    )
    out["guardian_active_MonTueThu"] = conditional_correlation(
        h_lorb_daily, panel["guardian"], dow_mask=GUARDIAN_DOW,
        label="Guardian | Mon/Tue/Thu"
    )
    out["aegis_active_MonTueWed"] = conditional_correlation(
        h_lorb_daily, panel["aegis"], dow_mask=AEGIS_DOW,
        label="Aegis | Mon/Tue/Wed"
    )
    composite = composite_gsa(panel)
    out["gsa_composite_active"] = conditional_correlation(
        h_lorb_daily, composite, dow_mask={0, 1, 2, 3, 4},
        label="G/S/A composite | all weekdays (kill #5)"
    )
    if dxy_daily is not None:
        out["dxy_pooled"] = conditional_correlation(
            h_lorb_daily, dxy_daily, dow_mask=None,
            label="DXY chg | pooled (guardrail #7)"
        )
        out["dxy_guardian_dow"] = conditional_correlation(
            h_lorb_daily, dxy_daily, dow_mask=GUARDIAN_DOW,
            label="DXY chg | Guardian-active dow (guardrail #7)"
        )
    return out


def summarize_slices(slices: dict[str, CorrSlice]) -> pd.DataFrame:
    rows = []
    for k, s in slices.items():
        rows.append({
            "key": k,
            "label": s.label,
            "n": s.n,
            "pearson_r": s.pearson_r,
            "pvalue": s.pvalue,
        })
    return pd.DataFrame(rows)


def _probe():
    print("=== correlation.py (H-LORB) probe — Pepperstone G/S/A panel ===")
    panel = load_gsa_daily_panel()
    print(f"Panel: {panel.index.min().date()} -> {panel.index.max().date()}  ({len(panel)} bdays)")
    print(panel.head())
    print()
    print("Per-strategy non-zero days:")
    for s in panel.columns:
        nz = (panel[s] != 0).sum()
        print(f"  {s}: {nz} non-zero / {len(panel)}  mean=${panel[s].mean():.2f}")


if __name__ == "__main__":
    _probe()
