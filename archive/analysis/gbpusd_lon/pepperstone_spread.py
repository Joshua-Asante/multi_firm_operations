"""Pepperstone-Razor session-conditional spread model — GBPUSD (parametric).

Per parent Notice §5 #1 (spread model provenance):
  GBPUSD-specific parametric Pepperstone-Razor model required. Calibration source
  must be stated explicitly: typical-spread reference, sample window, known
  divergence vs Pepperstone live quotes, news-minute multipliers (UK 07:00 BST,
  US 13:30 BST). Sensitivity at 1.25× mandatory.

Calibration: PARAMETRIC. Not empirically calibrated against an MT5 export
(parent Notice §9 deferred this; same status as the EURUSD predecessor). The
1.25× spread sensitivity (mandatory per parent Notice §4.2) does the load-bearing
work in the falsification — kill verdicts are reported at both 1.0× and 1.25×.

Defaults — Pepperstone Razor account, GBPUSD:
  - Raw spread: 0.2-0.6 pips typical, 0.4 pip used as point estimate
  - Commission: $7/lot RT (≈ 0.6 pip on 1 lot of GBPUSD at ~1.25)
  - Baseline all-in RT cost: ~1.0 pip (parent Notice §1.4 — 0.4 pip wider than EURUSD's ~0.7)
  - Per-side cost (one fill): 0.5 pip
  - UK 07:00 BST data-release multiplier: 2.0× baseline for 60 min post-release
    (i.e., 07:00–08:00 BST window). Conservative parametric estimate; UK
    releases (BoE / ONS — CPI, GDP, employment, retail sales, BoE rate) are
    GBPUSD-dominant news risk and elevated spread can persist 30–60 min post.
    Calibration uncertainty disclosed; 1.25× sensitivity captures this.
  - US 13:30 BST (= 08:30 ET) multiplier: 3.0× baseline (USD-leg news;
    CPI/NFP/PCE/retail-sales). Outside H-LORB's time-stop (11:00 BST) so
    rarely binds for the H-LORB exit, but included for completeness.
  - NFP first-minute factor: 10.0× baseline (08:30 ET 1st Friday). Same
    rationale as US 13:30 BST multiplier — outside H-LORB time-stop.

Inquire-phase use: per-fill cost in pips. H-LORB has 2 fills per trade
(entry + exit) so per-trade cost = 2 × per-fill cost.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
BST = ZoneInfo("Europe/London")

# Baseline per-fill cost in pips, normal session.
# 1.0 pip RT all-in / 2 fills = 0.5 pip per fill (parent Notice §1.4).
PEPPERSTONE_RAZOR_BASELINE_PIPS = 0.5

# Multipliers
UK_RELEASE_FACTOR = 2.0     # 07:00-08:00 BST post-release residual (UK)
US_DATA_RELEASE_FACTOR = 3.0  # 08:30 ET ±2 min on US data days
NFP_FACTOR = 10.0           # first 60 sec of NFP release


@dataclass(frozen=True)
class SpreadConfig:
    baseline_pips: float = PEPPERSTONE_RAZOR_BASELINE_PIPS
    uk_release_factor: float = UK_RELEASE_FACTOR
    us_data_release_factor: float = US_DATA_RELEASE_FACTOR
    nfp_factor: float = NFP_FACTOR


# UK release window: 07:00-07:59 BST on weekdays (residual extends to ~08:00 BST).
# Parametric — applied conservatively (every weekday, not just confirmed release
# dates). This widens spread on more bars, biasing edge low — falsification-friendly.
UK_RELEASE_HOUR_BST = 7

# US release: 08:30 ET = 13:30 BST (summer) / 13:30 BST (winter, since US shifts
# but ET timestamp is on US calendar). The ET-anchored check is correct for
# the US release calendar regardless of UK BST/GMT state.
US_DATA_RELEASE_HOUR_ET = 8
US_DATA_RELEASE_MINUTE_ET = 30
US_DATA_RELEASE_WINDOW_MINUTES = 2


def _is_uk_release_window(et_dt: datetime) -> bool:
    """Return True if the bar starts within 07:00-07:59 BST on a weekday.

    UK 07:00 BST data releases (BoE / ONS) — CPI, GDP, employment, retail sales,
    BoE Bank Rate. Conservative: applied to every weekday at 07:00-07:59 BST,
    not just confirmed release days.
    """
    if et_dt.tzinfo is None:
        raise ValueError("et_dt must be timezone-aware")
    bst = et_dt.astimezone(BST)
    if bst.weekday() >= 5:
        return False
    return bst.hour == UK_RELEASE_HOUR_BST


def _is_us_data_release_minute(et_dt: datetime) -> bool:
    """Return True if the bar starts within ±2 min of 08:30 ET on a weekday."""
    if et_dt.tzinfo is None:
        raise ValueError("et_dt must be timezone-aware")
    et = et_dt.astimezone(ET)
    if et.weekday() >= 5:
        return False
    target = time(US_DATA_RELEASE_HOUR_ET, US_DATA_RELEASE_MINUTE_ET)
    bar_minutes = et.hour * 60 + et.minute
    target_minutes = target.hour * 60 + target.minute
    return abs(bar_minutes - target_minutes) <= US_DATA_RELEASE_WINDOW_MINUTES


def _is_nfp_first_minute(et_dt: datetime) -> bool:
    """First Friday of the month at 08:30 ET ± 1 min — NFP heuristic."""
    if et_dt.tzinfo is None:
        raise ValueError("et_dt must be timezone-aware")
    et = et_dt.astimezone(ET)
    if et.weekday() != 4:
        return False
    if et.day > 7:
        return False
    target = time(US_DATA_RELEASE_HOUR_ET, US_DATA_RELEASE_MINUTE_ET)
    bar_minutes = et.hour * 60 + et.minute
    target_minutes = target.hour * 60 + target.minute
    return abs(bar_minutes - target_minutes) <= 1


def per_fill_cost_pips(et_dt: datetime, cfg: SpreadConfig | None = None) -> float:
    """Per-fill cost in pips at the given tz-aware timestamp.

    Precedence: NFP first minute > US data release > UK release window > baseline.
    """
    cfg = cfg or SpreadConfig()
    base = cfg.baseline_pips
    if _is_nfp_first_minute(et_dt):
        return base * cfg.nfp_factor
    if _is_us_data_release_minute(et_dt):
        return base * cfg.us_data_release_factor
    if _is_uk_release_window(et_dt):
        return base * cfg.uk_release_factor
    return base


def per_trade_cost_pips(entry_dt: datetime, exit_dt: datetime,
                         cfg: SpreadConfig | None = None) -> float:
    """Two-fill round-trip cost: entry + exit."""
    return per_fill_cost_pips(entry_dt, cfg) + per_fill_cost_pips(exit_dt, cfg)


# --- Self-test ---------------------------------------------------------------

def _self_test():
    print("=== pepperstone_spread.py (GBPUSD) self-test ===")
    cfg = SpreadConfig()
    # Normal: 09:15 BST on Wednesday (post-OR, baseline)
    normal = datetime(2024, 9, 4, 9, 15, tzinfo=BST)
    # UK release: 07:30 BST on Wednesday
    uk = datetime(2024, 9, 4, 7, 30, tzinfo=BST)
    # US data: 08:30 ET = 13:30 BST in summer on Wednesday
    us = datetime(2024, 9, 4, 8, 30, tzinfo=ET)
    # NFP: 08:30 ET first Friday
    nfp = datetime(2024, 9, 6, 8, 30, tzinfo=ET)

    cn = per_fill_cost_pips(normal, cfg)
    cu = per_fill_cost_pips(uk, cfg)
    cd = per_fill_cost_pips(us, cfg)
    cf = per_fill_cost_pips(nfp, cfg)

    print(f"Normal session (09:15 BST Wed):    {cn:.3f} pips/fill")
    print(f"UK release    (07:30 BST Wed):    {cu:.3f} pips/fill   ({cu/cn:.1f}× normal)")
    print(f"US data       (08:30 ET Wed):     {cd:.3f} pips/fill   ({cd/cn:.1f}× normal)")
    print(f"NFP first min (08:30 ET 1st Fri): {cf:.3f} pips/fill   ({cf/cn:.1f}× normal)")
    print()

    # H-LORB RT cost: entry 09:15 BST, exit 11:00 BST (same day, post-OR)
    entry = datetime(2024, 9, 4, 9, 15, tzinfo=BST)
    exit_ = datetime(2024, 9, 4, 11, 0, tzinfo=BST)
    rt = per_trade_cost_pips(entry, exit_, cfg)
    print(f"H-LORB RT cost (09:15->11:00 BST): {rt:.3f} pips/trade  (= 2× baseline = ~1.0 pip)")
    print()
    print("Calibration: PARAMETRIC (parent Notice §1.4 + §5 #1).")
    print("Verify ratios match: UK 2.0× baseline; US 3.0×; NFP 10.0×.")

    # Sanity assertions
    assert abs(cn - cfg.baseline_pips) < 1e-9, f"baseline drift: {cn} vs {cfg.baseline_pips}"
    assert abs(cu - cfg.baseline_pips * cfg.uk_release_factor) < 1e-9, "UK factor drift"
    assert abs(cd - cfg.baseline_pips * cfg.us_data_release_factor) < 1e-9, "US factor drift"
    assert abs(cf - cfg.baseline_pips * cfg.nfp_factor) < 1e-9, "NFP factor drift"
    print("OK")


if __name__ == "__main__":
    _self_test()
