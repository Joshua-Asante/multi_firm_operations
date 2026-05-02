# EURUSD M15 LNYO — Inquire-Phase Entry Handoff

**Status:** entry stub for a fresh Inquire-phase session. Notice-phase complete 2026-05-02.
**Parent brief:** [2026-05-02_eurusd_m15_lnyo_notice.md](2026-05-02_eurusd_m15_lnyo_notice.md)
**Why this file exists:** to enforce session isolation. The Inquire session must perform its own Rule-0 reads (parent brief §0), not inherit them from the Notice-authoring session that produced the brief.
**Loop:** INQHIORI — falsifiable hypothesis (H-NYFBO single-config), structural decision, gated promotion.
**Out-of-scope reaffirmation:** parent brief §7 binds the Inquire session in full.

---

## Spawn prompt for fresh Inquire session

Open a fresh Claude Code session in this repo (worktree or main branch — Inquire reads code, does not modify it) and submit:

```
Run H-NYFBO Inquire-phase falsification per
docs/methodology/findings/2026-05-02_eurusd_m15_lnyo_notice.md.

Before any data work:
1. Read every source in parent brief §0 (Rule-0 reads). State
   each one's load-bearing fact in your own words.
2. Read parent brief §3 (corpus + S-collapse), §4 (H-NYFBO
   hypothesis + 6 kill criteria including the Striker-active-day
   conditional estimator), §5 (10 methodology guardrails),
   §6 (G1 stage gate).
3. Independently verify Striker dow Tue+Fri
   (strategies/striker/striker_dj30_v4.4.pine:109) and
   Aegis dow Mon/Tue/Wed
   (strategies/aegis/aegis_usdjpy_v4.3.pine:190) by reading the
   Pine source — not the brief.

Then:
- Build Pepperstone-Razor session-conditional spread model
  (parent brief §5 guardrail #1).
- Load Dukascopy M15 EURUSD bid+ask 2022-01-04 → 2026-04-20
  with IANA tz-aware timestamps (§5 guardrail #4).
- Execute H-NYFBO single-config falsification with literature-
  default parameters (§5 guardrail #9).
- Stratify by three regimes (§5 guardrail #2); pooled stat is
  not the headline.
- Apply Striker-active-day (Tue + Fri) conditional correlation
  per kill #3; Friday-only sub-test recorded separately.
- Apply Guardian-active-day (Mon/Tue/Thu) conditional DXY
  anti-correlation check per §5 guardrail #6.
- Permutation gating ≥ 1000 shuffles per §5 guardrail #8.
- Apply Rule 1 small-cell variance-inflation if any regime
  n < 25.

Evaluate against G1 stage gate (parent brief §6). If any kill
criterion fires, write a kill note at
docs/methodology/archive/gate_audits/<YYYY-MM-DD>_eurusd_m15_h_nyfbo_kill.md
per parent brief §8.

Do not modify Pine, dd_protection, portfolio_mc, or CLAUDE.md.
No grid-search this session — single-variable iteration only
after first-config falsification per §5 guardrail #10.
```

---

## Routing if Inquire fails (parent brief §6 stage gates)

- **G1 fail (NYFBO):** if regime-specific failure → route to G2 (PDSB Inquire). If structural failure (spread > edge in all regimes) → route to G4 (abandon EURUSD M15).
- **G2 fail (PDSB):** if NYFBO survived as primary, decision is on portfolio merit; otherwise → G3 (PDDB Inquire).
- **G3 fail (PDDB):** route to G4.
- **G4 (all three failed):** abandon EURUSD M15 in this slot. Do not weaken kill criteria. Routing options in parent brief §6.

Each gate decision writes its own audit-trail file per parent brief §8.
