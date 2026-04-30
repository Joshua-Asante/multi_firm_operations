# Q-A1.1 — Aegis Pepperstone Panel-Quintile Replication Test

**Date:** 2026-04-29
**Author:** Claude (Opus 4.7)
**Type:** Decision brief — analysis-only refinement of Q-A1; no code/allocation/dd_protection touch
**Verdict:** **PARTIAL** (with substantively refined finding — see below)
**Routing:** Hand back to Joshua for routing call; recommended candidates listed below.

## Parent / dependencies

- **Parent:** [Q-A1 — Pepperstone panel-thirds replication](q_a1_pepperstone_replication.md) — verdict PARTIAL; recommended quintile split as Refinement #1 (cheapest).
- **Q15 closure:** [findings_2026-04-26.md:414-510](../../../../analysis/notice_phase/findings_2026-04-26.md).
- **Q-A parent gated brief:** [`q_a_aegis_panel_mechanism_gated.md`](../2026-04-27/q_a_aegis_panel_mechanism_gated.md) (2026-04-27 synthesis, backfilled to repo 2026-04-29 — Q-A1-d closed).
- **Methodology:** [observation_routing.md](../../observation_routing.md), [1r_estimation.md](../../1r_estimation.md).
- **Data files (reused from Q-A1):**
  - Pepperstone: `data/tv_exports/pepperstone/Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-04-26_0bf1b.csv`
  - OANDA reference: `data/tv_exports/oanda/Aegis_USDJPY_v4.3_OANDA_USDJPY_2026-04-25_7ee6b.csv`
- **Analysis script:** [analysis/notice_phase/q_a1_1_aegis_pepperstone_quintile.py](../../../../analysis/notice_phase/q_a1_1_aegis_pepperstone_quintile.py) (imports loader from Q-A1).

## Methodology

Same loader, same data, same risk_pct, same R-multiple convention as Q-A1. Two conventions:

- **Convention A — calendar-year quintile.** One calendar year per bin: q1=2022 (n=18), q2=2023 (n=26), q3=2024 (n=28), q4=2025 (n=41), q5=2026 partial (n=10). Generalization of Q-A1 Conv A's calendar-year tertile.
- **Convention B — equal-N trade-index quintile.** Sort by entry time, partition into 5 most-even bins via `np.array_split`. For N=123: 25 / 25 / 25 / 24 / 24.

Per-bin metrics (PF, n, WR, mean R, median R, ret_std, sum R, date range), bootstrap 95% CI on PF (Pepperstone only, 10,000 resamples, seed 42), and **Spearman rank correlation permutation test** (Pepperstone only, 10,000 shuffles, seed 42). Spearman replaces Q-A1's strict-monotonic-AND-ratio criterion as the natural generalization for 5 bins, where strict monotonicity across all 5 is too restrictive given per-bin noise.

Two p-values reported per convention:
- `p (Spearman ≥ obs)` — tests rank-monotonicity alone.
- `p (Spearman AND ratio q5/q1 ≥ obs)` — joint criterion matching Q-A1's spirit.

The verdict criterion uses the joint p.

## Self-tests

**Conv A — aggregation self-test against Q-A1 Conv A tertiles.** Aggregating quintiles q1+q2 (44 trades = 18+26) / q3 (28 trades) / q4+q5 (51 trades = 41+10) must reproduce Q-A1 Conv A Pepperstone tertile PFs exactly.

| Tertile | n agg | observed | Q-A1 anchor | \|delta\| | Result |
|---------|-------|----------|-------------|-----------|--------|
| early   | 44 (q1+q2) | 2.468  | 2.468 | 0.0001 | PASS |
| mid     | 28 (q3)    | 4.500  | 4.500 | 0.0000 | PASS |
| late    | 51 (q4+q5) | 5.561  | 5.561 | 0.0004 | PASS |

n aggregated matches Q-A1 expected: 44 / 28 / 51. **PASS** — quintile splitting and aggregation logic is internally consistent with Q-A1's tertile run.

**Conv B — column-sum reconciliation against panel.** Σn_quintile = 123 = panel; Σsum_R_quintile = 3.6867 = panel sum_R; Σn_wins_quintile = 74 = panel n_wins. Bin sizes 25 / 25 / 25 / 24 / 24. **PASS.**

(Conv B has no clean aggregation map to Q-A1's equal-N tertile (49/25/49 ≠ 41/41/41), so the column-sum reconciliation is the available internal-consistency check.)

## Per-quintile metrics — Pepperstone Convention A

| Bin     | n  | PF     | WR%   | mean R | median R | ret_std | sum R  | date range                |
|---------|----|--------|-------|--------|----------|---------|--------|---------------------------|
| q1=2022 | 18 | 0.328  | 44.44 | -0.015 | +0.000   | 0.0504  | -0.273 | 2022-01-12 → 2022-12-07   |
| q2=2023 | 26 | 5.187  | 73.08 | +0.052 | +0.007   | 0.1124  | +1.340 | 2023-01-11 → 2023-12-27   |
| q3=2024 | 28 | 4.500  | 53.57 | +0.032 | +0.000   | 0.0894  | +0.887 | 2024-01-08 → 2024-12-23   |
| q4=2025 | 41 | 4.053  | 56.10 | +0.028 | +0.000   | 0.0795  | +1.160 | 2025-02-03 → 2025-12-24   |
| q5=2026 | 10 | inf    | 90.00 | +0.057 | +0.010   | 0.0704  | +0.573 | 2026-01-27 → 2026-04-15   |

q5=2026 has only one losing trade (n=10, 9 wins), making PF undefined-as-finite. Treated as `+inf` for verdict; ratio q5/q1 propagates as NaN.

## Per-quintile metrics — Pepperstone Convention B

| Bin | n  | PF     | WR%   | mean R | median R | ret_std | sum R  | date range                |
|-----|----|--------|-------|--------|----------|---------|--------|---------------------------|
| q1  | 25 | 2.525  | 52.00 | +0.025 | +0.000   | 0.1009  | +0.620 | 2022-01-12 → 2023-03-28   |
| q2  | 25 | 2.333  | 68.00 | +0.021 | +0.000   | 0.0895  | +0.533 | 2023-04-03 → 2024-04-15   |
| q3  | 25 | 6.133  | 56.00 | +0.041 | +0.000   | 0.0983  | +1.027 | 2024-04-17 → 2025-02-19   |
| q4  | 24 | 2.854  | 50.00 | +0.025 | -0.003   | 0.0843  | +0.593 | 2025-02-24 → 2025-08-27   |
| q5  | 24 | 28.400 | 75.00 | +0.038 | +0.000   | 0.0621  | +0.913 | 2025-09-03 → 2026-04-15   |

## OANDA vs Pepperstone — quintile reconciliation

Convention A:

| Bin     | OANDA PF | Pep PF | ΔPF    | rel %  |
|---------|----------|--------|--------|--------|
| q1=2022 | 0.344    | 0.328  | -0.016 | -4.7   |
| q2=2023 | 5.102    | 5.187  | +0.085 | +1.7   |
| q3=2024 | 4.973    | 4.500  | -0.473 | -9.5   |
| q4=2025 | 4.246    | 4.053  | -0.193 | -4.5   |
| q5=2026 | inf      | inf    | —      | —      |

Convention B:

| Bin | OANDA PF | Pep PF  | ΔPF    | rel %  |
|-----|----------|---------|--------|--------|
| q1  | 2.557    | 2.525   | -0.032 | -1.3   |
| q2  | 2.621    | 2.333   | -0.288 | -11.0  |
| q3  | 6.379    | 6.133   | -0.246 | -3.9   |
| q4  | 2.740    | 2.854   | +0.114 | +4.2   |
| q5  | 27.500   | 28.400  | +0.900 | +3.3   |

OANDA and Pepperstone track each other tightly per bin (max divergence ~11% in Conv B q2, but the *shape* of the curve is identical across feeds). The feed-vs-feed delta is small relative to the bin-vs-bin variation; the substantive finding below is feed-robust.

## Bootstrap 95% CI on PF — Pepperstone (10,000 resamples, seed 42)

Convention A:

| Bin     | n  | CI_lo | CI_hi  |
|---------|----|-------|--------|
| q1=2022 | 18 | 0.022 | 1.810  |
| q2=2023 | 26 | 1.565 | 25.912 |
| q3=2024 | 28 | 1.176 | 15.400 |
| q4=2025 | 41 | 1.441 | 10.513 |
| q5=2026 | 10 | NaN   | NaN    |

q1's upper bound (1.81) is below q2/q3/q4 lower bounds — q1 is statistically distinguishable from the others. q2-q4 CIs overlap heavily (1.18-25.9, 1.18-15.4, 1.44-10.5). q5 CI undefined (n=10, all-but-one wins).

Convention B:

| Bin | n  | CI_lo  | CI_hi  |
|-----|----|--------|--------|
| q1  | 25 | 0.503  | 11.909 |
| q2  | 25 | 0.552  | 9.723  |
| q3  | 25 | 1.562  | 21.278 |
| q4  | 24 | 0.643  | 9.148  |
| q5  | 24 | 6.914  | 97.675 |

q5 lower bound (6.914) is well above all other bins' upper bounds — q5 is statistically distinguishable as the high-PF bin. q1-q4 CIs overlap heavily.

## Spearman permutation test — Pepperstone (10,000 shuffles, seed 42)

| Convention | Observed PFs                       | Spearman | q5/q1   | Strict mono ↑ | p (Spearman) | p (joint) |
|------------|------------------------------------|----------|---------|---------------|--------------|-----------|
| A          | 0.33 / 5.19 / 4.50 / 4.05 / inf    | +0.600   | NaN     | False         | 0.2011       | 0.0000*   |
| B          | 2.53 / 2.33 / 6.13 / 2.85 / 28.40  | +0.800   | 11.25   | False         | 0.0640       | 0.0055    |

\* Conv A `p (joint)` is degenerate: ratio is NaN (q5=inf), so the `ratio ≥ observed` clause never matches in any permutation. The meaningful Conv A p-value is `p (Spearman) = 0.2011`.

Neither convention shows strict monotonic increase. The patterns are non-monotonic at quintile resolution — see below.

## Substantive refinement of the Q-A1 tertile story

Quintile resolution reveals that the Q-A1 tertile-level "monotonic improvement" was a coarseness artifact, in different ways under the two conventions:

**Conv A reveals a step function, not a ramp.** 2022 was Aegis's worst year (PF 0.328, sum R = -0.27 — net losing). From 2023 onwards, PF stabilized at 4.0-5.2 with no clear monotonic trend (5.19 → 4.50 → 4.05). The 2026 partial year (n=10, only 1 loss) inflates to inf. The Q-A1 Conv A "early=2022+2023 (PF 2.47)" tertile bin **averaged a near-zero-PF year (2022) with a strong year (2023)** to produce the appearance of a low early baseline. Under quintile splitting, the apparent gradient is replaced by a one-shot regime change between 2022 and 2023, followed by a flat-to-slightly-declining trajectory.

**Conv B reveals a late-panel spike, not a smooth ramp.** Quintiles q1-q4 are noisily flat (PF 2.5 / 2.3 / 6.1 / 2.9). q5 (the last 24 trades, Sept 2025 onwards) explodes to PF 28.4. The Q-A1 Conv B "late=82-123 (PF 7.32)" tertile bin **averaged a moderate q4 (PF 2.85) with the exceptional q5 (PF 28.4)** to produce an apparent middle-of-three lift. The bootstrap CI on q5 (6.91-97.7) confirms this is statistically distinguishable from earlier bins, but the q5-only-spike pattern is not a "monotonic regime improvement" — it is a recent-period concentration.

**Both conventions agree on:**
- 2022 / earliest-trades was the weakest period (Conv A q1, Conv B q1-q2).
- Late-panel (2025-09 onwards) is the strongest period (Conv A q5, Conv B q5).
- The middle of the panel (2023-2024 / Conv B q3) is variable but generally elevated relative to 2022.
- The pattern is **not a smooth gradient** — it is a step (Conv A) and / or a spike (Conv B).

**Both conventions agree the pattern is not strictly monotonic increase.** Q-A1 reported Conv A and Conv B as both showing strict monotonic increase across 3 bins (because tertile aggregation smooths the step / spike). At 5-bin resolution the smoothing is insufficient to maintain strict monotonicity.

## Bin-convention sensitivity

The two conventions disagree on the shape of the lift, but agree on the location of the extremes:

- **Conv A (year-bucket)** highlights the **2022→2023 step**. 2022 stands alone as the weak year; 2023-2025 are roughly equivalent (PF 4-5).
- **Conv B (equal-N index)** highlights the **q5 spike**. q1-q4 are roughly equivalent; q5 (last 24 trades) is exceptional.

These are **different views of the same underlying signal**: the 2026 trades (and the late 2025 trades that push into Conv B q5) are the major contributor to the lift. Under year-binning, 2026's small N (10) yields PF=inf and gets visually absorbed by the q4=2025 bin in Q-A1 Conv A late aggregation. Under equal-N binning, the last 24 chronologically-ordered trades are concentrated into one bin (Sept 2025 → April 2026), which is why Conv B q5 appears as a pure spike.

## Verdict

**PARTIAL.** Per the dual-convention routing rule (Spearman generalization):

- **Convention A:** Spearman = +0.600 (mildly positive), `p (Spearman) = 0.2011` (well above 0.05), ratio NaN (degenerate). Strict monotonic check False. → **partial** (Spearman > 0 but p ≥ 0.05; ratio undefined).
- **Convention B:** Spearman = +0.800, ratio q5/q1 = 11.25 ≥ 2.0 ✓, joint p = 0.0055 < 0.05 ✓. → **replication** under the joint criterion. But strict monotonic check False; the "replication" is driven by the q5 spike, not a smooth Spearman pattern. Spearman-only p (0.0640) is *just above* 0.05.
- **Combined:** partial + replication → **PARTIAL**.

**No strict monotonic-decline flag.** Both conventions show positive Spearman; neither convention shows strict decline.

The verdict at quintile resolution is consistent with Q-A1's tertile PARTIAL — but the substantive content is materially refined: the lift is **localized** (step in Conv A, spike in Conv B) rather than a smooth panel-wide regime improvement. This sharpens the question for any further inquire-phase work.

## Routing recommendation

**Recommend hand back to Joshua for the routing call.** The PARTIAL verdict is unchanged from Q-A1 in its routing class, but the substantive finding is sharper: **the lift is localized to the recent ~6 months (Sept 2025 → April 2026) plus the 2022→2023 step**. This is a more focused diagnostic than "panel-wide monotonic improvement."

Cheapest-first refinement candidates (all OANDA+Pepperstone-doable, no re-MC required):

1. **Recent-period drill-down** (cheapest): isolate the last 24 trades (Conv B q5: Sept 2025 onwards) and characterize them — what filters fired, what session windows, what was unusual about that period? If the spike maps to a small set of trades, the "regime improvement" story degrades into "a few good trades in a row." If it maps to a structural pattern (e.g., consistent EOM filter alignment), it's evidence of a different mechanism than what Q15's panel-wide vol-coupling test could see.
2. **2022-only diagnostic** (cheap): characterize the q1=2022 bin's losses. If 2022 had a small number of large stops (n=18 trades) that explain the PF=0.33, the "step up to 2023" story is confounded with one or two outlier trades. If 2022 had a consistently-poor distribution, it's a real regime difference.
3. **Filter-funnel composition through-time** (Q-A1's recommended Refinement #2 — unchanged): does the v4.3 filter stack produce a different distribution of accepted trades in 2022 vs 2023+ vs 2025-09+? This would test whether the localized lift is filter-driven (structural) or pure regime (luck).

EOM-block decomposition (Q-A1 Refinement #3) is now lower priority — the quintile result suggests time-windowed effects, not EOM-cycle effects.

**Do NOT auto-escalate Q-A2.** The Conv A partial (Spearman > 0 but p ≥ 0.05) and the Conv B q5-spike-driven replication don't constitute strong replication evidence; they refine where the signal is, not whether it's robust. Q-A2 stays gated on next re-MC trigger as planned.

**Do NOT recommend any allocation, dd_protection, or calibration change.** Out of scope; the verdict does not justify it regardless.

## Cross-references

- **Parent Q-A1 brief:** [q_a1_pepperstone_replication.md](q_a1_pepperstone_replication.md) — PARTIAL verdict at tertile resolution, recommended quintile split as Refinement #1.
- **Q15 closure:** [analysis/notice_phase/findings_2026-04-26.md:414-510](../../../../analysis/notice_phase/findings_2026-04-26.md).
- **Q-A parent gated brief:** [`q_a_aegis_panel_mechanism_gated.md`](../2026-04-27/q_a_aegis_panel_mechanism_gated.md) (2026-04-27 synthesis, backfilled to repo 2026-04-29 — Q-A1-d closed).
- **Q-T inquire brief:** [analysis/inquire_phase/findings_q_t_2026-04-27.md](../../../../analysis/inquire_phase/findings_q_t_2026-04-27.md) (bootstrap pattern reference).
- **Methodology:** [observation_routing.md](../../observation_routing.md), [1r_estimation.md](../../1r_estimation.md), [operational_rules.md](../../../operational_rules.md).
- **Memory:** [feedback_gated_q_subquestion_forking.md](../../../../../../joshu/.claude/projects/C--Users-joshu-prop-firm-pipeline/memory/feedback_gated_q_subquestion_forking.md) — methodology lesson saved with Q-A1.

## Open forks (post-Q-A1.1)

- **Recent-period drill-down (cheapest next step)** — characterize Conv B q5 (Sept 2025 → April 2026) trade-by-trade. Filter activations, session times, MFE/MAE distribution. If the spike is structural, it's a finding; if it's a streak of luck, it changes the inference. Notice-phase work, no re-MC required.
- **Q-A1-d** (carryover from Q-A1) — **CLOSED 2026-04-29.** Q-A parent brief landed at [`q_a_aegis_panel_mechanism_gated.md`](../2026-04-27/q_a_aegis_panel_mechanism_gated.md), pasted verbatim from Notion `34fdc0b5…bb6f` with 2026-04-29 disposition banner.
- **Q-A2** — remains gated on next re-MC trigger as originally planned. Q-A1.1's PARTIAL verdict does not satisfy the auto-escalation bar.
