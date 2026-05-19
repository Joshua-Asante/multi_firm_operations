# CC-Spawn: DJ30 swept-parameter decomposition into 3 single-axis sweep CSVs

**Authored:** 2026-05-17
**Author:** Joshua
**Repo / branch:** multi_firm_operations / claude/gifted-ritchie-9da9da (or a fresh branch off origin/main — see §1)
**Estimated effort:** medium (Pine edits + 4 backtest exports + 4 reconciles + summary table)

---

## §0 — Rule 0 reads (DO THESE FIRST, BEFORE PROPOSING ANY CHANGES)

Before authoring any Pine edits or running any backtests, read and report back the contents of:

1. `strategies/striker/Striker_DJ30_v4.5.pine` (or whichever path holds the production v4.5 source; check `strategies/MANIFEST.sha256` for the canonical path and hash) — needed because §2 requires three single-axis Pine variants. Report: (a) the Pine source path, (b) the manifest hash, (c) the current values of `risk_pct`, `pyramid_pct` (or equivalent — the parameter that maps to "pyramid 500%"), and `day_soft_stop_pct` (or equivalent — the parameter that maps to "−2.00% daily soft-stop"). Cite exact line numbers for each.
2. `references/baselines.md` in the trade-csv-reconcile skill at `C:/Users/joshu/.claude/skills/trade-csv-reconcile/references/baselines.md` — needed because §2 reconciles each variant against the same-day locked control. Report: the Striker DJ30 v4.5 Pepperstone baseline block (panel, N, PF, WR, Net, DD, 1R), and confirm DJ30's risk_pct = 0.75% with pyramid 500% per the 2026-05-14 allocation refresh.
3. `docs/adr/2026-05-14-allocation-refresh.md` (on `origin/main`) — needed because the decomposition outputs feed back into a Pre-Q gate (`Q-DJ30-decomp`) that supersedes a portion of this ADR if any single axis is shown to be load-bearing alone. Report: the §Decision table row for Striker DJ30 v4.5, the §Override grounds, and the §Falsifier list. Confirm allocation refresh is still ACCEPTED status.
4. `docs/methodology/regime_robustness_gate.md` — needed because the eventual Pre-Q closure runs the same gate. Report: criterion 5 (regime-robustness) statement verbatim.
5. The same-day locked-control DJ30 CSV: `C:/Users/joshu/multi_firm_operations/.claude/worktrees/admiring-saha-147572/data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-17_c0b35.csv` — needed for the apples-to-apples reconcile against each sweep variant. Report: panel window, trade count, PF, Net, DD via `python C:/Users/joshu/.claude/skills/trade-csv-reconcile/scripts/reconcile.py <path>`. (If this exact file is missing on the executor's filesystem, halt and ask Joshua to confirm the canonical control CSV path; do NOT substitute a different vintage.)
6. The joint swept variant CSV (the one already produced): `C:/Users/joshu/Downloads/updated_Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-17_1e83b.csv` — needed as the joint-effect reference. Report: panel window, N, PF, Net, DD via reconcile.py.

After reading, report back to Joshua (in the spawning conversation) the relevant sections of each file. Do NOT proceed to §2 plan execution until §0 is reported and Joshua confirms the readings match his understanding. **§0 is the authoritative read, not a sanity check on this brief.** Where this brief and §0 conflict, §0 wins; report the divergence to Joshua before §2 execution.

If any file does not exist or cannot be read, halt and report the failure mode — do not work around it.

---

## §1 — Task statement

Produce three single-axis Pine sweep CSVs for Striker DJ30 v4.5 — each holding two axes at the 2026-05-14 locked values and varying only one to the candidate value — and reconcile each against the same-day locked-control export (`_c0b35`) so the marginal effect of each axis can be measured independently before joining them into a Pre-Q gate.

The three axes (per Joshua's joint sweep `_1e83b`):

| Axis | Locked value | Candidate value |
|---|---:|---:|
| A. `risk_pct` | 0.75% | 0.70% |
| B. `pyramid_pct` | 500% | 750% |
| C. `day_soft_stop_pct` | −2.00% | −1.15% |

**Out of scope (explicitly):**
- Editing `firm_rules.py`, `dd_protection.py`, `portfolio_mc.py`, `references/baselines.md`, `CLAUDE.md`, or any allocation/risk constant. This handoff produces CSVs and a reconcile table only; no production code or doc changes.
- Editing the joint-swept CSV `_1e83b` or the locked-control `_c0b35` — both are inputs.
- Running `portfolio_mc.py` against any new config. That's gated to the Pre-Q (`Q-DJ30-decomp`) that consumes this handoff's output.
- Modifying Pine for Guardian, Aegis, or NAS100. Single-strategy scope only.
- Authoring the eventual Pre-Q brief or its ADR. This handoff produces the data the Pre-Q needs; brief authoring is Joshua's parent session.
- Committing the new CSVs to `data/tv_exports/pepperstone/` or updating `SHA256SUMS`. Provenance lands only if the Pre-Q resolves; until then, the CSVs are staging artifacts.

---

## §2 — Step-by-step plan with verification gates

### Step 2.1 — Save Pine baseline before any edits
**Action:** Save a copy of the unmodified `Striker_DJ30_v4.5.pine` (per §0 step 1's reported path) to a backup at `strategies/striker/.archive/Striker_DJ30_v4.5_pre_decomp_2026-05-17.pine`. Verify the SHA256 of the backup matches the source.
**Verification:**
```
sha256sum strategies/striker/Striker_DJ30_v4.5.pine
sha256sum strategies/striker/.archive/Striker_DJ30_v4.5_pre_decomp_2026-05-17.pine
# Expected: identical SHA256
```

### Step 2.2 — Produce Pine variant A (risk-only)
**Action:** Edit the Pine to change `risk_pct = 0.75` → `0.70`. Hold `pyramid_pct = 500` and `day_soft_stop_pct = -2.00` at locked values. Save as `strategies/striker/.sweep/Striker_DJ30_v4.5_decomp_A_risk070.pine`. Report the unified diff vs baseline (should be 1-line change, exact line cited).
**Verification:**
```
diff strategies/striker/Striker_DJ30_v4.5.pine strategies/striker/.sweep/Striker_DJ30_v4.5_decomp_A_risk070.pine
# Expected: exactly one hunk, +risk_pct = 0.70 / -risk_pct = 0.75 (or equivalent identifier)
grep -c "pyramid" strategies/striker/.sweep/Striker_DJ30_v4.5_decomp_A_risk070.pine
# Expected: matches the baseline grep count for pyramid (no incidental edits)
```

### Step 2.3 — Backtest variant A and export CSV
**Action:** Run the variant A Pine in TradingView against `PEPPERSTONE:US30` on the same window as `_c0b35` (2022-01-04 → 2026-03-31, 15m). Export the trade CSV to `data/tv_exports/pepperstone/.sweep/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-17_decompA_risk070.csv`. **Do NOT commit; this is a staging file under `.sweep/`.**
**Verification:**
```
python C:/Users/joshu/.claude/skills/trade-csv-reconcile/scripts/reconcile.py \
  data/tv_exports/pepperstone/.sweep/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-17_decompA_risk070.csv
# Expected: feed=pepperstone, strategy=striker_dj30 auto-detect succeeds; N within ±5 of c0b35's 210
```

### Step 2.4 — Produce Pine variant B (pyramid-only)
**Action:** Edit the Pine from baseline (re-derive from the .archive backup, do NOT stack on variant A) to change `pyramid_pct = 500` → `750`. Hold `risk_pct = 0.75` and `day_soft_stop_pct = -2.00`. Save as `strategies/striker/.sweep/Striker_DJ30_v4.5_decomp_B_pyr750.pine`. Report unified diff.
**Verification:**
```
diff strategies/striker/.archive/Striker_DJ30_v4.5_pre_decomp_2026-05-17.pine strategies/striker/.sweep/Striker_DJ30_v4.5_decomp_B_pyr750.pine
# Expected: exactly one hunk, +pyramid_pct = 750 / -pyramid_pct = 500
```

### Step 2.5 — Backtest variant B and export CSV
**Action:** As Step 2.3, exporting to `..._decompB_pyr750.csv`. Same panel window.
**Verification:**
```
python C:/Users/joshu/.claude/skills/trade-csv-reconcile/scripts/reconcile.py \
  data/tv_exports/pepperstone/.sweep/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-17_decompB_pyr750.csv
# Expected: clean parse; N likely higher than c0b35 (more pyramid adds counted as separate trades, see _1e83b which had +6)
```

### Step 2.6 — Produce Pine variant C (day-soft-stop only)
**Action:** Edit the Pine from baseline to change `day_soft_stop_pct = -2.00` → `-1.15`. Hold `risk_pct = 0.75` and `pyramid_pct = 500`. Save as `strategies/striker/.sweep/Striker_DJ30_v4.5_decomp_C_dss115.pine`. Report unified diff.
**Verification:**
```
diff strategies/striker/.archive/Striker_DJ30_v4.5_pre_decomp_2026-05-17.pine strategies/striker/.sweep/Striker_DJ30_v4.5_decomp_C_dss115.pine
# Expected: exactly one hunk, +day_soft_stop_pct = -1.15 / -day_soft_stop_pct = -2.00
```

### Step 2.7 — Backtest variant C and export CSV
**Action:** As Step 2.3, exporting to `..._decompC_dss115.csv`. Same panel window.
**Verification:**
```
python C:/Users/joshu/.claude/skills/trade-csv-reconcile/scripts/reconcile.py \
  data/tv_exports/pepperstone/.sweep/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-17_decompC_dss115.csv
# Expected: clean parse; expect more "DD Limit" exits than c0b35 (tighter day-stop fires more often)
```

### Step 2.8 — Build the marginal-effect reconciliation table
**Action:** Author a Python script (or use the reconcile.py JSON output) that computes, for each of {c0b35 control, decompA, decompB, decompC, 1e83b joint}, the following on **both compounded and static-equity bases**:
- N
- PF
- WR %
- Net (USD)
- max DD %
- count of exits by Signal type (Exit Long, DD Limit, Max Hold, Exit Long Add)

Output to `docs/briefs/Q-DJ30-decomp_reconcile_table.md` as a markdown table plus a summary section:
- Marginal effect of axis A alone: Δ vs control (PF, Net-static, DD-static)
- Marginal effect of axis B alone: Δ vs control
- Marginal effect of axis C alone: Δ vs control
- Joint effect (1e83b): Δ vs control
- Additivity check: does A+B+C marginal sum ≈ joint? Or are there cross-axis interactions?

**Static-equity rebase is mandatory** (per memory `feedback_static_equity_default_for_param_compare`): for each trade, `static_pnl = Net P&L % / 100 × $200,000`. Sum for Net-static; reconstruct equity curve from these for DD-static.

**Verification:**
```
ls docs/briefs/Q-DJ30-decomp_reconcile_table.md
# Expected: file exists
grep -E "decomp_A|decomp_B|decomp_C|1e83b|c0b35" docs/briefs/Q-DJ30-decomp_reconcile_table.md | wc -l
# Expected: >=5 (table covers all five configs)
grep -i "static-equity\|static equity" docs/briefs/Q-DJ30-decomp_reconcile_table.md
# Expected: >=1 (static-equity rebase explicitly applied)
```

### Step 2.9 — Flag any pyramid-share or DD-Limit anomalies
**Action:** For each of the 4 swept CSVs (decompA/B/C + 1e83b), compute and report:
- Pyramid P&L share (per the corrected loader logic: trades whose Signal contains "Add" / "Pyr"; sum that subset's Net P&L / total Net P&L)
- DD-Limit exit count and dollar contribution
- Max Hold exit count and dollar contribution

Cross-reference: per memory, pyramid share <50% is a red flag; per locked baseline DJ30 expects ~94%. If decompB (pyr 750%) pushes pyramid share above the locked level OR if decompC's DD-Limit count exceeds 30 exits (signal of over-firing of the day-stop), flag prominently in the §6 report.

**Verification:**
```
grep -iE "pyramid share|DD Limit count|Max Hold count" docs/briefs/Q-DJ30-decomp_reconcile_table.md | wc -l
# Expected: >=3 lines (all three metrics surfaced per variant)
```

---

## §3 — Forbidden moves

- **Do NOT modify `firm_rules.py`, `dd_protection.py`, `portfolio_mc.py`, `references/baselines.md`, `CLAUDE.md`, or any allocation/risk constant.** These are governed by the 2026-05-14 ADR and any subsequent Pre-Q. This handoff produces analytical artifacts only.
- **Do NOT commit the new Pine `.sweep/` files or the new staging CSVs to the canonical tree.** Provenance lands only after a Pre-Q resolves. Leaving them in `.sweep/` keeps them clearly staging.
- **Do NOT update `data/tv_exports/pepperstone/SHA256SUMS`** — the canonical-tracking gate is gated to lock decisions, not sweeps. The `.sweep/` subdirectory should be gitignored or excluded from `check_data_manifests.py` per its existing rules.
- **Do NOT skip the static-equity rebase in the reconciliation table** — compounded-only reads will mislead the Pre-Q. Memory `feedback_static_equity_default_for_param_compare` is binding.
- **Do NOT stack edits — each variant must derive from the .archive backup, not from the previous variant.** Coupled edits across variants destroy the single-axis attribution this handoff exists to produce.
- **Do NOT add tests or refactor adjacent Pine code** — even if it looks improvable. Out of scope.
- **Do NOT commit or push.** Joshua reviews the diff and decides commit scope.
- **Do NOT proceed past §0 readings** until Joshua confirms them in the spawning conversation. Per the brief-authoring §0 sub-rule "architecture truth before edit prescription," the executor reports the file state and proposed edit shape before §2 execution.

The check for forbidden-move adherence is the diff at task end: if the diff touches anything outside §2's enumerated targets (`.archive/`, `.sweep/`, `docs/briefs/Q-DJ30-decomp_reconcile_table.md`), the move was forbidden.

---

## §4 — Expected output

When this task completes, the following must be true:

- **Files created:**
  - `strategies/striker/.archive/Striker_DJ30_v4.5_pre_decomp_2026-05-17.pine` (backup)
  - `strategies/striker/.sweep/Striker_DJ30_v4.5_decomp_A_risk070.pine`
  - `strategies/striker/.sweep/Striker_DJ30_v4.5_decomp_B_pyr750.pine`
  - `strategies/striker/.sweep/Striker_DJ30_v4.5_decomp_C_dss115.pine`
  - `data/tv_exports/pepperstone/.sweep/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-17_decompA_risk070.csv`
  - `data/tv_exports/pepperstone/.sweep/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-17_decompB_pyr750.csv`
  - `data/tv_exports/pepperstone/.sweep/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-17_decompC_dss115.csv`
  - `docs/briefs/Q-DJ30-decomp_reconcile_table.md`
- **Files modified:** none (canonical Pine, CSVs, and config untouched)
- **Files deleted:** none
- **Final verification commands to run before exit:**
  ```
  ls strategies/striker/.sweep/*.pine | wc -l           # Expected: 3
  ls data/tv_exports/pepperstone/.sweep/*.csv | wc -l   # Expected: 3
  test -f docs/briefs/Q-DJ30-decomp_reconcile_table.md  # Expected: exit 0
  git diff --name-only HEAD                              # Expected: empty (no modifications, only untracked)
  git status -s | grep -v '^??'                          # Expected: empty (no staged or modified-tracked files)
  ```
- **Expected diff shape:** zero modifications to tracked files; new untracked files only under `strategies/striker/.archive/`, `strategies/striker/.sweep/`, `data/tv_exports/pepperstone/.sweep/`, and `docs/briefs/Q-DJ30-decomp_reconcile_table.md`.

---

## §5 — Done criteria

This task is complete when ALL of:

- [ ] §0 readings reported to Joshua AND Joshua confirmed before §2 execution
- [ ] Every Step 2.x verification passed
- [ ] Final §4 verification commands all pass
- [ ] Diff shape matches §4 expectation (no surprise modifications to tracked files)
- [ ] No forbidden move from §3 leaked into the diff
- [ ] §6 report summarizes the marginal vs joint effect with explicit additivity check
- [ ] Pyramid-share and DD-Limit/Max-Hold counts reported per variant per Step 2.9
- [ ] Summary of what was done reported back to Joshua (in the spawning conversation, not just a commit message)

If any criterion fails, halt and report — do not declare done.

---

## §6 — Reporting format

When the task is complete (or halted), report back in this format:

```
=== CC-Spawn: DJ30 swept-parameter decomposition ===
Status: COMPLETE | HALTED-AT-STEP-N | FAILED

§0 readings (cite verbatim):
  1. Pine source path: <path>, hash: <sha>, risk_pct=<X> pyramid=<Y> day_soft_stop=<Z> at lines <a/b/c>
  2. baselines.md DJ30 block: <verbatim>
  3. ADR §Decision row for DJ30: <verbatim>
  4. Regime-robustness gate criterion 5: <verbatim>
  5. c0b35 reconcile: N=<>, PF=<>, Net=<>, DD=<>
  6. 1e83b reconcile: N=<>, PF=<>, Net=<>, DD=<>

Step results:
  2.1: PASS | FAIL
  2.2: PASS | FAIL  (Pine diff: <hunk>)
  2.3: PASS | FAIL  (decompA reconcile: N=<>, PF=<>, Net=<>, DD=<>)
  2.4: PASS | FAIL  (Pine diff: <hunk>)
  2.5: PASS | FAIL  (decompB reconcile: N=<>, PF=<>, Net=<>, DD=<>)
  2.6: PASS | FAIL  (Pine diff: <hunk>)
  2.7: PASS | FAIL  (decompC reconcile: N=<>, PF=<>, Net=<>, DD=<>)
  2.8: PASS | FAIL  (reconcile table written, static-equity applied)
  2.9: PASS | FAIL  (pyramid/DD-Limit/Max-Hold flags surfaced)

Marginal-effect summary (static-equity, Δ vs c0b35 control):
  Axis A (risk 0.75 → 0.70):     PF Δ=<>%   Net Δ=$<>   DD Δ=<>pp
  Axis B (pyramid 500 → 750):    PF Δ=<>%   Net Δ=$<>   DD Δ=<>pp
  Axis C (day-stop -2.00 → -1.15): PF Δ=<>%   Net Δ=$<>   DD Δ=<>pp
  Joint (1e83b):                 PF Δ=<>%   Net Δ=$<>   DD Δ=<>pp
  Additivity check: <A+B+C marginal sum> vs <joint>; cross-axis interaction = <delta>

Files created:
  - strategies/striker/.archive/... (+0 -0 baseline backup)
  - strategies/striker/.sweep/decomp_{A,B,C}.pine (3 single-line diffs vs baseline)
  - data/tv_exports/pepperstone/.sweep/*decomp{A,B,C}*.csv (3 CSVs)
  - docs/briefs/Q-DJ30-decomp_reconcile_table.md (reconcile table + summary)

Final verification:
  $ ls strategies/striker/.sweep/*.pine | wc -l: PASS (3)
  $ ls data/tv_exports/pepperstone/.sweep/*.csv | wc -l: PASS (3)
  $ git diff --name-only HEAD: PASS (empty)
  $ git status -s | grep -v '^??': PASS (empty)

Notes:
  [Anything Joshua needs to know — Pine parameter naming surprises, panel-window misalignment, pyramid-share anomalies, DD-Limit firing rates, cross-axis interaction sign/magnitude, anything that warrants methodology-lesson capture]
```

---

## §7 — Notes for the user (parent session)

When CC reports back, the parent session reviews:
- Was every §2 verification gate respected? (Skipped verifications are a discipline failure.)
- Did the diff match the §4 shape — strictly no tracked-file modifications? (Surprise modifications are forbidden-move leaks; especially watch for canonical Pine, `SHA256SUMS`, or config drift.)
- Does the additivity check (marginal sum vs joint) reveal cross-axis interactions? If `|interaction| > 25%` on any of PF/Net/DD, the joint sweep cannot be locked from the marginal evidence alone — the Pre-Q must include the joint configuration as its own arm.
- Did any pyramid-share or DD-Limit anomaly fire from Step 2.9? Flag for the Pre-Q's §5 forbidden moves (e.g., "do not lock variant B if pyramid share exceeds 96% — suggests pyramid mechanism is degenerate at 750%").
- Did anything in §6 Notes warrant a methodology lesson capture? (Pine parameter naming drift, panel-window subtleties, multi-axis interaction patterns are candidates for the lessons registry.)
