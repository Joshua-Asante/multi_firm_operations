# Issue #54 — ULP-Precision Comparison Audit (survey output)

**Spec**: `docs/spec/issue_54_survey_brief.md` (commit `d46a76f`)
**Spawn date**: 2026-05-10
**Status return**: `DONE_WITH_CONCERNS`
**Instance count**: 17

## Totals

| Bucket | Count |
|---|---:|
| `var_type=money` | 5 |
| `var_type=ratio` | 11 |
| `var_type=time` | 0 |
| `var_type=count` | 0 |
| `var_type=other` | 1 |
| `ulp_vulnerable=yes` | 2 |
| `ulp_vulnerable=no` | 11 |
| `ulp_vulnerable=unclear` | 4 |

## §0 Rule-0 read anchors

| Path | Git hash | Timestamp | Status |
|---|---|---|---|
| `dd_protection.py` | `6c7fa54` | 2026-05-10T10:36:42 | READ |
| `docs/adr/2026-05-10-dd-protection-ulp-rounding.md` | `0b2bdab` | 2026-05-10T11:18:38 | READ |
| `accounts.py` | `b546655` | 2026-05-07T20:40:19 | READ |
| `firm_rules.py` | `cd58bb9` | 2026-05-10T00:45:56 | READ |
| `portfolio_mc.py` | `54d2285` | 2026-05-10T12:58:04 | READ |
| `analysis/time_to_pass.py` | `2567b15` | 2026-05-08T18:16:20 | READ |
| `analysis/oanda_stage1/` | n/a | 2026-05-10 | READ — null finding (research/Stage-1 hypothesis-generation, no equity/DD/risk-control comparisons) |
| `weekly_review_feeder/` | n/a | 2026-05-10 | READ — null finding (no equity/DD/risk-control comparisons; categorization/reporting only; `dd_wrapper` is `NotImplementedError` stub) |
| `fxify_rule_validator.py` | `65f5829` | 2026-05-10T11:17:22 | OUT-OF-SCOPE |

**Out-of-scope confirmation**: `fxify_rule_validator.py` confirmed out of scope per #54.

## ADR precision-rule quote (verbatim, §0)

> Validator at 2 dp is correct for money math: floor, target, equity all live at the cent scale, and round(x, 2) matches the natural quantum of the variable.
> dd_from_peak is a ratio, not money. It has no cent quantum. The natural fineness is the smallest drawdown distinction the trader cares about — empirically, no DD policy resolves below 1 bp (10^-4). Rounding finer than 1 bp is sufficient.
> 6 dp = ~10^-6 = micro-percent precision. Eight orders of magnitude above float64 ULP at 0.015. Two orders of magnitude finer than any DD policy. Sufficient to collapse ULP noise without affecting any decision the trader could meaningfully care about.

## Findings (one row per comparison site; §8 schema)

| # | file | line | expression | lhs_var | op | rhs | var_type | current_treatment | ulp_vulnerable | recommended_treatment | notes (short) |
|--:|---|---:|---|---|:-:|---|---|---|---|---|---|
| 1 | dd_protection.py | 92 | `dd_triggered = round(dd_from_peak, 6) >= DD_TRIGGER` | `round(dd_from_peak, 6)` | `>=` | `DD_TRIGGER (=0.015)` | ratio | round(x,6) | no | round(x,6) | Canonical fix site (PR #53). Already rounded per ADR. Reference baseline. |
| 2 | dd_protection.py | 202 | `if dd_from_start >= 0.04:` | `dd_from_start` | `>=` | `0.04` | ratio | raw_float | yes | round(x,6) | dd_from_start = (STARTING_EQUITY - equity)/STARTING_EQUITY — same subtraction-at-near-equal pattern as dd_from_peak. RAW. |
| 3 | dd_protection.py | 205 | `elif dd_from_start >= 0.03:` | `dd_from_start` | `>=` | `0.03` | ratio | raw_float | yes | round(x,6) | Second branch of same ladder. §0.5 (4): distinct site. |
| 4 | dd_protection.py | 295 | `if equity > state["peak_equity"]:` | `equity` | `>` | `state["peak_equity"]` (JSON-stored float) | money | raw_float | unclear | unclear | Peak-update path. RHS not a constant threshold — partially fails §4 schema. JSON round-trip introduces precision mutation. Classified `unclear` per §5 (4). |
| 5 | accounts.py | 43 | `if self.dd_remaining_pct <= 0:` | `self.dd_remaining_pct` (property: `round(.., 2)`) | `<=` | `0` | ratio | round(x,2) | no | round(x,2) | Property already rounded at 2 dp; 2dp vs 6dp ratio-rule mismatch (see concern #1). |
| 6 | accounts.py | 45 | `elif self.dd_remaining_pct < 1.5:` | `self.dd_remaining_pct` | `<` | `1.5` | ratio | round(x,2) | no | round(x,2) | Same property. Same precision-rule mismatch flag. |
| 7 | accounts.py | 47 | `if self.target_remaining <= 0 and self.profit_target_pct > 0:` (first op) | `self.target_remaining` (property: `round(.., 2)`) | `<=` | `0` | money | round(x,2) | no | round(x,2) | Money-typed (cents); matches ADR 2dp rule. §0.5 (4): second op (`profit_target_pct > 0`) is sentinel-zero on non-arithmetic LHS, excluded. |
| 8 | accounts.py | 162 | `if a.dd_remaining_pct <= 0 and a.phase != "failed":` (first op) | `a.dd_remaining_pct` | `<=` | `0` | ratio | round(x,2) | no | round(x,2) | Account-state transition: phase -> "failed". Composite per §0.5 (4); second op is `!=`, excluded. |
| 9 | portfolio_mc.py | 145 | `full_stops = abs_losses[abs_losses > 0.01 * account]` | `abs_losses` (Series elementwise) | `>` | `0.01 * account (=2000.0)` | money | raw_float | unclear | round(x,2) | 1R calibration mask. Drives implied_1r; ~10pp MC swing per user-memory fallback trap. Boundary case (loss exactly $2000) plausible. |
| 10 | portfolio_mc.py | 198 | `scale = dd_scale if round(dd_from_peak, 6) <= -dd_trigger else 1.0` | `round(dd_from_peak, 6)` | `<=` | `-dd_trigger` | ratio | round(x,6) | no | round(x,6) | MC sim DD-trigger mirror of dd_protection.py:92. Already rounded per Q-MCFP-1. Reference. |
| 11 | portfolio_mc.py | 203 | `if round(pnl / STARTING_EQUITY, 6) <= DAILY_LOSS_PCT:` | `round(pnl / STARTING_EQUITY, 6)` | `<=` | `DAILY_LOSS_PCT (=-0.05)` | ratio | round(x,6) | no | round(x,6) | Daily-loss bust gate. Already rounded. Reference. |
| 12 | portfolio_mc.py | 205 | `if round((eq_new - STARTING_EQUITY) / STARTING_EQUITY, 6) <= STATIC_DD_PCT:` | `round((eq_new - STARTING_EQUITY) / STARTING_EQUITY, 6)` | `<=` | `STATIC_DD_PCT (=-0.05)` | ratio | round(x,6) | no | round(x,6) | Static-DD bust gate. Already rounded. Reference. |
| 13 | portfolio_mc.py | 217 | `if round(eq, 2) >= PROFIT_TARGET and trade_days >= MIN_TRADING_DAYS:` (first op) | `round(eq, 2)` | `>=` | `PROFIT_TARGET (=210_000)` | money | round(x,2) | no | round(x,2) | Profit-target pass gate. Already rounded at 2dp (money). §0.5 (4): second op is int-typed, excluded. |
| 14 | portfolio_mc.py | 501 | `if not no_protection and round(dd_from_peak, 6) <= -dd_trigger:` | `round(dd_from_peak, 6)` | `<=` | `-dd_trigger` | ratio | round(x,6) | no | round(x,6) | Mirror of line 198 in mode_historical. Already rounded. Reference. |
| 15 | portfolio_mc.py | 510 | `if outcome == "pass" and round(eq, 2) >= PROFIT_TARGET:` (second op) | `round(eq, 2)` | `>=` | `PROFIT_TARGET` | money | round(x,2) | no | round(x,2) | Profit-target gate in mode_historical. §0.5 (4): first op is `==`, excluded. |
| 16 | analysis/time_to_pass.py | 100 | `if delta_pp > 2.0:` | `delta_pp` (= `abs(pass_rate - 0.9809) * 100`) | `>` | `2.0` | other | raw_float | unclear | unclear | Drift-band gate halts Notion-post when MC pass-rate drifts >2pp from C2 anchor. Operational, not live-trade. `other` per §4 (pp-typed). |
| 17 | analysis/time_to_pass.py | 204 | `both_below = all(r["pass_rate"] < PASS_RATE_FLOOR for r in available)` | `r["pass_rate"]` | `<` | `PASS_RATE_FLOOR (=0.95)` | ratio | raw_float | unclear | round(x,6) | Regime-check revert-trigger gate per ADR 2026-05-08-dd-trigger-c2-relock. Substantive risk-control consequence: recommends C2 -> C0 revert. |

## Concerns

1. **Precision-rule mismatch (cross-cutting)**: `accounts.py:43/45/162` compare a ratio-typed property (`dd_remaining_pct`) that is rounded to **2 dp** at the property level, not the canonical **6 dp** the ADR specifies for ratios. The 2 dp treatment matches the in-file precedent (`round(x, 2)` inside `dd_remaining_pct` / `target_remaining` at lines 32/38) because `dd_limit_pct` itself lives at 0.01-pp granularity (e.g. 5.0, 1.5) — but the ADR's ratio-rule recommended treatment is 6 dp. **Parent (claude.ai) should resolve** whether `dd_remaining_pct` qualifies as a ratio (apply 6 dp) or as a percentage-point quantum where 2 dp is the natural fineness. This is a precision-rule scope question, not a survey rule renegotiation. Flagged here per §5 (6) discipline.

2. **Already-fixed reference instances**: **6 of the 17 findings** are sites already rounded per the canonical PR #53 / Q-MCFP-1 pattern (`dd_protection.py:92`; `portfolio_mc.py:198,203,205,217,501,510`). They are included per §2 (“every site emits a row”) as reference baselines for the pattern. If the parent's disposition rule counts **only un-fixed sites**, the un-fixed count is **4** (`dd_protection.py:202`, `dd_protection.py:205`, plus 2 `unclear` sites at `dd_protection.py:295` and `time_to_pass.py:204`). The `dd_remaining_pct` family (`accounts.py:43/45/162`) is already-rounded at 2 dp; whether it counts as fixed depends on resolution of concern #1. **Parent should apply the §9 disposition rule with this distinction explicit**.

3. **Out-of-scope import flag**: `portfolio_mc.py` imports `DD_TRIGGER` and `DD_SCALE` from `dd_protection.py` (lines 31-34) and shares the same trigger comparison semantics in two sim-class sites (already rounded). No cross-repo imports of `firm_rules` in scope per §0.5 (2) — confirmed (only same-repo `accounts.py` imports `RISK_TIERS`).

4. **`analysis/oanda_stage1/` and `weekly_review_feeder/` surveyed and produced null findings per §0 conditional**. `analysis/oanda_stage1/` is research/Stage-1 hypothesis-generation code with statistical/signal-qualification comparisons (`p < 0.05`, `|effect| < cost-floor`, `match_rate < 0.98`), not risk-control gates. `weekly_review_feeder/compute.py` contains MC-placement bucketing (`realized_pnl < p10/p50/p90`) which is categorization for Notion reporting — does not gate live trade, position size, or account state.

## §6 Status

`DONE_WITH_CONCERNS` — survey complete and artifacts emitted, but four flagged concerns require parent resolution before disposition (see above). Disposition decision per §9 deferred to parent (claude.ai).
