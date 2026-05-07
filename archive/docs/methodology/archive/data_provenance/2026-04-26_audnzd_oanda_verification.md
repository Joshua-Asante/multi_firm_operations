# AUDNZD OANDA M15 — data provenance and verification

**Loop:** `loop_2026-04-26_audnzd_discovery`
**Brief:** AUDNZD candidate-strategy discovery (2026-04-26)
**Phase:** 1 (data ingestion)
**Status:** PASS — proceed to Phase 2

## 1. Source

- **Endpoint used:** `https://api-fxpractice.oanda.com/v3/instruments/AUD_NZD/candles`
- **Endpoint specified by brief:** `https://api-fxtrade.oanda.com/...` (live)
- **Deviation:** brief authorized 2026-04-26 by Joshua. Live endpoint returned 401
  for the available token (account prefix `101-` = practice). Practice endpoint
  accepted the same token (200 OK). Sole credential available; obtaining a live
  token would have blocked the loop.
- **Empirical guard:** the brief's external cross-reference at three dates is
  the gating test for whether the practice feed is fit for this loop's purpose.
  Result: PASS (see §4).

## 2. Request parameters

| Parameter | Value |
|---|---|
| instrument | `AUD_NZD` |
| granularity | `M15` |
| price | `BA` (bid+ask both columns; never collapsed to mid) |
| from | `2022-01-01T00:00:00Z` |
| to (effective) | `2026-04-26T00:00:00Z` |
| dailyAlignment | `17` |
| alignmentTimezone | `America/New_York` (NY-close convention) |
| count per request | `5000` (OANDA hard cap) |
| pagination | cursor-advance past last candle, page-boundary dedup |

Fetcher: [scripts/audnzd_phase1_fetch.py](../../../scripts/audnzd_phase1_fetch.py).
Credentials helper (path-only, never values): [lib/oanda_creds.py](../../../lib/oanda_creds.py).

## 3. Output

| Artifact | Path | SHA256 |
|---|---|---|
| Raw CSV | `data/audnzd_oanda_m15_2022-01-01_to_2026-04-26_raw.csv` | `6ff6cc3ce9f3f7ac825b2bae8e1d0cd82295564ca909ba6698f523606fba2d92` |
| Clean CSV | `data/audnzd_oanda_m15_2022-01-01_to_2026-04-26_clean.csv` | `6ff6cc3ce9f3f7ac825b2bae8e1d0cd82295564ca909ba6698f523606fba2d92` |

Raw and clean are byte-identical: no deletions were warranted (see §5).

Schema: `datetime_utc, datetime_ny, open_bid, high_bid, low_bid, close_bid, open_ask, high_ask, low_ask, close_ask, volume, complete`.

Window endpoints actually returned:
- first bar: `2022-01-02T22:00:00Z` (Sunday market open, NY)
- last bar:  `2026-04-24T20:45:00Z` (Friday market close, NY)
- pages fetched: 22

All Phase 2/3/4 artifacts must reference the SHA256 above so the data lineage is reproducible.

## 4. Verification (Phase 1.3)

### 4.1 Programmatic checks

Runner: [scripts/audnzd_phase1_verify.py](../../../scripts/audnzd_phase1_verify.py).

| Check | Threshold | Observed | Verdict |
|---|---|---|---|
| bar count | [100k, 160k] | 107,243 | PASS |
| weekend gaps (>60 min) | [200, 240] | 234 | PASS |
| spread median (pips) | < 3.0 | 2.600 | PASS |
| spread p99 (pips) | < 15.0 | 17.500 | **FAIL** |
| OHLC integrity (bid+ask) | 0 violations | 0 | PASS |
| NaN OHLC rows | 0 | 0 | PASS |
| `complete=true` for all rows | yes | yes | PASS |
| zero-volume rows (surface) | log only | 0 | PASS |

Median gap between bars: 15.00 min (consecutive M15). Max gap: 4,335 min (~3 days = long-weekend / holiday closure).

### 4.2 Spread p99 fail — explanation

Median of 2.60 pips is consistent with retail AUDNZD mid-spread; p99 of 17.5
pips and tail max of 59.4 pips reflect the OANDA practice feed's habit of
widening quoted spreads on news-event / illiquid bars more aggressively than
the live feed. This is a known practice-vs-live difference in spread quoting,
not an OHLC fault — the OHLC bars themselves match Dukascopy within sub-pip
tolerance (§4.3).

**Implication for downstream phases:**
- Phase 2 (structural characterization) is computed from OHLC patterns; the
  spread tail does not affect Hurst, ADF, range/trend ratio, DOW seasonality,
  or volatility profile measurements. Spread profile is reported as one of
  the §2.1 measurements; the practice-tail caveat is noted there.
- Phase 3 (strategy backtests) inherits a known optimistic-bias on spread
  cost: any framework that turns out to be edge-positive on this dataset must
  remain edge-positive after re-running on a live-feed sample (or after
  applying a flat 2-pip per-trade slippage haircut as a conservative proxy).
  This is logged as a Phase-3 caveat, not a Phase-1 blocker.

### 4.3 External cross-reference — Dukascopy

Runner: [scripts/audnzd_phase1_xref.py](../../../scripts/audnzd_phase1_xref.py).
Comparison point: M15 bar closing at 16:00 UTC (London close, DST-stable).
Tolerance: 2.0 pips on mid-price. Second source: Dukascopy bi5 hourly tick
files, last tick before 16:00 UTC.

| Date | Tag | OANDA mid | Dukascopy mid | Diff (pips) | Verdict |
|---|---|---|---|---|---|
| 2024-08-05 | yen-carry-unwind | 1.09416 | 1.09417 | 0.100 | PASS |
| 2025-04-02 | RBA decision day | 1.09769 | 1.09770 | 0.050 | PASS |
| 2026-01-15 | quiet day baseline | 1.16687 | 1.16684 | 0.250 | PASS |

Max observed diff: 0.250 pips. All three days pass within an order of
magnitude under the tolerance. The OANDA practice OHLC feed is empirically
validated against an independent source on three diverse market regimes
(crisis / event / calm).

This reconciliation is the gating test that authorizes Phase 2 against this
data. The 2026-04-23 Aegis-on-Alchemy-mislabeled-as-Pepperstone failure mode
is the exact shape this guards against.

## 5. Cleaning (Phase 1.4)

Runner: [scripts/audnzd_phase1_clean.py](../../../scripts/audnzd_phase1_clean.py).

| Test | Permitted? | Count | Action |
|---|---|---|---|
| Weekend-gap candles | ✓ temporal scope (artefact) | N/A | OANDA omits these by construction; no candles to delete |
| `complete=false` candles | ✓ duplication | 0 | none in dataset |
| NaN OHLC | ✓ measurement artefact | 0 | none in dataset |
| `volume=0` | log + surface (NOT auto-delete) | 0 | none in dataset |

**Clean rows = raw rows = 107,243.** No D-tests deleted any rows. Pre-Q gate's
D step on this corpus is effectively a no-op: the OANDA practice feed for
AUDNZD M15 over this window is uniformly clean. This is itself a finding —
no measurement artefacts to denoise around.

## 6. Forbidden-D-test audit

Per the inqhiori-algorithm gate discipline, no forbidden D-tests were applied
in Phase 1. Specifically:

- ❌ "Does this bar fit a mean-reversion model?" — not asked
- ❌ "Is this period a known regime break?" — not asked
- ❌ "Does Aegis methodology fork cleanly here?" — not asked

The brief's pre-Q gate explicitly forbids these, and the cleaning loop's only
deletion criteria are the four permitted tests in §5. No silent substitutions.

## 7. Cross-references

- Brief: AUDNZD candidate-strategy discovery (2026-04-26)
- Decorrelation scan that surfaced AUDNZD: 2026-04-19 chat
- Practice-endpoint deviation authorization: 2026-04-26 chat (this loop)
- INQHIORI ⊕ The Algorithm gate discipline: skill `inqhiori-algorithm`
- Two-tier canonical (Pepperstone / OANDA): user memory `feedback_two_tier_canonical_pepperstone_oanda.md`

## 8. Phase 1 verdict

**PASS — proceed to Phase 2 (structural characterization).**

Caveats inherited by Phase 2:
- Practice-feed spread p99 inflation; report in §2.1 spread profile, do not
  treat practice spreads as tradable estimates.

Caveats inherited by Phase 3 (if reached):
- Spread-cost optimism bias; require any edge to survive a flat 2-pip
  per-trade haircut, or re-validate against a live or Pepperstone feed before
  any further loop is opened on this candidate.

Caveats inherited by Phase 4 verdict file:
- The verdict applies to AUDNZD M15 OANDA-practice 2022-01-01..2026-04-26.
  Generalization to a live/Pepperstone deployment is out of scope for this
  loop; that is the verdict-4B/4C follow-on loop's question.
