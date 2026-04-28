"""Locked MC anchor pins.

Pepperstone is the CLAUDE.md canonical lock-anchor source. The 04-23 lock
decision used 92.73 / 0.65 / 4.94 against an in-flight panel that was not
committed; the committed 04-26 Pepperstone panel (the one in this repo)
reproduces 93.78 / 0.58 / 4.92 deterministically. Drift is within lock
criteria (bust <1%, p99 DD <5%); see CLAUDE.md "2026-04-23 lock MC anchors"
for the decision audit trail.

OANDA is the pattern-spotting proxy per the two-tier canonical rule. Its
anchor is pinned independently so a drift on either side surfaces.

Both anchors are deterministic given fixed SEEDS = (42, 123, 2026) in
portfolio_mc.py. Tolerance abs=1e-4 is comfortably tighter than any
acceptable drift; numpy/pandas float-arithmetic variations across patch
versions stay well within this.
"""

import pytest

from dd_protection import DD_SCALE, DD_TRIGGER
from portfolio_mc import ALLOCATIONS, compute_default_config


@pytest.fixture(scope="module")
def pepperstone_result():
    return compute_default_config(
        DD_TRIGGER, DD_SCALE, no_protection=False,
        allocs=ALLOCATIONS, panel_name="pepperstone",
    )


@pytest.fixture(scope="module")
def oanda_result():
    return compute_default_config(
        DD_TRIGGER, DD_SCALE, no_protection=False,
        allocs=ALLOCATIONS, panel_name="oanda",
    )


def test_pepperstone_anchor(pepperstone_result):
    """04-26 Pepperstone canonical anchor (code-reproducible)."""
    assert pepperstone_result["pass_rate"] == pytest.approx(0.9378, abs=1e-4)
    assert pepperstone_result["bust_rate"] == pytest.approx(0.0058, abs=1e-4)
    assert pepperstone_result["p99_dd"]    == pytest.approx(0.0492, abs=1e-4)


def test_oanda_anchor(oanda_result):
    """04-25 OANDA pattern-spotting proxy anchor."""
    assert oanda_result["pass_rate"] == pytest.approx(0.9605, abs=1e-4)
    assert oanda_result["bust_rate"] == pytest.approx(0.0048, abs=1e-4)
    assert oanda_result["p99_dd"]    == pytest.approx(0.0479, abs=1e-4)


def test_pepperstone_panel_shape(pepperstone_result):
    """Panel cardinality MVD: 1120 bdays, 223 week-blocks (Pepperstone)."""
    assert pepperstone_result["n_bdays"] == 1120
    assert pepperstone_result["n_blocks"] == 223


def test_oanda_panel_shape(oanda_result):
    """Panel cardinality MVD: 1120 bdays, 223 week-blocks (OANDA)."""
    assert oanda_result["n_bdays"] == 1120
    assert oanda_result["n_blocks"] == 223


def test_default_panel_is_pepperstone():
    """Locks the doc-and-default-agreement decision from 135e93c.

    `test_pepperstone_anchor` and `test_oanda_anchor` both pass because they
    use `panel_name=` explicitly. Neither exercises the bare
    `python portfolio_mc.py` path, which depends only on the argparse
    default (which mirrors `DEFAULT_PANEL`) and the function-signature
    defaults of compute_default_config / mode_default / mode_sensitivity.

    If a future refactor flips any of these back to "oanda", the anchor
    tests stay green but `python portfolio_mc.py` (no flags) starts
    producing OANDA numbers (96.05/0.48/4.79) instead of the CLAUDE.md
    canonical headline (Pepperstone, 93.78/0.58/4.92). This test catches
    that drift before it reaches the CLAUDE.md / code asymmetry surface
    we just spent effort closing.
    """
    import inspect

    import portfolio_mc as mc

    assert mc.DEFAULT_PANEL == "pepperstone"
    for fn in (mc.compute_default_config, mc.mode_default, mc.mode_sensitivity):
        actual = inspect.signature(fn).parameters["panel_name"].default
        assert actual == "pepperstone", (
            f"{fn.__name__} default panel_name is {actual!r}, expected 'pepperstone'"
        )


def test_lock_criteria_satisfied(pepperstone_result):
    """Lock criteria from CLAUDE.md: bust <1%, p99 DD <5%.

    Pepperstone is the lock-decision panel. If either gate is breached, the
    locked allocation (G 0.34% / S 1.00% / A 1.50%) and dd_protection config
    (DD_TRIGGER=0.010, DD_SCALE=0.40) need re-evaluation per the 2026-04-17
    ADR — do NOT bypass this check by tweaking constants.
    """
    assert pepperstone_result["bust_rate"] < 0.01
    assert pepperstone_result["p99_dd"] < 0.05


def test_serial_parallel_equivalence():
    """joblib --parallel must produce byte-identical output to sequential.

    Each seed's RNG is seeded inside run_seed(), so the parallel path is just
    a different scheduling of the same independent computations. If joblib
    ever introduces non-determinism (e.g. backend change, worker reuse bug),
    this test catches it before --parallel gets used in a lock decision.
    """
    serial = compute_default_config(
        DD_TRIGGER, DD_SCALE, no_protection=False,
        allocs=ALLOCATIONS, panel_name="pepperstone", parallel=False,
    )
    parallel = compute_default_config(
        DD_TRIGGER, DD_SCALE, no_protection=False,
        allocs=ALLOCATIONS, panel_name="pepperstone", parallel=True,
    )
    for key in (
        "pass_rate", "bust_rate", "p50_dd", "p95_dd", "p99_dd",
        "bust_daily_rate", "bust_static_rate", "timeout_rate",
        "n_bdays", "n_blocks", "median_days_to_pass",
    ):
        assert serial[key] == parallel[key], (
            f"divergence at {key}: serial={serial[key]!r} parallel={parallel[key]!r}"
        )
