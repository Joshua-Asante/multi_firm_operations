# ADR: Minimum Viable Defense (MVD) discipline for load-bearing artifacts

**Date:** 2026-04-24

## Status

Accepted — 2026-04-24.
Generalizes and supersedes the standing Rule 0 (2026-04-17, audit-first for risk-control decisions).

## Context

A retrospective audit of nine recent debugging instances across the trading research and ops pipeline surfaced a uniform failure pattern:

- `portfolio_mc` 1R median-fallback (silent fallback)
- OANDA fetch terminating at ~10K rows instead of ~100K (page-2 heuristic)
- `dd_protection` production-vs-memory drift (Rule 0 catalyst)
- Aegis $117K calibration on USDJPY mislabeled as USDJPY_X (~2× overstated)
- Striker primary bust-risk mis-attributed to pyramid-reversal (actual: solo gap-fill)
- Striker `dayStopPct` -3% inert (never fired in 4yr panel)
- Aegis EOM described as "last 3 trading days" while Pine reads `dayofmonth>=29`
- "4yr Alchemy panel" actually 14mo (no 2022 regime coverage)
- TradingView <30-day P&L distortion via JPY→USD conversion hook

The failure mode across all nine is consistent:

- **Plausibly-shaped output, never a crash.** Bugs produce numbers that look right at a glance.
- **Failure at component boundaries**, not inside a module — handoffs between code, broker labels, prose, and memory.
- **Catch only by independent re-derivation**, never by closer inspection of the original output.
- **Naming the pattern has not reduced its frequency.** The OANDA bug filed 2026-04-24 was recorded alongside an explicit comparison to the 1R fallback trap; awareness was not protective.
- **Cost asymmetry is severe.** Time to catch ≈ hours. Cost when missed = wrong haircut → wrong allocation → wrong MC bust probability → wrong lock decision, compounding across versions.

67% of instances (6/9) are an *identity* sub-pattern: a string identifier (symbol, broker, version, "primary X", "fallback") was treated as if verified to refer to its claimed referent.

The standing Rule 0 covers one node (risk-control decisions) and works. The remaining nodes have no equivalent forcing function.

## Decision

Adopt a Minimum Viable Defense (MVD) discipline scoped to artifacts that cross the **live capital boundary** — defined as artifacts whose silent failure would change allocation, risk parameters, or lock decisions.

### North star

**Prevention with minimal friction.** Defenses are inline assertions and template preambles in code-resident artifacts, not checklists or memory rules. Inline `assert` runs on every invocation regardless of attention state.

### Mandatory MVD triggers (5)

An artifact requires MVD if and only if it falls under one of:

1. **MC input panels** — anything `portfolio_mc.py` reads (`data/tv_exports/pepperstone/` or successor canonical paths).
2. **Lock decision inputs** — every performance number (PF, RF, DD, trade count, $, WR) cited in any lock brief must be reproducible by a script with identity assertions.
3. **Risk-control production code** — `dd_protection.py`, Pine `risk_pct` / `dayStopPct` / SL / TP / session blocks. Any change requires self-validation that guards fire and fallbacks don't.
4. **Allocation changes** — lot/risk per strategy in `accounts.json`; CLI `update`/`lots` operations.
5. **Specific numbers or named behavior cited in memory, ADR, or CHANGELOG** — every "PF 4.186 / $178,208" or "EOM = days 29–31" must trace to a reproducing script with identity assertions.

Out of scope (no mandatory tax): exploratory scripts, methodology drafts, ad-hoc charts, broker-feed comparisons not yet promoted, datasets on disk until used in scope (e.g. the OANDA bar dataset until cited in a load-bearing brief).

### Assertion library (5 families)

Implemented in `multi_firm_operations/lib/mvd.py` as importable helpers:

1. **Cardinality** — row counts, time-window span, page counts. Helpers: `assert_window`, `assert_min_rows`.
2. **Identity** — symbol, broker, version, instrument suffix verified at top of any script producing a load-bearing number. Helpers: `assert_symbol`, `assert_broker`, `assert_version`.
3. **Contract** — guards must fire; fallbacks must not; named computations produce what their name says. Helpers: `assert_no_fallback`, `assert_guard_fired`.
4. **Cross-source** — TV-vs-Python, Pepperstone-vs-OANDA, prose-vs-Pine reconciliation gates. Helper: `assert_reconciled`.
5. **Code-vs-doc** — briefs `view` and paste literal production lines. Brief templates at `docs/templates/` enforce a verification-block preamble. "Primary X" claims require a generating script, not a sentence.

### Producer-side rule

For any artifact in scope, identity assertions appear within ~5 lines of identifier declaration. Cardinality and contract assertions appear at producing site, not consuming site (the author is the only one with full context to write them).

### Consumer-side promotion check

Any brief, ADR, memory entry, or CHANGELOG entry that cites specific numbers or named behavior must include a one-line attestation:

> **MVD-attest:** For each cited number, the producing script's first ~5 lines include identity assertions.

If the check fails, the artifact is not promoted: either the producing script is hardened, or the citation is removed. This is the explicit defense against the moment-of-promotion gap, since promotion happens in the head and not in a file. Placing a small share of the burden on the consumer also aligns with how catches actually happen — by independent re-derivation, never by closer inspection.

### Update protocol

Every new caught bug post-MVD-launch:

1. Adds a row to the audit table in `docs/methodology/mvd.md`.
2. If the catch reveals a new family or a new identity sub-pattern, adds a worked example and (if applicable) a new helper in `lib/mvd.py`.
3. Enforced as a step in any post-mortem or CHANGELOG entry that records the bug.

This is the defense against library decay (catching the previous war while current risk drifts un-covered).

### Artifact homes

**Repo (canonical, runnable):**
- `multi_firm_operations/lib/mvd.py` — assertion helpers
- `multi_firm_operations/docs/methodology/mvd.md` — library reference, worked examples, audit table
- `multi_firm_operations/docs/templates/calibration_brief.md`, `bust_analysis.md`, `lock_decision.md` — brief templates with verification preamble
- `multi_firm_operations/docs/adr/2026-04-24-mvd-discipline.md` — this document

**Notion (human-readable index):**
- New page under FXIFY Command Center linking to the repo files, listing the 5 families with one-line descriptions, referencing the audit table.

## Consequences

### Cost

- **Steady-state friction:** ~1–2 hrs/month writing assertions and brief preambles for in-scope artifacts.
- **One-time retrofit:** ~3 hrs covering panel loader (`portfolio_mc.py`), Aegis/Striker/Guardian calibration scripts, and `dd_protection.py` self-check.

### What changes

- The standing Rule 0 (risk-control decision audit) is generalized to the 4 additional triggers above, plus the consumer-side promotion check.
- Lock briefs and CHANGELOG entries gain a one-line attestation.
- Calibration scripts gain ~3–5 lines of assertions at the top.
- `portfolio_mc.py` 1R compute gains an `assert_no_fallback` check.

### What does not change

- Exploratory work (broker-feed sweeps, ad-hoc analysis, methodology drafts, the OANDA bar dataset until promoted) remains frictionless.
- Pine Script strategy logic itself is unchanged — MVD lives in the calibration / evaluation infrastructure, not in trade generation.
- Existing strategy version locks (Guardian Gold v5.5, Striker DJ30 v4.4, Aegis v4.3) are grandfathered. Future locks (or any re-MC) follow MVD.

### Known risks

- **Library decay.** Mitigated by the update protocol. If the protocol is skipped, the library degrades to catching only the previous war.
- **Skipped under time pressure.** Mitigated by keeping helpers cheaper than the manual cross-check they replace (one import + one line). If a helper requires more, it gets refactored, not skipped.
- **Scope creep.** Triggers are explicit and additions require an ADR amendment. No standing review clause; expansion happens by deliberate decision only.

## References

- Audit table: `docs/methodology/mvd.md` (instances 1–9, 2026-04-24)
- Standing Rule 0 codification: 2026-04-17 (memory)
- OANDA bar dataset note: Notion page `34ddc0b53c1181339eddf34db8978d8c` (2026-04-24)
- Pattern audit conversation: 2026-04-24 (Identify → Notice → Question → Hypothesize → Investigate → Reflect)
