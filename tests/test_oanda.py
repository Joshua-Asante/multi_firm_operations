"""Tests for lib/oanda.py.

Pure-python tests run unconditionally. The live API smoke test is skipped
when ~/.keys/oanda.txt is absent (e.g. in CI) — locally it confirms the
SDK round-trip + the end-of-window epoch comparison fix.
"""

from pathlib import Path

import pytest

from lib.oanda import (
    LIVE_HOST,
    PRACTICE_HOST,
    _host_for_account,
    _iso_to_epoch,
)


def test_practice_host_for_101_prefix():
    assert _host_for_account("101-001-12345678-001") == PRACTICE_HOST


def test_live_host_for_001_prefix():
    assert _host_for_account("001-001-12345678-001") == LIVE_HOST


def test_unrecognized_prefix_raises():
    with pytest.raises(ValueError, match="Unrecognized"):
        _host_for_account("999-001-12345678-001")


def test_iso_to_epoch_handles_oanda_nanosecond_format():
    """Both forms must produce equal epochs — the bug we hit had a lexical
    string-compare treating them as different and yielding off-by-one
    boundary candles."""
    e_ns = _iso_to_epoch("2024-01-03T00:00:00.000000000Z")
    e_plain = _iso_to_epoch("2024-01-03T00:00:00Z")
    assert e_ns == e_plain


# ──────────────────────────────────────────────────────────────────────
# Live API smoke test — skipped when creds are absent
# ──────────────────────────────────────────────────────────────────────

NEEDS_OANDA = pytest.mark.skipif(
    not Path.home().joinpath(".keys/oanda.txt").exists(),
    reason="OANDA creds not present at ~/.keys/oanda.txt",
)


@NEEDS_OANDA
def test_fetch_candles_one_day_parity():
    """Fixed historical window: USD/JPY 2024-01-02 yields exactly 96 M15
    candles, ending at 23:45. End-of-window comparison must use epoch
    semantics so the boundary candle at 2024-01-03T00:00:00 is excluded."""
    from lib.oanda import fetch_candles
    rows = list(fetch_candles(
        "USD_JPY", "2024-01-02T00:00:00Z", "2024-01-03T00:00:00Z"
    ))
    assert len(rows) == 96
    assert rows[0]["time"] == "2024-01-02T00:00:00.000000000Z"
    assert rows[-1]["time"] == "2024-01-02T23:45:00.000000000Z"
