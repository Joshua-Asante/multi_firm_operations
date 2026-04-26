# Notice phase — findings

**Status (2026-04-25):** The original Notice/Inquire two-phase framework was
compressed under The Algorithm (`docs/methodology/observation_routing.md`).
Each finding is now routed into one of three buckets — **Closed**, **Action**,
or **Forward** — with no standing forward-loaded multi-file artefact requirement.
Standing JSON / figure / CSV outputs for closed-bucket findings were deleted in
the same compression; they are regenerable in under 5 minutes from
`notice_phase.py` if a future decision needs them. The B-series outputs are
retained because B2 routes Forward to the Q5 / Q3 question pair.

**Panel context (unchanged from prior run).** XAUUSD / US30 / USDJPY 15-min UTC
bars, NY-tz daily aggregation. Span 2022-01-02 → 2026-04-19, ~52 months. Bar
counts XAUUSD 101,461 / US30 101,245 / USDJPY 106,820. Daily counts XAU 1,336
/ US30 1,338 / JPY 1,342. See `rule0_sanity.json`.

---

## A — XAUUSD regime

### A3. ATR(14) tracks bar-range expansion through the regime shift — **Closed**

Pine-style `ta.atr(14)` on 15-min XAUUSD bars across 2022–2026 YTD shows the
RMA-smoothed ATR(14) sat within 0.6% of the contemporaneous mean bar range
in every year, including the ~5× regime jump from 2024 (mean ATR $2.95) to
2026 YTD (mean ATR $15.31). RMA-vs-SMA contemporaneous lag stayed in 1.03–1.06
across all years and *fell* slightly in 2025/2026 — the smoothed measure
tracked closer to the contemporaneous mean during the high-vol regime, not
further. Vol-regime overlay was already closed by ATR-based sizing locked in
Guardian v5.5; A3 re-confirms the auto-sizing argument at the bar-data level.
Investigated and closed; no action attached. Regenerable from
`notice_phase.py`.

### A1, A2, A4 — supporting structural findings — **Closed**

A1 (regime onset): three rolling-vol windows converge on late-Nov-2025 →
late-Jan-2026; 30-day rolling vol has not returned below 20% since 2026-01-22.
Closed — descriptive timestamp on a regime that is already fully reflected in
ATR-based sizing per A3.

A2a/A2b/A2c (drift attribution within 2026 YTD): vol elevation is pervasive
across the 24-hour cycle (Asia 2.24×, NY 2.09×, Late 3.12×); both daily-return
tails widened ~2.3× with mild left-skew increase; vol is week-concentrated
(top-5 weeks 78.3% of YTD weekly variance). Closed — bar-level structural
description. Routes to no operational change because (i) sizing is at
contemporaneous ATR, (ii) the overlay-proposal trigger discipline rules out
acting on bar-stat shifts without a live-PnL gap.

A4 (run lengths): 2026 YTD daily run-length distribution is statistically
indistinguishable from 2023–2025; trend persistence has not changed at the
daily horizon. Closed.

---

## B — Joint correlation

### B1. XAU-USDJPY sustained correlation break 2025-10-30 → 2026-01-27 — **Forward**

The XAU-USDJPY pair shows the only sustained 2026 correlation break on the
60-day rolling band test (89-day above-band run, then a second 35-day
above-band run 2026-02-06 → 2026-03-13). XAU-US30 and US30-USDJPY 2026 shifts
sit inside the historical ±1σ band and do not register as sustained breaks at
this test. Retained as B-series scaffolding for B2's forward route. File:
`B1_inflections.json`. Figure: `figures/B1_rolling_corr.png`.

### B2. 2026 correlation drift is pervasive, not event-driven — **Forward**

Trimming the top-10 |z|-day outliers *strengthens* the 2026 correlation
shift on XAU-US30 (+0.31 → +0.43) and US30-USDJPY (-0.22 → -0.40). The base
co-movement structure has shifted; outlier days attenuate rather than drive
the shift. File: `B2_event_vs_pervasive.json`.

**Forward route:** the binary question is whether the strategy-signal layer
absorbed the bar-level shift or whether the shift propagated into strategy
P&L. Cheapest falsification first:

- **Q5 (priority).** Inspect Guardian / Aegis / Striker P&L during the
  XAU-USDJPY break window 2025-10-30 → 2026-01-27 (89 days). One table.
  If P&L stats inside the window land within MC bands → signal layer
  absorbed the shift, route to **Closed**, no further action.
- **Q3 (conditional on Q5 showing breakdown only).** Full pairwise strategy-
  P&L correlation, 2024–25 vs 2026 YTD baseline, under the locked
  allocation. Q3 only runs if Q5 shows a P&L gap.

Q5 / Q3 are tracked on the parent Open Questions list. Per scope discipline,
this brief does not run them — they belong to a separate session.

**Q5 outcome (2026-04-25, second pre-Q gate test) — ESCALATE Q3 (positive-tail signal).**
Realized window cumulative scaled P&L (allocation-normalized to G 0.34% / S 1.00%
/ A 1.50% on $200K) over 64 trading days: G +17.76%, S +15.07%, A +14.77%,
**portfolio +47.60%**. Bootstrap distribution (Mon-anchored 5-day blocks per
`portfolio_mc.build_week_blocks:127`, 30K samples × 3 seeds): portfolio median
+15.72%, p95 +38.82%. Two-sided p-values: G 0.2174, S 0.1389, A 0.1729 — none
breach 0.05; **portfolio p_two = 0.0276 — breaches.** Co-movement of all three
legs into the upper tail is the signal, not any single-leg breakdown. dd_protection
sensitivity (Q5.5): signal persists and amplifies (p_two 0.0276 → 0.0159) because
protection clips bootstrap lower tail more than the realized window's intra-period
DD. **Direction is positive-tail outperformance, not breakdown-into-loss** — the
brief's "positive tail = also a regime signal" framing applies. Q3 escalation
authored separately. Reproducible: `python analysis/q5_break_window.py`. Resolution
page: [⚠️ Q5 — break-window P&L falsification — ESCALATE Q3 — 2026-04-25](https://www.notion.so/34edc0b53c118142a0c1fe26fac09179).

**No overlay proposals from observation alone.** Iran/Hormuz lesson
generalized — only a live-PnL gap vs MC justifies an overlay; bar-stat shifts
do not. If Q5 shows a gap, the response is to investigate further (Q3), not
to add an overlay.

### B3. Intraday-vs-daily structure — **Closed (supporting)**

15-min level shifts mirror daily-level shifts in direction and magnitude
across all three pairs. Rules out daily-aggregation-artefact as an
explanation for the B1/B2 observations. Closed — supporting context for B2's
forward route. File: `B3_intraday_vs_daily.json`.

---

## C — Vol clustering vs `portfolio_mc` bootstrap mechanics

### C3. Bootstrap vs empirical max-consec-neg-weeks comparison — **Closed**

For the specific metric "max consecutive strictly-negative weeks in a 32-week
horizon", the 5-day Mon-anchored block bootstrap (matching `portfolio_mc.py`
line-for-line) is *more* pessimistic than the empirical record: bootstrap
p99 = 8 weeks, empirical p99 = 5; bootstrap max = 11, empirical max = 5.
The empirical sample is mechanically bounded above by the historical max
(~6 effectively-independent overlapping windows), so the comparison cannot
prove the bootstrap is conservative in general. Single-fact finding — the
direction is the opposite of the prior-report hypothesis but does not refute
the GARCH lag-5 ACF concern, which is about within-block-sequence clustering,
not run length. Closed; contributes nothing to allocation or `dd_protection`
without an actual re-MC trigger fired by documented rules. The paired
stationary-bootstrap vs fixed-block experiment (Q6) remains gated on a
re-MC trigger. Investigated and closed; no action attached.

### C1, C2, C4 — supporting — **Closed**

C1 (empirical max-consec-neg-weeks distribution) and C2 (bootstrap-replicated
distribution) are the inputs to C3 and inherit the same Closed routing.
C4 (descriptive GARCH(1,1) fit) confirmed XAUUSD α+β = 0.965 and USDJPY
α+β = 0.964 (both above the 0.95 i.i.d.-assumption-stress threshold flagged
in the prep). Descriptive only; not used in any downstream computation. The
operational implication — paired stationary-bootstrap vs fixed-block — is
deliberately gated as Q6.

---

## Reproducibility

- Script: `notice_phase.py` (single-file, self-contained except for input bar
  CSVs at `C:/Users/joshu/prop_firm_pipeline/data/bar_data/`).
- Retained outputs: `B1_inflections.json`, `B2_event_vs_pervasive.json`,
  `B3_intraday_vs_daily.json`, `figures/B1_rolling_corr.png`, and
  `rule0_sanity.json` (Rule 0 audit dump).
- Add-back rule: any deleted A- or C-bucket artefact is regenerable in under
  5 minutes from `notice_phase.py`. Do not regenerate preemptively. Only
  regenerate to defend a specific decision under the bucket's gate
  (Closed → archive entry only; Action → required artefact; Forward →
  scaffolding for the routed question).
- Stack: pandas, numpy, scipy.stats, statsmodels (acf), arch (GARCH),
  matplotlib.
- Bootstrap mechanics in Thread C verified line-for-line against
  `portfolio_mc.build_week_blocks` (`portfolio_mc.py:127`) and `run_seed`'s
  `rng.integers(0, n_blocks, ...)` call (`portfolio_mc.py:187`).
- `portfolio_mc.py` was **not** executed during this work.

---

## Cross-references

- Methodology: [`docs/methodology/observation_routing.md`](../../docs/methodology/observation_routing.md) — three-bucket gate.
- Notion: [Claude Code brief — 1R diagnosis + Open Questions reorder + Notice phase compression — 2026-04-25](https://www.notion.so/34ddc0b53c1181199976c9b1b4effb17).
