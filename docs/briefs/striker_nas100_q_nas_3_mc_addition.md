# Q-NAS-3 — Portfolio MC: Striker NAS100 v1 add (joint with DJ30 v4.5 migration)

**Date:** 2026-05-05
**Brief:** Striker NAS100 v1 — Phase 4C/6 investigation (rev 2)
**Loop:** INQHIORI Inquire-phase, Striker NAS100 v1 dev thread
**Reproduce:** `python portfolio_mc.py --panel pepperstone`

---

## Headline

Adding Striker NAS100 v1 at 0.40% allocation, jointly with the DJ30 v4.4 → v4.5 migration on Pepperstone, **improves every gate** vs the prior 3-strategy lock anchor.

| Metric | 3-strategy 04-26 anchor | 4-strategy 05-05 anchor | Δ |
|---|---|---|---|
| Pass | 93.78% | **98.13%** | +4.35 pp |
| Bust (total) | 0.58% | **0.22%** | −0.36 pp |
| Bust (daily) | 0.00% | 0.00% | — |
| Bust (static) | 0.58% | 0.22% | −0.36 pp |
| Timeout | 5.65% | **1.65%** | −4.00 pp |
| Median days to pass | 32 | **23** | −9 days |
| p50 DD | 1.41% | 1.33% | −0.08 pp |
| p95 DD | 3.81% | 3.50% | −0.31 pp |
| p99 DD | 4.92% | **4.49%** | −0.43 pp |

Lock criteria (CLAUDE.md): bust < 1% ✓ (0.22% comfortable), p99 DD < 5% ✓ (4.49% comfortable).

## Configuration

- **Allocations:** G 0.34% / DJ30 1.00% / A 1.50% / NAS 0.40%
- **DD protection:** single-tier 1.0% from peak → 0.40× scaling (unchanged)
- **Panel:** Pepperstone 2022-01-04 → 2026-04-20 (1120 bdays, 223 week-blocks)
- **Sims:** 10,000 × 3 seeds (42, 123, 2026), horizon 150 days
- **DJ30:** v4.5 (file `Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv`)
- **NAS100:** v1 (file `Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-05_7ca6f.csv`)

## Per-strategy scale info (Q-NAS-4 closure inline)

| Strategy | implied 1R | scale | n_trades | fell_back |
|---|---|---|---|---|
| Guardian | $1,175.10 | 0.579 | 209 | False |
| Striker DJ30 | $3,897.54 | 0.513 | 224 | False |
| Aegis | $3,293.45 | 0.911 | 123 | False |
| Striker NAS100 | $3,599.09 | 0.222 | 200 | False |

**Q-NAS-4 closure:** NAS100 lands in the Striker-class branch (`mean(|losses| > 1% of $200K)`) at [portfolio_mc.py:122-127](../../portfolio_mc.py:122). `(r1, fell_back, n_full_stops) = ($3599.09, False, 25)`. The dashboard's "provisionally Striker-class" methodology assumption is **methodology-aligned**. The full-stop cohort is 25 (well above the n=5 fallback threshold), so MC is canon-clean.

The NAS scale of 0.222 is the lowest in the panel — pyramid-amplified per-trade dollars are downscaled hard so 1R maps to the 0.40% × $200K = $800 target. This is by design: NAS's "1R" in the locked methodology = pyramid-leg full-stop dollars, not base-leg dollars.

## Bust attribution shift

| Strategy | 3-strategy 04-26 share | 4-strategy 05-05 share | Δ |
|---|---|---|---|
| Striker DJ30 | 43.4% | **49.2%** | +5.8 pp |
| Guardian | 31.4% | 20.0% | −11.4 pp |
| Aegis | 25.1% | 20.0% | −5.1 pp |
| Striker NAS100 | — | **10.8%** | (new) |

Total busts down (0.58% → 0.22%) AND share redistributes — DJ30 v4.5 takes a slightly larger share of a smaller pie, NAS comes in as the lowest contributor (10.8%). Striker family combined (DJ30 + NAS) = 60.0% of busts, but absolute bust rate from Strikers = 0.22% × 0.600 = 0.13% (vs prior DJ30-alone 0.25%) — Striker family is now LESS bust-contributing in absolute terms despite owning a bigger relative share.

NAS as a marginal contributor ranks **lowest** of all four strategies, consistent with the diversification thesis the dashboard prior nominated.

## Comparison to dashboard prior

The web-thread brief cited a 4-strategy dashboard (`portfolio_4yr_dashboard.html`, 2026-05-05) with peak DD 3.17%. That dashboard is a deterministic point-estimate aggregation; this MC is a 30K-sim distribution. p99 DD 4.49% > dashboard peak DD 3.17% as expected (MC samples worse paths than the historical realization). Both pass lock criteria.

The dashboard's headline (Net Return +480%, RF 125.7) is a different metric class than this MC's pass/bust/p99 output — they don't directly compare numerically, but both point to the same qualitative conclusion: the 4-strategy combination is materially safer and faster than the 3-strategy baseline.

## What is NOT in this MC

- **OANDA still on DJ30 v4.4** — no fresh OANDA v4.5 fetch yet. The OANDA pattern-spotting anchor stays at 96.05/0.48/4.79 (3-strategy, v4.4) until that fetch lands. Tracked as a residual.
- **No NAS allocation sweep** — single-point pin at 0.40% per user decision (the dashboard's "NAS 1.00" was unit allocation = full slot, not 1.00% risk). If a future re-MC exercises a sweep, the indicator-locked 0.40% should remain the anchor.
- **NAS at v1 strategy file** — `strategy.entry()` native pyramid leg accounting, not the indicator's simplified-form (Q-NAS-1 indicator concern moot for the strategy file at [strategies/striker/striker_nas100_v1.pine:328-332](../../strategies/striker/striker_nas100_v1.pine:328)).

## Test pin

[tests/test_mc_anchors.py:42-48](../../tests/test_mc_anchors.py:42) re-pinned to:
- `pass_rate == 0.9813 ± 1e-4`
- `bust_rate == 0.0022 ± 1e-4`
- `p99_dd == 0.0449 ± 1e-4`

OANDA anchor (96.05/0.48/4.79) unchanged. The serial-vs-parallel equivalence check still passes. Lock criteria gate (bust <1%, p99 DD <5%) still passes.

## Residuals

- 5-trade dashboard count gap (753 expected vs 748 reported): MC sees 209 + 224 + 123 + 200 = 756 trades. Dashboard's 748 likely reflects a slightly different panel-end date (dashboard ends 2026-04-20; CSV ends 2026-04-14 for NAS, 2026-04-20 for others). Not material.
- DJ30 v4.5 lock-decision rationale: inferred from file diff in CHANGELOG; flagged in CHANGELOG `### Rationale` for Joshua to confirm/edit.
- OANDA v4.5 + OANDA NAS100 fetches: separate operational tasks, out of this session's scope.
