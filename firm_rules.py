"""
Firm rules as config. Add new firms by adding entries to FIRM_RULES dict.
"""

FIRM_RULES = {
    "FXIFY": {
        "dd_type": "static",
        "max_dd_pct": 5.0,
        "daily_loss_pct": 5.0,
        "profit_target_pct": 5.0,
        "min_trading_days": 5,
        "news_trading": True,
        "weekend_holds": True,
    },
    # Define when onboarding:
    # "FundedNext": { ... },
    # "The5ers": { ... },
    # "BrightFunded": { ... },
}

# Unified allocations — challenge phase = funded phase.
# Source of truth: https://www.notion.so/346dc0b53c1181d1b8d5e12df4bd3810
# Unified 2026-04-17; Guardian re-locked 0.30% → 0.34% on 2026-04-23 after
# Pepperstone-sourced CSVs (2022→2026) showed headroom under 1% bust + 5% p99 DD.
# Striker NAS100 v1 added 2026-05-07 at 0.40% (DXTrade contractValue=10
# broker-verified; 4-strategy MC anchor 97.88/0.22/4.55 already covers it).
# Phase axis retained as a lookup key for downstream callers, but both phases
# are byte-identical by construction so a future re-lock can't desync them.
_BASE_RISK = {"guardian": 0.0034, "striker": 0.0100, "aegis": 0.0150, "striker_nas100": 0.0040}
RISK_TIERS = {phase: _BASE_RISK for phase in ("challenge", "funded")}

# Baseline: Pine Script indicators output lot sizes for this account
BASELINE_BALANCE = 200_000
BASELINE_RISK = RISK_TIERS["challenge"]  # Guardian 0.34%, Striker 1.00%, Aegis 1.50%
