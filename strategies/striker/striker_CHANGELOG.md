# Striker DJ30 — Changelog

Long breakout strategy on DJ30 (US30) 15min. Pine Script v6.

**Source of truth:** `striker_dj30_v4.4.txt` holds the authoritative parameter values. This CHANGELOG records decisions, rationale, and known concerns. If the two ever disagree, the Pine file wins — fix the CHANGELOG.

Versioning begins at v4.3 (2026-04-17). Prior development history (v3.1 → v4.1 → v4.2 rejected → v4.3) is archived in Notion.

---

## [Unreleased]

_Queued changes. Move to a dated entry on commit._

- **v5 architectural rebuild** — priority #1 post-challenge pass. Hypothesis: strip BE/trail/T1 management following the Guardian v4 → v5.1 pattern, lift μ/σ from 1.24 toward portfolio average. See Notion: "Striker v5 architectural rebuild — priority #1 post-challenge — 2026-04-17".

---

## [v4.4] — 2026-04-23 🔒 LOCKED

**Status:** Active on FXIFY $200K challenge. Risk 1.00% (unchanged). Supersedes v4.3.

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
