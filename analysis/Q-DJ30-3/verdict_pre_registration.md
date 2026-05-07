# Q-DJ30-3 — Phase A pre-registration

**Date:** 2026-05-06
**Author:** Claude Code (auto mode), to be reviewed and acknowledged by Joshua before any Phase B data-touch
**Brief:** [docs/briefs/Q-DJ30-3/Q-DJ30-3.md](../../docs/briefs/Q-DJ30-3/Q-DJ30-3.md)
**Status:** PRE-EXECUTION — committed before any analysis script touches `per_trade_gap.csv` or daily-OHLC artefacts

This file pre-registers thresholds, decision rules, and verdict mapping for Q-DJ30-3 *before* any analysis touches data. It exists so the verdict cannot be retro-fit to observed numbers.

**Structural template:** [analysis/Q-DJ30-2/verdict_pre_registration.md](../Q-DJ30-2/verdict_pre_registration.md) (committed PR #38, 2026-05-06). Q-DJ30-2 established the "Phase A pre-registration as separate file with Immutability clause + Halt protocols" discipline; Q-DJ30-3 inherits that structure and adapts thresholds for partition-hypothesis (vs Q-DJ30-2's parameter-change) context.

**Immutability clause.** This file's gate thresholds, conditioning-variable definitions, strata definitions, and verdict mapping are FROZEN as of the pre-registration commit. Edits post-Phase A require a paired `docs/methodology/gate_audits/2026-MM-DD_q-dj30-3_<slug>.md` entry stating (a) what changed, (b) why, (c) which Phase the change was discovered in. Silent edits are a methodology violation per the inqhiori skill §12 audit-trail format. Q-DJ30-2's Phase B amendment (PF cardinality + pyramid contribution corrections, paired with `gate_audits/2026-05-06_q-dj30-2_pre_reg_amend.md`) is the worked precedent for how amendments are surfaced.

---

## 1. The Q (single sentence, falsifiable)

DJ30 worst-decile base-entry losses (loss/R ≤ p10) cluster on entry days where `|gap_atr_normalized|` ≥ p90 of the panel's gap distribution at a rate **≥ 5pp above the non-tail baseline rate**, **surviving Rule-1 partition-hypothesis permutation gating (p < 0.10)** and a **half-panel sanity check** (H1 and H2 lift each ≥ 0pp; spread ≤ 10pp).

---

## 2. Conditioning variable definition

`gap_atr_normalized` is a **day-level** conditioning variable, not an entry-bar property:

```
gap_atr_normalized(d) = (session_open(d) − prior_session_close(d−1)) / ATR(14, daily)(d−1)
```

where:
- `session_open(d)` = open price of the **first M15 bar at or after 13:00 UTC** on day d (the start of DJ30's locked active window per `striker_dj30_v4.5.pine` lines 105–109).
- `prior_session_close(d−1)` = close price of the **last M15 bar before 13:00 UTC on day d** (i.e. the M15 bar ending nearest to the start of the active window from the prior calendar period). For Tue entries, `d−1` is the prior Friday's session close. For Fri entries, `d−1` is Tuesday's. For pyramid legs that fire outside Tue/Fri, the gap is computed against the prior Tue/Fri session close.
- `ATR(14, daily)(d−1)` = 14-bar ATR on the daily OHLC series, evaluated at d−1 (lagging, no look-ahead).

**Daily OHLC** is derived by aggregating [data/bar_data/US30USD.csv](../../data/bar_data/US30USD.csv) (52-month M15 OANDA panel) into daily bars using a 13:00 UTC → 13:00 UTC rolling window so that "session open" coincides with DJ30's locked active-window start. **Sensitivity panel:** also compute against a calendar-day (00:00 UTC → 00:00 UTC) aggregation; if both produce qualitatively the same verdict, the 13:00-UTC convention is canonical for this Q.

**OANDA-vs-Pepperstone basis caveat.** The trade panel is Pepperstone CFD; the OHLC is OANDA. Spot-check 5 dates: aggregated daily OHLC must match Yahoo / Stooq DJI cash close to <1.5% on each. If deviations exceed this, halt and surface to Joshua before continuing — basis is a confound for the gap measurement.

**Why day-level not entry-bar.** Pine v4.5 entries fire intra-session on `rawBreakout = close > highestHigh[1]` (not session-open-gated). The mechanism the Q tests — ATR-stop sized on lagging vol being inside an actual gap-induced move — operates at the day-regime level, not at the bar level. Variable definition is independent of intra-day entry timing.

---

## 3. Strata

| Stratum | Definition | n (expected) | Use |
|---|---|---:|---|
| **Primary** | Base entries (Signal == 'Entry long') | 197 | Headline test |
| **Sensitivity 1** | All entries (incl. pyramid legs, Signal in {'Entry long', 'Entry long Add'}) | 224 | Match Pre-Q's full-corpus pre-reg |
| **Sensitivity 2** | Worst-quintile (loss/R ≤ p20) | 39 | Tail-definition robustness |
| **Sensitivity 3** | Worst ≤ −5R (≤ −$10,000) | 1 (anchor only) | Single-event diagnostic — not interpretable as evidence |

Tail count for primary = round(0.10 × 197) = **20**.
Tail count for sensitivity 1 = round(0.10 × 224) = **22**.

These mirror Q-DJ30-1's strata exactly so the harness ports cleanly.

---

## 4. Pre-registered thresholds

### 4.1 Primary gap-quantile bin

The conditioning variable is continuous; the test is binary in-bin / out-bin. Sweep four bin thresholds, treating **p90** as the primary and the others as sensitivity:

| Bin name | Threshold | Role |
|---|---|---|
| `in_gap_p80` | `|gap_atr_normalized|` ≥ panel-p80 | Sensitivity (loose) |
| `in_gap_p85` | ≥ panel-p85 | Sensitivity |
| **`in_gap_p90`** | ≥ panel-p90 | **PRIMARY** |
| `in_gap_p95` | ≥ panel-p95 | Sensitivity (tight) |

### 4.2 Verdict gates (primary 90-min, base entries n=197, tail n=20)

The harness is [analysis/Q-DJ30-1/run_tests.py](../Q-DJ30-1/run_tests.py) ported with column rename `in_window_90` → `in_gap_p90`. Three independent tests; **all three must clear** for a non-null verdict:

| Test | Statistic | Threshold | Verdict on failure |
|---|---|---|---|
| Fisher exact, two-sided | 2×2 contingency [tail × in_gap_p90] | `p < 0.10` | Below = null |
| Permutation, n=10,000, two-sided | shuffled tail-label, observed pp diff | `p < 0.10` | Below = null |
| Rule-1 bootstrap, n=1,000, on tail | `p05_tail_in_bin − p_nontail_in_bin` | **`≥ +5pp`** | Below = null |

If two of three pass at `p90`, declare AMBIGUOUS pending sensitivity sweep.

### 4.3 Phase D — half-panel sanity check (NOT canonical regime-robustness gate)

The canonical regime-robustness gate at [docs/methodology/regime_robustness_gate.md](../../docs/methodology/regime_robustness_gate.md) is for parameter-change Pareto-relaxation briefs (Q-DJ30-2's cap question is the worked example, adapting the canon's pass-rate-floor gate to a PF-relative gate at 0.95× full-panel value). **Q-DJ30-3 is structurally different** — it is a partition-hypothesis test on a clustering claim, not a parameter-change Pareto sweep. The full canonical gate fires downstream only if Q-DJ30-3 PROMOTEs to a Pine v4.6 brief proposing gap-conditional sizing.

What Phase D *does* run is a **half-panel sanity check** in the partition-hypothesis context — directly motivated by Q-DJ30-2's H1↔H2 PF spread of 59.55% (the prior that opened this Q). Adapted from Q-DJ30-2's gate but reframed for pp-lift on a clustering test:

**Split point:** trade_num 98, matching [analysis/Q-DJ30-2/verdict_pre_registration.md](../Q-DJ30-2/verdict_pre_registration.md) — H1 = 86 base trades (≈ 2022-01 → 2024-04 calendar), H2 = 111 base trades (≈ 2024-05 → 2026-04, contains 2025-02-07 anchor). Calendar-based alternate split is recorded as a sensitivity panel only.

| Sanity test | Statistic | Threshold | Verdict on failure |
|---|---|---|---|
| H1 lift | `p_tail_in_p90 − p_nontail_in_p90` on H1 trades only | `≥ 0pp` | Below = AMBIGUOUS (H2-only effect, the Q-DJ30-2 false-positive pattern) |
| H2 lift | same on H2 trades only | `≥ 0pp` | Below = AMBIGUOUS (H1-only effect — implausible given anchor lives in H2, but possible) |
| H1 ↔ H2 lift spread | `|H1_lift − H2_lift|` | `≤ 10pp` | Above = AMBIGUOUS (regime-asymmetric clustering, untreatable on locked panel) |

Failure on any one sanity test → AMBIGUOUS, even if §4.2 cleared. The Q-DJ30-2 lesson: full-panel apparent dominance can be H2-driven artifact, and the gate exists for exactly that scenario.

### 4.4 Pre-registered verdict mapping

| Outcome | Required | Verdict |
|---|---|---|
| **PROMOTE** | §4.2 all three tests clear AND §4.3 all three tests clear | Author Pine v4.6 brief proposing gap-conditional sizing; full canonical regime-robustness gate fires there. |
| **NULL** | Fisher p ≥ 0.10 OR permutation p ≥ 0.10 OR Rule-1 lift < 5pp | Close as null; SNAG tail filed as untreatable single-event diagnostic. |
| **AMBIGUOUS** | Anything else (incl. §4.2 clears but §4.3 fails; or 2-of-3 at §4.2) | Surface evidence to Joshua; default HOLD; SNAG tail filed; methodology budget redirects. |

---

## 5. Forbidden-D-test commitments (made before execution)

Per [INQHIORI §5](https://www.notion.so/34ddc0b53c1181479d7bdecc61f47078), the following operations are **FORBIDDEN** during Q-DJ30-3 execution. Any pressure to apply them HALTs execution and triggers a gate audit:

1. **Do NOT delete H1 (2022–2024) trades** because they "lack" the gap pattern. The Q-DJ30-2 H1↔H2 asymmetry is the *signal* this Q is built on; deleting H1 is the Iran-Hormuz failure pattern (encoding the conclusion in a relevance test).
2. **Do NOT condition gap definition on the 2025-02-07 anchor's specific shape** (e.g., "gap ≥ X% specifically for NFP days"). That re-imports Q-DJ30-1's failed mechanism through a side door.
3. **Do NOT delete trades on days where `gap_atr_normalized` is undefined** (e.g., session-boundary edge cases) without a written §5-permitted test. If gap is undefined for ≥3 trades, log the cause and surface to Joshua.
4. **Do NOT change the bin-quantile threshold mid-sweep.** The sweep over {p80, p85, p90, p95} is pre-committed; computing post-hoc that "p87 has the cleanest signal" is a hidden-parameter D-test.
5. **Do NOT swap Rule-1 lift threshold from 5pp to a lower number** if 5pp doesn't clear. The 5pp gate was inherited from Q-DJ30-1; any case for relaxation is a separate methodology brief, not an in-flight adjustment.

If any pressure to apply 1–5 surfaces during execution: HALT, write `docs/methodology/gate_audits/2026-MM-DD_q-dj30-3_<slug>.md`, surface to Joshua before continuing. Permitted D-tests applied during corpus prep (instrument scope, temporal scope, mechanism scope on pyramid legs as sensitivity-not-deletion) are listed in the brief.

---

## 6. Halt protocols

Per Q-DJ30-2's worked-precedent halt-protocol pattern:

- **Phase B reproduction failure** (cardinality drift, anchor-trade ID mismatch, daily-OHLC basis sanity > 1.5%) → HALT before Phase C. Surface to Joshua. Do not amend pre-reg silently — pair any amendment with a `gate_audits/` entry per §Immutability.
- **Phase D half-panel sanity reveals signal absence in BOTH halves** (i.e. neither H1 nor H2 lift clears 0pp) → HALT, surface, AMBIGUOUS verdict immediately even if Phase C passed. The Q-DJ30-2 worked example: a full-panel +24% PF that was H2-only was flagged because the gate exists for that scenario.
- **Forbidden D-test discovered mid-execution** (per §5 commitments) → HALT, write `docs/methodology/gate_audits/2026-MM-DD_q-dj30-3_<slug>.md`, surface to Joshua. Do not silently substitute a permitted test (Iran-Hormuz failure mode).
- **Locked artefact write attempted pre-verdict** (Pine v4.5, dd_protection, allocations, portfolio_mc source, MC anchor) → HALT immediately. The "DO NOT TOUCH" list in the brief is canonical; any attempted edit is a Rule 0 violation and the run is invalid.

---

## 7. Forward-queue commitment

If Q-DJ30-3 closes NULL or AMBIGUOUS, the SNAG tail mechanism on the −$11,871 / 2025-02-07 anchor is treated as **exhausted of cheap mechanism candidates on the locked panel**. The anchor is filed as a single-event diagnostic, not a class. Methodology budget redirects to:
- Aegis BOJ binary-event pause (already on forward queue per CLAUDE.md)
- NAS100 v1 live observation (candidate-not-deployed; live PnL accumulation gate)
- New strategy-candidate work (TBD)

This commitment is also frozen at pre-registration; the verdict cannot license re-opening a third Pre-Q gate on the same anchor (the methodology-budget discipline that motivated picking gap-magnitude over realized-vol or S&P range as the single Q-DJ30-3 candidate).

The continuous Spearman-ρ framing on `|gap|` vs loss/R is **deferred** — opened only if this binary framing returns null AND the mechanism remains live on independent evidence (e.g. a second −5R-or-worse base-trade event that is also large-gap-proximate). Three Pre-Q gates on one signal class is the failure mode this discipline exists to prevent.

---

## 8. What this pre-reg does NOT pre-commit

- The exact form of the closure artefact — see §4.4 verdict mapping (NULL → `findings/YYYY-MM-DD_dj30_gap.md`; AMBIGUOUS → `findings/YYYY-MM-DD_dj30_gap.md` per Q-DJ30-2 sentinel precedent; PROMOTE → `docs/briefs/Q-DJ30-3/recommendation.md` only after downstream Pine v4.6 brief clears canonical regime-robustness gate).
- Whether to author a Pine v4.6 brief on PROMOTE — that decision is downstream and Joshua-gated.
- Any change to `dd_protection.py`, `striker_dj30_v4.5.pine`, allocations, or MC anchor — all out of scope for Q-DJ30-3 at any verdict.

---

## 9. Audit attestation

This file is authored at Phase A of the Q-DJ30-3 execution plan, before:
- any `gap_atr_normalized` value was computed for any trade
- any quantile bin threshold was evaluated against the panel
- any half-panel split was inspected for signal preservation
- any data was loaded by `analysis/Q-DJ30-3/aggregate_m15_to_daily.py` or downstream scripts

Git commit history of this file is the canonical audit anchor. Any commit modifying gate thresholds, conditioning-variable definition, strata definitions, or verdict mapping after the pre-registration date is a methodology violation unless paired with a `gate_audits/` entry as specified in the Immutability clause above.

**Joshua acknowledgment:** \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ (date / signature)
