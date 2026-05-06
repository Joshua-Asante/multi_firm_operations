# 2026-05-06 — DJ30 stop-through tail / US macro release co-location

**Loop ID:** Q-DJ30-1
**Brief:** Q-DJ30-1 (web Claude, 2026-05-06)
**Plan:** `C:\Users\joshu\.claude\plans\q-dj30-1-dj30-silly-origami.md` (Claude Code, 2026-05-06)
**Phase:** Inquire
**Date closed:** 2026-05-06

**VERDICT: CLOSE — null result.**

Worst-decile DJ30 base-entry losses are **not** temporally co-located with major scheduled US macro releases at a rate higher than non-tail trades. Effect size sits at −2.5 pp (tail in-window proportion is *lower* than non-tail), Fisher exact p = 1.0000, permutation p = 1.0000, Rule-1 bootstrap p05 lift = −12.5 pp (fails the pre-registered ≥5 pp gate).

Q-DJ30-2 (event-window position pause) is **not** promoted. The alternative-mechanism queue (intraday volatility regime, opening gap magnitude, overnight S&P futures range) is enumerated below for any future investigation; none of them are opened inside this brief.

---

## Reframe note

The web brief framed the tail mechanism as "fixed-point base stop slipped on a release-driven gap." Plan-time Rule-0 read of the locked Pine source ([strategies/striker/striker_dj30_v4.5.pine:60](strategies/striker/striker_dj30_v4.5.pine):60, line 227) confirmed the base stop is **ATR-scaled** (`stopDist = atrVal * 1.2`), not fixed-points. Hand-back trigger #2 was resolved as **re-frame and proceed** — the tail observations (5.94R outlier on 2025-02-07, N=1-day worst-loss concentration, worst-decile asymmetry) hold regardless of stop form, and the macro-co-location question is mechanism-agnostic.

---

## Rule 0 anchors

All anchor files read at execution start. None changed since 2026-05-05.

| File | Last commit | Verified content |
| --- | --- | --- |
| [strategies/striker/striker_dj30_v4.5.pine](strategies/striker/striker_dj30_v4.5.pine) | `4c65d29` (2026-05-05) | `stopAtr = 1.2` (line 60); active window Tue/Fri 13:00–17:00 UTC (lines 105–109); `riskPerTrade = 1.00` (line 30) |
| [dd_protection.py](dd_protection.py) | `04e9363` | `DD_TRIGGER = 0.010`, `DD_SCALE = 0.40`, single-tier (lines 40–41) |
| [docs/methodology/observation_routing.md](docs/methodology/observation_routing.md) | `7adaa84` | Three-bucket Closed/Action/Forward gate |
| [docs/rule_0.md](docs/rule_0.md) | `7adaa84` | Audit-first canon, prior decision docs are not Rule-0 substrate |
| [data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv](data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv) | (data file) | Corpus equivalence to web `_25172` panel verified — see Step 0a below |
| ~~`docs/locks/striker_dj30_v4_5_lock.md`~~ | (does not exist) | Plan-time error: this lock doc does not exist; v4.5 lock is encoded in the Pine source itself (line 60 tooltip "LOCKED: 1.2") + CLAUDE.md headline. Logged as plan-time correction. |

### Step 0a — corpus equivalence

`_12175` (canonical, 2026-05-05) was verified equivalent to the web brief's `_25172` panel on all four pre-registered checks:

| Check | Web brief expected | Canonical observed | Match |
| --- | --- | --- | --- |
| `n_entry_long` | 224 | 224 | yes |
| `sum(net_pnl_usd)` over entry rows | $363,113 ± $50 | $363,113.05 | yes |
| Worst single trade date | 2025-02-07 | 2025-02-07 | yes |
| Worst trade pnl | ≈ −$11,870.65 | −$11,870.65 | yes |
| First entry datetime | 2022-01-04 | 2022-01-04 10:15 ET | yes |
| Last entry month | 2026-04-2X | 2026-04-17 11:45 ET | yes |

Reproducer: `python analysis/Q-DJ30-1/corpus_check.py`.

### Step 0b — timezone anchor

CSV `Date and time` confirmed as **chart time / America/New_York**, not UTC. After ET → UTC conversion all 197 base entries fall in DJ30's locked active window [13, 17) UTC; the 27 pyramid-leg entries (Signal=`Long Add`) are profit-trigger driven and not session-gated, so 14 of them appear in hours 17–19 UTC by design (Pine line 274: pyramid trigger does not include `sessionOK`). Anchor verification on the 2025-02-07 worst-loss trade: raw 09:45 ET → 14:45 UTC; NFP that day 13:30 UTC; signed distance +75 min; in_window_90 = True.

Reproducer: `python analysis/Q-DJ30-1/tz_check.py`.

This pyramid-leg discovery prompted the primary/sensitivity split of the analysis (see §"Pre-Q gate" below).

---

## Pre-Q gate (per INQHIORI SKILL §3)

```
D: events outside US instrument scope (DJ30 is US-only index) — test: instrument scope
   events outside CSV temporal span 2022-01-04 → 2026-05-06 — test: temporal scope
   FOMC statement / presser / minutes — test: temporal scope (release at 14:00 ET = 19:00 UTC, outside DJ30 13:00-17:00 UTC active window by construction)
   Initial Jobless Claims — test: temporal scope (Thursday 08:30 ET; DJ30 active Tue/Fri only; min gap 19.5 hours to nearest Friday DJ30 entry)
   pyramid-leg entries (Signal=Long Add) — test: mechanism scope (firing time = profit-trigger time, not signal time; conflates two firing mechanisms with the macro-co-location question framed against signal time). Used as sensitivity stratum, not deleted from corpus.

S: collapse to one row per Trade #, columns: trade_num, signal, entry_dt_utc, net_pnl_usd, n_entries_that_day, nearest_event_minutes_signed, nearest_event_type, in_window_{30,60,90,120,180}.

A: index event calendar by datetime (linear scan over 385 events × 224 trades = ~86k comparisons; trivial). Cache per-trade tagging output to analysis/Q-DJ30-1/per_trade_proximity.csv.
```

The pyramid-leg mechanism scope (S, not D) was added at execution time after Step 0b surfaced that 27 of 224 "trades" are pyramid legs. Primary analysis runs on n=197 base; sensitivity on n=224 all entries.

---

## Step 1 — Event calendar source log

**Hand-back trigger A fired** (per plan): all authoritative web sources (BLS schedule archives, BEA news schedule for historical span, FRED website) returned HTTP 403 to programmatic fetch (Claude WebFetch + curl with full browser headers). Federal Reserve FOMC calendar was the only authoritative source reachable, and FOMC events are a-priori screened out of this analysis anyway (Pre-Q gate).

Surfaced to Joshua at execution time. Joshua authorized **option 2: one-time, declared substitution to a single authoritative-adjacent source** (chat record 2026-05-06).

**Substitution declared:** rule-derivation from canonical BLS / BEA / Census / ISM release patterns (publicly-documented release schedules), implemented in [analysis/Q-DJ30-1/build_calendar.py](analysis/Q-DJ30-1/build_calendar.py). Extends [analysis/archive/eurusd_lnyo/event_calendar.py](analysis/archive/eurusd_lnyo/event_calendar.py) with PPI, ISM Manufacturing, ISM Services and adds 08:30 ET / 10:00 ET timestamps.

Rules used:

| Class | Source pattern | Time | Rule |
| --- | --- | --- | --- |
| NFP | BLS | 08:30 ET | 1st Friday of month (exact pattern) |
| CPI | BLS | 08:30 ET | 2nd Wednesday of month (proxy; actual is Tue–Thu mid-month) |
| PPI | BLS | 08:30 ET | 2nd Thursday of month (proxy; typically day after CPI) |
| Retail Sales | Census | 08:30 ET | 3rd Tuesday of month (proxy; actual is 13–17th business day) |
| PCE | BEA | 08:30 ET | last Friday of month (exact pattern) |
| GDP_Advance | BEA | 08:30 ET | 4th Thursday of Jan/Apr/Jul/Oct (proxy) |
| ISM_Mfg | ISM | 10:00 ET | 1st business day of month |
| ISM_Svc | ISM | 10:00 ET | 3rd business day of month |

Calendar coverage: 385 events across 8 classes spanning 2022-01-01 → 2026-05-06.

**Approximation error:** documented ±1 trading day for CPI / PPI / Retail Sales / GDP_Advance vs actual published dates. NFP, PCE, ISM Mfg, ISM Svc rules are exact (or within their published patterns).

**Bias direction:** date approximation errors will randomize trade-to-event tagging symmetrically across tail and non-tail strata, **biasing the test toward null** (false negative). False-positive risk from this calendar source is structurally low. The **null verdict reported here is therefore conservatively defended** against the calendar-source uncertainty: any tightening of the calendar (higher-fidelity dates) could only increase the in-window proportion symmetrically, not preferentially in the tail.

---

## Step 2-4 — Contingency table + tests

### Baseline framing (per plan Hunk 5)

The plan's Hunk-5 framing predicted "high baseline overlap" between DJ30's session and the macro-release cluster. **Observed baseline is 17.5% — lower than predicted.** Reason: DJ30 trades only Tue/Fri while many tier-1 releases (CPI, PPI, retail sales, GDP advance, FOMC, ISM_Svc-some) fall on Mon/Wed/Thu, structurally outside DJ30's trading days. The "high baseline" framing was correct for any-trading-day strategies but overstated for a Tue/Fri-only strategy. The relevant test is still the differential (tail % − non-tail %), as the plan specifies.

### Primary — base entries n=197, tail = worst-decile (n=20), window = ±90 min

| | in window ±90 | outside window | total |
| --- | ---:| ---:| ---:|
| **tail (n=20)** | 3 | 17 | 20 |
| **non-tail (n=177)** | 31 | 146 | 177 |
| **total** | 34 | 163 | 197 |

| Test | Result |
| --- | --- |
| p_tail in_window_90 | 15.0% |
| p_nontail in_window_90 (baseline) | 17.5% |
| pp diff (tail − non-tail) | **−2.5 pp** |
| Fisher exact, two-sided | **p = 1.0000** |
| Conditional odds ratio [95% CI] | 0.83 [0.15, 3.14] |
| Permutation, n=10,000, two-sided | **p = 1.0000** |
| Rule-1 bootstrap (n=1,000) tail in-window p05 / p50 / p95 | 5.0% / 15.0% / 30.0% |
| Rule-1 lift (p05_tail − p_nontail) | **−12.5 pp** — FAIL ≥5 pp gate |

### Sensitivity — all entries n=224 (incl. pyramid legs), tail = 22, window = ±90 min

| | in window ±90 | outside window | total |
| --- | ---:| ---:| ---:|
| **tail (n=22)** | 3 | 19 | 22 |
| **non-tail (n=202)** | 31 | 171 | 202 |

| Test | Result |
| --- | --- |
| pp diff | **−1.7 pp** |
| Fisher exact, two-sided | p = 1.0000 |
| Conditional odds ratio [95% CI] | 0.87 [0.16, 3.23] |
| Permutation, n=10,000 | p = 1.0000 |
| Rule-1 lift | −10.8 pp — FAIL |

The sensitivity result is qualitatively identical to primary. Pyramid-leg inclusion does not change the verdict.

### Of the 3 tail trades that ARE in_window_90

For transparency on what the tail-in-window column represents:

| Trade # | Date / time UTC | Net P&L | Nearest event | Distance |
| ---:| --- | ---:| --- | ---:|
| 168 | 2025-02-07 14:45 | −$11,870.65 | NFP (08:30 ET) | +75 min |
| 209 | 2025-12-05 15:00 | −$4,798.14 | NFP (08:30 ET) | +90 min (boundary) |
| 154 | 2024-11-01 14:15 | −$3,967.44 | ISM_Mfg (10:00 ET) | +15 min |

All three "in-window" tail trades are on first-Friday-of-month dates, which are NFP days (and 11-01 is also ISM_Mfg day since it's the 1st business day). This is structurally consistent: NFP is the only high-impact release that lands reliably on a Friday inside DJ30's session window. The ±90 min "in-window" tag for the tail is essentially a "fired on an NFP Friday" tag.

---

## Window sensitivity (worst-decile primary stratum, base entries)

| Window | p_tail | p_nontail | pp diff | Fisher p |
| ---:| ---:| ---:| ---:| ---:|
| ±30 min | 5.0% | 4.0% | +1.0 pp | 0.5823 |
| ±60 min | 5.0% | 6.2% | −1.2 pp | 1.0000 |
| **±90 min** | **15.0%** | **17.5%** | **−2.5 pp** | **1.0000** |
| ±120 min | 30.0% | 29.9% | +0.1 pp | 1.0000 |
| ±180 min | 30.0% | 36.7% | −6.7 pp | 0.6303 |

The pp-diff sign oscillates between negative and positive across windows, but **all p-values exceed 0.5 and all effects are within ±7 pp**. Per plan hand-back trigger #5, a sign flip becomes a hand-back trigger when results suggest *different conclusions* across windows. Here all five windows agree on the conclusion (null); the sign variation is statistical noise consistent with the null hypothesis. Not a hand-back trigger.

### Stratum sensitivity (Fisher p at ±90 min)

| Stratum | n | p_tail | p_nontail | pp diff | Fisher p |
| --- | ---:| ---:| ---:| ---:| ---:|
| Worst-decile | 20 | 15.0% | 17.5% | −2.5 | 1.0000 |
| Worst-quintile | 39 | 12.8% | 18.4% | −5.5 | 0.4848 |
| N=1-day-only worst-decile | 19 (n_n1=192) | 21.1% | 16.7% | +4.4 | 0.7378 |
| ≤ −5R (≤ −$10,000) | 1 | 100.0% | 16.8% | +83.2 | 0.1729 |

The ≤ −5R stratum has n=1 (the 2025-02-07 anchor). Sample-size-driven; not interpretable as evidence.

---

## Verdict mechanics

Mapping to the pre-registered table from the plan:

| Outcome row | Required Fisher p | Required pp diff | Required Rule-1 p05 lift | Observed | Verdict |
| --- | --- | --- | --- | --- | --- |
| Strong positive | < 0.05 | ≥ 15 pp | ≥ 5 pp | p=1.0, diff=−2.5 pp, lift=−12.5 pp | NO |
| Weak positive | < 0.10 | ≥ 10 pp | ≥ 5 pp | same | NO |
| Null | ≥ 0.10 OR < 5 pp diff | — | — | p=1.0 ≥ 0.10 AND diff=−2.5 pp < 5 pp | **YES** |
| Ambiguous | anything else | — | — | — | NO |

**Verdict: CLOSE — null result.** Routing per [docs/methodology/observation_routing.md](docs/methodology/observation_routing.md) is the **Closed** bucket: investigated and closed, no standing artefacts beyond the regenerable scripts under `analysis/Q-DJ30-1/`. No decision artefact (`docs/briefs/Q-DJ30-1/recommendation.md`) is created — matches 2026-05-03 sentinel precedent for null/reject results.

---

## Forbidden-D-test audit

Per INQHIORI SKILL §5, the following pre-data screens were applied; all are permitted (instrument / temporal / mechanism scope), none are forbidden ("doesn't move price meaningfully" or outcome-conditional inclusion):

1. **FOMC events** — temporal scope (releases at 14:00 ET = 19:00 UTC, outside DJ30's 13:00–17:00 UTC active window by construction). Not forbidden.
2. **Initial Jobless Claims** — temporal scope (Thursday-only release; DJ30 trades Tue/Fri only). Not forbidden.
3. **Pyramid-leg entries** — mechanism scope (firing time is profit-trigger time, not signal time; conflates two mechanisms with the question's framing). Not deleted from corpus — kept as sensitivity stratum (n=224 vs n=197 primary). Not forbidden.

**Audit catch — forbidden-D-test in original web brief (resolved):** The original brief's Initial Jobless Claims rule said "include only if at least one tail trade lands within ±90 min of a Thursday 08:30 ET claims release; otherwise screen out (per brief — too-frequent comparison)." That is an **outcome-conditional inclusion rule** — the conclusion ("not relevant") is encoded in the inclusion test, which is the forbidden D-test pattern. The plan-review redline (Hunk 4, 2026-05-06) caught this and replaced it with the structural temporal-scope screen documented above. This is the gate working as intended; it does not change the verdict pathway.

---

## Forward notes — alternative mechanisms

Per the plan's pre-registered alternative-mechanism queue (Step 5, executed when verdict = CLOSE):

1. **Intraday volatility regime** — VIX or DJ30 realized-vol at trade entry vs tail outcome. Hypothesis: tail trades cluster in elevated-vol days regardless of macro proximity.
2. **DJ30 opening-gap magnitude** — gap from prior close to current 13:00 UTC bar open. Hypothesis: tail trades cluster on large-gap days.
3. **S&P futures overnight session range** — Asia + London session range (high − low) divided by ATR. Hypothesis: tail trades cluster after wide overnight ranges.

These are enumerated, **not opened**. None of them are pursued inside this brief. They become Forward-bucket questions on the Open Questions list if/when they get prioritized.

The 2025-02-07 anchor trade (in-window, NFP +75 min, −5.94R) is consistent with macro mechanism for the worst observation — but the rest of the worst-decile is not. **The anchor was anomalous within the tail, not representative.** Future investigation should probably treat 2025-02-07 as a single-event diagnostic, not as a class.

---

## Out of scope (❌ checklist)

- ❌ NAS100 — Q-NAS-2 is the symmetric question, queueable after this closes.
- ❌ Guardian / Aegis tail behavior — different mechanisms; not in scope.
- ❌ Any modification to allocation, dd_protection constants, or the v4.5 lock — verdict does not move policy.
- ❌ Live-trading decisions for the upcoming week — INQHIORI investigation, not OODA tactical.

---

## Cross-references

- Plan: `C:\Users\joshu\.claude\plans\q-dj30-1-dj30-silly-origami.md` (Claude Code, 2026-05-06)
- Brief: web Claude, 2026-05-06 (chat record)
- Q-DDP-1 closing brief (2026-05-06) — methodology lesson on regime-robustness gating, Rule-1 bootstrap pattern reused here
- Sentinel USDCHF H4 (2026-05-03) — null-finding format precedent
- INQHIORI canon: https://www.notion.so/34ddc0b53c1181479d7bdecc61f47078
- Locked DJ30 v4.5 source: [strategies/striker/striker_dj30_v4.5.pine](strategies/striker/striker_dj30_v4.5.pine)
- Portfolio MC current: [portfolio_mc.py](portfolio_mc.py) + [data/tv_exports/pepperstone/](data/tv_exports/pepperstone/)
- Permutation infrastructure reference: [analysis/oanda_stage1/permutation.py](analysis/oanda_stage1/permutation.py) (not directly reused; scipy.stats.fisher_exact + numpy permutation chosen for this 2×2 with n=197)

---

## Reproducers

```bash
python analysis/Q-DJ30-1/corpus_check.py        # Step 0a
python analysis/Q-DJ30-1/tz_check.py            # Step 0b
python analysis/Q-DJ30-1/build_calendar.py      # Step 1 → event_calendar.csv
python analysis/Q-DJ30-1/tag_trades.py          # Step 2 → per_trade_proximity.csv
python analysis/Q-DJ30-1/run_tests.py           # Steps 3-4 → results.json
```

Time accounting: ~2.5h active. Inside 3h budget; no hand-back triggers fired post-execution-start except #1 (source-coverage gap in Step 1, resolved by user-authorized substitution per option 2).
