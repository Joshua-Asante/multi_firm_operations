# ADR 2026-05-10 — MC C2 anchor ratification post-PR-#53; no repin required

**Status:** ACCEPTED
**Date:** 2026-05-10
**Supersedes:** none
**Relates to:** ADR 2026-05-08-dd-trigger-c2-relock; ADR 2026-05-10-dd-protection-ulp-rounding (PR #53); PR #60 / Q-MCFP-1 (MC inline ULP rounding); GH#55 (closes)

---

## Context

PR #53 applied `round(dd_from_peak, 6)` to the comparison site in `dd_protection.py` (live-tool path used by the morning dashboard). GH#55 was enumerated as deferred follow-up #2 from PR #53, on the premise that the MC simulator shared the comparison logic via `dd_protection.calculate_protection` and that the C2 calibration anchor (Pepperstone 98.09 / 0.36 / 4.73; OANDA 96.23 / 0.69 / 4.91) might therefore drift post-fix.

CC verification (2026-05-10, 10K × 3-seed re-run on both panels under the lock-anchor config) reproduced every pinned anchor in `tests/test_mc_anchors.py` to printed precision, Δ = 0.00 pp across pass-rate, bust-rate, p99 DD, n_bdays, n_blocks on both panels. All 8 anchor tests PASS. Bust attribution Pepperstone reproduces memory anchor exactly (44.4 / 24.1 / 21.3 / 10.2).

The Δ = 0.00 result is not coincidence; it is structurally guaranteed by the import topology:

- `portfolio_mc.py:31-34` imports only the constants `DD_TRIGGER` and `DD_SCALE` from `dd_protection`. It never calls `calculate_protection`.
- The MC threshold check is inlined twice: `portfolio_mc.py:198` (`_simulate_path`) and `portfolio_mc.py:501` (`mode_historical`).
- Both inline sites were ULP-rounded by PR #60 / Q-MCFP-1, which merged before the C2 anchor was committed.

Therefore the C2 anchor was already computed under ULP-rounded comparisons in the MC path. PR #53 is a forward-only consistency fix at the live-tool site; the two ULP-comparison domains are independently applied and not coupled to a shared anchor.

GH#55's framing inherited an implicit call-graph assumption that was not verified at issue-authoring time. The verification was still load-bearing as a cross-coupling sanity check — had any unintended import path connected the two domains, the Δ would have surfaced it — but the "drift plausible / possibly material" risk surface described in the issue was structurally moot from the start.

## Decision

1. Ratify existing pins in `tests/test_mc_anchors.py` as valid post-PR-#53. **No file change.**
2. Live C2 dd_protection lock (1.5 % / 0.40×, relocked 2026-05-08) is unchanged. **No risk-constant modification.**
3. Document the import-topology finding here so future PRs to either domain (`dd_protection.py` or `portfolio_mc.py` threshold sites) reference this ADR in their own §0 reads and do not re-enumerate "MC anchor stability" as a follow-up unless the import topology has changed.

## Consequences

- GH#55 closes with this ADR as the resolution artifact.
- Future ULP-class fixes at either domain require explicit topology verification before enumerating cross-domain follow-ups.
- The methodology lesson (issue-authoring Rule 0: verify call-graph claims by grep before enumerating cross-domain risk) is captured separately as a candidate lesson; not graduating to load-bearing this ADR.

## Forbidden moves

- Do not repin `tests/test_mc_anchors.py` — the existing pins reproduce. Repinning to "post-fix values" when the values are bitwise identical is ceremony and obscures the actual finding.
- Do not amend PR #53's ADR retroactively to claim it never enumerated GH#55. The enumeration was made; this ADR documents why the enumerated risk did not materialize.
- Do not generalize this finding to "ULP fixes at one site never affect MC anchors." The conclusion is specific to the import topology as of 2026-05-10. If the topology changes (e.g., `portfolio_mc.py` is refactored to call `calculate_protection`), the next ULP-class fix re-opens the verification.

## Alternatives considered

- **Open a C2 re-evaluation ADR** — rejected. Verdict is unambiguously WITHIN_TOLERANCE with Δ = 0.00 pp; no re-evaluation triggered.
- **Repin tests to "post-fix values" as ceremonial confirmation** — rejected. Pins reproduce. Repinning would imply a numerical change occurred when none did.
- **Close GH#55 without an ADR** — rejected. The import-topology finding is structural information that needs to live in `docs/adr/` for cross-reference. Closing with only a comment loses it.
- **Audit-note rather than ADR** — borderline. Chose ADR because the decision (ratify pins, no action) is itself a structural commitment future PRs reference; audit-note is the parallel methodology-lesson artifact.

## Audit hooks


```bash
# Topology assertion: portfolio_mc.py imports only constants, never the function
grep -nE "from \.?dd_protection import" portfolio_mc.py
# Expected: imports DD_TRIGGER, DD_SCALE only at BOTH the relative-import
# (line 31, `from .dd_protection`) and absolute-import fallback (line 34,
# `from dd_protection`) inside the try/except. NO calculate_protection
# import at either site. Asymmetric drift — one path adds the function
# import, the other doesn't — would surface here.

grep -n "calculate_protection" portfolio_mc.py
# Expected: zero matches. If any match appears, this ADR's premise is invalidated; re-verify.

# Both inline ULP-rounded sites still rounded
grep -n "round(dd_from_peak" portfolio_mc.py
# Expected: ≥2 matches (lines ~198 and ~501 as of 2026-05-10).

grep -n "round(dd_from_peak" dd_protection.py
# Expected: 1 match at the calculate_protection comparison site.

# Verify pinned anchor VALUES unchanged. Inspect assert lines, not commit
# metadata: tests/test_mc_anchors.py may legitimately gain new tests post-
# PR #53 without modifying anchors (e.g., PR #63 / Q-MCFP-1, 54d2285,
# added a Rule 0-T direct-call test on 2026-05-10 with pin values
# untouched). What matters is the six numerics. Pins are stored in decimal
# form (0.9809 = 98.09 %) — match decimal not percent.
grep -E "approx\((0\.9809|0\.0036|0\.0473|0\.9623|0\.0069|0\.0491)" tests/test_mc_anchors.py | sort -u | wc -l
# Expected: 6. If any other count, the pins moved; this ADR's premise
# is invalidated. Re-verify against the latest MC re-run before accepting
# any test failure as benign.
```


If any audit hook fails on quarterly review, the ratification's premise has shifted and the ADR needs re-evaluation.
