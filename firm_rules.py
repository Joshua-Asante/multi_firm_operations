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

# Unified allocations as of 2026-04-17 — challenge phase = funded phase.
# Source of truth: https://www.notion.so/346dc0b53c1181d1b8d5e12df4bd3810
# No re-sizing at pass; both tiers intentionally identical.
RISK_TIERS = {
    "challenge": {"guardian": 0.0030, "striker": 0.0100, "aegis": 0.0150},
    "funded":    {"guardian": 0.0030, "striker": 0.0100, "aegis": 0.0150},
}

# Baseline: Pine Script indicators output lot sizes for this account
BASELINE_BALANCE = 200_000
BASELINE_RISK = RISK_TIERS["challenge"]  # Guardian 0.30%, Striker 1.00%, Aegis 1.50%
