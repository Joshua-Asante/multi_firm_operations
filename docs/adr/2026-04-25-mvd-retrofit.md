# ADR: MVD retrofit — portfolio_mc, dd_protection

**Date:** 2026-04-25

## Status

Accepted — 2026-04-25.
Implements the retrofit pass scoped in [`docs/adr/2026-04-24-mvd-discipline.md`](2026-04-24-mvd-discipline.md) (Consequences → Cost → "One-time retrofit"). Follows successful sanity gate ([PR #2](https://github.com/Joshua-Asante/prop_firm_pipeline/pull/2): all 9 helpers exercised against canonical Aegis v4.3 panel, all 5 reference numbers reproduced).

## Context

The MVD framework landed 2026-04-24 (ADR + methodology + library + templates) but was not yet wired into production code. Until the retrofit, MVD existed as docs and helpers, not enforced practice — exactly the failure mode the discipline exists to prevent (framework available, current risk drifts un-covered).

Two production sites cross the live capital boundary today:

1. **`portfolio_mc.py`** — produces pass/bust probabilities and DD distributions that drive lock decisions and allocation. Has a known silent-fallback in `implied_1r` (audit instance #1, recorded in user memory `portfolio_mc_1r_fallback_trap.md`): when fewer than 5 full-stop losses exist, falls back to median and returns it without flag. Documented as "can swing MC by ~10pp."
2. **`dd_protection.py`** — produces the live risk-multiplier consumed by every TradingView strategy. Constants (`DD_TRIGGER = 0.010`, `DD_SCALE = 0.40`) are the rule. No self-validation that the rule actually triggers when crossed.

Plus a finding from the dry-run gate ([PR #2](https://github.com/Joshua-Asante/prop_firm_pipeline/pull/2)): "DD" without a qualifier is a label ambiguity (intra-trade vs trade-close). Identity-class instance, adds to the audit table.

## Decision

Retrofit both production files using helpers from [`lib/mvd.py`](../../lib/mvd.py), and append the DD-label finding to the methodology audit table.

### `portfolio_mc.py` changes

**`implied_1r` returns a fallback flag.** Signature changes from `-> float` to `-> tuple[float, bool]`. Guardian's median path is by design (not a fallback) → returns `False`. Striker/Aegis median path on `len(full_stops) < 5` → returns `True`. Caller in `build_daily_panel` records the flag in `scale_info`. `mode_default` aggregates and asserts:

```python
total_fallbacks = sum(1 for info in scale_info.values() if info["fell_back"])
assert_no_fallback(total_fallbacks, label="portfolio_mc implied_1r (Striker/Aegis full-stop cohort)")
```

For canonical config (Pepperstone 52mo with current ALLOCATIONS), this assertion must pass. For exploratory configs that legitimately have sparse stops, the assertion fails loudly — at which point the operator either (a) provides more data, or (b) hardens `implied_1r` for the new regime, then promotes the result.

**`load_trades` validates input panels.** Cardinality + window assertions on each CSV:

```python
assert_min_rows(len(df), 100, label=f"MC input panel {path.name}")
assert_window(min(exit_dates), max(exit_dates), expected_min_days=4*365,
              label=f"MC input panel {path.name}", tolerance_days=60)
```

Catches the OANDA short-fetch class (audit instance #2) at the consuming site. 100 rows is a deliberately low floor — the panel files are entry+exit pairs, so 100 rows ≈ 50 trades, well below any plausible 4yr canonical panel.

### `dd_protection.py` changes

**Module-load self-check.** A `_validate_protection_rule()` function runs at import time. Constructs synthetic equity values just-below and just-above the trigger, calls `calculate_protection`, and asserts:

- `assert_guard_fired` on multiplier dropping below 1.0 when DD crosses threshold
- `assert_no_fallback` on multiplier remaining 1.0 when just under threshold (no spurious trigger)

If either fails, the module raises `AssertionError` at import — `portfolio_mc.py`, the CLI, anything that imports `dd_protection` cannot proceed. Catches: any future edit to `DD_TRIGGER`, `DD_SCALE`, or `calculate_protection` that breaks the rule. The validation is also a doctest-equivalent — anyone reading the module sees the rule's behavior in two test points.

### Audit table

Append row #10 to `docs/methodology/mvd.md`:

| # | Date | Instance | MVD | Family | Identity? |
|---|------|----------|-----|--------|-----------|
| 10 | 2026-04-25 | "DD" cited as 5.01% (intra-trade) vs 3.76% (trade-close) — same metric name, different measurements | Use qualified labels in `assert_reconciled` (e.g. `"DD_intra vs canonical"`, not `"DD"`) — discipline at call site | **Identity** | Y (broad) |

Update summary stats: `9 instances → 10`, `6/9 (67%) identity → 7/10 (70%)`, `6/9 single-line → 7/10 single-line`. Update the doc's bottom MVD-attest to match.

The original ADR (`2026-04-24-mvd-discipline.md`) is **not** updated — it freezes the decision context as of 2026-04-24 (9 instances at adoption time). The methodology doc is the live source per the update protocol.

## Consequences

### Cost (actual)

- One-time retrofit: ~2 hrs (came in under the ~3 hrs estimate from the original ADR; only two production files needed touching).
- Steady state: assertions are one-line additions; future calibration scripts pay the documented ~3–5 lines tax.

### What changes

- `portfolio_mc.py` invocation: silent-fallback case now raises. Existing canonical config (G/S/A on Pepperstone 52mo) is verified clean — the assertion will pass on the canonical run, fail on misconfigured runs.
- `dd_protection.py` import: any drift in `DD_TRIGGER` / `DD_SCALE` / `calculate_protection` body that breaks the rule fails loudly at import time.
- Methodology doc `docs/methodology/mvd.md`: audit table grows by one row (#10), summary stats update.

### What does not change

- No strategy parameters touched (Guardian v5.5, Striker v4.4, Aegis v4.3 still locked).
- No allocation changes.
- No DD protection rule semantics — only adds self-validation that the existing rule still works.
- No retroactive sweep of historical artifacts (per the no-archaeology rule).

### Known risks

- **`implied_1r` shape change** is a small breaking change for any caller. Only one caller exists in-tree (`build_daily_panel`); updated in same commit. Out-of-tree callers (ad-hoc notebooks) would break — acceptable, the breakage is exactly the kind of "you should re-attest your numbers" surfacing the discipline calls for.
- **Self-check overhead at dd_protection import.** Two `calculate_protection` calls; ~µs. Negligible.

## References

- Framework ADR: [`docs/adr/2026-04-24-mvd-discipline.md`](2026-04-24-mvd-discipline.md)
- Methodology: [`docs/methodology/mvd.md`](../methodology/mvd.md) (with audit row #10 in this PR)
- Library: [`lib/mvd.py`](../../lib/mvd.py)
- Sanity gate: [PR #2](https://github.com/Joshua-Asante/prop_firm_pipeline/pull/2)
- 1R fallback memory entry (precursor): user memory `portfolio_mc_1r_fallback_trap.md`
