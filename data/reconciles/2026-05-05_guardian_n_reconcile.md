# Guardian trade-count reconcile (2026-05-05)

**Trigger:** reconcile run reported Guardian n=209; investigator's working
"canonical" was 201, with cross-contamination suspicion against NAS100 B_15.

**Verdict (one line):** 209 is the canonical Guardian trade count for the
locked Pepperstone v5.5 panel. The "201" baseline is stale, sourced from a
pre-2026-04-26 CSV snapshot that no longer exists on disk. No
cross-contamination.

**Rule 0 binding honored:** all counts below come from reading the CSVs
directly; identity gates verified against `portfolio_mc.py` source, not
memory or briefs.

## Files read (with line numbers for key constants)

| File | Key lines |
|---|---|
| [portfolio_mc.py](portfolio_mc.py) | 70-75 (Pepperstone panel paths), 86 (expected symbols), 93 (expected versions), 102-124 (load_trades — only floor `assert_min_rows ≥ 100` + `assert_window ≥ 4yr`, **no per-strategy n_trades hardcode**), 451-458 (`assert_tv_export` identity gate per panel) |
| [lib/mvd.py](lib/mvd.py) | 33-43 (`assert_min_rows`), 46-63 (`assert_window`), 139-172 (`assert_tv_export`) |
| [tests/test_tv_export_loader.py](tests/test_tv_export_loader.py) | 22-23 (**Guardian canonical pin: n_trades=209**), 26-27 (DJ30 v4.5 = 224), 30-31 (Aegis = 123), 34-35 (NAS100 v1 = 200) |
| [tests/test_mc_anchors.py](tests/test_mc_anchors.py) | (no per-strategy n_trades pinned; pins pass/bust/p99_dd + n_bdays=1120, n_blocks=223 only) |
| [data/tv_exports/pepperstone/Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-04-26_87e73.csv](data/tv_exports/pepperstone/Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-04-26_87e73.csv) | 418 lines (1 header + 417 data rows = 209 entries + 209 exits, all `Entry long`/`Exit long`) |
| [docs/adr/2026-04-23-guardian-risk-relock-0.34.md](docs/adr/2026-04-23-guardian-risk-relock-0.34.md) | 22 (**source of the stale "201 trades"** — pre-04-26 v5.5 CSV used in the 0.30→0.50% headroom sweep, three days before the current 04-26 export was committed) |
| [docs/briefs/striker_nas100_q_nas_3_mc_addition.md](docs/briefs/striker_nas100_q_nas_3_mc_addition.md) | 41 (independent confirmation: Guardian n=209 in the 4-strategy MC addition brief, 2026-05-05) |
| [archive/docs/methodology/archive/gate_audits/2026-05-03_gbpusd_m15_h_lorb_phaseA_abort.md](archive/docs/methodology/archive/gate_audits/2026-05-03_gbpusd_m15_h_lorb_phaseA_abort.md) | 44 (independent DOW breakdown: Mon 57 + Tue 64 + Thu 88 = 209) |

## Counts table A–G

| Slot | Description | Result | Source |
|---|---|---|---|
| **A** | portfolio_mc.py expected Guardian count | **No hardcoded constant.** Only `assert_min_rows ≥ 100` floor + `assert_window ≥ 4yr*365 days` (tolerance 60d). Canonical n_trades pin lives in [tests/test_tv_export_loader.py:23](tests/test_tv_export_loader.py:23) → **209** | portfolio_mc.py:107-124, tests/test_tv_export_loader.py:23 |
| **B** | Guardian CSV raw rows | **418** (incl. header) → **417 data rows** | `wc -l` on Guardian CSV |
| **C** | Guardian CSV post-filter rows (= n_trades, exit-only filter from `load_trades`) | **209** (209 `Exit long` rows; paired with 209 `Entry long`) | pandas read of Guardian CSV; matches `Type.value_counts()` exactly |
| **D** | NAS100 B_15 CSV rows | **N/A — no `*B_15*` file exists in the repo** (Glob `**/*B_15*` returns 0 results; no `analysis/striker_nas100/` Phase 4B artefact on disk; only `q_nas_1_pyramid_hypothesis.py` present). The "B_15 = 209" recollection cannot be verified from local files. | `Glob **/*B_15*`; `Glob analysis/striker_nas100/**` |
| **E** | Striker DJ30 v4.5 expected vs actual | tests pin **224**; CSV has **224** entries + **224** exits (all `*long`) | tests/test_tv_export_loader.py:27, pandas read |
| **F** | Aegis expected vs actual | tests pin **123**; CSV has **123** entries + **123** exits | tests/test_tv_export_loader.py:31, pandas read |
| **G** | NAS100 v1 expected vs actual | tests pin **200** (166 base + 34 pyramid); CSV has **200** entries + **200** exits | tests/test_tv_export_loader.py:35, pandas read |

All four match their canonical pins. Date ranges: Guardian 2022-01-11 →
2026-04-20 (1560d), DJ30 2022-01-04 → 2026-04-17 (1564d), Aegis 2022-01-12
→ 2026-04-15 (1554d), NAS100 2022-01-11 → 2026-04-14 (1554d). All clear
the 4×365−60 = 1400d MVD window floor.

## Hypotheses (ranked by likelihood, with falsifiable tests)

### H5 (NEW, primary): "201 canonical" baseline is stale; current canonical is 209

**Mechanism.** The 2026-04-23 Guardian risk-relock ADR (line 22) ran the
headroom sweep against an earlier v5.5 Pepperstone CSV containing 201
trades. Three days later (2026-04-26) a re-fetch produced the current
canonical CSV (`...87e73.csv`) with 209 trades — 8 additional v5.5
signals from the intervening window. The locked production code never
hardcoded the count; the canonical pin was added to
`tests/test_tv_export_loader.py` on 2026-05-05 (alongside the NAS100 v1
add) at **209**, not 201.

**Falsifiable test.** Read `tests/test_tv_export_loader.py:23` — if it
declares 209 (it does), 209 is canonical and any reconcile expecting 201
is using a stale baseline. ✅ **Confirmed canonical = 209.**

**Why this fired:** the per-strategy Pepperstone baseline metrics are not
pinned in CLAUDE.md — only the portfolio-combined MC headline is. This
matches the existing memory `feedback_per_strategy_pepperstone_baseline_uncommitted.md`
hygiene gap exactly. The stale "201" propagated through investigator
memory because no headline number contradicted it until the test was
added on 05-05.

### H1: CSV path mis-routes Guardian to a NAS100 file (label≠content)

**Falsifiable test.** Open the CSV resolved at `portfolio_mc.py:71`,
inspect `Type` and PnL pattern; run `assert_tv_export` against
`expected_strategy="Guardian"`, `expected_symbol="XAUUSD"`,
`expected_version="v5.5"`, `expected_broker="PEPPERSTONE"`.
- Filename parses to `Guardian / Gold / v5.5 / PEPPERSTONE / XAUUSD /
  2026-04-26 / 87e73`. ✅ identity gate passes.
- `Type` column is 100% `Entry long` / `Exit long` (Guardian's
  long-only XAUUSD trend rider).
- First trade Price USD ≈ 1806 (gold spot 2022-01-11), last ≈ 4823
  (gold 2026-04-20). Consistent with XAUUSD, not NAS100 (which would
  read in the 14K–22K range over the same window).

**Verdict: REFUTED.** Content matches label.

### H2: portfolio_mc.py expected count not updated post-05-05 locks

**Falsifiable test.** Grep portfolio_mc.py for any hardcoded n_trades
constant for Guardian.
- `portfolio_mc.py` carries no `EXPECTED_TRADES_*` constant or assert
  on n_trades. The only cardinality assertions are `assert_min_rows
  ≥ 100` (line 110) and `assert_window ≥ 4yr` (line 117).
- The canonical n_trades pin lives in `tests/test_tv_export_loader.py`,
  was added 2026-05-05 alongside the NAS100 v1 add, and reads **209**
  for Guardian — already current.

**Verdict: REFUTED for production code.** The hypothesis is incorrectly
shaped — there is nothing in `portfolio_mc.py` to update. The canonical
pin is in the loader test and is already correct.

### H3: filter / date-range boundary changed the effective N

**Falsifiable test.** `load_trades` (portfolio_mc.py:102-124) filters
only `Type.startswith("Exit")`; no date trim, no PnL filter, no signal
filter. Therefore n_trades = number of exit rows. CSV has 209 exit rows;
`load_trades` returns 209.

**Verdict: REFUTED.** No filter discrepancy.

### H4: stale CSV from a pre-v5.5 Guardian variant

**Falsifiable test.** `git log` for the Guardian Pepperstone CSV path;
inspect filename version field; check for any other `Guardian_Gold_v*`
files on disk.
- Glob returns exactly one Pepperstone Guardian CSV, declaring v5.5.
- `assert_tv_export` enforces version match at load time.
- Two-line `git log --oneline --all -- 'data/tv_exports/pepperstone/Guardian*'`
  output (`be7d4d1`, `05297c2`) confirms a single tracked file, no
  v5.4 leftovers.

**Verdict: REFUTED.** No stale variant on disk.

### Coincidence note re: NAS100 B_15

The user-supplied premise that 209 "exactly matches Striker NAS100 B_15
(Phase 4B, 2026-05-04)" cannot be verified locally — no `*B_15*` artefact
exists in the repo (`Glob **/*B_15*` → 0 hits). The current NAS100 v1
canonical is **200** trades, not 209. If a B_15 result of 209 trades
exists in an external note, it is numerically coincidental with Guardian's
209 and not evidence of cross-contamination.

## Recommended next step (gated, NOT executed)

1. **Update investigator's working "canonical" baseline from 201 → 209.**
   The locked Pepperstone Guardian panel as of 2026-04-26 has 209 trades;
   this is pinned by `tests/test_tv_export_loader.py:23`. The reconcile
   run that reported 209 is **correct**.

2. **(Optional, gated on Joshua's call)** Pin per-strategy Pepperstone
   baseline counts in CLAUDE.md alongside the portfolio MC headline, to
   close the hygiene gap that allowed "201" to persist as working memory
   for ~12 days after the canonical re-fetch. This is the action implied
   by `feedback_per_strategy_pepperstone_baseline_uncommitted.md`.

3. **(Optional, gated)** Append a one-line note to
   `docs/adr/2026-04-23-guardian-risk-relock-0.34.md` clarifying that
   the "201 trades" referenced in the headroom-sweep section refers to
   the pre-04-26 v5.5 export (now superseded by the 04-26 canonical with
   209 trades). This prevents the same stale-baseline trip in future
   re-reads of the ADR.

**No code or CSV edits in this run** (per the FORBIDDEN list in the brief).

---

## Postscript (same day, post-resolution)

The reconcile's verdict above ("209 is canonical") was **inverted** by user
intervention shortly after this brief was written. Joshua supplied a fresh
Pepperstone export
`Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-05_33781.csv` containing
**201 trades** over the same 2022-01-11 → 2026-04-20 window, with first/last
trade timestamps and prices matching the 87e73 export to within ~$0.01
rounding. The 04-26 87e73 export was itself anomalous (contained 8 extra
v5.5 signals over the same window — probable Pine recompile / dirty cache
artefact during the 04-26 fetch).

**Resolution actions taken:**

1. Replaced production CSV: 87e73 → 33781 in
   [data/tv_exports/pepperstone/](data/tv_exports/pepperstone/), with old
   file deleted.
2. Updated [portfolio_mc.py:71](portfolio_mc.py:71) to point at the new
   filename.
3. Updated [tests/test_tv_export_loader.py:22-23](tests/test_tv_export_loader.py:22)
   pin: filename + n_trades 209 → 201. `pytest` re-run confirms loader test
   passes against the new CSV (4/4).
4. Updated [data/tv_exports/pepperstone/SHA256SUMS](data/tv_exports/pepperstone/SHA256SUMS)
   with the new file's hash.
5. Updated two non-MC analysis scripts that referenced the old filename:
   [archive/analysis/gbpusd_lon/correlation.py:44](archive/analysis/gbpusd_lon/correlation.py:44),
   [archive/analysis/eurusd_lnyo/correlation.py:45](archive/analysis/eurusd_lnyo/correlation.py:45).
6. NAS100 B_15 deletion: nothing to do — no `*B_15*` artefact exists in the
   repo (verified via `Glob **/*B_15*`).

**Known DOWNSTREAM impact NOT yet addressed (gated, requires re-run):**

- [tests/test_mc_anchors.py](tests/test_mc_anchors.py) pins
  `pass_rate=0.9813 / bust_rate=0.0022 / p99_dd=0.0449` against the
  209-trade Guardian panel. With 201 trades, Guardian's `implied_1r`
  (median loss) and per-day P&L distribution shift, so the bootstrap
  result will move. Tests will FAIL on next run until re-anchored.
- The CLAUDE.md "2026-05-05 lock MC anchor" headline (`98.13% pass / 0.22%
  bust ... 4.49% p99 DD` and bust attribution `DJ30 49.2% / G 20.0% /
  A 20.0% / NAS 10.8%`) is now stale.
- [docs/briefs/striker_nas100_q_nas_3_mc_addition.md:41](docs/briefs/striker_nas100_q_nas_3_mc_addition.md:41)
  carries Guardian n=209 in the addition-decision table; the brief's MC
  attribution figures derive from that panel.

**Recommended next step (gated, NOT executed):** re-run
`python portfolio_mc.py` to produce the new 4-strategy anchor on the 201-
trade Guardian panel. If both lock gates (bust < 1%, p99 DD < 5%) still
clear, update the test pin + CLAUDE.md headline + the NAS addition brief
in one commit. If either gate breaches, the lock decision needs
re-evaluation per the 2026-04-17 ADR (do not bypass by tweaking constants).

**Out-of-scope finding (separate from this reconcile):** the two updated
analysis scripts also still reference a deleted Striker CSV
(`Striker_DJ30_v4.4_PEPPERSTONE_US30_2026-04-26_3eea0.csv`). This was
already broken before today's swap and is not addressed here.

**Methodology lesson logged:** the original verdict ("209 is canonical")
correctly reported what the on-disk artefact + test pin claimed, but those
artefacts can themselves be wrong. When a user-supplied baseline disagrees
with on-disk + test pins, treat the on-disk artefact as a candidate
for re-fetch, not just the user's memory as a candidate for correction.
Saved to user memory as `feedback_on_disk_artefact_can_be_wrong.md`.

---

## Re-anchor results (2026-05-05 PM)

`python portfolio_mc.py --panel pepperstone` re-run on the corrected 201-
trade Guardian panel (joint with DJ30 v4.5 + Aegis + NAS100 v1):

| Metric | Old (209 G) | New (201 G) | Δ |
|---|---|---|---|
| Pass | 98.13% | **97.88%** | −0.25 pp |
| Bust (total) | 0.22% | 0.22% | 0 |
| Bust daily / static | 0.00 / 0.22 | 0.00 / 0.22 | 0 / 0 |
| Timeout | 1.65% | **1.90%** | +0.25 pp |
| Median days to pass | 23 | 23 | 0 |
| p50 / p95 / p99 DD | — / — / 4.49% | 1.34 / 3.52 / **4.55%** | +0.06 pp p99 |

**Lock gates:** bust 0.22% < 1% ✓, p99 DD 4.55% < 5% ✓. Both clear with
comfortable margin — lock decision unchanged.

**Bust attribution shift:**

| Strategy | Old share | New share | Δ |
|---|---|---|---|
| Striker DJ30 | 49.2% | **40.9%** | −8.3 pp |
| Guardian | 20.0% | **25.8%** | +5.8 pp |
| Aegis | 20.0% | **22.7%** | +2.7 pp |
| NAS100 | 10.8% | **10.6%** | −0.2 pp |

Guardian moves up because its `implied_1r` (median loss) on the 201-trade
panel is $1,196.68 (vs $1,175.10 on the 209-trade panel) — the 8 phantom
trades had below-median losses that pulled the median down; removing them
raises the median, which lowers `scale`, which lets larger raw P&L flow
through into bust paths. NAS still ranks lowest, so the diversification
thesis holds.

**Independent corroboration:** dashboard total trade count (748) now
matches MC (201 + 224 + 123 + 200 = **748**) exactly. The original brief
flagged a 5-trade gap (756 MC vs 748 dashboard) — now closed.

**Updates landed in this session:**
1. `tests/test_mc_anchors.py` — pinned 0.9788 / 0.0022 / 0.0455 (abs=1e-4).
2. `CLAUDE.md` — "2026-05-05 lock MC anchor" block + Protection section MC
   line both updated to new headline + attribution.
3. `docs/briefs/striker_nas100_q_nas_3_mc_addition.md` — headline table,
   per-strategy scale row (Guardian), bust attribution table, test pin
   section, and dashboard-residual section all updated.
4. `memory/project_4strategy_mc_anchor_2026_05_05.md` + `MEMORY.md` index
   updated; STALE flag removed.

