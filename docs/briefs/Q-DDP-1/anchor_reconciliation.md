# Q-DDP-1 Pre-B — C0 anchor reconciliation

**Date:** 2026-05-06
**Author:** Claude Code (auto mode)
**Gate purpose:** identify source of brief Context numbers (98.13% / 0.22% / 4.49%) and reconcile against production-pinned anchor (97.88% / 0.22% / 4.55%).

## Re-run of canonical C0

```
$ python portfolio_mc.py --panel pepperstone

Pass:         97.88%  (sigma 0.01%)
Bust:          0.22%  (sigma 0.03%)
  Daily:       0.00%
  Static:      0.22%
Timeout:       1.90%
Median days to pass: 23
p99 DD:        4.55%

Bust attribution:
  striker        40.9%
  guardian       25.8%
  aegis          22.7%
  striker_nas100 10.6%
```

Matches [tests/test_mc_anchors.py:57-59](../../../tests/test_mc_anchors.py:57) and [CLAUDE.md](../../../CLAUDE.md) exactly.

## Source of 98.13 / 0.22 / 4.49

Identified via `git log` for the recent NAS100 add commit:

**Commit `4c65d29` (2026-05-05 17:02):**
> "Striker NAS100 v1 add (0.40%) + DJ30 v4.4 → v4.5 migration; **4-strategy MC anchor 98.13/0.22/4.49**"
>
> Pepperstone canonical anchor migrates 3-strategy 93.78/0.58/4.92 → 4-strategy 98.13/0.22/4.49. Bust attribution DJ30 49.2% / G 20.0% / A 20.0% / NAS 10.8%.

**Commit `09206eb` (2026-05-05 21:43, same day, four hours later):**
> "Guardian Pepperstone re-export: 209 → 201 trades; **4-strategy MC re-anchor 97.88/0.22/4.55**"
>
> The 04-26 Guardian export (87e73, 209 trades) contained 8 phantom v5.5 signals — likely a Pine recompile / cache artefact. Re-export 33781 produces 201 trades over the identical window. Re-MC: Pass 97.88% (was 98.13%) / Bust 0.22% (unchanged) / p99 DD 4.55% (was 4.49%).

Full audit trail: [data/reconciles/2026-05-05_guardian_n_reconcile.md](../../../data/reconciles/2026-05-05_guardian_n_reconcile.md).

## Verdict

**98.13/0.22/4.49 is obsolete.** It was the pre-reconcile anchor that lived as canonical for ~4 hours on 2026-05-05 before being superseded by 97.88/0.22/4.55 the same evening. The Q-DDP-1 brief was authored 2026-05-06; the brief author cited the morning's pre-reconcile numbers, missing the same-day re-anchor.

This is a textbook case of [feedback_per_strategy_pepperstone_baseline_uncommitted.md](../../../../../.claude/projects/C--Users-joshu-multi-firm-operations/memory/feedback_per_strategy_pepperstone_baseline_uncommitted.md) — when canonical numbers move within hours, downstream consumers can pick up the stale value.

## Resolution: which baseline does the sweep use?

**C0 anchor for sweep: 97.88% / 0.22% / 4.55%** (production-pinned, post-reconcile).

The brief's pass-rate floor of 97.9% was set at a time when the brief author believed C0 was 98.13% — a 0.23pp safety margin below C0. With the corrected C0 of 97.88%, the original 97.9% floor is now 0.02pp **above** C0, so C0 itself fails criterion 1 against itself.

**Adopted resolution (Option A from Phase 3 question):**

- Use **97.88% as the C0 baseline** for sweep comparison (already canonical).
- **Lower the pass-rate floor to 97.5%** for sweep acceptance criterion 1, preserving the brief author's intended ~0.2-0.4pp safety margin below C0 (97.5% is 0.38pp below C0, comparable to the original 0.23pp gap).
- All other acceptance criteria (bust ≤ 0.50%, p99 DD ≤ 5.00%, drag savings ≥ 10%, regime-robustness 5th-pctile ≥ floor) remain as authored.

This preserves the brief's intent (C0 narrowly passes criterion 1 with a small safety margin; relaxation candidates must clear by ≥ 0.5pp margin per the "no marginal-pass winners" rule) while honoring the corrected anchor.

**Symmetric consequence:** if a candidate config C* delivers pass_rate ∈ [97.50%, 97.88%), it satisfies criterion 1 but **fails the 0.5pp margin requirement against the floor** — so will be rejected as a marginal-pass winner. This means the effective binding floor for a LOCK CANDIDATE is ~98.0% (97.5% + 0.5pp), which is above C0 itself. **Therefore: a relaxation can only be a lock candidate if it strictly improves pass-rate above C0**, which is a strong constraint.

**Caveat for Joshua review:** the brief's author intent on the 97.9% floor is inferable but not explicit. If Joshua wants a different floor (e.g. exact preservation of 97.9% — accepting C0 fails its own criterion as a feature, since it forces all candidates to strictly beat C0), the sweep results CSV will still contain enough information to re-evaluate against any floor; the recommendation document can be regenerated with a different floor without re-running MC.

## Reproducibility

```bash
python portfolio_mc.py --panel pepperstone
# -> Pass 97.88% / Bust 0.22% / p99 DD 4.55%

git show 4c65d29 | head -15  # pre-reconcile 98.13/0.22/4.49 commit
git show 09206eb | head -15  # post-reconcile 97.88/0.22/4.55 commit
cat data/reconciles/2026-05-05_guardian_n_reconcile.md  # full audit
```
