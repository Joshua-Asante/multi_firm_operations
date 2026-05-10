# ADR: dd_protection ULP-precision rounding at the trigger comparison

**Date:** 2026-05-10
**Status:** Accepted (with documented downstream cascade)
**Scope:** `dd_protection.py` (line 92), new `tests/test_dd_protection.py`
**Bound to:** [2026-05-08-dd-trigger-c2-relock](2026-05-08-dd-trigger-c2-relock.md) — precision-correctness companion. The C2 lock binds the `0.015 / 0.40×` threshold; this ADR binds how that threshold is compared.

**Ratification note (2026-05-10):** Accepted on the strength of the asymmetric-error-costs reading (account-loss-class miss-fire vs opportunity-cost early-fire). The empirical 47.4% pre-fix miss rate **inverts the brief's framing** — the C2 calibration substrate (anchor 98.09 / 0.36 / 4.73, 2026-05-08 relock) is now known to have systematically under-fired the risk control. Direction of MC drift is asymmetric: post-fix bust rate likely *higher*, pass rate likely *lower*. Issue [#55](https://github.com/Joshua-Asante/multi_firm_operations/issues/55) is **P0** and is the falsifier on whether the C2 lock itself survives. The 0.5pp tolerance from the original brief is provisional; the MC re-run spawn brief reframes it explicitly. The 2026-05-08 bust attribution (striker 44.4 / aegis 24.1 / G 21.3 / NAS 10.2) was computed on the buggy comparison; if the attribution shape changes post-fix, the relock decision itself is up for review (separate ADR if drift confirms).

**Post-merge update (2026-05-10, ~14:36Z):** `tests/test_mc_anchors.py` verification on post-fix main showed C2 anchor (98.09 / 0.36 / 4.73) and OANDA anchor (96.23 / 0.69 / 4.91) hold at `abs=1e-4` tolerance — 50× tighter than the brief's proposed 0.5pp. Parent's escalation of [#55](https://github.com/Joshua-Asante/multi_firm_operations/issues/55) to P0 was based on overweighting the 47.4% boundary-exact mis-fire rate without first checking whether that magnitude translates through the MC impact path. It does not — boundary-exact cases are rare per evaluation step in continuous trajectories, and pre-fix `dd_protection` effectively fired one bar late rather than missing entirely. Issue [#55](https://github.com/Joshua-Asante/multi_firm_operations/issues/55) downgraded to P3; remaining scope is supplementary metric verification (bust attribution shape, median days-to-pass, p50/p95 DD, bust-type split) folded into next hygiene pass. The 2026-05-08 C2 relock decision stands.

**See also:** `docs/adr/2026-05-10-mc-c2-anchor-ratification.md` documents the import-topology reason the C2 anchor was structurally insulated from this fix. The post-merge addendum above records the empirical reproduction (Δ = 0.00 pp); the standalone ADR records the structural reason future PR authors should reference during §0 reads to either domain.

This addendum is additive to the original ratification note (2026-05-10, pre-merge). Editing in place would lose the audit trail of the parent's reasoning *before* the impact-path verification — that escalation logic and the lesson it embeds (overweight boundary-exact magnitude → check impact path → downgrade) is itself the load-bearing artifact, not the corrected verdict alone.

## Context

`dd_protection.calculate_protection` decides whether the locked C2 risk control fires by computing `dd_from_peak = (peak - equity) / peak` (line 89) and comparing `dd_from_peak >= DD_TRIGGER` where `DD_TRIGGER = 0.015` (line 90). The comparison uses raw IEEE 754 float64.

At the trigger boundary, the line-89 arithmetic can land below the true rational answer by one or more ULPs (~10⁻¹⁶) for the same logical drawdown, depending on the (peak, equity) magnitudes that produced it. The defect was surfaced during `fxify_rule_validator` authoring on 2026-05-09 (PR [#52](https://github.com/Joshua-Asante/multi_firm_operations/pull/52)) and deferred for separate ADR per the asymmetry-of-error-costs lesson.

**Why the existing MVD self-check did not catch this.** The boundary self-check at lines 130-148 uses `epsilon = 0.0001` — three orders of magnitude above ULP. The ULP-scale boundary noise documented here lives twelve orders of magnitude below that detector. The existing self-check pins coarse spec drift; it cannot see precision drift at the float64 floor.

**Empirical magnitude.** A 1000-trial sweep across three arithmetic paths constructing true-1.5%-drawdown (peak, equity) pairs shows:

```
Pre-fix MISSES (raw FP < DD_TRIGGER, true dd = 1.5%): 474 / 1000 (47.4%)
Post-fix MISSES (round6 < DD_TRIGGER):                 0 / 1000 (0.0%)
Asymmetry guard (true dd = 1.49%, post-fix):           0 / 500 over-fires (0.0%)
```

This is materially larger than the brief's "1 ULP, occasional" framing. ~Half of the realistic (peak, equity) configurations representing a true 1.5% drawdown produce a sub-trigger float result without rounding. Synthetic clean-ratio test pairs (peak=1000 / equity=985 etc.) all happen to round-to-nearest in the favorable direction; non-clean pairs typical of live broker fills do not.

**Live-binding stakes.** `dd_protection.py` is the locked C2 risk control on the 1.5% / 0.40× tier (relocked 2026-05-08, anchor 98.09% pass / 0.36% bust / p99 DD 4.73%). A miss-fire under this defect is an account-loss-class error, not a logging-class one. The fix is forward-looking; historical re-evaluation is filed as a deferred follow-up.

**Existing precedent in this very file.** Line 303 already applies `round(result["dd_from_peak"], 6)` — for state logging only, not for the trigger comparison. The fix extends a precision treatment that already lives in the file from telemetry to decision logic. It does not introduce a new convention.

## Decision

Add `round(dd_from_peak, 6)` to the LHS of the trigger comparison at line 90:

```python
# Before
dd_triggered = dd_from_peak >= DD_TRIGGER

# After
dd_triggered = round(dd_from_peak, 6) >= DD_TRIGGER
```

The semantic comparison (`>=`) is unchanged. The conservative-of-trader inclusive-at-boundary reading from the validator's lock (`equity <= floor` for breach) is preserved.

### Asymmetry of error costs

The validator's PR #52 introduced the inclusive-at-boundary reading on the explicit asymmetric-error-costs ground (test [`test_2phase_faq_example_inclusive_interpretation`](../../tests/test_fxify_rule_validator.py:181) — *"asymmetric error costs justify the conservative-of-trader reading"*). The same reasoning applies one layer earlier here, on the precision dimension:

| Direction | Mechanism | Worst case | Recoverable? |
|---|---|---|---|
| Round (post-fix) | A drawdown one micro-ulp below 0.015 fires | `DD_SCALE` flag fractions of a percent earlier than spec literally requires | Yes — sized-down trades; opportunity cost only |
| Don't round (pre-fix) | A drawdown computed at one ULP below 0.015 silently passes | Risk control fails to fire on a true 1.5% drawdown | **No** — uncapped position size on a portfolio already at the C2 trigger |

The post-fix worst case is bounded and recoverable. The pre-fix worst case is unbounded at the account level. Conservative-of-trader picks rounding.

### Why 6 decimals (vs 2 dp money-math precedent vs Decimal)

- **Validator at 2 dp** is correct for money math: `floor`, `target`, `equity` all live at the cent scale, and `round(x, 2)` matches the natural quantum of the variable.
- **`dd_from_peak` is a ratio**, not money. It has no cent quantum. The natural fineness is the smallest drawdown distinction the trader cares about — empirically, no DD policy resolves below 1 bp (10⁻⁴). Rounding finer than 1 bp is sufficient.
- **6 dp = ~10⁻⁶ = micro-percent precision.** Eight orders of magnitude above float64 ULP at 0.015. Two orders of magnitude finer than any DD policy. Sufficient to collapse ULP noise without affecting any decision the trader could meaningfully care about.
- **Already in the file.** Line 303's state-log treatment is exactly `round(result["dd_from_peak"], 6)`. Uniformity is a virtue.
- **Decimal would change the type of every value flowing through dd_protection**, breaking MC throughput. Out of scope. Future ADR if 6 dp is later found insufficient.

## Consequences

- **Historical `dd_protection_state.json`** may contain logged events where the fire-or-not decision could flip under the rounded comparison. Re-evaluation is deferred — see follow-up issue [#56](https://github.com/Joshua-Asante/multi_firm_operations/issues/56).
- **C2 calibration anchor stability.** `portfolio_mc.py` shares the same comparison logic. Post-fix MC re-run is required to confirm the 98.09% / 0.36% / 4.73% anchor survives. Out of scope this PR; see follow-up issue [#55](https://github.com/Joshua-Asante/multi_firm_operations/issues/55). Tolerance: 0.5 pp on pass-rate; if drift exceeds, C2 lock is up for re-evaluation in a separate ADR.
- **MVD self-check epsilon (`1e-4`) unchanged.** Whether to tighten it post-fix is a separate methodology question — see follow-up issue [#57](https://github.com/Joshua-Asante/multi_firm_operations/issues/57).
- **Other risk-control comparison sites** (`accounts.py`, etc.) may carry the same defect pattern. Audit deferred — see follow-up issue [#54](https://github.com/Joshua-Asante/multi_firm_operations/issues/54).
- **Reverts:** none. ULP noise is non-deterministic; no specific historical event needs re-running before merge.

### Falsifier capture (paste of §4 protocol output)

```
N = 1000
Pre-fix MISSES (raw FP < DD_TRIGGER, true dd = 1.5%): 474 / 1000 (47.4%)
Post-fix MISSES (round6 < DD_TRIGGER): 0 / 1000 (0.0%)

Asymmetry guard (true dd = 1.49%): post-fix over-fires 0 / 500 (0.0%)
```

Construction: 1000 (peak, equity) pairs across three arithmetic paths (multiplicative diff, subtractive via reciprocal, cents-aligned broker-realistic), all targeting true rational dd = 0.015. Asymmetry guard: 500 pairs targeting true rational dd = 0.0149. Run via `python` one-shot; not added to the test suite (the named boundary tests in `tests/test_dd_protection.py` are the standing gates).

### Follow-up issues (deferred)

Filed via `gh issue create` 2026-05-10. Cross-referenced inline:

1. [**#54**](https://github.com/Joshua-Asante/multi_firm_operations/issues/54) — `accounts.py` ULP-precision audit. Sweep other risk-control comparison sites; disposition Pre-Q if ≥ 3 instances.
2. [**#55**](https://github.com/Joshua-Asante/multi_firm_operations/issues/55) — Post-fix MC re-run. Verify C2 anchor (98.09% / 0.36% / 4.73%) stability; tolerance 0.5 pp on pass-rate. **The load-bearing falsifier on this ADR's "the calibration anchor survives" claim.**
3. [**#56**](https://github.com/Joshua-Asante/multi_firm_operations/issues/56) — Historical `dd_protection_state.json` re-evaluation. Flag any fire-or-not flips under rounded comparison.
4. [**#57**](https://github.com/Joshua-Asante/multi_firm_operations/issues/57) — MVD self-check epsilon tightening. Post-fix the boundary check is precision-stable; should `1e-4` be tightened?

## Alternatives considered

1. **Loosen the trigger** (`dd_from_peak >= DD_TRIGGER - epsilon`). Rejected — arbitrary semantic change, not a precision fix. Round-before-compare collapses ULP noise without altering the comparison's meaning.
2. **Switch `dd_from_peak` to `Decimal`.** Rejected — type cascade through dd_protection, MC throughput regression, validator chose `float + round` for the same reason on PR #52.
3. **Tighten the MVD self-check epsilon to ULP scale.** Rejected as part of *this* fix — the self-check role is sanity-bounds against spec drift, not float-precision detection. Whether to tighten is a separate methodology question (issue #4).
4. **Add prophylactic rounding at every comparison in the file.** Rejected — line 90 is the only `dd_from_peak` decision site; each rounding site is a behavior change requiring its own justification. Pattern: surface other sites in a deliberate audit, not a "while I'm in here" sweep.
