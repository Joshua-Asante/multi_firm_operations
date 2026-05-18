# Q-GDN-DDcap — Does a 2.6% per-day DD cap on Guardian Gold improve static-equity Pareto over the no-cap lock?

**Status:** OPEN
**Authored:** 2026-05-17
**Closed:** N/A
**Authors:** Joshua
**Parent question:** N/A (originating)
**Sub-questions opened:** N/A

---

## §0 — Rule 0 reads (production-source verification)

Files read **before** authoring this brief, with verification anchors as of 2026-05-17:

- `firm_rules.py` — anchor `origin/main` (verified `git show origin/main:firm_rules.py` returns `_BASE_RISK = {"guardian": 0.0034, ...}`; allocation unchanged by this Q). The 2026-05-14 allocation refresh on `origin/main` left Guardian at 0.34% — this brief proposes **no allocation change**, only a per-day DD cap inside the Guardian Pine source.
- `dd_protection.py` — anchor `8e2a2d6` (HEAD), verified `DD_TRIGGER = 0.015 / DD_SCALE = 0.40` at line 49–50. This brief is **not** a dd_protection lock change; the per-day DD cap proposed here is a strategy-internal Pine guard, distinct from the portfolio-level dd_protection rule.
- `docs/adr/2026-05-14-allocation-refresh.md` (per `origin/main`) — read for §Override pattern; this brief follows the same override-with-documented-grounds template if regime-robustness gate criterion 5 cannot be reproduced.
- `docs/methodology/regime_robustness_gate.md` — anchor `2567b15`. The gate is scoped to "any LOCK CANDIDATE on a `dd_protection`-class risk constant." A per-strategy daily DD cap is a strategy-internal sizing-adjacent rule; gate applicability is ambiguous on literal reading. This brief treats the gate as **applicable** (loss-magnitude family) and runs it.
- `references/baselines.md` in the trade-csv-reconcile skill — read for current locked Guardian Pepperstone anchor (2026-05-14: n=191, PF 3.644, WR 19.90%, Net $480,547, DD 5.00%, 1R basis: median loss).
- `data/tv_exports/pepperstone/Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-17_90bb1.csv` — same-day locked-control re-export (no DD cap). Reconciled 2026-05-17: n=207, PF 3.457, WR 22.71%, Net (compounded) $452,479 / Net (static) $187,220, DD (compounded) 4.69% / DD (static) 5.51%. Panel: 2022-01-11 → 2026-04-20.
- `Downloads/updated_Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-17_8f599.csv` — swept variant with 2.6% per-day DD cap. Reconciled 2026-05-17: n=201, PF 3.935, WR 22.39%, Net (compounded) $596,748 / Net (static) $214,080, DD (compounded) 5.01% / DD (static) 4.20%. Panel: 2022-01-11 → 2026-04-20 (identical to control). 6 of 201 exits via "DD Limit" signal.

Pine source for Guardian v5.5 with the proposed `dailyDDCap = 2.6` parameter is **not directly readable from this authoring environment**; the swept CSV `8f599` was produced from that source by Joshua. Pine-source verification deferred to the Phase-A executor (per §7 step 1).

---

## §1 — Context & motivation

The 2026-05-14 allocation refresh (`docs/adr/2026-05-14-allocation-refresh.md`) left Guardian at 0.34% risk with no per-day DD cap; bust attribution on the refreshed Pepperstone anchor put Guardian at 34.3% (largest contributor after striker 25.7%). Standing doctrine: dd_protection at C2 (1.5%/0.40×) covers portfolio-level DD but does not bound *per-strategy per-day* DD — a long Guardian losing streak inside a single trading day can exhaust ~3-4% of static equity before the portfolio-level rule fires. A Pine-internal day-stop at 2.6% would cap the per-strategy daily contribution. Static-equity reconciliation (per trade `Net P&L % × $200K`) of the same-day swept vs locked-control CSVs shows the cap is Pareto-improving on PF (+10.0%) and Net (+14.3%) with DD reduced 1.31pp.

## §2 — Prior art / lineage

- **Q-DDP-1 (CLOSED-RESOLVED-WITH-OVERRIDE, 2026-05-08)** — `docs/briefs/Q-DDP-1/recommendation.md`. Established the override-with-documented-grounds template when regime-robustness gate criterion 5 fails but other risk-control criteria pass. Precedent for accepting a risk-control change on broker-feed-confirmed + median-pass-time grounds.
- **2026-05-14 allocation refresh ADR** — `docs/adr/2026-05-14-allocation-refresh.md`. Precedent for documented override of regime-robustness gate at allocation-class change.
- **Methodology memory `feedback_static_equity_default_for_param_compare`** — TV CSV compounding artifact swallowed 81.4% of Q-GDN-DDcap (prior in-session 2026-05-17 analysis) headline Net delta. Static-equity rebase is the default for any param-compare here.
- **Methodology memory `project_2024_regime_shift_accumulating_signal`** — accumulating signal of H1/H2 sign-flips near 2024 boundary. Panel split for this Q must straddle 2024-02/03.
- **Methodology memory `feedback_pareto_criterion_mc_noise_floor`** — strict-strict-strict-strict criteria reject for noise alone; softest metric becomes "≤ baseline within MC bootstrap CI"; strict-inequality concentrated on highest signal-to-noise metric. Applied in §6.
- **Bust-attribution memory `project_4strategy_mc_anchor_2026_05_05`** — historical bust attribution context; per-day cap proposal sits within the Pareto-improving change pattern that closed `bust_attribution_flip` broker-feed-confirmed.

## §3 — Question (Q-GDN-DDcap)

What is the cost of Guardian's unbounded per-strategy per-day DD contribution, and does a per-day DD cap on the Guardian Pine source produce a strict-inequality improvement on at least one Pareto metric (PF / Net / DD) without degrading any other metric beyond MC bootstrap noise on the canonical Pepperstone panel?

*(Pre-Q gate symptom-only rephrase: the symptom is "Guardian's per-day DD is unbounded and is the largest single-strategy bust contributor in the current 4-strategy MC." The fix — DD cap at 2.6% — is one of several possible responses, named in §7. The question does not bake in the 2.6% threshold or the cap-vs-position-sizing-vs-time-of-day-block choice of architecture.)*

## §4 — Falsifiable hypothesis (H-GDN-DDcap)

**H-GDN-DDcap:** If a per-day DD cap of 2.6% on the Guardian Pine source produces all three of (a) PF strict-inequality improvement ≥+5% on the static-equity Pepperstone panel, (b) static-equity Net ≤ baseline within MC bootstrap 95% CI OR strict-inequality improvement, (c) static-equity DD strict-inequality improvement of ≥0.5pp, **and** survives a 2024-straddling half-panel split with both H1 and H2 above brief floor at 95% CI overlap, **and** the OANDA cross-feed confirms direction (PF and DD both improve, magnitude may differ), then the cap is load-bearing and should advance to lock evaluation; otherwise the cap is screened out, classified as panel-noise or single-feed artifact, and the symptom is logged as a Forward observation for re-test if a future Pepperstone re-export produces a different bust-attribution read on Guardian.

## §5 — Forbidden moves

- **Compounded-basis Net or DD comparison as load-bearing.** Per memory `feedback_static_equity_default_for_param_compare`, TV CSV compounding can swallow 80%+ of headline Net delta. The same-day reconcile on `8f599` vs `90bb1` shows compounded Net Δ +31.9% vs static-equity Net Δ +14.3% — a 17.6pp gap is artifact. Use static-equity for all gate evaluations; compounded shown as supplementary only.
- **Skipping the 2024-straddling H1/H2 split.** Tempting because the headline static-equity numbers are clean (PF +10%, DD −1.31pp). Memory `project_2024_regime_shift_accumulating_signal` says any 2024-spanning panel must be split-tested; Guardian specifically had a yearly PF transition that could carry an asymmetric DD-cap effect on one half only.
- **Treating Pepperstone-only confirmation as sufficient.** Tempting because OANDA cross-feed isn't yet exported. Per the 2026-04-28 two-tier canonical policy (memory `feedback_two_tier_canonical_pepperstone_oanda`), OANDA validates; without OANDA confirmation we cannot rule out a Pepperstone-specific 2.6% threshold artifact (XAUUSD has documented 16-29% stop-proximity haircut Pepperstone vs OANDA — a threshold-based rule is sensitive to that).
- **Locking the 2.6% threshold without a sensitivity check around it.** Tempting because 2.6% is what was swept. The Pareto-improvement could be a knife-edge artifact at 2.6% with 2.4% / 2.8% degrading. Sensitivity sweep across ±0.4pp (5 grid points) is gated.
- **Folding this into a single brief with DJ30 or NAS100 sweep changes.** Per memory `feedback_d_vs_s_collapse_discipline` (D-vs-S domain), parallel multi-strategy changes are S (Simplify) territory inside one brief only when they target the same mechanism; the Guardian DD cap and the DJ30 multi-axis change target different mechanisms and panels and must remain decomposed.
- **Skipping operational tooling integration in lock evaluation.** Per the 2026-05-07 lesson (memory `feedback_two_tier_canonical_pepperstone_oanda` and brief-authoring §0 sub-rule "lock procedures need an operational-tooling integration phase"), a Pine-source change that adds a per-day DD-cap input parameter must be reflected in DXTrade input documentation, in `dd_protection.py` doc comments (the per-day cap is strategy-internal but interacts with portfolio-level scaling), and in `references/baselines.md` (new Pine config block). Lock not complete until those land.

## §6 — Gate (criteria for closure)

This brief closes when one of:

- **CLOSED-RESOLVED:** All of H-GDN-DDcap's clauses (a), (b), (c) pass on static-equity Pepperstone panel **AND** both H1 (2022-01-11 → 2024-02-29) and H2 (2024-03-01 → 2026-04-20) half-panels satisfy: static-equity PF and DD point estimates both within or above the joint-panel 95% bootstrap CI **AND** OANDA cross-feed reproduces sign-direction on PF and DD (magnitude may differ — no magnitude gate cross-feed) **AND** sensitivity sweep at thresholds {2.2, 2.4, 2.6, 2.8, 3.0}% shows monotonic or near-monotonic PF/DD improvement (i.e., 2.6% is not a knife-edge optimum) **AND** 4-strategy portfolio_mc with Guardian-with-cap clears bust <1% and p99 DD <5% on canonical 2026-05-14 Pepperstone panel.
- **CLOSED-FALSIFIED:** Any clause of H-GDN-DDcap fails on static-equity Pepperstone panel **OR** H1/H2 half-panel split shows opposite-sign PF or DD effect on either half at 95% bootstrap CI **OR** sensitivity sweep shows knife-edge (2.6% optimum bounded by degradation at 2.4% AND 2.8%) **OR** OANDA cross-feed shows opposite-sign PF or DD direction **OR** 4-strategy portfolio_mc with cap fails either lock criterion.
- **CLOSED-AMBIGUOUS-HOLD:** Pareto-improvement holds on full Pepperstone panel **but** H1/H2 split is null (no significant effect on either half individually with bootstrap CI overlapping zero) **and** OANDA confirms direction. Re-opens if (i) 60 additional Guardian Pepperstone trades accumulate, OR (ii) a future re-export changes Guardian's bust-attribution rank in the 4-strategy MC.

## §7 — Methodology

Investigation sequence (each step has a verification check and may close the brief early if a clause of §6 falsifies):

1. **Phase A — Pine source verification.** Read `strategies/guardian/Guardian_Gold_v5.5.pine` (or whichever path holds the production v5.5 source) and confirm the `dailyDDCap` parameter is a clean additive guard — no interaction with `maxDailyTrades`, `maxHold`, or hour-block logic that could produce coupled effects. Reconcile the `8f599` CSV produces from the Pine source under `dailyDDCap = 2.6` (re-run the strategy tester from the Pine source with the parameter set; trade count and Net within ±1% reconcile tolerance).
2. **Phase B — Static-equity recompute on already-loaded CSVs.** Already completed in this session: PF +10.0% (3.232 → 3.559), Net +14.3% ($187K → $214K), DD −1.31pp (5.51 → 4.20). Document this as the headline reference.
3. **Phase C — H1/H2 panel split with bootstrap CI.** Split panel at 2024-02-29 / 2024-03-01. Recompute PF, Net, DD on each half for both swept (`8f599`) and locked control (`90bb1`). 1000-iter block bootstrap (block length = 30 trading days) for 95% CI on each half. Gate: both halves point estimates within or above the joint-panel CI for PF and DD; sign-direction must agree across halves.
4. **Phase D — Sensitivity sweep.** Joshua produces additional Pine sweeps at `dailyDDCap ∈ {2.2, 2.4, 2.8, 3.0}` and exports CSVs. Reconcile each via the trade-csv-reconcile skill; static-equity PF and DD as 5-point grid. Gate: monotonic or near-monotonic — point at 2.6% is not bounded by degradation on both sides.
5. **Phase E — OANDA cross-feed.** Joshua produces OANDA-feed sweep at `dailyDDCap = 2.6` and the locked-control OANDA re-export. Static-equity reconcile. Gate: PF and DD direction match Pepperstone (signs only — magnitude unfettered).
6. **Phase F — Portfolio MC at new 4-strategy config.** Spawn CC handoff to run `portfolio_mc.py` with Guardian's CSV swapped to `8f599`-equivalent (rebuilt from Pine if Phase A reconciled). Keep DJ30 / NAS / Aegis at canonical 2026-05-14 panel. Gate: bust <1%, p99 DD <5%, both lock criteria clear.
7. **Phase G — Regime-robustness gate (Q-DDP-1 pattern).** Run `analysis/time_to_pass.py --regime-check` on the new config. If criterion 5 (regime-robustness) fails, decide between (a) override-with-grounds per Q-DDP-1 / 2026-05-14 ADR template, or (b) hold pending forward `time_to_pass.py --regime-check` cadence (next 2026-08-08).

What constitutes evidence vs noise: static-equity headline magnitudes (Phase B) are evidence; bootstrap CI on H1/H2 (Phase C) is the load-bearing falsifier; OANDA sign-direction (Phase E) is the cross-feed validator; portfolio MC (Phase F) is the lock criterion.

## §8 — Findings

*(Populated as work progresses.)*

- **Robust:** Same-day Pepperstone static-equity reconcile (Phase B complete) — PF +10.0%, Net +14.3%, DD −1.31pp on the swept vs locked-control panel. Source: this brief's §0 reads, computed via reconcile.py + per-trade pct rebase, panel identical between swept and control.
- **Pending:** Phases A, C, D, E, F, G.

## §9 — Decision

*(Populated at closure.)*

## §10 — Audit hooks

```
# Verify §0 Rule 0 anchors still resolve to the claimed state
git -C C:/Users/joshu/multi_firm_operations show origin/main:firm_rules.py | grep -E '_BASE_RISK'
# Expected: includes guardian 0.0034 (allocation unchanged)

git -C C:/Users/joshu/multi_firm_operations log -1 -- dd_protection.py | head -3
# Expected: anchor commit shows DD_TRIGGER = 0.015 / DD_SCALE = 0.40 unchanged

# Verify cited swept CSV still exists with the cited hash basename
ls C:/Users/joshu/Downloads/updated_Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-17_8f599.csv
# Expected: file present

# Verify locked-control CSV referenced exists
ls C:/Users/joshu/multi_firm_operations/.claude/worktrees/admiring-saha-147572/data/tv_exports/pepperstone/Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-17_90bb1.csv
# Expected: file present (or path-update note if Joshua moves the control export)

# Verify reconcile reproduces the static-equity numbers cited in §8
python C:/Users/joshu/.claude/skills/trade-csv-reconcile/scripts/reconcile.py \
  C:/Users/joshu/Downloads/updated_Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-17_8f599.csv
# Expected: N=201, PF~3.935, Net~$596,748, DD~5.01% (compounded basis; static-equity recompute via per-trade pct ×$200K)

# Verify 2026-05-14 allocation refresh ADR exists for citation
git -C C:/Users/joshu/multi_firm_operations show origin/main:docs/adr/2026-05-14-allocation-refresh.md | head -3
# Expected: file present, status ACCEPTED
```

---

## Verification

```
# Mechanical discipline checks
python C:/Users/joshu/.claude/skills/brief-authoring/scripts/check_brief.py --type inquire docs/briefs/Q-GDN-DDcap.md
# Expected: all 6 checks PASS

# Production-source verification (Rule 0 confirmation)
# Each anchor in §0 above is runnable via §10 audit hooks; results should be captured at first run.

# Cross-reference verification
git -C C:/Users/joshu/multi_firm_operations show origin/main:docs/adr/2026-05-14-allocation-refresh.md | grep -c "ACCEPTED"
# Expected: >=1
```

If any verification command fails, the brief is not complete.
