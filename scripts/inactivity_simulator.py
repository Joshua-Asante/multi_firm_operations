"""FXIFY-correct portfolio MC simulator (Q-MCTO-1 Phase 1 work product).

Replaces `portfolio_mc._simulate_path`'s 150-bday horizon-runout timeout with
the FXIFY-correct 60-bday inactivity bust rule documented at
`firm_rules.py:14`. A 1500-bday safety ceiling exists for runtime tractability
but should empirically never fire (bootstrap of 5-day week-blocks makes 60+
consecutive all-zero days vanishingly rare).

Q-MCTO-1 STATUS: this module is Phase 1 evidence-gathering only. It is NOT
production code, does NOT replace `portfolio_mc.py`, and is NOT consumed by
`tests/test_mc_anchors.py`. Adoption is gated by Phase 2 regime-robustness
clearance and a separate ADR per Q-MCTO-1 §5 forbidden moves.

Differences from `portfolio_mc._simulate_path`:

  | Outcome           | portfolio_mc.py (current)              | this module (FXIFY-correct)            |
  |-------------------|----------------------------------------|----------------------------------------|
  | pass              | eq >= $210K AND trade_days >= 5        | same                                   |
  | bust_daily        | day pnl <= -5% of $200K                | same                                   |
  | bust_static       | eq - $200K <= -5% of $200K             | same                                   |
  | bust_inactivity   | (not modeled)                          | 60 consecutive idle bdays              |
  | timeout           | day == 150 (horizon cap)               | (removed)                              |
  | horizon_cap       | (not modeled)                          | day == 1500 (safety; should be ~0)     |

An "idle" bday is one where total cross-strategy pnl is 0 AND no individual
strategy had a non-zero pnl. The check is symmetric: both conditions must hold,
guarding against the false-idle case where two strategies have offsetting
non-zero pnls.

Determinism: identical to portfolio_mc for fixed SEEDS = (42, 123, 2026).
Bootstrap RNG is `np.random.default_rng(seed)` per seed; sample-block indices
are produced before the simulation walk; the walk itself is deterministic given
the sampled path.
"""

from __future__ import annotations
from typing import Dict, Tuple
import numpy as np

# ── Constants (mirror portfolio_mc.py where applicable) ──────────────────
STARTING_EQUITY = 200_000
PROFIT_TARGET = 210_000
DAILY_LOSS_PCT = -0.05
STATIC_DD_PCT = -0.05
MIN_TRADING_DAYS = 5

INACTIVITY_LIMIT = 60      # FXIFY: 60 consecutive idle bdays terminates challenge
HORIZON_CAP = 1500         # safety; should empirically never fire under week-block bootstrap

SIMS_PER_SEED = 10_000
SEEDS = (42, 123, 2026)


def simulate_path(
    path: np.ndarray,
    dd_trigger: float,
    dd_scale: float,
) -> Tuple[str, int, float, int | None]:
    """Walk a (n_days, n_strats) path with FXIFY-correct timeout semantics.

    Returns (outcome, day_terminated, max_dd, culprit_strat_idx).

    Outcomes:
      - "pass": equity >= PROFIT_TARGET with trade_days >= MIN_TRADING_DAYS
      - "bust_daily": single-day pnl <= -5% of starting equity
      - "bust_static": equity - starting <= -5% of starting equity
      - "bust_inactivity": INACTIVITY_LIMIT consecutive all-zero bdays
      - "horizon_cap": HORIZON_CAP reached (safety; should be ~0)

    culprit is the strategy index for daily/static busts (argmin of strat_pnls);
    None for pass / inactivity / horizon_cap. Inactivity is structurally
    "no one traded" — no single-strategy attribution applies.
    """
    eq = peak = float(STARTING_EQUITY)
    trade_days = 0
    consecutive_idle = 0
    max_dd = 0.0
    horizon = len(path)

    for day in range(horizon):
        dd_from_peak = (eq - peak) / peak if peak > 0 else 0.0
        # ULP-precision rounding before threshold compare (Q-MCFP-1 precedent)
        scale = dd_scale if round(dd_from_peak, 6) <= -dd_trigger else 1.0
        strat_pnls = path[day] * scale
        pnl = float(strat_pnls.sum())
        eq_new = eq + pnl

        # Bust checks — identical to portfolio_mc._simulate_path
        if round(pnl / STARTING_EQUITY, 6) <= DAILY_LOSS_PCT:
            return "bust_daily", day + 1, max_dd, int(np.argmin(strat_pnls))
        if round((eq_new - STARTING_EQUITY) / STARTING_EQUITY, 6) <= STATIC_DD_PCT:
            return "bust_static", day + 1, max_dd, int(np.argmin(strat_pnls))

        # Inactivity tracking — both conditions guard against false-idle
        # (offsetting non-zero pnls summing to 0 is NOT idle for inactivity purposes).
        is_idle = (pnl == 0.0) and (not np.any(strat_pnls != 0.0))
        if is_idle:
            consecutive_idle += 1
        else:
            consecutive_idle = 0
        if consecutive_idle >= INACTIVITY_LIMIT:
            return "bust_inactivity", day + 1, max_dd, None

        eq = eq_new
        if eq > peak:
            peak = eq
        dd_now = (peak - eq) / peak if peak > 0 else 0.0
        if dd_now > max_dd:
            max_dd = dd_now
        if pnl != 0:
            trade_days += 1

        if round(eq, 2) >= PROFIT_TARGET and trade_days >= MIN_TRADING_DAYS:
            return "pass", day + 1, max_dd, None

    return "horizon_cap", horizon, max_dd, None


def run_seed(
    seed: int,
    n_sims: int,
    blocks: np.ndarray,
    dd_trigger: float,
    dd_scale: float,
    strats: Tuple[str, ...],
) -> Dict:
    """Run n_sims bootstrap paths for one seed."""
    rng = np.random.default_rng(seed)
    n_blocks = len(blocks)
    blocks_per_sim = (HORIZON_CAP + 4) // 5

    outcomes = {"pass": 0, "bust_daily": 0, "bust_static": 0,
                "bust_inactivity": 0, "horizon_cap": 0}
    days_to_pass: list[int] = []
    days_to_inactivity: list[int] = []
    max_dds: list[float] = []
    bust_attrib = {s: 0 for s in strats}

    for _ in range(n_sims):
        idx = rng.integers(0, n_blocks, blocks_per_sim)
        path = np.concatenate([blocks[i] for i in idx])[:HORIZON_CAP]

        outcome, day, max_dd, culprit = simulate_path(path, dd_trigger, dd_scale)
        outcomes[outcome] += 1
        max_dds.append(max_dd)
        if outcome == "pass":
            days_to_pass.append(day)
        elif outcome == "bust_inactivity":
            days_to_inactivity.append(day)
        elif outcome in ("bust_daily", "bust_static") and culprit is not None:
            bust_attrib[strats[culprit]] += 1

    return {
        "outcomes": outcomes,
        "days_to_pass": days_to_pass,
        "days_to_inactivity": days_to_inactivity,
        "max_dds": max_dds,
        "bust_attribution": bust_attrib,
    }
