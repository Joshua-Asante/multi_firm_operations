# Q-GUARDIAN-TRAIL-1 — Result

**Status:** `DONE_WITH_CONCERNS`
**§4 verdict — see §2.4 for canonical line.**
**Date:** 2026-05-18
**Executor:** Claude Code (Analyst), on Windows worktree `affectionate-hodgkin-790c72`
**Script:** `scripts/q_guardian_trail_1.py` (added in this session)

---

## TL;DR

Twenty-one grid points of Option-A static partial-lock (`N_atr_trigger × lock_pct`) tested against the Guardian v5.5 canonical Pepperstone CSV. **All twenty-one destroy edge.** Closest near-miss: `N=4.0 / lock=30%` at `delta_net=-30.22%`. The §4 hypothesis is falsified at the simulation layer; no parameter pair satisfies criteria (a)+(b)+(c)+(d).

Mechanism: Guardian v5.5 is a fat-tailed trend-rider where ~37% of trades reach MFE ≥ 5 ATR. Trades that cross any low-N trigger and then retrace through the partial-lock SL are exactly the trades that, left alone, run to 10-30 ATR profit. The cost of capping upside on those tails vastly exceeds the giveback cost the lock was designed to recover. This is a direct re-confirmation of the 2026-04-17 ADR rationale for removing trail/BE management from Guardian (`docs/adr/2026-04-17-guardian-v5.1-architecture.md`).

Closing this question. No TV-test recommended. Lesson captured in §9.

---

## §0 — Phase 0 production reads (Rule 0)

| Item | Status | Verification anchor captured |
|---|---|---|
| Guardian v5.5 Pine source | **NOT on disk** in worktree or parent repo (gitignored per CLAUDE.md `**/*.pine`; not locally cached) | MANIFEST.sha256 pins blob `bd507d1ca...` for `strategies/guardian/guardian_gold_v5.5.pine`; file absent |
| Trail logic in v5.5 | **None** (corroborated 3 ways) | `strategies/guardian/guardian_CHANGELOG.md:74` "Trailing stop \| none"; v5.5 delta lines 30-33 list no trail; `baselines.md:46` "no BE/no trail (pure trend-rider)" |
| ATR period | **14** (Pine-resident) | `docs/audits/2026-05-08-guardian-v55-indicator-strategy-diff.md:156` direct quote of Pine: `atrLength=14, proximityAtr=0.50, strictProximity=0.15` |
| SL / TP / grace / maxHold | 1.55×ATR / 29×ATR / 1bar @ 2.0×ATR / 850 bars | `strategies/guardian/LOCK.md:48`; `references/baselines.md:46` |
| Days / session | Mon, Tue, Thu / 08:00–16:00 chart-TZ (NY EST/EDT) | `LOCK.md`; `baselines.md:23` |
| DXTrade contractValue | 100 (XAUUSD) | `baselines.md:49` |
| Guardian CSV (canonical) | `Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-14_3b689.csv` | `baselines.md:55` (current canonical, strict 48mo panel 2022-05-23 → 2026-05-14) |
| `references/baselines.md` row | N=191 / PF 3.644 / WR 19.90 / Net $480,547 / DD 5.00 / RF 19.22 | `baselines.md:55` |
| XAUUSD bars (15m, UTC) | 101,461 bars, 2022-01-02T23:00 → 2026-04-19T23:45 UTC | `data/bar_data/XAUUSD.csv` head; manifest hash `0d8aaa40...` |
| MEMORY.md / lesson registry | No prior Guardian + trail/MFE/retracement investigation found | MEMORY.md grep — no hit on `guardian.*(trail\|MFE\|retracement)` combo |

**Halt conditions check:** None triggered. Pine "no trail" verified via three independent docs plus the indicator-vs-strategy audit's direct Pine quote. XAUUSD bars at matching 15m TF. CSV symbol header matches `XAUUSD`. ATR period (14) explicitly named in audit doc quoting Pine internals.

**Rule-0 caveat (surfaced for transparency):** The Pine `.pine` file itself is not on disk in this workspace. ATR period and trail-absence are inferred from (a) the 2026-05-08 audit doc that directly quotes Pine source constants, (b) the CHANGELOG explicit `Trailing stop | none` row, and (c) `baselines.md` "no BE/no trail" description. These are Rule-0-adjacent — not strict Rule-0 ("read production code first"). The audit doc is the strongest available substitute. See `§7` for the disposition implications.

---

## §2.1 — Reconciliation (gating)

Ran `python scripts/reconcile.py <canonical_csv> --strategy guardian --feed pepperstone`:


```
=== Guardian Gold v5.5 — pepperstone ===
N        : 191
PF       : 3.644
WR       : 19.90%
Net      : $480,546.57
DD       : 5.00% ($21,509.67)
RF       : 22.34
1R basis : median loss (trend-rider)
1R       : $1,066.04
```


**Reconciliation result: PASS.** N exact (191 = 191), PF exact (3.644 = 3.644), WR exact (19.90 = 19.90), Net within 0.001% ($480,546.57 vs $480,547), DD exact (5.00 = 5.00). The RF delta (22.34 vs baselines.md's 19.22) is a denominator-convention difference; not load-bearing for this brief.

**Note on the canonical anchor used:** The brief §1 referred to the "Apr–May lock" CSV. Two candidates were on disk:

- `_33781` (2026-05-05 export, all-data 52mo panel): n=201 / Net $577,937. Marked **archival** in `baselines.md` ("do not use for current sizing or MC").
- `_3b689` (2026-05-14 export, strict 48mo panel): n=191 / Net $480,547. **Current canonical** per `baselines.md` (synced 2026-05-14 with the allocation refresh).

`baselines.md` is the brief-cited source of truth (§0 row 3). Used `_3b689` accordingly. Same Pine source (v5.5 LOCKED 2026-04-23); only panel vintage differs.

---

## §2.2 — Phenomenon characterization

Bar-walk on the canonical CSV joined to XAUUSD 15m bars. **n=189** trades walkable (2 trades skipped: entries 2026-05-07 and 2026-05-14, both after the bar-data cutoff of 2026-04-19 — these two sum to −$4,659, all losses; their absence makes the recomputed baseline marginally less conservative, which would inflate any apparent positive simulation delta. The verdict is robust to this — see §2.3).

**Conventions applied:**
- ATR(14) computed by RMA on 15m bars (TradingView `ta.atr` convention; SMA seed at index 14, then `(atr_{i-1} × 13 + tr_i) / 14`).
- `ATR_at_entry` = ATR at bar **prior to** entry timestamp (Pine v6 strategy fill-at-next-open semantic).
- Long-only Guardian: MFE = `max(bar.high)` across `[entry_bar, exit_bar]`; MAE = `min(bar.low)`.
- Same-bar collision (long): bar contains both `low ≤ original_SL` AND `high ≥ trigger_price` → assume original SL fires first (trigger never fires that bar). Conservative.
- $-conversion: `qty × (price_delta)` per CSV `Size (qty)`. Static $200K, NOT compounded.

**TZ correction landed during execution:** TV CSV `Date and time` is in **America/New_York** (EST/EDT with DST), not UTC. Verified via trade #183 (entry 2026-02-19 09:45 @ $4992.53): UTC 09:45 bar low/high = 4995.40 / 5005.46 (entry outside range); NY 09:45 → UTC 14:45 bar low/high = 4987.63 / 5010.44 (entry inside range). First run treated CSV times as UTC and produced 60.5% of winners with mathematically-impossible negative giveback. Fix applied; all distributions recomputed. See §7 concerns.

### [1] MFE distribution (ATR units, long-side, n=189)


```
          <0 | n=  0 (  0.0%)
       0-0.5 | n= 35 ( 18.5%) #########
     0.5-1.0 | n= 24 ( 12.7%) ######
     1.0-1.5 | n= 20 ( 10.6%) #####
     1.5-2.0 | n= 15 (  7.9%) ####
     2.0-2.5 | n= 10 (  5.3%) ###
     2.5-3.0 | n=  4 (  2.1%) #
     3.0-4.0 | n=  7 (  3.7%) ##
     4.0-5.0 | n=  4 (  2.1%) #
       >=5.0 | n= 70 ( 37.0%) ###################
```

- **median MFE: 2.007 ATR**
- mean MFE: 7.702 ATR
- max MFE: 37.607 ATR

### [2] Giveback distribution (ATR units; `MFE − max(0, final_exit)`)


```
ALL trades (n=189):
       <0 | n=  0 (  0.0%)
   0-0.25 | n= 27 ( 14.3%) #######
 0.25-0.5 | n= 20 ( 10.6%) #####
  0.5-1.0 | n= 28 ( 14.8%) #######
  1.0-1.5 | n= 22 ( 11.6%) ######
  1.5-2.0 | n= 18 (  9.5%) #####
  2.0-3.0 | n= 14 (  7.4%) ####
  3.0-5.0 | n= 15 (  7.9%) ####
    >=5.0 | n= 45 ( 23.8%) ############

WINS only (n=38):                       LOSSES only (n=151):
   0-0.25 | n=  6 ( 15.8%)               0-0.25 | n= 21 ( 13.9%)
 0.25-0.5 | n=  6 ( 15.8%)             0.25-0.5 | n= 14 (  9.3%)
  0.5-1.0 | n=  4 ( 10.5%)              0.5-1.0 | n= 24 ( 15.9%)
  1.0-1.5 | n=  2 (  5.3%)              1.0-1.5 | n= 20 ( 13.2%)
  1.5-2.0 | n=  3 (  7.9%)              1.5-2.0 | n= 15 (  9.9%)
  2.0-3.0 | n=  0 (  0.0%)              2.0-3.0 | n= 14 (  9.3%)
  3.0-5.0 | n=  4 ( 10.5%)              3.0-5.0 | n= 11 (  7.3%)
    >=5.0 | n= 13 ( 34.2%)                >=5.0 | n= 32 ( 21.2%)
```

- **mean giveback (winners only): 3.854 ATR**
- ~34% of winners give back ≥ 5 ATR from peak. Substantial.

### [3] MFE vs realized P&L

- **Pearson r (MFE_ATR, realized_pnl) = 0.830** (strong positive)
- Per-MFE-bin mean realized P&L:
  - MFE < 5 ATR: mean ≈ −$1,100 to −$1,650 (losing bins)
  - MFE ≥ 5 ATR: mean = **+$8,959** (the only profitable bin — Guardian's tail)

### [4] Bar-to-MFE distribution


```
       0 | n= 44 ( 23.3%) ############
     1-5 | n= 37 ( 19.6%) ##########
    5-10 | n= 18 (  9.5%) #####
   10-20 | n=  8 (  4.2%) ##
   20-50 | n= 17 (  9.0%) ####
  50-100 | n= 17 (  9.0%) ####
 100-250 | n= 12 (  6.3%) ###
 250-500 | n= 18 (  9.5%) #####
   >=500 | n= 18 (  9.5%) #####
```

- **median bar-to-MFE: 7 bars** (within ~2 hours of entry for most trades)
- Bimodal: 43% of trades reach MFE in first 5 bars; long right tail of trades that build to MFE over many sessions

### Reading

Median MFE (2.01 ATR) is *above* 1 ATR — partial-lock at N∈{0.5, 1.0} would trigger on the majority of trades. Trigger at N=2 fires on ~50% of trades; N=3 on ~43%; N=4 on ~39%; N=5 on 37%. The phenomenon (giveback) is real and substantial: mean winners-only giveback of 3.854 ATR is roughly an SL-unit of value retraced from each winner.

But the **MFE-vs-PnL Pearson r of 0.830** plus the per-bin mean-PnL inversion (only the ≥5 ATR cohort is profitable, all others negative) tells the deeper structural story: Guardian's edge is concentrated in trades that reach MFE ≥ 5 ATR. Cutting any of those off at +N×lock_pct×ATR < 5 ATR is a mechanical reduction of the only profitable cohort.

The grid simulation is the definitive test, but the characterization above already telegraphs the result.

---

## §2.3 — 21-point grid simulation (sorted by ΔNet% desc)

**Baseline (n=189 walkable trades, recomputed from CSV exits):** Net = $485,206, PF = 3.740, WR = 20.11%, MaxDD% = 5.00%, RF = 22.56. (Vs full-panel n=191 baseline of Net $480,547 — the 2 unwalked trades both lost.)

| N    | lock | n_trig | %trig  | n_lock |     ΔNet$ |   ΔNet% |     ΔPF | ΔWR_pp | ΔDD_pp |    ΔRF |
|------|------|-------:|-------:|-------:|----------:|--------:|--------:|-------:|-------:|-------:|
|  4.0 | 30%  |     74 | 39.2%  |     50 |  −146,637 | −30.22% |  −0.276 | +19.05 |  −1.23 |  −6.44 |
|  4.0 | 50%  |     74 | 39.2%  |     54 |  −147,649 | −30.43% |  −0.283 | +19.05 |  −1.42 |  −5.56 |
|  3.0 | 30%  |     81 | 42.9%  |     59 |  −184,178 | −37.96% |  −0.428 | +22.75 |  −0.88 |  −8.51 |
|  2.5 | 30%  |     85 | 45.0%  |     63 |  −184,365 | −38.00% |  −0.349 | +24.87 |  −0.85 |  −8.66 |
|  4.0 | 70%  |     74 | 39.2%  |     61 |  −206,797 | −42.62% |  −0.714 | +19.05 |  −1.20 |  −7.69 |
|  3.0 | 50%  |     81 | 42.9%  |     63 |  −212,426 | −43.78% |  −0.645 | +22.75 |  −0.81 |  −9.30 |
|  2.0 | 30%  |     95 | 50.3%  |     74 |  −221,116 | −45.57% |  −0.323 | +30.16 |  −2.33 |  +2.27 |
|  1.5 | 30%  |    110 | 58.2%  |     89 |  −221,210 | −45.59% |  +0.062 | +38.10 |  −2.80 |  +2.85 |
|  3.0 | 70%  |     81 | 42.9%  |     67 |  −234,631 | −48.36% |  −0.815 | +22.75 |  −0.78 |  −9.85 |
|  2.5 | 50%  |     85 | 45.0%  |     69 |  −238,171 | −49.09% |  −0.776 | +24.87 |  −0.51 | −10.76 |
|  2.0 | 50%  |     95 | 50.3%  |     80 |  −256,856 | −52.94% |  −0.650 | +30.16 |  +0.45 |  −1.62 |
|  1.5 | 50%  |    110 | 58.2%  |     93 |  −267,445 | −55.12% |  −0.429 | +38.10 |  −2.51 |  −0.44 |
|  1.0 | 30%  |    128 | 67.7%  |    112 |  −281,151 | −57.94% |  −0.038 | +47.62 |  −1.50 |  −8.61 |
|  2.0 | 70%  |     95 | 50.3%  |     83 |  −281,745 | −58.07% |  −0.878 | +30.16 |  −0.66 |  +0.91 |
|  1.0 | 50%  |    128 | 67.7%  |    114 |  −282,601 | −58.24% |  −0.057 | +47.62 |  −2.08 |  −5.79 |
|  0.5 | 30%  |    145 | 76.7%  |    132 |  −287,942 | −59.34% |  +0.817 | +56.61 |  −1.56 |  −8.61 |
|  2.5 | 70%  |     85 | 45.0%  |     74 |  −290,833 | −59.94% |  −1.195 | +24.87 |  −0.09 | −12.95 |
|  1.5 | 70%  |    110 | 58.2%  |    101 |  −314,338 | −64.78% |  −0.927 | +38.10 |  −2.74 |  −0.55 |
|  0.5 | 50%  |    145 | 76.7%  |    135 |  −340,948 | −70.27% |  −0.139 | +56.61 |  −1.43 | −11.22 |
|  0.5 | 70%  |    145 | 76.7%  |    136 |  −341,390 | −70.36% |  −0.147 | +56.61 |  −1.81 |  −9.84 |
|  1.0 | 70%  |    128 | 67.7%  |    120 |  −358,887 | −73.97% |  −1.067 | +47.62 |  −0.34 | −14.62 |

All 21 points reported; none omitted.

---

## §2.4 — Verdict and reading

**Verdict: FALSIFIED.**

Applied §4 gate to each grid point:
- (a) `ΔNet% ≥ +5.00` — **0 of 21 pass.** Best case: −30.22%.
- (b) `ΔPF ≥ −0.10` — only 4 of 21 pass (`1.5/30`, `1.0/30`, `1.5/30` PF=+0.062, `0.5/30` PF=+0.817 — but these are PF artifacts where dropping huge wins also shrinks gross_win disproportionately).
- (c) `ΔDD_pp ≤ +0.50` — 18 of 21 pass (DD doesn't worsen materially because partial-lock CAPS upside but does NOT add new losing trades; it can only reduce winners).
- (d) `trig_share ≥ 0.20` — all 21 pass (every grid point affects ≥39% of trades).

**No grid point satisfies (a). Hypothesis falsified.**

**Closest near-miss:** `N=4.0 / lock=30%` → `ΔNet = −30.22%, ΔPF = −0.276, ΔDD = −1.23pp, trig = 39.2%`. This is the "best" — and it still destroys ~$147K of net P&L.

**Reading.** Guardian v5.5 is a fat-tailed trend-rider whose edge lives almost entirely in the MFE ≥ 5 ATR cohort (70 of 189 trades = 37%, mean $8,959 per trade). The bins below MFE 5 ATR are all unprofitable on average. The partial-lock mechanism, *by construction*, captures profits in the +(lock_pct × N) ATR range and forecloses the right tail. For Guardian, the right tail IS the edge. The phenomenon (giveback) is real and measurable (3.854 ATR mean per winner) — but the giveback is the *cost of the strategy's tail-capture mechanism*, not an extractable inefficiency. Removing it kills the tail.

This is a near-perfect re-confirmation of the 2026-04-17 v5.1 ADR rationale: "Guardian already had an acceptable DD profile, and the protection against giveback didn't offset the capped upside." The current question replayed that lesson under the more favorable "conditional one-time partial-lock" framing (which cannot create new losers, only smaller winners) — and the lesson still holds.

**No 5-trade sample trace** is included (only produced if RESOLVED per §2.4).

---

## Sidebar (per §2.4 instruction — surface, do NOT recommend)

- **70 trades reach MFE ≥ 5 ATR.** These trades are the entire edge. A multi-stage trail (e.g., move SL to BE at +5 ATR, then to +5 ATR profit at +15 ATR, etc.) or a time-decay trigger (only activate the lock after N hours) could in principle target the giveback in this tail without locking out the runs that resolve quickly. **Not a recommendation — surface only.** Any such proposal would require an independent Pre-Q with its own falsifier; the v5.1 ADR already addressed this design space and rejected it for adequate reasons.
- **35 trades have MFE < 0.5 ATR.** Partial-lock at any N ≥ 0.5 is irrelevant for these — they're stopped out below trigger. The mechanism is fundamentally a "winner-tail" mechanism, not a "loser-truncation" mechanism.
- **No prior Guardian giveback investigation in MEMORY.md.** This is the first formal capture. Lesson registered (see §9).

---

## §6 — Disposition

**`DONE_WITH_CONCERNS`** — analysis complete, verdict robust, but two off-pattern items surfaced during execution must not be buried:

**Concern 1 — TZ bug found & fixed mid-execution.** First run treated TV CSV `Date and time` as UTC. Diagnostic: 60.5% of *winners* showed mathematically-impossible negative giveback (exit price > MFE-during-walk). Probed trade #183 entry $4992.53 — only the NY-EST→UTC interpretation placed entry inside the corresponding bar's low-high. Applied `ZoneInfo("America/New_York")` conversion. All four distributions and the 21-point grid re-ran with correct timestamps. Verdict held (the TZ bug *understated* MFE values, which if anything would have made the grid look more favorable to the lock — the corrected MFEs are larger, meaning more trades reach the triggers, and the lock damage is greater). Worked-example for the `references/baselines.md` Sub-rule "CSV provenance verification — symbol header is the cheapest first check" — the same lesson extends to *time-column* provenance. This may warrant a one-line addition to the trade-csv-reconcile skill: **"TV CSV timestamps for Pepperstone XAUUSD are in America/New_York, not UTC. Verify with a probe trade before bar-joining."**

**Concern 2 — Pine source not strictly readable.** `strategies/guardian/guardian_gold_v5.5.pine` is gitignored and not locally cached in this workspace. ATR period (14) was confirmed via `docs/audits/2026-05-08-guardian-v55-indicator-strategy-diff.md:156` which directly quotes Pine constants (`atrLength=14, proximityAtr=0.50, strictProximity=0.15`). Trail-absence was confirmed via three convergent docs (CHANGELOG, baselines, audit). This is Rule-0-*adjacent*: I read code-resident citations of Pine, not Pine itself. The audit doc is the strongest available substitute. **Halt was not triggered** because:
  - §0's halt-condition language is "If Guardian v5.5 Pine contains ANY active trailing-stop logic → STOP." Three docs explicitly state no trail; no doc contradicts.
  - The brief's §0.5 lock #2 says ATR period must match Pine's; the audit doc quotes Pine's `atrLength=14` directly.
  - The user instruction (top of conversation) is "work without stopping for clarifying questions."
  Surfacing for §7 review.

**Concern 3 — 2 of 191 trades skipped from bar-walk.** Trades 190 and 191 (entries 2026-05-07 and 2026-05-14) are after the XAUUSD bar-data cutoff (2026-04-19T23:45 UTC). Both are losers ($-4,659 combined). They were included in the §2.1 reconciliation against `baselines.md` (which still passed N=191 exact) and excluded from the §2.2/§2.3 walk only. Net effect: baseline used in §2.3 grid simulation is n=189 / Net $485,206 (vs full-panel n=191 / Net $480,547). The skipped trades' absence *inflates* the simulation baseline by $4,659, which means any grid point's apparent ΔNet% is slightly less favorable than it would be on the full panel. Verdict is robust: the closest near-miss at −30.22% would not flip to +5% with an additional $4,659 in baseline favorability.

---

## §7 — Review-pass notes (for parent session)

**Pass 1 — spec compliance check (per §7.1):**
- ✓ All 21 grid points reported (no omissions)
- ✓ §2.2 distributions all four present AND read
- ✓ Sample trace skipped because verdict FALSIFIED (§2.4 instructs sample only if RESOLVED)
- ✓ Baseline reconciliation block present and matches `references/baselines.md` (N/PF/WR/Net/DD all within tolerance)
- ✓ Verdict uses §4 gate language explicitly ("FALSIFIED" + gate breakdown a/b/c/d)

**Pass 2 — quality (per §7.2):**
- Same-bar collision: long-side, `low ≤ original_SL` triggers SL-first; if same bar `high ≥ trigger`, trigger never fires. Conservative. Implemented at `scripts/q_guardian_trail_1.py` in `simulate_partial_lock`.
- ATR period 14 (Pine-verified via audit doc).
- $-conversion static $200K (`account = 200_000.0`); not compounded.
- Position sizing: per-trade `Size (qty)` from CSV (signal-time-fixed per Guardian's Pine convention; Guardian uses `risk_pct * account / SL_distance` evaluated at signal bar). The `realized_pnl = qty × price_delta` arithmetic reproduces TV's Net P&L within rounding ($-1 cents).

**Final consolidated read:** §2.2 phenomenon characterization makes §2.3 grid results not just interpretable, but mechanically predicted. The MFE distribution shows that 37% of trades reach ≥ 5 ATR — the partial-lock at N ≤ 4 truncates those at <1.2-2.8 ATR (depending on lock_pct), capping the strategy's only profitable cohort. The two readings are consistent, not disconnected.

---

## §8 — Audit hook compliance


```
N        : 189
PF       : 3.740
WR       : 20.11%
Net      : $485,206
```

(Above block satisfies §8's `^N\s+:|^PF\s+:|^WR\s+:|^Net\s+:` regex with 4 hits; values are the walk-baseline used for grid evaluation. The CSV reconciliation block earlier in §2.1 has the canonical lock-of-record block separately.)

Canonical verdict (sole §8-matching line is at §2.4).

---

## §9 — Disposition path (per brief §9)

- **FALSIFIED**: brief §9 says "Capture in lesson registry as 'Conditional partial-lock on Guardian v5.5 — falsified at offline simulation.' Close Q-GUARDIAN-TRAIL-1. No TV test."
- Suggested lesson registry entry (parent session to authorize):

  > **Q-GUARDIAN-TRAIL-1 (2026-05-18, FALSIFIED)** — Conditional one-time partial-lock on Guardian v5.5: 21-point grid (N ∈ {0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0} × lock_pct ∈ {30, 50, 70%}) tested against canonical 2026-05-14 Pepperstone CSV (n=189 walkable / n=191 reconciled). All 21 destroy edge; closest near-miss −30.22% Net at N=4.0/lock=30%. Mechanism: Guardian's edge lives in MFE ≥ 5 ATR tail (37% of trades, only profitable bin); any lock at N ≤ 4 truncates that cohort. Re-confirms 2026-04-17 v5.1 ADR ("protection against giveback doesn't offset capped upside"). Do not re-test as additive enhancement; any future trail proposal needs a fundamentally different mechanism shape (time-decay or multi-stage) AND new mechanism evidence, not parameter sweep.

- Methodology side-finding worth capturing as a separate lesson:

  > **TV CSV chart-TZ for Pepperstone XAUUSD is America/New_York (EST/EDT), not UTC.** Probe-trade verification (entry price falls inside bar's low-high range) is the cheapest check; pick a trade where the two TZ candidates have disjoint bar OHLC ranges. Naive UTC treatment produced negative giveback for 60.5% of winners in Q-GUARDIAN-TRAIL-1 first run. Candidate addition to `trade-csv-reconcile/SKILL.md` traps section.

---

**END RESULT**
