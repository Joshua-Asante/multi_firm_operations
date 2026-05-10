# Q-MCFP-1 — Closure

**Date:** 2026-05-10
**Parent:** [Q-MCFP-1 recommendation](recommendation.md)
**Spawn:** Q-MCFP-1-CC (this session)
**Branch:** `feat/q-mcfp-1-mc-precision-fix`
**Bound to:** [ADR 2026-05-08 dd-trigger-c2-relock](../../adr/2026-05-08-dd-trigger-c2-relock.md), [ADR 2026-05-10 dd-protection-ulp-rounding](../../adr/2026-05-10-dd-protection-ulp-rounding.md)

## TL;DR

Pre-Q's load-bearing claim — *C2 anchor (98.09 / 0.36 / 4.73) holds under fixed MC simulation* — **empirically confirmed**. ADR 2026-05-08 stands. The 47.4% boundary-exact mis-fire rate from PR #53 §6 was theoretical; it does not translate through the MC impact path because real trajectories are continuous and boundary-exact cases are rare per evaluation step. PR #53's fix was prophylactic on both the simulation path (Run A identical to baseline) and the live operational path (no historical decisions made under buggy comparison; the equity-log CLI was not state-tracking).

---

## H1 — Does the C2 anchor hold under fixed sim?

**Disposition:** **RESOLVED.** Anchor stable; ADR 2026-05-08 stands.

### Evidence

- Run A (canonical seeds 42/123/2026, post-fix): pass=98.09% / bust=0.36% / p99 DD=4.73% / median 22d / attribution striker 44.4 / aegis 24.1 / G 21.3 / NAS 10.2 — **identical to pre-fix baseline at all displayed precision**.
- Run B (fresh seeds 211/503/1009, post-fix): pass=98.02% / bust=0.34% / p99 DD=4.75% / median 22d / attribution striker 37.9 / aegis 28.2 / G 26.2 / NAS 7.8 — within seed noise of Run A; both clear C2 lock criteria (bust < 1%, p99 DD < 5%) with margin.
- `tests/test_mc_anchors.py::test_pepperstone_anchor` passes post-fix at the existing `abs=1e-4` tolerance.

### Interpretation note (parent's directive — preserve verbatim for future audit)

Run A and Run B measure different things, and the parent §7 attribution threshold (≤5pp/strategy) applies asymmetrically:

- **Run A measures fix-effect.** Canonical seeds, only the precision changed. If the fix moved the bust driver, this run shows it. Result: **zero movement at all displayed precision**. Attribution shifts: 0.0 / 0.0 / 0.0 / 0.0. The ≤5pp threshold is satisfied trivially.
- **Run B measures independence.** Fresh seeds AND precision changed. This run estimates path-noise variance, not fix-effect. Striker −6.5pp, G +4.9pp, aegis +4.1pp, NAS −2.4pp.
  - The −6.5pp striker shift is **path-driven seed noise, not fix-driven**, and is consistent with the 0.08% pass-rate sigma at 3 seeds × 10K sims. Bust attribution at this seed-density is a noisy estimator; ±5–7pp swings between independent triplets are expected.
  - Per parent §7's written justification: *"Attribution shifts >5pp would indicate the fix moved which strategy is the bust driver."* Run B's shifts are between independent seed triplets, not pre-vs-post-fix on identical seeds, so the threshold does not apply.

This interpretation is documented here so future audits do not re-litigate. The H1 disposition is decided by Run A's evidence (zero fix-effect drift); Run B is independence/robustness evidence (no anomalous behavior on a different seed slice).

### What this means for the 2026-05-08 ADR

ADR 2026-05-08-dd-trigger-c2-relock stands as authored. The relock decision was made on Run-A-equivalent evidence with the buggy comparison; post-fix Run A reproduces the same metrics. The bust-attribution signal that justified the override (striker 44.4 / aegis 24.1 / G 21.3 / NAS 10.2) is identical post-fix. No re-evaluation needed; no separate ADR required.

---

## H2 — Is `round(x, 6)` correct for ratio-vs-pct sites?

**Disposition:** **RESOLVED.** `round(x, 6)` confirmed correct for all four ratio-comparison sites (dd-pattern, daily-loss, static-DD).

### Evidence

`tests/test_mc_fp_boundaries.py` — 13 boundary tests, all passing. Three discriminating constructions demonstrate that:

1. **dd-pattern** (`dd_from_peak <= -dd_trigger`): `peak=133.33333, equity=131.33333005` produces `(equity − peak)/peak = -0.014999999999999916` in raw float64 (5 ULPs above −0.015). Raw FP fails to fire; `round(x, 6)` collapses to −0.015 and fires.
2. **daily-loss** (`pnl/STARTING_EQUITY <= DAILY_LOSS_PCT`): `pnl = math.nextafter(-10000.0, 0.0)` produces ratio `-0.04999999999999999` in raw float64. Raw FP fails to fire; `round(x, 6)` fires.
3. **static-DD** (`(eq_new − S)/S <= STATIC_DD_PCT`): `eq_new = math.nextafter(190_000.0, 200_000.0)` produces ratio `-0.04999999999999986`. Raw FP fails to fire; `round(x, 6)` fires.

Asymmetry guards confirm rounding does not over-fire on truly-below-threshold values (1.4% drawdown, 4.9% loss).

### Amendment 1 closure (sign-symmetry)

`test_dd_pattern_sign_symmetry_amendment_1`: `round(-0.01500001, 6) <= -0.015` and `round(0.01500001, 6) >= 0.015` produce identical fire-or-not at the boundary. Sign-symmetry between the MC sim's signed-form and `dd_protection`'s positive-form is mechanically confirmed. The §0.5 asymmetry observation is closed.

---

## H3 — Is `round(x, 2)` correct for dollar-vs-dollar sites?

**Disposition:** **RESOLVED.** `round(x, 2)` confirmed correct for both profit-target sites.

### Evidence

`TestH3ProfitTargetBoundary` (4 tests, all passing). Discriminating construction: `eq = 209_999.99999999` (1e-8 below `PROFIT_TARGET = 210_000.0`). Raw FP comparison `eq >= PROFIT_TARGET` returns False (sub-cent FP noise). Post-fix `round(eq, 2) = 210_000.0 >= 210_000.0` returns True. Asymmetry guard: `eq = $209_999.99` (one cent short) does NOT trigger pass — `round(eq, 2) = 209_999.99` correctly stays below threshold.

The cent-quantum precision matches the validator's precedent (`fxify_rule_validator.py` PR #52) and the broker's tracking granularity. Trader's experience: equity within 0.5 cents of target counts as target-met under broker's actual reporting. Conservative-of-trader on the early-pass dimension; opportunity-cost-bounded.

---

## H4 — What to do with `mc_explore.py`?

**Disposition:** **RESOLVED — DELETED.** No active runtime callers; speculative preservation rejected per The Algorithm.

### Evidence

`grep -rln "mc_explore\|simulate_path_with_curve" --include="*.py"` post-DELETE returned a single match: `archive/docs/methodology/archive/analysis/msee/archive/h1_community_matrix.py:49`. That file is quadruple-archived (under `archive/`), is not imported by any live code, and is broken-by-construction now (the `from mc_explore import (...)` line will fail). Live runtime callers: zero. Active doc references (REPO_MAP.md, docs/notion/repo_context.md, ADR 2026-05-08): three — flagged as residual hygiene in [Out-of-scope follow-ups](#out-of-scope-follow-ups).

### Per parent A3

> "Speculative preservation of unused capability is the opposite of The Algorithm. If a future analysis needs curve reconstruction, rebuild then from `_simulate_path` events."

DELETE removed 254 LOC of duplicate simulation logic. Defect-site count strictly decreased: 10 sites pre-Pre-Q → 6 sites post-Pre-Q (the 6 in `portfolio_mc.py` are the rounded forms; mc_explore's 4 are gone).

---

## H5 — Do historical `dd_protection_state.json` entries flip under post-fix logic?

**Disposition:** **RESOLVED-CLEAN-VACUOUS.** Joshua's option (ii): the equity-log CLI was never invoked, so the state file does not exist. No history to replay; vacuous closure.

### Evidence

`scripts/replay_state_h5.py` (staged for future re-run if state ever exists) returned exit code 2 with `BLOCKED: state file missing` on §2.6 first attempt. Searched locations: worktree root, main repo root. Both empty. The state file is created by `dd_protection.save_state()` on first equity-log invocation; the absence implies no equity logging occurred.

### What this means

PR #53's fix was **prophylactic on both layers**:
- The MC simulation path (Run A identical to baseline → no measurable historical impact under buggy comparison).
- The live operational path (CLI was not state-tracking → no historical fire-or-not decisions to retroactively flip).

The 47.4% boundary-noise rate from PR #53 §6 was a *theoretical* measurement on synthetic boundary-exact constructions. It was never realized in either path. The fix corrected the precision posture forward; nothing requires retroactive correction.

If Joshua begins using the equity-log CLI in the future, `scripts/replay_state_h5.py` is staged to re-run the H5 replay against any accumulated history.

---

## Methodology lesson capture

### Lesson #1 — Theoretical magnitude vs realized-distribution-density assessment

**Status:** Candidate (first firing). Graduates on next-instance-in-separate-context within 90 days (next eligible review: 2026-08-08).

**Statement:** *ULP-precision defect severity should be assessed against the realized-distribution density at the boundary, not the theoretical maximum mis-fire rate on synthetic boundary-exact constructions.*

**Anchor:** PR #53's §6 reported 47.4% pre-fix mis-fire on 1000 (peak, equity) pairs constructed *exactly at* dd = 0.015. Q-MCFP-1's empirical re-MC with the corrected simulation showed **zero measurable impact** at canonical seeds and within-seed-noise impact at fresh seeds. The 47.4% inflation factor of inferred severity (47.4% theoretical → 0% realized) is the load-bearing miss.

**Mechanism:** Real trajectories are continuous noisy paths. The probability of evaluating at the boundary in any given step is small. Pre-fix dd_protection effectively fired one bar later than spec (timing noise) rather than failing to fire entirely (substance loss). Across thousands of trajectories this washes out below the test-suite's 1e-4 tolerance.

**How to apply:** When authoring or reviewing a brief that escalates priority based on a theoretical mis-fire rate, the brief should also state — or commit to measuring — the *realized* mis-fire rate under the actual trajectory distribution. If the wash-out hypothesis is plausible (continuous trajectories, rare boundary-exact evaluation), the realized rate is the load-bearing number. The theoretical maximum is the upper bound; the realized rate is the right scale for severity assessment.

**Future audit hook:** If a similar precision-fix Pre-Q lands within 90 days and the same theoretical-vs-realized inflation is observed, this lesson graduates from candidate to load-bearing. If 90 days pass without a second instance, lesson stays candidate (real but not load-bearing yet) — re-evaluate at 2026-08-08.

### Rule 0-T (test-exercises-the-change verification)

**Status:** **Candidate (unchanged).**

The PR #60 incident (2026-05-10, ~14:30Z) was the first instance: aggregator-level test passed → "fix validated" without verifying the test's call graph included the changed code path. The Q-MCFP-1 spawn's in-the-moment recognition of the same trap pattern at §0.5 (75 minutes later, in the same session) is **not** a separate-context firing per parent's directive — same conversation, same author chain, same load-bearing artifact. Rule 0-T graduates only when a separate context (different session, different artifact, different audit window) re-encounters and surfaces the same pattern.

The §2.7 direct-`_simulate_path` call test added in this Pre-Q is the structural fix for the trap, not a rule-graduation event. Concrete next-step: when the next change touches MC simulation aggregator boundaries, the new test pattern (direct-call assertion that exercises the inner FP comparison) should be the standing convention.

**Future audit hook:** Rule 0-T graduates to load-bearing on second-instance-in-separate-context. Re-evaluate at the next aggregator-boundary fix or at 90 days, whichever comes first.

---

## Final summary

The Pre-Q's load-bearing claim — **C2 anchor holds under fixed simulation** — is **empirically confirmed**. The 2026-05-08 C2 relock decision stands. ADR 2026-05-10 (dd-protection ULP-rounding) stands. PR #53 was correct in fix posture but over-stated in inferred severity; this Pre-Q's evidence retroactively right-sizes the cascade.

7 of 7 §2 steps executed. 119/119 pytest pass. C2 anchor 98.09 / 0.36 / 4.73 holds at `abs=1e-4` post-fix. The methodology cascade — chain authored validator → defect surface → fix landed → empirical magnitude verified → MC re-validation → C2 lock empirically reconfirmed — closes in a single Pre-Q. Superpowers chain holds at load-bearing status; M-EC criterion now has four deployments in the audit trail (PR #52 + #53 + #58 + this Pre-Q).

## Out-of-scope follow-ups

Filed as separate issues on parent's directive — not folded into this PR.

1. **Doc-update for residual mc_explore references** — `chore`, low-priority. Per-file recommended actions:
   - `archive/.../h1_community_matrix.py`: add `# BROKEN: imports mc_explore, removed in Q-MCFP-1 (2026-05-10). Archive file; not re-runnable as-is.` comment block. Don't delete (archive policy is preserve-for-history).
   - `REPO_MAP.md` and `docs/notion/repo_context.md`: strike `mc_explore` line; add one-liner under "Removed files" referencing Q-MCFP-1.
   - `docs/adr/2026-05-08-dd-trigger-c2-relock.md`: append addendum noting `mc_explore` deleted in Q-MCFP-1; C2 anchor empirically reconfirmed; reference this closure document. Additive, no history rewrite.
2. **PR #59 manifest-generation process drift audit** — `op-risk`, P1. Investigation: did PR #59's manifest-script run correctly when authored, or did it produce shipped manifests against a different snapshot than is on disk? Audit hook proposal: pre-commit or CI check re-validating manifests against on-disk on every push. NAS100USD bar_data missing from main is a related vendor-data observation, tracking-only.

Issue numbers populated below post-creation:
- Doc-update issue: [**#61**](https://github.com/Joshua-Asante/multi_firm_operations/issues/61)
- Manifest audit issue: [**#62**](https://github.com/Joshua-Asante/multi_firm_operations/issues/62)
