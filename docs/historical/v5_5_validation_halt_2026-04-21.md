# Guardian v5.5 Pepperstone Validation -- HALTED 2026-04-21

**Status: HALT at Task A (reconciliation). MC not run. No SHIP/BLOCK verdict
issued -- candidate cannot be evaluated against gates until input is fixed.**

> **Resolution (2026-04-23).** The 2026-04-21 halt was retired by a re-scoped
> Pepperstone panel run on 2026-04-23. Guardian v5.5 was locked jointly with
> Striker v4.4 / Aegis v4.3 (commit `e40802d`) and Guardian risk re-locked
> 0.30% → 0.34% same day (commit `84d3cb1`) on a 52-month Pepperstone panel
> showing headroom under both the 1% bust target and 5% static DD cap.
> Canonical post-relock MC: **92.73% pass / 0.65% bust / p99 DD 4.94%**.
> The reconciliation mismatch documented below is preserved as a record of
> the halt protocol firing correctly. See
> [`docs/adr/2026-04-23-guardian-risk-relock-0.34.md`](../adr/2026-04-23-guardian-risk-relock-0.34.md)
> and [`strategies/guardian/guardian_CHANGELOG.md`](../../strategies/guardian/guardian_CHANGELOG.md)
> v5.5 entry for the locked-of-record numbers.

Brief: Notion 34adc0b53c118181b12eff8a18f131c6.
Notion connector unauthenticated at run time -> this status posted as local
file in worktree; please paste / upload manually as the Results 2026-04-21
child page.

---

## Halt reason

`guardian.csv` (the file the brief identifies as v5.5) does not reconcile
to the v5.5 reference numbers given in the brief. Deviation is far outside
the 0.5% tolerance.

| metric | brief expected (v5.5) | guardian.csv actual | error |
|---|---:|---:|---:|
| trades | 188 | 190 | 1.06% |
| net P&L | $314,613.00 | $352,870.85 | **12.16%** |
| profit factor | 3.425 | 3.5327 | 3.15% |

Span: 2022-01-24 -> 2026-04-20.
Wins/losses: 42 / 148 (win_rate 22.11%).
Gross win $492,195.29 / gross loss $139,324.44.

This is unambiguous: per the brief halt list ("Guardian v5.4 or v5.5
Pepperstone reconciliation fails (>0.5% tolerance)") the run was stopped
before any MC was attempted. ~5 min of the ~30 min budget consumed.

## Cross-check: v5.4 reconciles cleanly

To rule out a parser / file-format issue:

| metric | brief expected (v5.4) | guardian_v5.4.csv actual | error |
|---|---:|---:|---:|
| trades | 215 | 215 | 0.00% |
| net P&L | $347,730.00 | $347,730.08 | 0.00% |
| profit factor | 3.16 | 3.1609 | 0.03% |

Same parser, same column layout, same date span -- v5.4 lands exactly on
spec. So the issue is the candidate file's contents, not the harness.

## What guardian.csv looks like vs the v5.5 spec and vs v5.4

- guardian.csv (alleged v5.5): **190t / $352,870.85 / PF 3.5327**
- brief v5.5 spec:             188t / $314,613.00 / PF 3.4250
- guardian_v5.4.csv (v5.4):    215t / $347,730.08 / PF 3.1609

guardian.csv has *more* net P&L than v5.4 with *fewer* trades and a higher
PF. So it is plausibly *some* v5.5-shaped variant -- but not the candidate
the brief was scoped against. Most likely causes (for human triage):

1. The TV export captured a slightly newer / different parameter sweep
   than the v5.5 spec was frozen on (e.g. a 2-trade tail extended the
   sample after the spec was written).
2. The brief's reference numbers are stale (spec finalized earlier, file
   re-exported afterward).
3. Wrong file uploaded into the pepperstone/ directory.

## Striker / Aegis (reported, not gated)

Per brief, Striker / Aegis Pepperstone numbers do not auto-halt -- they
flag for human review since there is no canonical Pepperstone reference
in memory yet (memory directory is empty). Reporting here so they are not
lost:

| CSV | trades | net P&L | PF | win_rate | span |
|---|---:|---:|---:|---:|---|
| striker.csv (v4.4) | 229 | $279,437.56 | 2.272 | 71.18% | 2022-01-04 -> 2026-03-31 |
| aegis.csv (v4.2)   | 136 | $165,288.79 | 3.227 | 58.82% | 2022-01-12 -> 2026-04-15 |

These look healthy -- positive PF, no zero-trade or negative-PF
pathologies, win-rate profiles consistent with each strategy's character
(Striker high-WR scalper, Aegis selective swing). They will need a
canonical Pepperstone reference recorded before any future run can use
the >25% deviation gate against memory.

## What I did NOT do (per halt protocol + brief constraints)

- Did not run portfolio MC for v5.4 baseline.
- Did not run portfolio MC for v5.5 candidate.
- Did not evaluate the 5 ship gates.
- Did not issue SHIP / BLOCK / REVIEW.
- Did not modify dd_protection.py, portfolio_mc.py, strategy parameters,
  or run Alchemy calibration.
- Did not deploy to live.

## Required to resume

Either:

1. Re-export `guardian.csv` from TradingView at the v5.5-frozen settings,
   confirm it lands at 188t / $314,613 / PF 3.425, drop into
   `data/tv_exports/pepperstone/guardian.csv`, then re-run.
2. Or, if the brief's v5.5 reference numbers are themselves stale and the
   190t / $352,870 / PF 3.5327 file is the correct candidate, update the
   brief's reconciliation targets and re-run with the new tolerance window.

Once reconciliation passes I can pick up at Task B (diff) -> Task C (MC) ->
Tasks D / E. Harness preserved at `scripts/run_v55_validation.py` (moved
2026-04-28 from this directory; archival, does not modify the locked
`portfolio_mc.py`).

## Methodology note

Counts are exit-row only (TradingView lists each trade as Entry + Exit
rows with identical P&L; MC and reconciliation use only exit rows for
single-counting). Same convention as `portfolio_mc.load_trades`.
