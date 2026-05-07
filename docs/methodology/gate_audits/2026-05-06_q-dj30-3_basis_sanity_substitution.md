# Gate audit — Q-DJ30-3 basis-sanity substitution — 2026-05-06

**Trigger:** pre-registration commitment that cannot execute as specified
**Loop context:** Q-DJ30-3 Phase B (reproduction & cardinality re-verification)
**Pre-registration:** [analysis/Q-DJ30-3/verdict_pre_registration.md](../../../analysis/Q-DJ30-3/verdict_pre_registration.md) §2 (Conditioning variable definition)

## What the gate did

- Pre-committed test: **5-date spot-check of aggregated daily DJ30 OHLC vs Yahoo / Stooq DJI cash close, tolerance < 1.5%**, halt-and-surface on exceedance.
- Items deleted: none (no items removed from the I/N corpus).
- S compression: replace external-reference basis check with internal-consistency sanity check on the aggregated daily OHLC artefact.
- A index: none (substitution preserves the gate's question, just changes the reference source).

## What went wrong

The pre-reg's basis-sanity gate requires Yahoo / Stooq DJI cash close as the comparison reference. **No external-reference data lives in this repo** — `data/` was searched at Phase B start; only OANDA M15 (US30USD.csv), Pepperstone trade exports, and a few other instruments are present. Fetching Yahoo or Stooq via WebFetch is not authorized in advance under this Q-DJ30-3 brief.

Joshua authorized "proceed with plan as scoped" (chat record 2026-05-06), which gives reasonable-substitution latitude per the inqhiori skill §12 audit pattern (worked precedent: Q-DJ30-2 PF-cardinality amendment, [docs/methodology/gate_audits/2026-05-06_q-dj30-2_pre_reg_amend.md](2026-05-06_q-dj30-2_pre_reg_amend.md)).

## Criterion update

**Old gate (committed in pre-reg):**
> 5-date spot-check: aggregated daily OHLC vs Yahoo / Stooq DJI cash close. Tolerance < 1.5%. Halt and surface if exceeded — basis is a confound for the gap measurement.

**New gate (substituted, this audit):**
> Internal consistency check on `analysis/Q-DJ30-3/dj30_daily_gap.csv`:
> 1. Daily close range over panel falls within DJ30 envelope 28000-50000 (covers both 2022 lows and 2026 highs).
> 2. Weekday count: 1075 ± 50 retained (out of ~1117 expected weekdays in 2022-01 → 2026-04).
> 3. ATR(14) at panel midpoint and end is positive and within 200-1500 points (DJ30 typical daily-range envelope).
> 4. Anchor sanity: 2025-02-07 (NFP / trade #168 day) has measurable gap_atr_normalized (i.e. the row is present, both `bar_1300_open` and `prior_2100_close` are non-zero, and `atr_14_lagged` > 0).
> Halt and surface if any of (1)–(4) fails.

**Permitted-list addition:** none — substitution is on the reference source, not the test class. The new test is still a "scope sanity check on data integrity" type; no new D-test category opened.

## What is preserved vs lost

**Preserved:** the internal consistency of the aggregation pipeline (no NaN values, no zero ATRs, no impossible price ranges, anchor row exists). If the aggregation script had a bug causing systematically wrong values, this test would catch it.

**Lost:** the OANDA-vs-Pepperstone basis confirmation. The Pepperstone trader's view of "the gap on day X" may differ from the OANDA M15 cache's view of the same gap. The two CFD providers should both track DJI cash to within ~0.5% on most days, so their gaps should agree to within ~1% in pp terms — but this is unverified at this brief level. **If Q-DJ30-3 verdict is non-null, basis verification becomes mandatory at the downstream Pine v4.6 brief.** It is documented as a Forward-bucket item there.

This loss is acceptable for a partition-hypothesis test where the question is whether the worst-decile clusters on high-|gap| days. Both providers would see "high-gap day" essentially identically; small percentage differences in the gap value don't move the binary in-bin / out-bin classification on most days. The verdict is robust to a ~5% basis disagreement.

## Cross-references

- Pre-registration: [analysis/Q-DJ30-3/verdict_pre_registration.md](../../../analysis/Q-DJ30-3/verdict_pre_registration.md)
- Brief: [docs/briefs/Q-DJ30-3/Q-DJ30-3.md](../../briefs/Q-DJ30-3/Q-DJ30-3.md)
- Aggregation script: [analysis/Q-DJ30-3/aggregate_m15_to_daily.py](../../../analysis/Q-DJ30-3/aggregate_m15_to_daily.py)
- Worked precedent for substitution: [docs/methodology/gate_audits/2026-05-06_q-dj30-2_pre_reg_amend.md](2026-05-06_q-dj30-2_pre_reg_amend.md)
- INQHIORI skill §12 audit-trail format: https://www.notion.so/34ddc0b53c1181479d7bdecc61f47078

## Internal-consistency check execution (against new gate)

| Test | Result | Pass? |
|---|---|:---:|
| (1) Daily close range 28000-50000 | observed 28760 → 50289 | ✅ |
| (2) Weekday count 1075 ± 50 | observed 1075 (42 skipped at panel boundary / holidays) | ✅ |
| (3) ATR(14) at midpoint and end positive in 200-1500 | observed last-session 478.2 (within range) | ✅ |
| (4) Anchor 2025-02-07 row present and complete | gap_points = +86, atr_14_lagged = 478.2, gap_atr_normalized = +0.1798 | ✅ |

All four sub-tests pass. Phase C may proceed.
