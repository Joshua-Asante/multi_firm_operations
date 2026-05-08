# Repo Context — prop_firm_pipeline

**Maintainer:** Claude Code (refresh authority); Joshua (trigger authority); web Claude (read-only consumer)
**Initial population:** 2026-05-07
**Source spec:** authored 2026-05-07 by web Claude (parent session); destination this Notion page (`32cdc0b53c1181b8a18cce1401a4f8e8`).

This section is the canonical architecture-truth surface for web Claude when authoring briefs against `prop_firm_pipeline`. It is **not** a codebase backup, a status dashboard, or a substitute for CC's §0. It primes brief authoring; CC's §0 remains the truth gate at execution.

---

## §1 — Active file tree
_Last refreshed: 2026-05-08_

```
prop_firm_pipeline/
├── accounts.py                                       # Account dataclass + multiplier calc
├── cli.py                                            # add / update / status / lots / tearsheet
├── csv_parser.py                                     # DXTrade CSV → trade-level normaliser
├── firm_rules.py                                     # _BASE_RISK + per-firm meta (FXIFY only canonical)
├── dd_protection.py                                  # portfolio DD scaler — Q-DDP-1 LOCKED 2026-05-06
├── portfolio_mc.py                                   # canonical lock-decision MC (Pepperstone default)
├── mc_explore.py                                     # exploratory; explicitly NOT for locks
├── CLAUDE.md                                         # canonical project doc
├── README.md, CHANGELOG.md, REPO_MAP.md              # root meta
├── pyproject.toml                                    # flat py-modules layout (no package namespace)
│
├── lib/
│   ├── mvd.py                                        # assert_min_rows / assert_window / assert_no_fallback / assert_tv_export / assert_guard_fired
│   ├── nonlinear.py                                  # H-stat / Hurst on log returns (post r-s-on-log-prices fix)
│   ├── oanda.py, oanda_creds.py                      # OANDA REST client + cred loader
│   └── tearsheet.py                                  # quantstats wrapper used by `cli.py tearsheet`
│
├── strategies/                                       # Pine v6 — LOCKED, do not edit
│   ├── guardian/
│   │   ├── guardian_gold_v5.5.pine                   # LOCKED 2026-04-23 (v5.5)
│   │   └── guardian_CHANGELOG.md
│   ├── striker/
│   │   ├── striker_dj30_v4.5.pine                    # LOCKED 2026-05-05 (v4.4 archived)
│   │   ├── striker_nas100_v1.pine                    # LOCKED 2026-05-05 (operational 2026-05-07)
│   │   └── striker_CHANGELOG.md
│   └── aegis/
│       ├── aegis_usdjpy_v4.3.pine                    # LOCKED 2026-04-22
│       └── aegis_CHANGELOG.md
│
├── scripts/
│   ├── build_us_releases.py                          # release calendar builder
│   ├── dryrun_aegis_v4_3.py                          # MVD-helper exercise / sanity gate
│   ├── fetch_oanda_bars.py                           # hard-coded USDJPY/XAUUSD/US30USD only
│   ├── lock_event_hook.py                            # post-lock hook
│   └── run_v55_validation.py                         # [?] template-vs-one-shot disposition open
│
├── live_journal/                                     # signal-vs-fill reconciliation runtime; skill ↔ repo runtime mirror
│   ├── scripts/
│   │   ├── journal_review.py                         # canonical reconciliation pipeline
│   │   └── m7_anticipation_gap_backfill.py           # M-7 Route A backfill (sibling-imports journal_review)
│   ├── references/
│   │   └── execution_lessons.md                      # E1/E2 anchor registry
│   └── data/                                         # gitignored DXTrade exports + journal outputs (.gitkeep retained)
│
├── tests/                                            # CI-load-bearing
│   ├── test_mc_anchors.py                            # MC headline pinning (4-strategy 97.88/0.22/4.55)
│   ├── test_mvd_selfchecks.py                        # MVD helper assertions
│   ├── test_nonlinear.py                             # H-stat / R-S correctness
│   ├── test_oanda.py, test_oanda_gate.py             # OANDA loader + two-tier-canonical gate
│   ├── test_tearsheet.py                             # HTML smoke
│   └── test_tv_export_loader.py                      # MVD identity gate on TV exports
│
├── data/
│   ├── tv_exports/pepperstone/                       # canonical MC inputs (4 panels + SHA256SUMS)
│   ├── tv_exports/oanda/                             # secondary panels (3 panels; no NAS)
│   ├── bar_data/                                     # active bars (XAUUSD, USDJPY, US30USD) + vendor panels (EUR/GBP/USDCHF/USOIL)
│   ├── external/                                     # dxy.csv + us_high_impact_0830et_2022_2026.csv
│   ├── reconciles/                                   # 2026-05-05_guardian_n_reconcile.md
│   └── *.sha256                                      # pinned hashes
│
├── analysis/
│   ├── Q-DJ30-1/, Q-DJ30-2/, Q-DJ30-3/               # closed 2026-05-06; cooldown to ~2026-05-20
│   ├── striker_nas100/                               # placeholder __init__.py (Q-NAS-1 archived)
│   ├── oanda_stage1/                                 # stage-1 OANDA findings package
│   ├── dd_protection_trace.py                        # [?] forensic-tool-vs-one-shot disposition open
│   └── time_to_pass.py                               # [?] reusable-vs-one-shot disposition open
│
├── docs/
│   ├── rule_0.md                                     # Rule 0 — audit-first methodology
│   ├── operational_rules.md                          # incl. doc/code skew audit trigger
│   ├── methodology/                                  # 1r_estimation, observation_routing, regime_robustness_gate
│   │   ├── findings/                                 # 2026-05-02 (oanda_stage1, eurusd_lnyo, usoil) + 2026-05-06 (dj30 *)
│   │   └── gate_audits/                              # 2026-05-06 Q-DJ30-2 + Q-DJ30-3 audits
│   ├── adr/                                          # IMMUTABLE record (2026-03-01 → 2026-05-03)
│   ├── briefs/                                       # active: Q-DDP-1, Q-DJ30-3, bust_attribution_flip, NAS100 (×2)
│   ├── historical/                                   # IMMUTABLE record
│   ├── templates/                                    # bust_analysis, calibration_brief, lock_decision
│   └── striker_nas100/                               # q_nas_2_capture_plan.md (Q-NAS-2 OPEN)
│
├── archive/                                          # consolidated 2026-05-07 (Approach D)
│   ├── analysis/                                     # eurusd_lnyo, gbpusd_lon, usdchf_sentinel, usoil, striker_nas100/q_nas_1
│   ├── strategies/striker/                           # striker_dj30_v4.4.pine, striker_nas100_v1_research.pine
│   ├── data/tv_exports/                              # USOIL_pepperstone_*.csv
│   └── docs/methodology/archive/                     # full retired methodology + msee/_active_paths_2026-05-07/ + overlays/guardian_conflict_risk.md
│
└── .claude/, .github/                                # commands (lock-check, mc-anchors, skew-audit) + CI workflows (pylint, tests)
```

Conventions: REPO_MAP.md classifies every active path as `[A]` active / `[U]` utility / `[X]` archived / `[?]` open question. The five `[?]` items above are the live disposition queue (see §6).

---

## §2 — Production module summary
_Last refreshed: 2026-05-07_

### `firm_rules.py`
- **Purpose:** firm metadata + risk-tier dict. Both axes (firm and phase) collapse: only FXIFY is fully populated; challenge phase = funded phase by construction.
- **Key data:** `_BASE_RISK = {"guardian": 0.0034, "striker": 0.0100, "aegis": 0.0150, "striker_nas100": 0.0040}`. `RISK_TIERS = {phase: _BASE_RISK for phase in ("challenge", "funded")}`. `BASELINE_BALANCE = 200_000`. FXIFY firm dict has `dd_type, max_dd_pct, daily_loss_pct, profit_target_pct, min_trading_days, news_trading, weekend_holds`.
- **Does NOT contain:** per-firm strategy schemas, active_days, session windows, contractValue, soft-stops, ATR overrides. Those live in **Pine** (the indicators are LOCKED). Do not propose adding them here.

### `accounts.py`
- **Purpose:** `Account` dataclass + `get_multipliers(account)` → dict keyed by strategy ID, returning per-strategy multiplier vs the $200K baseline. Persistence is on-demand (JSON list at `data/accounts.json`); the file may not exist (currently absent).
- **Key data:** `Account` fields = `account_id, firm, phase, balance, initial_balance, dd_limit_pct, profit_target_pct`. No per-strategy state, no fills. Properties: `dd_remaining_pct`, `target_remaining`, `flags`.
- **Multiplier formula:** `(balance × tier[strategy]) / (200_000 × baseline_risk[strategy])`, floored to 2dp. Because `tier == BASELINE_RISK` under unified allocations, the per-strategy variation cancels — multipliers are equal across strategies for a given account (open observation, not a bug; see §6).
- **Does NOT contain:** per-strategy fills tracking, active flags, P&L history, broker integration. The `firm_rules.FIRM_RULES` lookup auto-fills DD/target on `add_account`.

### `dd_protection.py`
- **Purpose:** portfolio-level risk scaler. When `(peak − equity)/peak ≥ 0.010`, multiplies all strategies' base risk by `0.40×`. Clears at peak.
- **Key data:** `BASE_RISK = {"Guardian": 0.0034, "Striker": 0.0100, "Aegis": 0.0150, "Striker NAS100": 0.0040}` (**Title-case**, intentional vs `firm_rules` lowercase). `DD_TRIGGER = 0.010`, `DD_SCALE = 0.40` — Q-DDP-1 LOCKED 2026-05-06. State persisted to `dd_protection_state.json` (currently absent).
- **MVD self-check at import:** two-layer (boundary + literal pin). Any change to either constant must update both the constant and the literal pin in the same commit, tied to a re-MC run (per 2026-04-24 ADR).
- **Does NOT contain:** monitored-strategies set (flat scaler over all in `BASE_RISK`), active-day gating, fills tracking, per-strategy DD logic, intraday triggers. Single tier only — equity tier deleted 2026-04-17.
- **Note:** Windows console emits `cp1252` decode error on `✅` / `📈` / `⚡` print lines — workaround: `PYTHONIOENCODING=utf-8` (live in `.claude/settings.json`). ASCII-replacement is on the queue (§6).

### `cli.py`
- **Purpose:** subcommand dispatcher. Subcommands: `add`, `update`, `status`, `lots`, `tearsheet`. `update` supports `--from-oanda` (NAV from OANDA REST) but only for accounts with `firm == "OANDA"` AND matching `~/.keys/oanda.txt` cred — the two-tier canonical guard.
- **Key data / signatures:**
  - `cmd_add(account_id, firm, balance, --phase=challenge)`
  - `cmd_update(account_id, [balance], --from-oanda)` (balance optional iff `--from-oanda`)
  - `cmd_status` — no args, prints account table
  - `cmd_lots` — no args, prints 4-column multiplier card (G / S / A / N)
  - `cmd_tearsheet(csv_path, --out, --starting-equity=200000, --title)`
- **Does NOT contain:** ATR flags, date-selector args, active-day suppression, fill recording, per-strategy `--enable`/`--disable`. Pine handles ATR + per-bar lot sizing live.

### `portfolio_mc.py`
- **Purpose:** Monte Carlo challenge-outcome simulator. Pepperstone is the canonical lock anchor; OANDA is pattern-spotting proxy. 10K sims × 3 seeds × 150-day horizon, week-block bootstrap.
- **Key data:**
  - `ALLOCATIONS = {"guardian": 0.0034, "striker": 0.0100, "aegis": 0.0150, "striker_nas100": 0.0040}`
  - `STARTING_EQUITY = 200_000`, `PROFIT_TARGET = 210_000`, `DAILY_LOSS_PCT = -0.05`, `STATIC_DD_PCT = -0.05`, `MIN_TRADING_DAYS = 5`, `HORIZON_DAYS = 150`, `SIMS_PER_SEED = 10_000`, `SEEDS = (42, 123, 2026)`
  - `PEPPERSTONE_PANELS` (4 strategies, all v-current) + `OANDA_PANELS` (3 strategies, DJ30 still v4.4)
  - `EXPECTED_VERSIONS_BY_BROKER` — Pepperstone = v5.5/v4.5/v4.3/v1; OANDA = v5.5/v4.4/v4.3
- **MVD gates:** `assert_tv_export` (filename identity), `assert_min_rows` (≥100 raw rows), `assert_window` (≥4yr panel ±60d), `assert_no_fallback` on aggregated `implied_1r` fallback count.
- **Anchor pinned by:** `tests/test_mc_anchors.py` (4-strategy 97.88/0.22/4.55, p99 DD 4.55%, attribution DJ30 40.9% / G 25.8% / A 22.7% / NAS 10.6%).
- **Does NOT contain:** per-firm scaling, live-deploy logic, allocation tuning. Read-only simulation against frozen panels.

---

## §3 — Schema surface
_Last refreshed: 2026-05-07_

Copyable as-of source. CC pastes actual current values, not summaries.

### `firm_rules._BASE_RISK`
```python
_BASE_RISK = {
    "guardian":       0.0034,   # 0.34%
    "striker":        0.0100,   # 1.00% (DJ30)
    "aegis":          0.0150,   # 1.50%
    "striker_nas100": 0.0040,   # 0.40%
}
RISK_TIERS = {phase: _BASE_RISK for phase in ("challenge", "funded")}
BASELINE_BALANCE = 200_000
BASELINE_RISK = RISK_TIERS["challenge"]
```

### `firm_rules.FIRM_RULES["FXIFY"]`
```python
{
    "dd_type": "static",
    "max_dd_pct": 5.0,
    "daily_loss_pct": 5.0,
    "profit_target_pct": 5.0,
    "min_trading_days": 5,
    "news_trading": True,
    "weekend_holds": True,
}
```
Other firm slots (FundedNext, The5ers, BrightFunded) exist as commented stubs only.

### `accounts.Account`
```python
@dataclass
class Account:
    account_id: str
    firm: str
    phase: str               # challenge | funded | scaling | failed
    balance: float
    initial_balance: float
    dd_limit_pct: float
    profit_target_pct: float
    # properties: dd_remaining_pct, target_remaining, flags
```

### `accounts.get_multipliers`
Returns `dict[str, float]` keyed by strategy ID:
```python
{"guardian": float, "striker": float, "aegis": float, "striker_nas100": float}
```

### `dd_protection.BASE_RISK` (Title-case — note divergence from `firm_rules` lowercase)
```python
BASE_RISK = {
    "Guardian":       0.0034,
    "Striker":        0.0100,
    "Aegis":          0.0150,
    "Striker NAS100": 0.0040,
}
DD_TRIGGER = 0.010   # Q-DDP-1 LOCKED 2026-05-06 — joint edit + re-MC required
DD_SCALE   = 0.40    # Q-DDP-1 LOCKED 2026-05-06 — joint edit + re-MC required
```

### `dd_protection.calculate_protection`
- **Input:** `equity: float, peak: float`
- **Output:** `{"dd_from_peak": float, "dd_triggered": bool, "multiplier": 1.0|0.40, "rule": str, "scaled_risk": dict[str, float]}`

### `cli` subcommand argspec (current)
```
add      <account_id> <firm> <balance> [--phase challenge|funded|scaling|failed]
update   <account_id> [<balance>] [--from-oanda]
status   (no args)
lots     (no args)
tearsheet <csv_path> [--out <path>] [--starting-equity 200000] [--title <str>]
```
No `--atr-*`, no `--date`, no `--strategy`, no `record-fill`. Per-bar sizing is in Pine.

### `portfolio_mc.ALLOCATIONS`
```python
ALLOCATIONS = {
    "guardian":       0.0034,
    "striker":        0.0100,
    "aegis":          0.0150,
    "striker_nas100": 0.0040,
}
STRATS = ("guardian", "striker", "aegis", "striker_nas100")
```

---

## §4 — Strategy lock state matrix (2-axis)
_Last refreshed: 2026-05-07_

| Strategy | Code-lock | Live-deploy (FXIFY) | Live-deploy (FundedNext) | Live-deploy (The5ers) | Live-deploy (BrightFunded) |
|---|---|---|---|---|---|
| Guardian Gold v5.5 | LOCKED 2026-04-23 | not tracked in repo¹ | not active | not active | not active |
| Striker DJ30 v4.5 | LOCKED 2026-05-05 | not tracked in repo¹ | not active | not active | not active |
| Aegis USDJPY v4.3 | LOCKED 2026-04-22 | not tracked in repo¹ | not active | not active | not active |
| Striker NAS100 v1 | LOCKED 2026-05-05 | operational tooling integrated 2026-05-07² | not active | not active | not active |

¹ `data/accounts.json` is currently absent — there is no on-disk record of which accounts are live or when each strategy was deployed against them. The repo treats live-deploy as out-of-scope state. **If web Claude needs a live-deploy date, ask Joshua directly.**
² NAS100 v1 was code-locked 2026-05-05; operational integration (firm_rules / dd_protection / accounts / cli all carrying the strategy) landed 2026-05-07. DXTrade `contractValue=10` broker-verified 2026-05-07.

**Per-strategy DXTrade `contractValue`:**
| Strategy | contractValue | Verified |
|---|---|---|
| Guardian Gold | 100 | (date not in repo) |
| Striker DJ30 | 10 | (date not in repo — critical: default 1 gives ~7% risk) |
| Aegis USDJPY | default (1) | (date not in repo) |
| Striker NAS100 v1 | 10 | 2026-05-07 |

---

## §5 — Pytest baseline
_Last refreshed: 2026-05-07_

- **Pass count:** 31 passed, 2 warnings, 71.97s
- **Last baseline run:** 2026-05-07 (this refresh)
- **Test files (7):**
  - `test_mc_anchors.py` — 4-strategy MC headline pin (97.88/0.22/4.55)
  - `test_mvd_selfchecks.py` — MVD helper assertions
  - `test_nonlinear.py` — Hurst/R-S correctness on log returns
  - `test_oanda.py`, `test_oanda_gate.py` — OANDA loader + two-tier-canonical gate
  - `test_tearsheet.py` — HTML smoke (only test with warnings: seaborn `vert:` PendingDeprecation, ×2)
  - `test_tv_export_loader.py` — MVD identity gate on TV exports
- **No operational-tooling unit tests** for `firm_rules / accounts / dd_protection / cli`. All four are exercised at import (MVD self-checks fire at module load) and via integration paths through `portfolio_mc.py` and `lib.tearsheet`. Do not propose "extend tests for X" against these unless the brief defines what the test should pin.

---

## §6 — Pending decisions queue (carry-forward)
_Last refreshed: 2026-05-08_

**Time-gated:**
- **Q-DJ30-1/2/3 archive move** → ~2026-05-20 (2-week cooldown from 2026-05-06 closures). Currently still under `analysis/`.

**Awaiting Joshua's disposition (5 items, REPO_MAP `[?]` flagged):**
- `archive/strategies/striker/striker_dj30_v4.4.pine` — keep until OANDA mirror regenerates against v4.5, OR regen + delete in one transaction. Currently load-bearing for `OANDA_PANELS["striker"]` filename token.
- `scripts/run_v55_validation.py` — template-shape (rename to generic) or one-shot (archive).
- `analysis/dd_protection_trace.py` — reusable forensic tool or one-shot trace.
- `analysis/time_to_pass.py` — recurring re-MC reporting tool (wire into trigger checklist) or one-shot.
- `analysis/oanda_stage1/` — closed (archive + clear `data/bar_data/` cache delete) or paused (keep both). Findings already in `docs/methodology/findings/2026-05-02_oanda_stage1_*`.

**Authoring queue (parent-session pending):**
- Methodology lesson capture — 4 anchors flagged this conversation:
  - §0 sub-rule formalization (cross-ref grep + archive convention check + ±20-line context read)
  - Path-A-vs-Path-B architecture-shape lesson (operational integration was 10 lines across 5 files, not the imagined per-firm schema rebuild)
  - Lock-procedure operational-tooling integration phase (Pine + manifest + MC ≠ live; add checklist item)
  - This Repo Context section itself (the artifact closing the loop)
- `archive/README.md` orientation index — after DJ30 cooldown move lands.

**Small infrastructure:**
- Windows console emoji bug (`dd_protection.py:201`) — `PYTHONIOENCODING=utf-8` workaround live; ASCII-replacement is a 5-min task.
- Multiplier-equal-across-strategies design observation (formula cancels per-strategy risk under unified allocations) — confirm whether per-strategy multiplier divergence is ever expected; if no, document the cancellation and consider simplifying `get_multipliers` to a single value.

**live_journal subtree (added 2026-05-08):**
- **CI test policy.** No unit tests currently exercise `live_journal/scripts/`. Three options:
  (a) extend `tests/` with `test_journal_review.py` pinning loader behavior + edge-captured ratio computation against synthetic DXTrade fixtures;
  (b) treat live_journal as runtime tooling, no unit tests, rely on integration runs against weekly DXTrade exports;
  (c) hybrid — unit tests for pairing logic only (pure function), nothing for I/O paths.
  Joshua to decide before any production use.
- **execution_lessons.md sync policy.** Two copies now exist: skill-bundle `references/execution_lessons.md` (CC context-loading canonical, currently at the local-agent-mode sandbox path — ephemeral) and `live_journal/references/execution_lessons.md` (repo runtime, durable). When a new E-entry is added, which is source of truth and how does the other update? Mirrors the brief-authoring SKILL.md ↔ Notion §7 sync clause; same failure mode. Note: because the skill bundle lives in a session-ephemeral sandbox, the repo copy is the de-facto durable canon — sync direction proposal: edit repo, propagate to skill bundle on next session install.
- **m7 backfill execution.** Script in place but not yet run end-to-end against real DXTrade fills. Until run, M-7 lesson status remains CANDIDATE. Schedule for next weekly review (target: 2026-05-11 morning, before live NAS100 first fill at 13:00 UTC). Verdict updates `execution_lessons.md` registry; on-disk lesson-file capture deferred per §0.C C3 verdict (no `docs/methodology/lessons/` registry exists yet for M-1..M-6).

CC adds new items as they surface; Joshua resolves or graduates them out.

---

## §7 — Methodology canon (Rule 0 sub-rules)
_Last refreshed: 2026-05-08_

Active sub-rules from prior lesson captures, applied at brief-authoring time AND at CC §0 execution time:

1. **Cross-reference grep before classifying "isolated cruft."** For each candidate move/delete, run `grep -rn <basename>` across active paths and report N callers in §0. If N > 3, classify as "doctrine-referenced cruft" rather than "isolated cruft" — the move still goes through but the cross-ref repair budget is non-trivial. _(Anchored: Simplify-pass cross-ref miss, 2026-05-07.)_
2. **Archive convention verification.** For any move targeting an archive, §0 must read REPO_MAP.md's Archive section and report whether the brief's destination convention matches the existing tree. _(Anchored: Simplify-pass parallel-archive near-miss, 2026-05-07.)_
3. **Rule 0 reads must include surrounding context.** When a brief cites a specific line, §0 reads the surrounding section (±20 lines minimum), not the line in isolation. Disambiguating qualifiers often live nearby. _(Anchored: NAS100 drift fix brief CLAUDE.md:48-vs-50 miss, 2026-05-07.)_
4. **Architecture truth before edit prescription.** For briefs that prescribe edits to production code web Claude has not seen in the current conversation, §0 reads the *actual architecture* (module purposes, schemas, function signatures) and CC proposes the *edit shape* in the §0 report; Joshua confirms before §2 execution. The "web Claude prescribes specific edits, CC executes" pattern is reliable only when web Claude's mental model matches the codebase. _(Anchored: lock-NAS100-live Path A vs Path B, 2026-05-07.)_
5. **Lock procedures need an operational-tooling integration phase.** Pine + manifest + MC ≠ live. A lock is not complete until operational tooling (`firm_rules / dd_protection / accounts / cli`) reflects the new strategy. Future lock memos include an "operational tooling integrated" checklist item before declaring lock complete. _(Anchored: NAS100 v1 lock 2026-05-05 vs operational integration 2026-05-07 gap.)_
6. **Live-execution claims require edge-captured citation.** When a brief asserts that a strategy is performing as designed in live trading, or proposes any change motivated by live execution behavior, §0 must cite the most recent `journal_review.py` output (edge-captured ratio + version-mixed flag + the date window the report covers). A claim of "I'm trading the system" without this citation is unverified — see execution lessons E1 (2026-04-07 Guardian skip, $3,752 counterfactual) and E2 (2026-04-15 Aegis decomposition, $6,100 gap). _(Anchored: 2026-04-29 honesty audit; methodology layer was 6× more cited than execution layer in briefs over a 7-week sample.)_

This list grows as lessons capture; web Claude consults it during brief authoring.

---

## §8 — Cross-references that web Claude routinely needs
_Last refreshed: 2026-05-08_

- **Notion Command Center page:** `32cdc0b53c1181b8a18cce1401a4f8e8`
- **INQHIORI ⊕ OODA framework page:** `34ddc0b53c1181479d7bdecc61f47078`
- **Dev-phase archive page:** `358dc0b53c11814f8b70c95fd25ec906`
- **DD-protection FINAL decision:** `https://www.notion.so/346dc0b53c11816085bbf2292be934cc`
- **Allocations source-of-truth:** `https://www.notion.so/346dc0b53c1181d1b8d5e12df4bd3810`
- **Repo manifest:** `REPO_MAP.md` (root)
- **Project doc:** `CLAUDE.md` (root)
- **Lock memos location:** `docs/briefs/<strategy>_<version>_lock.md` or `docs/briefs/striker_nas100_q_nas_3_mc_addition.md`-style
- **ADR location:** `docs/adr/`
- **Methodology archive:** `archive/docs/methodology/archive/` (full retired methodology — INQHIORI ⊕ The Algorithm, Pre-Q gates, MVD framing; 90-day review gate 2026-07-29)
- **Methodology findings (active):** `docs/methodology/findings/`
- **Gate audits (active):** `docs/methodology/gate_audits/`
- **Live execution journal scripts:** `live_journal/scripts/journal_review.py`, `live_journal/scripts/m7_anticipation_gap_backfill.py`
- **Execution lessons registry:** `live_journal/references/execution_lessons.md`
- **Skill bundle (live-execution-journal):** `~/AppData/Roaming/Claude/local-agent-mode-sessions/skills-plugin/<session-id>/skills/live-execution-journal/` (sandbox path, ephemeral; repo `live_journal/` is the durable runtime)

---

## §9 — Refresh trigger contract
_Last refreshed: 2026-05-07_

CC refreshes the relevant section on each trigger. Multiple sections may refresh on a single trigger.

| Trigger | Sections to refresh |
|---|---|
| Any structural repo change (file move, rename, delete, new module) | §1 (file tree), §8 if a referenced path moved |
| Any production-code edit (firm_rules, accounts, dd_protection, cli, portfolio_mc) | §2 (module summary), §3 (schema surface) |
| Any lock event (Pine source promotion, MC re-lock, allocation lock) | §4 (lock matrix), §6 (queue updates) |
| Any live-deploy event (broker contractValue verification, strategy goes live, strategy goes offline) | §4 (lock matrix) |
| Any pytest-affecting change (new test, removed test, baseline run) | §5 (pytest baseline) |
| Any methodology lesson capture | §7 (canon) |
| Any new pending decision or resolved decision | §6 (queue) |
| Any cross-reference path change (Notion ID, important repo path) | §8 (cross-refs) |
| Any §7 sub-rule edit (added, removed, substantively reworded) | brief-authoring SKILL.md sub-rules subsection — see sync clause below |

**Manual refresh:** Joshua triggers a full refresh by asking CC "refresh repo context" — useful as a periodic sanity-check (e.g., monthly).

**Drift detection:** If web Claude flags a section as stale during brief authoring (a referenced file is missing per CC's §0, a schema doesn't match), Joshua triggers a targeted refresh of the affected section.

**SKILL.md sync clause.** Notion §7 is canonical for the sub-rule substance. The brief-authoring skill carries a generalized propagation in its "Rule 0 sub-rules — context scope" subsection (`~/.claude/skills/brief-authoring/SKILL.md` user-override; the published `anthropic-skills:brief-authoring` is upstream-only and not edited directly). When §7 is edited, propagate to SKILL.md in the same conversation; when SKILL.md drifts first, re-sync to §7. Drift between the two surfaces means web Claude reads divergent canons during brief authoring — the failure this section was built to prevent.

**On-disk source for this section:** `docs/notion/repo_context.md` — CC edits this file in place; Joshua copy-pastes to Notion. Treating the on-disk file as the canonical pre-publish surface (versioned, diff-able) avoids the "Notion edit then forget to update repo" failure mode.

---

## §10 — What this section is NOT

- **NOT a backup of the codebase** — git is the backup. This section is for shape, not content.
- **NOT a full schema dump** — only the schemas that web Claude has actually gotten wrong or is likely to. New schemas are added when a brief failure shows they're needed.
- **NOT a project status dashboard** — strategy lock matrix tracks operational state, not project progress narratives.
- **NOT a substitute for CC's §0** — CC still reads the actual files at execution time. This primes the brief; §0 is the truth gate.
- **NOT a replacement for ADRs or methodology archive** — those are decision records; this is a current-state snapshot.

If a future brief failure surfaces a category of context not covered here, the spec extends. The discipline is *grow on evidence, not speculation.*
