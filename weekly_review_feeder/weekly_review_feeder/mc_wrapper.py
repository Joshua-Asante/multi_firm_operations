"""portfolio_mc.py wrapper — STUB.

Per spec §0 Rule-0: confirm portfolio_mc.py CLI surface before implementing this.
The function below describes the contract; wire to your actual portfolio_mc.py invocation.

Two implementation options:

OPTION A — Subprocess invocation (preferred if portfolio_mc.py is a CLI):

    import subprocess, json, sys
    def get_mc_band_for_week(week_start, week_end):
        result = subprocess.run(
            [sys.executable, 'portfolio_mc.py',
             '--week-start', week_start.isoformat(),
             '--week-end', week_end.isoformat(),
             '--mode', 'json'],
            capture_output=True, text=True, check=True,
        )
        return json.loads(result.stdout)

OPTION B — Direct import (preferred if portfolio_mc.py exposes a callable):

    from prop_firm_pipeline import portfolio_mc
    def get_mc_band_for_week(week_start, week_end):
        return portfolio_mc.weekly_band(week_start, week_end)

Required output schema:
    {"p10": float, "p50": float, "p90": float}

These are the 10th/50th/90th percentile of weekly P&L from the portfolio MC
calibrated against the locked Pepperstone 52mo panel (Jan 2022 – Apr 2026).
The MC anchor: 98.09 / 0.36 / 4.73.
"""
from __future__ import annotations

from datetime import date


def get_mc_band_for_week(
    week_start: date, week_end: date
) -> dict[str, float]:
    """Return {p10, p50, p90} for the given trading week.

    STUB — wire to portfolio_mc.py per docstring above.
    """
    raise NotImplementedError(
        "Wire to portfolio_mc.py per spec §0 Rule-0 read. "
        "See module docstring for two implementation options."
    )
