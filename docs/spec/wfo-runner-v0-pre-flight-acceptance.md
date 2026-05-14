# WFO Path B — §15 acceptance-battery outcomes (Q-CORR-1.2)

**Status:** outcome record (parallel to [`wfo-runner-v0-adversarial-tests.md`](wfo-runner-v0-adversarial-tests.md))
**Parent:** [`docs/briefs/Q-CORR-1.2-guardian-family-silver-wfo.md`](../briefs/Q-CORR-1.2-guardian-family-silver-wfo.md) §15

Records outcomes of the four `Acceptance battery` items from §15. Each item runs against locally-resident vendor CSVs (gitignored per public-clone posture) and is "skip-if-missing-data" by design — so this file is the only persistent record that the anchors reproduce on Joshua's local clone.

---

## Item 1 — `pytest tests/ -q` baseline preserved

**Date:** 2026-05-13
**Operator:** Claude Code (post-merge of PR #79)
**Command:**

```bash
python -m pytest tests/ -q
```

**Outcome:** **PASS** — 157 passed, 14 skipped (all skips are vendor-CSV–dependent on tests that don't exercise §15 anchors). Brief §15 acceptance bar (140+ pass) cleared.

---

## Item 2 — `acceptance_silver.py` against `_dc6a3` Gold-on-Silver dump

**Date:** 2026-05-13
**Operator:** Claude Code (post-merge of PR #79)
**Command:**

```bash
Q_CORR_SILVER_TV_CSV=data/tv_exports/pepperstone/Guardian_Gold_v5.5_PEPPERSTONE_XAGUSD_2026-05-13_dc6a3.csv \
  python scripts/wfo/acceptance_silver.py
```

**Expected (Q-CORR-1.1 amendment §7 reference, §15 DD-amended 2026-05-13):** n=238, PF=1.613, WR=11.34%, DD=14.99% (static-equity notional basis).

**Outcome:** **PASS — anchor reproduces exactly.**

```
n_trades=238 PF=1.613 WR=11.34% maxDD%=14.99
PASS
```

**Significance:** confirms the §15 DD-convention amendment (11.52% compounded-peak → 14.99% static-equity notional) is empirically correct against the same dc6a3 bytes Joshua holds on disk. The static-equity convention is what `acceptance_silver.py`, `scripts/wfo/operations.py`, and the §14 Gate 8 disposition all consume — these are now triangulated.

**File hash verified:** comparator sha `f35c40ed2ef6d083e4984f90b6848c96e7f3ca382c5cbd54b24dc090eb9d7dc5` in `data/tv_exports/pepperstone/SHA256SUMS` matches working-tree bytes.

---

## Item 3 — `lib/correlation.py` ρ_DJNAS anchor

**Date:** 2026-05-13
**Operator:** Claude Code (post-merge of PR #79)
**Command:**

```bash
python -m pytest tests/test_correlation.py::test_pearson_daily_pnl_dj_nas_anchor -v
```

**Expected (§10 audit hook anchor):** ρ_DJNAS ≈ 0.021704 on the canonical 2026-05-05 Pepperstone DJ30 + NAS100 pair (`Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-05_12175.csv` + `Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-05_7ca6f.csv`).

**Outcome:** **PASS.**

```
tests/test_correlation.py::test_pearson_daily_pnl_dj_nas_anchor[...DJ30...US30..._12175.csv-...NAS100...NAS100..._7ca6f.csv-0.021704118183897454] PASSED
```

**Significance:** the zero-fill aligned-calendar Pearson method in `lib/correlation.py` reproduces the canonical DJ30/NAS reference. Q-CORR-1.2 §14 Gate 12 uses the same `pearson_daily_series` against the locked `_13fad` Gold comparator — the underlying function is anchor-stable.

---

## Item 4 — `lib/regime_bootstrap.py` Silver p05_pf historical anchor

**Date:** 2026-05-13
**Operator:** Claude Code (post-merge of PR #79)
**Command:**

```bash
Q_CORR_SILVER_TV_CSV=data/tv_exports/pepperstone/Guardian_Gold_v5.5_PEPPERSTONE_XAGUSD_2026-05-13_dc6a3.csv \
  python -m pytest tests/test_regime_bootstrap.py::test_silver_bootstrap_p05_optional -v
```

**Expected (§15 historical anchor):** p05_pf ≈ 1.05 ± 0.02 at the **historical pin** (bootstrap_seed=7, bootstrap_n_panels=100, block_months=6). These are *historical-anchor* parameters; distinct from the §14 Gate 9 *disposition* convention (canonical seed=42, n_panels=1000).

**Outcome:** **PASS.**

```
tests/test_regime_bootstrap.py::test_silver_bootstrap_p05_optional PASSED
```

**Significance:** the dual-convention split documented in `docs/spec/wfo-runner-v0.md` §2 holds empirically. Historical anchor reproduces at (7, 100, 6); orchestration metadata pin (42, 1000) recorded in run manifests at `init-run`. Both regime-robustness invocations use the same `regime_bootstrap_daily_pnl` function with different seeds/n_panels.

---

## Composite finding

All four acceptance-battery items pass against bytes Joshua holds locally. Combined with the §11/§12/§13 pinned tests + the four recorded adversarial scenarios + the live `init-run` smoke, **§15 programmatic pre-flight is GREEN.**

Remaining §15 items are operator-manual:

- [ ] Pepperstone TV XAGUSD chart spot-check: 2022-01-11 → 2026-04-20+ availability
- [ ] No live Silver execution in OOS window 2025-05-11 → 2026-04-20

Joshua attests both before Stage 1 TV operations begin.

---

## Reproducibility note

The vendor CSVs referenced above are gitignored per CLAUDE.md public-clone posture. Their content-addressed integrity lives in `data/tv_exports/pepperstone/SHA256SUMS`. To reproduce this acceptance battery on a fresh clone, restore the CSVs locally (Joshua's main worktree or another local source) and re-run the commands above. The CI workflow is format-only and cannot re-execute these items on GitHub runners.
