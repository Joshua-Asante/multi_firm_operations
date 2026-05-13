# Feed Equivalence Discovery Test — LOCKED

**Status:** LOCKED (re-locked) 2026-05-10
**Originally drafted:** 2026-05-06
**Stage:** Multi-firm onboarding stage 1 — feed equivalence pre-flight
**Loop:** INQHIORI, Inquire phase, data-domain
**Canonical path:** `multi_firm_operations/docs/spec/feed_equivalence_discovery_test_LOCKED.md`
**ADR number:** assign next sequential on commit

---

## §Context (preserved verbatim from 2026-05-06)

Locked Pepperstone-52mo MC (Pass 97.88% / Bust 0.22% / p99 DD 4.55%, attribution DJ30 49.2 / G 20 / A 20 / NAS 10.8) was calibrated against TV-Pepperstone CSV exports. Multi-firm scaling phase introduces three additional firms (FundedNext, FTMO, fourth firm in onboarding) executing on MT5, while FXIFY remains anchor on DXTrade/TV. Three of four firms will execute on MT5-Pepperstone — making MT5 the majority execution feed even though TV is the calibration feed of record.

Stage 1 question: do MT5-Pepperstone and TV-Pepperstone serve identical 15m OHLC data, or different processing pipelines on the same broker? Binary answer determines whether locked MC transfers as-is, or whether canonical calibration source needs to change.

## §Context-update (added 2026-05-10)

Two facts in §Context have drifted since 2026-05-06. Documented here rather than back-edited into §Context to preserve the audit trail of what the original author knew. Neither modifies the test design.

- **F4 — MC anchor drift.** The "Pass 97.88% / Bust 0.22% / p99 DD 4.55%" anchor cited in §Context was superseded on 2026-05-08 by the C2 relock (ADR `2026-05-08-dd-trigger-c2-relock`). Current anchor: **Pass 98.09 / Bust 0.36 / p99 DD 4.73, attribution striker 44.4 / aegis 24.1 / G 21.3 / NAS 10.2.** The test design is unchanged; only the anchor numbers that the test's "MC transfers as-is" branch licenses transferring have moved. See §Outcome bridge for explicit current-anchor handling.
- **F5 — Firm pipeline rename.** "FundedNext, FTMO, fourth firm in onboarding" was the candidate pipeline as of 2026-05-06. Current state: BrightFunded is the named next firm, gated on FXIFY $200K→$805K scaling milestone. The test's logic — that majority MT5 execution makes feed equivalence the gating question for canonical calibration — is unchanged regardless of which firms hold the MT5 majority.

## §D-S-A domain

Data. Cascade note: outcome may trigger system-domain action (re-anchor canonical MC source) but this brief does not author that action.

## §Pre-Q gate

- **D:** deleted bar-count parity, weekly-open KS, stop-proximity sign-of-touch, wick-extreme distributions, tick-volume correlation, DST advisory, and 2 of 3 symbols. D-test applied: *"is this datum a proxy for an answer the binary same-source check returns directly?"* — permitted (literal duplication of higher-fidelity source).
- **S:** corpus reduced from ~96K bars across 3 symbols × 52 months to ~250 bars × 1 symbol × 2 weeks. Anomaly preserved (any feed divergence shows in raw OHLC comparison).
- **A:** index by `(symbol, timestamp_utc)`; comparison is dataframe join, O(seconds).

## §Hypothesis

**H_0:** MT5-Pepperstone and TV-Pepperstone serve identical 15m OHLC data, modulo display-precision rounding.

## §Scope

- Symbol: **XAUUSD.a** only. Selected because gold has the most documented cross-vendor feed precision variance and Guardian's no-BE stop logic is most sensitive to single-bar OHLC errors. If XAUUSD passes, USDJPY.a / US30.cash / NAS100 trivially pass; if XAUUSD fails, escalation covers all symbols.
- Window: 2026-04-13 through 2026-04-25 (two completed weeks). Captures two Sunday opens, two Friday closes, one EOM-adjacent period.
- Timeframe: 15m.

## §Phase 0 — Rule 0

Before pulling MT5 data:

1. Re-reconcile existing `data/tv_exports/pepperstone/Guardian_Gold_v5.5_*.csv` against its Pine-header backtest (201 trades / PF 3.7717 / Net +$576,085 / closed-DD 6.128% / WR 20.40%; tolerance 0.5% on each).
2. **F3 (added 2026-05-10) — SHA + post-ULP-fix anchor verification.** Verify the CSV SHA256 against the entry in `data/tv_exports/pepperstone/SHA256SUMS`. The export may have been regenerated post-ULP-fix (PR #53, 2026-05-08); if SHA mismatch, halt and update the anchor numbers in step 1 before resuming. This is the only step that may be modified post-lock without an ADR, and only to the extent of substituting current-parse numbers from the re-exported CSV. Echo the SHA, the parse output, and any anchor substitution into the result artifact.
3. `ls scripts/` to verify nothing like `feed_overlap.py` already exists before proposing it as a new file. If a similar tool exists, extend rather than duplicate. (Repo path updated from `prop_firm_pipeline/scripts/` per rename 2026-05-08.)

## §Procedure

1. Export 15m XAUUSD.a from MT5-Pepperstone for the window (History Center → CSV). Capture broker-server timezone metadata.
2. Pull the same symbol/window from the existing TV-Pepperstone source.
3. Normalize both to UTC; align on `(timestamp, symbol)`.
4. For each bar: compute `|MT5_x - TV_x|` for x in {O, H, L, C} at the precision both feeds display.
5. **F1 (added 2026-05-10) — precision convention sub-rule.** The precision convention used for the `|MT5_x - TV_x|` comparison must be consistent across all four OHLC fields and documented in the output table header. Mixed precision (e.g., 2dp on close, 4dp on open) would mask or invent differences. The 0.5% tolerance check in §Phase 0 step 1 must likewise use a single precision convention across PF / Net / DD / WR. This sub-rule distils the lesson from PR #53 (dd_protection ULP-rounding fix): mixed precision conventions across comparison sites produce artifacts that read as data divergences.
6. Output a single table: bar-count match, count of bars with any nonzero diff, max diff per OHLC field, the precision convention used, and the timestamps of the top 10 divergent bars.

## §Decision rule

Outcome shape determines the call:

- **All bars match exactly to displayed precision** → same source. H_0 not rejected. Locked MC transfers to MT5-Pepperstone without recalibration. Proceed to multi-firm onboarding stage 2.
- **All bars match within sub-pip rounding only, consistent pattern** → same source with display precision differences. H_0 not rejected. Note rounding behavior in ADR followup. Proceed.
- **Bars match on most days, divergence localized to specific dates / session boundaries** → not yet decisive. Investigate the specific dates manually. May or may not require escalation.
- **Systematic small diffs distributed across all bars, OR diffs >0.5% of bars exceed displayed precision** → different source or different processing. H_0 rejected. Halt onboarding stage 2. Author full spec (recovering relevant pieces of v1) against the *observed* divergence pattern rather than guessed thresholds.

**F2 (added 2026-05-10) — per-bar diff incidence vs MC impact.** The 0.5% threshold above is on *per-bar diff incidence rate*, not on downstream MC impact magnitude. If H_0 is rejected, do NOT infer the magnitude of MC bust-rate impact from the diff rate. The Q-MCFP-1 closure (2026-05-10) established that continuous-trajectory aggregation washes out boundary-discontinuity noise at the population level — the 47.4% boundary-exact mis-fire rate in dd_protection produced negligible MC impact. The bar-level diff rate is the falsifier for *feed equivalence*, not for *MC equivalence*. If H_0 is rejected, the escalation spec authored against the observed divergence pattern must independently establish MC impact, not assume it follows linearly from bar-diff incidence.

## §Out of scope

- USDJPY.a, US30.cash, NAS100 — covered by transitive logic if XAUUSD passes; covered by escalation if it fails.
- Spread / commission modelling deltas — legitimate concern, will be raised in escalation if H_0 rejected. Not silently deleted.
- Per-firm rule-delta re-MC triggers — orthogonal. Fire regardless of feed equivalence.

## §Pre-registration commitment

Thresholds and decision rule above are immutable for this gate cycle. Re-opening requires a separate ADR justifying why prior thresholds were misspecified, written without reference to observed data.

The 2026-05-10 re-lock applied B.3 integration (F1/F2/F3 inline as sub-rules, F4/F5 in §Context-update, §Outcome bridge clarification). None of these modified the spec body's H_0, decision-rule branches, scope, or thresholds — they constrain *how* the test is executed and interpreted, not *what* the test decides.

## §Outcome bridge

- H_0 not rejected → onboarding stage 2 (per-firm rule matrix re-MC scoping for any firm with rule deltas vs FXIFY; copier multiplier setup; per-firm contractValue verification).
- H_0 rejected → escalation: author full feed-divergence investigation spec against observed pattern, AND open structural Q on canonical calibration source.

**Anchor reference (added 2026-05-10):** "Locked MC transfers to MT5-Pepperstone" in the H_0-not-rejected branch refers to whichever MC anchor is current at result-read time, not the snapshot in §Context. The §Context anchor (97.88 / 0.22 / 4.55) is preserved for audit. The current anchor as of re-lock (2026-05-10) is 98.09 / 0.36 / 4.73 per the 2026-05-08 C2 relock — that is what would actually transfer if the test runs today and returns H_0 not rejected. Future relocks update this reference automatically; the decision rule's binary structure is unchanged.

---

## §Lock metadata

- **Originally drafted:** 2026-05-06 (web Claude). Self-review pass completed pre-lock; v1 spec narrowed to v2 per The Algorithm (delete what shouldn't exist before optimizing).
- **Re-locked:** 2026-05-10 (web Claude). B.3 integration per Rule 0 audit. Spec body sections (§Hypothesis, §Scope, §Procedure steps 1-4 and 6, §Decision rule branches, §Out of scope, §Pre-registration top paragraph, §Outcome bridge top-level branches) byte-identical to 2026-05-06. Added: §Context-update sub-section (F4/F5), §Phase 0 step 2 (F3), §Procedure step 5 (F1), §Decision rule F2 sub-rule, §Outcome bridge anchor-reference clause, §Pre-registration 2026-05-10 paragraph.
- **Authorship & migration note:** Original committed path target was `prop_firm_pipeline/docs/` (never landed in git per pickaxe + working-tree grep 2026-05-10 — see CC handoff §0.1 evidence). Re-locked at canonical path `multi_firm_operations/docs/spec/feed_equivalence_discovery_test_LOCKED.md` per parallel-work doctrine (`docs/spec/` singular convention staged 2026-05-10).
- **Notion canonical:** retired 2026-05-10 (page `358dc0b53c11818085d0cc36692e0185` trashed during Notion cleanup). This markdown is sole canon going forward.
