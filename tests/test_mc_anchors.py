"""Locked MC anchor pins.

Pepperstone is the CLAUDE.md canonical lock-anchor source. The 2026-05-16
ADR replaced the 150-bday horizon-runout timeout with the FXIFY-correct
semantic (60-bday inactivity bust + 1500-bday safety ceiling), closing
Q-MCTO-1 CLOSED-RESOLVED. The canonical 4-strategy config (G 0.34% /
DJ30 v4.5 0.75% pyr 500% / A v4.3 1.50% / NAS v1 0.45%, dd_protection C2)
on the 2026-05-14 Pepperstone panel reproduces 99.88 / 0.12 / 4.21
deterministically — both lock criteria (bust <1%, p99 DD <5%) clear with
the widest margin on record, and median days-to-pass holds at 21. Bust
attribution under the FXIFY-correct semantic: guardian 40.0% / aegis
37.1% / striker_nas100 14.3% / striker 8.6% (35 total busts across 30K
sims). Prior 2026-05-14 allocation-refresh anchor (98.78 / 0.12 / 4.17
under 150-bday semantics) and 2026-05-08 C2 anchor (98.09 / 0.36 / 4.73)
remain in CLAUDE.md "Prior anchors (historical)" for comparison. See
docs/adr/2026-05-16-fxify-correct-timeout-semantic.md for the lock
decision.

OANDA is the pattern-spotting proxy per the two-tier canonical rule. OANDA
NAS100 panel does not exist; OANDA still on DJ30 v4.4 (no v4.5 OANDA fetch
yet). OANDA C2 anchor under FXIFY-correct semantic reproduces 99.51% pass /
0.49% bust / 4.82% p99 DD on the 1120-bday / 223-block OANDA panel — both
lock criteria clear with thinner margin than Pepperstone, consistent with
OANDA's pattern-spotting role. The 2026-05-14 panel refresh did not include
OANDA — OANDA panel remains 2026-04-25 / 2026-05-08 vintage.

Both anchors are deterministic given fixed SEEDS = (42, 123, 2026) in
portfolio_mc.py. Tolerance abs=1e-4 is comfortably tighter than any
acceptable drift; numpy/pandas float-arithmetic variations across patch
versions stay well within this.
"""

import math

import numpy as np
import pytest

from dd_protection import DD_SCALE, DD_TRIGGER
from portfolio_mc import (
    ALLOCATIONS,
    DAILY_LOSS_PCT,
    HORIZON_CAP,
    INACTIVITY_LIMIT,
    OANDA_PANELS,
    PEPPERSTONE_PANELS,
    STARTING_EQUITY,
    STRATS,
    _simulate_path,
    compute_default_config,
)

_PEPPERSTONE_PRESENT = all(p.exists() for p in PEPPERSTONE_PANELS.values())
_OANDA_PRESENT = all(p.exists() for p in OANDA_PANELS.values())

requires_pepperstone = pytest.mark.skipif(
    not _PEPPERSTONE_PRESENT,
    reason="Pepperstone TV-export CSVs not present (gitignored vendor data; see data/tv_exports/pepperstone/SHA256SUMS).",
)
requires_oanda = pytest.mark.skipif(
    not _OANDA_PRESENT,
    reason="OANDA TV-export CSVs not present (gitignored vendor data; see data/tv_exports/oanda/SHA256SUMS).",
)


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


@requires_pepperstone
def test_pepperstone_anchor(pepperstone_result):
    """2026-05-16 FXIFY-correct timeout-semantic Pepperstone 4-strategy C2 anchor.

    portfolio_mc.py's 150-bday horizon-runout timeout was replaced with the
    FXIFY-correct semantic (60-bday inactivity bust + 1500-bday safety
    ceiling) per ADR 2026-05-16-fxify-correct-timeout-semantic.md (closes
    Q-MCTO-1 CLOSED-RESOLVED). Allocations + dd_protection C2 unchanged
    from 2026-05-14 allocation refresh. The new semantic re-validates with
    the widest margin on record:
      pass 98.78% → 99.88%   (+1.10pp; ex-timeout paths now resolve as passes)
      bust 0.12% → 0.12%     (unchanged; risk behavior unchanged)
      p99 DD 4.17% → 4.21%   (+0.04pp; within sampling noise)
      median days 21 → 21    (unchanged)
    Both gates clear with margin. See ADR §Locked MC numbers.
    """
    assert pepperstone_result["pass_rate"] == pytest.approx(0.9988, abs=1e-4)
    assert pepperstone_result["bust_rate"] == pytest.approx(0.0012, abs=1e-4)
    assert pepperstone_result["p99_dd"]    == pytest.approx(0.0421, abs=1e-4)


@requires_oanda
def test_oanda_anchor(oanda_result):
    """2026-05-16 FXIFY-correct timeout-semantic OANDA C2 anchor (pattern-spotting).

    OANDA panel unchanged (2026-04-25 / 2026-05-08 vintage; no re-export).
    The FXIFY-correct timeout-semantic ADR (2026-05-16) reshapes the OANDA
    anchor identically in principle to Pepperstone — ex-timeout paths now
    resolve as passes:
      pass 96.33% → 99.51%   (+3.18pp; OANDA had a larger timeout bucket)
      bust 0.40% → 0.49%     (+0.09pp; some ex-timeout paths bust later)
      p99 DD 4.73% → 4.82%   (+0.09pp; longer horizon exposes deeper paths)
      median days 26 → 27    (small +1d shift)
    Both lock criteria clear with thinner margin than Pepperstone (bust
    0.51pp headroom vs 0.88pp; p99 DD 0.18pp headroom vs 0.79pp),
    consistent with OANDA's pattern-spotting role.
    """
    assert oanda_result["pass_rate"] == pytest.approx(0.9951, abs=1e-4)
    assert oanda_result["bust_rate"] == pytest.approx(0.0049, abs=1e-4)
    assert oanda_result["p99_dd"]    == pytest.approx(0.0482, abs=1e-4)


@requires_pepperstone
def test_pepperstone_panel_shape(pepperstone_result):
    """Panel cardinality MVD: 1039 bdays, 207 week-blocks (Pepperstone 2026-05-14).

    Panel shape unchanged from the 2026-05-14 panel-refresh anchor (1039
    bdays / 207 week-blocks). The 2026-05-14 allocation refresh swapped
    DJ30 + NAS100 CSV vintages but preserved the union date range —
    Aegis's 2022-07-18 first signal still defines the union-start.
    Drops from 1120 / 223 (pre-2026-05-14) reflect the strict 4yr window
    (2022-05-14 → 2026-05-14) vs the prior all-data exports back to 2022-01.
    """
    assert pepperstone_result["n_bdays"] == 1039
    assert pepperstone_result["n_blocks"] == 207


@requires_oanda
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
    producing OANDA numbers (96.23/0.69/4.91 at C2) instead of the CLAUDE.md
    canonical headline (Pepperstone, 98.78/0.12/4.17 at C2 under the
    2026-05-14 allocation refresh). This test catches that drift before
    it reaches the CLAUDE.md / code asymmetry surface we just spent effort
    closing.
    """
    import inspect

    import portfolio_mc as mc

    assert mc.DEFAULT_PANEL == "pepperstone"
    for fn in (mc.compute_default_config, mc.mode_default, mc.mode_sensitivity):
        actual = inspect.signature(fn).parameters["panel_name"].default
        assert actual == "pepperstone", (
            f"{fn.__name__} default panel_name is {actual!r}, expected 'pepperstone'"
        )


@requires_pepperstone
def test_lock_criteria_satisfied(pepperstone_result):
    """Lock criteria from CLAUDE.md: bust <1%, p99 DD <5%.

    Pepperstone is the lock-decision panel. If either gate is breached, the
    locked allocation (G 0.34% / S 1.00% / A 1.50% / NAS 0.40%) and
    dd_protection config (DD_TRIGGER=0.015, DD_SCALE=0.40 — C2 relock
    2026-05-08) need re-evaluation — do NOT bypass this check by tweaking
    constants.
    """
    assert pepperstone_result["bust_rate"] < 0.01
    assert pepperstone_result["p99_dd"] < 0.05


@requires_pepperstone
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
        "bust_daily_rate", "bust_static_rate",
        "bust_inactivity_rate", "horizon_cap_rate",
        "n_bdays", "n_blocks", "median_days_to_pass",
    ):
        assert serial[key] == parallel[key], (
            f"divergence at {key}: serial={serial[key]!r} parallel={parallel[key]!r}"
        )


# ── Rule 0-T compliance — direct _simulate_path call against constructed path ─

def test_simulate_path_direct_call_at_daily_loss_boundary():
    """Rule 0-T: exercise the inner FP comparison directly via _simulate_path.

    Aggregator-level tests (test_pepperstone_anchor etc.) call
    `compute_default_config` which loops _simulate_path over thousands of
    bootstrap paths, but no individual path is constructed to test the
    boundary FP comparison. Without this direct-call test, a future fix
    to the comparison could pass aggregator-level tests by coincidence —
    the PR #60 trap.

    Construction: single-day path where the realized P&L lands one ULP
    above DAILY_LOSS_PCT (-5%) in raw float64 — i.e., raw FP comparison
    `pnl / STARTING_EQUITY <= DAILY_LOSS_PCT` is FALSE. Post-fix
    `round(..., 6)` collapses ULP noise and the comparison fires, busting
    the simulation as `bust_daily` on day 1.

    Pre-fix: this path would NOT bust (raw FP comparison fails to fire),
    and the rest of the path is zeros, so outcome would be "horizon_cap"
    (under FXIFY-correct semantics) — but if inactivity counter trips at
    INACTIVITY_LIMIT, it would be "bust_inactivity" first. Either way it
    is NOT "bust_daily". Post-fix: outcome is "bust_daily" on day 1.

    Q-MCFP-1 §2.7 Rule 0-T compliance evidence.
    """
    n_strats = len(STRATS)
    # Horizon must be large enough to exercise the bust-on-day-1 path, but small
    # enough to keep the test fast. INACTIVITY_LIMIT + 1 is sufficient.
    horizon = INACTIVITY_LIMIT + 1

    # Path[0]: realize a loss whose pnl/S lands one ULP above -0.05 in raw FP.
    # Allocate the entire loss to one strategy (any will do); rest get 0.
    pnl_total = math.nextafter(-10000.0, 0.0)  # = -9999.999999999998
    path = np.zeros((horizon, n_strats))
    path[0, 0] = pnl_total

    # Pre-flight invariants: confirm the path actually exercises the boundary.
    raw_ratio = pnl_total / STARTING_EQUITY
    assert raw_ratio > DAILY_LOSS_PCT, (
        f"Construction invariant: raw FP must land above -0.05 (less negative); "
        f"got pnl_total={pnl_total!r}, ratio={raw_ratio!r}"
    )
    assert round(raw_ratio, 6) <= DAILY_LOSS_PCT, (
        f"Construction invariant: round6 must collapse to -0.05 and fire; "
        f"got round6={round(raw_ratio, 6)!r}"
    )

    # Run _simulate_path directly (NOT through compute_default_config).
    outcome, day, max_dd, culprit = _simulate_path(
        path, dd_trigger=DD_TRIGGER, dd_scale=DD_SCALE, horizon=horizon
    )

    # Post-fix expectation: the round6'd comparison fires on day 1, bust_daily.
    # Pre-fix expectation: would have been "timeout" (raw comparison silent,
    # rest of path is zeros, no profit, no static DD breach).
    assert outcome == "bust_daily", (
        f"post-fix _simulate_path must declare bust_daily on day 1 for the "
        f"ULP-above-DAILY_LOSS_PCT path; got outcome={outcome!r}, day={day}"
    )
    assert day == 1, (
        f"bust must occur on day 1 (when the loss is realized); got day={day}"
    )
    assert culprit == 0, (
        f"culprit strat index must be the strategy that took the loss; got {culprit}"
    )
