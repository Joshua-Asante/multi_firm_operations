# Brief — Bust-attribution flip (Aegis ↔ Guardian) between panel reads

**Status:** Prep — Inquire-phase, not yet authorized.
**Date drafted:** 2026-04-26.
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

## Partial-D's (declared)

- **Pepperstone × pre-relock attribution** (Aegis 43.2 / Striker 33.8 / Guardian 23.0): cited from 4f9c497 commit message, 2026-04-18. Configuration: Guardian 0.30%, Aegis v4.1 era, Striker pre-pyramid-v4.4. **Not** a current-locks comparand.
- **OANDA × current-locks attribution** (Guardian 37.1 / Striker 34.3 / Aegis 28.7): from [portfolio_mc.py](../../portfolio_mc.py) run 2026-04-26 on `data/tv_exports/oanda/<dated>.csv`, 223 week-blocks, panel 2022-01-04 → 2026-04-20.
- **CLAUDE.md headline metrics** (92.73% pass / 0.65% bust / p99 DD 4.94%): Pepperstone × current-locks, authoritative for lock decisions. Did not publish attribution.
- **Two-tier canonical model:** Pepperstone authoritative, OANDA pattern-spotting proxy. Documented in user feedback memory `feedback_two_tier_canonical_pepperstone_oanda.md`.

## Out of scope

- Live-PnL gap vs MC. The bust-attribution flip is a backtest-MC observation; no overlay is implied or proposed (bar `feedback_overlay_trigger_discipline.md`).
- Strategy parameter changes. v5.5 / v4.4 / v4.3 are locked.
- Bar-level microstructure investigation (would be a follow-up only if broker-feed effect is confirmed and warrants instrument-level audit).
- Re-MC of pass/bust headline metrics. The 92.73%/0.65% Pepperstone numbers are not in question; only the attribution split.

## Acceptance criteria for promotion to Inquire

This brief is in **prep status**. Promote to active Inquire when:
1. Joshua confirms the question is worth answering at this priority.
2. Pepperstone × current-locks panel is available locally to run the falsification.
3. Brief is registered against a Notion question-of-record (per repo convention; q5_break_window cites `https://www.notion.so/...`).

## Cross-references

- Source run: [portfolio_mc.py](../../portfolio_mc.py) (canonical-OANDA migration commit, this branch)
- MVD identity gate: [lib/mvd.py](../../lib/mvd.py) `assert_tv_export`
- Pre-relock comparand: commit 4f9c497 (2026-04-18)
- Post-retrofit verification: commit b7211e4 (2026-04-25)
- Two-tier canonical memory: `feedback_two_tier_canonical_pepperstone_oanda.md`
