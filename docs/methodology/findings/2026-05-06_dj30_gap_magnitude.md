# 2026-05-06 — DJ30 entry-day opening-gap magnitude

**Loop ID:** Q-DJ30-3
**Brief:** [docs/briefs/Q-DJ30-3/Q-DJ30-3.md](../../briefs/Q-DJ30-3/Q-DJ30-3.md) (Claude Code, 2026-05-06)
**Plan:** `C:\Users\joshu\.claude\plans\q-dj30-3-pre-q-fizzy-metcalfe.md` (Claude Code, 2026-05-06)
**Pre-registration:** [archive/analysis/Q-DJ30-3/verdict_pre_registration.md](../../../archive/analysis/Q-DJ30-3/verdict_pre_registration.md)
**Phase:** Inquire (INQHIORI)
**Date closed:** 2026-05-06

**VERDICT: CLOSE — null result.**

DJ30 worst-decile base-entry losses do **not** cluster on entry days where `|gap_atr_normalized|` ≥ p90 of the panel's gap distribution at any meaningful rate. Effect is small (+4.4 pp tail-vs-nontail at p90) and statistically indistinguishable from noise (Fisher exact p = 0.3493, permutation p = 0.6188, Rule-1 bootstrap p05 lift = −5.6 pp — fails ≥5 pp gate). The diagnostic Phase D half-panel split shows the small full-panel signal is H2-driven (H1 lift −3.9 pp / H2 lift +11.2 pp / spread 15.1 pp) — the same regime-asymmetric artefact pattern Q-DDP-1 and Q-DJ30-2 surfaced.

**The 2025-02-07 anchor trade (#168, −$11,870.65, −5.94R) is itself a below-median |gap| day** (gap_atr_normalized = +0.18, panel percentile 43%). The mechanism the Pre-Q proposed — "gap exceeds ATR-stop, putting stop inside gap" — does not fit the anchor. The SNAG tail is exhausted of cheap mechanism candidates on the locked panel; per pre-reg §7, methodology budget redirects to Aegis BOJ binary-event pause / NAS100 v1 live observation / new strategy candidates.

No Pine v4.6 brief, no full canonical regime-robustness gate, no re-MC, no lock memo. Match Q-DJ30-1 / Q-DJ30-2 sentinel precedent: NULL closes at `findings/`, no `recommendation.md`.

---

## Reframe note

Three sequential mechanism candidates have now been opened on the SNAG tail anchor (trade #168 / 2025-02-07 / NFP +75min / −5.94R / −$11,870.65) and all three closed without producing a treatable mechanism:

1. **Q-DJ30-1** (macro-proximity / event-window pause): CLOSE/null. Worst-decile not co-located with US macro releases.
2. **Q-DJ30-2** (hard dollar cap on base-entry stop): AMBIGUOUS/HOLD. Phase C single-pass at 1.5R cap (+24% PF) failed Phase D regime-robustness gate decisively (H1↔H2 PF spread 59.55%).
3. **Q-DJ30-3** (this brief — opening-gap magnitude): CLOSE/null. **The anchor itself is not a high-gap day.**

The accumulated evidence: the 2025-02-07 worst-loss observation is a **single-event diagnostic, not a class**. It does not resolve to any of: macro-proximity, hard-cap-curable stop slippage, or gap-driven ATR-stop-inside-volatility. Future investigation should probably treat 2025-02-07 as out-of-distribution noise within the locked panel, not as evidence of a class of treatable losses.

This is the right outcome for the methodology — three Pre-Qs on one signal class is the failure mode the discipline exists to prevent, but each Q opened was sharp, falsifiable, and closed cheaply on a defined gate. Methodology budget on this anchor is now exhausted per pre-reg §7.

---

## Rule 0 anchors

All anchor files read at execution start. None changed since 2026-05-05.

| File | Verified content |
| --- | --- |
| [strategies/striker/striker_dj30_v4.5.pine](../../../strategies/striker/striker_dj30_v4.5.pine) | `stopAtr = 1.2` (line 60); active window Tue/Fri 13:00–17:00 UTC (lines 105–109); `riskPerTrade = 1.00` (line 30); entry `rawBreakout = close > highestHigh[1]` is intra-session (not session-open-gated) — **does not invalidate the day-level gap variable** |
| [data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv](../../../data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv) | 224 entries (197 base + 27 pyramid); reproduced cardinality + worst-trade #168 / −$11,870.65 in Phase B |
| [data/bar_data/US30USD.csv](../../../data/bar_data/US30USD.csv) | 101245 M15 OANDA bars, 2022-01-02 → 2026-04-19; aggregated to daily for gap variable |
| [docs/methodology/regime_robustness_gate.md](../regime_robustness_gate.md) | Canonical gate; out-of-scope at this Q level (partition-hypothesis test, not Pareto-relaxation) |
| [docs/methodology/observation_routing.md](../observation_routing.md) | Three-bucket Closed/Action/Forward gate |
| [archive/analysis/Q-DJ30-2/verdict_pre_registration.md](../../../archive/analysis/Q-DJ30-2/verdict_pre_registration.md) | Structural template for pre-reg discipline (Immutability + Halt protocols + Forward-queue commitment) |

---

## Pre-Q gate (per INQHIORI SKILL §3, on the data domain)

```
D: 27 pyramid-add legs (Signal=Long Add) — test: outside temporal/instrument scope
   of the question class (gap operates at session-boundary regime; pyramid legs
   trigger intra-session off profitAtr). Permitted §5 (mechanism scope).
   n=224 retained as Rule-0 anchor + sensitivity panel.

S: per-trade representation augmented with one variable —
   {entry_date_utc, signal, pnl, gap_atr_signed, |gap_atr|, in_gap_p{80,85,90,95}}.
   Day-level gap inherits from the trade's entry UTC date.

A: pre-compute |gap_atr_normalized| panel quantiles once at sweep init
   (panel = 1108 weekday rows from M15 OANDA aggregation).
```

D-test on the §5 permitted list (mechanism scope). No forbidden tests applied.

---

## Phase B — reproduction & cardinality + daily-OHLC aggregation + basis-sanity substitution

### Step 1 — corpus check (PASSED)

| Check | Expected | Observed | Pass? |
|---|---:|---:|:---:|
| `n_entry_long` | 224 | 224 | ✓ |
| `n_base (Signal=Long)` | 197 | 197 | ✓ |
| `n_pyramid (Signal=Long Add)` | 27 | 27 | ✓ |
| Worst single trade | #168 / 2025-02-07 / −$11,870.65 | #168 / 2025-02-07 09:45 / −$11,870.65 | ✓ |

Reproducer: `python archive/analysis/Q-DJ30-3/corpus_check.py`.

### Step 2 — daily OHLC aggregation from M15 OANDA (PC3 path)

Aggregation rule: per-trading-day gap measured between **prior-weekday 21:00 UTC close** (futures RTH close ~ 17:00 ET) and **trade-day 13:00 UTC open** (Pine v4.5 active-window start). Holiday walkback handles cases like Black Friday (prior = Thanksgiving Thursday, market closed) and post-MLK Tuesday by stepping further back to the most recent weekday with a 21:00 UTC bar.

Output: 1108 weekday rows in [archive/analysis/Q-DJ30-3/dj30_daily_gap.csv](../../../archive/analysis/Q-DJ30-3/dj30_daily_gap.csv) (9 skipped at panel boundaries / consecutive-holiday cases).

Panel `|gap_atr_normalized|` quantiles (the binning thresholds for Phase C):

| Quantile | Threshold |
|---:|---:|
| p80 | 0.4545 |
| p85 | 0.5261 |
| **p90** | **0.6209** |
| p95 | 0.7523 |

### Step 3 — basis-sanity substitution (paired gate audit)

Pre-reg committed to a 5-date OHLC vs Yahoo / Stooq DJI cash-close spot-check at < 1.5% tolerance. **No external-reference data lives in this repo** and external WebFetch was not pre-authorized. Per Joshua's "proceed with plan as scoped" authorization (chat record 2026-05-06) and the Q-DJ30-2 amendment precedent ([gate_audits/2026-05-06_q-dj30-2_pre_reg_amend.md](../gate_audits/2026-05-06_q-dj30-2_pre_reg_amend.md)), the gate was substituted with internal-consistency sanity per [gate_audits/2026-05-06_q-dj30-3_basis_sanity_substitution.md](../gate_audits/2026-05-06_q-dj30-3_basis_sanity_substitution.md). All four substituted sub-tests cleared.

The OANDA-vs-Pepperstone basis remains unverified at this brief level; would have become mandatory only at a downstream Pine v4.6 brief (which is not authored under this NULL verdict).

### Step 4 — anchor sanity

| Anchor row | Value |
|---|---:|
| Date | 2025-02-07 (Fri, NFP day) |
| Prior-weekday close (2025-02-06 21:00 UTC) | 44665.0 |
| Trade-day open (2025-02-07 13:00 UTC) | 44751.0 |
| Gap points | +86.0 |
| ATR(14) lagged | 478.2 points |
| `gap_atr_normalized` | **+0.1798** |
| `\|gap_atr\|` | **0.1798** |
| Empirical percentile in panel | **42.9%** (BELOW median) |

**The single trade that motivated this entire Q is below the panel's median absolute gap.** The Pre-Q's mechanism hypothesis — "gap exceeds ATR-stop, putting stop inside gap" — does not fit the anchor. Whatever caused trade #168's −5.94R loss, it was not a gap-mediated event. (NFP-induced fast-market slippage on a 75-min-post-release entry is the more parsimonious mechanism, but Q-DJ30-1 already closed null on macro-proximity, so this routes to single-event diagnostic.)

---

## Phase C — primary clustering test

### Primary — base entries n=197, tail = worst-decile (n=20), bin = `in_gap_p90`

| | in p90 | outside p90 | total |
|---|---:|---:|---:|
| **tail (n=20)** | 2 | 18 | 20 |
| **non-tail (n=177)** | 10 | 167 | 177 |
| **total** | 12 | 185 | 197 |

| Test | Result | Gate | Pass? |
|---|---:|---:|:---:|
| p_tail in p90 | 10.0% | — | — |
| p_nontail in p90 (baseline) | 5.6% | — | — |
| pp diff (tail − nontail) | **+4.4 pp** | — | — |
| Fisher exact, two-sided | **p = 0.3493** | p < 0.10 | ❌ |
| Conditional odds ratio [95% CI] | 1.85 [0.18, 9.73] | — | — |
| Permutation, n=10,000, two-sided | **p = 0.6188** | p < 0.10 | ❌ |
| Rule-1 bootstrap (n=1,000) tail-in-p90 p05/p50/p95 | 0.0% / 10.0% / 20.0% | — | — |
| Rule-1 lift (p05 − p_nontail) | **−5.6 pp** | ≥ +5 pp | ❌ |

**All three primary gates fail.** Per pre-reg §4.4: "NULL — Fisher p ≥ 0.10 OR permutation p ≥ 0.10 OR Rule-1 lift < 5pp." All three conditions for NULL met independently.

### Sensitivity — all entries n=224 (incl. pyramid legs), tail n=22

Qualitatively identical: pp diff +3.6 pp, Fisher p = 0.3719, permutation p = 0.6266, Rule-1 lift −5.4 pp. Pyramid-leg inclusion does not change the verdict.

### Bin sensitivity (worst-decile primary base)

| Bin | p_tail | p_nontail | pp diff | Fisher p |
|---:|---:|---:|---:|---:|
| p80 | 15.0% | 16.9% | **−1.9 pp** | 1.0000 |
| p85 | 15.0% | 10.7% | +4.3 pp | 0.4737 |
| p90 | 10.0% | 5.6% | +4.4 pp | 0.3493 |
| p95 | 5.0% | 2.3% | +2.7 pp | 0.4179 |

Pp-diff oscillates between −1.9 and +4.4 across bins; **all p-values ≥ 0.35**. No bin shows a clustering signal.

### Stratum sensitivity at p90

| Stratum | n | p_tail | p_nontail | pp diff | Fisher p |
|---|---:|---:|---:|---:|---:|
| Worst-decile | 20 | 10.0% | 5.6% | +4.4 pp | 0.3493 |
| Worst-quintile | 39 | 7.7% | 5.7% | +2.0 pp | 0.7079 |
| N=1-day-only worst-decile | 10 | 10.0% | 5.9% | +4.1 pp | 0.4747 |
| ≤ −5R (−$10,000) | 1 | **0.0%** | 6.1% | **−6.1 pp** | 1.0000 |

The ≤ −5R stratum has n=1 (the 2025-02-07 anchor). p_tail = 0.0% confirms the anchor is NOT in the p90 bin — consistent with the anchor's empirical percentile of 42.9% reported in Step 4. Sample-size-driven; not interpretable as evidence on its own, but cleanly mirrors the per-trade tagging.

---

## Phase D — half-panel sanity (diagnostic, NOT load-bearing for verdict)

Verdict was determined by Phase C. This half-panel split is run for diagnostic completeness in this findings doc; it does not flip the verdict.

Per pre-reg §4.3, split point = trade_num 98 (matching Q-DJ30-2). H1 = 86 base trades (2022-01-04 → 2023-10-10). H2 = 111 base trades (2023-10-10 → 2026-04-17).

### Phase D gate at p90 (FAILED — even diagnostic value confirms no signal)

| Sanity test | Statistic | Threshold | Pass? |
|---|---:|---:|:---:|
| H1 lift | **−3.9 pp** (tail 0.0% / nontail 3.9%) | ≥ 0 pp | ❌ |
| H2 lift | **+11.2 pp** (tail 18.2% / nontail 7.0%) | ≥ 0 pp | ✅ |
| Spread `\|H1−H2\|` | **15.1 pp** | ≤ 10 pp | ❌ |

**Two of three Phase D criteria fail.** The full-panel +4.4 pp pp-diff at p90 is **entirely H2-driven**: H1 actively shows tail trades being LESS likely on high-gap days; the asymmetry with H2's +11.2 pp creates the 15.1 pp spread. This is the same regime-asymmetric artefact pattern Q-DDP-1 surfaced on dd_protection's C2 (12.9pp pass-rate spread) and Q-DJ30-2 surfaced on the 1.5R cap (59.55% PF spread).

### Bin sweep — half-panel diagnostic

| Bin | H1 lift | H2 lift | Spread |
|---:|---:|---:|---:|
| p80 | −7.1 pp | +2.2 pp | 9.3 pp |
| p85 | **−10.4 pp** | +6.2 pp | **16.6 pp** |
| p90 | −3.9 pp | +11.2 pp | 15.1 pp |
| p95 | +0.0 pp | +5.1 pp | 5.1 pp |

H1 is consistently below H2 across all bins (always negative or zero). Even the p95 bin (where the spread happens to be small, 5.1 pp) has H1 = 0.0pp — no signal in the early panel period at all.

**This is the third independent confirmation of the same H2-asymmetry pattern on DJ30 worst-decile / SNAG-tail questions.** The 2025-02-07 anchor is in H2; the perceived "signal" in any sub-question on the DJ30 tail tends to fit the anchor's neighborhood and not generalize backward.

---

## Phases E and F — not run

Per pre-registration verdict mapping: Phase E (pyramid audit) and a separate Phase F scope are not load-bearing for partition-hypothesis NULL verdicts. The Rule-1 partition-hypothesis permutation gate (which Q-DJ30-2 reserved as Phase F) is folded into Phase C's permutation test in this brief — already failed. No additional permutation evidence is required.

Also not run: full canonical regime-robustness gate. Reserved for downstream Pine v4.6 brief (PROMOTE-path only); not authored under NULL verdict.

---

## Verdict mechanics

Mapping to the pre-registered verdict table ([archive/analysis/Q-DJ30-3/verdict_pre_registration.md](../../../archive/analysis/Q-DJ30-3/verdict_pre_registration.md) §4.4):

| Verdict | Pre-registered trigger | Observed | Verdict |
|---|---|---|:---:|
| **PROMOTE** | Phase C all three gates clear AND Phase D all three gates clear | Phase C 0/3, Phase D 1/3 | NO |
| **NULL** | Fisher p ≥ 0.10 OR permutation p ≥ 0.10 OR Rule-1 lift < 5pp | All three Phase C gates fail independently | **YES** |
| **AMBIGUOUS** | Phase C clears but Phase D fails; OR 2-of-3 at Phase C | Phase C 0/3 (not 2/3); not applicable | NO |

**Verdict: CLOSE — null result.** Routing per [docs/methodology/observation_routing.md](../observation_routing.md): the gap-magnitude question is closed (Phase C answers it decisively); the SNAG-tail observation routes to **Forward** as a watchlist item — but per pre-reg §7, the methodology-budget commitment is that Q-DJ30-3 closes the budget on this anchor; no fourth Pre-Q on the same anchor.

No `docs/briefs/Q-DJ30-3/recommendation.md` is created (NULL track per pre-reg). No Pine v4.6, no re-MC, no lock memo.

---

## What this verdict says and does not say

**Does say:**
- DJ30 worst-decile base-entry losses are not enriched on high-`|gap_atr|` days at any of {p80, p85, p90, p95} bin thresholds with statistical or bootstrap support.
- The 2025-02-07 anchor (the single −5.94R / −$11,871 worst-loss event) is itself a below-median-gap day (panel percentile 43%). The anchor is not a high-gap event.
- The small +4.4 pp full-panel pp-diff at p90 is entirely H2-driven (H1 is −3.9 pp, H2 is +11.2 pp). Without the H2 asymmetry there is no perceptible signal.
- This is the third sequential mechanism candidate on the SNAG tail to close non-PROMOTE; per pre-reg §7, methodology budget on this anchor is exhausted.

**Does NOT say:**
- That the −5.94R / −$11,871 trade is acceptable or unimportant. It is the dominant tail observation in DJ30 v4.5 history. The verdict surfaces that the gap-magnitude framing is not the right instrument for it; the observation itself remains a single-event diagnostic on the watchlist.
- That gap-magnitude could not matter at finer-grain quantiles (e.g. p99) or in a continuous-Spearman framing. The pre-reg pre-committed to a binary partition-hypothesis test; the continuous framing was deferred per methodology-budget discipline (pre-reg §7) and is not re-opened here.
- That all pyramid legs are unaffected by gap regime. Pyramid legs were included in sensitivity stratum n=224; verdict was qualitatively identical to base-only. If a future Q on pyramid behavior arises, it should be opened on its own merits, not via this brief.
- That the locked v4.5 strategy is deficient. The verdict does not move policy. The 4-strategy 2026-05-05 MC anchor (97.88 / 0.22 / 4.55) is unaffected.
- That OANDA-vs-Pepperstone basis is irrelevant. Substituted at this Q level under Joshua's authorization; would become mandatory at any downstream Pine v4.6 brief (not authored under NULL).

---

## Forbidden-D-test audit

Per INQHIORI SKILL §5, the pre-Q gate's only D-test was permitted (mechanism scope on pyramid legs as sensitivity-not-deletion).

Per pre-reg §5 commitments (5 forbidden-D-tests pre-committed in advance):
1. Did NOT delete H1 trades for "lacking" the pattern. ✓ H1 retained as sanity-relevant in Phase D.
2. Did NOT condition gap definition on the anchor's specific shape. ✓ Definition is panel-quantile-based.
3. Did NOT delete trades on undefined-gap days. ✓ Halt fired on 7 missing trades; cause identified (prior-day-was-holiday cases) and fixed in aggregation by walkback through holidays — no deletion. Reproducer: [archive/analysis/Q-DJ30-3/diagnose_missing.py](../../../archive/analysis/Q-DJ30-3/diagnose_missing.py) → fix in [aggregate_m15_to_daily.py](../../../archive/analysis/Q-DJ30-3/aggregate_m15_to_daily.py).
4. Did NOT change bin thresholds mid-sweep. ✓ Sweep ran on pre-committed {p80, p85, p90, p95}.
5. Did NOT swap the 5pp Rule-1 gate. ✓ Gate failed at −5.6 pp; verdict respected.

One paired pre-reg amendment: basis-sanity substituted to internal-consistency check ([gate_audits/2026-05-06_q-dj30-3_basis_sanity_substitution.md](../gate_audits/2026-05-06_q-dj30-3_basis_sanity_substitution.md)). Surfaced and audit-trailed per the inqhiori SKILL §12 pattern; not a forbidden-D-test smuggling.

---

## Forward-queue status

Per pre-reg §7 commitment: the SNAG tail mechanism on the 2025-02-07 anchor is **exhausted of cheap mechanism candidates on the locked panel**.

Methodology budget on this anchor is closed. Redirected forward queue (as authored at closure 2026-05-06):
1. **Aegis BOJ binary-event pause** — already on forward queue per CLAUDE.md.
2. **NAS100 v1 live observation** — candidate-not-deployed; live-PnL accumulation gate to validate the +0.40% addition.
3. **New strategy candidates** — TBD; no specific candidate currently surfaced.

**Re-opening the SNAG tail at Q-DJ30-N (N ≥ 4) would require new evidence**, not just a new mediator hypothesis. Specifically, per pre-reg §7: "if a second −5R-or-worse base-trade event occurs and is also large-gap-proximate, the gap-magnitude thesis advances with n=2 evidence." Until then, single-event diagnostic.

The continuous Spearman-ρ framing on `|gap|` vs loss/R is **not** opened as a fourth Pre-Q on the same anchor. Three Pre-Qs on one signal class is the methodology-budget failure mode; the discipline is to close the budget, not to keep iterating mediator framings.

### Postscript (2026-05-08) — redirect queue accepted as empty

On 2026-05-08 the redirect queue above was reviewed and **accepted as empty**:

1. **Aegis BOJ binary-event pause** — closed at the strategy-CHANGELOG layer. The April 28, 2026 BOJ meeting watch was closed 2026-05-05 with no parameter change required ([strategies/aegis/aegis_CHANGELOG.md:21](../../../strategies/aegis/aegis_CHANGELOG.md:21)). The reference here was doctrine-stale.
2. **NAS100 v1 live observation** — ongoing operational tracking (live-PnL accumulation), not a methodology investigation requiring its own brief. Removed from this queue; tracked instead via [live_journal/](../../../live_journal/) reconciliation cadence.
3. **New strategy candidates** — no candidate surfaced 2026-05-06 → 2026-05-08; queue closes empty rather than carrying forward an indefinite TBD.

**Q-DJ30-3 is fully closed.** The methodology-budget exhaustion verdict above stands, and there is no active redirect target. Future strategy-candidate work, if any, opens its own brief without inheriting from this closure.

---

## Out of scope (❌ checklist)

- ❌ Pine v4.6 draft, full canonical regime-robustness gate, portfolio re-MC, pin updates in `tests/test_mc_anchors.py`, lock memo, `docs/briefs/Q-DJ30-3/recommendation.md` — all PROMOTE-only artefacts; verdict is NULL.
- ❌ NAS100 / Guardian / Aegis tail behavior — different mechanisms.
- ❌ Allocation, dd_protection constants, MC calibration source — verdict does not move policy.
- ❌ Continuous Spearman-ρ on `|gap|` vs loss/R — methodology-budget closed on this anchor.
- ❌ Re-litigation of the +4.4 pp p90 effect — failed all three primary gates and Phase D diagnostic; no goalpost moves.
- ❌ Live-trading decisions for the upcoming week — INQHIORI investigation, not OODA tactical.

---

## Cross-references

- Plan: `C:\Users\joshu\.claude\plans\q-dj30-3-pre-q-fizzy-metcalfe.md` (Claude Code, 2026-05-06)
- Brief: [docs/briefs/Q-DJ30-3/Q-DJ30-3.md](../../briefs/Q-DJ30-3/Q-DJ30-3.md)
- Pre-registration: [archive/analysis/Q-DJ30-3/verdict_pre_registration.md](../../../archive/analysis/Q-DJ30-3/verdict_pre_registration.md)
- Basis-sanity substitution audit: [docs/methodology/gate_audits/2026-05-06_q-dj30-3_basis_sanity_substitution.md](../gate_audits/2026-05-06_q-dj30-3_basis_sanity_substitution.md)
- Sibling closures: [Q-DJ30-1 / 2026-05-06_dj30_event_clustering.md](2026-05-06_dj30_event_clustering.md) (CLOSE/null), [Q-DJ30-2 / 2026-05-06_dj30_stop_cap.md](2026-05-06_dj30_stop_cap.md) (AMBIGUOUS/HOLD)
- Methodology canon: [regime_robustness_gate.md](../regime_robustness_gate.md), [observation_routing.md](../observation_routing.md), [rule_0.md](../../rule_0.md)
- Q-DDP-1 false-positive worked example: [docs/briefs/Q-DDP-1/recommendation.md](../../briefs/Q-DDP-1/recommendation.md)
- Locked DJ30 v4.5 source: [strategies/striker/striker_dj30_v4.5.pine](../../../strategies/striker/striker_dj30_v4.5.pine)
- INQHIORI canon: https://www.notion.so/34ddc0b53c1181479d7bdecc61f47078

---

## Reproducers

```bash
python archive/analysis/Q-DJ30-3/corpus_check.py          # Phase B Step 1: cardinality + anchor
python archive/analysis/Q-DJ30-3/aggregate_m15_to_daily.py  # Phase B Step 2: M15 -> daily gap panel
python archive/analysis/Q-DJ30-3/tag_trades.py            # Phase C Step 1: per-trade gap tagging
python archive/analysis/Q-DJ30-3/run_tests.py             # Phase C Steps 2-4: Fisher / perm / Rule-1 + sensitivity
python archive/analysis/Q-DJ30-3/half_panel_sanity.py     # Phase D diagnostic: H1/H2 split at trade_num 98
```

Time accounting: ~3h active. One paired pre-reg amendment under Immutability clause (basis-sanity substitution at Phase B start). One halt-and-fix during Phase C tag (7 missing trades on prior-day-holiday dates) — fixed in aggregation by holiday-walkback; no methodology violation.
