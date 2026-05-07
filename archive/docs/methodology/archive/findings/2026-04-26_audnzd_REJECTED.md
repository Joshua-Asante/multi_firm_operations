# AUDNZD candidate strategy — REJECTED

**Loop:** `loop_2026-04-26_audnzd_discovery`
**Brief:** AUDNZD candidate-strategy discovery (2026-04-26)
**Phase:** 4 — verdict
**Outcome:** **4A — all tested frameworks fail OOS.**
**Date closed:** 2026-04-26

## Verdict

AUDNZD M15 over 2022-01-02 → 2026-04-24 (OANDA practice feed, validated
against Dukascopy at three dates) **does not currently exhibit a tradeable
edge under the standard mean-reversion and range-fade frameworks the
Phase 2 structural fingerprint authorized.**

Both frameworks fail every directional pass criterion (train PF, OOS PF,
OOS μ/σ, OOS Sharpe degradation) by margins that cannot be closed with
parameter retuning within the same framework family. Even with the
2-pip slippage haircut removed (a non-verdict-relevant diagnostic), neither
framework approaches the brief's PF ≥ 2.0 train threshold.

## Frameworks tested

| Framework | Train PF (slip 2p) | OOS PF | OOS n | Failed criteria |
|---|---:|---:|---:|---|
| Aegis-style BB+ATR | 0.722 | 0.620 | 136 | train PF, OOS PF, OOS μ/σ, OOS Sharpe |
| Range-fade + regime gate | 0.769 | 0.663 | 114 | train PF, OOS PF, OOS μ/σ, OOS Sharpe |

Frameworks **rejected at Phase 2** without testing (per brief §3.1
discipline that frameworks are determined by the structural fingerprint,
not pre-selected): EMA-cross trend, Striker-style breakout+pyramid, ORB
session breakout. Donchian channel reversion was held in reserve as
redundant with Aegis-style; given Aegis-style's failure, Donchian would
fail for the same reason and is not separately tested. See
[framework_screen §2.4 / §3.4](2026-04-26_audnzd_framework_screen.md) and
[structural_characterization §11](2026-04-26_audnzd_structural_characterization.md)
for full justification.

## Root cause

The Phase 2 structural fingerprint correctly identified AUDNZD as
range-biased + mean-reverting (42.7% range-day rate, lag-1 ACF = −0.078,
Hurst convergent to 0.5). The error in the candidate hypothesis was
**magnitude**, not direction: the structural mean-reversion signal at
lag-1 (−0.078 ACF) is real but **smaller than the irreducible 2-pip
execution cost** on M15. No parameter combination in the native sweep
can amplify the signal past that cost floor.

## Notice-routed forward observation (per brief §4A)

> **AUDNZD does not currently exhibit a tradeable edge under standard
> frameworks — re-evaluate if structural conditions shift.**

Logged as a Notice-routed observation. Specific re-evaluation triggers
that would warrant re-opening this loop:

- AUDNZD M15 lag-1 ACF magnitude exceeds 0.15 (≈2× current) on a
  rolling 6-month window.
- Daily range-day rate (|dir| < 0.3 of ATR14) drops below 30% AND trend-day
  rate exceeds 25% — would indicate a regime shift away from
  range-bound structure that might admit non-mean-reversion frameworks.
- A monetary-policy divergence between RBA and RBNZ widens to a
  multi-quarter trending phase (e.g., one easing while the other holds);
  this would amplify the cross's directional component beyond its
  range-bound default.

If none of those triggers fire, this finding does not need to be
re-opened. **No follow-up loop, no parameter retry, no broader framework
search.** The methodology that locked G v5.5 / S v4.4 / A v4.3 succeeds
because rejected hypotheses stay rejected.

## What this verdict does NOT mean

Per the brief's scope discipline:

- **It does not mean AUDNZD is uninteresting.** The structural fingerprint
  is informative and could inform other questions (e.g., correlation
  hedge for an existing position, or a multi-instrument breadth measure).
  Those would be separate briefs with separate questions.
- **It does not mean a non-M15 horizon would fail.** This loop tested
  M15 only because the existing portfolio operates at M15. A separate
  daily-horizon test could produce a different verdict; the lag-1 ACF
  finding is M15-specific.
- **It does not mean a non-retail execution feed would fail.** The 2-pip
  haircut is appropriate for FXIFY/retail prop conditions. A
  prime-brokerage feed at sub-1-pip might admit the small underlying edge.
  Outside FXIFY's constraint and outside this loop's scope.

Each of these is a separate INQHIORI loop with its own pre-Q gate. None
are authorized by this verdict.

## Carryover from Phase 1 (now permanent)

- The OANDA practice-endpoint deviation logged on 2026-04-26 is closed
  with this verdict. The empirical Dukascopy cross-reference (max diff
  0.250 pips at three dates) discharged the data-quality concern; the
  spread-tail caveat is moot now that no framework progresses to live.
- The data artifacts on disk (raw + clean CSV, structural results JSON,
  framework_screen results JSON) are not Production code. They are the
  audit trail for this verdict and should be retained for re-evaluation
  reference, not migrated into the operational pipeline.

## Out of scope (confirmed unmoved)

This verdict authorizes nothing in production:

- ❌ No Pine Script implementation work
- ❌ No portfolio Monte Carlo run
- ❌ No allocation discussion (G 0.34% / S 1.00% / A 1.50% remain locked)
- ❌ No dd_protection retuning
- ❌ No Notion ADR beyond the Inquire-loops log row (§ below)
- ❌ No modification of locked production parameters (G v5.5, S v4.4, A v4.3)

## Notion log row (per brief §"Notion integration")

After Joshua confirms this verdict, append the following single row to
the Command Center "Inquire-phase loops" log:

| Loop ID | Question | Verdict | Date | Findings file |
|---|---|---|---|---|
| `loop_2026-04-26_audnzd_discovery` | AUDNZD strategy edge under standard frameworks | 4A — REJECTED | 2026-04-26 | `docs/methodology/findings/2026-04-26_audnzd_*` |

No other Notion changes. No "potential portfolio addition" ADR.

## Forbidden-D-test audit (final)

Throughout the loop:

- Phase 1: no forbidden D-tests applied (only the four permitted tests
  in the cleaning discipline; deviations surfaced and authorized).
- Phase 2: caught and corrected one self-detected methodology bug (R/S
  Hurst applied to log-prices yielded spurious H≈1.0; corrected to log
  returns). Documented in
  [structural_characterization §15](2026-04-26_audnzd_structural_characterization.md).
- Phase 3: parameter sweep grids declared up-front and used in full; OOS
  evaluation happened once per framework with the frozen best-train
  params; no reverse-engineering. The widening of the entry-variant
  axis during diagnostic produced **worse** results, not better, and is
  documented in framework_screen §6.
- Phase 4 (this file): the verdict mechanically follows from the §3.3
  pass criteria. No qualitative override.

## Time accounting

| Phase | Brief soft cap | Actual | Notes |
|---|---:|---:|---|
| 0 | 10 min | ~10 min | Halt for OANDA endpoint deviation |
| 1 | 60 min | ~30 min | Practice-feed deviation + Dukascopy xref retry |
| 2 | 90 min | ~40 min | Hurst methodology bug caught and fixed mid-pass |
| 3 | 120 min (2 fw) | ~30 min | Sweep + diagnostic |
| 4 | 30 min | ~15 min | This file |

Total: **~125 min.** Well within the brief's 5-7h ceiling. The loop closed
fast because the verdict is unambiguous; no third-pass parameter retries
or framework expansions were attempted, per the brief's "rejected
hypotheses stay rejected" discipline.

## Cross-references

- Phase 1 provenance: [data_provenance/2026-04-26_audnzd_oanda_verification.md](../data_provenance/2026-04-26_audnzd_oanda_verification.md)
- Phase 2 structural fingerprint: [2026-04-26_audnzd_structural_characterization.md](2026-04-26_audnzd_structural_characterization.md)
- Phase 3 framework screen: [2026-04-26_audnzd_framework_screen.md](2026-04-26_audnzd_framework_screen.md)
- Brief: AUDNZD candidate-strategy discovery (2026-04-26)
- Decorrelation scan that surfaced AUDNZD: 2026-04-19 chat
- INQHIORI ⊕ The Algorithm: skill `inqhiori-algorithm`
- Two-tier canonical (Pepperstone/OANDA): user memory
  `feedback_two_tier_canonical_pepperstone_oanda.md`
