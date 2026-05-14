# WFO Path B — adversarial OOS-guard tests (Q-CORR-1.2)

**Status:** checklist (execute during §15 pre-flight, before TV operation)  
**Parent:** [`docs/briefs/Q-CORR-1.2-guardian-family-silver-wfo.md`](../briefs/Q-CORR-1.2-guardian-family-silver-wfo.md) §15

These scenarios validate that `train_selection_lock.py` and `audit_path_b_ordering.py` fail loudly on discipline violations.

---

## Scenario 1 — OOS config not in train selection

**Setup:** Ingest an OOS CSV whose basename does not match `expected_oos_csv_basename` in `train_selection_lock.json`.

**Expected:** `assert_oos_matches_lock` raises `AssertionError`.

---

## Scenario 2 — OOS file predates train-selection commit

**Setup:** Manifest lists `train_selection_committed_utc` after the OOS CSV file `mtime` (simulate by touching OOS old, commit time new).

**Expected:** `python scripts/wfo/audit_path_b_ordering.py <manifest>` exits **non-zero**.

---

## Scenario 3 — Post-hoc lock recreation

**Setup:** Delete and recreate `train_selection_lock.json` after OOS export such that the lock file `mtime` is **after** OOS CSV `mtime` while manifest `train_selection_committed_utc` is inconsistent with the legitimate workflow ordering.

**Expected:** Ordering audit **FAIL**; failure mode distinguishable from legitimate “commit then export” flow (OOS mtime should still be **after** committed selection time in the valid path).

---

## Scenario 4 — NO_CANDIDATE lock refusal (Seam #1 follow-up, 2026-05-13)

**Setup:** Train sweep ingest completes; no config in the manifest passes the §16 hard constraints (DD ≤ 8% AND WR ≥ 15% AND trades ≥ 50). `run_path_b.py select --fold=1` is invoked.

**Expected behavior chain:**

1. `select_train_fold` writes `train_selection_lock.json` with `selection_status="NO_CANDIDATE"`, `candidate_count=0`, `selected_config_id=""`, and a committed UTC timestamp — preserving an audit trail of the failed selection attempt.
2. `select` raises `ValueError` (CLI exits with code `1`).
3. If an operator subsequently attempts to ingest an OOS CSV against this lock, `assert_oos_matches_lock` raises `AssertionError` with message `"OOS ingest refused: lock <path> has selection_status=NO_CANDIDATE"` — preventing accidental OOS work against a failed-train run.

**Disposition implication:** NO_CANDIDATE at the data layer is a FALSIFIED-disposition signal per §17. Operator closes the Pre-Q FALSIFIED on grounds that no parameter zone clears the §16 floor; appends to `docs/rejected_candidates.md`; does NOT proceed to OOS.

---

## Record

| Date | Operator | Outcome / notes |
|------|----------|-----------------|
| 2026-05-13 | Claude Code (Q-CORR-1.2 §15 pre-flight) | **Scenario 1 PASS.** Covered by [`tests/test_wfo_path_b.py::test_train_selection_lock`](../../tests/test_wfo_path_b.py): `assert_oos_matches_lock` raises `AssertionError` when basename differs from `expected_oos_csv_basename`. Targeted run green at HEAD `31110f5`. |
| 2026-05-13 | Claude Code (Q-CORR-1.2 §15 pre-flight) | **Scenario 2 PASS.** Covered by [`tests/test_wfo_path_b.py::test_audit_detects_oos_before_commit`](../../tests/test_wfo_path_b.py): manifest with OOS `mtime` predating `train_selection_committed_utc` causes `audit_path_b_ordering.py` to exit `1`. Targeted run green at HEAD `31110f5`. |
| 2026-05-13 | Claude Code (Q-CORR-1.2 §15 pre-flight) | **Scenario 3 PASS-WITH-LIMITATION.** Three sub-cases exercised manually: (3a) fully-forged manifest+lock pair → audit returns `0` (PASS), confirming the §6.5 acknowledged gap "does not prevent a determined bypass of git history"; (3b) distinguishable forgery signature: `lock_file.mtime − lock.committed_utc = 7200s` in the forged case vs ~0s in legitimate flow — detectable but not surfaced by the current audit script; (3c) partial forgery (lock rewritten, manifest left consistent with original ordering) → audit returns `1` (FAIL). Residual: a determined attacker who coherently rewrites both manifest and lock can pass `audit_path_b_ordering.py`. Git-committing `train_selection_lock.json` is the load-bearing mitigation (§6.5 line "committed or timestamp-persisted **before** any OOS TV export"). |

## Findings surfaced to brief author

- **Scenario 3 residual (informational, no methodology change):** `audit_path_b_ordering.py` is a one-sided check (manifest-only). A coherent post-hoc forgery of both `run_manifest.json` and `train_selection_lock.json` passes the audit. Mitigation already in §6.5: commit `train_selection_lock.json` to git **before** OOS TV export. A small follow-up script (`audit_lock_mtime_consistency.py`, ~20 lines) cross-checking `lock_file.stat().st_mtime` vs `lock["committed_utc"]` would close the forensic gap. Not gating Q-CORR-1.2 — flagged for post-disposition consideration.
