# Q-DDP-1 Step 1 — Rule 0 reconciliation

**Date:** 2026-05-06
**Author:** Claude Code (auto mode)
**Purpose:** verbatim summary of production constants and semantics; match/mismatch table against brief's chat-based model; Joshua's resolutions on the surfaced gaps.

---

## Production source — verbatim

### `dd_protection.py` — constants

[dd_protection.py:40-41](../../../dd_protection.py:40):
```python
DD_TRIGGER = 0.010            # 1.0% DD from peak triggers scaling
DD_SCALE = 0.40               # multiply risk by 0.40x when triggered
```

### `dd_protection.py` — `calculate_protection`

[dd_protection.py:76-96](../../../dd_protection.py:76):
```python
def calculate_protection(equity: float, peak: float) -> dict:
    """Determine active multiplier and scaled risk levels."""
    dd_from_peak = (peak - equity) / peak if equity < peak else 0.0
    dd_triggered = dd_from_peak >= DD_TRIGGER

    if dd_triggered:
        multiplier = DD_SCALE
        rule = f"DD PROTECTION (DD {dd_from_peak:.2%} ≥ {DD_TRIGGER:.1%})"
    else:
        multiplier = 1.0
        rule = "NONE — full risk"

    scaled_risk = {k: v * multiplier for k, v in BASE_RISK.items()}
    ...
```

Live tool returns scaled `risk_pct` for the user to type into TradingView strategy inputs at the start of the trading session. Sticks at the scaled value until the user runs the script again with a new equity reading (typically next day). Implicit release: `dd_triggered = False` once `dd_from_peak < DD_TRIGGER`, i.e. equity ≥ peak × (1 − DD_TRIGGER).

### `dd_protection.py` — MVD spec pin (raises at import on drift)

[dd_protection.py:145-154](../../../dd_protection.py:145):
```python
if DD_TRIGGER != 0.010:
    raise AssertionError(
        f"MVD spec drift: DD_TRIGGER moved from locked 0.010 to {DD_TRIGGER}. "
        f"Re-run portfolio_mc and update the pin literal in the same commit."
    )
if DD_SCALE != 0.40:
    raise AssertionError(
        f"MVD spec drift: DD_SCALE moved from locked 0.40 to {DD_SCALE}. "
        f"Re-run portfolio_mc and update the pin literal in the same commit."
    )
```

This means the live tool cannot test alternate constants — sweep MC must override at call time via [`portfolio_mc.py`](../../../portfolio_mc.py)'s `--dd-trigger` and `--dd-scale` CLI flags or via `compute_default_config(...)` programmatic entry.

### `portfolio_mc.py` — MC sim semantics

[portfolio_mc.py:187-219](../../../portfolio_mc.py:187):
```python
def _simulate_path(path: np.ndarray, dd_trigger: float, dd_scale: float,
                   horizon: int) -> Tuple[str, int, float, int | None]:
    eq = peak = float(STARTING_EQUITY)
    trade_days = 0
    max_dd = 0.0

    for day in range(horizon):
        dd_from_peak = (eq - peak) / peak if peak > 0 else 0.0
        scale = dd_scale if dd_from_peak <= -dd_trigger else 1.0
        strat_pnls = path[day] * scale
        pnl = float(strat_pnls.sum())
        eq_new = eq + pnl

        if pnl / STARTING_EQUITY <= DAILY_LOSS_PCT:
            return "bust_daily", day + 1, max_dd, int(np.argmin(strat_pnls))
        if (eq_new - STARTING_EQUITY) / STARTING_EQUITY <= STATIC_DD_PCT:
            return "bust_static", day + 1, max_dd, int(np.argmin(strat_pnls))

        eq = eq_new
        if eq > peak:
            peak = eq
        ...
```

Per-day evaluation. Trigger fires when `dd_from_peak <= -dd_trigger` (equivalently: equity is more than `dd_trigger` below peak). Scale released the moment `dd_from_peak > -dd_trigger`, i.e. equity recovers to within `dd_trigger` of peak. Multiplier applied to each strategy's day PnL pre-aggregation. Peak is running maximum of equity.

---

## Match/mismatch table

| Brief's chat-based model | Production reality | Match? |
|---|---|---|
| "day-start check" | Per-day eval in MC ([portfolio_mc.py:195-197](../../../portfolio_mc.py:195)); per-CLI-call in live tool ([dd_protection.py:76](../../../dd_protection.py:76)). MC and live tool both evaluate trigger before applying day's PnL/risk. | ✅ |
| "entry-tagged scaling" | MC: scales **day-aggregate** per-strategy PnL ([portfolio_mc.py:198](../../../portfolio_mc.py:198)). Live tool: returns scaled `risk_pct` user types into TV — applies to all subsequent entries until user updates equity. **Equivalent in expectation for i.i.d. daily PnL but not strictly entry-tagged in either path.** | ⚠️ partial |
| "≥peak release" | Both MC and live tool release scale=1.0× when `dd_from_peak < DD_TRIGGER`, i.e. equity ≥ peak × (1 − DD_TRIGGER) — about $2,000 short of peak at $200K base. **NOT** when equity ≥ peak. The dd_protection.py docstring at line 17 ("Clears automatically when equity returns to peak") is misleading — production releases on partial recovery. | ❌ mismatch |
| "position-size multiplier" | MC: multiplicative on day's per-strategy PnL ≈ multiplicative on position size at first order. Live tool: multiplicative on `risk_pct` → TV converts to lots. | ✅ |

---

## Joshua's resolutions on the surfaced gaps

### Pre-A — Drag re-baseline (Joshua: "Halt and re-baseline drag first")

Executed. Outcome: corrected drag is **−$126,013 (−24.4% of unprotected PnL over 28-month sub-window)**. Chat-based number was **−$149,277 (24%)**. Drag percentage essentially identical; drag dollars 18% smaller under production semantics. Engagement-window narrative in chat-based prose was wrong (52% of calendar days assumed long ≥peak release windows; production releases more often and is ~half the active fraction). The Inquire-phase trigger survives — drag remains material at >>10% of unprotected PnL.

Full audit: [drag_rebaseline.md](drag_rebaseline.md).

### Pre-B — C0 anchor reconciliation (Joshua: "Use brief's 98.13 numbers (re-fetch source)")

Executed. Outcome: **98.13/0.22/4.49 is obsolete** — it was the pre-reconcile 4-strategy anchor (commit `4c65d29`, against the 209-trade Guardian export with 8 phantom v5.5 signals) that lived as canonical for ~4 hours on 2026-05-05 before being superseded by 97.88/0.22/4.55 (commit `09206eb`) the same evening after the Guardian re-export reconcile.

**Resolution adopted:** anchor sweep against production-pinned **97.88/0.22/4.55**, lower the brief's pass-rate floor to **97.5%** to preserve the brief author's intended ~0.2pp safety margin below C0. With the 0.5pp "no marginal-pass winners" margin requirement on top, effective binding floor for a LOCK CANDIDATE is ~98.0% — meaning a relaxation can only be a lock candidate if it strictly improves pass-rate above C0.

Full audit: [anchor_reconciliation.md](anchor_reconciliation.md).

### Sim count (Joshua: "10K per seed, existing default = 30K total")

`SIMS_PER_SEED = 10_000`, `SEEDS = (42, 123, 2026)` in [portfolio_mc.py:43-44](../../../portfolio_mc.py:43). 30K total per config, no override. Matches the test-pinned C0 anchor.

### `rule1_gate.py` (Joshua: "Skip; document if it would have fired")

File does not exist in repo. Sweep stays at full-panel resolution. `recommendation.md` will note whether partition-specific dominance was observed.

---

## Statement of internal consistency

**Steps 2-5 of this brief use production semantics throughout** — they invoke the same `_simulate_path` code as the canonical 2026-05-05 lock MC. The chat-based model was the unreliable artefact (mismatch on release semantics), but the harness itself is internally consistent and the sweep results will be directly comparable to the C0 anchor pinned in [tests/test_mc_anchors.py](../../../tests/test_mc_anchors.py).

The Rule 0 mismatch (chat-based model assumed `≥peak release`, production releases on partial recovery) is recorded here for completeness but does **not** affect the sweep mechanics. It only affects how the Inquire-phase trigger should be described going forward — the corrected production-walk drag (−$126K, 24.4%) supersedes the chat-based −$149K, and the engagement-window narrative (17 windows / 34.4% of bdays) supersedes the chat-based "14 windows / 52% of calendar days".
