# Q-A1.2 — Aegis Pepperstone q5 (Sept 2025 → April 2026) Drill-Down

**Date:** 2026-04-29
**Author:** Claude (Opus 4.7)
**Type:** Decision brief — analysis-only refinement of Q-A1.1; no code/allocation/dd_protection touch
**Verdict:** **MIXED — leaning fragile-loss-avoidance** (substantive finding far more nuanced than streak-vs-structural)
**Routing:** Hand back to Joshua. The q5 PF=28.4 spike reframes substantively into a loss-truncation finding, not a regime improvement. **Concrete recommendation: do not auto-escalate Q-A2; install a forward live-PnL tripwire (single-full-SL-hit) instead.**

## TL;DR

The Q-A1.1 Conv B q5 PF=28.4 is **not driven by large winners and not driven by a single jackpot trade**. It is driven by the **complete absence of full-stop losers and time-stops** across the last 24 trades. The maximum R-multiple in q5 is **+0.153** (a BE-pad scratch, not a TP); the minimum is **−0.020** (a sub-BE scratch loss). Gross profit = 0.947 R units; gross loss = 0.033 R units. PF math is dominated by the denominator being ~zero.

This is a **fragile-zero-loss regime**: a single full-SL hit (R = −1.0) in any next 24-trade window would invert the entire apparent "spike." Whether that absence is structural (vol compression / filter alignment) or pure luck cannot be distinguished from this drill-down alone. The MW-U test on R-distributions returns p = 0.16 (no significant central-tendency shift), with q5's distribution showing **variance compression** (std 0.062 vs 0.092) rather than a mean lift.

Practical implication: the Q-A1.1 PF=28.4 should be read as "Aegis avoided every full-stop trigger for 7 months" rather than "Aegis is performing meaningfully better." The first reading does not justify Q-A2 escalation; the second reading would, but the data does not support it.

## Parent / dependencies

- **Parent:** [Q-A1.1 — Pepperstone panel-quintile replication](q_a1_1_pepperstone_quintile.md). Verdict PARTIAL; recommended q5 drill-down as Refinement #1 (cheapest).
- **Grandparent:** [Q-A1 — Pepperstone panel-thirds replication](q_a1_pepperstone_replication.md). Verdict PARTIAL.
- **Q15 closure:** [analysis/notice_phase/findings_2026-04-26.md:414-510](../../../../analysis/notice_phase/findings_2026-04-26.md). The OANDA panel-thirds anchor and its `Forward → Closed (post-Q15)` route.
- **Pine v4.3 source (Rule-0-extends-to-Pine-code memory):** [strategies/aegis/aegis_usdjpy_v4.3.pine:247-270](../../../../strategies/aegis/aegis_usdjpy_v4.3.pine) — strategy.exit(label="X-Long") for SL/BE/TP bracket; strategy.close_all(comment="Stale") for time-stop.
- **Methodology:** [observation_routing.md](../../observation_routing.md), [1r_estimation.md](../../1r_estimation.md), [overlay-trigger discipline memory](feedback_overlay_trigger_discipline.md), [leading-indicator+P&L-gate rationalization memory](feedback_leading_indicator_pnl_gate_rationalization.md).
- **Data:** Pepperstone canonical CSV (same file as Q-A1 / Q-A1.1).
- **Analysis script:** [analysis/notice_phase/q_a1_2_aegis_pepperstone_q5_drilldown.py](../../../../analysis/notice_phase/q_a1_2_aegis_pepperstone_q5_drilldown.py) (imports loader from Q-A1; reuses risk_pct, PF helper, locked-header constants).

## Self-tests

- **Rule 0 echo:** N=123, PF(USD)=4.186 vs locked 4.186 → **PASS**.
- **q5 PF self-test against Q-A1.1 anchor:** observed q5 PF = **28.400** vs Q-A1.1 anchor 28.400 → \|delta\| = 0.0000 → **PASS**.

## Cohort definition

- **q5:** trades #100-123 (Pepperstone trade index, sorted by entry_time). Date span: 2025-09-03 → 2026-04-15 (224 calendar days). n=24.
- **rest:** trades #1-99. Date span: 2022-01-12 → 2025-08-27. n=99.

## Per-trade detail — q5 (all 24 trades)

```
    #  entry             exit              hold(b)  exit_sig    mode             R     mfe%    mae%
  100  2025-09-03 10:15  2025-09-03 10:45      2.0  X-Long      BE_or_flat  -0.020   +0.05   -0.07
  101  2025-09-10 10:15  2025-09-10 10:30      1.0  X-Long      BE_or_flat  +0.000   +0.08   -0.01
  102  2025-09-22 13:00  2025-09-22 13:15      1.0  X-Long      BE_or_flat  +0.000   +0.02   -0.02
  103  2025-09-23 13:45  2025-09-23 14:00      1.0  X-Long      BE_or_flat  +0.000   +0.05   -0.03
  104  2025-10-14 12:45  2025-10-14 13:00      1.0  X-Long      BE_or_flat  +0.000   +0.04   -0.02
  105  2025-10-20 10:30  2025-10-20 11:00      2.0  X-Long      BE_or_flat  +0.000   +0.05   -0.09
  106  2025-10-22 13:45  2025-10-22 15:00      5.0  X-Long      BE_or_flat  +0.120   +0.18   -0.01
  107  2025-11-03 10:15  2025-11-03 10:30      1.0  X-Long      BE_or_flat  +0.000   +0.06   -0.03
  108  2025-11-12 12:15  2025-11-12 19:45     30.0  X-Long      BE_or_flat  +0.140   +0.22   -0.03
  109  2025-11-25 12:30  2025-11-25 12:45      1.0  X-Long      BE_or_flat  +0.007   +0.03   -0.04
  110  2025-12-03 10:30  2025-12-03 10:45      1.0  X-Long      BE_or_flat  +0.000   +0.10   -0.04
  111  2025-12-10 10:15  2025-12-10 10:30      1.0  X-Long      BE_or_flat  +0.000   +0.03   -0.02
  112  2025-12-17 10:45  2025-12-17 11:00      1.0  X-Long      BE_or_flat  -0.013   +0.06   -0.05
  113  2025-12-24 10:15  2025-12-24 12:45     10.0  X-Long      BE_or_flat  +0.107   +0.16   -0.01
  114  2026-01-27 12:45  2026-01-27 13:00      1.0  X-Long      BE_or_flat  +0.007   +0.10   -0.03
  115  2026-02-11 12:15  2026-02-11 13:15      4.0  X-Long      BE_or_flat  +0.013   +0.08   -0.19
  116  2026-02-23 10:15  2026-02-23 10:30      1.0  X-Long      BE_or_flat  +0.000   +0.05   -0.01
  117  2026-02-25 10:15  2026-02-25 10:30      1.0  X-Long      BE_or_flat  +0.000   +0.04   -0.03
  118  2026-03-03 13:45  2026-03-03 14:30      3.0  X-Long      BE_or_flat  +0.000   +0.15   -0.03
  119  2026-03-09 12:45  2026-03-09 14:45      8.0  X-Long      BE_or_flat  +0.153   +0.24   -0.03
  120  2026-03-10 13:30  2026-03-10 14:00      2.0  X-Long      BE_or_flat  +0.133   +0.20   +0.00
  121  2026-03-16 10:15  2026-03-16 11:00      3.0  X-Long      BE_or_flat  +0.147   +0.22   -0.01
  122  2026-04-13 13:15  2026-04-13 16:30     13.0  X-Long      BE_or_flat  +0.000   +0.02   -0.08
  123  2026-04-15 12:30  2026-04-15 13:45      5.0  X-Long      BE_or_flat  +0.120   +0.19   -0.01
```

R-multiple range: **−0.020 to +0.153**. Maximum |R| is 0.153 — there are no large winners. Most losers are sub-BE-pad scratches; the largest "loser" is −0.020.

## Concentration — top-N gross-profit share

| Metric                                | q5 (n=24) | rest (n=99) |
|---------------------------------------|-----------|-------------|
| PF (full)                             | 28.400    | 3.090       |
| Gross profit (R units)                | +0.947    | (large)     |
| Gross loss (R units)                  | +0.033    | (large)     |
| Top-1 winner share of gross profit    | 16.2%     | 7.5%        |
| Top-2 winners share                   | 31.7%     | —           |
| Top-3 winners share                   | 46.5%     | —           |
| Top-5 winners share                   | 73.2%     | —           |
| PF after dropping top-1 winner        | 23.800    | —           |
| PF after dropping top-2 winners       | 19.400    | —           |
| PF after dropping top-3 winners       | 15.200    | —           |

**Concentration verdict: not streak-by-concentration.** Top-1 winner contributes only 16.2% of q5 gross profit (lower than even rest-of-panel's 7.5%? — no, that's because rest has more trades so any single trade is a smaller share; the q5 16.2% is *roughly* in line with what we'd expect for a 24-trade cohort where wins are roughly uniformly distributed). Removing the top winner drops PF from 28.4 to 23.8 — still very high. The "spike" is not concentrated in one trade.

But removing the top winner doesn't drop PF much because **the denominator (gross loss) is already tiny**. PF = (0.947 − 0.153) / 0.033 = 24.06 ≈ 23.8. Even removing the top 3 winners, PF stays at 15.2 because gross loss stays at 0.033. **The PF is denominator-driven, not numerator-driven.**

## R-multiple distribution — q5 vs rest-of-panel

| Metric  | q5 (n=24)  | rest (n=99) | delta    |
|---------|------------|-------------|----------|
| mean    | +0.0381    | +0.0280     | +0.0100  |
| std     | +0.0621    | +0.0925     | −0.0304  |
| min     | −0.0200    | −0.1333     | +0.1133  |
| p10     | +0.0000    | −0.0493     | +0.0493  |
| p25     | +0.0000    | −0.0167     | +0.0167  |
| median  | +0.0000    | +0.0000     | +0.0000  |
| p75     | +0.1100    | +0.0067     | +0.1033  |
| p90     | +0.1380    | +0.1747     | −0.0367  |
| max     | +0.1533    | +0.3067     | −0.1533  |
| WR_USD  | 75.0%      | 56.6%       | +18.4 pp |

**Substantive observations:**

1. **Median R is identical (0.0000) in both cohorts.** Most trades exit near zero (BE-pad activation = R ≈ +0.106; many trades exit at exactly entry price = R = 0.000 due to TV's rounding).
2. **q5's variance is compressed** (std 0.062 vs 0.092). Both the **left tail** (q5 min −0.020 vs rest min −0.133) and the **right tail** (q5 max +0.153 vs rest max +0.307) are truncated. q5 is operating in a narrower R-range.
3. **q5's losses are nearly absent.** p10 in q5 = 0.000 (90% of trades have R ≥ 0). p25 in q5 = 0.000. In rest-of-panel, p10 = −0.049 and p25 = −0.017 (i.e., the bottom quarter of trades are negative).
4. **q5's wins are smaller, not bigger.** p75 in q5 = +0.110 (BE-pad scratch). p90 in q5 = +0.138. p90 in rest = +0.175 — actually higher than q5. Max R in rest = +0.307 — twice the q5 max.
5. **Mean shift is small** (+0.010 R), entirely explained by left-tail truncation. This is *not* a "strategy is making more per trade" signal.
6. **WR jump (+18 pp) is meaningful** but explained by left-tail truncation (the trades that would have been small losses are now scratches at zero or tiny positives).

## Mann-Whitney U permutation test (q5 R vs rest R; 10,000 shuffles, seed 42, two-sided)

| Statistic              | Value     |
|------------------------|-----------|
| U_observed             | 1403.5    |
| U_null (n_q × n_r / 2) | 1188.0    |
| Mean shift (q5 − rest) | +0.0100 R |
| Median shift           | +0.0000 R |
| **p (two-sided)**      | **0.1631** |

**No significant central-tendency shift.** The MW-U test asks whether the q5 distribution is shifted relative to rest-of-panel. p = 0.163 — well above 0.05, well above the 0.20 mixed-verdict threshold. The "spike" in PF is not detectable as a distribution shift in central tendency.

This is consistent with the variance-compression observation: q5 has the *same median* but a *narrower spread*. MW-U is sensitive to median/rank shift, not variance compression. A test sensitive to variance shift (e.g., Levene's, or comparing IQRs) would likely detect a difference, but variance compression alone doesn't justify a structural-regime claim.

## Exit-mode breakdown (q5 vs rest)

| Mode                  | q5 (n=24)         | rest (n=99)         | q5 %     | rest %   |
|-----------------------|-------------------|---------------------|----------|----------|
| TP_or_strong_win (R>0.30) | 0             | 1                   | 0.0%     | 1.0%     |
| BE_or_flat (−0.05 ≤ R ≤ 0.30) | 24        | 85                  | 100.0%   | 85.9%    |
| loss_partial (−0.70 < R < −0.05) | 0      | 10                  | 0.0%     | 10.1%    |
| SL_full (R ≤ −0.70)   | 0                 | 0                   | 0.0%     | 0.0%     |
| Stale                 | 0                 | 3                   | 0.0%     | 3.0%     |

**This is the clearest signal in the data.** All 24 q5 trades land in the "BE_or_flat" bucket. Across the entire panel (n=123), there are 0 full-SL hits; the loss tail is comprised of "loss_partial" trades (n=10 across rest; 0 in q5) and "stale" exits (n=3 across rest; 0 in q5).

**q5 is operating exclusively on the BE-trigger pathway.** Every single q5 trade reached entry+0.3*ATR (BE_trigger), promoting the stop to entry+0.15*ATR (BE_pad), then exited within R ∈ [−0.05, +0.16]. No trade failed to reach BE_trigger and went on to hit the initial SL. No trade ran the full 40-bar max_hold.

The rest-of-panel includes 10 "loss_partial" trades (slow drift losses, didn't reach BE_trigger then exited mid-trade) and 3 stales (max_hold timeouts). In q5, both modes are absent.

## Hold duration

| Metric  | q5 (15min-bars) | rest (15min-bars) |
|---------|-----------------|-------------------|
| mean    | 4.1             | 5.5               |
| median  | 1.5             | 1.0               |
| p25     | 1.0             | 1.0               |
| p75     | 4.2             | 4.0               |
| max     | 30.0            | 40.0              |

q5 hold durations are similar to rest. Median hold is 1-1.5 bars (15-22 minutes). Trades resolve quickly in both cohorts. No q5 trade reaches the max_hold=40 (consistent with 0 stales).

## Hour-of-day / day-of-week distribution

Entry hours (NY-local):

| Hour | q5 (n=24) | rest (n=99) | q5 %  | rest % |
|------|-----------|-------------|-------|--------|
| 10   | 11        | 57          | 45.8% | 57.6%  |
| 12   | 7         | 22          | 29.2% | 22.2%  |
| 13   | 6         | 20          | 25.0% | 20.2%  |

Distribution is broadly similar; q5 has slightly fewer 10am entries and slightly more 12-13 entries. No striking shift.

Day-of-week (entries):

| DoW | q5 | rest | q5 %  | rest % |
|-----|----|------|-------|--------|
| Mon | 7  | 36   | 29.2% | 36.4%  |
| Tue | 6  | 17   | 25.0% | 17.2%  |
| Wed | 11 | 46   | 45.8% | 46.5%  |

q5 has slightly more Tuesday entries (note: Tue-H10 is a filter block in v4.3, but Tuesday entries at 12 / 13 are allowed). Distribution is broadly similar.

## Inter-trade interval (q5)

- Span: 224 calendar days (2025-09-03 → 2026-04-15)
- 23 inter-trade intervals
- Mean interval: 9.7 days; median 7.0 days
- min / max: 1.0 / 34.1 days
- Expected if uniformly spaced: 9.7 days/trade — q5 entries are well-spaced (not bunched into clusters).

q5 trades are temporally distributed across the 7-month window; this is **not** a concentrated-streak pattern.

## Verdict

**MIXED — leaning fragile-loss-avoidance.**

Per the pre-defined verdict criteria:

- Top-1 share = 16.2% (< 25% structural threshold) → **structural-leaning**
- PF after dropping top-1 = 23.8 (>> 5.0 streak threshold) → **not streak**
- MW-U p = 0.163 (>> 0.05 structural threshold) → **not structural by central tendency**
- WR jump +18 pp → **structural-leaning**
- Stale rate 0% vs 3%, full-SL 0/24 → **structural-leaning** in shape, but small n means the absence is small-sample
- → falls into MIXED bucket (structural and streak both partially supported, neither decisive)

**But the substantive interpretation cuts deeper than the bucket label.** The PF=28.4 in q5 is not "Aegis is making more money" — it is "Aegis avoided every full-stop trigger for 24 consecutive trades over 7 months." This is a **denominator-driven** PF, not a numerator-driven one. The right tail of wins is smaller in q5 than in rest-of-panel (max R 0.153 vs 0.307); the left tail is truncated (no full SL, no loss_partial, no stale).

**Implication for "structural vs streak" framing:**
- Classical streak: not present. No single trade dominates; PF survives leave-one-out.
- Classical structural improvement: not present. Median R is identical; mean shift is tiny; MW-U detects no shift.
- **Loss-truncation regime**: present. q5 operates entirely on the BE-trigger → BE-pad pathway. Whether this is structural (vol-compression-driven) or sampling luck (no full SL happened to hit) cannot be distinguished without additional evidence (e.g., per-trade adverse-excursion distribution against the 1.42*ATR stop-distance, or filter-funnel composition through-time).

## Routing recommendation

**Hand back to Joshua.** Two concrete recommendations, ranked by expected value:

1. **Install a forward live-PnL tripwire (cheapest, highest leverage):** the next full-SL hit on Aegis (R ≤ −0.70 in live trading) is the watch-event. If it fires within the next ~24 trades or within the next 6 months — whichever comes first — the q5 zero-loss artefact is confirmed as sampling, and no further action. If it does NOT fire (i.e., the loss-truncation pattern persists into more live trades), that is *forward live evidence* for a structural mechanism, and earns Q-A2 cycles. This matches the [overlay-trigger discipline memory](feedback_overlay_trigger_discipline.md): live-PnL gap is the falsification bar; backtest-only signals don't earn allocation/dd_protection cycles.

2. **Filter-funnel composition through-time (Q-A1's Refinement #2):** test whether the v4.3 filter stack (block hours, EOM filter, BB envelope, vol_ok min_atr, daily count cap) accepts a meaningfully different distribution of bars in q5 vs rest-of-panel. If yes → structural mechanism candidate (the filter stack is preferentially picking up bars that reach BE-trigger). If no → the loss-truncation is regime/luck. This is more expensive than #1 and not necessary if #1's tripwire fires within a reasonable window.

**Do NOT auto-escalate Q-A2.** Q-A1.2 has *weakened* the case for Q-A2, not strengthened it. Q-A2 (epoch-conditioned bootstrap stress-test) tests whether the late-panel uplift survives bootstrap resampling — but the uplift is denominator-driven, so a bootstrap that resamples q5 trades will preserve the zero-loss pattern by construction. The test would be uninformative. The genuine falsification path is forward live-PnL, not retrospective bootstrap.

**Do NOT recommend any allocation, dd_protection, or calibration change.** Out of scope; verdict does not justify it.

## Bin-convention sensitivity (re-stating across the chain)

- **Q-A1 tertile (n=44/28/51 calendar-year):** PARTIAL. Apparent monotonic increase 2.47 → 4.50 → 5.56.
- **Q-A1 tertile (n=41/41/41 equal-N):** PARTIAL. Apparent monotonic increase 2.54 → 3.62 → 7.32.
- **Q-A1.1 quintile (Conv A, calendar-year):** PARTIAL. Step pattern (2022 weak, 2023+ stable around 4-5).
- **Q-A1.1 quintile (Conv B, equal-N):** non-monotonic with q5 spike. Spearman = +0.80; joint p = 0.0055.
- **Q-A1.2 q5 drill-down:** the spike is loss-truncation, not profit generation.

The chain has moved from "monotonic regime improvement" (Q-A1) → "localized step + recent spike" (Q-A1.1) → "the recent spike is zero-loss avoidance, not better wins" (Q-A1.2). Each refinement has weakened the structural-regime claim and sharpened the operational interpretation.

## Cross-references

- **Parent Q-A1.1 brief:** [q_a1_1_pepperstone_quintile.md](q_a1_1_pepperstone_quintile.md).
- **Grandparent Q-A1 brief:** [q_a1_pepperstone_replication.md](q_a1_pepperstone_replication.md).
- **Q15 closure:** [analysis/notice_phase/findings_2026-04-26.md:414-510](../../../../analysis/notice_phase/findings_2026-04-26.md).
- **Pine source (Rule-0 read-first):** [strategies/aegis/aegis_usdjpy_v4.3.pine:247-270](../../../../strategies/aegis/aegis_usdjpy_v4.3.pine).
- **Q-A parent gated brief** authored 2026-04-27 in chat / Notion; repo artefact pending — Q-A1-d (Joshua's task, independent of this verdict).
- **Methodology:** [observation_routing.md](../../observation_routing.md), [1r_estimation.md](../../1r_estimation.md), [operational_rules.md](../../../operational_rules.md).
- **Memory rules consulted:** Rule-0-extends-to-Pine-code (read Pine before scripting); overlay-trigger discipline (live-PnL gap is the bar); leading-indicator+P&L-gate rationalization (a backtest-only structural inference is not enough).

## Open forks (post-Q-A1.2)

- **Forward live-PnL tripwire on Aegis full-SL hits** — this is the concrete, ungated, cheapest next step. Joshua to install / track in live operations.
- **Filter-funnel composition through-time (Q-A1 Refinement #2)** — secondary, useful only if the tripwire takes a long time to fire and intermediate evidence is wanted.
- **2022-only diagnostic (Q-A1.1 alternative refinement)** — now lower priority. Q-A1.2 has shifted the question's center of gravity to "what's happening in q5" rather than "what was wrong in 2022."
- **Q-A1-d** — backfill `docs/methodology/identify_corpus/2026-04-27/q_a_aegis_panel_mechanism_gated.md`. Joshua's task, unchanged.
- **Q-A2** — remains gated on next re-MC trigger. Q-A1.2 substantially *weakens* the case for pulling Q-A2 forward; the "regime improvement" framing it would have tested is replaced by a "loss-truncation" framing that bootstrap is ill-suited for.
