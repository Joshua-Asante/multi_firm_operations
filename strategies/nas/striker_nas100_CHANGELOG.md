# Striker NAS100 — Changelog

Long breakout strategy on NAS100 (NASDAQ 100) 15min. Pine Script v6. Architecture-family sibling of Striker DJ30 v4.5 — shares entry filters, exit logic, and adaptive trail, but instrument-tuned (0.40% risk, 1000% pyramid, Mon+Tue only).

**Source of truth:** `striker_nas100_v1.pine` holds the authoritative parameter values. This CHANGELOG records decisions, rationale, and known concerns. If the two ever disagree, the Pine file wins — fix the CHANGELOG.

Versioning begins at v1.0 (released 2026-05-04, locked 2026-05-05). Pre-release lineage (v0.1 dev / B_15 label / v4.5-test branch) is archived under `archive/strategies/striker/striker_nas100_v1_research.pine` and Notion.

---

## [Unreleased]

_Queued changes. Move to a dated entry on commit._

_(none)_

---

## 2026-05-08 — Folder split + 4-strategy MC re-anchor (C2)

- **Strategy file moved `strategies/striker/` → `strategies/nas/`.** No parameter change. Codifies the architecture-family-but-instrument-tuned distinction from DJ30 (separate risk %, separate DOW set, separate pyramid size). DJ30 family stays in `strategies/striker/`. Cross-references in `REPO_MAP.md`, `docs/briefs/striker_nas100_q_nas_1_results.md`, and `docs/briefs/striker_nas100_q_nas_3_mc_addition.md` repaired in the same commit.
- **OANDA NAS100 panel landed.** `data/tv_exports/oanda/Striker_NAS100_v1_OANDA_NAS100USD_2026-05-08_74d8e.csv` added (secondary feed; Pepperstone remains canonical). `data/bar_data/NAS100USD.csv` fetched from OANDA M15 (2022-01-02 → 2026-04-19, 101,226 rows; same window as the other three instruments). `scripts/fetch_oanda_bars.py` now includes NAS100USD permanently.
- **dd_protection C2 relock (cross-ref).** Same-day relock from C0 (1.0%/0.40×) → C2 (1.5%/0.40×) re-anchored the 4-strategy Pepperstone MC. New canonical: **98.09% pass / 0.36% bust (0.00% daily + 0.36% static) / p99 DD 4.73%**, median days-to-pass 22. NAS100 bust attribution **10.2%** — lowest of the four strategies, consistent with the diversification thesis at lock. See `docs/adr/2026-05-08-dd-trigger-c2-relock.md` and `strategies/striker/striker_CHANGELOG.md` for the full ADR + DJ30 anchor record.

---

## [v1.0] — 2026-05-04 RELEASED · 2026-05-05 🔒 LOCKED

**Status:** Locked, integrated into FXIFY operational tooling 2026-05-07 after DXTrade `contractValue=10` broker-verified. Risk **0.40%** (FXIFY-deployable). Released 2026-05-04 after Phase 4C + Phase 6 closure and FINAL_LOCK verification; v1 is the first production version (predecessor v0.1 dev / B_15 archived).

### Parameters
| Field | Value |
|---|---|
| Instrument | NAS100 (NASDAQ 100) |
| Timeframe | 15min |
| Direction | Long breakout |
| Risk per trade | 0.40% (rolling-equity; compounds) |
| Daily DD cap | 1.00% |
| Total DD cap (internal kill) | 4.85% |
| Max trades / day | 2 |
| Day soft-stop | -1.5% of initial equity |
| Lookback | 15 |
| ATR length | 11 |
| ATR MA length | 85 |
| ATR expansion | 0.28 |
| Min body ratio | 0.38 |
| Stop loss | 1.20 × ATR |
| Take profit | 9 × ATR |
| BE trigger | 0.55 × ATR |
| BE pad | 0.15 × ATR |
| Trail trigger | 0.10 × ATR |
| Trail wide | 0.80 × ATR |
| Trail tight | 0.90 × ATR |
| Trail tightens at | 1.0 × ATR profit |
| maxHold | 15 bars |
| Pyramid trigger | 1.10 × ATR profit |
| Pyramid size | 1000% (vs DJ30 v4.5 350%) |
| Pyramid min bars | 6 |
| Session (UTC) | 13:00–17:00, warmup > 3 bars |
| Days | Mon, Tue (vs DJ30 v4.5 [DJ30-locked DOW set]) |
| `margin_long` / `margin_short` | 0 / 0 |
| **DXTrade `contractValue`** | **10** (default of 1 understates risk — same gotcha as DJ30) |

### Design intent
**Pyramid is the load-bearing edge.** Base entry is a qualifier; the pyramid trigger (price +1.10 ATR after ≥6 bars in profit) is where the structural edge lives. Q-NAS-1 (2026-05-05) confirms the pattern at the trade-log level:
- Base-only cohort on non-pyramid days: PF **0.314**, net **-$68,543** (n=129) — loss-making by design.
- Pyramid contribution to total profit by year: **81–99%** (2022–2026).
- Pyramid-conditional cohort WR ~75%, PF ~15.

The 1000% pyramid size on NAS100 (vs 350% on DJ30) is intentional: NAS100's trend-continuation autocorrelation is high enough that a validated continuation deserves heavy leverage. Smaller base risk (0.40% vs DJ30's 1.00%) balances the pyramid amplification — effective peak-stack risk ~4.4% on both instruments via inverse-scaled levers.

**Implication:** do not overlay base-entry filters intended to "improve" base PF. The base is supposed to be near-breakeven; the pyramid is the strategy. (See `project_pyramid_is_strategy_for_nas100.md` memory.)

### Backtest (Pepperstone NAS100 15m, 2022-01-01 → 2026-04-20, 4y4m)
Net **+$508,291** · PF **4.492** · WR **57.50%** · 200 trades · Max DD **4.56%** · RF **41.86** · all years positive · PF excl-2024 **3.121**.

FXIFY 5% static DD buffer at lock backtest: **8.8%** ($440 on the $10K rule; internal cap 4.85% lands ahead of FXIFY's 5% rule).

### Portfolio MC anchors

**2026-05-08 (C2 relock, current canonical):**
4-strategy Pepperstone (G 0.34% / DJ30 v4.5 1.00% / A 1.50% / NAS v1 0.40%, dd_protection C2 1.5%/0.40×, 10K × 3 seeds): **98.09% pass / 0.36% bust / p99 DD 4.73%**, median days-to-pass 22. **NAS100 bust attribution 10.2%** — lowest of the four; consistent with the diversification thesis at addition. OANDA pattern-spotting (3-strategy still v4.4): 96.23/0.69/4.91. Reproducible under `python portfolio_mc.py --panel pepperstone`. Pinned in `tests/test_mc_anchors.py`.

**2026-05-05 (C0 baseline at addition, historical):**
Same 4-strategy stack at C0 (1.0%/0.40×): 97.88% pass / 0.22% bust / p99 DD 4.55%, median days-to-pass 23. Bust attribution: DJ30 40.9% / G 25.8% / A 22.7% / NAS 10.6%. See `docs/briefs/striker_nas100_q_nas_3_mc_addition.md` for the addition decision audit.

### Known concerns
- **Pyramid-load fragility (live).** Pyramid-conditional cohort carries the strategy. A regime where continuation autocorrelation breaks (or where the continuation filter stops firing) collapses edge to base-only PF 0.31. Forward live-PnL tripwire applies; if pyramid contribution drops sustainably below ~70%, escalate.
- **Mon+Tue concentration.** Day-of-week footprint is narrow by design (validated empirically) but reduces the panel's regime coverage at the trade level vs broader-DOW strategies.
- **n=200 panel.** 4-year backtest sample is moderate; permutation/bootstrap CI is wide on tails. Q-NAS-1 confirmatory tests (2026-05-05) clear the design-intent claim, but tail estimates remain MC-bounded.

### Cross-reference
- `docs/briefs/striker_nas100_q_nas_1_results.md` — Q-NAS-1 pyramid-dependence confirmatory tests (2026-05-05)
- `docs/briefs/striker_nas100_q_nas_3_mc_addition.md` — joint v4.5 + NAS100 add MC results (2026-05-05)
- `archive/docs/striker_nas100/q_nas_2_capture_plan.md` — Q-NAS-2 capture plan (closed/archived 2026-05-08)
- `archive/strategies/striker/striker_nas100_v1_research.pine` — post-lock research file (archived 2026-05-07)
- `archive/analysis/striker_nas100/q_nas_1_pyramid_hypothesis.py` — Q-NAS-1 source (archived 2026-05-08)
- `strategies/striker/striker_CHANGELOG.md` v4.5 entry — sibling DJ30 lock and joint MC anchor

### FXIFY operational integration (2026-05-07)
NAS100 v1 added to `firm_rules.py` / `dd_protection.py` / `accounts.py` / `cli.py lots` after DXTrade `contractValue=10` broker-verified. `portfolio_mc.py` already covered NAS100 from the 2026-05-05 lock anchor. See `CLAUDE.md` Strategy Reference table for the operational scope.

---

## Change convention

Each entry: version, date, lock status, parameters (full snapshot or delta), rationale, backtest metrics if re-run, cross-reference to Notion decision page.

Tag in git on lock: `git tag striker-nas-vX.Y && git push --tags`.
