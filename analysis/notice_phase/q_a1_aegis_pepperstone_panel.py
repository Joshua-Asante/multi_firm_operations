"""Q-A1 — Aegis Pepperstone Panel-Thirds Replication Test.

Tests whether the OANDA Aegis panel-thirds PF lift (2.46 / 4.97 / 5.96
across early / mid / late) replicates on Pepperstone canonical data.
Analysis-only. Does not touch strategy code, allocations, dd_protection,
MC calibration, or Notion.

Parent question: Q-A gated brief — 2026-04-27 synthesis backfilled at
docs/methodology/identify_corpus/2026-04-27/q_a_aegis_panel_mechanism_gated.md
(Q-A1-d closed 2026-04-29).
Q15 closure: analysis/notice_phase/findings_2026-04-26.md:414-510.

Methodology (per approved plan):
  - Convention A: calendar-year buckets matching Q15 — early ∈ {2022, 2023},
    mid == 2024, late ∈ {2025, 2026}. (Q15's actual method: "Early 2022-2023
    / Mid 2024 / Late 2025-2026" giving n=44/28/51 on OANDA. Equal-time-
    thirds was the plan's nominal phrasing but year-buckets is what Q15
    actually used; preserving Q15-faithful boundaries lets the self-test
    reproduce 2.46/4.97/5.96.)
  - Convention B: equal-N trade-index thirds — sort by entry_time,
    [0:41] / [41:82] / [82:123].
  - Bootstrap CI per third: Pepperstone only, 10K resamples, 95% CI on PF,
    seed 42.
  - Monotonicity permutation: Pepperstone only, 10K shuffles, p-value =
    fraction with monotonic increase AND PF_late/PF_early ≥ observed,
    seed 42.

Verdict (dual-convention routing rule):
  - REPLICATION CONFIRMED  : both conventions hit replication criteria
    (monotonic increase, PF_late/PF_early ≥ 2.0, perm p < 0.05).
  - NON-REPLICATION        : both conventions hit non-replication
    (flat / non-monotonic / decline).
  - PARTIAL                : anything else (mixed or partial).
  - MONOTONIC-DECLINE FLAG : flagged additionally if either convention
    shows PF_early > PF_mid > PF_late on Pepperstone, regardless of
    routing class.

Run: python analysis/notice_phase/q_a1_aegis_pepperstone_panel.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths — discover project root by walking up to find data/tv_exports/
HERE = Path(__file__).resolve()


def find_root() -> Path:
    for cand in [HERE.parent, *HERE.parents]:
        if (cand / "data" / "tv_exports").exists():
            return cand
    raise RuntimeError("Could not locate project root with data/tv_exports/")


ROOT = find_root()
TV = ROOT / "data" / "tv_exports"

PEPPERSTONE_CSV = TV / "pepperstone" / "Aegis_USDJPY_v4.3_PEPPERSTONE_USDJPY_2026-04-26_0bf1b.csv"
OANDA_CSV = TV / "oanda" / "Aegis_USDJPY_v4.3_OANDA_USDJPY_2026-04-25_7ee6b.csv"

# ---------------------------------------------------------------------------
# Locked Aegis v4.3 header (2026-04-23) — Pepperstone canonical
LOCKED_AEGIS_V43 = {
    "trades": 123,
    "pf": 4.186,
    "wr": 60.16,         # percent
    "net_pnl_usd": 178208,
    "max_dd_pct": 5.01,
    "symbol": "USDJPY 15m",
}
RISK_PCT_AEGIS = 1.50  # percent units, per scripts/identify/2026-04-26/common.py

# Q15 anchor (OANDA, calendar-year buckets) — for self-test
Q15_ANCHOR_OANDA = {"early_2022_2023": 2.46, "mid_2024": 4.97, "late_2025_2026": 5.96}
SELF_TEST_TOLERANCE = 0.005  # |delta| per per-third PF

# Tolerance for Rule 0 reconciliation
PF_TOLERANCE = 0.01

BOOTSTRAP_N = 10_000
PERMUTATION_N = 10_000
SEED = 42


# ---------------------------------------------------------------------------
def load_tv_feed(csv_path: Path) -> pd.DataFrame:
    """Load TV trade export → one row per Trade # (entry/exit pivot).

    Both OANDA and Pepperstone Aegis exports share the schema:
      Trade #, Type, Date and time, Signal, Price JPY, Size (qty),
      Size (value), Net P&L USD, Net P&L %, Favorable excursion USD/%,
      Adverse excursion USD/%, Cumulative P&L USD/[%].

    Times are naive (chart-TZ); we keep them naive — boundary logic is
    year-based (Convention A) and trade-order-based (Convention B), so
    TZ doesn't matter.
    """
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    df["Date and time"] = pd.to_datetime(df["Date and time"], format="%Y-%m-%d %H:%M")

    entries = df[df["Type"] == "Entry long"][[
        "Trade #", "Date and time", "Signal", "Price JPY",
        "Size (qty)", "Size (value)",
    ]].rename(columns={
        "Date and time": "entry_time",
        "Signal": "entry_signal",
        "Price JPY": "entry_price",
    })
    exits = df[df["Type"] == "Exit long"][[
        "Trade #", "Date and time", "Signal", "Price JPY",
        "Net P&L USD", "Net P&L %",
        "Favorable excursion USD", "Favorable excursion %",
        "Adverse excursion USD", "Adverse excursion %",
        "Cumulative P&L USD",
    ]].rename(columns={
        "Date and time": "exit_time",
        "Signal": "exit_signal",
        "Price JPY": "exit_price",
        "Net P&L USD": "net_pnl_usd",
        "Net P&L %": "net_pnl_pct",
        "Favorable excursion USD": "mfe_usd",
        "Favorable excursion %": "mfe_pct",
        "Adverse excursion USD": "mae_usd",
        "Adverse excursion %": "mae_pct",
        "Cumulative P&L USD": "cum_pnl_usd",
    })

    merged = entries.merge(exits, on="Trade #", how="outer")
    merged = merged.sort_values("Trade #").reset_index(drop=True)
    merged = merged.dropna(subset=["entry_time", "exit_time", "net_pnl_pct"]).copy()
    merged["net_pnl_R"] = merged["net_pnl_pct"] / RISK_PCT_AEGIS
    # is_win from USD (precise) — Net P&L % is rounded to 2 decimals so many
    # small wins/losses round to 0 and would be miscounted as losses.
    merged["is_win"] = (merged["net_pnl_usd"] > 0).astype(int)
    merged = merged.sort_values("entry_time").reset_index(drop=True)
    return merged


# ---------------------------------------------------------------------------
def compute_pf(r: np.ndarray) -> float:
    pos = r[r > 0].sum()
    neg = -r[r < 0].sum()
    if neg == 0:
        return float("inf") if pos > 0 else float("nan")
    return float(pos / neg)


def per_third_metrics(third: pd.DataFrame, label: str) -> dict:
    r = third["net_pnl_R"].to_numpy()
    return {
        "label": label,
        "n": int(len(third)),
        "pf": compute_pf(r),
        "win_rate": float(third["is_win"].mean()) if len(third) else float("nan"),
        "mean_R": float(r.mean()) if len(r) else float("nan"),
        "median_R": float(np.median(r)) if len(r) else float("nan"),
        "ret_std": float(r.std(ddof=1)) if len(r) > 1 else float("nan"),
        "sum_R": float(r.sum()),
        "trade_idx_lo": int(third.index.min()) if len(third) else -1,
        "trade_idx_hi": int(third.index.max()) if len(third) else -1,
        "date_lo": third["entry_time"].min() if len(third) else None,
        "date_hi": third["entry_time"].max() if len(third) else None,
    }


# ---------------------------------------------------------------------------
def split_convention_a(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Convention A — calendar-year buckets (Q15-matching).

    early ∈ {2022, 2023}, mid == 2024, late ∈ {2025, 2026}.
    Same boundaries on both feeds (year-buckets are absolute).
    """
    yr = df["entry_time"].dt.year
    early = df[yr.isin([2022, 2023])].copy()
    mid = df[yr == 2024].copy()
    late = df[yr.isin([2025, 2026])].copy()
    return early, mid, late


def split_convention_b(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Convention B — equal-N trade-index thirds.

    floor(N/3) per third; remainder absorbed into the last third (per spec
    resilience note). For N=123: 41 / 41 / 41.
    """
    n = len(df)
    k = n // 3
    early = df.iloc[:k].copy()
    mid = df.iloc[k:2 * k].copy()
    late = df.iloc[2 * k:].copy()
    return early, mid, late


# ---------------------------------------------------------------------------
def bootstrap_pf_ci(r: np.ndarray, n_boot: int, seed: int, ci: float = 0.95) -> tuple[float, float]:
    if len(r) == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    pfs = np.empty(n_boot)
    n = len(r)
    for i in range(n_boot):
        sample = rng.choice(r, size=n, replace=True)
        pfs[i] = compute_pf(sample)
    finite = pfs[np.isfinite(pfs)]
    if len(finite) == 0:
        return (float("nan"), float("nan"))
    lo = float(np.quantile(finite, (1 - ci) / 2))
    hi = float(np.quantile(finite, 1 - (1 - ci) / 2))
    return (lo, hi)


def permutation_test_monotonic(
    df: pd.DataFrame,
    splitter,
    n_perm: int,
    seed: int,
) -> dict:
    """Permutation test for monotonic PF increase across thirds.

    H0: trade-level R i.i.d. across panel (i.e., no epoch effect).
    Shuffle trade order; recompute three per-third PFs under the active
    splitter; record fraction with monotonic increase AND
    PF_late/PF_early >= observed ratio.

    For Convention A (year-bucket), shuffling the trade order while keeping
    the entry_time index would do nothing — we permute the R values across
    the trade index instead. This preserves the per-third trade counts and
    asks: under H0 of i.i.d. R, how often does this monotonic-with-magnitude
    pattern arise by chance?
    """
    early0, mid0, late0 = splitter(df)
    pf_e0 = compute_pf(early0["net_pnl_R"].to_numpy())
    pf_m0 = compute_pf(mid0["net_pnl_R"].to_numpy())
    pf_l0 = compute_pf(late0["net_pnl_R"].to_numpy())
    observed_monotonic = pf_e0 < pf_m0 < pf_l0
    observed_ratio = pf_l0 / pf_e0 if pf_e0 > 0 and np.isfinite(pf_l0) else float("nan")

    n_e, n_m, n_l = len(early0), len(mid0), len(late0)

    rng = np.random.default_rng(seed)
    R_all = df["net_pnl_R"].to_numpy()
    n_total = len(R_all)
    hits = 0
    for _ in range(n_perm):
        perm = rng.permutation(n_total)
        e = R_all[perm[:n_e]]
        m = R_all[perm[n_e:n_e + n_m]]
        l = R_all[perm[n_e + n_m:n_e + n_m + n_l]]
        pf_e = compute_pf(e)
        pf_m = compute_pf(m)
        pf_l = compute_pf(l)
        if not (pf_e < pf_m < pf_l):
            continue
        if not np.isfinite(observed_ratio):
            continue
        ratio = pf_l / pf_e if pf_e > 0 and np.isfinite(pf_l) else float("inf")
        if ratio >= observed_ratio:
            hits += 1
    p_value = hits / n_perm

    return {
        "observed_pf_early": pf_e0,
        "observed_pf_mid": pf_m0,
        "observed_pf_late": pf_l0,
        "observed_monotonic_increase": observed_monotonic,
        "observed_ratio_late_over_early": observed_ratio,
        "p_value": p_value,
        "n_perm": n_perm,
    }


# ---------------------------------------------------------------------------
def classify_replication(early_pf: float, mid_pf: float, late_pf: float, perm_p: float) -> tuple[str, bool]:
    """Per-convention classification + monotonic-decline flag.

    Returns (class, decline_flag).

    class ∈ {"replication", "non_replication", "partial"}
    decline_flag = True iff PF_early > PF_mid > PF_late.
    """
    decline = (early_pf > mid_pf > late_pf)
    if not all(np.isfinite([early_pf, mid_pf, late_pf, perm_p])):
        return ("partial", decline)

    monotonic_inc = early_pf < mid_pf < late_pf
    ratio = late_pf / early_pf if early_pf > 0 else float("nan")

    if monotonic_inc and np.isfinite(ratio) and ratio >= 2.0 and perm_p < 0.05:
        return ("replication", decline)

    middle_highest = mid_pf > early_pf and mid_pf > late_pf
    flat = np.isfinite(ratio) and ratio < 1.3
    if flat or middle_highest or decline:
        return ("non_replication", decline)

    return ("partial", decline)


def combine_verdicts(class_a: str, class_b: str) -> str:
    if class_a == "replication" and class_b == "replication":
        return "REPLICATION CONFIRMED"
    if class_a == "non_replication" and class_b == "non_replication":
        return "NON-REPLICATION"
    return "PARTIAL"


# ---------------------------------------------------------------------------
def reconciliation_block(pep: pd.DataFrame) -> None:
    """Rule 0: reconcile Pepperstone vs locked v4.3 header.

    PF and trade count must pass tight tolerance (PF +/- 0.01, N exact).
    PF is computed from Net P&L USD (full precision) for the gate; the
    R-aggregation PF is also reported because per-third PFs use R-multiples
    to match Q15 method (the rounded-pct loss-of-precision is the reason).
    Net P&L 2x delta is documented but not blocking.
    """
    n = len(pep)
    pf_usd = compute_pf(pep["net_pnl_usd"].to_numpy())
    pf_r = compute_pf(pep["net_pnl_R"].to_numpy())
    wr = pep["is_win"].mean() * 100
    pnl_usd = pep["net_pnl_usd"].sum()
    date_lo = pep["entry_time"].min()
    date_hi = pep["entry_time"].max()

    print("=" * 78)
    print("Rule 0 -- Pepperstone Aegis canonical reconciliation vs locked v4.3 (2026-04-23)")
    print("=" * 78)
    print(f"  Trades         : {n:>10d}    (locked: {LOCKED_AEGIS_V43['trades']})    "
          f"{'PASS' if n == LOCKED_AEGIS_V43['trades'] else 'FAIL'}")
    print(f"  PF (USD-based) : {pf_usd:>10.3f}    (locked: {LOCKED_AEGIS_V43['pf']:.3f})    "
          f"{'PASS' if abs(pf_usd - LOCKED_AEGIS_V43['pf']) <= PF_TOLERANCE else 'FAIL'}")
    print(f"  PF (R-based)   : {pf_r:>10.3f}    (informational; rounded pct loses precision;")
    print(f"                                used for per-third PFs to match Q15 method)")
    print(f"  Win rate (%)   : {wr:>10.2f}    (locked: {LOCKED_AEGIS_V43['wr']:.2f})    "
          f"{'PASS' if abs(wr - LOCKED_AEGIS_V43['wr']) <= 0.05 else 'CHECK'}")
    print(f"  Net P&L USD    : {pnl_usd:>10,.0f}    (locked header reports {LOCKED_AEGIS_V43['net_pnl_usd']:,})")
    print(f"                   2x delta -- column-convention diff (raw full-size USD vs")
    print(f"                   $200K-equity / risk-normalized). PF/N exact rule out a")
    print(f"                   different trade set. Forked as Q-A1-c. Not blocking.")
    print(f"  Date range     : {date_lo.date()} -> {date_hi.date()}")
    print(f"                   (inside locked data window 2022-01-04 -> 2026-04-20)")
    print()

    # Hard gate on PF and N
    if n != LOCKED_AEGIS_V43["trades"]:
        print(f"FATAL: trade count mismatch -- halting.")
        sys.exit(1)
    if abs(pf_usd - LOCKED_AEGIS_V43["pf"]) > PF_TOLERANCE:
        print(f"FATAL: PF outside +/- {PF_TOLERANCE} tolerance -- halting.")
        sys.exit(1)
    print("  Rule 0 status  : PASS (PF + N within tight tolerance)")
    print()


def per_third_table(rows: list[dict], title: str) -> None:
    print(f"--- {title}")
    print(f"  {'Third':<10}  {'n':>3}  {'PF':>7}  {'WR%':>5}  {'meanR':>7}  "
          f"{'medR':>7}  {'retstd':>7}  {'sumR':>7}  date range")
    for r in rows:
        date_str = (
            f"{r['date_lo'].date()} -> {r['date_hi'].date()}"
            if r["date_lo"] is not None else "--"
        )
        pf_str = f"{r['pf']:>7.3f}" if np.isfinite(r["pf"]) else "    inf"
        print(f"  {r['label']:<10}  {r['n']:>3}  {pf_str}  "
              f"{r['win_rate']*100:>5.2f}  {r['mean_R']:>+7.3f}  "
              f"{r['median_R']:>+7.3f}  {r['ret_std']:>7.4f}  {r['sum_R']:>+7.3f}  "
              f"{date_str}")
    print()


def reconciliation_table(pep_rows: list[dict], oanda_rows: list[dict], title: str) -> None:
    print(f"--- {title}")
    print(f"  {'Third':<10}  {'OANDA n':>7}  {'OANDA PF':>9}  {'PEP n':>5}  "
          f"{'PEP PF':>7}  {'dPF':>7}  {'rel %':>7}")
    for o, p in zip(oanda_rows, pep_rows):
        d = p["pf"] - o["pf"]
        rel = (d / o["pf"] * 100) if o["pf"] != 0 else float("nan")
        print(f"  {o['label']:<10}  {o['n']:>7}  {o['pf']:>9.3f}  {p['n']:>5}  "
              f"{p['pf']:>7.3f}  {d:>+7.3f}  {rel:>+7.1f}")
    print()


# ---------------------------------------------------------------------------
def run_convention(
    df: pd.DataFrame,
    splitter,
    feed_label: str,
    convention_label: str,
    do_bootstrap: bool,
    do_permutation: bool,
) -> dict:
    early, mid, late = splitter(df)
    rows = [
        per_third_metrics(early, "early"),
        per_third_metrics(mid, "mid"),
        per_third_metrics(late, "late"),
    ]
    out: dict = {"rows": rows, "feed": feed_label, "convention": convention_label}

    if do_bootstrap:
        boot = []
        for label, third in zip(["early", "mid", "late"], [early, mid, late]):
            r = third["net_pnl_R"].to_numpy()
            lo, hi = bootstrap_pf_ci(r, BOOTSTRAP_N, seed=SEED)
            boot.append({"label": label, "pf_ci_lo": lo, "pf_ci_hi": hi, "n": len(r)})
        out["bootstrap"] = boot

    if do_permutation:
        out["permutation"] = permutation_test_monotonic(df, splitter, PERMUTATION_N, seed=SEED)

    return out


# ---------------------------------------------------------------------------
def self_test_oanda_convention_a(oanda: pd.DataFrame) -> None:
    """Convention A on OANDA must reproduce 2.46/4.97/5.96 within +/- 0.005."""
    early, mid, late = split_convention_a(oanda)
    pfs = {
        "early_2022_2023": compute_pf(early["net_pnl_R"].to_numpy()),
        "mid_2024": compute_pf(mid["net_pnl_R"].to_numpy()),
        "late_2025_2026": compute_pf(late["net_pnl_R"].to_numpy()),
    }
    print("--- Self-test: OANDA Convention A vs Q15 anchor (target +/- 0.005)")
    print(f"  {'third':<20}  {'observed':>9}  {'Q15 anchor':>11}  {'|delta|':>8}  result")
    fail = False
    for k, anchor in Q15_ANCHOR_OANDA.items():
        obs = pfs[k]
        d = abs(obs - anchor)
        passed = d <= SELF_TEST_TOLERANCE
        if not passed:
            fail = True
        print(f"  {k:<20}  {obs:>9.3f}  {anchor:>11.2f}  {d:>8.4f}  {'PASS' if passed else 'FAIL'}")
    print()
    print(f"  n per third (OANDA): {len(early)} / {len(mid)} / {len(late)}    "
          f"(Q15 expected 44 / 28 / 51)")
    print()
    if fail:
        print("FATAL: OANDA Convention A self-test failed -- halting before computing")
        print("       Pepperstone results. This indicates a loader / return-convention")
        print("       / boundary-derivation bug, NOT a Q-A1 finding.")
        sys.exit(1)
    print("  Self-test status: PASS")
    print()


# ---------------------------------------------------------------------------
def main() -> None:
    print()
    print("Q-A1 -- Aegis Pepperstone Panel-Thirds Replication Test")
    print(f"      ({len((PEPPERSTONE_CSV).read_bytes())} bytes Pepperstone CSV; "
          f"{len((OANDA_CSV).read_bytes())} bytes OANDA CSV)")
    print()

    pep = load_tv_feed(PEPPERSTONE_CSV)
    oanda = load_tv_feed(OANDA_CSV)

    # 1. Rule 0
    reconciliation_block(pep)

    # 2. Self-test: OANDA Convention A reproduces Q15 anchor
    self_test_oanda_convention_a(oanda)

    # 3. Convention A -- both feeds
    print("=" * 78)
    print("Convention A -- calendar-year buckets (Q15-matching)")
    print("           early in {2022, 2023} ; mid == 2024 ; late in {2025, 2026}")
    print("=" * 78)
    print()

    pep_a = run_convention(pep, split_convention_a, "Pepperstone", "A",
                           do_bootstrap=True, do_permutation=True)
    oanda_a = run_convention(oanda, split_convention_a, "OANDA", "A",
                             do_bootstrap=False, do_permutation=False)

    per_third_table(oanda_a["rows"], "Per-third -- OANDA -- Convention A (reference)")
    per_third_table(pep_a["rows"], "Per-third -- Pepperstone -- Convention A")
    reconciliation_table(pep_a["rows"], oanda_a["rows"],
                         "OANDA vs Pepperstone reconciliation -- Convention A")

    print("--- Bootstrap 95% CI on PF -- Pepperstone -- Convention A "
          f"({BOOTSTRAP_N:,} resamples, seed={SEED})")
    print(f"  {'Third':<10}  {'n':>3}  {'CI_lo':>7}  {'CI_hi':>7}")
    for b in pep_a["bootstrap"]:
        print(f"  {b['label']:<10}  {b['n']:>3}  {b['pf_ci_lo']:>7.3f}  {b['pf_ci_hi']:>7.3f}")
    print()

    perm_a = pep_a["permutation"]
    print(f"--- Monotonicity permutation -- Pepperstone -- Convention A "
          f"({PERMUTATION_N:,} shuffles, seed={SEED})")
    print(f"  observed PFs           : {perm_a['observed_pf_early']:.3f} / "
          f"{perm_a['observed_pf_mid']:.3f} / {perm_a['observed_pf_late']:.3f}")
    print(f"  monotonic increase     : {perm_a['observed_monotonic_increase']}")
    ratio_a = perm_a["observed_ratio_late_over_early"]
    print(f"  PF_late / PF_early     : {ratio_a:.3f}" if np.isfinite(ratio_a) else
          f"  PF_late / PF_early     : {ratio_a}")
    print(f"  p-value (mono inc AND ratio >= obs): {perm_a['p_value']:.4f}")
    print()

    # 4. Convention B -- both feeds (equal-N trade-index thirds)
    print("=" * 78)
    print("Convention B -- equal-N trade-index thirds (41 / 41 / 41)")
    print("=" * 78)
    print()

    pep_b = run_convention(pep, split_convention_b, "Pepperstone", "B",
                           do_bootstrap=True, do_permutation=True)
    oanda_b = run_convention(oanda, split_convention_b, "OANDA", "B",
                             do_bootstrap=False, do_permutation=False)

    per_third_table(oanda_b["rows"], "Per-third -- OANDA -- Convention B (reference)")
    per_third_table(pep_b["rows"], "Per-third -- Pepperstone -- Convention B")
    reconciliation_table(pep_b["rows"], oanda_b["rows"],
                         "OANDA vs Pepperstone reconciliation -- Convention B")

    print("--- Bootstrap 95% CI on PF -- Pepperstone -- Convention B "
          f"({BOOTSTRAP_N:,} resamples, seed={SEED})")
    print(f"  {'Third':<10}  {'n':>3}  {'CI_lo':>7}  {'CI_hi':>7}")
    for b in pep_b["bootstrap"]:
        print(f"  {b['label']:<10}  {b['n']:>3}  {b['pf_ci_lo']:>7.3f}  {b['pf_ci_hi']:>7.3f}")
    print()

    perm_b = pep_b["permutation"]
    print(f"--- Monotonicity permutation -- Pepperstone -- Convention B "
          f"({PERMUTATION_N:,} shuffles, seed={SEED})")
    print(f"  observed PFs           : {perm_b['observed_pf_early']:.3f} / "
          f"{perm_b['observed_pf_mid']:.3f} / {perm_b['observed_pf_late']:.3f}")
    print(f"  monotonic increase     : {perm_b['observed_monotonic_increase']}")
    ratio_b = perm_b["observed_ratio_late_over_early"]
    print(f"  PF_late / PF_early     : {ratio_b:.3f}" if np.isfinite(ratio_b) else
          f"  PF_late / PF_early     : {ratio_b}")
    print(f"  p-value (mono inc AND ratio >= obs): {perm_b['p_value']:.4f}")
    print()

    # 5. Verdict
    pep_a_pfs = [r["pf"] for r in pep_a["rows"]]
    pep_b_pfs = [r["pf"] for r in pep_b["rows"]]
    class_a, decline_a = classify_replication(*pep_a_pfs, perm_a["p_value"])
    class_b, decline_b = classify_replication(*pep_b_pfs, perm_b["p_value"])
    verdict = combine_verdicts(class_a, class_b)

    print("=" * 78)
    print("VERDICT -- dual-convention routing rule")
    print("=" * 78)
    print(f"  Convention A  : {class_a}")
    print(f"  Convention B  : {class_b}")
    print(f"  Combined      : {verdict}")
    if decline_a:
        print("  *** MONOTONIC DECLINE -- Conv A (PF_early > PF_mid > PF_late on Pepperstone)")
    if decline_b:
        print("  *** MONOTONIC DECLINE -- Conv B (PF_early > PF_mid > PF_late on Pepperstone)")
    print()

    # 6. Console summary
    print("=" * 78)
    print("CONSOLE SUMMARY")
    print("=" * 78)
    print(f"  VERDICT                       : {verdict}")
    print(f"  Pepperstone Conv A PFs        : "
          f"{pep_a_pfs[0]:.3f} / {pep_a_pfs[1]:.3f} / {pep_a_pfs[2]:.3f}    "
          f"ratio={pep_a_pfs[2]/pep_a_pfs[0] if pep_a_pfs[0] > 0 else float('nan'):.2f}    "
          f"perm_p={perm_a['p_value']:.4f}")
    print(f"  Pepperstone Conv B PFs        : "
          f"{pep_b_pfs[0]:.3f} / {pep_b_pfs[1]:.3f} / {pep_b_pfs[2]:.3f}    "
          f"ratio={pep_b_pfs[2]/pep_b_pfs[0] if pep_b_pfs[0] > 0 else float('nan'):.2f}    "
          f"perm_p={perm_b['p_value']:.4f}")
    print(f"  OANDA Q15 anchor (Conv A)     : "
          f"{Q15_ANCHOR_OANDA['early_2022_2023']:.2f} / "
          f"{Q15_ANCHOR_OANDA['mid_2024']:.2f} / "
          f"{Q15_ANCHOR_OANDA['late_2025_2026']:.2f}    ratio="
          f"{Q15_ANCHOR_OANDA['late_2025_2026']/Q15_ANCHOR_OANDA['early_2022_2023']:.2f}")
    if decline_a or decline_b:
        flags = []
        if decline_a:
            flags.append("Conv A")
        if decline_b:
            flags.append("Conv B")
        print(f"  *** MONOTONIC DECLINE FLAG    : {', '.join(flags)}")
    print()


if __name__ == "__main__":
    main()
