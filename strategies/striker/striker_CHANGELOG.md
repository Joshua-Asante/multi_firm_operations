# Striker DJ30 — Changelog

Long breakout strategy on DJ30 (US30) 15min. Pine Script v6.

**Source of truth:** `striker_dj30_v4.5.pine` holds the authoritative parameter values. This CHANGELOG records decisions, rationale, and known concerns. If the two ever disagree, the Pine file wins — fix the CHANGELOG. Prior locked versions are in `archive/`.

This file covers Striker DJ30 only. Striker NAS100 (architecture-family sibling — separate risk/DOW/pyramid tuning) was split out to `strategies/nas/striker_nas100_v1.pine` on 2026-05-08; see `strategies/nas/striker_nas100_CHANGELOG.md`.

Versioning begins at v4.3 (2026-04-17). Prior development history (v3.1 → v4.1 → v4.2 rejected → v4.3) is archived in Notion.

---

## [Unreleased]

_Queued changes. Move to a dated entry on commit._

- **v5 architectural rebuild** — priority #1 post-challenge pass. Hypothesis: strip BE/trail/T1 management following the Guardian v4 → v5.1 pattern, lift μ/σ from 1.24 toward portfolio average. See Notion: "Striker v5 architectural rebuild — priority #1 post-challenge — 2026-04-17".

---

## 2026-05-17 — Canonical reference panel migrated to BT-OFF + static-equity

No parameter change. Canonical Pepperstone reference panel for Striker DJ30
v4.5 moves from `Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv`
(BT-ON compounded, n=224 = 197 base + 27 pyramid) to `Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-17_c0b35.csv`
(BT-OFF, n=210 = 185 base + 25 pyramid). Static-equity recomputation
(per-trade `Net P&L USD × (INITIAL / equity_at_entry)`) is the new
FXIFY-equivalent headline.

### Headline (BT-OFF + static-equity, 2026-05-17 canonical)
| Metric | Compounded (TV) | Static (FXIFY-equivalent) |
|---|---:|---:|
| N | 210 (185 base + 25 pyramid) | 210 |
| WR | 69.52% (146W / 64L) | 69.52% |
| PF | 2.347 | **2.27** |
| Net P&L | +$260,708.70 | **+$173,569.89** (+86.78% on $200K) |
| Max DD % | 4.70% | **4.72%** |
| Max DD $ | — | $9,490.13 |
| RF | — | 18.29 |
| 1R (mean full-stop, n=47) | — | $2,593.29 |

Static/compounded Net ratio = **67%**.

**BT-mode trade-count delta:** BT-ON 12175 panel had 197 base + 27 pyramid =
224 trades; BT-OFF c0b35 has 185 base + 25 pyramid = 210 trades. 14 trades
(12 base + 2 pyramid) that fire under deterministic BT-ON fills do not fire
under BT-OFF's pessimistic intra-bar resolution. WR profile shifts modestly
(higher WR under BT-OFF — losing entries don't fire).

### Methodology change rationale
See [`data/reconciles/2026-05-17_guardian_bt_off_static_canonical.md`](../../data/reconciles/2026-05-17_guardian_bt_off_static_canonical.md)
for the full methodology change documentation. Pine sizing line
`calcSize(stopDist) => risk = strategy.equity * (riskPerTrade / 100)` is
the same on DJ30 as on Guardian (user-confirmed 2026-05-17).

### Reconcile vs prior BT-ON anchor
- 05-05 BT-ON panel (`12175.csv`): retained on disk + in SHA256SUMS as
  historical reference; no longer the canonical reference.
- v4.5 §"Portfolio MC anchors (2026-05-05)" table below retained unchanged
  — captures the 4-strategy MC at the v4.5 lock decision under the prior
  compounded panels. The current 4-strategy MC will re-anchor in Stage 3
  of this methodology cascade against all four new BT-OFF panels.

---

## 2026-05-08 — NAS100 split-out + dd_protection C2 relock (cross-ref)

- **`striker_nas100_v1.pine` moved `strategies/striker/` → `strategies/nas/`.** No DJ30 parameter change; DJ30 v4.5 stays in this folder. The split codifies the architecture-family-but-instrument-tuned distinction (NAS: 0.40% / 1000% pyramid / Mon+Tue; DJ30: 1.00% / 350% pyramid / [DJ30-locked DOW set]). Cross-references repaired in `REPO_MAP.md`, `docs/briefs/striker_nas100_q_nas_1_results.md`, and `docs/briefs/striker_nas100_q_nas_3_mc_addition.md`.
- **dd_protection C2 relock — 4-strategy MC re-anchored.** Same-day relock from C0 (1.0%/0.40×) → C2 (1.5%/0.40×) after `bust_attribution_flip` closed broker-feed-confirmed (Pepperstone+OANDA TV re-export) and Q-DDP-1's C2 sweep showed risk-controls-met + median-pass-time benefit. New canonical 4-strategy Pepperstone MC: **98.09% pass / 0.36% bust (0.00% daily + 0.36% static) / p99 DD 4.73%**, median days-to-pass 22 (vs 23 under C0). **DJ30 bust attribution 44.4%** — still the marginal bust contributor, share up from 40.9% under C0 (consistent with C2's wider DD-trigger letting more DJ30-driven static DD episodes through to closure rather than truncating early). Both lock criteria still clear with margin. Q-DDP-1's regime-robustness gate failed for C2; the 2026-05-08 override accepts that risk on broker-feed + median-pass-time grounds. Forward C2→C0 revert trigger: rolling 6-month pass-rate <95% for two consecutive 6-month windows. See `docs/adr/2026-05-08-dd-trigger-c2-relock.md` (canonical ADR), `docs/briefs/Q-DDP-1/recommendation.md` override note, and `docs/briefs/bust_attribution_flip.md` closure.

---

## [v4.5] — 2026-05-05 🔒 LOCKED

**Status:** Active on FXIFY $200K challenge. Risk 1.00% (unchanged). Supersedes v4.4. v4.4 moved to `archive/`.

### Delta from v4.4
Multi-parameter tuning — five inputs adjusted:

| Param | v4.4 | v4.5 | Direction |
|---|---|---|---|
| `minBodyRatio` | 0.25 | 0.38 | tighter (filters more weak bars) |
| `stopAtr` | 1.25 | 1.20 | tighter SL |
| `tpAtr` | 8.0 | 8.5 | wider TP |
| `trailDistTight` | 0.85 | 0.80 | tighter trail in tight phase |
| `trailTightenAt` | 1.5 | 1.0 | trail tightens earlier |
| `pyramidSize` maxval | 500 | 1000 | input-range expansion only; default still 350 |

Risk per trade, daily DD cap, max trades/day, lookback, ATR length, BE trigger, pyramid default size and trigger, maxHold, minBars all preserved from v4.4.

### Rationale
The migration thesis was that in a portfolio where the FXIFY DD cap is the binding constraint, trading ~$77K of net for ~1pp of max-DD compression is the right swap — that 1pp shows up directly in MC bust-rate. The 4-strategy re-MC bore that out (Pass 97.88% / Bust 0.22% / p99 DD 4.55%; pre-re-export figure was 98.13 / 0.22 / 4.49, superseded same-day after the Guardian 87e73 → 33781 phantom-signal correction — see `data/reconciles/2026-05-05_guardian_n_reconcile.md`).

### Portfolio MC anchors (2026-05-05)
- 4-strategy Pepperstone lock (G 0.34% / DJ30 v4.5 1.00% / A 1.50% / NAS v1 0.40%, 10K × 3 seeds): **97.88% pass / 0.22% bust / p99 DD 4.55%** (median days-to-pass 23). DJ30 bust attribution 40.9% — still the marginal bust contributor; share down from 43.4% under the 3-strategy 04-26 anchor. Both lock gates (bust < 1%, p99 DD < 5%) pass with comfortable margin. Pinned in `tests/test_mc_anchors.py`.

### Cross-reference
- `docs/briefs/striker_nas100_q_nas_3_mc_addition.md` — joint v4.5 + NAS100 add MC results.
- `archive/striker_dj30_v4.4.pine` — preserved for reproducibility.

---

## [v4.4] — 2026-04-23 🔒 LOCKED (superseded by v4.5 on 2026-05-05; archived)

**Status:** Historical. Was active on FXIFY $200K challenge 2026-04-23 → 2026-05-05. Risk 1.00%. Pine file moved to `archive/striker_dj30_v4.4.pine`.

### Delta from v4.3
- **Stop loss tightened: 1.35 × ATR → 1.25 × ATR.** Sole parameter change. All other v4.3 parameters (pyramid 350%, BE trigger 0.15, trail 0.15/0.90, maxHold 55, minBars 6, lookback 15, ATR length 11, TP 8×ATR, max 3/day) preserved.
- Tooltip on `stopAtr` still reads "LOCKED: 1.35" as historical annotation; current default is 1.25.

### Rationale
Joint lock with Guardian v5.5 and Aegis v4.3 on 2026-04-23. Tighter SL reduces the single-trade tail on pyramid-reversal days and feeds into the portfolio-level MC: bust contribution held roughly flat while pass rate ticked up modestly on the Pepperstone 52-month panel.

### Portfolio MC anchors (2026-04-23)
- 2026-04-20 Alchemy baseline (Striker v4.4 + Aegis v4.2 era): 99.21% pass / 0.03% bust.
- 2026-04-23 Pepperstone directional (all three at candidate versions, 10K × 3 seeds): 88.45% pass / 4.68% bust raw; 84.37% pass / 1.03% bust after Aegis 1R correction.
- Post-Guardian-risk-relock (G 0.34% / S 1.00% / A 1.50%): 92.73% pass / 0.65% bust / p99 DD 4.94%.

### Cross-reference
- 2026-04-23 joint version lock (commit `e40802d`)
- `docs/adr/2026-04-17-striker-v4.3-pyramid.md` (pyramid architecture — still load-bearing; v4.4 does not change pyramid)

---

## [v4.3] — 2026-04-17 🔒 LOCKED (superseded by v4.4 on 2026-04-23)

**Status:** Historical. Was active on FXIFY $200K challenge 2026-04-17 → 2026-04-23. Risk 1.00%. Saved in TradingView as "Striker v4.3". Initial tracked version.

### Parameters
| Field | Value |
|---|---|
| Instrument | DJ30 (US30) |
| Timeframe | 15min |
| Direction | Long breakout |
| Risk per trade | 1.00% |
| Daily DD cap | 1.00% |
| Max trades / day | 3 |
| Pyramid size | 350% |
| T1 partial | removed |
| BE trigger | 0.15 |
| Trail trigger | 0.15 |
| Trail wide | 0.9 |
| Stop loss | 1.35 × ATR |
| Take profit | 8 × ATR |
| maxHold | 55 bars |
| minBars | 6 |
| Lookback | 15 |
| `margin_long` / `margin_short` | 0 / 0 |
| **DXTrade `contractValue`** | **10** (default of 1 produces ~7% per-trade risk — critical) |

### Design intent
Capture pyramid-cohort profit concentration. MFE/MAE diagnostic on prior version showed pyramid cohort produced ~94% of total profit; v4.3 removes T1 and raises pyramid size to 350% to fully exploit that pattern.

### Backtest (4yr)
Net +$422K · PF 2.55 · RF 18.43 · WR 72.2% · 237 trades · Max DD 5.59% · μ/σ 1.24

### Known concerns
- **392-day max DD duration (N=1)** — single occurrence in 4yr window. No statistical basis for expectation. Monitor live.
- **μ/σ 1.24 is lowest in portfolio** (Guardian 1.54, Aegis 1.63). v5 rebuild queued post-challenge.

---

## Change convention

Each entry: version, date, lock status, parameters (full snapshot or delta), rationale, backtest metrics if re-run, cross-reference to Notion decision page.

Tag in git on lock: `git tag striker-vX.Y && git push --tags`.
