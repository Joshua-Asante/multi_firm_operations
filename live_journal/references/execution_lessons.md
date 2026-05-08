# Execution Lessons Registry

This file is the canonical anchor for behavioral lessons surfaced via the
live-execution-journal pipeline. Each lesson must be tied to:

1. A **dated incident** (specific trade, specific date)
2. A **dollar cost or counterfactual gain** (so the lesson is load-bearing, not ceremonial)
3. A **rule statement** in imperative form (do X, never do Y)
4. A **watch-point** (which Step 6 pattern check fires for this lesson)

**Promotion criteria:** A pattern graduates from candidate to promoted lesson
when EITHER (a) a single incident with dollar cost >$3K surfaces, OR (b) the
same pattern fires across three separate review windows. E1 and E2 promoted
on (a); E3 currently candidate awaiting (b).

**Demotion criteria:** A promoted lesson demotes if 12+ months pass without
the watch-point firing AND the structural condition that produced the lesson
no longer exists (e.g., strategy code changed in a way that eliminates the
pattern). Demotion is rare; lessons mostly accumulate.

---

## E1 — Trust the design through macro

**Status:** PROMOTED 2026-04-29

**Anchor incident:** 2026-04-07 Guardian skip during US-Iran macro-stress window.

**Counterfactual:** Backtest fired a valid Guardian XAUUSD long entry on Tue
2026-04-07. The trader skipped it on the basis that the Iran-Hormuz macro
escalation made the position too risky. The strategy held the position 13
days — through the entire macro window — and exited on 2026-04-20 at +$3,752
realized counterfactual. This was the largest single winner in the strategy
CSV for the surrounding window. The skip "to protect against macro" cost the
biggest gain.

**Rule:** Never skip a valid system signal based on a macro-volatility forecast.
The strategy's filter stack (EMA slope, BB position, ATR expansion, hour blocks,
day-of-week filters) already handles volatility regime. Discretionary overrides
on macro thesis are systematically wrong over the panel.

**Mechanism (why this fails):** The strategies were calibrated against a 52-month
Pepperstone panel that includes the 2022 hostile gold regime, the 2023 disinflation
regime, the 2024 election regime, and the 2025-2026 geopolitical regime. The
filter parameters that survived this calibration are *already adapted* to
macro-volatility periods — that's what "regime-adaptive via base signal logic"
means. Adding a discretionary macro filter on top double-adjusts what's already
captured, and the discretionary judgment systematically penalizes the right tail
(macro-volatile periods are when the strongest trends form).

**Connection to standing doctrine:** Reinforces the "no regime overlays" principle
locked 2026-04-23 (Hormuz overlay deactivated). Discretionary skips on macro
thesis are operationally equivalent to a regime overlay applied at execution
time. Same failure mode, different layer.

**Watch-point:** `check_macro_skip` in `scripts/journal_review.py`. Fires when
skip rate on tier-1 macro days (CPI/FOMC/NFP/BOJ) exceeds baseline by 1.5×
with at least 2 macro-day skips in the window.

**Output trigger:** When E1 fires, the watchlist message references this lesson
by name and dollar cost. Do NOT re-derive the rule each time — the registry is
the source.

---

## E2 — Don't decompose intended single-position holds

**Status:** PROMOTED 2026-04-29

**Anchor incident:** 2026-04-15 Aegis intra-trade discretion on USDJPY.

**Counterfactual:** Backtest fired one Aegis entry signal at 12:30 USDJPY for a
35-lot position, held to 13:45 BB-mean exit, +$6,467 realized counterfactual.
Live execution decomposed this into three separate entries totaling ~35 lots
across the same window. One of the three sub-entries hit its individual stop
loss while the other two continued. Net realized: +$362.

**Execution gap:** $6,105 ($6,467 − $362). Largest single-day execution leakage
in the 7-week 04-29 audit window.

**Rule:** When a FIRE alert specifies a single entry size, execute it as a
single entry. Do not re-enter on each minor BB-touch within the held position.
Re-entering decomposes one trade with one stop into N trades with N stops,
asymmetrically increasing tail risk. The strategy's R-budget is calibrated
against single-entry execution.

**Mechanism (why this fails on Aegis specifically):** Aegis carries 1.50%
per trade — the highest allocation in the portfolio. Splitting a single
intended 35-lot position into three sub-positions doesn't change total
exposure, but it does change DD geometry: each sub-position has its own
1R worst-case loss. The aggregate worst case for three split sub-positions
is ~3R if they all hit stops near-simultaneously, vs 1R for the single
intended position. On Aegis at 1.50% per trade, that's the difference
between -1.50% and -4.50% on a single coordinated mean-reversion failure
— directly contesting the FXIFY 5% daily DD cap.

**Connection to standing doctrine:** Aegis's BE logic IS the edge — 41% of
winners are BE-manufactured. Splitting an entry undermines the BE-manufactured
winner mechanism, because the BE trigger fires on the original entry price;
sub-entries at later prices have different effective BE points and degrade the
BE conversion rate.

**Watch-point:** `check_discretion_on_largest` in `scripts/journal_review.py`.
Fires when TAKEN-DISCRETIONARY events concentrate on the highest-allocation
strategy with at least 2 events and >50% concentration. Aegis-specifically,
the multi-fill-on-single-signal pattern (which the pairing logic flags
automatically for non-pyramid arch).

**Output trigger:** When E2 fires, the watchlist message references this
lesson by name. The discretionary detail line shows the multi-fill count
and aggregate gap, anchoring the abstract pattern to concrete dollar cost.

---

## E3 — Capture rationale at skip time, not retrospectively

**Status:** CANDIDATE (not yet promoted; awaiting either single >$3K incident
or three firings across separate windows)

**Observation:** When skipped signals are reviewed weeks after the fact, the
recall of "why I skipped" tends toward reconstruction rather than recall.
Reconstructed rationales are systematically more flattering than the
as-experienced ones — they tend to invoke risk management, market structure,
or strategy concerns that may not have been present in the moment of decision.

**Provisional rule:** One-line entry in the Notion Trade Journal at the
moment of skip — date, strategy, alert tag, one-sentence reason. If under
60 seconds of effort isn't tolerable in the moment, that itself is a signal
that the rationale being constructed is post-hoc.

**Why not yet promoted:** The dollar cost of "post-hoc rationale" is hard to
isolate from the dollar cost of the underlying skips. E1 and E2 each isolate
to a specific trade. E3 is a procedural lesson that affects rationale quality
but not directly P&L. The registry needs either a documented case where
post-hoc rationale led to a recurring failure pattern (n=3 firings of the
same masked-skip pattern), or a single incident where post-hoc rationale
produced a wrong decision with measurable cost.

**Watch-point:** Indirect — when MISSING rationale appears for ≥3 skips in a
single review window, that's evidence the discipline isn't operationalized.
Three consecutive review windows with ≥3 MISSING rationales each would
trigger promotion.

---

## Candidate watch-list (insufficient firings, not yet candidates)

These are observations that *might* graduate to candidates if the pattern
recurs. Do NOT cite as lessons; do NOT add to the registry until a clear
incident anchors them.

- **Size-cutting bias.** Hypothesis: when uncertain, the trader executes at
  smaller size than the alert specifies, capping upside without proportionally
  reducing downside. No anchored incident yet. Watch via the size-deviation
  field in TAKEN-DISCRETIONARY classification.

- **Early-exit-on-winner bias.** Hypothesis: closing winners before TP triggers
  a regret-avoidance pattern. No anchored incident yet. Watch via exit-time
  deviation in TAKEN-DISCRETIONARY classification (close_time materially
  earlier than backtest exit_time).

- **First-trade-of-day-skip bias.** Hypothesis: the first FIRE alert of any
  trading day has a higher skip rate than subsequent alerts within the same
  day. No anchored incident; would need pattern detection across dozens of
  trading days.

---

## Doctrine cross-references

These lessons interlock with standing doctrine in `fxify-challenge`:

- **fxify-challenge Core Principle 1:** "Trade the system, not your opinion."
  E1 is the operational instantiation: macro-volatility opinions are a
  specific case of "your opinion" that fail systematically.

- **fxify-challenge Core Principle 2:** "No discretionary overrides."
  E1 (skip override) and E2 (size/timing override) are both discretionary
  overrides. The registered February override on a Guardian long is the
  pre-2026-04 anchor; E1 and E2 are the post-04-23-lock anchors.

- **fxify-challenge Lesson — headlines drive markets, not physical ground-truth.**
  E1 is the execution-layer manifestation. The Hormuz overlay was rejected
  at the strategy layer; E1 catches the same logic re-entering at the
  execution layer.

The execution-lesson registry should therefore be read with `fxify-challenge`'s
Core Principles section nearby — they are the same doctrine at different
abstraction layers.

---

## Versioning & change-log

- 2026-04-29: Registry seeded with E1, E2 (promoted on single-incident anchors
  >$3K). E3 added as candidate.
- 2026-05-07: Live-execution-journal skill authored; this registry becomes the
  output reference for `scripts/journal_review.py` watch-point messages.
