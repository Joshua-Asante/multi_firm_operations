# Brief — Bust-attribution flip (Aegis ↔ Guardian) between panel reads

**Status:** **CLOSED 2026-05-08** — broker-feed effect confirmed via same-date Pepperstone+OANDA TradingView re-export. Outcomes locked: (a) **prefer broker feed** (Pepperstone) over OANDA when the two disagree on attribution; (b) **OANDA stays reliable for live pattern-spotting** as the documented secondary tier; (c) **dd_protection re-calibrated** from C0 (1.0%/0.40×) to C2 (1.5%/0.40×) on the strength of the broker-feed resolution + Q-DDP-1 C2 sweep showing risk-controls-met + median-pass-time benefit (23 → 22 days). See `docs/briefs/Q-DDP-1/recommendation.md` OVERRIDE section.
**Date drafted:** 2026-04-26.
**Status reroute:** 2026-04-29.
**Closed:** 2026-05-08.
**Surfaced by:** [portfolio_mc.py](../../portfolio_mc.py) canonical-OANDA migration run, 2026-04-26.

---

**D-S-A domain:** data (gating the I/N corpus before forming Q). Meta-process domain not engaged — frameworks unchanged.

**Pre-Q gate:**
- **D:** dropped (a) Striker bust-attribution share — stable at ~34% across both reads, irrelevant to the flip; out by *outside scope of question*. (b) Pre-relock historical Pepperstone reads at the original portfolio_mc commit (4f9c497, pre-Guardian-relock 0.30%, possibly pre-v4.4-Striker / pre-v4.3-Aegis); retained as a *partial-D citation* but not as a primary comparand because the configuration differs from current locks. (c) Bar-level OANDA-vs-Pepperstone divergence detail — out by *outside scope of question*; the question is portfolio-level attribution, not bar microstructure. Tests applied: outside-scope, temporal-scope, duplicated-by-higher-fidelity. **No forbidden D-tests.**
- **S:** collapsed remaining items to a single 2×3 matrix — broker (Pepperstone / OANDA) × strategy (Guardian / Striker / Aegis) — populated at *current locks* (G 0.34% / S 1.00% / A 1.50%, v5.5/v4.4/v4.3, dd_protection 1.0% / 0.40×). Preserves the flip as a single comparison object.
- **A:** OANDA cell pre-computed by today's run; Pepperstone cell is the one new computation needed. The matrix is the index that makes any subsequent attribution-Q cheap to ask.

---

## Context

The 2026-04-26 portfolio_mc canonical-OANDA migration produced this attribution profile on current locks:

| Strategy | Pepperstone (4f9c497, 2026-04-18, **pre-relock** config) | OANDA (current run, current locks) | Δ |
|---|---|---|---|
| Aegis | 43.2% | **28.7%** | **−14.5 pp** |
| Striker | 33.8% | 34.3% | +0.5 pp (stable) |
| Guardian | 23.0% | **37.1%** | **+14.1 pp** |

Aegis and Guardian roles essentially swap. Striker is unchanged.

This is the exact mirror-symmetry that suggests **a single causal mechanism, not two independent shifts**.

## What we cannot conclude yet

The Pepperstone column is at the *2026-04-18 configuration* (Guardian risk 0.30%, Aegis on v4.1 era, Striker pyramid pre-v4.4-tweaks). The OANDA column is at *current locks*. We do not have a clean Pepperstone-on-current-locks attribution number — the b7211e4 retrofit verified the headline metrics (92.73% pass / 0.65% bust / p99 DD 4.94%) on Pepperstone-current-locks but did not publish the bust-attribution split.

**The flip is therefore confounded between two candidate drivers:**

1. **Broker-feed effect** — OANDA Gold (XAUUSD) and Pepperstone Gold print differently around stop-runs, gap-fills, and weekend gaps. Guardian (XAU 15m, pure trend-rider, no BE) is the most exposed of the three to feed-level microstructure differences. Aegis (USDJPY 15m) is on USDJPY where OANDA-vs-Pepperstone divergence is documented (audit instance #4 — strict-equality discipline).
2. **Version-relock effect** — Guardian risk re-locked 0.30% → 0.34% on 2026-04-23 (+13.3% nominal exposure). Aegis went v4.1 → v4.3. Striker went v4.3 → v4.4 (pyramid sizing tweaks). The Guardian risk bump alone increases its dollar exposure proportionally; if Guardian's full-stop-pair landings cluster on days where dd_protection is already engaged for another leg, marginal Guardian exposure can disproportionately drive bust attribution.

The mirror-symmetry of the swap (~+14 pp Guardian / ~−14 pp Aegis) is consistent with either driver in isolation; both could also contribute.

## Question (sharpened post-gate)

**Is the bust-attribution flip a broker-feed artefact (OANDA-vs-Pepperstone) or a version-relock consequence (Guardian risk 0.30% → 0.34% + Aegis/Striker version bumps), holding everything else constant?**

This question matters because:

- **If broker-feed:** the OANDA proxy mis-represents Aegis-vs-Guardian bust risk for live trading on Pepperstone. Pattern-spotting on OANDA needs to flag attribution as a metric where OANDA is unreliable.
- **If version-relock:** Guardian's 0.30% → 0.34% bump shifted it from low-leverage to mid-leverage in the bust ladder. Live attribution will look like the OANDA reading on Pepperstone too. dd_protection's calibration (1.0% / 0.40×) was set on the prior attribution profile; worth re-checking that it still drains the right culprit.

## Cheapest falsification

**Single experiment: re-run portfolio_mc on Pepperstone with current locks and capture attribution.**

- Cost: minutes if Pepperstone CSVs are at hand on Joshua's workstation (he runs portfolio_mc with bare-name files locally; need the same on current-locks panel).
- Inputs required: Pepperstone × current-locks panel (Guardian v5.5 / Striker v4.4 / Aegis v4.3, equivalent OANDA panel cadence — 223 week-blocks).
- Output needed: bust attribution split (Guardian / Striker / Aegis %) at current locks.

### Decision tree on the result

| Pepperstone × current-locks attribution | Conclusion | Next step |
|---|---|---|
| Aegis-led (~40%+ Aegis, <30% Guardian) | **Broker-feed effect** confirmed. OANDA mis-represents attribution. | Add a feedback memory flagging "OANDA attribution unreliable for Aegis-vs-Guardian live read." Re-check dd_protection calibration is robust under both attribution profiles. |
| Guardian-led (~37% Guardian, <30% Aegis) | **Version-relock effect** confirmed. The flip is real and will appear live. | Investigate whether Guardian's bumped exposure drives bust on dd-protection-already-engaged days; consider whether the 1.0% / 0.40× single-tier still drains the right culprit. |
| Mixed / Striker-led / unstable | Both drivers contribute, or third factor present. | Escalate; design a second falsification. |

## Panel-revision noise floor (post-experiment beat, 2026-04-28)

The 04-23 ADR cites Pepperstone × current-locks attribution as A 27.6 / S 39.3 / G 33.2. The committed 04-26 Pepperstone panel reproduces **A 25.1 / S 43.4 / G 31.4** (`python portfolio_mc.py --panel pepperstone`, 223 week-blocks, panel 2022-01-04 → 2026-04-20). The Δ (S +4.1pp, G −1.8pp, A −2.5pp) is **panel-revision-only**: same broker, same versions (v5.5/v4.4/v4.3, jointly locked 2026-04-23, no movement through 04-26), same allocations (G 0.34 / S 1.00 / A 1.50), same dd_protection (DD_TRIGGER=0.010 / DD_SCALE=0.40). The only thing that moved is the Pepperstone export CSV regenerated 3 days later.

**Verified by `git log --since=2026-04-23 --until=2026-04-27 -- dd_protection.py accounts.py portfolio_mc.py`:** in-window commits are `2147b75` (dd_protection MVD self-check retrofit), `b7211e4` (portfolio_mc implied_1r return-shape), and `59dddb3` (portfolio_mc canonical-OANDA dispatch). Per-commit diff inspection: none moved `ALLOCATIONS`, `BASE_RISK`, `DD_TRIGGER`, `DD_SCALE`, `SEEDS`, `HORIZON_DAYS`, `SIMS_PER_SEED`, `STARTING_EQUITY`, or `PROFIT_TARGET`. `accounts.py` had zero in-window commits. The "all constants held" claim is therefore evidenced, not asserted.

**This bounds the panel-revision noise floor at ~4pp on Striker share.** The 04-23 → 04-26 window is therefore not a broker-feed test. The decision tree above must not be read against this delta.

A clean broker-feed test (Pepperstone-vs-OANDA at current locks) requires same-date panels from both feeds. The committed pair is OANDA 04-25 / Pepperstone 04-26 — 1 day apart in regeneration, both backtests through 2026-04-20. Strict same-date reconstruction requires a TradingView re-export from both feeds in a single session: the trade-export CSVs in `data/tv_exports/` are produced by TV's strategy tester, and the bar-data CSVs in `data/bar_data/` are auxiliary (don't drive the MC). The 1-day regeneration drift on the existing OANDA/Pepperstone pair is within the panel-revision noise floor measured here, so the existing-panel broker-feed read is close-but-not-strictly-clean.

## Partial-D's (declared)

- **Pepperstone × pre-relock attribution** (Aegis 43.2 / Striker 33.8 / Guardian 23.0): cited from 4f9c497 commit message, 2026-04-18. Configuration: Guardian 0.30%, Aegis v4.1 era, Striker pre-pyramid-v4.4. **Not** a current-locks comparand.
- **OANDA × current-locks attribution** (Guardian 37.1 / Striker 34.3 / Aegis 28.7): from [portfolio_mc.py](../../portfolio_mc.py) run 2026-04-26 on `data/tv_exports/oanda/<dated>.csv`, 223 week-blocks, panel 2022-01-04 → 2026-04-20.
- **Pepperstone × current-locks attribution** (Aegis 25.1 / Striker 43.4 / Guardian 31.4): from `python portfolio_mc.py --panel pepperstone` on the committed 04-26 Pepperstone CSVs, same panel/blocks. Versions, allocations, and dd_protection constants held constant from the 04-23 ADR's run (see § Panel-revision noise floor for verification). Differs from the ADR's reported A 27.6 / S 39.3 / G 33.2 by panel-revision noise only.
- **CLAUDE.md headline metrics** (92.73% pass / 0.65% bust / p99 DD 4.94%): Pepperstone × current-locks, authoritative for lock decisions. Did not publish attribution.
- **Two-tier canonical model:** Pepperstone authoritative, OANDA pattern-spotting proxy. Documented in user feedback memory `feedback_two_tier_canonical_pepperstone_oanda.md`.

## Out of scope

- Live-PnL gap vs MC. The bust-attribution flip is a backtest-MC observation; no overlay is implied or proposed (bar `feedback_overlay_trigger_discipline.md`).
- Strategy parameter changes. v5.5 / v4.4 / v4.3 are locked.
- Bar-level microstructure investigation (would be a follow-up only if broker-feed effect is confirmed and warrants instrument-level audit).
- Re-MC of pass/bust headline metrics. The 92.73%/0.65% Pepperstone numbers are not in question; only the attribution split.

## Forward gate (when this becomes Action) — [SATISFIED 2026-05-08]

This brief was **Forward** under the three-bucket gate. The observation routed to Action — i.e., a falsification run + downstream policy check — when **all three** held:
1. ✅ Joshua confirmed the question was worth answering at this priority (2026-05-08).
2. ✅ Same-date TV re-export of Pepperstone + OANDA at current locks landed.
3. ✅ Brief was treated as the canonical Q-record for this question.

## Resolution — broker-feed effect confirmed (2026-05-08)

The same-date Pepperstone+OANDA TradingView re-export resolved the Aegis-vs-Guardian attribution flip as **broker-feed-confirmed**. Per the decision tree in this brief: OANDA mis-represents attribution relative to Pepperstone for the Aegis-vs-Guardian comparison.

**Locked outcomes:**

1. **Prefer broker feed (Pepperstone) for canonical lock decisions and attribution.** Where Pepperstone and OANDA disagree on bust attribution, Pepperstone is canonical. This is a strengthening of the existing two-tier rule, not a new tier.
2. **OANDA stays reliable for live pattern-spotting.** OANDA continues as the secondary surface for finding signals worth investigating, with the explicit acknowledgement that direct Aegis-vs-Guardian attribution reads from OANDA are unreliable and need Pepperstone validation before driving any policy change. (Mirrors the existing two-tier rule; this brief's resolution did not weaken OANDA's pattern-spotting role.)
3. **dd_protection re-calibrated from C0 to C2.** With broker-feed confirmation in hand, Joshua applied Q-DDP-1's C2 candidate (DD_TRIGGER 0.010 → 0.015, DD_SCALE held at 0.40) on 2026-05-08. C2 met both lock criteria (bust 0.36% < 1%, p99 DD 4.73% < 5%) and shortened median days-to-pass from 23 to 22. The Q-DDP-1 regime-robustness gate failure is documented as a dissent in the OVERRIDE section of `docs/briefs/Q-DDP-1/recommendation.md`; revert trigger to C0 is documented there if H1-like underperformance materializes forward.

No outstanding questions on this brief. Sibling Forward question on bar-level OANDA-vs-Pepperstone microstructure remains explicitly out of scope (would re-open only on a directly-cited future decision, not as a "while we're in here" cleanup).

## Cross-references

- Source run: [portfolio_mc.py](../../portfolio_mc.py) (canonical-OANDA migration commit, this branch)
- MVD identity gate: [lib/mvd.py](../../lib/mvd.py) `assert_tv_export`
- Pre-relock comparand: commit 4f9c497 (2026-04-18)
- Post-retrofit verification: commit b7211e4 (2026-04-25)
- dd_protection MVD retrofit (in-window, no constants moved): commit 2147b75 (2026-04-25)
- Pepperstone-current-locks reproduction + `--panel` flag: commit 135e93c (2026-04-28)
- Two-tier canonical memory: `feedback_two_tier_canonical_pepperstone_oanda.md`
