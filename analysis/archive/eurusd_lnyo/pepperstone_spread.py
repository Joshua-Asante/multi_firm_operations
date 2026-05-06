"""Pepperstone-Razor session-conditional spread model (parametric).

Per parent brief §5 guardrail #1:
  Pepperstone-Razor session-conditional spread (mean + 2σ widening at 08:30 ET
  data-release minute, 10× normal during NFP first 60 sec). Constant-spread
  backtests overstate edge by ~30–50%; do not use.

Calibration: PARAMETRIC. Not empirically calibrated against an MT5 export
(parent brief §9 checklist calls for one but no sample is committed). User-
confirmed approach at plan ExitPlanMode: proceed parametric and document
calibration uncertainty in G1 verdict.

Defaults — Pepperstone Razor account, EURUSD:
  - Raw spread: 0.0–0.2 pips typical, 0.1 pip used as point estimate
  - Commission: $7/lot RT (≈ 0.6 pip on 1 lot of EURUSD at ~1.10)
  - Baseline all-in RT cost: ~0.7 pip
  - Per-side cost (one fill): 0.35 pip
  - Data-release widening factor (08:30 ET ±2 min): 3× baseline (mean+2σ proxy)
  - NFP first-minute factor: 10× baseline
  - Major-news minute set: 08:30 ET on US-data days; first Friday 08:30 = NFP

Inquire-phase use: per-fill cost. NYFBO has 2 fills per trade (entry + exit) so
the per-trade cost is 2× per-fill cost.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Set
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# Baseline per-fill cost, in pips, in normal session.
# 0.7 pip RT all-in / 2 fills = 0.35 pip per fill.
PEPPERSTONE_RAZOR_BASELINE_PIPS = 0.35

# Multipliers
DATA_RELEASE_FACTOR = 3.0   # 08:30 ET ±2 min on US data days
NFP_FACTOR = 10.0           # first 60 sec of NFP release


@dataclass(frozen=True)
class SpreadConfig:
    baseline_pips: float = PEPPERSTONE_RAZOR_BASELINE_PIPS
    data_release_factor: float = DATA_RELEASE_FACTOR
    nfp_factor: float = NFP_FACTOR


# US economic-release minutes that 08:30 ET typically delivers:
# NFP, CPI, PCE, retail sales, GDP advance, initial jobless claims (08:30 Thu),
# durable goods, ISM (10:00 ET — outside NYFBO window so not modeled).
DATA_RELEASE_HOUR_ET = 8
DATA_RELEASE_MINUTE_ET = 30
DATA_RELEASE_WINDOW_MINUTES = 2  # ±2 minutes around 08:30 ET


def _is_data_release_minute(et_dt: datetime) -> bool:
    """Return True if the bar starts within ±2 min of 08:30 ET on a weekday.

    Conservatively assumes a US data print might land any weekday 08:30 ET.
    Real-world refinement (only days with actual prints) would tighten this.
    The conservative approach widens spread on more bars, biasing edge low —
    safer for falsification.
    """
    if et_dt.tzinfo is None:
        raise ValueError("et_dt must be timezone-aware")
    et = et_dt.astimezone(ET)
    if et.weekday() >= 5:  # Sat/Sun
        return False
    target = time(DATA_RELEASE_HOUR_ET, DATA_RELEASE_MINUTE_ET)
    bar_minutes = et.hour * 60 + et.minute
    target_minutes = target.hour * 60 + target.minute
    return abs(bar_minutes - target_minutes) <= DATA_RELEASE_WINDOW_MINUTES


def _is_nfp_first_minute(et_dt: datetime) -> bool:
    """First Friday of the month at 08:30 ET ± 1 min — NFP heuristic.

    Approximate. Actual NFP dates vary (calendar-fixed first Friday with
    occasional shifts). Rare event — used only to flag the most extreme
    cost minute. NYFBO entry window starts 09:00 ET so NFP at 08:30 ET
    rarely directly hits an NYFBO fill, but inclusion in the model keeps
    shape correct for PDSB later if revisited.
    """
    if et_dt.tzinfo is None:
        raise ValueError("et_dt must be timezone-aware")
    et = et_dt.astimezone(ET)
    if et.weekday() != 4:  # Friday
        return False
    if et.day > 7:  # not first Friday
        return False
    target = time(DATA_RELEASE_HOUR_ET, DATA_RELEASE_MINUTE_ET)
    bar_minutes = et.hour * 60 + et.minute
    target_minutes = target.hour * 60 + target.minute
    return abs(bar_minutes - target_minutes) <= 1


def per_fill_cost_pips(et_dt: datetime, cfg: SpreadConfig | None = None) -> float:
    """Return the per-fill cost in pips at the given ET-aware timestamp.

    et_dt may be a UTC-aware or ET-aware datetime; both are accepted.
    """
    cfg = cfg or SpreadConfig()
    base = cfg.baseline_pips
    if _is_nfp_first_minute(et_dt):
        return base * cfg.nfp_factor
    if _is_data_release_minute(et_dt):
        return base * cfg.data_release_factor
    return base


def per_trade_cost_pips(entry_dt: datetime, exit_dt: datetime,
                         cfg: SpreadConfig | None = None) -> float:
    """Two-fill round-trip cost: entry + exit."""
    return per_fill_cost_pips(entry_dt, cfg) + per_fill_cost_pips(exit_dt, cfg)


# --- Self-test ---------------------------------------------------------------

def _self_test():
    """Quick probe — confirm the three regimes return expected ratios."""
    print("=== pepperstone_spread.py self-test ===")
    cfg = SpreadConfig()
    # Normal: 09:00 ET on Wednesday
    normal = datetime(2024, 9, 4, 9, 0, tzinfo=ET)  # Wed
    # Data-release: 08:30 ET on Wednesday (CPI day, hypothetically)
    drelease = datetime(2024, 9, 4, 8, 30, tzinfo=ET)
    # NFP first minute: 08:30 ET on first Friday
    nfp = datetime(2024, 9, 6, 8, 30, tzinfo=ET)  # Fri Sep 6 2024 (first Fri)

    cn = per_fill_cost_pips(normal, cfg)
    cd = per_fill_cost_pips(drelease, cfg)
    cf = per_fill_cost_pips(nfp, cfg)

    print(f"Normal session (09:00 ET Wed):    {cn:.3f} pips/fill")
    print(f"Data release  (08:30 ET Wed):    {cd:.3f} pips/fill   ({cd/cn:.1f}× normal)")
    print(f"NFP first min (08:30 ET 1st Fri):{cf:.3f} pips/fill   ({cf/cn:.1f}× normal)")
    print()
    # Round-trip cost for an NYFBO trade entering 09:15 ET, exiting 10:30 ET
    entry = datetime(2024, 9, 4, 9, 15, tzinfo=ET)
    exit_ = datetime(2024, 9, 4, 10, 30, tzinfo=ET)
    rt = per_trade_cost_pips(entry, exit_, cfg)
    print(f"NYFBO RT cost (09:15->10:30 ET):  {rt:.3f} pips/trade")
    print()
    print("Calibration: PARAMETRIC (literature defaults).")
    print("Verify ratios match parent brief §5 #1: data 3× normal; NFP 10× normal.")

    # Sanity assertions
    assert abs(cn - cfg.baseline_pips) < 1e-9
    assert abs(cd - cfg.baseline_pips * cfg.data_release_factor) < 1e-9
    assert abs(cf - cfg.baseline_pips * cfg.nfp_factor) < 1e-9
    print("OK")


if __name__ == "__main__":
    _self_test()
