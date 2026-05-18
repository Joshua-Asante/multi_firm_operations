"""ADR 2026-05-16-fixture-test-requirement anchor: TV <30-day JPY ~153× P&L inflation defect (Q-MT5-TV)."""

from pathlib import Path

import pandas as pd
import pytest

from tv_mt5_pnl_reconciliation import (
    compute_pnl,
    compute_pnl_tv_buggy,
    holding_days,
    is_tv_short_horizon,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "usdjpy_pnl_fixtures.csv"


@pytest.fixture
def usdjpy_fixtures() -> pd.DataFrame:
    return pd.read_csv(FIXTURE_PATH, comment="#", skipinitialspace=True)


def test_usdjpy_pnl_within_tolerance(usdjpy_fixtures: pd.DataFrame) -> None:
    """ADR 2026-05-16-fixture-test-requirement anchor: TV <30-day JPY ~153x inflation defect.

    For each fixture, computed P&L must match reference within tolerance.
    Tolerance is wide enough for legitimate spread/rounding,
    narrow enough that order-of-magnitude defects fail.
    """
    for _, row in usdjpy_fixtures.iterrows():
        computed = compute_pnl(
            entry_price=row["entry_price"],
            exit_price=row["exit_price"],
            lot_size=row["lot_size"],
            direction=row["direction"],
            entry_time=row["entry_time"],
            exit_time=row["exit_time"],
        )
        assert abs(computed - row["expected_pnl_usd"]) <= row["tolerance_usd"], (
            f"P&L drift on fixture {row['case_id']}: "
            f"computed={computed:.2f}, expected={row['expected_pnl_usd']}, "
            f"tolerance=±{row['tolerance_usd']}"
        )


def test_boundary_hold_not_classified_as_short_horizon(usdjpy_fixtures: pd.DataFrame) -> None:
    """30 calendar days must not trigger the <30-day TV conversion path."""
    boundary = usdjpy_fixtures.loc[usdjpy_fixtures["case_id"] == "boundary_long_30d"].iloc[0]
    hold = holding_days(boundary["entry_time"], boundary["exit_time"])
    assert hold == 30
    assert not is_tv_short_horizon(hold)


def test_deliberate_153x_regression_fails_tolerance(usdjpy_fixtures: pd.DataFrame) -> None:
    """Simulated TV bug (no JPY→USD on <30d holds) must exceed ±$5 tolerance."""
    row = usdjpy_fixtures.loc[usdjpy_fixtures["case_id"] == "canonical_long_lt30d"].iloc[0]
    buggy = compute_pnl_tv_buggy(
        entry_price=row["entry_price"],
        exit_price=row["exit_price"],
        lot_size=row["lot_size"],
        direction=row["direction"],
        entry_time=row["entry_time"],
        exit_time=row["exit_time"],
    )
    correct = compute_pnl(
        entry_price=row["entry_price"],
        exit_price=row["exit_price"],
        lot_size=row["lot_size"],
        direction=row["direction"],
    )
    assert buggy > correct * 100
    assert abs(buggy - row["expected_pnl_usd"]) > row["tolerance_usd"]
