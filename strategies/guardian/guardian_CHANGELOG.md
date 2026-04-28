# Guardian Gold — Changelog

Long-only XAUUSD 15min trend strategy. Pine Script v6.

**Source of truth:** `guardian_gold_v5.5.txt` holds the authoritative parameter values. This CHANGELOG records decisions, rationale, and active overlays. If the two ever disagree, the Pine file wins — fix the CHANGELOG.

Versioning begins at v5.1 (2026-04-17). Prior development history (v3.7 → v3.8 → v3.9 → v4 → v5.1) is archived in Notion under the FXIFY Command Center.

---

## [Unreleased]

_Queued changes. Move to a dated entry on commit._

- Re-MC with v5.4 Pepperstone CSV to isolate feed-level drag from v5.5 added-filter effect (noted at v5.5 lock).

---

## [v5.5 + risk 0.34%] — 2026-04-23 🔒 LOCKED

**Status:** Active on FXIFY $200K challenge. Cold-start risk **0.34%** (re-locked from 0.30% same day on expanded 52-month Pepperstone panel). Supersedes v5.4.

### Delta from v5.4
- Added blocks: **Mon H08**, **Mon H12**, **Tue H12**, **H12 signal-day latch** (blockH12Day — when any day's H12 would fire a valid trend-recovery signal on a day whose H12 is blocked, block all subsequent entries that day).
- Thu H12 block retained from v5.4 legacy (4 trades, 25% WR, +$23,131 — kept locked true; test input exposed to allow isolated unblock experiment).
- Grace mechanic: 1 bar @ 2.0× stop (vs v5.1's 3 bars @ 3.0×).

### Risk re-lock 0.30% → 0.34% (same-day)
Pepperstone-sourced CSVs (2022→2026) expanded the MC panel from ~14 months to 52 months of regime coverage, revealing headroom under the 1% bust target and 5% static DD cap. Post-relock portfolio MC (G 0.34% / S 1.00% / A 1.50%, 10K × 3 seeds): **92.73% pass / 0.65% bust (0.00% daily + 0.65% static) / 6.62% timeout**, p99 DD 4.94% (6 bp below cap), median days-to-pass 32. Iran-Israel / Hormuz conflict overlay deactivated same day — revert triggers met. See `docs/adr/2026-04-23-guardian-risk-relock-0.34.md` and `docs/overlays/guardian_conflict_risk.md` (historical record).

### Lock MC anchors (2026-04-23, pre-risk-relock)
- Alchemy reference (2026-04-20, Striker v4.4 + Aegis v4.2 era): 99.21% pass / 0.03% bust.
- Pepperstone directional: 88.45% pass / 4.68% bust raw → 84.37% pass / 1.03% bust after correcting Aegis 1R for n=1 full-stop thin-cohort artifact (median fallback inflates Aegis scale 4.4×). Bust gate passed under corrected 1R; pass-rate gap vs Alchemy attributed to feed-level drag + v5.5 added filters. Locked under brief-authorized directional read, not anchor-grade MC. Re-MC with v5.4 Pepperstone pending.

### Cross-reference
- 2026-04-23 joint version lock (commit `e40802d`, Guardian v5.5 / Striker v4.4 / Aegis v4.3)
- 2026-04-23 Guardian risk re-lock (commit `84d3cb1`)
- `docs/adr/2026-04-23-guardian-risk-relock-0.34.md`

---

## [v5.4] — 2026-04-20 (interim, superseded by v5.5)

**Status:** Interim candidate; superseded within 3 days by v5.5. No risk/allocation change at v5.4.

### Notes
Pepperstone panel integration run (Alchemy → Pepperstone feed migration). Adjusted filter set produced the baseline 2026-04-20 Alchemy MC reference (99.21% pass / 0.03% bust) against which v5.5 was later anchored. Retained `data/tv_exports/pepperstone/guardian_v5.4.csv` as a re-MC input for feed-effect isolation (see v5.5 Unreleased queue).

---

## [v5.1] — 2026-04-17 🔒 LOCKED (superseded by v5.5 on 2026-04-23)

**Status:** Historical. Was active on FXIFY $200K challenge 2026-04-17 → 2026-04-23. Cold-start risk 0.30%. Initial tracked version.

### Parameters
| Field | Value |
|---|---|
| Instrument | XAUUSD |
| Timeframe | 15min |
| Direction | Long only |
| Fast EMA | 25 |
| Slow EMA | 385 |
| Stop loss | 1.55 × ATR |
| Take profit | 29 × ATR |
| Grace stop | 3-bar, 3 × ATR |
| Breakeven | none |
| Trailing stop | none |
| MFE-BE | none |
| Session (UTC) | 08:00–16:00 |
| Days | Mon / Tue / Thu |
| Hour blocks | H14 (all days), Tue H08, Mon H09, Thu H12 |
| maxHold | 850 bars |
| maxDailyTrades | 2 |
| Risk (cold-start) | 0.30% |
| `margin_long` / `margin_short` | 0 / 0 |

### Design intent
Pure trend-rider. No exit management beyond SL / TP / grace / maxHold. Captures full ATR-extension moves without BE or trail truncation.

### Backtest (4yr full period)
Net $444,765 · PF 3.17 · RF 22.04 · Max DD $20,182 · Static DD 0% · μ/σ 1.54

### Funded-account risk ramp
| Equity | Risk |
|---|---|
| $200K (challenge) | 0.30% |
| $210K | 0.40% |
| $220K | 0.50% |
| $225K | 0.55% |

### Active overlays
- **Conflict risk overlay (2026-04-16):** per-trade risk reduced 0.55% → 0.25% pending Iran-Israel / Hormuz resolution. Revert triggers (BOTH, sustained 5 sessions): GVZ sub-25 AND Hormuz transit >50% of baseline. If signals don't fire in 8–12 weeks, extend — do not revert on calendar. See Notion: "Guardian conflict risk overlay — 2026-04-16".

### Known concerns
- Mar 2–30, 2026: worst losing streak on record, coincident with Iran conflict onset and Hormuz closure. Prompted the conflict risk overlay. Monitoring continues.

---

## Change convention

Each entry: version, date, lock status, parameters (full snapshot or delta), rationale, backtest metrics if re-run, cross-reference to Notion decision page.

Tag in git on lock: `git tag guardian-vX.Y && git push --tags`.
