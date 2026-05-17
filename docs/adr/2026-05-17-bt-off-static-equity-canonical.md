# ADR 2026-05-17 — BT-OFF + static-equity becomes canonical Pepperstone reference

**Status:** ACCEPTED (Joshua, 2026-05-17 — Option A from the Q-GDN-DDcap closure surface).
**Scope:** Pepperstone canonical reference panels for all 4 locked strategies (Guardian v5.5, DJ30 v4.5, Aegis v4.3, NAS100 v1) + 4-strategy MC anchor + per-strategy lock docs. OANDA pattern-spotting feed is out of scope.
**Replaces (anchor):** 2026-05-08 BT-ON compounded Pepperstone anchor (98.09 / 0.36 / 4.73 at C2).
**Does NOT change:** Pine source; locked parameters; locked allocations (G 0.34% / DJ30 1.00% / A 1.50% / NAS 0.40%); dd_protection C2 trigger (DD_TRIGGER=0.015, DD_SCALE=0.40); v5.5 / v4.5 / v4.3 / v1 lock versions; lock criteria (bust <1%, p99 DD <5%).

## Context

The 2026-05-17 Q-GDN-DDcap investigation (Guardian daily-DD-cap parameter sweep, 1.6% vs 2.6%) surfaced two methodology gaps in how locked anchors were constructed:

1. **TradingView "Backtest mode ON" vs "Backtest mode OFF"** produces materially different per-trade fills for fill-quality-sensitive strategies. The 2.6%-vs-1.6% Guardian comparison run with BT OFF showed PF 3.65 / Net $392K, while the reproducible LOCK anchor (BT ON, same parameters) showed PF 4.49 / Net $508K — a 23% net gap entirely attributable to optimistic intra-bar fill resolution under BT ON. NAS100 showed a similar gap (BT-ON 200 trades / +$509K → BT-OFF 193 trades / +$392K).

2. **TV's compounded `strategy.equity` sizing** overstates the live-FXIFY-equivalent P&L. FXIFY live execution sizes off static $200K initial capital. Pine sizing line `calcSize(stopDist) => risk = strategy.equity * (riskPerTrade / 100)` is confirmed identical across all 4 locked strategies (user-confirmed 2026-05-17). The compounded TV CSV inflates net P&L by 27-46% depending on the strategy (Guardian's massive winners + long hold times = biggest distortion).

The combination — BT-ON compounded panels — overstates both per-trade fill quality and equity-curve magnitude relative to what FXIFY live execution actually realizes. Continuing to anchor lock decisions on that combination is methodologically inconsistent with the operational reality the locks are meant to govern.

## Decision

**Option A — canonical replacement** (not dual-anchor):
- All 4 Pepperstone reference panels switch to BT-OFF re-exports (2026-05-17 vintage: 90bb1 / 836cc / c0b35 / cd2b6).
- Per-strategy headline metrics in LOCK.md / CHANGELOGs use **static-equity recomputation**: `static_pnl_N = Net_P&L_USD_N × (INITIAL / equity_at_entry_N)`. Reusable script: `scripts/reconcile_bt_off_static.py`.
- Portfolio MC pipeline runs against the new BT-OFF panels with no changes to its internal logic (the existing 1R-normalization layer is preserved).
- Prior BT-ON CSVs and historical anchors retained on disk and in `SHA256SUMS` for traceability; not the lock-of-record going forward.
- OANDA panels (pattern-spotting secondary feed) out of scope — remain BT-ON; 96.23 / 0.69 / 4.91 OANDA anchor unchanged.

**Formula correction (mid-session, 2026-05-17):** the initial Q-GDN-DDcap analysis used `Net P&L % × INITIAL` as the static-equity recomputation. That is incorrect — the CSV's `Net P&L %` column is `Net P&L USD / Size (value)` (return on position notional), not return on equity. The correct per-trade formula uses `Net P&L USD × (INITIAL / equity_at_entry)`. For Aegis (USDJPY, qty in JPY units, Size value ≫ equity) the wrong formula understated static net by ~12×. All headlines on this ADR use the corrected formula.

## New canonical anchor (2026-05-17)

**Portfolio MC (4-strategy Pepperstone, C2 dd_protection, BT-OFF panels):**

| Metric | Prior BT-ON (2026-05-08) | New BT-OFF (2026-05-17) | Δ |
|---|---:|---:|---:|
| Pass rate | 98.09% | **97.56%** | −0.53 pp |
| Bust rate | 0.36% | **0.40%** | +0.04 pp |
| p99 DD | 4.73% | **4.79%** | +0.06 pp |
| Median days to pass | 22 | 23 | +1 |
| Bust attribution: striker | 44.4% | 42.9% | −1.5 pp |
| Bust attribution: guardian | 21.3% | 25.2% | +3.9 pp |
| Bust attribution: aegis | 24.1% | 22.7% | −1.4 pp |
| Bust attribution: NAS | 10.2% | 9.2% | −1.0 pp |

Both lock criteria still clear with margin (bust <1%, p99 DD <5%). **This is an anchor update, not a re-lock event.**

**Per-strategy headlines (BT-OFF static-equity, 2026-05-17):**

| Strategy | N | WR | PF | Net (static) | Max DD % (static) | Static/Compounded |
|---|---:|---:|---:|---:|---:|---:|
| Guardian Gold v5.5 | 207 | 22.71% | 3.26 | $245,424 | 6.92% | 54% |
| Aegis USDJPY v4.3 | 123 | 60.16% | 3.81 | $130,381 | 4.37% | 73% |
| Striker DJ30 v4.5 | 210 | 69.52% | 2.27 | $173,570 | 4.72% | 67% |
| Striker NAS100 v1 | 193 | 55.96% | 3.63 | $226,877 | 6.20% | 58% |

## Rationale

1. **Methodology consistency with operational reality.** Live FXIFY execution uses static $200K initial capital and broker-real fills. Anchors built on compounded sizing + optimistic fills systematically overstate the achievable live profile. The new convention removes that bias.
2. **MC robustness validates lock decision.** The MC pipeline's existing 1R-normalization layer absorbs much of the per-strategy headline distortion — bust/pass dynamics barely move (−0.53 pp / +0.04 pp) despite Net P&L $ dropping 27-46% per strategy. This is a positive methodology robustness result: the lock decision was not sensitive to the compounding artifact.
3. **No locked parameters changed.** Strategies, allocations, dd_protection C2 trigger, lock criteria — all preserved. Only the measurement convention for headline anchors changes.

## Cross-references

- **C0→C2 ADR ([`docs/adr/2026-05-08-dd-trigger-c2-relock.md`](2026-05-08-dd-trigger-c2-relock.md)):** The C2 override grounds (broker-feed-confirmation, median-pass-time benefit 23→22) were authored against BT-ON compounded panels. Under the new BT-OFF anchor, median-pass-time returns to 23 (the prior C0 timing). **The C2 ADR's median-pass-time argument is weakened under the new methodology** — the broker-feed-confirmation argument (`bust_attribution_flip` closed via Pepperstone+OANDA re-export) is unchanged. The C2 lock decision is not reversed by this ADR, but the C2 override should be re-examined on the new panels if the dd_protection question reopens.
- **Q-GDN-DDcap closure (this session, 2026-05-17):** the verdict (H_null on daily_dd_cap=2.6% Pareto-dominates 1.6%) was based on compounded half-panel evidence and is preserved. The 81.4% compounding-share claim in the original closure is superseded by the corrected formula (per-strategy ratios 54-73%, not 81%).
- **Reconcile note ([`data/reconciles/2026-05-17_guardian_bt_off_static_canonical.md`](../../data/reconciles/2026-05-17_guardian_bt_off_static_canonical.md)):** full file-by-file change documentation.
- **Memory:** `feedback_static_equity_default_for_param_compare.md` (methodology lesson), `project_canonical_bt_off_static_replacement_2026_05_17.md` (decision record).

## Forward triggers

- **Quarterly MC regime-check** unchanged (next: 2026-08-08): rolling 6-month MC pass-rate < 95% for two consecutive 6-month windows → revert to C0. Now operates on BT-OFF panels.
- **OANDA cascade decision:** if/when OANDA panels are brought into the canonical-replacement scope, re-run with BT-OFF + static-equity equivalent and re-evaluate OANDA anchor (currently 96.23 / 0.69 / 4.91 unchanged).
- **C2 re-examination trigger:** if any future signal reopens the dd_protection question (e.g., live drawdown patterns, regime shift), the C2 override grounds need re-evaluation against the BT-OFF panel — the prior median-pass-time argument no longer holds.

## Test verification

- `tests/test_tv_export_loader.py` — 5/5 PASS (all 4 strategies + the parametrize fixture).
- `tests/test_wfo_silver_ingest_select.py` — 12/12 PASS (Guardian CSV fixture swap doesn't affect trade-count-agnostic ingestion tests).
- `tests/test_mc_anchors.py` — 8/8 PASS (new pins 0.9756 / 0.0040 / 0.0479; lock-criteria check passes; OANDA anchor unchanged; panel cardinality unchanged at 1120 bdays / 223 blocks).
- `python scripts/check_data_manifests.py --check` — PASS (4 new CSV hashes added to Pepperstone SHA256SUMS; oanda/bar_data/external unchanged).
- `python portfolio_mc.py --panel pepperstone` — reproduces 97.56 / 0.40 / 4.79 deterministically given fixed seeds.
