# ADR: Pine `input.float` default realignment + validator HARD-tier promotion

**Date:** 2026-05-18
**Status:** **SUPERSEDED** by [`2026-05-18-relock-to-test-values.md`](2026-05-18-relock-to-test-values.md) (same day).
**Related:** [`scripts/validate_params.py`](../../scripts/validate_params.py), [`config/params.toml`](../../config/params.toml)

> **Superseding note (2026-05-18):** The 4 fixes in this ADR realigned Pine
> defaults *upward* toward the then-locked spec (DJ30 0.70 → 1.00 etc.).
> Same-day portfolio MC comparison via
> [`scripts/compare_dj30_nas100_configs.py`](../../scripts/compare_dj30_nas100_configs.py)
> showed the *unfixed* Pine defaults (0.70 / 0.37 with pyramid 750 + maxDD
> 1.15) were a materially better operational config (−60% bust rate,
> −0.44pp p99 DD, at −0.67pp pass cost). The lock was therefore moved *to*
> the Pine defaults rather than fixing Pine to the lock. All 4 fixes in
> this ADR were reverted (defaults now match the new lock). The validator
> machinery and tier-promotion in this ADR remain in effect; only the
> direction-of-fix is superseded. See the new ADR for the re-lock rationale.

## Context

The parameter validator landed earlier 2026-05-18 (see `CLAUDE.md` "Parameter
manifest gate" subsection). Its opportunistic Pine-grep tier, initially
WARN-only, was run against the four production Pine files (gitignored;
held privately, mirrored to the worktree from local source for the check).
Two files declared `input.float` defaults that disagreed with every other
in-tree source for the same parameter:

| File | Line | Default | Tooltip says | dd_protection.py `BASE_RISK` | `firm_rules.py` `_BASE_RISK` | `CLAUDE.md` | CHANGELOG | Manifest |
|---|---|---|---|---|---|---|---|---|
| `strategies/striker/striker_dj30_v4.5.pine` | 30 | **0.70%** | "LOCKED: 1.00%" | 0.0100 | 0.0100 | 1.00% | 1.00% | 1.00% |
| `strategies/nas/striker_nas100_v1_indicator.pine` | 87 | **0.45%** | "LOCKED v1.0: 0.40%" | 0.0040 | 0.0040 | 0.40% | 0.40% | 0.40% |

Operational impact: on a fresh TradingView chart attach, the strategy would
trade at the stale Pine default until the user manually overrode the input
per the tooltip cue. Every other layer of the stack was correct and
internally consistent at the locked value; the Pine source itself was the
only outlier.

Adjacent stale tooltips/defaults observed but **not in scope for this ADR**
(out of v1 manifest tracking — flagged as v2 expansion candidates):
- `striker_dj30_v4.5.pine:32` `maxDailyDD` default 1.15 vs tooltip "LOCKED: 1.00%"
- `striker_dj30_v4.5.pine:35` `maxDailyTrades` default 2 vs tooltip "LOCKED: 3"
- `striker_dj30_v4.5.pine:97` `pyramidSize` default 750.0 vs tooltip "LOCKED: 350%"
- `guardian_gold_v5.5_indicator.pine:40` tooltip says "LOCKED: 0.30%" — stale
  post-2026-04-23 risk relock to 0.34%; default 0.34% is correct.

## Decision

1. **Realign the two `riskPerTrade` defaults** to match the locked values
   declared in `dd_protection.py BASE_RISK` and the Strategy Reference table
   in `CLAUDE.md`:
   - `strategies/striker/striker_dj30_v4.5.pine:30` — `0.70` → `1.00`
   - `strategies/nas/striker_nas100_v1_indicator.pine:87` — `0.45` → `0.40`
2. **Promote the Pine-vs-manifest tier in `scripts/validate_params.py` from
   WARN to HARD** when Pine files are present locally. "Pine entirely absent"
   (CI / public clone) remains a status WARN — absence is not drift.
3. **Re-export the corrected Pine source** to local TradingView via
   `C:\Users\joshu\Downloads\dj30.txt` / `nas100.txt` (same bytes as the
   worktree copies after the edit).

## Trade-offs

| Approach | Outcome |
|---|---|
| Accept-and-document only (keep WARN forever) | **Rejected** — leaves the manual-override-on-every-attach failure mode in place. The validator's purpose is to eliminate exactly this class. |
| Fix Pine but keep tier WARN | **Rejected** — a regression (re-import of an unfixed Pine source) would not block a commit; defeats the gate. |
| Promote to HARD without fixing | **Rejected** — would block all current commits until fix lands; trivially equivalent to "fix then promote" with worse ergonomics. |
| Also fix the adjacent stale defaults (max daily DD, max trades, pyramid, Guardian tooltip) | **Deferred** — those parameters aren't in the v1 manifest. Adding them is a v2 manifest expansion, not a fix-in-place. ADR scoped to v1 manifest fields only. |

## Consequences

- The 2026-05-18 validator landing now reports `0 HARD / 0 WARN` on the
  current repo with Pine present, and `0 HARD / 1 WARN` on a fresh clone
  (Pine absent — status).
- A future re-import of an unfixed Pine source (or an unintentional revert
  of these two lines) will hard-fail the commit. Joshua's local pre-commit
  hook installed at `.git/hooks/pre-commit` enforces this.
- The "promote v2 manifest fields" follow-up is now bounded: add
  `max_daily_dd_pct`, `max_daily_trades`, `pyramid_size_pct` to per-strategy
  manifest sections; extend the Pine regex to cover them. Until that lands,
  those four adjacent drifts remain unflagged.
- Methodology note: this is the first complete cycle of the validator —
  build → surface real drift on first run → fix → promote tier. The
  superpowers/Rule-0 chain identified the brief's own seed-value drifts in
  Phase 0; the validator then identified the production Pine drifts on
  first execution. Both classes were caught at the in-tree boundary.

## Verification

```bash
$ python scripts/validate_params.py
Summary: 0 HARD violation(s), 0 WARN violation(s)
Runtime: 72.9 ms

$ python scripts/validate_params.py --self-test-only
Self-test OK (good: 0 hard / 1 warn; bad: 2 hard / 1 warn)
```

Pine source-of-truth post-fix (line-anchor check):

```bash
$ sed -n '30p' strategies/striker/striker_dj30_v4.5.pine
riskPerTrade = input.float(1.00, "Risk Per Trade (%)", minval=0.1, maxval=3.0, step=0.01, group=group_risk,
$ sed -n '87p' strategies/nas/striker_nas100_v1_indicator.pine
riskPerTrade      = input.float(0.40, "Risk Per Trade (%)", minval=0.1, maxval=3.0, step=0.01, group=group_acct,
```

## Addendum — second-pass coverage expansion (same day)

After Round 1 (initial 2 fixes above) Joshua provided the four **strategy**
Pine files that weren't reachable on the first pass — full coverage of the
canonical set declared in `strategies/MANIFEST.sha256` minus only the DJ30
indicator sibling. Two material findings:

1. **`Downloads/dj30.txt` was reverted** between Round 1 and Round 2 — Round
   1's mirrored fix (`0.70 → 1.00`) was overwritten back to `0.70`, likely
   by a fresh TradingView re-export. The validator caught the same drift
   again; fix re-applied. **Operational implication:** mirroring corrected
   bytes to `Downloads/` does NOT propagate to TradingView's source-of-truth
   — that round-trip requires manually pasting the corrected source over
   the existing code in the TV Pine editor. Until that step happens, every
   fresh TV re-export will reintroduce the drift.
2. **NAS100 strategy file `riskPerTrade` default was 0.37**, distinct from
   both the indicator (0.45, fixed in Round 1) and the locked value (0.40).
   Three different values for the same parameter across two files plus the
   locked spec — research-mode drift accumulating per-file. Validator now
   checks BOTH strategy and `_indicator.pine` when both exist (extended
   from "either or" → "both, must agree") via `_resolve_pine_targets`
   returning a list rather than a single best-available file.

### Round 2 fixes

| File | Line | Default before | After |
|---|---|---|---|
| `strategies/striker/striker_dj30_v4.5.pine` (strategy) | 30 | `0.70` | **`1.00`** |
| `strategies/nas/striker_nas100_v1.pine` (strategy) | 63 | `0.37` | **`0.40`** |

### Round 2 verification

```bash
$ python scripts/validate_params.py
Summary: 0 HARD violation(s), 0 WARN violation(s)
Runtime: 66.0 ms

$ ls strategies/{guardian,striker,aegis,nas}/*.pine | wc -l
7    # 4 strategies + 3 indicators (DJ30 indicator still not provided)
```

### Open follow-up — TradingView round-trip

Joshua needs to paste the corrected `Downloads/*.txt` source into
TradingView's Pine editor and "save" / publish, to make the fix stick at
the TV-side source-of-truth. Without that step, the next fresh TV
re-export will revert all affected files to their research-mode defaults
and the validator will hard-fail the next commit. The validator itself is
doing its job (catching the drift on every commit) — the gap is the
human-loop step to push corrected bytes back into TradingView.

## Addendum — Round 3 (same day, DJ30 indicator)

The DJ30 indicator sibling — final file of the canonical 8 — landed after
Round 2. Same drift class as the DJ30 strategy:

| File | Line | Default before | After |
|---|---|---|---|
| `strategies/striker/striker_dj30_v4.5_indicator.pine` | 54 | `0.7` | **`1.00`** |

### Cumulative drift summary (across all 3 rounds, same day)

Four `riskPerTrade input.float` drifts found, all in production Pine
source-of-truth files for the two strategies whose locked risk_pct
disagreed with the file defaults. Guardian and Aegis Pine files were
clean from the start.

| Strategy | Locked | Strategy file default | Indicator file default |
|---|---|---|---|
| Striker DJ30 v4.5 | 1.00% | **0.70%** ← drift (R1+R2) | **0.7%** ← drift (R3) |
| Striker NAS100 v1 | 0.40% | **0.37%** ← drift (R2) | **0.45%** ← drift (R1) |
| Guardian Gold v5.5 | 0.34% | 0.34% ✓ | 0.34% ✓ |
| Aegis USDJPY v4.3 | 1.50% | 1.5% ✓ | 1.50% ✓ |

Three observations worth promoting to methodology lessons:

1. **Per-file drift accumulation.** For Striker NAS100, three different
   numbers (`0.37` strategy / `0.40` locked / `0.45` indicator) for the
   same parameter across two files. Editing one didn't propagate to the
   other, and neither file matched the locked value. The validator's
   "check both" extension (Round 2) was load-bearing for catching the
   indicator drift — without it, fixing only the strategy file would
   have left the indicator silently wrong.
2. **Tooltip-vs-default decoupling is the dominant pattern.** All four
   drifted files have tooltips that correctly cite the locked value
   ("LOCKED: 1.00%", "LOCKED v1.0: 0.40%"). The drift is between the
   `input.float(<default>, ...)` and the tooltip on the same line. The
   user must override per the tooltip cue on every fresh TV attach.
3. **Round-trip persistence is human-loop only.** Round 1's fix to
   `Downloads/dj30.txt` was reverted between rounds by a fresh TV
   re-export. Mirroring corrected bytes to `Downloads/` does NOT
   propagate to TradingView's cloud source. The gate works (validator
   catches re-introduced drift on every commit), but the fix needs to
   land in TV's editor to stop the cycle.

### Round 3 verification

```bash
$ python scripts/validate_params.py
Summary: 0 HARD violation(s), 0 WARN violation(s)
Runtime: 70.8 ms

$ python scripts/validate_params.py --self-test-only
Self-test OK (good: 0 hard / 1 warn; bad: 2 hard / 1 warn)

$ ls strategies/{guardian,striker,aegis,nas}/*.pine | wc -l
8    # full canonical set per strategies/MANIFEST.sha256
```
