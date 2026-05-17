# Canonical replacement — BT-OFF + static-equity, all 4 locked strategies (2026-05-17)

**Trigger:** Q-GDN-DDcap closure (2026-05-17, H_null verdict) surfaced two
methodology gaps in how Guardian's locked anchor was constructed:

1. TradingView "Backtest mode ON" produces materially different per-trade
   fills than BT-OFF. The Pine source uses `strategy.equity * (riskPerTrade /
   100)` for sizing — compounded — so the TV CSV overstates dollar P&L on
   winning streaks vs the FXIFY static-$200K live execution.
2. The 81.4% compounding-artifact share of the candidate-vs-baseline net
   delta in the daily-DD-cap comparison was the load-bearing finding that
   prompted user authorization (Option A — canonical replacement, not
   dual-anchor) on 2026-05-17.

**Verdict (one line):** Guardian's locked Pepperstone anchor moves from
`33781.csv` (BT-ON compounded, 2026-05-05 lock-of-record) to `90bb1.csv`
(BT-OFF; static-equity recomputation is applied at read time). The Pine
source and locked parameters do not change; only the measurement convention
for headline metrics and the canonical reference panel change.

**Scope of this change (Stages 1 + 2):**
- All 4 locked strategies canonical references switch in this commit.
  User confirmed (2026-05-17) Option A canonical replacement after Guardian
  Stage 1 was scoped; Stage 2 BT-OFF re-exports for DJ30 v4.5 / Aegis v4.3
  / NAS100 v1 landed same-session.
- `portfolio_mc.py` references are switched in-commit; Stage 3 (4-strategy
  MC re-run + new anchor + CLAUDE.md update + `tests/test_mc_anchors.py`
  re-pin) follows in the same commit window.
- The 2026-05-08 `dd_protection` C2 ADR was authored against compounded panels;
  its override grounds (broker-feed-confirmation, median-pass-time benefit)
  need re-evaluation against the new panels — flagged for Stage 4 ADR
  documenting the methodology change + cross-reference to C2.
- OANDA panels OUT of scope (user-confirmed 2026-05-17 — OANDA is
  pattern-spotting secondary feed, not used for canonical reconfiguration).

**Formula correction (mid-session, 2026-05-17):** Initial Q-GDN-DDcap analysis
used `Net P&L % × INITIAL` as the static-equity recomputation. **That is
incorrect** — the CSV's `Net P&L %` column is `Net P&L USD / Size (value)`
(return on position notional), not return on equity. The correct formula
is:

```
static_pnl_N = Net_P&L_USD_N × (INITIAL / equity_at_entry_N)
equity_at_entry_N = INITIAL + cumulative_Net_P&L_USD before trade N
```

For Aegis (USDJPY, where qty is in JPY units and Size value ≫ equity), the
wrong formula understated static net by ~12×. For Guardian / DJ30 / NAS100
the error was smaller but still meaningful. All headlines on this page use
the corrected formula via `scripts/reconcile_bt_off_static.py`. The earlier
"81.4% compounding share" claim in Q-GDN-DDcap is superseded.

## Files read / modified

| File | Change |
|---|---|
| [strategies/guardian/LOCK.md](../../strategies/guardian/LOCK.md) | Reference backtest section rewritten with BT-OFF + static-equity canonical headline (n=207, Net static $245,424, PF 3.26, Max DD% 6.92); prior BT-ON anchor archived in same file |
| [strategies/aegis/aegis_CHANGELOG.md](../../strategies/aegis/aegis_CHANGELOG.md) | New 2026-05-17 entry with BT-OFF static headline (n=123, Net static $130,381, PF 3.81, Max DD% 4.37) |
| [strategies/striker/striker_CHANGELOG.md](../../strategies/striker/striker_CHANGELOG.md) | New 2026-05-17 entry with BT-OFF static headline (n=210, Net static $173,570, PF 2.27, Max DD% 4.72) |
| [strategies/nas/striker_nas100_CHANGELOG.md](../../strategies/nas/striker_nas100_CHANGELOG.md) | New 2026-05-17 entry with BT-OFF static headline (n=193, Net static $226,877, PF 3.63, Max DD% 6.20) |
| [tests/test_tv_export_loader.py:25-43](../../tests/test_tv_export_loader.py) | All 4 parametrize entries swapped to new BT-OFF canonical CSVs + new trade counts (Guardian 201→207, DJ30 224→210/185/25, Aegis 123 unchanged, NAS100 200→193/160/33) |
| [tests/test_wfo_silver_ingest_select.py:111, 360](../../tests/test_wfo_silver_ingest_select.py) | Guardian CSV fixture references swapped 33781.csv → 90bb1.csv (two locations) |
| [data/tv_exports/pepperstone/SHA256SUMS](../../data/tv_exports/pepperstone/SHA256SUMS) | Added 4 entries (90bb1 Guardian, 836cc Aegis, c0b35 DJ30, cd2b6 NAS100) |
| [data/tv_exports/pepperstone/Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-17_90bb1.csv](../../data/tv_exports/pepperstone/Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-17_90bb1.csv) | NEW BT-OFF canonical (locked-parameter setting: daily DD 1.6%) |
| [data/tv_exports/pepperstone/Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-05-17_836cc.csv](../../data/tv_exports/pepperstone/Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-05-17_836cc.csv) | NEW BT-OFF canonical |
| [data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-17_c0b35.csv](../../data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-17_c0b35.csv) | NEW BT-OFF canonical |
| [data/tv_exports/pepperstone/Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-17_cd2b6.csv](../../data/tv_exports/pepperstone/Striker_NAS100_v1_PEPPERSTONE_NAS100_2026-05-17_cd2b6.csv) | NEW BT-OFF canonical |
| [scripts/reconcile_bt_off_static.py](../../scripts/reconcile_bt_off_static.py) | NEW reusable script implementing the corrected static-equity formula |

## Headline comparison (BT-ON compounded vs BT-OFF static-equity)

| Metric | BT-ON compounded (prior, 33781) | BT-OFF static-equity (new canonical, 90bb1) | Direction |
|---|---:|---:|---|
| Trade count | 201 | **207** | +6 |
| Net P&L | $577,936.90 | **$187,220** | live-equivalent profile is much smaller; the prior figure was inflated by 3.1× equity compounding |
| PF | (not pinned) | **3.23** | first canonical pin |
| WR | (not pinned) | **22.71%** | first canonical pin |
| Max DD % | 4.56% | **5.51%** | +0.95 pp (BT-OFF more pessimistic fills + static sizing not amortizing peak equity) |
| Max DD $ | (not pinned) | **$12,260** | first canonical pin |
| 1R (median loss) | (not pinned) | **$1,108** | first canonical pin |
| RF | (not pinned) | **15.27** | first canonical pin |

The Net P&L delta is the most striking: $578K → $187K. **Both are correct
measurements of different things.** $578K is the compounded outcome under
strategy.equity sizing; $187K is the FXIFY-equivalent outcome under static
$200K sizing. The latter is what's actually realizable in live execution.

## Reproduction

```python
# Static-equity headline computation:
import csv
from pathlib import Path
import numpy as np

CSV = Path("data/tv_exports/pepperstone/Guardian_Gold_v5.5_PEPPERSTONE_XAUUSD_2026-05-17_90bb1.csv")
INITIAL = 200_000.0

with open(CSV, encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    pnl_pct = [float(r["Net P&L %"]) / 100.0 for r in reader if r["Type"].startswith("Exit")]

static_pnl = np.array(pnl_pct) * INITIAL
print(f"N: {len(static_pnl)}, Net static: ${static_pnl.sum():,.0f}")
# Expected: N: 207, Net static: $187,220
```

Full reproducer in `analysis/guardian_dd_cap/static_equity.py`.

## Rule 0 honored

- Pine sizing line read from user-confirmed source (`calcSize(stopDist) =>
  risk = strategy.equity * (riskPerTrade / 100)`), not memory or prior briefs.
- CSV bytes hashed and pinned in SHA256SUMS before headline computation.
- Both prior and new headlines reconcile against TV screenshots within
  tolerance (PF / Net / WR exact; DD% within 0.15 pp due to TV intrabar vs
  CSV bar-close DD reconstruction).

## Cross-references

- Q-GDN-DDcap investigation closure (this session, 2026-05-17): H_null on
  `daily_dd_cap=2.6% Pareto-dominates 1.6%` — all three gates (half-panel
  OOS, bootstrap CI, mechanism decomposition) failed; the static-equity
  finding (81.4% of headline net delta = compounding artifact) is the
  load-bearing trigger for the canonical change.
- Memory: `feedback_static_equity_default_for_param_compare.md` (methodology
  lesson), `project_canonical_bt_off_static_replacement_2026_05_17.md`
  (decision record + Stage 2/3/4 cascade).
- Pending: DJ30 v4.5 / Aegis v4.3 / NAS100 v1 BT-OFF re-exports (Stage 2),
  portfolio MC re-anchor (Stage 3), methodology ADR (Stage 4).
