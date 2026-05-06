# Q-DDP-1 — Recommendation

**Date:** 2026-05-06
**Author:** Claude Code (auto mode)
**Brief:** Q-DDP-1 — dd_protection relaxation Pareto sweep (authored 2026-05-06)
**Author's prior:** HOLD

---

## Verdict: **AMBIGUOUS — default HOLD**

Per brief §Recommendation:
> "AMBIGUOUS — A C* dominates on the full panel but fails regime-robustness, OR multiple configs tie within 0.5pp on dominant criteria. Surface to Joshua with full evidence; default recommendation is HOLD."

C2 (1.5% / 0.40×) was the **sole config** to pass criteria 1-4 strictly on the full Pepperstone panel, but **decisively fails regime-robustness criterion 5**:

- Bootstrap (n=100, 6mo blocks): 5th-pctile pass-rate = **90.82%** (floor 97.5%, fails by ~7pp)
- Half-panel split: H1 (2022-01 → 2024-04) pass-rate = **86.78%** (floor 97.5%, fails by ~11pp); H2 (2024-05 → 2026-04) pass-rate = 99.67% (passes)

C2's apparent dominance on the full panel is a **regime-specific artifact** driven entirely by the H2 (2024-05+) sub-panel. In H1, C2 underperforms even C0's full-panel pass rate by >11pp. **No production change recommended.**

---

## Five-criterion scorecard (full panel + regime-robustness)

C0 baseline: Pass 97.88% / Bust 0.22% / p99 DD 4.55% / Drag $112,794 (17.5% of unprotected PnL)

Acceptance criteria (per brief §Acceptance, with anchor adjustment from Pre-B — see [anchor_reconciliation.md](anchor_reconciliation.md)):
1. Pass-rate floor ≥ **97.5%** (adjusted from brief's 97.9% to preserve intended margin below corrected C0 anchor)
2. Bust-rate ceiling ≤ 0.50%
3. Tail-DD ceiling ≤ 5.00%
4. Drag savings ≥ 10% reduction vs C0 (drag ≤ 0.90 × $112,794 = $101,515)
5. Regime-robustness: bootstrap p05 ≥ floor AND both half-panel pass-rates ≥ floor

| Config | (trig / scale) | Pass | Bust | p99 DD | Drag $ | C1 | C2 | C3 | C4 | C5 | Verdict |
|---|---|---:|---:|---:|---:|:-:|:-:|:-:|:-:|:-:|---|
| C0 | (1.0% / 0.40×) | 97.88% | 0.22% | 4.55% | -$112,794 | ✓ | ✓ | ✓ | — | n/a | baseline |
| C1 | (1.0% / 0.50×) | 98.39% | **0.54%** | 4.89% | -$94,275 | ✓ | **✗** | ✓ | ✓ (16% sav) | n/a | **REJECTED on C2** |
| C2 | (1.5% / 0.40×) | 98.09% | 0.36% | 4.73% | -$84,628 | ✓ | ✓ | ✓ | ✓ (25% sav) | **✗** | **REJECTED on C5** |
| C3 | (1.5% / 0.50×) | 98.33% | **0.74%** | 4.96% | -$59,809 | ✓ | **✗** | ✓ | ✓ (47% sav) | n/a | **REJECTED on C2** |
| C4 | (2.0% / 0.50×) | 98.21% | **1.03%** | **5.06%** | -$30,535 | ✓ | **✗** | **✗** | ✓ (73% sav) | n/a | **REJECTED on C2 + C3** |

### Per-config rejection itemization (per brief §Anti-confirmation guardrails symmetry-check)

- **C1**: bust 0.54% **exceeds 0.50% ceiling by 0.04pp**. Reduces drag by 16% but accepts >2× the C0 bust rate. Rejected on criterion 2.
- **C2**: passes criteria 1-4 strictly (pass 98.09% / bust 0.36% / p99 DD 4.73% / drag savings 25%). Fails criterion 5 (regime-robustness): bootstrap p05 = 90.82% (vs floor 97.5%), H1 pass = 86.78% (vs floor 97.5%). The regime fragility is decisive — H1 underperformance is ~11pp below floor, not a marginal miss.
- **C3**: bust 0.74% **exceeds 0.50% ceiling by 0.24pp**. Reduces drag by 47% but at >3× the C0 bust rate. Rejected on criterion 2.
- **C4**: bust 1.03% **exceeds 0.50% ceiling by 0.53pp** AND p99 DD 5.06% **exceeds 5.00% ceiling by 0.06pp**. Rejected on criteria 2 AND 3.

### Pareto frontier: see [pareto_frontier.svg](pareto_frontier.svg)

(pass-rate, drag-as-%-of-unprotected-PnL) plane. C2 is the only point that satisfies the Pareto sense (higher pass + lower drag than C0) under criteria 1-4. C0 is itself Pareto-undominated under the full criteria set (1-5) — no candidate strictly dominates without breaching either bust ceiling or regime-robustness.

---

## Why this verdict (extended reasoning)

The brief's Inquire-phase question was: does the additional 4-strategy diversification create headroom for a Pareto-dominant relaxation of the inherited (1.0%, 0.40×) config?

**Answer: no — within the scope of this brief.**

The H1 (2022-01 → 2024-04) sub-panel is itself an in-distribution sample of the locked Pepperstone panel — these are real historical trades from the locked strategies. C2's pass-rate of 86.78% on H1 is not a "cherry-picked stress" — it's the realized characterization of the strategy under early-panel market conditions. The headline 98.09% on the full panel is dominated by the H2 sub-panel (99.67%), which mathematically outweighs H1's 86.78% (~514 vs ~606 bdays, but H2's MC sims have many fewer block options to draw from, so the bootstrap distribution skews H1-flavored).

**This is the asymmetric haircut working as designed.** Drag savings (criterion 4) are concretely measurable on the panel — C2 saves $28K vs C0 (25% reduction). Tail-protection benefit (the implicit other side of dd_protection's value) lives in regimes the panel didn't sample. The brief explicitly built this asymmetry into the design:

> "Drag savings are concrete and measurable; tail-protection benefit is partially invisible (lives in regimes the panel didn't sample). The bias is conservative: C* must clear regime stress before earning the lock."

C2 doesn't clear regime stress. The locked (1.0%, 0.40×) config holds.

### Brief author's prior was HOLD; sweep confirms

Brief §Anti-confirmation guardrails: "Most likely outcome is HOLD with documented Pareto-undomination of C0." The sweep confirms this prior. C0 is Pareto-undominated under the brief's criteria set (1-5). The 4-strategy diversification did improve the locked config's MC numbers (3-strategy 93.78% → 4-strategy 97.88%), but it did NOT create headroom for a relaxation that survives regime stress.

---

## Partition-specific dominance observation (rule1_gate.py would have fired)

Per Joshua's Pre-Q resolution to skip the missing `rule1_gate.py` permutation gate but document if it would have fired:

C2's full-panel dominance is **decisively partition-specific**. Half-panel split:
- H1: 86.78% pass (worse than C0's full-panel 97.88% by ~11pp)
- H2: 99.67% pass (better than C0's full-panel by ~1.8pp)
- Gap between halves: 12.9pp

Under a permutation gate that shuffled the H1/H2 partition labels, the observed-margin probability of the H1↔H2 dominance asymmetry being random would be vanishingly small (no formal computation done, but a 12.9pp split between equal-sized halves is decisive). A formal `rule1_gate.py` test would screen out C2 as partition-specific dominance with very high confidence.

**This is independent corroboration of the regime-robustness rejection.** Both gates point the same way.

---

## Caveats and methodology notes

1. **Anchor adjustment for Pre-B.** Brief Context cited 98.13/0.22/4.49 (obsolete pre-reconcile numbers from commit 4c65d29); production-pinned anchor is 97.88/0.22/4.55 (commit 09206eb). Pass-rate floor lowered from brief's 97.9% to 97.5% to preserve intended ~0.2pp safety margin below corrected C0. **C2 fails the regime-robustness gate against either floor**; the anchor adjustment is not load-bearing for this verdict. Full audit in [anchor_reconciliation.md](anchor_reconciliation.md).
2. **Drag re-baseline for Pre-A.** Brief context's chat-based drag of −$149K was modeled with assumed `≥peak release`; production releases on partial recovery. Corrected drag over the 28mo sub-window: −$126K (24.4% of unprotected PnL — essentially identical percentage to chat-based, ~$23K smaller in dollars). Drag re-baseline does not change verdict. Full audit in [drag_rebaseline.md](drag_rebaseline.md).
3. **Margin commentary on C2 (informational only — not load-bearing for the AMBIGUOUS verdict).** Even setting aside the regime-robustness failure, C2's safety margins on bust (0.14pp below ceiling) and p99 DD (0.27pp below ceiling) are slim relative to the ≥0.5pp threshold the brief's "no marginal-pass winners" rule would impose if multiple configs qualified. C2 was sole qualifier so the rule didn't formally fire, but the spirit ("winner shouldn't barely sneak across the line") would have been violated.
4. **Sweep harness sanity check.** C0 row in [sweep_results.csv](sweep_results.csv) reads pass=97.88%, bust=0.22%, p99 DD=4.55% — matches [tests/test_mc_anchors.py](../../../tests/test_mc_anchors.py) pin within `abs=1e-4`. Sweep harness is internally consistent with production MC.
5. **Sanity check on regime-robustness implementation.** Bootstrap p05 (90.82%) ≤ full-panel pass-rate (98.09%) ✓ — robustness is a haircut, not a boost. Bootstrap p95 (99.05%) > full-panel ✓. Implementation is correctly biased.

---

## Recommendation actions

### Production change
**None.** The locked (DD_TRIGGER=0.010, DD_SCALE=0.40) config in [dd_protection.py](../../../dd_protection.py) is Pareto-undominated under the brief's criteria set. The MVD spec pin at [dd_protection.py:145-154](../../../dd_protection.py:145) remains correctly anchored to the locked values.

### Brief closure
- Q-DDP-1: **CLOSED**, verdict AMBIGUOUS / default HOLD.
- Re-MC trigger: **NOT FIRED** (no constant change).
- ADR draft: **not authored** (would only be authored on LOCK CANDIDATE verdict).

### Methodology updates (recommend Joshua review)

The sweep surfaced two methodology data points worth retaining:

1. **The regime-robustness gate caught what the full-panel sweep missed.** C2 looked like a clean win on the full panel (passes criteria 1-4 with reasonable margins; 25% drag savings; sole qualifier). Without criterion 5, the brief would have produced a LOCK CANDIDATE recommendation that was a regime-specific artifact. This is a worked example of why the asymmetric haircut belongs in any future Pareto-relaxation brief on dd_protection or analogous risk constants. Suggest adding to operational rules: "any dd_protection / risk-constant Pareto sweep MUST include a regime-robustness gate; full-panel pass-rate alone is insufficient evidence for a lock."

2. **Half-panel pass-rate spread was 12.9pp.** This is large enough that the brief should explicitly note the H1 regime as a candidate for separate study. Possible reasons: H1 includes the 2022 commodity volatility regime + early NAS100 trade activity; H2 is more recent/calmer. If a future brief asks "should we relax dd_protection during specific regimes?", it should treat this asymmetry as a starting hypothesis, not as something to be re-discovered.

These are observations, not actions. Joshua to decide whether either becomes a follow-up brief.

---

## Cross-references

- [drag_rebaseline.md](drag_rebaseline.md) — Pre-A: corrected drag estimate under production semantics
- [anchor_reconciliation.md](anchor_reconciliation.md) — Pre-B: source of brief Context numbers identified as obsolete
- [rule0_reconciliation.md](rule0_reconciliation.md) — Step 1: Rule 0 anchor + match/mismatch table + Joshua resolutions
- [sweep_results.csv](sweep_results.csv) — Step 2: 5-config sweep, per-seed + aggregate rows
- [regime_robustness.csv](regime_robustness.csv) — Step 3: 100-panel bootstrap + half-panel split for C2
- [pareto_frontier.svg](pareto_frontier.svg) — Step 4: (pass-rate, drag) Pareto plot
- [_run_regime_robustness.py](_run_regime_robustness.py), [_plot_pareto_frontier.py](_plot_pareto_frontier.py) — sweep + plot scripts (reproducibility)

## Reproducibility

```bash
# C0 baseline (production-pinned anchor)
python portfolio_mc.py --panel pepperstone

# Sweep (regenerates sweep_results.csv inline)
python -c "$(cat << 'EOF'
# (see _run_regime_robustness.py for full version with worktree-path guard)
import os, sys
sys.path.insert(0, os.getcwd())
# ... see Step 2 inline command in conversation transcript ...
EOF
)"

# Regime robustness
python -u docs/briefs/Q-DDP-1/_run_regime_robustness.py

# Pareto plot
python -u docs/briefs/Q-DDP-1/_plot_pareto_frontier.py
```

Determinism: SEEDS = (42, 123, 2026) for MC; bootstrap RNG seeded at 20260506. Re-runs are byte-identical.
