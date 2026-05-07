# Q-A1 — Aegis Pepperstone Panel-Thirds Replication Test

**Date:** 2026-04-29
**Author:** Claude (Opus 4.7)
**Type:** Decision brief — analysis only, no code/allocation/dd_protection touch
**Verdict:** **PARTIAL**
**Routing:** Return to corpus inquire with refined question; do NOT auto-escalate Q-A2.

## Parent / dependencies

- **Parent question:** Q-A — does the Aegis OANDA panel-thirds PF lift (2.46 → 4.97 → 5.96) reflect real regime structure or an OANDA-proxy artefact? Parent brief: [`q_a_aegis_panel_mechanism_gated.md`](../2026-04-27/q_a_aegis_panel_mechanism_gated.md) (2026-04-27 synthesis, backfilled 2026-04-29 — Q-A1-d closed).
- **Q15 closure (anchor for the OANDA reference numbers):** [findings_2026-04-26.md:414-510](../../../../analysis/notice_phase/findings_2026-04-26.md), specifically the panel-wide P&L sub-period table at lines 463-468.
- **Methodology references:** [observation_routing.md](../../observation_routing.md), [1r_estimation.md](../../1r_estimation.md), [operational_rules.md](../../../operational_rules.md).
- **Data files (canonical, on disk):**
  - Pepperstone: `data/tv_exports/pepperstone/Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-04-26_0bf1b.csv`
  - OANDA reference: `data/tv_exports/oanda/Aegis_USDJPY_v4.3_OANDA_USDJPY_2026-04-25_7ee6b.csv`
- **Analysis script:** [analysis/notice_phase/q_a1_aegis_pepperstone_panel.py](../../../../analysis/notice_phase/q_a1_aegis_pepperstone_panel.py)

## Rule 0 reconciliation — PASS

Pepperstone Aegis canonical vs locked v4.3 header (2026-04-23):

| Field          | Locked v4.3   | Observed       | Result |
|----------------|---------------|----------------|--------|
| Trades         | 123           | 123            | PASS (exact) |
| PF (USD-based) | 4.186         | 4.186          | PASS (within ±0.01) |
| PF (R-based)   | —             | 3.711          | informational; rounded `Net P&L %` (2 decimals) loses precision; per-third PFs use R-multiples to match Q15 method |
| Win rate       | 60.16%        | 60.16%         | PASS |
| Net P&L USD    | $178,208      | $178,208 (sum of `Net P&L USD` column) | matches locked figure exactly. The earlier exploration's "2× delta" reading was an artefact of a different read path; resolved here. See *Pipeline integrity observations* below. |
| Date range     | 2022-01-04 → 2026-04-20 | trade entries 2022-01-12 → 2026-04-15 | PASS (inside locked data window) |
| Symbol / TF    | USDJPY 15m    | USDJPY 15m     | PASS |

**Status:** PASS — proceed.

## Pipeline integrity observations

**Net P&L USD reconciliation note.** During pre-flight exploration the Pepperstone CSV's `Net P&L USD` column appeared to sum to ~$356K (2× the locked $178K). When recomputed inside the analysis script via the same `load_tv_feed()` entry/exit pivot, the column sums to exactly $178,208. The earlier reading double-counted the column by aggregating both Entry-row and Exit-row copies (TV exports duplicate trade-level fields onto both rows of each Exit/Entry pair); the script's de-duplication via `df[df["Type"] == "Exit long"]` resolves this. **No actual data discrepancy. Q-A1-c fork is closed by inspection** — the original concern was an artefact of a one-off ad-hoc read, not a Pepperstone-vs-OANDA convention difference. (OANDA, loaded via the same code path, also reconciles cleanly.)

**Net P&L % rounding caveat.** TV exports `Net P&L %` to 2 decimals. Many small wins/losses round to 0.00 even when `Net P&L USD` is non-zero. Consequence: PF computed from R-multiples (`net_pnl_pct / risk_pct`) on the whole panel reads 3.711 vs the USD-based 4.186 — a precision artefact, not a data integrity issue. Per-third PFs in §5–§7 below use R-multiples (matching Q15's method, by which `2.46 / 4.97 / 5.96` were reported). The Rule 0 gate uses USD-based PF (matches TV's headline number).

## Panel-split convention — boundaries

**Convention A — calendar-year buckets (Q15-faithful).** `early ∈ {2022, 2023}`, `mid == 2024`, `late ∈ {2025, 2026}`. The plan's wording was "chronological time-thirds derived from OANDA range," but Q15's actual method as published in [findings_2026-04-26.md:463-468](../../../../analysis/notice_phase/findings_2026-04-26.md) was calendar-year groupings yielding n=44/28/51 on OANDA. Year-buckets is what reproduces 2.46/4.97/5.96, so we matched the published Q15 method. Year-bucket boundaries are absolute and feed-independent, so applied identically to both feeds.

**Convention B — equal-N trade-index thirds.** Sort by entry time, split `[0:41] / [41:82] / [82:123]` (floor(123/3) = 41 per third, no remainder). Applied to both feeds.

| Convention | Feed       | early                          | mid                            | late                           |
|------------|------------|--------------------------------|--------------------------------|--------------------------------|
| A          | OANDA      | n=44, 2022-01-12 → 2023-12-27  | n=28, 2024-01-08 → 2024-12-23  | n=51, 2025-02-03 → 2026-04-15  |
| A          | Pepperstone| n=44, 2022-01-12 → 2023-12-27  | n=28, 2024-01-08 → 2024-12-23  | n=51, 2025-02-03 → 2026-04-15  |
| B          | OANDA      | idx [0:41], 2022-01-12 → 2023-11-01 | idx [41:82], 2023-11-13 → 2025-04-08 | idx [82:123], 2025-04-16 → 2026-04-15 |
| B          | Pepperstone| idx [0:41], 2022-01-12 → 2023-11-01 | idx [41:82], 2023-11-13 → 2025-04-08 | idx [82:123], 2025-04-16 → 2026-04-15 |

OANDA and Pepperstone trade entry-times are tightly aligned (both feeds running the same Pine v4.3 strategy on equivalent USDJPY 15m bars) — the per-third date ranges match almost exactly across feeds, both conventions.

## Self-test — OANDA Convention A reproduces Q15 anchor

Prerequisite: before any Pepperstone result is read, OANDA Convention A must reproduce Q15's published 2.46 / 4.97 / 5.96 to within ±0.005 per per-third PF. This catches loader / return-convention / boundary-derivation bugs.

| Third            | Observed | Q15 anchor | \|delta\| | Result |
|------------------|----------|------------|-----------|--------|
| early_2022_2023  | 2.464    | 2.46       | 0.0036    | PASS   |
| mid_2024         | 4.973    | 4.97       | 0.0030    | PASS   |
| late_2025_2026   | 5.965    | 5.96       | 0.0049    | PASS   |

n per third (OANDA): 44 / 28 / 51 — exact match with Q15. **Self-test PASS.**

## Per-third metrics — Pepperstone Convention A (calendar-year buckets)

| Third  | n   | PF    | WR%   | mean R  | median R | ret_std | sum R  | date range                |
|--------|-----|-------|-------|---------|----------|---------|--------|---------------------------|
| early  | 44  | 2.468 | 61.36 | +0.024  | +0.000   | 0.0972  | +1.067 | 2022-01-12 → 2023-12-27   |
| mid    | 28  | 4.500 | 53.57 | +0.032  | +0.000   | 0.0894  | +0.887 | 2024-01-08 → 2024-12-23   |
| late   | 51  | 5.561 | 62.75 | +0.034  | +0.000   | 0.0780  | +1.733 | 2025-02-03 → 2026-04-15   |

## Per-third metrics — Pepperstone Convention B (equal-N trade-index)

| Third  | n   | PF    | WR%   | mean R  | median R | ret_std | sum R  | date range                |
|--------|-----|-------|-------|---------|----------|---------|--------|---------------------------|
| early  | 41  | 2.535 | 60.98 | +0.025  | +0.000   | 0.0985  | +1.013 | 2022-01-12 → 2023-11-01   |
| mid    | 41  | 3.620 | 53.66 | +0.030  | +0.000   | 0.0907  | +1.240 | 2023-11-13 → 2025-04-08   |
| late   | 41  | 7.324 | 65.85 | +0.035  | +0.000   | 0.0724  | +1.433 | 2025-04-16 → 2026-04-15   |

## OANDA vs Pepperstone reconciliation — Convention A

| Third  | OANDA n | OANDA PF | PEP n | PEP PF | ΔPF    | rel %  |
|--------|---------|----------|-------|--------|--------|--------|
| early  | 44      | 2.464    | 44    | 2.468  | +0.004 | +0.2   |
| mid    | 28      | 4.973    | 28    | 4.500  | -0.473 | -9.5   |
| late   | 51      | 5.965    | 51    | 5.561  | -0.404 | -6.8   |

ret_std comparison (OANDA vs Pepperstone, per third): early 0.0977 vs 0.0972, mid 0.0895 vs 0.0894, late 0.0782 vs 0.0780 — feed-level dispersion is essentially identical.

## OANDA vs Pepperstone reconciliation — Convention B

| Third  | OANDA n | OANDA PF | PEP n | PEP PF | ΔPF    | rel %  |
|--------|---------|----------|-------|--------|--------|--------|
| early  | 41      | 2.540    | 41    | 2.535  | -0.005 | -0.2   |
| mid    | 41      | 3.899    | 41    | 3.620  | -0.279 | -7.2   |
| late   | 41      | 7.771    | 41    | 7.324  | -0.448 | -5.8   |

Pattern: feed difference is small in the early third (≤0.2% in either convention), modest in mid (~7-9% Pepperstone-lower), and modest in late (~6-7% Pepperstone-lower). The shape replicates; the absolute level on Pepperstone is uniformly slightly weaker than OANDA in the mid+late thirds.

## Bootstrap 95% CI on PF — Pepperstone only (10,000 resamples, seed 42)

Convention A:

| Third  | n   | CI_lo  | CI_hi  |
|--------|-----|--------|--------|
| early  | 44  | 0.861  | 7.058  |
| mid    | 28  | 1.176  | 15.400 |
| late   | 51  | 2.400  | 14.042 |

Convention B:

| Third  | n   | CI_lo  | CI_hi  |
|--------|-----|--------|--------|
| early  | 41  | 0.801  | 7.882  |
| mid    | 41  | 1.296  | 8.740  |
| late   | 41  | 2.589  | 26.501 |

CIs are wide (n per third 28-51; PF is highly nonlinear in tail outcomes). **Early-third upper bound overlaps mid-third and late-third lower bounds in both conventions** — meaning the per-third PF point estimates are not statistically distinguishable from each other under bootstrap resampling alone. The discriminating evidence has to come from the monotonic ordering across all three thirds simultaneously, which is what the permutation test addresses.

## Monotonicity permutation test — Pepperstone only (10,000 shuffles, seed 42)

H0: trade-level R i.i.d. across panel (no epoch effect). Test statistic: fraction of shuffled assignments that yield monotonic increase AND PF_late/PF_early ≥ observed ratio.

| Convention | observed PFs            | mono inc | ratio | p-value |
|------------|-------------------------|----------|-------|---------|
| A          | 2.468 / 4.500 / 5.561   | True     | 2.254 | 0.0667  |
| B          | 2.535 / 3.620 / 7.324   | True     | 2.889 | 0.0559  |

Both conventions show monotonic increase with ratio > 2.0, but neither permutation p-value crosses the strict 0.05 threshold. p ≈ 0.06 in both cases — directionally suggestive but not significant under a conventional cutoff.

## Bin-convention sensitivity

Both conventions agree on the qualitative pattern (monotonic increase, ratio > 2.0, perm p marginally above 0.05). They disagree on:

- **Magnitude of the lift.** Conv B gives a steeper lift (PF_late/PF_early = 2.89) than Conv A (2.25). This is because Conv B's late third is composed of the most recent 41 trades, while Conv A's late third (n=51) includes the early-2025 trades that are not yet in B's late third.
- **Mid-third PF.** Conv A mid = 4.50; Conv B mid = 3.62. Conv A's mid is a calendar-year-pure 2024 cohort; Conv B's mid spans late-2023 through early-2025, smearing across the year boundary.
- **Permutation p.** Conv B's p (0.0559) is marginally more decisive than Conv A's (0.0667) — both conventions are consistent in being just above the 0.05 cutoff.

The pattern is **convention-robust at the qualitative level** and **convention-sensitive at the quantitative level**. This means:

1. The OANDA Q15 published numbers (2.46 / 4.97 / 5.96 on the year-bucket convention) are themselves convention-sensitive — under equal-N trade-index thirds (B), OANDA reads 2.54 / 3.90 / 7.77, a different shape with the same monotonic-increase signal.
2. Neither convention rejects the artefact hypothesis at the standard p<0.05 cutoff on Pepperstone, despite the visually strong monotonic pattern. The small N per third (28-51) is the binding constraint.

## Verdict

**PARTIAL.** Per the dual-convention routing rule:

- Convention A: monotonic increase ✓, ratio 2.25 ≥ 2.0 ✓, perm p 0.0667 ≥ 0.05 ✗ → **partial** (replication criteria fail on p-value alone)
- Convention B: monotonic increase ✓, ratio 2.89 ≥ 2.0 ✓, perm p 0.0559 ≥ 0.05 ✗ → **partial**
- Combined → **PARTIAL**

**No monotonic-decline flag.** Both conventions show monotonic increase on Pepperstone — Q15's published direction is qualitatively reproduced, just below the strict-significance threshold.

The signal on Pepperstone is qualitatively consistent with Q15's OANDA result. The strict permutation-p criterion fails by a narrow margin in both conventions (0.06 vs 0.05 cutoff), against the noise floor of small per-third N. This is exactly the regime where the spec's "PARTIAL" class is engineered to land — directionally suggestive but below the falsification bar. Auto-escalating to Q-A2 on this evidence would over-commit; archiving Q-A on this evidence would under-commit.

## Routing recommendation

**Return to corpus inquire with a refined question.** Specific candidate refinements (cheapest-first, all OANDA+Pepperstone-doable, no re-MC required):

1. **Quintile split** — recompute per-quintile PF on Pepperstone (n ≈ 24-25 per quintile). Asks whether the monotonic pattern holds at finer resolution. Cheapest; same data, same loader.
2. **Filter-funnel composition through-time** — does the v4.3 filter stack (block hours, EOM filter, BB envelope) produce a *different distribution of accepted trades* in late-panel vs early-panel? If yes, the late-panel PF lift is structural (driven by stricter filter alignment) rather than regime-driven. Touches the [o5_filter_contribution_2026_04_27.py](../../../../analysis/notice_phase/o5_filter_contribution_2026_04_27.py) machinery — adapt to per-cohort.
3. **EOM-block decomposition** — Q15's first speculative mechanism candidate (`findings_2026-04-26.md:474-475`). Test whether removing EOM trades from each third changes the PF lift profile.

**Do NOT auto-escalate Q-A2 (epoch-conditioned bootstrap stress-test).** The evidence does not meet the spec's REPLICATION CONFIRMED bar (perm p < 0.05 in both conventions). Q-A2 remains gated on next re-MC trigger as originally planned.

**Do NOT recommend any allocation, dd_protection, or calibration change.** Out of scope for Q-A1 by spec; the verdict does not justify it regardless.

## Cross-references

- **Q15 closure:** [analysis/notice_phase/findings_2026-04-26.md:414-510](../../../../analysis/notice_phase/findings_2026-04-26.md) — the OANDA panel-thirds anchor (2.46 / 4.97 / 5.96) and its `Forward → Closed (post-Q15)` routing.
- **04-26 corpus synthesis:** same file — the Notice-phase synthesis that produced Q15.
- **Q-T inquire-phase brief:** [analysis/inquire_phase/findings_q_t_2026-04-27.md](../../../../analysis/inquire_phase/findings_q_t_2026-04-27.md) — bootstrap pattern reference (seed 42, 10K resamples).
- **Q-A parent gated brief:** [`q_a_aegis_panel_mechanism_gated.md`](../2026-04-27/q_a_aegis_panel_mechanism_gated.md) (2026-04-27 synthesis, backfilled to repo 2026-04-29 — Q-A1-d closed).
- Methodology: [docs/methodology/observation_routing.md](../../observation_routing.md), [docs/methodology/1r_estimation.md](../../1r_estimation.md), [docs/operational_rules.md](../../../operational_rules.md).

## Open forks (post-Q-A1)

- **Q-A1-c — Net P&L USD column-convention diagnostic:** **CLOSED by inspection.** Pre-flight exploration's "2× delta" was a one-off read-path artefact, not a Pepperstone-specific column-convention issue. The script's `load_tv_feed()` reconciles exactly to the locked $178,208. No follow-up needed.
- **Q-A1-d — Backfill 2026-04-27 Q-A parent brief: CLOSED 2026-04-29.** The gated Q-A synthesis is now on disk at [`q_a_aegis_panel_mechanism_gated.md`](../2026-04-27/q_a_aegis_panel_mechanism_gated.md) — pasted verbatim from Notion `34fdc0b5…bb6f` with a 2026-04-29 disposition banner reflecting the Q-A1 chain's PARTIAL outcome and forward-tripwire routing.
- **Methodology lesson — gated-Q sub-question forking discipline:** when a parent question has both gated and ungated components, fork the ungated as a sub-question runnable on existing data without waiting for the gate. Q-A1 is the worked example: Q-A's gated component (Pepperstone re-MC) waits, but the panel-thirds replication test runs immediately on already-on-disk Pepperstone canonical. Saved to memory.
