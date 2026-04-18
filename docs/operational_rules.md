# Operational rules

Hard rules. No exceptions. Each rule is here because it was violated or nearly violated in the past and the correction was costly.

---

## 1. Never override a valid signal based on a macro volatility forecast

If the strategy fires a valid signal per its Pine code, take the trade. Do not skip it because of a scheduled macro event, a conflict headline, a Fed meeting, a BOJ decision, or any other forecast about what volatility might do.

**Origin:** Guardian fired a valid long during the Iran ceasefire announcement (entry 4653.26, 1:18.1 R:R). Trade was skipped on the reasoning that ceasefire-driven gold volatility was unpredictable. The trade subsequently moved in favor through breakeven. The skip had no basis in the system's measured edge — it was intuition dressed up as risk management.

**The overlay mechanism exists for this.** If a regime genuinely warrants reduced exposure, apply a risk overlay (see `docs/overlays/`). Do not improvise per-trade skips.

---

## 2. Audit production code before authoring risk-control briefs

Before writing any brief, ADR, or decision document that specifies risk-control parameters, read the current state of the code being discussed. Do not author proposals against remembered or assumed code state.

**Origin:** 2026-04-17 session. A dd_protection retune brief was authored against an assumed single-tier architecture. The actual code had a two-tier architecture with `min()` combination. Three decision iterations occurred in one session (retune → reverse → delete equity tier) because the first two iterations were arguing about code that didn't match reality.

**Workflow:** `view` the relevant file(s) before the first line of the brief. Not after. Not "I remember what it does." Before.

---

## 3. DXTrade `contractValue` for DJ30 MUST be 10

Default DXTrade `contractValue` is 1. At `contractValue=1`, Striker position sizing produces approximately **7% per-trade risk** against a 1% intended risk. This is catastrophic and silent — the platform will execute the trade without warning.

**Check:** Before any Striker trade on DXTrade, verify `contractValue=10` is set on the account symbol configuration.

**Origin:** Prop firm setup phase. Caught during Pine-to-platform parameter reconciliation. Would have been account-ending if missed.

---

## 4. Three or more consecutive losses on one strategy = normal variance

Do not adjust strategy parameters, reduce size, or skip signals in response to 3+ consecutive losses on a single strategy. This is within the normal variance distribution of every strategy in the portfolio.

**What to do instead:** Log the losing streak in the weekly review. Continue executing signals per the Pine code. Only consider intervention if ALL of the following hold:
- Losing streak exceeds 5yr backtest p99 for that strategy
- No identifiable regime shift explains it (e.g., conflict overlay applies)
- Weekly review shows systematic issue (e.g., execution slippage materially different from backtest)

**Origin:** The Algorithm (Delete before Optimize). Reactive parameter tuning during drawdown is the most common failure mode in systematic trading. Intervention during losing streaks has, historically, made things worse more often than better.

---

## 5. Pine file is the source of truth for strategy parameters

If the Pine file and any document (CHANGELOG, ADR, Notion page, README) disagree on a parameter value, the Pine file wins. Fix the document.

The only exceptions are:
- `dd_protection.py` parameters — those live in the Python pipeline, not in Pine
- `firm_rules.py` allocations — same
- Active overlays (e.g., Guardian conflict risk) — those modify risk at the sizing layer, documented in `docs/overlays/`

---

## Rule maintenance

New operational rules are added here only after a specific failure or near-miss. Do not add preemptive rules based on what might go wrong. Rules earn their place by being paid for.

Edits to existing rules must be logged with a dated entry explaining what changed and why. Rules do not silently drift.
