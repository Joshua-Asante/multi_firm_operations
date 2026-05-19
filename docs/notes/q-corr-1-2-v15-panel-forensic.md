# Guardian Silver v1.5 panel — forensic record

**Status:** forensic note (pre-disposition; informational only)
**Parent:** [`docs/briefs/Q-CORR-1.2-guardian-family-silver-wfo.md`](../briefs/Q-CORR-1.2-guardian-family-silver-wfo.md)
**Date:** 2026-05-13
**Authored by:** Claude Code, post-merge of PR #79

This is a **pre-disposition forensic record** of the Silver v1.5 prototype panel that motivated the Q-CORR-1.2 §12 v1.5-hint zone. It is **not part of the Q-CORR-1.2 LOCK**, does not modify any §14 gate, and does not pre-empt the Pre-Q disposition. Its purpose is to record what was known about v1.5 *before* the Cartesian sweep, so the closure note can refer back to it without re-deriving.

---

## Cohort

| Field | Value |
|---|---|
| Strategy | Guardian Silver v1.5 (prototype; Pine source at user-local path) |
| Instrument | XAGUSD 15m |
| Feed | Pepperstone |
| File | `data/tv_exports/pepperstone/Guardian_Silver_v1.5_PEPPERSTONE_XAGUSD_2026-05-13_82815.csv` |
| SHA256 | `db45eb3aa23569611b9796766076a4646d62dde3cb7f6d602744ac6928a71864` |
| Bytes | 61,485 |
| Span | 2022-01-11 → 2026-04-20 (51.2 months, full Q-CORR-1.2 fold window) |
| Trade pairs | 260 (520 rows: 260 Entry + 260 Exit) |

Parameters that distinguish v1.5 from the Gold v5.5 lock:

| Param | v1.5 | Gold v5.5 (lock) |
|---|---:|---:|
| `emaSlowLen` | 395 | 385 |
| `entryEmaLen` | 20 | 25 |
| `atrLength` | 15 | 14 |
| `stopAtr` | 1.4 | 1.55 |
| `tpAtr` | 33.0 | 29.0 |
| `minBarsBeforeStop` | 0 | 1 |
| `maxDailyTrades` | 3 | 2 |
| `riskPerTrade` | 0.30% | 0.34% |
| Active days | Tue, Thu, Fri | Mon, Tue, Thu |

The four parameters Q-CORR-1.2 sweeps (`emaSlowLen`, `stopAtr`, `tpAtr`, `sessionChoice`) are exposed as Pine `input.*()` declarations in the v1.5 source. No mechanical edit required for the 250-config Cartesian.

---

## Headline metrics — full panel, train slice, OOS slice

Slice boundaries set to Q-CORR-1.2 §13 `fold_spec.json`: train_end = 2025-05-10, oos_start = 2025-05-11, oos_end = 2026-04-20. Static-equity notional ($200K) basis for DD per §15 DD-convention amendment.

| Cohort | N | PF | WR % | Net | DD % (notional) | DD % (compounded) | MFE/MAE | median \|loss\| |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Full 52-month | 260 | 3.536 | 15.38 | $576,880 | 8.77 | 7.76 | 5.007 | $914 |
| Train (40mo) | 209 | 1.833 | 11.00 | $138,173 | 8.77 | 7.76 | 3.463 | $874 |
| OOS (11.3mo) | 50 | 7.890 | 32.00 | $424,928 | 6.60 | 2.54 | 8.293 | $1,590 |

1R basis (Guardian = trend-rider, no BE): median |loss| per the `trade-csv-reconcile` skill's per-strategy archetype table.

---

## §16 train floors — v1.5 against constraint gate

§16.2 selection requires ALL of: `n_trades ≥ 50` AND `WR ≥ 15.0%` AND `DD ≤ 8.0%`. Evaluated against the **train slice**:

| Floor | v1.5 train | Pass? |
|---|---:|---|
| `n_trades ≥ 50` | 209 | ✓ |
| `WR ≥ 15.0%` | **11.00%** | ✗ |
| `DD ≤ 8.0%` | **8.77%** | ✗ |

**Disposition under §16:** v1.5 fails train selection on two of three floors. Under WFO discipline, `select_train_fold` would refuse to advance v1.5 to OOS — `selection_status="NO_CANDIDATE"` if v1.5 were the only feasible point in the Cartesian.

---

## §14 OOS gates — v1.5 against disposition gate

Evaluated against the **OOS slice** for informational purposes. (Reminder: under WFO discipline v1.5 doesn't reach OOS evaluation; this section exists to record what the OOS slice looks like in case other Cartesian points behave similarly.)

| Gate | Threshold | v1.5 OOS | Pass? |
|---|---|---:|---|
| 6 (PF) | ≥ 1.50 | 7.890 | ✓ |
| 7 (WR%) | ≥ 15.0% | 32.00% | ✓ |
| 8 (DD%) | ≤ 8.0% | 6.60% | ✓ |
| 9 (bootstrap p05 PF, canonical seed=42 n=1000 block=6mo) | ≥ 1.30 | 8.320 | ✓ (caveat below) |
| 10 (half-panel H1/H2 PF ratio) | ∈ [0.7, 1.3] | 0.852 | ✓ |
| 11 (MFE/MAE asymmetry) | > 2.0 | 8.293 | ✓ |
| 12 (ρ vs locked Gold v5.5, zero-fill aligned) | ≤ 0.10 | — | not computed |

**Gate 9 caveat:** the 11.3-month OOS slice contains only **n_blocks = 2** under 6-month blocking. The bootstrap is structurally degenerate at this fold size — `p05 ≈ p50 ≈ full_pf` because only 2 blocks can be resampled. Gate 9's discriminatory power is limited; do not treat the "PASS" as strong evidence on its own.

**Gate 12 not computed:** the worktree this forensic was authored on holds locked Gold v5.5 comparator bytes; but the v1.5-vs-Gold correlation is meaningful only when v1.5 is being compared as a *candidate* OOS winner via Q-CORR-1.2 §14. Doing it here pre-Pre-Q would create a comparison without methodological cohort declaration. Defer until disposition; can be computed in seconds with `lib.correlation.pearson_daily_pnl` if/when needed.

---

## Train-OOS asymmetry — the load-bearing finding

| Metric | Train (40mo, n=209) | OOS (11.3mo, n=50) | Delta |
|---|---:|---:|---|
| PF | 1.833 | 7.890 | **4.3×** |
| WR % | 11.00 | 32.00 | **+21 pp** |
| MFE/MAE | 3.463 | 8.293 | 2.4× |
| Median \|loss\| | $874 | $1,590 | 1.8× (1R inflation) |

On **identical parameter values** between train and OOS slices. This is either:

1. **Genuine late-2025 regime shift** in Silver favoring Guardian-family signals (XAGUSD trended hard from late-2025 into 2026; structurally consistent with a trend-rider strategy).
2. **Dev-time data-snooping**: the v1.5 parameters were chosen by hand-tuning over a window that included some or all of the 2025-05-11+ slice, contaminating the "OOS" label retroactively.
3. Both, in proportions unknown from this single CSV.

Q-CORR-1.2's procedural discipline (commit `grid_hash`/`fold_spec_hash` at run-start; ingest train CSVs *before* OOS CSV; basename-match enforcement) is precisely designed to detect this pattern — but only for *future* parameter selection, not for v1.5 itself which was chosen pre-LOCK.

---

## Methodology implications for Q-CORR-1.2

1. **v1.5 is the v1.5-hint zone** (`emaSlowLen=395, stopAtr=1.4, tpAtr=33, session=NY_Extended`). It is one of the 250 Cartesian points. Under §16 WFO discipline it would not pass train selection, so it cannot itself be the Pre-Q winner.

2. **The wider Cartesian perturbation regions** (slower-trend EMAs 450/500/550, wider stops 1.55/1.75/2.0/2.25, faster TPs 15/20/25, alt session London_NY_Overlap) are the search space for a config that simultaneously: lifts train WR ≥ 15%, holds train DD ≤ 8%, and delivers clean OOS. The v1.5 train cohort (WR 11%, DD 8.77%) is a substantial *prior against* finding such a pocket — the train cohort is the weakest known on the v1.5-hint side.

3. **If the Cartesian sweep returns NO_CANDIDATE** (no point clears train floors), that is a real FALSIFIED disposition signal — not a methodology problem. The closure note's §17 FALSIFIED branch would apply, and `docs/rejected_candidates.md` gets the entry "no Guardian-family parameter zone on Silver clears §16 floor on the 2022-01-11 → 2025-05-10 train cohort".

4. **If a Cartesian point passes train selection**: forensic checks worth running before treating it as RESOLVED:
   - `pearson_daily_pnl(winner_oos_csv, this_v1.5_csv)` — rebadge check; high ρ means the winner is v1.5-shaped.
   - Compare winner OOS metrics to v1.5 OOS metrics (PF 7.89, WR 32%, DD 6.60%) — if very similar, suspect parameter-region overlap rather than independent edge.
   - Forensic ρ is **informational only**, does not modify the §14 disposition.

---

## Pine source housekeeping (operator note)

The Guardian Silver v1.5 prototype Pine source (gitignored locally) contains two stale references that don't affect strategy logic:

- Top comment block reads `// GUARDIAN GOLD v5.5 — FXIFY Trend-Follower (XAUUSD)` — copy-paste residue from the Gold v5.5 lock.
- Dashboard label `table.cell(dash, 0, 0, "Guardian Gold v5.5", text_color=#FFD700, ...)` — hardcoded Gold name.

Recommend fixing both before the 5-8-session TV sweep. Five-second edit; will spare visual confusion across ~250 chart-input changes when every dashboard says "Gold v5.5" while the strategy is sweeping Silver parameters.

---

## Provenance attestation

- CSV bytes loaded directly from disk; sha256 verified against pinned line in `data/tv_exports/pepperstone/SHA256SUMS` (commit `b54c02a`).
- Metrics computed with the canonical Exit-row–only attribution per `trade-csv-reconcile` skill Step 2.
- §16 floors and §14 gates evaluated against thresholds frozen in the LOCKED Q-CORR-1.2 brief at the time of authoring (commit `670625d` and descendants).
- Bootstrap (Gate 9) and half-panel (Gate 10) executed via `lib.regime_bootstrap.regime_bootstrap_daily_pnl` and `lib.regime_bootstrap.compute_pf` respectively; canonical (seed=42, n_panels=1000, block_months=6) parameters for Gate 9.
- No anchor in `references/baselines.md` was updated as a result of this analysis. Guardian Silver v1.5 is a **new cohort**, not a re-baseline of any existing strategy/version.
