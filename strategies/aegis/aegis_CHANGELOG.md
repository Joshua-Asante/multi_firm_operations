# Aegis-Reversion — Changelog

Mean-reversion strategy on USDJPY 15min. Pine Script v6.

**Source of truth:** `aegis_usdjpy_v4.3.txt` holds the authoritative parameter values. This CHANGELOG records decisions, rationale, and portfolio role. If the two ever disagree, the Pine file wins — fix the CHANGELOG.

Versioning begins at v4.1 (2026-04-17). Prior development (v4 → v4.1 with +12% net P&L and shifted DD shape) is archived in Notion.

---

## [Unreleased]

_Queued changes. Move to a dated entry on commit._

- **BOJ April 28, 2026 meeting** — binary vol event. Monitor for regime shift post-meeting; no parameter change queued, but a dated entry should record observed behavior.

---

## [v4.3] — 2026-04-22 (candidate) / 2026-04-23 🔒 LOCKED

**Status:** LOCKED 2026-04-23 (commit `e40802d`, jointly with Guardian v5.5 and Striker v4.4). Active on FXIFY $200K challenge. Risk 1.50%. Supersedes v4.2.

### Delta from v4.2
Single parameter change: **block calendar day 29, 30, 31 of every month** (`eom_block = dayofmonth >= 29`). All other parameters (BB(19, 1.9), ATR(19), atr_sl_mult 1.42, tp_offset 0.8, be_trigger 0.3, be_pad 0.15, min_atr_val 0.07, session 10:00–13:45, Mon/Tue/Wed only, Tuesday H10 block, max_hold 40 bars, max 1 trade/day) are preserved unchanged from v4.2.

### Mechanism
Month-end JPY flow impulse (Japanese exporter repatriation, WMR fix-window positioning, fund rebalancing, options expiry adjustments) overrides mean-reversion on days 29–31. Loss-character diagnostic (days 1–28 vs 29–31): full-stop share of losses 14.3% → 71.4% (5×); avg loss size −$1,122 → −$2,746 (2.4×); mean hold on losses 2.1 → 0.9 bars; loss MFE mean $1,571 → $834; % of losses with MFE < $500: 14% → 43%. Signature of directional impulse overwhelming mean-reversion.

### OOS validation
Train 2022–2024 (n=83): Δnet +$5,113, ΔPF +0.68. Test 2025–2026 (n=53): Δnet +$3,462, ΔPF +1.08. Both splits improve on both metrics — filter transfers across the regime change (key evidence vs curve-fit).

### Full-panel impact (Pepperstone 52mo)
| Metric | v4.2 | v4.3 | Delta |
|---|---:|---:|---:|
| Trades | 136 | 123 | −13 |
| Net P&L | +$165,289 | +$173,863 | +$8,574 |
| Profit Factor | 3.23 | 4.16 | +0.93 |
| Win Rate | 58.8% | 60.2% | +1.3 pp |
| MaxDD (trade-close) | −$11,667 (5.83%) | −$7,526 (3.76%) | +$4,141 |
| RoMaD | 14.2 | 23.1 | +63% |

Simultaneous improvement in trade count, MaxDD, and net — signature of removing genuine negative-expectancy trades, not curve-fit noise.

### Rejected during same INQHIORI loop (do not revisit without new mechanism evidence)
- **Post-holiday Wed 10:15 filter** — failed OOS (train 3/3 losses, test +$9,096 winner).
- **FOMC-day filter** — different mechanism (chop/BE-shaves, not impulse); near-flat aggregate.
- **BOJ-day filter** — no session overlap in 4yr panel (BOJ announces pre-10:00 ET).
- **Wed 10:15 blanket block** — redundant after EOM; residual is noise on top of EOM/FOMC correlation.

### Post-v4.3 portfolio Monte Carlo (completed 2026-04-23)
The previously-queued post-v4.3 portfolio MC re-run executed at the joint 2026-04-23 lock and the same-day Guardian risk re-lock (0.30% → 0.34%). Aegis bust contribution moved from the 2026-04-17 MC's ~47% to **27.6%** at the post-relock canonical config (G 0.34% / S 1.00% / A 1.50%) — close to the original 25% expectation, somewhat above the optimistic 15–20% lower bound. Headline portfolio numbers: 92.73% pass / 0.65% bust / 6.62% timeout, p99 DD 4.94%. See `docs/adr/2026-04-23-guardian-risk-relock-0.34.md` for the locked MC anchors and `CLAUDE.md` Protection section.

### Cross-reference
- 2026-04-22 INQHIORI loop (candidate)
- 2026-04-23 Pepperstone directional MC re-lock (84.37% pass / 1.03% bust) vs 2026-04-20 Alchemy baseline (99.21% / 0.03%) — commit `e40802d`
- 2026-04-23 post-Guardian-risk-relock canonical MC (92.73% pass / 0.65% bust / p99 DD 4.94%) — commit `84d3cb1`
- 2026-04-24 Mon-H10 2024 Inversion INVESTIGATE: H-A confirmed (tail-noise, not a structural issue)

---

## [v4.1] — 2026-04-17 🔒 LOCKED (superseded by v4.3 on 2026-04-23)

**Status:** Historical. Active on FXIFY $200K challenge from 2026-04-17 to 2026-04-23. Risk 1.50%. Initial tracked version.

### Parameters
Authoritative parameter values (as of the v4.1 lock) lived in the then-current `strategies/aegis/aegis_usdjpy_v4.1.txt` (removed when v4.3 superseded it). Partial snapshot of known fields:

| Field | Value |
|---|---|
| Instrument | USDJPY |
| Timeframe | 15min |
| Direction | Mean-reversion (both sides) |
| Risk per trade | 1.50% |

### Allocation rationale
1.50% risk chosen on per-strategy recovery factor optimization. Final portfolio Monte Carlo (2026-04-17) attributes ~47% of bust probability to Aegis — the dominant bust driver. Decision stands:

1. Aegis has the highest μ/σ in the portfolio (1.63 vs Guardian 1.54, Striker 1.24)
2. Recovery-factor optimization prefers higher allocation to highest-Sharpe strategy
3. Bust attribution at correct sizing is an artifact of having a strongest edge, not a miscalibration

### MC context (final, 2026-04-17)
Run at G 0.30% / S 1.00% / A 1.50% with single-tier DD 1.0%/0.40×:
Bust rate 1.55% · Pass rate 93.00% · p99 DD ~4.9% · Bust attribution Aegis ~47% / Striker ~40% / Guardian ~12%

### Strategy role in portfolio
Yen safe-haven bid capture and BOJ/Fed divergence expression. Structurally countercyclical to Guardian and Striker:
- Iran-Israel conflict regime (Feb 28, 2026 onset, Hormuz closure Mar 2): Aegis fired 4 consecutive winners while Guardian drew down through its worst-ever losing streak
- Debate-to-election 2024 window: Aegis/Guardian positive, Striker PF 0.90 (its worst window)
- Zero all-three-negative days across 4yr backtest

### Regime sensitivities
- Benefits from: violent round-trip regimes, yen safe-haven flows, BOJ/Fed rate divergence
- Threatened by: sustained USDJPY trend regime, BOJ policy shock
- BOJ April 28, 2026 meeting flagged as binary vol event

---

## Change convention

Each entry: version, date, lock status, parameters (full snapshot or delta), rationale, backtest metrics if re-run, cross-reference to Notion decision page.

Tag in git on lock: `git tag aegis-vX.Y && git push --tags`.
