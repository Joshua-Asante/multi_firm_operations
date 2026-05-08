# Brief authoring drifted from codebase shape — 2026-05-07

**Session:** parent-session conversation that produced [PR #41](https://github.com/Joshua-Asante/prop_firm_pipeline/pull/41) (NAS100 ops integration) and [PR #42](https://github.com/Joshua-Asante/prop_firm_pipeline/pull/42) (Repo Context section).
**Anchors:** five incidents in one session — four failures plus one structural fix.
**Resolution status:** structurally fixed already. This lesson documents the historical context, not a proposed change.

---

## Pattern

Web Claude (the brief-authoring layer) drafts edit prescriptions against a *mental model* of `multi_firm_operations` that diverges from the codebase's *actual shape*. CC executes the prescription, treats the brief as authoritative, and does not surface the divergence until the prescribed edit fails or produces wrong work.

The pattern is **not** "web Claude is wrong" — web Claude *cannot see* the codebase mid-conversation. The pattern is "the handoff protocol assumed `brief == ground truth`" when the brief is in fact a model that decays as the codebase evolves.

---

## Anchors (5)

### 1. NAS100 drift fix brief — premise miss (`CLAUDE.md:48` vs `:50`)

The brief cited `CLAUDE.md:48` as defining canonical scope. CC's §0 read line 48 in isolation, confirmed the brief's premise, and proceeded. The disambiguating qualifier (the operational-scope sentence) was at line 50 — ten lines below — and would have flipped the brief's premise on read.

**Failure mode:** §0 reads at exact-line precision instead of ±20-line context. The line citation framed §0's read window too tightly.

### 2. Simplify-pass cross-ref count under-prediction (0–5 expected, 10 actual)

The Simplify-pass brief estimated 0–5 callers for the cruft candidates. CC executed the moves and discovered 10 actual callers (the deactivated overlay alone had 6). Cross-ref repair budget exceeded brief estimate by ~2×.

**Failure mode:** brief authored without `grep -rn <basename>` per candidate; cross-ref count was eyeballed from memory of doctrine references.

### 3. Lock-NAS100-live operational architecture invention (Path B that didn't exist)

The lock-NAS100-live brief prescribed edits against an imagined architecture: per-firm strategy schemas, per-strategy `Account` state, active-day gating in `dd_protection`, ATR flags in CLI, operational-tooling unit tests. **None of these structures exist for any strategy** — not for Guardian, not for DJ30, not for Aegis, not for NAS100. The actual integration was ~10 lines across 5 files (Path A), discovered when CC's §0 read the actual modules.

**Failure mode:** brief prescribed specific edits to production code web Claude had not seen in the conversation. Mental model substituted for source-of-truth at edit-prescription precision.

### 4. Lock-procedure operational-tooling integration phase gap (2026-05-05 → 2026-05-07)

NAS100 v1 was code-locked 2026-05-05 (Pine + manifest + MC anchor). The strategy was treated as locked-and-done. But operational tooling (`firm_rules / dd_protection / accounts / cli`) carried no awareness of NAS100 until 2026-05-07, when the gap surfaced during live-deploy planning. Two-day gap between "locked" and "actually deployable."

**Failure mode:** lock-procedure checklist conflated `Pine + manifest + MC` with `live-deployable state`. The operational layer was an unflagged dependency.

### 5. The structural fix itself (Repo Context section + §9 refresh contract)

The Notion Command Center page now carries a 10-section "Repo Context — multi_firm_operations" surface authored by CC, refreshed on triggers in §9. Web Claude reads it during brief authoring; CC's §0 still reads files at execution time as the truth gate. On-disk source [docs/notion/repo_context.md](../../notion/repo_context.md) (PR #42).

**Why anchor #5 is unusual:** most methodology lessons document failures-without-fixes — the lesson is the proposal, the fix happens later (or doesn't). This one bundles the lesson and the fix in the same shipping cycle. The structural change exists already; this lesson is documenting what already happened. That makes the capture lower-stakes than usual.

---

## Root cause

The brief-authoring handoff protocol implicitly assumed `brief == ground truth`. It does not. A brief is a snapshot of web Claude's working model at the moment of authoring. The model can be:

- **Correct and current** (ideal) — proceeds cleanly.
- **Correct but stale** (codebase moved since web Claude last saw it) — silent drift.
- **Approximately correct** (mental model of architecture diverges from actual shape) — anchors #1, #3, #4 above.
- **Counted wrong** (estimates without grep / cross-ref / count check) — anchor #2.

Anchors #1–#4 are different shapes of the same root: brief precision exceeded brief grounding.

---

## Structural fix (already shipped)

1. **Repo Context Notion section** (PR #42, 2026-05-07) — primes brief authoring with current architecture truth (file tree, schemas, lock matrix, queue). Web Claude reads it before drafting edit prescriptions. Refresh contract in §9.
2. **Five Rule 0 sub-rules** (in Notion §7) — operational discipline web Claude applies during authoring AND CC applies during §0 execution:
   1. Cross-reference grep before classifying "isolated cruft" (anchors #2)
   2. Archive convention verification (anchor #2 corollary)
   3. Rule 0 reads must include surrounding context (±20 lines) (anchor #1)
   4. Architecture truth before edit prescription (anchor #3)
   5. Lock procedures need an operational-tooling integration phase (anchor #4)
3. **CC's §0 truth-gate role formalized** — §0 is no longer a sanity check, it is the authoritative read. The brief is the *plan*; §0 is the *ground truth*. Where they conflict, §0 wins, and CC reports the divergence to Joshua before §2 execution.

---

## Residual risk

The fix addresses the *brief-authoring* side of the handoff. Two residual modes remain:

1. **Repo Context section drift.** §9 refresh triggers are claimed-but-untested. First missed-trigger event (e.g., a production-code edit that doesn't refresh §2/§3) will tell us whether the contract holds. Watch for ~30-day window.
2. **Architecture-truth blind spots.** §0 reads code; it does not automatically read *system semantics* (e.g., the multiplier-formula cancellation observation in §6 was discovered mid-conversation, not during a §0 read). Some shape lives in invariants no single file reveals. Mitigation: §6 carries observations as they surface; cross-strategy invariants migrate to §3 schemas as they're validated.

---

## What this lesson is NOT

- **Not a critique of web Claude.** Web Claude is the brief-authoring layer; it has structural visibility limits that this lesson addresses with structural support.
- **Not a proposal.** The proposal already shipped.
- **Not a one-time fix.** §9 refresh contract is a live commitment; staleness is a re-emerging failure mode.

---

## References

- **Notion Command Center — Repo Context section:** `32cdc0b53c1181b8a18cce1401a4f8e8`
- **On-disk source:** [docs/notion/repo_context.md](../../notion/repo_context.md)
- **PR #42** (this fix): https://github.com/Joshua-Asante/prop_firm_pipeline/pull/42
- **PR #41** (NAS100 ops integration, anchor #4 evidence): merged 2026-05-07
- **Rule 0 doctrinal page:** [docs/rule_0.md](../../rule_0.md)
