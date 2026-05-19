# Q-CORR-2 pre-condition A — portfolio_mc joint-day sampling report

Date: 2026-05-17
Spawn: parent-dispatched subagent (Walk-away CC handoff per `2026-05-16-cc-handoff-q-corr-2-precondition-a.md`)
Parent: 2026-05-16-q-corr-2-pyramid-conditional-correlation.md

---

## §1 Files read (with git anchors)

Worktree root: `C:\Users\joshu\multi_firm_operations\.claude\worktrees\amazing-northcutt-37cce1`
Worktree HEAD: `317e43a` (branch `claude/amazing-northcutt-37cce1`, not on `origin/main`).

| Path | Last commit on this branch | Notes |
|---|---|---|
| `portfolio_mc.py` (612 lines, full) | `54d2285` (PR #63, Q-MCFP-1, 2026-05-10) | Sole MC simulator module — flat `.py`, not a package. |
| `dd_protection.py` (lines 1–50) | `6c7fa54` (PR #53, ULP-rounding fix, 2026-05-10) | DD_TRIGGER=0.015, DD_SCALE=0.40 (C2). Read for constants/coupling check — no correlation/copula state. |
| `lib/correlation.py` (lines 1–40) | `31110f5` (PR #75, 2026-05-13) | Q-CORR-1.x forensic helper (`pearson_daily_pnl`). Verified NOT imported by `portfolio_mc.py` — grep returned only `from lib.mvd import …` on L35. |

§0 candidates evaluated and dispositioned:

- **`portfolio_mc/` module root** → does not exist; `portfolio_mc.py` is a single top-level module (confirmed by `Glob portfolio_mc*` → 3 hits, only the `.py` is code). Entry point is `main()` at L577.
- **Joint-sampling function** → identified at L223–258 (`run_seed`); core sampling line at L242–243 (block-index draw + concatenation). Per-day execution in `_simulate_path` at L187–220.
- **Config / constants module naming correlation, covariance, "independence", or "iid" flags** → none found. Repo-wide grep on `correlation|covariance|multivariate|copula` returned 38 files; the only non-archive hit relevant to MC was `lib/correlation.py`, which is Q-CORR forensic tooling and not in the MC import graph. `portfolio_mc.py` contains zero hits for those four tokens.
- **STATE.md** → does not exist in this repo (parent's pre-flagged surfacing #2 confirmed by `Glob STATE.md` → no files found). Notice §7 audit hook "STATE.md open-questions row expected" cannot be honored as-written. Flagged in §7 below; not in spawn scope to resolve.

Worktree-vs-anchor reconciliation (parent pre-flag #1 confirmed, with one correction):

- Parent stated worktree HEAD is `54d2285`. Actual worktree HEAD is `317e43a` (the docs-only commit that filed the Notice + handoff). `54d2285` is the last commit *touching `portfolio_mc.py`* on this branch — distinct claim.
- The 99.88/0.12/4.21 anchor cited in the parent Notice §1 was produced by commit `43aa187` (PR #85, FXIFY-correct timeout semantic, merged 2026-05-16 to `origin/main`). `43aa187` is **not in this worktree's ancestry**: `git merge-base 317e43a 43aa187` returns `670625d`, meaning this branch diverged before PR #85 landed.
- Therefore the `portfolio_mc.py` read in this report is the **pre-PR-#85 version**. I separately read PR #85's diff to `portfolio_mc.py` (88 lines changed) and verified the joint-sampling code (`build_week_blocks`, the `run_seed` block-index draw and `np.concatenate`) is untouched by PR #85. Parent's claim "joint sampling unchanged across PR #85" is confirmed. The PR #85 changes are confined to inactivity tracking + outcome-label additions in `_simulate_path`, the outcome-dict shape in `run_seed`, the reporting path in `compute_default_config`/`report_default`, and the sensitivity-grid row formatter. None of these change how cross-strategy joint days are sampled.

---

## §2 Assumption branch (A1 / A2 / A3 / OTHER)

**Branch: A1 — empirical joint resample via non-overlapping Monday-anchored 5-day block bootstrap on a union-aligned daily panel.**

Three observations carry the classification:

1. **Joint panel is empirical and date-aligned** (`build_daily_panel`, L151–172). Each strategy's exit-date-grouped P&L series is concatenated wide with `pd.concat(..., axis=1, sort=True).fillna(0.0)`, then reindexed to `pd.bdate_range(panel.index.min(), panel.index.max())`. The resulting panel is shape `(n_bdays, n_strats)` with each row corresponding to **one calendar business day** and each column to one strategy. Non-trade days are zero-filled (joint absence, not joint independence).
2. **Resample preserves intra-day cross-strategy structure exactly.** `build_week_blocks` (L175–182) cuts the panel into non-overlapping Mon-anchored 5-day windows, returning shape `(n_blocks, 5, n_strats)`. Each block keeps the four strategies' realized daily P&Ls bound together — when block `i` is drawn, all four strategies' rows for those five days come along together. No per-strategy independent shuffling.
3. **Sampling is block-uniform with replacement, no parametric coupling.** In `run_seed` (L241–243):
   ```python
   for _ in range(n_sims):
       idx = rng.integers(0, n_blocks, blocks_per_sim)
       path = np.concatenate([blocks[i] for i in idx])[:horizon]
   ```
   `rng.integers(0, n_blocks, blocks_per_sim)` draws one integer per block slot uniformly with replacement from `[0, n_blocks)`. The drawn blocks are concatenated along axis 0 (time), preserving each block's `(5, n_strats)` shape. There is no correlation matrix, no copula, no per-strategy independent draw, and no parametric joint distribution at any point.

No code combines branches. The assumption is cleanly A1.

What this means for Q-CORR-2's Pre-Q falsifier (per Notice §6 Pre-condition A):

- The MC's joint-tail estimate already embeds whatever empirical correlation exists in the **unconditional** Pepperstone/OANDA panel over the resample horizon (panel window: 2022 → 2026 per CLAUDE.md). Specifically, any *within-block* cross-strategy correlation is preserved verbatim; *across-block* correlation is broken by uniform-with-replacement block draws (this is the standard block-bootstrap trade-off).
- The Pre-Q's test is therefore the A1 form named in Notice §6: `corr(pyramid-active subset of the panel) − corr(unconditional panel)`, with a Δ threshold to be set at Pre-Q drafting time. Out of scope here.

---

## §3 Code excerpt (verbatim)

All line numbers from `portfolio_mc.py` at worktree commit `54d2285`.

### Panel construction (L151–172)

```python
def build_daily_panel(trades_by_strat: Dict[str, pd.DataFrame],
                      allocations: Dict[str, float]) -> Tuple[pd.DataFrame, Dict[str, dict]]:
    """Scale each strategy's realized P&L so 1R maps to allocation × $200K, then
    aggregate to a business-day panel."""
    scale_info: Dict[str, dict] = {}
    series = []
    for strat, trades in trades_by_strat.items():
        r1, fell_back = implied_1r(trades["pnl"], strat)
        target_dollars = allocations[strat] * STARTING_EQUITY
        scale = target_dollars / r1 if r1 > 0 else 1.0
        scale_info[strat] = {
            "implied_1r": r1,
            "scale": scale,
            "n_trades": len(trades),
            "fell_back": fell_back,
        }
        s = trades.groupby("exit_date")["pnl"].sum() * scale
        s.name = strat
        series.append(s)
    panel = pd.concat(series, axis=1, sort=True).fillna(0.0)
    bdays = pd.bdate_range(panel.index.min(), panel.index.max())
    return panel.reindex(bdays).fillna(0.0), scale_info
```

### Block construction (L175–182)

```python
def build_week_blocks(panel: pd.DataFrame) -> np.ndarray:
    """Mon-anchored non-overlapping 5-day blocks. Returns shape (n_blocks, 5, n_strats)."""
    vals = panel.values  # (n_days, n_strats)
    blocks = []
    for i, d in enumerate(panel.index):
        if d.weekday() == 0 and i + 5 <= len(panel):
            blocks.append(vals[i:i + 5])
    return np.array(blocks)
```

### Joint-day sampling loop (L223–258, key lines L241–243 highlighted)

```python
def run_seed(seed: int, n_sims: int, blocks: np.ndarray,
             dd_trigger: float, dd_scale: float, horizon: int = HORIZON_DAYS,
             strats: Tuple[str, ...] = STRATS) -> dict:
    """Run n_sims bootstrap simulations for one seed.

    `strats` labels the path's column axis for bust attribution. Defaults to
    the global 4-tuple but callers (via `_load_all`) pass the panel-specific
    tuple — Pepperstone gets all 4, OANDA gets 3.
    """
    rng = np.random.default_rng(seed)
    n_blocks = len(blocks)
    blocks_per_sim = (horizon + 4) // 5

    outcomes = {"pass": 0, "bust_daily": 0, "bust_static": 0, "timeout": 0}
    days_to_pass: list[int] = []
    max_dds: list[float] = []
    bust_attrib = {s: 0 for s in strats}

    for _ in range(n_sims):
        idx = rng.integers(0, n_blocks, blocks_per_sim)
        path = np.concatenate([blocks[i] for i in idx])[:horizon]

        outcome, day, max_dd, culprit = _simulate_path(path, dd_trigger, dd_scale, horizon)
        outcomes[outcome] += 1
        max_dds.append(max_dd)
        if outcome == "pass":
            days_to_pass.append(day)
        elif outcome in ("bust_daily", "bust_static") and culprit is not None:
            bust_attrib[strats[culprit]] += 1

    return {
        "outcomes": outcomes,
        "days_to_pass": days_to_pass,
        "max_dds": max_dds,
        "bust_attribution": bust_attrib,
    }
```

### Per-day P&L coupling inside `_simulate_path` (L195–200)

```python
for day in range(horizon):
    dd_from_peak = (eq - peak) / peak if peak > 0 else 0.0
    # ULP-precision rounding before threshold compare; see Q-MCFP-1
    scale = dd_scale if round(dd_from_peak, 6) <= -dd_trigger else 1.0
    strat_pnls = path[day] * scale
    pnl = float(strat_pnls.sum())
```

`path[day]` is a length-`n_strats` row drawn jointly from the bootstrap path. `strat_pnls.sum()` is the day's portfolio P&L (the four strategies summed as a single number, with the dd-scale applied uniformly). The same `scale` is applied to all strategies on a given day — no per-strategy independent dd_protection.

---

## §4 Empirical figures (conditional on branch — A1)

**Date range of joint panel** (Pepperstone canonical, per panel filenames at L72–77 and CLAUDE.md):
- Guardian: `Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-05_33781.csv`
- Striker DJ30: `Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv`
- Aegis: `Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-04-26_0bf1b.csv`
- Striker NAS100: `Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-05_7ca6f.csv`

Panel span asserted by `assert_window` (L119–125): at least `4 * 365` days (with 60-day tolerance) per strategy. CLAUDE.md anchor strings the panel as 2022 → 2026 (223 week-blocks). The exact `panel.index.min()` / `panel.index.max()` is computed at load time from the union of the four strategies' exit dates; I did not run the loader (read-only spec; running would also fail for OANDA on this worktree since `Glob` is sufficient for the structural finding).

**Resample unit:** block.

**Block construction rule:** non-overlapping, Monday-anchored, 5-business-day length. Code at L175–182.
- A block starts at panel index `i` iff `panel.index[i].weekday() == 0` (Monday) AND `i + 5 <= len(panel)`.
- Blocks do not overlap because the iterator advances day-by-day but only emits at Monday indices; the next Monday is exactly 5 business days later (no wraparound consideration in code, since `bdate_range` skips weekends).
- `blocks_per_sim = (horizon + 4) // 5` (L234). For the canonical horizon=150 (worktree value at L42), `blocks_per_sim = 30`. Note: PR #85 changed this constant; under HORIZON_CAP=1500 the per-sim block count becomes 300, but each individual block draw is still uniform-with-replacement and joint across strategies.

**Joint-panel construction style:** strategy-by-strategy series, then `pd.concat(axis=1)` with `fillna(0.0)`, then reindex to the union business-day range (also zero-filled). Per §0.5 Q3, this is the "strategy-by-strategy with date alignment imposed at sample time" branch — both Q3 options are defensible per the handoff, this is the one used.

No conditional correlations computed (forbidden by handoff §5 move #1).

---

## §5 Sanity check against 2026-05-15 lock

The 99.88/0.12/4.21 Pepperstone anchor cited in parent Notice §1 was produced by commit `43aa187` (PR #85, merged 2026-05-16 to `origin/main`). This anchor uses the FXIFY-correct timeout semantic (INACTIVITY_LIMIT=60 + HORIZON_CAP=1500) that landed in PR #85, replacing the prior `HORIZON_DAYS=150` runout. (Note: parent Notice and handoff date this as "2026-05-15 lock"; the actual merge timestamp is 2026-05-16 22:16:14 -0400 per `git show 43aa187`. The semantic-change PR landed 2026-05-16; if there is a separate 2026-05-15 lock event, it is not the one in `origin/main`. Not material to branch classification — the joint-sampling code is identical.)

**Code-path sanity-check verdict: PASS with one disclosure.**

- The code path read in this report (worktree `54d2285`) is the **immediate predecessor** of the lock-producing code path (`origin/main` `43aa187`).
- PR #85's diff to `portfolio_mc.py` was inspected line-by-line via `git show 43aa187 -- portfolio_mc.py`. Confirmed changes:
  - L42: `HORIZON_DAYS = 150` → `INACTIVITY_LIMIT = 60` + `HORIZON_CAP = 1500`
  - `_simulate_path`: docstring expansion; added `consecutive_idle` counter; added `is_idle = (pnl == 0.0) and (not np.any(strat_pnls != 0.0))` check; added `bust_inactivity` early-return; renamed `"timeout"` outcome to `"horizon_cap"`.
  - `run_seed`: outcome dict gained `bust_inactivity` and `horizon_cap` keys; default `horizon` arg renamed `HORIZON_DAYS` → `HORIZON_CAP`.
  - `compute_default_config`: added `bi_r` / `hc_r` rates; bust_r aggregation unchanged (still daily + static, explicitly preserved for "lock-gate continuity").
  - `report_default` and `mode_sensitivity._row`: cosmetic relabeling of the printed bucket.
- **None of these changes touch `build_daily_panel`, `build_week_blocks`, or the `rng.integers` + `np.concatenate` lines.** The joint-sampling assumption (A1, week-block bootstrap on union-aligned daily panel) is byte-identical between the worktree code I read and the lock-producing code.

So the read code path produces the lock, modulo a termination-rule modification that operates entirely after joint-day sampling has already happened. The Pre-Q falsifier for Q-CORR-2 — which is about the joint-day sampling assumption, not about termination semantics — can be drafted against the assumption named in §2 without revisiting this report when working from `origin/main`.

---

## §6 Status

**DONE_WITH_CONCERNS**

Joint-sampling code located, assumption named (A1), report file written, code excerpts quoted verbatim, sanity check passed. Two concerns warrant parent awareness; both are surfacings rather than blockers, and neither alters the branch classification or the falsifier-shape implication for Pre-Q. See §7.

---

## §7 Concerns

### C1 — Worktree HEAD does not include the lock-producing commit (parent's pre-flag #1, confirmed and clarified)

Parent's pre-flag stated worktree HEAD is `54d2285`. Worktree HEAD is actually `317e43a` (the docs-only commit filing the Notice + handoff); `54d2285` is the last commit *touching `portfolio_mc.py`* on this branch. The substantive point parent surfaced is correct: PR #85 (`43aa187`) is on `origin/main` and not in this branch's ancestry (merge-base is `670625d`). I read PR #85's portfolio_mc.py diff via `git show` and confirmed the joint-sampling code is unchanged. **Disposition: not load-bearing for the branch classification, but worth noting in the Pre-Q audit trail that the canonical lock code is on main, not this branch.**

### C2 — STATE.md does not exist (parent's pre-flag #2, confirmed)

`Glob STATE.md` and `Glob docs/STATE.md` both return no matches. The parent Notice §7 audit hook "STATE.md open-questions row expected" and the handoff §0 read target #4 cannot be honored. This is parent-session housekeeping, not spawn-scope work. **Disposition: noted, not actioned (per handoff §5 forbidden move #5 — do not edit parent Notice).**

### C3 — Lock-date discrepancy (informational)

Parent Notice §1 and handoff §2.4 cite "2026-05-15 FXIFY-correct lock" producing 99.88/0.12/4.21. The actual merge commit (`43aa187`) is timestamped 2026-05-16 22:16:14 -0400 per `git show 43aa187`. If there is a separate 2026-05-15 lock event distinct from the PR #85 merge, it is not visible in `origin/main` log filtered on "FXIFY" or "timeout". Possibilities (not investigated): (a) the anchor was first computed on 2026-05-15 and merged 2026-05-16; (b) typo in parent docs. **Disposition: not load-bearing for assumption classification. Parent should reconcile during Pre-Q drafting.**

### C4 — `blocks_per_sim` changed substantially under PR #85 (informational, not a re-classification)

The worktree's `blocks_per_sim = (horizon + 4) // 5` with `horizon=150` yields 30 blocks per sim. PR #85's `horizon=HORIZON_CAP=1500` yields 300 blocks per sim. This is a **20× increase in the number of independent block draws per simulated trajectory**, which has implications for how much *across-block* correlation washes out in any given sim. The branch classification is unchanged (still A1), but if the Pre-Q falsifier framing turns on the conditional-correlation half-life across the bootstrap horizon, this 20× difference may matter. Flagging for parent awareness; not in spawn scope to evaluate. **Disposition: informational. The A1 classification stands; the falsifier-threshold-setting Pre-Q work should be aware of this when reading from main.**

---

End of report.
