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

## Record

| Date | Operator | Outcome / notes |
|------|----------|-----------------|
|      |          | (fill on execution) |
