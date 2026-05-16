# Regime-robustness gate

**Status:** canonical
**Version:** 1.0
**Authored:** 2026-05-06 (post Q-DDP-1 closure)
**Origin:** worked example in Q-DDP-1 (`docs/briefs/Q-DDP-1/`)
**D-S-A domain at authoring:** meta-process (framework codification)
**Applies during:** INQHIORI loops on system-domain questions involving risk-constant Pareto sweeps

---

## What this gate is

A two-part panel-resampling test that any candidate configuration must pass before being recommended as a LOCK CANDIDATE in a Pareto-relaxation brief on a risk-control constant. Specifically: **6-month-block bootstrap** + **half-panel time split**, both pinned to the brief's full-panel pass-rate floor.

This gate exists because of one structural asymmetry: in any Pareto-relaxation question on `dd_protection` or analogous risk constants, **drag is fully measurable on the panel; tail-protection benefit is only partially measurable**. The realized panel is one trajectory through regime-space. A relaxation that wins on the realized panel may lose under regimes the panel didn't sample. This gate is the conservative haircut that lets the brief surface that distinction.

---

## When this gate fires

**Mandatory** for:
- Any brief proposing a change to constants in `multi_firm_operations/dd_protection.py`
- Any brief proposing a Pareto-relaxation on (pass-rate, drag) or analogous (safety, performance) plane
- Any brief comparing MC configurations on a single panel where regime distribution materially affects the result

**Not required** for:
- Strategy parameter changes (governed by strategy-specific gates: pyramid-conditional WR, MFE/MAE direction-symmetry, etc.)
- Allocation changes (governed by variance-contribution + MC re-balance methodology)
- Adding / removing strategies (full re-MC at locked `dd_protection` — no Pareto sweep)
- Operational decisions (OODA layer, not INQHIORI)
- Any decision routed to OODA per the loop-selection canon

If a brief is uncertain whether this gate applies: default to running it. The gate is cheap (typically <30min wall-clock); the false-positive LOCK CANDIDATE failure mode is expensive (a production change that doesn't generalize).

---

## Procedure

### Part A — Block bootstrap on the locked panel

1. Take the locked panel (e.g. 52-month Pepperstone). Treat as a daily DataFrame with one row per business day.
2. Define **6-month contiguous blocks** over the panel timeline. With a 52-month panel, this yields ~9 candidate blocks; bootstrap variance scales accordingly.
3. **Resample with replacement** to construct 100 alternate-history panels of the same total length as the original.
4. For each alternate panel, rebuild the inner MC week-blocks (the existing harness's 5-day resampling unit) and run the full MC sweep at the candidate config — same seed count as the parent brief (e.g. 30K paths × 3 seeds).
5. Record per-(config, alt_panel_id) tuple: `pass_rate, bust_rate, p99_dd`.
6. Compute the **5th percentile** of the 100-panel pass-rate distribution per candidate.

### Part B — Half-panel time split

1. Split the locked panel at its temporal midpoint:
   - For 52mo Pepperstone (2022-01 → 2026-04): H1 = 2022-01 → 2024-04, H2 = 2024-05 → 2026-04.
   - Unequal-length halves are acceptable; document the split point.
2. Run full MC at the candidate config on each half independently — same seed count as the parent brief.
3. Record per-(config, half) tuple: `pass_rate, bust_rate, p99_dd`.

### Part C — Acceptance test

A candidate config C* passes the gate **if and only if all three** hold:

1. **Bootstrap 5th-percentile pass-rate ≥ floor** (where floor = the brief's full-panel pass-rate floor)
2. **H1 pass-rate ≥ floor**
3. **H2 pass-rate ≥ floor**

Failure on any one criterion rejects the candidate as **regime-fragile**, even if it strictly Pareto-dominates on the full panel under criteria 1-4 of the brief's acceptance set.

The bootstrap and half-panel parts are complementary. Bootstrap captures **block-level regime variance**; half-panel captures **temporally-coherent regime asymmetry**. A candidate can fail one and pass the other; both must clear.

---

## What this gate catches

- **Partition-specific dominance** masquerading as full-panel dominance (Q-DDP-1's C2 result).
- **Panel-regime artifacts** where the candidate's win is concentrated in one sub-period.
- **Sensitivity to block-resampling order** that wouldn't generalize forward.

## What this gate does NOT catch

- **Out-of-distribution regimes the panel never sampled.** A 52mo Pepperstone panel from 2022-01 → 2026-04 contains no 2008-style crisis sample. No bootstrap or split can manufacture data the panel doesn't have. This is the residual uncertainty that justifies keeping the locked config conservative even after the gate clears — there are regimes outside both H1 and H2 that the panel doesn't reach.
- **Continuous non-stationarity** as opposed to block-coherent regimes. Block bootstrap preserves intra-block correlation structure but destroys inter-block ordering; if the actual regime evolves smoothly, the bootstrap distribution will be unrepresentative.
- **Strategy-specific tail risks** that aren't expressed in the panel's MC trajectories (e.g. a strategy that has a structural binary-event tail not represented in its 4yr trade history).

The gate is necessary but not sufficient. A passing candidate still requires the brief author's judgment on the residual uncertainty haircut.

---

## Relationship to other gates

| Gate | Layer | Operates on | When |
|---|---|---|---|
| Rule 0 (audit-first) | Pre-loop | Production source | Before INQHIORI begins |
| Pre-Q gate (D-S-A on data) | Inside INQHIORI | The I/N corpus | Before Q is asked |
| **Regime-robustness gate** | **Inside INQHIORI** | **Candidate configs** | **Before LOCK recommendation** |
| Rule 1 (partition-hypothesis permutation) | Post-observation | Specific partition hypotheses | When partition-specific dominance is asserted |
| Observation routing gate | Post-pre-Q | Observations | After Q produces evidence |

These compose; they don't compete. A brief running this gate may also need to run Rule 1 if the gate's failure surfaces a specific partition hypothesis worth formal screening (e.g. "C2 wins in H2 but not H1 — is this stochastic or systematic?"). When in doubt, run both.

---

## Worked example: Q-DDP-1 (2026-05-06)

The first formal application of this gate. Brief asked whether a Pareto-dominant relaxation of `(DD_TRIGGER=1.0%, DD_SCALE=0.40×)` exists under 4-strategy diversification.

Sweep over 5-config grid produced one candidate that passed full-panel acceptance criteria 1-4: **C2 = (1.5%, 0.40×)** with full-panel pass-rate 98.09%, drag savings 25%.

This gate's verdict on C2:

| Test | Result | Floor | Pass? |
|---|---:|---:|:---:|
| Bootstrap 5th-percentile pass-rate | 90.82% | 97.5% | ❌ |
| H1 (2022-01 → 2024-04) pass-rate | 86.78% | 97.5% | ❌ |
| H2 (2024-05 → 2026-04) pass-rate | 99.67% | 97.5% | ✅ |

C2 rejected as **regime-fragile** by the gate. The H1↔H2 spread of 12.9pp is decisive — C2's apparent full-panel dominance was an H2-driven artifact. Brief verdict: AMBIGUOUS / default HOLD.

Without this gate, the sweep would have produced a LOCK CANDIDATE recommendation on C2 with no dissenting evidence. **This gate is the specific reason the regime fragility entered the record.**

**Postscript — 2026-05-08 OVERRIDE.** Joshua subsequently adopted C2 anyway, on broker-feed-resolution + median-pass-time grounds (see `docs/briefs/Q-DDP-1/recommendation.md` OVERRIDE section + `docs/briefs/bust_attribution_flip.md` closure). The gate's regime-fragility signal was preserved as dissent, with a forward revert trigger (rolling 6-month MC pass-rate <95% for two consecutive windows → revert to C0). The methodology value of this worked example is unchanged — the gate **correctly surfaced** fragility evidence; whether to act on that evidence is a separate decision Joshua made on broader information.

---

## Edge cases and boundary conditions

**Panel length.** Block bootstrap requires the panel to have ≥4 candidate blocks at the chosen block size. For 6-month blocks, that means ≥24-month panel minimum. Shorter panels: either reduce block size to 3 months (with documented justification) or reject the brief as unable to clear regime stress.

**Unequal half-panels.** Acceptable. Document the split point. The split should reflect a meaningful regime boundary if one is identifiable; absent that, midpoint is the default.

**Bootstrap n.** Default n=100. For close calls (5th-percentile within 1pp of floor), upgrade to n=200 to reduce 5th-percentile estimator variance.

**All candidates rejected.** That IS the answer. The brief closes with HOLD verdict and the locked config is confirmed. This is not a methodology failure — it's the gate working correctly to surface regime fragility across the entire grid.

**Pre-registered floor.** The gate's pass-rate floor must equal the brief's full-panel pass-rate floor (criterion 1 in standard Pareto sweep). No separate "regime floor" is permitted — that would be a hidden parameter through which post-hoc fitting could enter.

**Sanity checks during execution.**
- Bootstrap 5th-percentile must be ≤ full-panel pass-rate (regime stress is a haircut, not a boost). Violation = bootstrap implementation bug.
- Bootstrap p95 should typically be ≥ full-panel pass-rate. If not, the panel itself is regime-anomalous.
- H1 + H2 path counts should sum approximately to full-panel path count. Material gaps suggest a panel-construction error.

---

## Implementation notes

The procedure above is implementation-agnostic. A reference implementation lives inline in `docs/briefs/Q-DDP-1/_run_regime_robustness.py` (script-form, brief-specific). A canonical reusable implementation should be added to the operations pipeline at `multi_firm_operations/regime_robustness_gate.py` if/when a second brief invokes this gate — at that point, the implementation graduates from inline to library.

Until graduation, briefs invoking this gate should write their own script under their `docs/briefs/Q-XXX/` directory and reference back to the Q-DDP-1 implementation as the structural template.

---

## Re-MC trigger registration

A brief that **invokes this gate AND produces a LOCK CANDIDATE** has, by construction, changed a risk constant. That constant change is itself the canonical re-MC trigger. The order of operations:

1. Brief gates clear (including this gate)
2. LOCK CANDIDATE recommendation surfaced to Joshua
3. Joshua approves → constant change committed to production
4. Re-MC fires immediately at the new config (full 4-strategy MC, all locked seeds)
5. ADR drafted documenting the lock decision and re-MC results

Steps 4–5 are not part of the brief that ran this gate — they are downstream consequences. A brief that bundles them is a Rule-0-violating brief and should be rejected.

---

## Provenance

- **2026-05-06 — Q-DDP-1 closure**: gate worked example produced; H1↔H2 spread of 12.9pp on C2 surfaced regime fragility that full-panel sweep missed.
- **2026-05-06 — methodology canonization**: this doc authored.
- **Future calibration**: the bootstrap n=100 and 5th-percentile floor are calibrated to the current panel size and seed count. If the locked panel grows substantially (e.g. to 8+ years post-2030) or seed count changes, re-evaluate whether n and the percentile threshold remain appropriate.

---

## Cross-references

- **INQHIORI ⊕ OODA framework**: `notion.so/34ddc0b53c1181479d7bdecc61f47078`
- **INQHIORI skill**: `~/.claude/skills/inqhiori/SKILL.md` (web + Code)
- **Rule 0**: `docs/rule_0.md`
- **Rule 1 (partition-hypothesis permutation gate)**: methodology canon in skill registry, reference implementation deferred until first formal use
- **Observation routing gate**: `docs/methodology/observation_routing.md`
- **Q-DDP-1 worked example**: `docs/briefs/Q-DDP-1/recommendation.md`
- **Locked dd_protection config**: `multi_firm_operations/dd_protection.py` (DD_TRIGGER=0.015, DD_SCALE=0.40 — C2 relock 2026-05-08)
- **MC harness**: `multi_firm_operations/portfolio_mc.py`
- **Production-pinned MC anchor**: `tests/test_mc_anchors.py` (98.78% / 0.12% / 4.17% on 48mo Pepperstone 2026-05-14 allocation refresh, 4-strategy at C2 with DJ30 0.75%/pyramid 500% + NAS 0.45%; prior panel-refresh-only anchor 98.65/0.25/4.69 and 2026-05-08 C2 anchor 98.09/0.36/4.73 preserved as historical in CLAUDE.md. The 2026-05-14 allocation refresh overrides this gate explicitly per `docs/adr/2026-05-14-allocation-refresh.md` §Override.)

---

## What this doc does NOT change

- Any locked strategy parameter (v5.5 / v4.5 / v4.3 / v1)
- Any locked allocation (G 0.34% / DJ30 1.00% / A 1.50% / NAS 0.40%)
- The locked dd_protection config (1.5%, 0.40× — C2 since 2026-05-08; was 1.0%, 0.40× until override)
- The MC harness logic
- The full-panel acceptance criteria template for Pareto sweeps (this doc adds a layer on top, doesn't replace)

This is a methodology layer addition. Production state is unaffected. The next time a Pareto-relaxation question on a risk constant gets authored, this gate becomes mandatory criterion 5 (or analogous numbering) in that brief's acceptance set.
