"""Pytest configuration and shared fixture loaders."""

from pathlib import Path

import pandas as pd
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def usdjpy_fixtures() -> pd.DataFrame:
    path = FIXTURES_DIR / "usdjpy_pnl_fixtures.csv"
    return pd.read_csv(path)
