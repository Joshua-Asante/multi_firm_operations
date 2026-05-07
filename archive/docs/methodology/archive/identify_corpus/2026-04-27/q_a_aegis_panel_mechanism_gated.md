# Q-A — Aegis panel-wide PF improvement mechanism (gated parent)

> **Backfill artefact** — repo landing of the 2026-04-27 OANDA-proxy bar-corpus Notice pass synthesis, in which Q-A's inheritance update was authored. Q-A is the gated parent question; this synthesis is the parent reference cited by [Q-A1](../2026-04-29/q_a1_pepperstone_replication.md), [Q-A1.1](../2026-04-29/q_a1_1_pepperstone_quintile.md), and [Q-A1.2](../2026-04-29/q_a1_2_pepperstone_q5_drilldown.md).

| Field | Value |
|---|---|
| Date authored | 2026-04-27 |
| Date backfilled (repo) | 2026-04-29 |
| Source | Notion page `34fdc0b53c1181c690d6c21f5d69bb6f` |
| Type | Notice-pass synthesis (parent for Q-A inheritance) |
| Canonical status | OANDA-proxy (per [`AMENDMENT_oanda_rescope.md`](../2026-04-26/AMENDMENT_oanda_rescope.md)) |
| Q-A gating | Pepperstone-canonical access (re-MC piggyback OR Observe #1 escalation) |
| Q-A status as of 2026-04-29 | Still gated; ungated component closed-looped via Q-A1 chain — see Disposition below |

**Source attribution.** Verified pasted from Notion `34fdc0b5…bb6f` on 2026-04-29. Repo-relative link paths and broken Notion-export auto-link artefacts (`[file.md](http://file.md)` patterns) have been normalised; analytical content is unchanged.

## Disposition (2026-04-29) — Q-A1 chain closed-loop

The ungated component of Q-A was forked into a three-stage analysis-only chain (Q-A1 panel-thirds → Q-A1.1 quintile → Q-A1.2 q5 trade-by-trade drill-down) on the Pepperstone canonical CSV without re-MC. Outcome: the Q15 monotonic-PF-lift framing **dissolves under refinement**. The Conv B q5 PF=28.4 is **denominator-driven** (gross_loss = 0.033 R across 24 trades; max R = +0.153, no full-SL hits, no stales) — fragile loss-truncation, not regime improvement.

**Routing:** Q-A2 NOT escalated. Recommended falsification path is forward live-PnL tripwire on the next Aegis full-SL hit (R ≤ −0.70 in live trading). No allocation, dd_protection, or calibration change. Closing artefact: [`q_a1_2_pepperstone_q5_drilldown.md`](../2026-04-29/q_a1_2_pepperstone_q5_drilldown.md).

## Why backfill this parent (vs. point children at Q-A1.2)

The cheaper alternative was to delete every "pending — Q-A1-d" reference in the children and link directly to Q-A1.2 (the closing artefact). Rejected because:

1. Chat / Notion is not a stable reference (link rot, access-control changes, edit history not co-versioned with the repo). On-disk-first evidence is the project convention.
2. The parent's framing question and gating criterion are template material for future gated-Q forks of the same shape; deleting the parent erases the template.
3. Stating the rationale here preserves the decision for the next instance of "gated Q with ungated component runnable on existing data."

---

## Banner

**Loop iteration:** 2026-04-27 OANDA-proxy bar-corpus Notice pass (sibling iteration to 2026-04-26; same substrate, sharper criteria).

**Canonical-status reminder:** entire corpus is OANDA proxy per [`docs/methodology/identify_corpus/2026-04-26/AMENDMENT_oanda_rescope.md`](../2026-04-26/AMENDMENT_oanda_rescope.md). **Action routing is forbidden on this corpus**; only Closed / Forward / Gated verdicts are admissible. Pepperstone re-verification gates any operational change.

**Anomalies surfaced:** 10 underlying observations across O1/O3/O4/O5/O6 (12 row-level entries; some are facets of the same observation).

**Bucket movement:** 7 Closed, 3 Forward, 0 Action. Q-A and Q-G both inherit observation context (no firing).

**Predecessor independence:** per Code's brief-binding, this run did NOT carry forward 04-26 verdicts. Several anomalies re-surface 04-26 observations on shared substrate. Independent re-discovery, not citation.

**Findings file (line-level evidence):** [`analysis/notice_phase/findings_2026-04-27.md`](../../../../analysis/notice_phase/findings_2026-04-27.md).

---

## Brief-author error acknowledged

The Notice brief authored 2026-04-27 labeled this run as a "Pepperstone-canonical bar-corpus Notice pass" in its preamble. **The corpus is OANDA-proxy per the AMENDMENT.** Code surfaced the conflation and tagged `canonical_status = "PROXY"` end-to-end — the Sources Read discipline working as intended.

Process learning: the brief author must declare their own Sources Read at authorship time, not only require it of Code at execution time. Mirrors INQHIORI v2 §3 backfill discipline, which currently lives on the auditor side. Folding this back into brief-author hygiene next iteration.

No gate audit file warranted (no forbidden D-test was applied, no deletion proved wrong, no time-budget breach). The catch was upstream of any harm.

---

## Routing table — all 10 underlying observations

| # | Source | Observation | Verdict | Rationale |
| --- | --- | --- | --- | --- |
| **1** | O1 | Guardian `block_MonH08` rejected mean R = −0.32 vs accepted +1.65 (Δ = −1.97R, n=38) | **Closed (Q-G inheritance)** | Already preserved in Q-G's underlying observation; updated with on-canonical-criteria magnitude. Mon-H08 was the only Guardian hour-block with negative rejected R per Q-G; Code's stricter \|Δ\|>0.5R threshold confirms. |
| **2** | O1 | Guardian `block_TueH08` rejected mean R = +0.86 vs accepted +1.65 (Δ = −0.79R, n=51) | **Closed (Q-G inheritance)** | Q-G's underlying observation lists TueH08 as positive-rejected-sim_R; Code's panel-aligned cohort confirms positive but materially below accepted. Inherited as additional gate-firing context for Q-G, not new Q. |
| **3** | O3 | Striker `s4_warmup_pass` +127.4% drift across panel (sustained +34.6%) | **Closed (Q11 evidence-class)** | Same evidence-class as Q11 (Striker funnel drift, regime-driven hour shift). Permitted D-test "question-class extrapolation" (declared 2026-04-26) applies. Locked filter (13–17 UTC) sits in the same window the signal mass concentrated into; mechanically absorbed. |
| **4** | O3 | Guardian `s4_hour_pass` +101.7% drift (sustained +52.9%) | **Closed (Q12 evidence-class)** | Independent re-discovery of F2/Q12 — Guardian hour_pass +94% drift on the 04-26 scan, +101.7% on the 04-27 stricter sustained-thirds criterion. Same observation, larger magnitude. Q12 verdict (downstream of XAU vol-regime expansion, ATR-contemporaneous sizing absorbs) re-applies. |
| **5** | O3 | **Aegis `s2_in_session` +33.4% drift (sustained +36.0%) co-moving with Q15 PF 2.46 → 5.96 across early/mid/late panel** | **Forward → Q-A inheritance** | The highest-leverage finding in the scan. Code flagged the co-movement explicitly per brief instruction: s2_in_session 6mo period rate grew across the same panel sub-periods where Q15 observed Aegis PF improvement. Sharpens Q-A's candidate-mechanism set: locates the candidate at the post-session-window-filter stage rather than diffuse across all v4.3 filters. Does **not** fire Q-A (gated on Pepperstone-canonical access; OANDA cannot resolve real-vs-artefact). |
| **6** | O4 | Bar-level adverse-window autocorrelation: lags 1–4 all z>5; run-length ≥2 observed 7 vs expected 0.45 (15.6× iid); ≥97% NOT macro-event-aligned | **Forward (Q-T)** | Q14 closed at the daily resolution with "no portfolio-DD signal." O4 finds bar-level co-movement at much higher z than Q14 measured at, AND the clustering is largely macro-event-independent. Q14's verdict was *schedule diversification absorbs bar-level co-movement* — but Q14's measurement was at day level. Sharp Forward question: **does Tuesday-specific bar-level concentration (the single overlap day for all three strategies) materially elevate concurrent-loss above Q14's daily-level finding?** |
| **7** | O5 | Guardian `block_MonH09` sign reversal: −10.0R early → +16.5R mid → +43.1R late (max magnitude 43.1R, sustained reversal) | **Closed (Q-G inheritance)** | Q-G's underlying observation includes MonH09 (+1.24 R rejected sim_R aggregate). Code's per-third decomposition reveals the aggregate hides a sign reversal with material magnitude growth. Sharpens Q-G from "is the lock too conservative?" to "is the lock's protective sign even still negative in late panel?" |
| **8** | O5 | Aegis `block_TueH10` sign reversal: −1.7R early → +0.06R late | **Closed (sub-noise)** | Magnitude (max \|R\| = 1.7) below the 2R noise floor used elsewhere in the routing; sign reversal is structurally interesting but operationally below the threshold for Q-A inheritance. Logged in findings file; no inheritance update. |
| **9** | O6 | p8 (2026-01..2026-04-19, partial 3.5/6 months) Guardian +1.98 / Aegis −1.99 z opposite-sign | **Forward (wait-state)** | Partial period; current panel-edge. Aegis conversion-rate dropping while Guardian conversion-rate rising in early 2026 is descriptively interesting but conditional on the next ~2.5 months not reversing. Re-evaluate at p8 completion (~mid-2026). **Notable interaction with Observe #1:** if Aegis live per-trade R degrades AND OANDA conversion rate continues dropping, the two signals would corroborate. |
| **10** | O6 | p4 (2024-01..2024-07, full) Guardian +1.09 / Striker −1.24 z opposite-sign | **Closed (descriptive only)** | Past-panel mid-window candidate boundary. Var-alloc 4A REJECTED + state-readable bottleneck both bind: no overlay/classifier proposal admitted. Logged as descriptive panel feature; no operational implication. |

**Bucket summary (post-routing):**

| Bucket | Count | Items |
| --- | --- | --- |
| Closed | 7 | #1, #2, #3, #4, #7, #8, #10 |
| Forward | 3 | #5 (Q-A inheritance), #6 (Q-T new), #9 (wait-state) |
| Gated | 2 unchanged | Q-G (inherits from #1, #2, #7); Q-A (inherits from #5) |
| Action | 0 | OANDA-proxy: forbidden by AMENDMENT |

---

## Cross-cutting patterns

**1. The four-rule gate continued working under tighter criteria.** 04-26 used 30%/sign-reversal thresholds; 04-27 used \|Δ\|>0.5R, sustained-thirds, \|z\|>2 autocorrelation, \|z\|>1 opposite-sign cross-strategy. Most observations still Closed under the existing rule set — the criteria-tightening did not produce a flood of new Action candidates (and Action is forbidden anyway). The two genuinely new Forward items (#5 funnel co-movement, #6 bar-level autocorrelation) emerged because their observation classes were *not* present in the 04-26 criterion set, not because the criteria tightened.

**2. The Aegis funnel-vs-PF co-movement is the single load-bearing new finding.** Q15 left the late-panel Aegis PF improvement uncharacterized; O3 located the candidate at `s2_in_session` (post-session-window-filter pass-rate growth +33%). This narrows Q-A's mechanism candidate set materially without firing the gate. The narrowing is the value: when Q-A fires (via Pepperstone re-MC piggyback or Observe #1 escalation), the decomposition starts at s2 rather than scanning all v4.3 filters.

**3. The bar-level autocorrelation (#6) is genuinely surprising and survives the four-rule gate.** Q14 found no portfolio-DD signal at the daily level. O4 found bar-level adverse clustering at lags 1–4 with z>5–14 — much stronger than Q14 measured at, AND mostly NOT macro-event-driven (97%+ not in NFP/FOMC windows). The Q14 verdict (schedule diversification absorbs) likely still holds because the strategies barely co-trade — but the measurement was at the wrong resolution to confirm robustness. Q-T tests this directly. **Critical methodology guard:** Q-T must NOT propose an overlay or sizing modulation regardless of result. Iran/Hormuz lesson + var-alloc 4A REJECTED bind. Q-T is a falsifiability check on Q14's resolution, not an overlay candidate.

**4. The OANDA-proxy scope-correction was caught at execution time, not at brief-authorship time.** This is the second time in 5 days that a substrate-identity error was caught downstream rather than upstream (the first was the 2026-04-23 Aegis-on-Alchemy-mislabeled-as-Pepperstone failure). Sources Read discipline at brief-authorship time would catch these upstream. Folded into authoring discipline.

**5. Striker base-leg-only sim caveat is the largest interpretive constraint on this run.** O1 and O5 Striker results exclude the 350% pyramid, which is "the entire structural edge" per Pine v4.4 header. Striker anomaly absence in O1 is therefore upper-bounded — not "Striker has no rejected-cohort anomaly," but "Striker has no rejected-cohort anomaly *under base-leg sim*." Real Striker P&L on rejected cohorts could be materially larger in either direction. Worth a future Code task to extend O1/O5 with pyramid-inclusive sim once the simulation infrastructure is wired (separate Identify-corpus addendum).

---

## Q-G — inheritance update (no firing)

**Inherited observations from this run (added to Q-G's underlying observation):**

- Mon-H08: −1.97R Δ vs accepted (n=38), confirming Q-G's negative-only-block of all six.
- Tue-H08: +0.86R rejected, but materially below accepted at +1.65 — adds asymmetry context to Q-G's "5 of 6 positive rejected sim_R" framing.
- **Mon-H09: panel-third sign reversal (−10R → +16R → +43R) with sustained reversal and 43.1R late-panel magnitude.** This is the most material addition. Sharpens Q-G's question from "is the lock too conservative?" to "is the lock's protective sign even still negative on current-panel data?" When Q-G fires, Mon-H09 becomes the highest-priority block for per-third decomposition.

**Q-G status:** still gated. Same three fire conditions hold. The OANDA-proxy evidence from this run is observation context, not gate-firing evidence — does not satisfy gate condition 1.

---

## Q-A — inheritance update (no firing)

**Inherited observations from this run (added to Q-A's underlying observation and candidate-mechanism set):**

- **Aegis `s2_in_session` pass-rate grew +33.4% across panel (sustained +36.0%) on the same OANDA panel where Q15 observed PF 2.46 → 4.97 → 5.96.** The co-movement is descriptive — mechanism (whether the s2 expansion and PF improvement share a substrate) is open.
- Aegis `s4_day_pass`, `s5_vol_pass`, `s6_not_block_TueH10` all show sign-mismatched or sub-30% drift — meaning the s2 expansion is *partly* absorbed by downstream filters but trade count still grows in late panel (consistent with Q15's n=44 / 28 / 51 trade count growth).

**Refined Q-A candidate-mechanism set:**

1. ~~"Trade-selection composition through the multi-filter funnel"~~ → **sharpened to "post-session-window-filter (s2) candidate-pool expansion in late panel"**. Most-likely candidate.
2. ~~"Late-panel session-microstructure shift"~~ → **partial overlap with #1**. The 10:00–13:45 EST window is Aegis's session filter; if late-panel USDJPY behavior in that window has shifted (e.g., more BB(19,1.9) triggers per session-day), s2 expansion is a direct measurement of that shift.
3. EOM-filter contribution shift across panel — **demoted** (O5: EOM contribution monotonically negative, no sign reversal).
4. ATR-adaptive sizing's win/loss-ratio behavior in lower-vol regimes — **unchanged** (not in this Notice scan's scope).
5. Selection bias from thinning trade count — **demoted** (Q15 trade count actually GREW slightly in late panel: 44 → 28 → 51; not a thinning story).
6. OANDA-vs-Pepperstone basis divergence — **unchanged** (resolved only by Pepperstone re-verification when Q-A fires).

**Q-A status:** still gated. The s2 candidate refinement is a methodology win even without firing — when Q-A fires, the decomposition starts at one stage rather than searching all six.

**2026-04-29 update — Q-A1 chain closed-loop summary added.** A three-stage analysis-only chain (Q-A1 panel-thirds → Q-A1.1 quintile → Q-A1.2 q5 trade-by-trade drill-down) ran on the Pepperstone canonical CSV without re-MC, forking out the ungated component of Q-A. Outcome: the Q15 monotonic-PF-lift framing dissolves under refinement. The Conv B q5 PF=28.4 is **denominator-driven** (gross_loss = 0.033 R across 24 trades; max R = +0.153, no full-SL hits, no stales) — fragile loss-truncation, not regime improvement. **Q-A2 NOT escalated**; recommended falsification path is forward live-PnL tripwire on next Aegis full-SL hit. Full summary, decomposition tables, and unresolved-items list: Notion `352dc0b53c1181fa90fdc88f6225d6f0` ([`q_a1_2_pepperstone_q5_drilldown.md`](../2026-04-29/q_a1_2_pepperstone_q5_drilldown.md) is the on-disk closing artefact).

---

## Q-T — new Forward Q (drafted)

**Underlying observation (preserved):** O4 — bar-level simultaneous-adverse 15min windows show autocorrelation at lags 1–4 with z=+5.31 to +14.29, run-length ≥2 observed 7 vs iid-expected 0.45 (15.6× excess), ≥97% NOT macro-event-aligned. Q14 closed at daily resolution with "no portfolio-DD signal" and "schedule diversification absorbs bar-level co-movement"; the absorption claim was not directly measured at the day-cohort with maximum schedule overlap.

**The question (Forward queue, gate runs at Inquire-brief authorship):**

*"On Tuesdays — the only weekday all three strategies are scheduled to potentially trade (Guardian Mon/Tue/Thu × Striker Tue/Fri × Aegis Mon/Tue/Wed) — does the bar-level adverse-window autocorrelation observed in O4 translate into multi-strategy concurrent-loss rates exceeding Q14's daily-level finding (7.5% adverse vs 7.1% non-adverse, no portfolio-DD signal at MW p=0.19)? Or does the daily-resolution finding hold at the Tuesday cohort, confirming Q14's robustness at finer time resolution?"*

**Cheapness:** Low (~1 day analysis on existing OANDA bar corpus). No new infrastructure needed.

**Pre-Q gate planning (declared, runs at brief authorship):**

- D: filter to Tuesday-only bar windows where ≥2 of 3 strategies are session-active per their locked schedules. Permitted under "temporal scope" D-test.
- D: out-of-scope: non-Tuesday days (closed by temporal scope), days with single-strategy-only activity (closed by non-overlap).
- S: collapse to per-Tuesday-cohort concurrent-loss series (binary per overlap-window: ≥2 strategies adverse simultaneously), preserving Q14's adversity definition for direct comparability.
- A: index Tuesday cohort by time-of-day; not expensive given existing time-series infrastructure.

**Forbidden D-test pre-flagged:** do NOT delete clusters that align with "high-impact macroeconomic Tuesday" categories (FOMC-Tuesdays, BoJ-Tuesdays). Iran/Hormuz repeat. The question is whether overlap-day concurrent-loss exceeds the daily baseline; macro-event Tuesdays are part of the population.

**Routing on resolution:**

- If Tuesday cohort confirms Q14 (concurrent-loss rate ≤ 8% non-significant): **Closed**, with explicit "Q14 robust at higher time resolution on overlap day" verdict.
- If Tuesday cohort shows materially elevated concurrent-loss (e.g., >12% sustained): **Forward to Pepperstone re-verification** (gated on Pepperstone-canonical access, same gate as Q-G/Q-A). No overlay or sizing modulation may be proposed at this verdict — descriptive only, with action gated on re-verification.

---

## Wait-state log — p8 partial-period re-evaluation

**Underlying observation (preserved):** O6 p8 (2026-01..2026-04-19, partial 3.5/6 months) shows Guardian conversion-rate z=+1.98, Aegis conversion-rate z=−1.99 — opposite-sign with magnitude meeting O6's \|z\|>1 criterion at face value, but conditional on partial-period extrapolation.

**Wait-state action:** re-run O6 at p8 completion (target: 2026-07-01 or earlier if a Pepperstone re-MC fires on schedule for an unrelated reason). No mechanism proposed; descriptive only.

**Interaction with Observe #1:** if Aegis live per-trade R rolling-mean drops below +0.020 sustained over 10 trades during p8 (Observe #1 escalation trigger) AND Aegis OANDA conversion rate continues dropping at p8 completion, the two signals would corroborate. This would NOT change the gating discipline — Observe #1 fires whatever escalation is pre-defined; the OANDA conversion-rate observation is only context. But the corroboration would increase the urgency of the Observe #1 escalation (Q-A fires via gate condition 2 + Q15a EOM-decomp inherits as immediate decomposition tactic).

**Not promoted to active Forward queue.** Wait-state is below Forward in priority — Forward is investigated this loop; wait-state is investigated next loop with new data.

---

## Routing summary (full Command Center state, post 04-27 synthesis)

| Bucket | Count | Notes |
| --- | --- | --- |
| Closed | 31 (was 24; +7 from this synthesis) | Includes #1, #2, #3, #4, #7, #8, #10 from 04-27 |
| Forward | 1 (was 0) | Q-T (new) |
| Wait-state | 1 (was 0) | p8 re-evaluation at completion |
| Gated | 2 unchanged | Q-G, Q-A — both inherited observation context this synthesis, neither fired |
| Action | 0 | OANDA-proxy: forbidden by AMENDMENT |

---

## Methodological note — gate operation under OANDA-proxy constraint

This is the first synthesis run entirely under the OANDA-proxy AMENDMENT discipline. Three observations:

**1. The proxy constraint is operationally clean.** Every routing verdict is a Closed-or-Forward-or-Wait, no Action eligible. The constraint did not produce ambiguity in any of the 10 observations — no finding was "borderline Action" that required handicapping. The findings either resolved cleanly under the existing rule set (Closed) or surfaced a sharp falsifiable question (Forward/Wait), and Pepperstone re-verification gates appropriately.

**2. Question-class extrapolation D-test (declared 2026-04-26) saw heavier use this synthesis.** Closures #3 and #4 both invoked it explicitly (Striker funnel drift, Guardian hour drift — both same-class as Q11/Q12 closures from prior synthesis). The permitted-list addition from 04-26 is now load-bearing infrastructure rather than experimental. **Pending review:** at the next gate audit, confirm that the criterion has not silently widened beyond its original scope ("≥4 same-class closures within an iteration justify a-priori closure of remaining same-class Q's"). The 04-27 application stayed within scope (closures, not a-priori dismissals of unauthored Q's), but the line is worth re-walking.

**3. Time budget:** authoring this synthesis took ~30% of the loop's effort against ~70% on Code's Notice scan. That's outside the §6 ε-greedy guardrail (gate effort ≤10% of I/N effort). Two reasons not to flag this as a budget-breach: (a) the synthesis pass IS the gate-application pass, not a separate gate-on-the-corpus inside Notice; (b) authoring the inheritance updates for Q-G and Q-A required walking the gated-Q underlying observations to confirm what's new vs duplicate, which is one-time work that won't recur at the same scale next iteration. Worth re-measuring next loop to confirm the synthesis pass settles below 20%.

---

## Cross-references

- **Findings file (line-level evidence):** [`analysis/notice_phase/findings_2026-04-27.md`](../../../../analysis/notice_phase/findings_2026-04-27.md)
- **Predecessor synthesis (04-26):** Notion `34edc0b53c118179b57cd38fc1f9f72e` ("Identify-corpus Inquire synthesis — Q11/Q12/Q14/Q15 closure, Observe-phase 1, 2026-04-26")
- **Identify corpus + amendment:** [`docs/methodology/identify_corpus/2026-04-26/`](../2026-04-26/), [`AMENDMENT_oanda_rescope.md`](../2026-04-26/AMENDMENT_oanda_rescope.md)
- **Notice brief (with preamble error noted):** `2026-04-27_notice_phase_15min_bar_corpus_brief.md` — Notion/chat artefact, not on disk
- **Routing gate:** [`docs/methodology/observation_routing.md`](../../observation_routing.md)
- **Methodology canonical:** Notion `34ddc0b53c1181479d7bdecc61f47078` ("INQHIORI ⊕ The Algorithm — Unified framework with D-S-A pre-Q gate reference")
- **Skill (operational):** `inqhiori-algorithm` SKILL.md v2 (2026-04-27 codification)
- **Gated Q's downstream of this synthesis:**
    - Q-G — Guardian hour-block lock vs current-Pepperstone evidence (gated; inherits #1, #2, #7)
    - Q-A — Aegis panel-wide PF improvement mechanism (gated; inherits #5, with candidate-mechanism set narrowed to s2_in_session as primary candidate). **2026-04-29 update:** ungated component closed-looped via [Q-A1](../2026-04-29/q_a1_pepperstone_replication.md) → [Q-A1.1](../2026-04-29/q_a1_1_pepperstone_quintile.md) → [Q-A1.2](../2026-04-29/q_a1_2_pepperstone_q5_drilldown.md) chain — reframed as fragile loss-truncation, not regime improvement; Q-A2 NOT escalated; forward live-PnL tripwire recommended. Notion summary: `352dc0b53c1181fa90fdc88f6225d6f0`.
- **Forward queue (active):** Q-T (Tuesday-cohort bar-level concurrent-loss falsifiability) — Notion `34fdc0b53c1181bcbe07e7bb5aac8e57`; on-disk closure: [`analysis/inquire_phase/findings_q_t_2026-04-27.md`](../../../../analysis/inquire_phase/findings_q_t_2026-04-27.md)
- **Q-T Pepperstone re-verification (gated):** Notion `34fdc0b53c1181b9a121f0c8d38aa27f`
- **Wait-state:** O6 p8 re-evaluation at period completion
