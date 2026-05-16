"""Boundary tests for the FXIFY-correct inactivity simulator (Q-MCTO-1 Phase 1).

Per Q-MCTO-1 §7, three boundary properties must hold:
  1. consecutive_idle == 59 does NOT trigger bust_inactivity
  2. consecutive_idle == 60 DOES trigger bust_inactivity
  3. A single non-zero day resets the counter
  4. (added) Inactivity bust has culprit=None (semantically "no one traded")
  5. (added) Offsetting non-zero pnls (e.g. +$100/-$100) are NOT idle

The simulator lives at `scripts/inactivity_simulator.py`. This test does not
import `portfolio_mc.py` — it tests the simulator in isolation.
"""

from __future__ import annotations
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import numpy as np
import pytest

from inactivity_simulator import (
    simulate_path,
    INACTIVITY_LIMIT,
    HORIZON_CAP,
    STARTING_EQUITY,
)

N_STRATS = 4
DD_TRIGGER = 0.015
DD_SCALE = 0.40


def _build_path(rows: list[list[float]]) -> np.ndarray:
    """Construct an (n_days, n_strats) path from a list of per-day strat-pnl rows."""
    arr = np.array(rows, dtype=float)
    assert arr.shape[1] == N_STRATS, f"each row must have {N_STRATS} pnl values"
    return arr


# ── 1. consecutive_idle == 59 does NOT trigger ──────────────────────────

def test_idle_59_does_not_trigger_inactivity():
    """59 consecutive all-zero days followed by a small positive day should
    NOT produce bust_inactivity. Counter resets on day 60 (the non-zero day)."""
    rows = [[0.0, 0.0, 0.0, 0.0]] * 59 + [[1.0, 0.0, 0.0, 0.0]] + [[0.0, 0.0, 0.0, 0.0]] * 10
    path = _build_path(rows)
    outcome, day, max_dd, culprit = simulate_path(path, DD_TRIGGER, DD_SCALE)
    assert outcome != "bust_inactivity", (
        f"59 idle + 1 trade + 10 idle should NOT trigger inactivity bust; got {outcome} on day {day}"
    )
    assert outcome == "horizon_cap"  # path ends without hitting any bust or pass


# ── 2. consecutive_idle == 60 DOES trigger ──────────────────────────────

def test_idle_60_triggers_inactivity():
    """60 consecutive all-zero days should produce bust_inactivity on day 60."""
    rows = [[0.0, 0.0, 0.0, 0.0]] * 60 + [[1000.0, 0.0, 0.0, 0.0]]  # day 61 won't be reached
    path = _build_path(rows)
    outcome, day, max_dd, culprit = simulate_path(path, DD_TRIGGER, DD_SCALE)
    assert outcome == "bust_inactivity", f"60 idle days should trigger; got {outcome}"
    assert day == 60, f"should fire on day 60; got day {day}"
    assert culprit is None, f"inactivity bust has no culprit; got {culprit}"


def test_idle_60_after_initial_trade_still_triggers():
    """One trade then 60 consecutive idle should still trigger on idle-day 60."""
    rows = [[100.0, 0.0, 0.0, 0.0]] + [[0.0, 0.0, 0.0, 0.0]] * 60
    path = _build_path(rows)
    outcome, day, max_dd, culprit = simulate_path(path, DD_TRIGGER, DD_SCALE)
    assert outcome == "bust_inactivity"
    assert day == 61  # 1 trade day + 60 idle days


# ── 3. Single non-zero day resets the counter ───────────────────────────

def test_single_trade_resets_counter():
    """59 idle + 1 trade + 59 idle should NOT trigger (counter resets on trade)."""
    rows = (
        [[0.0, 0.0, 0.0, 0.0]] * 59
        + [[100.0, 0.0, 0.0, 0.0]]
        + [[0.0, 0.0, 0.0, 0.0]] * 59
    )
    path = _build_path(rows)
    outcome, day, max_dd, culprit = simulate_path(path, DD_TRIGGER, DD_SCALE)
    assert outcome != "bust_inactivity", (
        f"counter should reset after non-zero day; got {outcome} on day {day}"
    )


def test_single_negative_trade_also_resets_counter():
    """Counter resets on any non-zero pnl, including negative."""
    rows = (
        [[0.0, 0.0, 0.0, 0.0]] * 59
        + [[-50.0, 0.0, 0.0, 0.0]]
        + [[0.0, 0.0, 0.0, 0.0]] * 59
    )
    path = _build_path(rows)
    outcome, day, _, _ = simulate_path(path, DD_TRIGGER, DD_SCALE)
    assert outcome != "bust_inactivity"


# ── 4. Inactivity bust has culprit=None ─────────────────────────────────

def test_inactivity_bust_culprit_is_none():
    """Daily/static busts have culprit=int; inactivity bust has culprit=None."""
    rows = [[0.0, 0.0, 0.0, 0.0]] * 60
    path = _build_path(rows)
    outcome, _, _, culprit = simulate_path(path, DD_TRIGGER, DD_SCALE)
    assert outcome == "bust_inactivity"
    assert culprit is None


def test_daily_bust_has_int_culprit():
    """Sanity: a daily-bust path produces an integer culprit. Strategy 2 (NAS-position)
    blows up hardest — verifies argmin attribution still works."""
    # Day 1: large negative on strategy 2, everything else zero
    rows = [[0.0, 0.0, -0.06 * STARTING_EQUITY, 0.0]]
    path = _build_path(rows)
    outcome, day, _, culprit = simulate_path(path, DD_TRIGGER, DD_SCALE)
    assert outcome == "bust_daily"
    assert day == 1
    assert culprit == 2


# ── 5. Offsetting non-zero pnls are NOT idle ────────────────────────────

def test_offsetting_pnls_not_idle():
    """If strategy 0 makes +$100 and strategy 1 loses $100 same day, total pnl is 0
    but np.any(strat_pnls != 0) is True — NOT idle. Counter should reset, not increment."""
    rows = (
        [[0.0, 0.0, 0.0, 0.0]] * 30
        + [[100.0, -100.0, 0.0, 0.0]]   # offsetting day — total pnl = 0 but trades happened
        + [[0.0, 0.0, 0.0, 0.0]] * 30
    )
    path = _build_path(rows)
    outcome, day, _, _ = simulate_path(path, DD_TRIGGER, DD_SCALE)
    # 30 idle + 1 offsetting (resets counter) + 30 idle = 30 max consecutive idle
    # should NOT trigger inactivity bust at INACTIVITY_LIMIT=60
    assert outcome != "bust_inactivity", (
        f"offsetting pnls reset the counter (real trades happened); got {outcome} on day {day}"
    )


# ── Determinism check ──────────────────────────────────────────────────

def test_inactivity_at_boundary_constant_matches_60():
    """Pin the constant. Phase 2 + ADR adoption shifts here; this test forces co-edit."""
    assert INACTIVITY_LIMIT == 60, (
        f"INACTIVITY_LIMIT must match FXIFY firm_rules.py:14 inactivity_max_idle_days=60; "
        f"got {INACTIVITY_LIMIT}"
    )


def test_horizon_cap_is_safety_only():
    """Safety cap must be much larger than INACTIVITY_LIMIT so it's effectively never hit
    on FXIFY-correct semantics. 1500 = 25x INACTIVITY_LIMIT = >5 calendar years of bdays."""
    assert HORIZON_CAP >= 25 * INACTIVITY_LIMIT, (
        f"HORIZON_CAP={HORIZON_CAP} too small relative to INACTIVITY_LIMIT={INACTIVITY_LIMIT}"
    )
