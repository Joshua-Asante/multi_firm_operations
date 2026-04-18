"""
FXIFY Portfolio Optimization — Configuration
All strategy parameters, challenge rules, and risk allocations.
"""

# ─────────────────────────────────────────────
# CHALLENGE RULES
# ─────────────────────────────────────────────
CHALLENGE = {
    "account_size": 200_000,
    "profit_target_pct": 5.0,       # $10,000
    "max_daily_loss_pct": 5.0,      # $10,000
    "max_total_dd_pct": 5.0,        # static, non-trailing
    "min_trading_days": 5,
    "profit_target_usd": 10_000,
    "max_daily_loss_usd": 10_000,
    "max_total_dd_usd": 10_000,
}

# ─────────────────────────────────────────────
# STRATEGY DEFINITIONS
# ─────────────────────────────────────────────
STRATEGIES = {
    "guardian": {
        "name": "Guardian Gold v3.8",
        "instrument": "XAUUSD",
        "timeframe": "15min",
        "type": "trend-following",
        "direction": "long_only",
        "risk_pct_challenge": 0.30,
        "risk_pct_funded": 0.45,
        "active_days": ["Monday", "Tuesday", "Thursday"],
        "session_est": (8, 16),     # 8:00 - 16:00 EST
        "csv_filename": "Guardian_Gold_v3.8_FXIFY_OANDA_XAUUSD_2026-04-11_eae41.csv",
        # Backtest baselines (4yr)
        "baseline": {
            "total_profit": 205_255,
            "profit_factor": 3.35,
            "win_rate": 0.667,
            "max_dd_pct": 2.58,
            "total_trades": 261,
        },
        # Parameters (reference only — DO NOT CHANGE)
        "params": {
            "ema_slow": 385,
            "ema_fast": 25,
            "sl_atr_mult": 1.55,
            "be_trigger_atr": 0.8,
            "be_offset_atr": 0.17,
            "tp_atr_mult": 28.0,
            "trail_ema": 36,
            "trail_trigger_atr": 3.8,
        },
    },
    "striker": {
        "name": "Striker DJ30 v4.1",
        "instrument": "DJ30",
        "timeframe": "15min",
        "type": "breakout",
        "direction": "long_only",
        "risk_pct_challenge": 0.70,
        "risk_pct_funded": 0.75,
        "active_days": ["Tuesday", "Friday"],
        "session_est": (8, 12),     # 8:00 - 12:00 EST (13-17 UTC)
        "csv_filename": "Striker_DJ30_v4.1_FINAL_VANTAGE_DJ30_2026-04-10_03f6f.csv",
        "baseline": {
            "total_profit": 144_135,
            "profit_factor": 2.40,
            "win_rate": 0.775,
            "max_dd_pct": 3.51,
            "total_trades": 285,
        },
        "params": {
            "atr_fast": 11,
            "atr_slow": 85,
            "expansion_thresh": 0.28,
            "body_ratio": 0.25,
            "sl_atr_mult": 1.4,
            "tp_atr_mult": 7.5,
            "t1_atr": 1.6,
            "t1_pct": 0.25,
            "be_trigger_atr": 0.10,
            "be_offset_atr": 0.05,
            "trail_trigger": 0.17,
            "pyramid_atr": 1.29,
            "pyramid_size_pct": 2.0,
            "pyramid_min_bars": 5,
            "max_bars": 55,
        },
    },
    "aegis": {
        "name": "Aegis-Reversion USDJPY v4",
        "instrument": "USDJPY",
        "timeframe": "15min",
        "type": "mean-reversion",
        "direction": "long_only",
        "risk_pct_challenge": 0.75,
        "risk_pct_funded": 0.80,
        "active_days": ["Monday", "Tuesday", "Wednesday"],
        "session_est": (10, 13.75),  # 10:00 - 13:45 EST
        "csv_filename": "Aegis-Reversion_USDJPY_v4_OANDA_USDJPY_2026-04-10_318eb.csv",
        "baseline": {
            "total_profit": 64_898,
            "profit_factor": 2.33,
            "win_rate": 0.601,
            "max_dd_pct": 2.78,
            "total_trades": 168,
        },
        "params": {
            "bb_length": 19,
            "bb_mult": 1.9,
            "bb_source": "close",
            "atr_length": 17,
            "sl_atr_mult": 1.5,
            "tp_basis_offset_atr": 0.8,
            "be_trigger_atr": 0.30,
            "be_offset_atr": 0.15,
            "h11_blocked": True,
            "max_trades_per_day": 1,
            "max_hold_bars": 40,
            "min_atr": 0.05,
        },
    },
}

# ─────────────────────────────────────────────
# MONTE CARLO SETTINGS
# ─────────────────────────────────────────────
MONTE_CARLO = {
    "n_simulations": 10_000,
    "seed": 42,
    "account_size": CHALLENGE["account_size"],
    "target_pct": CHALLENGE["profit_target_pct"],
    "dd_limit_pct": CHALLENGE["max_total_dd_pct"],
    "daily_loss_limit_pct": CHALLENGE["max_daily_loss_pct"],
}

# ─────────────────────────────────────────────
# COLUMN MAPPING (TradingView CSV export)
# ─────────────────────────────────────────────
# Update these if your CSV column names differ
COLUMN_MAP = {
    "trade_num": "Trade #",
    "type": "Type",           # "Exit long" in current TV exports
    "signal": "Signal",
    "datetime": "Date and time",
    "price": "Price USD",     # Aegis uses "Price JPY" — handled in loader
    "contracts": "Size (qty)",
    "profit": "Net P&L USD",
    "cum_profit": "Cumulative P&L USD",
    "run_up": "Favorable excursion USD",
    "drawdown": "Adverse excursion USD",
}

# ─────────────────────────────────────────────
# OUT-OF-SAMPLE SPLIT
# ─────────────────────────────────────────────
OOS_SPLIT = {
    "train_start": "2021-01-01",
    "train_end": "2023-12-31",
    "test_start": "2024-01-01",
    "test_end": "2025-12-31",
}

# ─────────────────────────────────────────────
# ANALYSIS SETTINGS
# ─────────────────────────────────────────────
ANALYSIS = {
    "risk_scaling_steps": [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35,
                           0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70,
                           0.75, 0.80],
    "equity_thresholds_pct": [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
    "dd_warning_thresholds_pct": [1.0, 1.5, 2.0, 2.5, 3.0, 3.5],
    "session_windows_utc": {
        "tokyo": (0, 9),
        "london": (7, 16),
        "ny": (13, 22),
        "london_ny_overlap": (13, 16),
        "thin_liquidity": (22, 0),
    },
}
