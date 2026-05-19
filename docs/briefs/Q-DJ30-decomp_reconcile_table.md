# Q-DJ30-decomp — single-axis decomposition reconcile table

**Status:** Inputs registered, decomposition computed. Pre-Q brief NOT YET AUTHORED.
**Authored:** 2026-05-17
**Author:** Joshua + CC executor (spawn brief)
**Spawn brief:** `CC-Spawn: DJ30 swept-parameter decomposition` (this session)
**Purpose:** Decompose the joint (`1e83b`) configuration against the baseline by isolating the marginal effect of each of three axes — risk, pyramid, BT-mode — so the eventual Pre-Q (`Q-DJ30-decomp`) can reason about which axis is load-bearing.

---

## §0 — Configuration anchors

Panel: `2022-01-01 → 2026-04-20`, Pepperstone US30 15m, 213 baseline trades.

| Config | Hash | Description | Pine state |
|---|---|---|---|
| Baseline | `98bf2` | Pre-2026-05-14 lock proxy | BT-**ON**, risk 1.00%, pyramid 350, max daily DD 1.00% |
| Variant A | `953f2` | Risk-only sweep | BT-ON, **risk 0.70%**, pyramid 350, max daily DD 1.00% |
| Variant B | `ac9a9` | Pyramid-only sweep | BT-ON, risk 1.00%, **pyramid 750**, max daily DD 1.00% |
| Variant C | `c0b35` | BT-mode-only sweep | **BT-OFF**, risk 1.00%, pyramid 350, max daily DD 1.00% |
| Variant D | `9a714` | dDD-only sweep (BT-ON regime) | BT-ON, risk 1.00%, pyramid 350, max daily DD **1.15%** |
| Joint / "best setting" | `1e83b` ≡ `902aa` | All swept axes combined; Joshua's "best setting found" for Striker DJ30 | BT-**OFF**, risk **0.70%**, pyramid **750**, max daily DD **1.15%** |

All five CSVs staged at `data/tv_exports/pepperstone/.sweep/` (gitignored, not committed). Hash suffixes preserve TV-export provenance. `902aa` is byte-identical to `1e83b` (verified via `diff -q`; same backtest output, different filenames).

**Brief deviations from the original spawn (registered during execution):**
1. Original spawn brief listed axis C as a numeric day-soft-stop sweep (`-2.00% → -1.15%`). Joshua corrected at the executor's §0 halt: **axis C is the BT-mode boolean** (`backtest_mode` Pine toggle, compounded sizing vs static-equity sizing).
2. The joint config has max daily DD **1.15%**, not 1.00% as initially registered during the screenshot stream. This means the joint differs from the baseline on **four axes**, not three — the dDD shift 1.00 → 1.15 is a **fourth axis that was NOT decomposed** by the A/B/C single-axis sweeps. See §3 for the implication on the additivity check.
3. **Canonical-CSV doctrine update (2026-05-17, mid-session):** Joshua named BT-**OFF** as the canonical Pine state for all future CSV analysis. The decomposition's "baseline" (BT-ON) is now the **deprecated** state, not the canonical reference. The decomposition characterizes axes from the deprecated baseline TO the canonical best-setting; the directional framing throughout this artifact reflects this doctrine.

---

## §1 — Per-config metrics (compounded vs static-equity rebase)

Compounded basis reads `Net P&L USD` directly from each Exit row (TV's default; reflects equity-scaled position sizing).
Static-$200K rebase walks equity per trade: `per_trade_equity_pct = Net P&L USD / equity_at_entry`, then `static_pnl = pct × $200,000`. This converts the compounded view to the FXIFY-comparable view (static initial capital, no compounding).

**Important methodology pin (correcting the spawn brief):** the spawn brief proposed `static_pnl = Net P&L % × $200K`. That formula is wrong because the CSV's `Net P&L %` column is **per-notional** (e.g. trade #1's −0.13% = −$2,016 / $1.55M notional), not per-equity. The correct rebase walks equity from `Net P&L USD`. The Cumulative P&L % column is static-denominated (verified: trade #1's −1.01% ≈ −$2,016 / $200K).

### Compounded basis

| Config | N | WR % | PF | Net P&L | DD % (TV, intrabar) | DD % (bar-close) | Pyr share | DD-Limit | Max Hold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Baseline 98bf2** | 213 | 73.24 | 2.825 | **$360,586** | 4.70 | 4.36 | 35.5% | 0 fires, $0 | 2 fires, +$41,843 |
| Variant A `953f2` | 217 | 73.27 | 2.748 | $216,826 | 3.30 | 3.05 | 35.9% | 0 fires, $0 | 2 fires, +$23,217 |
| Variant B `ac9a9` | 212 | 73.11 | 3.172 | $674,561 | 7.80 | 8.82 | 49.7% | 0 fires, $0 | 2 fires, +$100,888 |
| Variant C `c0b35` | 210 | 69.52 | 2.347 | $260,709 | 4.94 | 4.67 | 28.0% | **20 fires, −$45,820** | 2 fires, +$38,032 |
| **Joint 1e83b ≡ 902aa** | 216 | 72.69 | 3.330 | $432,565 | **5.30** | 6.22 | 36.1% | **21 fires, +$78,175** | 2 fires, +$55,563 |

### Static-equity ($200K) rebase

| Config | N | WR % | PF | Net P&L | DD % | Pyr share | DD-Limit $ | Max Hold $ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Baseline** | 213 | 73.24 | 2.640 | **$213,489** | 3.41 | 36.3% | $0 | +$18,301 |
| Variant A | 217 | 73.27 | 2.624 | $150,568 | 2.56 | 36.5% | $0 | +$12,871 |
| Variant B | 212 | 73.11 | 2.867 | $315,870 | 5.82 | 52.6% | $0 | +$32,553 |
| Variant C | 210 | 69.52 | 2.270 | $173,570 | 3.74 | 28.2% | −$25,927 | +$18,282 |
| **Joint** | 216 | 72.69 | 3.099 | $241,736 | 4.10 | 38.3% | +$43,811 | +$22,950 |

Cascade share (= 1 − static_net / compounded_net) per config: baseline 40.8%, A 30.6%, B 53.2%, C 33.4%, joint 44.1%. Heavier pyramids amplify cascade (B is highest at 53.2%); lower risk dampens it (A is lowest at 30.6%).

---

## §2 — Marginal-effect deltas (static-equity basis, FXIFY-comparable)

| Variant | Δ Net | Δ Net % | Δ PF | Δ DD-pp | Δ WR-pp |
|---|---:|---:|---:|---:|---:|
| A (risk 1.00 → 0.70) | −$62,921 | −29.5% | −0.016 | −0.85 (less DD) | +0.03 |
| B (pyramid 350 → 750) | +$102,381 | +48.0% | +0.227 | **+2.41 (more DD)** | −0.13 |
| C (BT-ON → BT-OFF) | −$39,919 | −18.7% | −0.370 | +0.33 (more DD) | **−3.72** |
| Joint | +$28,247 | +13.2% | +0.459 | +0.69 (more DD) | −0.55 |

Per-axis read:

- **Axis A (risk 1.00 → 0.70).** Almost-pure linear scaling. WR and pyramid-share essentially unchanged; PF drops a hair (−0.016) reflecting the small +4 trade-count drift (lower risk → less daily-DD pressure → +4 entries on borderline-pressure days). The DD improvement (−0.85pp) is what you'd expect from a 30% risk reduction.
- **Axis B (pyramid 350 → 750).** Largest single Net contributor (+48% Net) AND largest single DD cost (+2.41pp). Pyramid share climbs from 36% → 52.6% (pyramid becomes majority contributor under 750). The 5.82% standalone DD is approaching the 6% headroom the regime-robustness gate typically demands; a 750-pyramid lock candidate would need to pass that gate.
- **Axis C (BT-OFF).** Net cost is −18.7%, but the load-bearing finding is the **−3.72pp WR drop** and the **DD-Limit going from 0 fires to 20 fires**. BT-OFF doesn't just rescale sizing — it changes which mechanism gates daily losses. See §4 anomaly notes.

---

## §3 — Additivity check

| Basis | Σ marginals (A+B+C) | Joint actual | Cross-axis interaction | Interaction share of joint |
|---|---:|---:|---:|---:|
| **Compounded Net** | +$70,338 | +$71,979 | +$1,641 | **+2.3%** |
| **Static-equity Net** | **−$460** | **+$28,247** | **+$28,707** | **+101.6%** |
| Static-equity DD-pp | −1.89pp (less DD) | −0.69pp | +1.20pp (more DD vs Σ-prediction) | — |

The two bases tell completely different stories. **This is the load-bearing finding of the decomposition.**

- **On compounded basis, the axes are linearly additive (2.3% interaction).** Marginal Σ predicts joint within $1.6K of actual. A reader looking at TV's default compounded numbers would conclude that the three changes are decoupled and a Pre-Q can treat them independently.
- **On static-equity basis, the marginal sum is essentially zero (−$460); the joint gain is +$28K, all of which is cross-axis interaction.** No single axis predicts the joint outcome under FXIFY-comparable accounting. The +13.2% joint Net is a synergy term that doesn't decompose.

**Mechanism:** the compounded-basis near-additivity is a side-effect of the cascade. Compounding amplifies each axis's effect proportionally, knitting them together into an apparent linear sum. Once compounding is removed (static rebase), the real interaction structure becomes visible — risk and pyramid effects only "see" each other through the daily-DD mechanism, which itself only fires in BT-OFF mode.

**Caveat — 4-axis gap RESOLVED (2026-05-17, mid-session): dDD axis is degenerate under BT-ON.** Variant D (`9a714`, BT-ON, r=1.00, pyr=350, **dDD=1.15**) was produced as the gap-closure variant. Its output is **byte-identical to baseline `98bf2`** (`diff -q` clean). Changing dDD from 1.00% to 1.15% under BT-ON produces zero change in the backtest because the DD-Limit mechanism never fires under BT-ON (compounded equity grows fast enough that 1% of running equity always exceeds any single-day P&L excursion — same mechanism behavior as §4.1's 0/0/0 fire-count rows). The threshold value is a no-op.

**Restatement of the additivity finding:** the +$28,707 cross-axis interaction is genuine 3-way A×B×C, NOT a contaminated 3-of-4 reading. The A/B/C single-axis sweeps are a complete decomposition for the BT-ON regime. Axis C (BT-mode) is the **gateway parameter**: it doesn't just toggle sizing-basis, it also activates the daily-DD mechanism. The dDD parameter is degenerate-when-C=ON, load-bearing-when-C=OFF — coupling by Pine mechanism design, not by accident. This means the joint's dDD=1.15 is genuinely co-moving with axis C and the decomposition captures it correctly through the C marginal + cross-axis interaction.

A remaining open question — narrower than the original 4-axis gap: under BT-OFF specifically, does dDD=1.15 vs dDD=1.00 matter? Variant C (BT-OFF, dDD=1.00) had 20 DD-Limit fires; joint (BT-OFF, dDD=1.15) has 21. A 6th variant (BT-OFF, r=1.00, pyr=350, **dDD=1.15**) would isolate that. Cost: one TV export. Not strictly needed to surface the best-setting candidate, but tightens the "is the 1.15 specifically load-bearing vs the 1.00" sub-question.

**Implication for the Pre-Q:** a parameter lock-decision cannot use single-axis marginals as the evidence basis. Either:
- The Pre-Q must include the **joint configuration as its own arm** (not derivable from A/B/C marginals), or
- The decomposition is re-formulated as a 2×2×2×2 design covering all 16 corners (risk × pyramid × BT-mode × dDD) to characterize the interaction surface, or
- A minimal patch: produce a single `dDD-only` variant to close the 4-axis gap and re-run additivity.

---

## §4 — Anomaly notes (§2.9)

### §4.1 — DD-Limit is BT-mode-gated

DD-Limit fires:

| Config | DD-Limit fires (raw count) |
|---|---:|
| Baseline (BT-ON) | **0** |
| Variant A (BT-ON, risk 0.70) | **0** |
| Variant B (BT-ON, pyramid 750) | **0** |
| Variant C (BT-OFF) | **20** |
| Joint (BT-OFF) | **21** |

The max-daily-DD soft-stop (1.00% per Joshua's spec) **never fires under BT-ON across baseline / A / B**. It only fires under BT-OFF. Plausible mechanism: the daily-DD trigger references current equity (compounded) under BT-ON, and as equity grows from $200K → $360K over the panel, 1% of the running equity is large enough that no single-day P&L excursion trips it. Under BT-OFF, the same 1% trigger references static $200K and fires regularly on losing days early in the panel.

**Load-bearing for the Pre-Q:** the brief's "axis C" is not a clean BT-mode swap — it's a coupled (sizing-basis, daily-DD-mechanism) change. The DD-Limit P&L sign-flip (−$26K on C → +$44K on joint, static basis) is real signal: the DD-Limit fires on different days when the position sizing changes (A risk reduction), and those different days happen to be more profitable on net. This is also why joint static-DD (4.10%) is lower than B-alone static-DD (5.82%) — turning BT-OFF reintroduces the daily-DD cap that was dormant on B.

### §4.2 — Pyramid share

| Config | Pyr share (compounded) | Pyr share (static) | Pyr exits (n) |
|---|---:|---:|---:|
| Baseline | 35.5% | 36.3% | 26 |
| Variant A | 35.9% | 36.5% | 26 |
| **Variant B** | **49.7%** | **52.6%** | 26 |
| Variant C | 28.0% | 28.2% | 23 |
| Joint | 36.1% | 38.3% | 20 |

Baselines.md anchor: "~94% under pre-2026-05-14 v4.5 (pyramid 350%)" — **none of these configs reproduce that anchor**. The 36% baseline pyramid share suggests the v4.5 pyramid-share-94% claim was either methodology-specific (different decomposition) or stale. The pyr_exits count (26) is consistent across BT-ON configs; the BT-OFF configs have fewer pyramid exits (23, 20), suggesting BT-OFF prevents some pyramid adds (likely the DD-Limit firing before the pyramid trigger fires).

No standalone variant trips the "sub-50% on pyramid arch is a red flag" guidance from the trade-csv-reconcile skill — Variant B at 52.6% is barely above the floor. But none are at the expected ~94%, suggesting the skill's expected-pyramid-share anchor itself needs a refresh.

### §4.3 — Max Hold

Identical fire count (2) across all five configs — same two trades hit max-hold across every Pine state. Dollar contribution scales with sizing (baseline +$18K static; B +$33K static; joint +$23K static). Not anomalous; just confirms that max-hold behavior is independent of the three swept axes.

### §4.4 — Bar-close vs intrabar DD gap

TV's "Max equity drawdown" includes intrabar peak-to-trough; bar-close walk from `Net P&L USD` misses unrealized-position lows. Gap is consistent (TV reads ~0.3–1.0pp deeper than bar-close walk per config), except Variant B where TV reads **shallower** than bar-close (7.80% vs 8.82%) — that's worth a small follow-up; possibly TV's intrabar window doesn't capture the worst-bar of a pyramid-deep day. Not a blocker.

---

## §4.5 — "Best setting found" candidate position

Joshua identified the joint configuration (CSV `1e83b` ≡ `902aa`) as his **best-setting candidate** for Striker DJ30 (mid-session, 2026-05-17):

| Parameter | Value | Δ vs current locked (2026-05-14 ADR) |
|---|---:|---|
| Pine version tag | v4.5 | unchanged |
| BT-mode | **OFF** | **CHANGED** (locked = ON) — **doctrine update**: BT-OFF is canonical going forward |
| Risk per trade | 0.70% | −0.05pp vs locked 0.75% |
| Max daily DD soft-stop | 1.15% | new field; locked Pine had this set differently — verify |
| Pyramid add | 750 | +250 vs locked 500 |

**Headline metrics for the best-setting (902aa, TV intrabar basis):**

| N | WR | PF | Net | DD |
|---:|---:|---:|---:|---:|
| 216 (157W/59L) | 72.69% | 3.33 | +$432,564.79 (+216.28% compounded) | $17,291 / 5.30% |

This is the candidate that the eventual Pre-Q (`Q-DJ30-decomp` or successor) will gate. Pre-lock requirements before this can replace the 2026-05-14 ADR's config:

1. **Portfolio MC at the new config** — re-run `portfolio_mc.py --panel pepperstone` with the 4-strategy portfolio at this CSV's implied 1R, validating that lock criteria (bust < 1%, p99 DD < 5%) clear with margin.
2. **Regime-robustness gate** — H1/H2 split + 6mo block bootstrap on the locked panel, since this is a Pine-source change (BT-mode + pyramid both change Pine state) and a risk-constant adjacent change (risk + dDD).
3. **DD-Limit characterization** — confirm whether the 21 DD-Limit fires are FXIFY-compliant on a live-extended panel (no single-day excursion exceeds the FXIFY daily loss cap before DD-Limit catches it).
4. ~~**dDD axis gap closure** — produce one `dDD-only` variant to characterize the dDD contribution independent of the other three axes (per §3 caveat).~~ **CLOSED** by Variant D (`9a714`, 2026-05-17): dDD axis is degenerate under BT-ON, so the 3-axis decomposition is complete for the BT-ON regime. Under BT-OFF the dDD effect remains coupled to axis C by Pine mechanism design; a narrower follow-up variant (BT-OFF, r=1.00, pyr=350, dDD=1.15) would isolate dDD-within-BT-OFF if Joshua wants to gate "is dDD=1.15 specifically load-bearing vs dDD=1.00" before locking the best-setting candidate.
5. **ADR delta** — supersedes or amends the 2026-05-14 allocation refresh ADR; needs explicit handling of: (a) Pine version tag (does this become v4.6?), (b) the "Key Principle: pipeline never touches strategy parameters" CLAUDE.md statement, which this candidate breaches further.

This artifact's role is to surface the candidate and its evidence basis. **It does NOT close the lock decision.**

---

## §5 — What this decomposition DOES NOT establish

- **Whether the joint config is a lock candidate.** The +13.2% static-Net gain at +0.69pp DD-cost is suggestive of a Pareto-improvement, but: (a) the +0.69pp DD-cost is on bar-close basis; TV-intrabar DD goes 4.70 → **5.30pp** (+0.60pp) on the joint per the 902aa screenshot, which is more favorable than the bar-close walk suggests; (b) no portfolio-MC has been run on this Pine state; (c) the regime-robustness gate has not been executed on the joint config. See §4.5.
- **Whether to revert the 2026-05-14 allocation refresh.** The 2026-05-14 refresh locked DJ30 to risk 0.75% / pyramid 500% / BT-ON. Joint here is risk 0.70% / pyramid 750% / BT-OFF / dDD 1.15% — a different vector entirely, AND the BT-mode shift is a new doctrine update beyond just allocation. The decomposition doesn't comment on the refresh's own merits.
- **The shape of the interaction surface.** With only 4 corners measured (baseline + 3 marginals + 1 joint) and a fourth axis (dDD) co-moved with the joint, the 16-corner interaction structure is underdetermined. A 2×2×2×2 sweep or at minimum a dDD-only variant would close the gap.
- **The dDD axis effect in isolation.** The dDD shift 1.00 → 1.15 in the joint is contaminated with the BT-mode, risk, and pyramid changes. A dedicated dDD-only variant is needed.

---

## §6 — Downstream actions

1. **Author the Pre-Q (`Q-DJ30-decomp`)** with this table as its §0 evidence base. The Pre-Q must include the joint configuration as its own arm (per the additivity finding) or pivot to a 2×2×2 design.
2. **Verify pyramid-share-expected anchor in [baselines.md](C:/Users/joshu/.claude/skills/trade-csv-reconcile/references/baselines.md)** — the "~94% pyramid share" claim for pre-2026-05-14 v4.5 does not reproduce on baseline `98bf2`. Either methodology-stale or anchor-stale. Update or remove.
3. **Strengthen the trade-csv-reconcile skill's static-rebase guidance.** The spawn brief's `Net P&L % × $200K` formula is wrong; walk-equity from `Net P&L USD` is the correct method. Update the skill's Step 6 docs.
4. **Investigate DD-Limit BT-mode coupling in Pine.** If axis C is intended to be a pure sizing-basis swap, the daily-DD mechanism should not also change. If the coupling is intentional, document it. Either way, the Pre-Q's axis-C arm needs to be characterized correctly before it can be a candidate.

---

## §7 — Methodology lessons (candidates for capture)

- **Compounded vs static-equity additivity diverges sharply.** A decomposition that looks linear-additive on compounded basis can be 100%-interaction on static basis. **Always run both rebase bases for axis-decomposition work; never trust compounded-only additivity.** Sibling lesson to the existing 2026-05-17 Q-GDN-DDcap finding (81.4% of headline net delta was compounding cascade).
- **`Net P&L %` in TV CSVs is per-notional, not per-equity.** Static-equity rebase requires walking equity from `Net P&L USD`. The Cumulative P&L % column is static-denominated (initial $200K) but mixes compounded numerator with static denominator. Brief authors should not propose `Net P&L %  × $200K` rebase.
- **BT-mode is not a pure sizing swap.** At least in the current Striker DJ30 Pine, toggling BT-OFF changes daily-DD mechanism behavior (0 fires → 20 fires). Any axis-C swap in a future brief should declare whether it is "sizing-basis only" or "sizing-basis + daily-DD mechanism".
- **Parameters can be degenerate under control flags — a single-axis sanity sweep detects it.** Under BT-ON, the dDD parameter has zero effect (Variant D byte-identical to baseline). Without the dDD-only variant, the brief author would have spent budget on a clean dDD-isolation sweep that produces no signal. **Recommended pattern:** before extending a decomposition to a new axis, produce a 1-CSV sanity sweep at the axis's candidate value while holding the other axes at baseline. If the result is byte-identical to baseline, the axis is degenerate in that regime and the decomposition collapses by one dimension — saving the rest of the sweep budget for axes that actually move.
- **Hash-suffix CSV naming + descriptive variant labels.** Joshua's TV-export hash suffix (`_98bf2`, `_953f2`, etc.) is the tamper-anchor; the brief-author's descriptive name (`_baseline`, `_decompA_risk070`) is the role-anchor. Compose both in staging filenames (e.g. `..._decompA_risk070_953f2.csv`) so the variant role is parseable but provenance is preserved.

---

## §8 — Audit hooks

```
# Reproduce the static-equity decomposition
$ python scripts/q_dj30_decomp_analysis.py
# Expected: per-config metrics + marginal-effect table + additivity check.

# Verify the 5 staged CSVs reconcile to the headline numbers
$ for h in 98bf2 953f2 ac9a9 c0b35 1e83b; do
    python C:/Users/joshu/.claude/skills/trade-csv-reconcile/scripts/reconcile.py \
      data/tv_exports/pepperstone/.sweep/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-17_*_${h}.csv | tail -8
  done
# Expected per-CSV: N matches §1 table column 2; PF, Net match §1 row.

# Confirm staging-only (no canonical-tree contamination)
$ git status -s data/tv_exports/pepperstone/.sweep/
# Expected: all 5 files untracked (.sweep/ is gitignored)
```

---

## §9 — Provenance

- Spawn brief (executor handoff): inline in this session
- Analysis script: `scripts/q_dj30_decomp_analysis.py`
- Methodology references:
  - `feedback_static_equity_default_for_param_compare` (memory) — static rebase discipline for parameter compares
  - `project_canonical_bt_off_static_replacement_2026_05_17` (memory) — BT-OFF + static-equity methodology heritage
  - [trade-csv-reconcile skill](C:/Users/joshu/.claude/skills/trade-csv-reconcile/SKILL.md) — pipeline this analysis follows
- Worktree branch: `claude/funny-pasteur-2e752c` (note: this branch predates the 2026-05-14 allocation refresh ADR; for the eventual Pre-Q artifact this should be rebased onto `main` so the ADR is in scope)
