"""Phase 1 — assemble result brief from JSON + plot references.

Brief: 2026-05-02 USOIL 15min behavioral characterization.
Plan: ~/.claude/plans/usoil-15min-behavioral-composed-tower.md (Stage C step 12).

Reads: docs/methodology/findings/2026-05-02_usoil_phase1_results.json
Writes: docs/methodology/findings/2026-05-02_usoil_15min_characterization.md

Brief format follows AUDNZD characterization brief at
docs/methodology/archive/findings/2026-04-26_audnzd_structural_characterization.md
(same loop phase: Notice/Identify, descriptive stats, no permutation).

Sections:
  1. Verdict (top of file)
  2. Provenance
  3. Tier-1 results table
  4. Tier-2 / Tier-3 prose + tables
  5. Plot embeds
  6. Pre-Q gate audit trail
  7. Recommended next Q (Inquire-phase seed)
  8. Risks and caveats
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
FINDINGS_DIR = REPO_ROOT / "docs" / "methodology" / "findings"
PREFIX = "2026-05-02_usoil"
RESULTS_JSON = FINDINGS_DIR / f"{PREFIX}_phase1_results.json"
OUT_MD = FINDINGS_DIR / f"{PREFIX}_15min_characterization.md"

DOW_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

VERDICT_PROSE = {
    "abort": "USOIL 15min does NOT clear the cost floor or has no statistically detectable structure. No 4th-strategy candidate from this characterization.",
    "mean-revert": "USOIL 15min exhibits clean mean-reverting structure: negative ACF(1) at significance, VR(q) significantly below 1 at short aggregation, sub-0.5 Hurst.",
    "persistence": "USOIL 15min exhibits trending/persistent structure: positive ACF(1) at significance, VR(q) significantly above 1, supra-0.5 Hurst.",
    "vol-gated": "USOIL 15min has volatility-clustering structure (ACF on |returns| significant, intraday concentration) but no clear directional edge in raw returns. A vol-gated strategy archetype is suggested for the Inquire phase.",
    "indeterminate": "Pattern does not cleanly match abort / mean-revert / persistence / vol-gated. The unmatched-pattern routing per the plan applies; explicit prose description below.",
}


def main() -> int:
    if not RESULTS_JSON.exists():
        print(f"FAIL: missing results JSON {RESULTS_JSON}")
        return 1
    R = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    verdict = R.get("verdict", "indeterminate")
    rationale = R.get("verdict_rationale", [])

    L = []
    L.append(f"# USOIL M15 — behavioral characterization (Phase 1)")
    L.append("")
    L.append(f"**Verdict:** {verdict}")
    L.append("")
    L.append(VERDICT_PROSE.get(verdict, ""))
    L.append("")
    L.append("**Verdict rationale (per §5 decision matrix):**")
    for r in rationale:
        L.append(f"- {r}")
    L.append("")
    L.append(f"**Loop:** USOIL 15min behavioral characterization (2026-05-02), Notice/Identify phase")
    L.append(f"**Plan:** `~/.claude/plans/usoil-15min-behavioral-composed-tower.md`")
    L.append(f"**Brief:** user-supplied scope brief 2026-05-02 (USOIL 15min behavioral characterization)")
    L.append("")

    # Provenance
    L.append("## 1. Provenance")
    L.append("")
    L.append(f"- **Data:** `data/bar_data/USOIL_oanda_m15_2022-01-04_to_2026-04-20_clean.csv`")
    L.append(f"- **SHA256:** `{R['data_hash']}`")
    L.append(f"- **N bars:** {R['n_bars']:,}  N returns (excl maintenance): {R['n_returns']:,}")
    L.append(f"- **Window:** {R['first_bar_utc']} -> {R['last_bar_utc']}")
    L.append(f"- **Source:** OANDA practice endpoint (`WTICO_USD`, mid pricing, M15)")
    L.append(f"- **Pipeline:** `analysis/usoil/phase1_characterize.py`")
    L.append(f"- **Raw results:** `{RESULTS_JSON.name}`")
    L.append(f"- **Stage 0 reconciliation:** `2026-05-02_usoil_feed_reconciliation.md` (must pass before Phase 1)")
    L.append("")
    L.append(f"- **Alchemy DXTrade USOIL cost reference (placeholder — verify):**")
    L.append(f"  - spread: ${R['alchemy_spread_usd']:.4f}/bbl")
    L.append(f"  - commission: ${R['alchemy_commission_usd']:.4f}/bbl")
    L.append(f"  - round-trip cost: ${R['alchemy_rt_cost_usd']:.4f}/bbl")
    L.append("")

    # Tier-1 table
    L.append("## 2. Tier-1 results")
    L.append("")
    L.append("| Stat | Value | CI / sig | Decision-relevant? |")
    L.append("|---|---:|---|---|")
    t11_1 = R["T1_1_acf_returns"]["1"]
    L.append(f"| T1.1 ACF(returns) lag 1 | {t11_1['rho']:.4f} | Bartlett ±{t11_1['bartlett_ci']:.4f}; bootstrap [{t11_1['boot_ci95_lo']:.4f}, {t11_1['boot_ci95_hi']:.4f}] | yes — directional persistence at 15min |")
    t11_4 = R["T1_1_acf_returns"]["4"]
    L.append(f"| T1.1 ACF(returns) lag 4 | {t11_4['rho']:.4f} | Bartlett ±{t11_4['bartlett_ci']:.4f} | yes — 1h horizon |")
    t11_96 = R["T1_1_acf_returns"]["96"]
    L.append(f"| T1.1 ACF(returns) lag 96 | {t11_96['rho']:.4f} | Bartlett ±{t11_96['bartlett_ci']:.4f} | yes — 1-day horizon |")
    t12_8 = R["T1_2_variance_ratio"]["8"]
    L.append(f"| T1.2 VR(8) | {t12_8['vr']:.4f} | z*={t12_8['z_star']:.3f} p={t12_8['p_two_sided']:.4g} | yes — 2h aggregation |")
    t12_32 = R["T1_2_variance_ratio"]["32"]
    L.append(f"| T1.2 VR(32) | {t12_32['vr']:.4f} | z*={t12_32['z_star']:.3f} p={t12_32['p_two_sided']:.4g} | yes — 8h aggregation |")
    t13 = R["T1_3_hurst"]
    L.append(f"| T1.3 Hurst R/S | {t13['rs']['H']:.4f} | CI95 [{t13['rs']['ci95_lo']:.3f}, {t13['rs']['ci95_hi']:.3f}] (width {t13['rs']['ci_width']:.3f}) | yes |")
    L.append(f"| T1.3 Hurst DFA-1 | {t13['dfa']['H']:.4f} | CI95 [{t13['dfa']['ci95_lo']:.3f}, {t13['dfa']['ci95_hi']:.3f}] (width {t13['dfa']['ci_width']:.3f}) | yes |")
    L.append(f"| T1.3 estimator difference | {t13['estimator_difference']:.4f} | max CI width {t13['max_ci_width']:.4f}; needs joint review = **{t13['needs_joint_review']}** | yes — replaces hard 0.10 threshold per plan |")
    t14_1 = R["T1_4_acf_abs_returns"]["1"]
    t14_96 = R["T1_4_acf_abs_returns"]["96"]
    L.append(f"| T1.4 ACF(|returns|) lag 1 | {t14_1['rho']:.4f} | Bartlett ±{t14_1['bartlett_ci']:.4f} | yes — vol clustering |")
    L.append(f"| T1.4 ACF(|returns|) lag 96 | {t14_96['rho']:.4f} | Bartlett ±{t14_96['bartlett_ci']:.4f} | yes — daily vol cycle |")
    t15 = R["T1_5_intraday_atr"]
    L.append(f"| T1.5 intraday ATR top-3 bins (NY) | {t15['top3_bins_by_median']} | peak/trough ratio {t15['peak_to_trough_ratio']:.2f} | yes — vol concentration |")
    t16 = R["T1_6_cost_floor"]
    L.append(f"| T1.6 cost floor: % bars > 3× cost (active hrs) | {t16['pct_clear_3x_cost']:.2f}% | kill if < {t16['kill_threshold_pct']}%; **{'PASS' if t16['cost_floor_pass'] else 'KILL'}** | yes — abort gate |")
    L.append("")

    # Tier-2 / Tier-3 prose
    L.append("## 3. Tier-2 — refines the picture")
    L.append("")
    L.append("### T2.1 Variance by DOW")
    L.append("")
    L.append("| DOW | n | Var(log_ret) | CI95 |")
    L.append("|---|---:|---:|---|")
    for d in range(7):
        row = R["T2_1_variance_by_dow"].get(str(d), {})
        if row.get("var") is None:
            L.append(f"| {DOW_LABELS[d]} | {row.get('n', 0)} | n/a | {row.get('note', '—')} |")
        else:
            L.append(f"| {DOW_LABELS[d]} | {row['n']:,} | {row['var']:.2e} | [{row['ci_lo']:.2e}, {row['ci_hi']:.2e}] |")
    L.append("")

    L.append("### T2.2 EIA event study (Wed 10:30–11:15 ET, 4 bars)")
    L.append("")
    t22 = R["T2_2_eia_event_study"]
    if "eia_to_other_ratio" in t22:
        L.append(f"- EIA bars n = {t22['n_eia']}")
        L.append(f"- Mon/Tue/Thu/Fri same-bin baseline n = {t22['n_other']}")
        L.append(f"- Mean |log ret| EIA = {t22['mean_abs_ret_eia']:.5f}, baseline = {t22['mean_abs_ret_other']:.5f}")
        L.append(f"- **Ratio EIA / baseline = {t22['eia_to_other_ratio']:.2f}×**")
        L.append(f"- EIA bootstrap CI95 = [{t22['eia_ci95'][0]:.5f}, {t22['eia_ci95'][1]:.5f}]")
    else:
        L.append(f"- {t22.get('note', '—')}")
    L.append("")

    L.append("### T2.3 Vol expansion (low-vol → next-bar |r|)")
    L.append("")
    t23 = R["T2_3_vol_expansion"]
    if "ratio_next_to_uncond" in t23:
        L.append(f"- Low-vol → not-low transitions: n = {t23['n_transitions']:,}")
        L.append(f"- Next-bar |r| mean (post-transition) = {t23['next_bar_abs_ret_mean']:.5f}")
        L.append(f"- Unconditional |r| mean = {t23['uncond_abs_ret_mean']:.5f}")
        L.append(f"- **Ratio next/uncond = {t23['ratio_next_to_uncond']:.3f}**")
        L.append(f"- Next-bar CI95 = [{t23['next_bar_ci95'][0]:.5f}, {t23['next_bar_ci95'][1]:.5f}]")
    else:
        L.append(f"- {t23.get('note', '—')}")
    L.append("")

    L.append("### T2.4 Body/range ratio (top-quartile |r| vs unconditional)")
    L.append("")
    t24 = R["T2_4_range_body_ratio"]
    L.append(f"- Unconditional median body/range = {t24['uncond_median_body_over_range']:.3f}")
    L.append(f"- Top-quartile |r| (n={t24['topq_n']:,}) median body/range = {t24['topq_median_body_over_range']:.3f}")
    L.append(f"- Top-quartile threshold (q75 |log ret|) = {t24['q75_abs_ret_threshold']:.5f}")
    L.append("")

    L.append("## 4. Tier-3 — informative but not decision-critical")
    L.append("")
    t31 = R["T3_1_tails"]
    L.append(f"- T3.1 Excess kurtosis = {t31['excess_kurtosis']:.2f}")
    if t31["weekly_var_share_top1_mean"] is not None:
        L.append(f"  - Weekly variance share: top-1 bar = {t31['weekly_var_share_top1_mean']*100:.2f}%, top-5 = {t31['weekly_var_share_top5_mean']*100:.2f}%, top-20 = {t31['weekly_var_share_top20_mean']*100:.2f}%")
    t32 = R["T3_2_three_sigma_days"]
    L.append(f"- T3.2 Daily 3σ events: n = {t32['n_3sigma_days']} of {t32['n_days_total']} days (daily σ = {t32['daily_std']:.4f})")
    if t32["small_cell_warning"]:
        L.append(f"  - **Small-cell warning** (Rule 1): n = {t32['n_3sigma_days']} < 30; tail-event statistics carry the small-cell prior")
    L.append("")

    # Plots
    L.append("## 5. Plots")
    L.append("")
    L.append(f"- T1.1 + T1.4 ACF: ![ACF]({PREFIX}_acf.png)")
    L.append(f"- T1.2 Variance ratio: ![VR]({PREFIX}_vr.png)")
    L.append(f"- T1.3 Hurst (R/S + DFA): ![Hurst]({PREFIX}_hurst.png)")
    L.append(f"- T1.5 + T3.3 Intraday ATR + DOW heatmap: ![Intraday ATR]({PREFIX}_intraday_atr.png)")
    L.append(f"- T1.6 Cost floor: ![Cost floor]({PREFIX}_cost_floor.png)")
    L.append(f"- T2.2 EIA event: ![EIA]({PREFIX}_eia_event.png)")
    L.append("")

    # Pre-Q gate audit trail
    L.append("## 6. Pre-Q gate audit trail")
    L.append("")
    L.append("**Permitted deletions applied:**")
    L.append("- D1: maintenance-window bars (CME Globex 17:00-17:45 ET, Mon-Fri) — TAGGED, retained, excluded only from return-distribution stats. D-test: known measurement artefact. Permitted.")
    L.append("")
    L.append("**Permitted deletions considered and rejected:**")
    L.append("- D2: Stage 0 quantitative feed-reconciliation deletion. Considered during plan clarification 2026-05-02; rejected by Joshua. Stage 0 was restored as a hard precondition. The 'we'll catch it in Phase 2' framing was identified as silent substitution and rejected.")
    L.append("")
    L.append("**Forbidden D-tests not applied** (committed in plan §Pre-Q gate):")
    L.append("- 'known fundamental driver?' — not asked")
    L.append("- 'matches Striker breakout pattern?' — not asked")
    L.append("- 'autocorrelation high enough to be useful?' — not asked")
    L.append("- 'copper or Brent shown similar?' — not asked")
    L.append("")

    # Recommended next Q
    L.append("## 7. Recommended next Q (Inquire-phase seed)")
    L.append("")
    if verdict == "abort":
        L.append("No Inquire-phase Q on USOIL. Revert to top-three CFD shortlist (Copper / EUR-USD).")
    elif verdict == "mean-revert":
        L.append("**Q-USOIL-1**: Conditional on USOIL 15min mean-reverting structure, can a Bollinger-band fade entry with intraday-window gating produce N≥100 trades and pass permutation gating against a same-cohort null? (Aegis-adjacent archetype, but with USOIL-specific session and EIA filters.)")
    elif verdict == "persistence":
        L.append("**Q-USOIL-2**: Conditional on USOIL 15min trend-continuation structure, can an EMA-cross or breakout-with-pyramid entry produce N≥100 trades and pass permutation gating? Care: structural persistence at 15min often reflects vol clustering not directional edge; the Q must distinguish.")
    elif verdict == "vol-gated":
        L.append("**Q-USOIL-3**: Conditional on USOIL 15min volatility-gated structure (ACF|r|>0.10, intraday concentration), separate the vol-gate from the underlying directional edge. What direction (if any) does USOIL exhibit conditional on entering a top-3 ATR-percentile bin?")
    else:  # indeterminate
        L.append("**Q-USOIL-?** (to be sharpened): The pattern observed here does not cleanly match any of the four pre-defined archetypes. Document the unmatched pattern explicitly above (see §1 verdict rationale) and design an Inquire-phase Q that addresses that specific structure, not the closest archetype-match.")
    L.append("")

    # Risks
    L.append("## 8. Risks and caveats")
    L.append("")
    L.append("- **Alchemy cost is a placeholder.** The T1.6 verdict depends on the round-trip cost assumption. Joshua to verify against current DXTrade USOIL spread before locking the verdict; a 2× cost increase (e.g. $0.10 round-trip becoming $0.20) materially shrinks the % bars clearing 3× cost and could flip T1.6 from PASS to KILL. Re-run with corrected cost if needed.")
    L.append("- **OANDA practice feed.** The 52-month panel is OANDA practice. Phase 2 visual on Pepperstone TV is the broker-equivalence check (see plan Stage D pre-registered criteria).")
    L.append("- **CFD synthetic.** OANDA WTICO_USD is a CFD; not the underlying CME front-month WTI. Stage 0 reconciliation against Pepperstone CFD addresses inter-broker drift but not CFD-vs-future drift.")
    L.append("- **Hurst estimator stability.** If R/S and DFA disagree by more than the bootstrap CI width (`needs_joint_review` flag in T1.3), the verdict's reliance on H is weakened — see plan stop conditions.")
    L.append("- **Maintenance-window detection is clock-time only.** OANDA's CFD feed may or may not honor the underlying CME settlement halt; the tag is conservative and may over-flag.")
    L.append("")

    # Cross-references
    L.append("## 9. Cross-references")
    L.append("")
    L.append("- Plan: `~/.claude/plans/usoil-15min-behavioral-composed-tower.md`")
    L.append("- Stage 0 reconciliation: `2026-05-02_usoil_feed_reconciliation.md`")
    L.append("- Phase 2 validation (downstream): `2026-05-02_usoil_phase2_validation.md`")
    L.append("- Brief format precedent: `docs/methodology/archive/findings/2026-04-26_audnzd_structural_characterization.md`")
    L.append("- Hurst log-prices trap memory: `feedback_hurst_rs_log_prices_trap.md`")
    L.append("- Observation routing: `docs/methodology/observation_routing.md`")
    L.append("")

    OUT_MD.write_text("\n".join(L), encoding="utf-8")
    print(f"brief written: {OUT_MD}")
    print(f"verdict: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
