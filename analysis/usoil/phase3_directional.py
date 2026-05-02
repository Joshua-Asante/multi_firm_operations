"""Phase 3 — USOIL M15 directional edge (Q-USOIL-3 sub-questions).

Brief:    docs/methodology/findings/2026-05-02_usoil_phase3_directional.md
Plan:     ~/.claude/plans/q-usoil-3-conditional-on-usoil-dynamic-turtle.md
Predecessor: analysis/usoil/phase1_characterize.py (Phase 1 verdict: vol-gated)

Pre-Q gate (frozen before first statistic computed):
  D1 — exclude maintenance bars (is_maintenance==True) from cohort
  D2 — exclude holiday-shortened sessions (is_holiday_short==True)
  D3 — exclude Sunday bars (Phase 1 §T2.1 DST/open-spike artefact)
  D4 — exclude ATR(14) warmup (first 14 bars)

  Forbidden D-tests committed not to apply (see plan §Pre-Q gate):
    - "Matches Striker DJ30 breakout (breakoutBars=15)?" — use N=20, not 15.
    - "Brent / Copper shows similar?" — cross-instrument, out of scope.
    - "Autocorrelation high enough to be useful?" — replaced by pre-registered
      effect-size thresholds.
    - "Would this be a 4th-strategy candidate?" — strategy design, downstream.

Sub-questions (cheapest-falsification-first):
  Q-3.1  bar-sign hit rate (conditioning, not voting)
  Q-3.2  mean log-return + PF decomposition (conditioning, not voting)
  Q-3.3  Donchian breakout follow-through ("dynamic turtle") — PRIMARY
         primary cell: N=20, K=4 (5h prior window, 1h forward window)
         secondaries:  (N=20, K=1), (N=20, K=16), (N=96, K=4)
  Q-3.4  DOW artifact gate (only fires if Q-3.3 primary passes)
         provenance: feedback_oanda_dow_feed_artifact.md;
                     2026-05-02 Stage 2 closures (commits 93b3c80, 2de9e2c).

Routing:
  This script reports Q-3.1..Q-3.4 numbers and the traversed decision branch.
  Action escalation requires a separate Pepperstone-validation loop and is out
  of scope.

Outputs:
  docs/methodology/findings/2026-05-02_usoil_phase3_results.json
  docs/methodology/findings/2026-05-02_usoil_q3_bar_sign.png
  docs/methodology/findings/2026-05-02_usoil_q3_pf_decomp.png
  docs/methodology/findings/2026-05-02_usoil_q3_donchian.png
  docs/methodology/findings/2026-05-02_usoil_q3_dow_gate.png
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
CLEAN_CSV = DATA_DIR / "bar_data" / "USOIL_oanda_m15_2022-01-04_to_2026-04-20_clean.csv"
CLEAN_HASH_FILE = DATA_DIR / "USOIL_oanda_m15_2022-01-04_to_2026-04-20_clean.sha256"

FINDINGS_DIR = REPO_ROOT / "docs" / "methodology" / "findings"
PREFIX = "2026-05-02_usoil"
PHASE1_RESULTS_JSON = FINDINGS_DIR / f"{PREFIX}_phase1_results.json"
RESULTS_JSON = FINDINGS_DIR / f"{PREFIX}_phase3_results.json"

NY_TZ = ZoneInfo("America/New_York")
RNG_SEED = 42

# Donchian (N) — prior-window length, in M15 bars
DONCHIAN_NS = [20, 96]   # 20 = 5h prior; 96 = 1 day prior
DONCHIAN_PRIMARY_N = 20
# Forward windows (K), in M15 bars
FORWARD_KS = [1, 4, 16]  # 15min, 1h, 4h
FORWARD_PRIMARY_K = 4

# Effect-size thresholds (pre-registered in plan)
Q31_HITRATE_THRESHOLD = 0.025          # |p_hat - 0.5| ≥ 0.025 economically meaningful
Q32_MEAN_THRESHOLD = 5e-4              # |mean log-ret| ≥ 5e-4 (~0.5× round-trip cost)
Q33_SIGNED_MEAN_THRESHOLD = 1e-3       # |signed_mean K=4| ≥ 1e-3 (~1× round-trip cost)
Q33_PROMOTE_SE_FLOOR = 3.0             # ≥3.0 cohort-SE separation for promotion
Q33_UNDERPOWER_N = 200                 # below: line stays Forward as underpowered
Q33_MARGINAL_PASS_N_HI = 350           # in [200, 350]: marginal-pass routes Forward-not-promoted
Q34_DOW_HALF_THRESHOLD = 5e-4          # per-DOW |signed_mean| ≥ half aggregate threshold
Q34_DOW_MIN_SAMESIGN = 3               # ≥3 of 5 DOWs same-sign for gate to pass

MIN_CELL_N = 30
BOOTSTRAP_B = 1000
BLOCK_SIZES = [1, 4, 16]   # CI sweep
PRIMARY_BLOCK = 4


# ---------------------------------------------------------------------------
# Helpers (copied verbatim from phase1_characterize.py per plan)
# ---------------------------------------------------------------------------

def _verify_hash() -> str:
    expected = CLEAN_HASH_FILE.read_text().strip().split()[0]
    h = hashlib.sha256()
    with CLEAN_CSV.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    actual = h.hexdigest()
    if actual != expected:
        raise SystemExit(f"clean CSV hash mismatch: got {actual} expected {expected}")
    print(f"data hash OK: {actual}")
    return actual


def _bartlett_ci(n: int, alpha: float = 0.05) -> float:
    z = 1.96 if alpha == 0.05 else 2.576
    return z / np.sqrt(n)


# ---------------------------------------------------------------------------
# New helpers (Phase 3)
# ---------------------------------------------------------------------------

def _binom_two_sided_p(n_up: int, n: int, p0: float = 0.5) -> float:
    """Two-sided binomial p-value via normal approximation with continuity correction.

    For N≈3000 this is essentially exact (Berry-Esseen bound is O(1/sqrt(N))).
    """
    if n == 0:
        return float("nan")
    mean = n * p0
    sd = math.sqrt(n * p0 * (1 - p0))
    if sd == 0:
        return float("nan")
    # continuity-corrected z
    diff = abs(n_up - mean) - 0.5
    if diff < 0:
        return 1.0
    z = diff / sd
    # two-sided p via complementary error fn
    return float(math.erfc(z / math.sqrt(2)))


def _trim_mean(x: np.ndarray, alpha: float) -> float:
    """Symmetric two-sided trim mean: drop alpha fraction from each tail."""
    x = np.sort(x[~np.isnan(x)])
    n = len(x)
    k = int(np.floor(n * alpha))
    if n - 2 * k <= 0:
        return float("nan")
    return float(x[k:n - k].mean())


def _tail_removed_mean(x: np.ndarray, q: float = 0.99) -> tuple[float, int]:
    """Drop bars with |x| > q-quantile of |x|, return mean of survivors and dropped count."""
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return float("nan"), 0
    abs_q = np.quantile(np.abs(x), q)
    keep = np.abs(x) <= abs_q
    return float(x[keep].mean()), int((~keep).sum())


def _block_bootstrap_mean_ci(
    x: np.ndarray, block: int, B: int = BOOTSTRAP_B, seed: int = RNG_SEED
) -> tuple[float, float]:
    """Block bootstrap CI for the mean. Block size in units of input observations.

    For block=1 this is iid bootstrap. For block≥2, resample contiguous blocks
    of length `block` (cohort events ordered by time-of-occurrence).
    """
    rng = np.random.default_rng(seed)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < max(10, block * 4):
        return float("nan"), float("nan")
    if block <= 1:
        means = [np.mean(rng.choice(x, size=n, replace=True)) for _ in range(B)]
    else:
        n_blocks = n // block
        means = []
        for _ in range(B):
            idx = rng.integers(0, n - block + 1, size=n_blocks)
            sample = np.concatenate([x[i:i + block] for i in idx])
            means.append(float(sample.mean()))
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi)


def _block_bootstrap_pvalue_two_sided(
    x: np.ndarray, block: int, null: float = 0.0, B: int = BOOTSTRAP_B, seed: int = RNG_SEED
) -> float:
    """Two-sided block-bootstrap p-value for H0: mean(x) = null, by inversion.

    Uses the percentile of `null` in the bootstrap distribution of the mean.
    p_two = 2 * min(F_boot(null), 1 - F_boot(null)) where F_boot is empirical CDF.
    """
    rng = np.random.default_rng(seed + 1)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < max(10, block * 4):
        return float("nan")
    means = []
    if block <= 1:
        for _ in range(B):
            means.append(float(np.mean(rng.choice(x, size=n, replace=True))))
    else:
        n_blocks = n // block
        for _ in range(B):
            idx = rng.integers(0, n - block + 1, size=n_blocks)
            sample = np.concatenate([x[i:i + block] for i in idx])
            means.append(float(sample.mean()))
    means = np.array(means)
    f = float((means <= null).mean())
    p_two = 2.0 * min(f, 1.0 - f)
    return p_two


def _pf_decomposition(x: np.ndarray) -> dict:
    """Mean / median / 5%-trimmed mean / tail-removed (drop |x|>q99) for a series.

    Includes block-bootstrap CIs at PRIMARY_BLOCK on the mean and median.
    Returns dict with all four point estimates and CI on mean (median CI is
    asymptotic for skew-robust comparison; we mainly use it for sign agreement).
    """
    x = x[~np.isnan(x)]
    n = int(len(x))
    if n < MIN_CELL_N:
        return {
            "n": n,
            "mean": float("nan"), "median": float("nan"),
            "trimmed_mean_5pct": float("nan"), "tail_removed_mean": float("nan"),
            "tail_removed_n_dropped": 0,
            "mean_ci95_block4": [float("nan"), float("nan")],
            "sign_agreement_4_estimators": False,
        }
    mean = float(x.mean())
    median = float(np.median(x))
    trimmed = _trim_mean(x, 0.025)  # 5% total = 2.5% each side
    tail_removed, n_dropped = _tail_removed_mean(x, q=0.99)
    mean_ci_lo, mean_ci_hi = _block_bootstrap_mean_ci(x, block=PRIMARY_BLOCK)

    sign_estimators = [mean, median, trimmed, tail_removed]
    sign_estimators = [s for s in sign_estimators if not np.isnan(s)]
    sign_agree = len({np.sign(s) for s in sign_estimators if s != 0}) <= 1

    return {
        "n": n,
        "mean": mean,
        "median": median,
        "trimmed_mean_5pct": trimmed,
        "tail_removed_mean": tail_removed,
        "tail_removed_n_dropped": n_dropped,
        "mean_ci95_block4": [mean_ci_lo, mean_ci_hi],
        "sign_agreement_4_estimators": bool(sign_agree),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    FINDINGS_DIR.mkdir(parents=True, exist_ok=True)
    data_hash = _verify_hash()

    # ---- Load Phase 1 top-3 bins (load-bearing — do not re-derive) ----
    phase1 = json.loads(PHASE1_RESULTS_JSON.read_text())
    top3_bins = [int(b) for b in phase1["T1_5_intraday_atr"]["top3_bins_by_median"]]
    pep_overlap = sorted(set(top3_bins) & {47, 48})  # Pepperstone Phase 2 overlap subset
    print(f"Phase 1 top-3 bins (OANDA): {top3_bins}")
    print(f"Pepperstone overlap subset: {pep_overlap}")

    # ---- Load + parse data (mirror Phase 1 setup) ----
    df = pd.read_csv(CLEAN_CSV)
    print(f"loaded {len(df):,} rows")

    df["time_utc"] = pd.to_datetime(
        df["time"].str[:23] + "Z",
        format="%Y-%m-%dT%H:%M:%S.%fZ",
        utc=True,
    )
    df["ny_dt"] = df["time_utc"].dt.tz_convert(NY_TZ)
    df["ny_hour"] = df["ny_dt"].dt.hour
    df["ny_minute"] = df["ny_dt"].dt.minute
    df["ny_dow"] = df["ny_dt"].dt.dayofweek  # 0=Mon
    df["ny_bin"] = df["ny_hour"] * 4 + df["ny_minute"] // 15

    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["is_maintenance"] = df["is_maintenance"].astype(str).str.lower() == "true"
    df["is_holiday_short"] = df["is_holiday_short"].astype(str).str.lower() == "true"

    # Log returns (D1: zero-out maintenance bars from return-distribution stats)
    df["log_ret"] = np.log(df["close"]).diff()
    df.loc[df["is_maintenance"], "log_ret"] = np.nan

    # ATR(14) — used for the warmup deletion (D4) and for diagnostic context
    pc = df["close"].shift(1)
    tr = np.maximum.reduce([
        (df["high"] - df["low"]).values,
        np.abs((df["high"] - pc).values),
        np.abs((df["low"] - pc).values),
    ])
    df["atr14"] = pd.Series(tr).rolling(14, min_periods=14).mean().values

    # ---- D-deletions (D1-D4) → cohort_eligible mask ----
    is_warmup = df.index < 14
    df["cohort_eligible"] = (
        (~df["is_maintenance"])              # D1
        & (~df["is_holiday_short"])          # D2
        & (df["ny_dow"] != 6)                # D3 — Sunday
        & (~is_warmup)                        # D4 — ATR warmup
    )
    n_excluded = {
        "D1_maintenance": int(df["is_maintenance"].sum()),
        "D2_holiday_short": int(df["is_holiday_short"].sum()),
        "D3_sunday": int((df["ny_dow"] == 6).sum()),
        "D4_atr_warmup": int(is_warmup.sum()),
    }
    print(f"D-deletion counts (with overlap): {n_excluded}")

    # ---- Forward windows: next-K log returns, closed-form ----
    for K in FORWARD_KS:
        df[f"next{K}_logret"] = np.log(df["close"].shift(-K) / df["close"])

    # Bar-direction (Q-3.1)
    df["bar_sign"] = np.sign(df["close"] - df["open"])
    df["bar_logret"] = np.log(df["close"] / df["open"])

    # ---- Donchian prior-N highs and lows (exclude current bar) ----
    for N in DONCHIAN_NS:
        df[f"prior{N}_high"] = df["high"].rolling(N).max().shift(1)
        df[f"prior{N}_low"] = df["low"].rolling(N).min().shift(1)
        df[f"long_break_N{N}"] = df["close"] > df[f"prior{N}_high"]
        df[f"short_break_N{N}"] = df["close"] < df[f"prior{N}_low"]

    # ---- Cohort masks ----
    is_top3 = df["ny_bin"].isin(top3_bins)
    is_overlap2 = df["ny_bin"].isin(pep_overlap) if pep_overlap else pd.Series(False, index=df.index)

    cohort_full = is_top3 & df["cohort_eligible"]
    cohort_overlap = is_overlap2 & df["cohort_eligible"]

    cohort_full_idx = df.index[cohort_full]
    cohort_overlap_idx = df.index[cohort_overlap]

    n_cohort_full = int(cohort_full.sum())
    n_cohort_overlap = int(cohort_overlap.sum())
    print(f"cohort N (top-3 OANDA full): {n_cohort_full:,}")
    print(f"cohort N (Pepperstone overlap [47,48]): {n_cohort_overlap:,}")

    # ---- Pre-step: cohort sigma (load-bearing for thresholds) ----
    cohort_logret = df.loc[cohort_full_idx, "bar_logret"].dropna().values
    cohort_sigma_bar = float(cohort_logret.std(ddof=1)) if len(cohort_logret) >= 2 else float("nan")
    # forward-K sigmas (used for cohort-SE pre-registration on Q-3.3)
    cohort_sigma_fwd = {}
    for K in FORWARD_KS:
        s = df.loc[cohort_full_idx, f"next{K}_logret"].dropna().values
        cohort_sigma_fwd[K] = float(s.std(ddof=1)) if len(s) >= 2 else float("nan")

    print(f"cohort sigma (1-bar log_ret): {cohort_sigma_bar:.5f}")
    for K in FORWARD_KS:
        print(f"cohort sigma (next{K}_logret): {cohort_sigma_fwd[K]:.5f}")

    results: dict = {
        "data_hash": data_hash,
        "phase1_top3_bins": top3_bins,
        "pepperstone_overlap_bins": pep_overlap,
        "n_bars_total": int(len(df)),
        "n_excluded_per_d_test_with_overlap": n_excluded,
        "n_cohort_full": n_cohort_full,
        "n_cohort_pep_overlap": n_cohort_overlap,
        "cohort_sigma_bar_logret": cohort_sigma_bar,
        "cohort_sigma_forward_K": {str(k): cohort_sigma_fwd[k] for k in FORWARD_KS},
        "pre_q_gate": {
            "permitted_deletions_applied": [
                "D1: maintenance-window bars",
                "D2: holiday-shortened sessions",
                "D3: Sunday bars",
                "D4: ATR(14) warmup (first 14 bars)",
            ],
            "forbidden_d_tests_committed_not_applied": [
                "Matches Striker DJ30 breakout (breakoutBars=15)? — N=20 used, not 15.",
                "Brent / Copper shows similar? — cross-instrument, out of scope.",
                "Autocorrelation high enough to be useful? — replaced by effect-size pre-reg.",
                "Would this be a 4th-strategy candidate? — strategy design, downstream.",
            ],
        },
        "thresholds": {
            "Q31_hitrate_diff_from_half": Q31_HITRATE_THRESHOLD,
            "Q32_mean_logret": Q32_MEAN_THRESHOLD,
            "Q33_signed_mean_K4": Q33_SIGNED_MEAN_THRESHOLD,
            "Q33_promotion_cohort_SE_floor": Q33_PROMOTE_SE_FLOOR,
            "Q33_underpower_N": Q33_UNDERPOWER_N,
            "Q33_marginal_pass_N_hi": Q33_MARGINAL_PASS_N_HI,
            "Q34_dow_half_threshold": Q34_DOW_HALF_THRESHOLD,
            "Q34_dow_min_samesign_count": Q34_DOW_MIN_SAMESIGN,
        },
    }

    # ====================================================================
    # Q-3.1 — Bar-sign hit rate (conditioning, not voting)
    # ====================================================================
    print("\n=== Q-3.1: bar-sign hit rate ===")
    q31 = {}
    for label, idx in [("full", cohort_full_idx), ("pep_overlap", cohort_overlap_idx)]:
        signs = df.loc[idx, "bar_sign"].dropna().values
        n = int(len(signs))
        n_up = int((signs > 0).sum())
        n_down = int((signs < 0).sum())
        n_flat = n - n_up - n_down
        # Convention: flat bars (close == open) excluded from binomial test
        n_eff = n_up + n_down
        p_hat = n_up / n_eff if n_eff > 0 else float("nan")
        bartlett = _bartlett_ci(n_eff) if n_eff > 0 else float("nan")
        ci_lo = p_hat - bartlett if not np.isnan(p_hat) else float("nan")
        ci_hi = p_hat + bartlett if not np.isnan(p_hat) else float("nan")
        p_value = _binom_two_sided_p(n_up, n_eff, p0=0.5)
        diff = abs(p_hat - 0.5) if not np.isnan(p_hat) else float("nan")
        passes_threshold = (not np.isnan(diff)) and diff >= Q31_HITRATE_THRESHOLD
        sig_at_005 = (not np.isnan(p_value)) and p_value < 0.05
        q31[label] = {
            "n": n, "n_up": n_up, "n_down": n_down, "n_flat": n_flat,
            "p_hat_up": p_hat,
            "ci95_lo": ci_lo, "ci95_hi": ci_hi,
            "p_value_two_sided": p_value,
            "diff_from_half": diff,
            "passes_economic_threshold": bool(passes_threshold),
            "sig_at_p005": bool(sig_at_005),
        }
        print(f"  [{label}] N={n} n_up={n_up} n_down={n_down} flat={n_flat}")
        print(f"           p_hat={p_hat:.4f} 95%=[{ci_lo:.4f},{ci_hi:.4f}] p={p_value:.4g} "
              f"|diff-0.5|={diff:.4f} threshold-pass={passes_threshold} sig@0.05={sig_at_005}")
    results["Q3_1_bar_sign"] = q31

    # ====================================================================
    # Q-3.2 — Mean log-return + PF decomposition
    # ====================================================================
    print("\n=== Q-3.2: mean log-return + PF decomposition ===")
    q32 = {}
    for label, idx in [("full", cohort_full_idx), ("pep_overlap", cohort_overlap_idx)]:
        x = df.loc[idx, "bar_logret"].dropna().values
        decomp = _pf_decomposition(x)
        # Block-bootstrap p-value at PRIMARY_BLOCK
        decomp["mean_p_value_block4"] = (
            _block_bootstrap_pvalue_two_sided(x, block=PRIMARY_BLOCK)
            if len(x) >= MIN_CELL_N else float("nan")
        )
        decomp["passes_economic_threshold"] = (
            (not np.isnan(decomp["mean"])) and abs(decomp["mean"]) >= Q32_MEAN_THRESHOLD
        )
        q32[label] = decomp
        print(f"  [{label}] N={decomp['n']} mean={decomp['mean']:.5f} "
              f"med={decomp['median']:.5f} trim5%={decomp['trimmed_mean_5pct']:.5f} "
              f"tail-rm={decomp['tail_removed_mean']:.5f} (drop n={decomp['tail_removed_n_dropped']})")
        print(f"           mean CI95 block=4: [{decomp['mean_ci95_block4'][0]:.5f}, "
              f"{decomp['mean_ci95_block4'][1]:.5f}] p={decomp['mean_p_value_block4']:.4g}  "
              f"sign-agree={decomp['sign_agreement_4_estimators']}")
    results["Q3_2_mean_logret_pf_decomp"] = q32

    # ====================================================================
    # Q-3.3 — Donchian breakout follow-through (PRIMARY)
    # ====================================================================
    print("\n=== Q-3.3: Donchian breakout follow-through ===")
    q33 = {"cells": {}}

    # Cohort: same as Q-3.1/3.2 (top-3 OANDA full, with sensitivity on overlap)
    for cohort_label, base_idx in [("full", cohort_full_idx), ("pep_overlap", cohort_overlap_idx)]:
        cell_results = {}
        for N in DONCHIAN_NS:
            for K in FORWARD_KS:
                long_break = df.loc[base_idx, f"long_break_N{N}"]
                short_break = df.loc[base_idx, f"short_break_N{N}"]
                # Direction
                direction = pd.Series(0, index=base_idx, dtype=float)
                direction[long_break] = 1.0
                direction[short_break] = -1.0
                is_break = direction != 0
                fwd = df.loc[base_idx, f"next{K}_logret"]
                signed = (direction * fwd).where(is_break)
                signed = signed.dropna().values
                n_evt = int(len(signed))
                n_long = int((direction[is_break] > 0).sum())
                n_short = int((direction[is_break] < 0).sum())
                base_n_eligible = int(df.loc[base_idx, f"next{K}_logret"].notna().sum())
                breakout_rate = n_evt / base_n_eligible if base_n_eligible > 0 else float("nan")

                if n_evt < MIN_CELL_N:
                    cell_results[f"N{N}_K{K}"] = {
                        "cohort_label": cohort_label,
                        "n_events": n_evt, "n_long": n_long, "n_short": n_short,
                        "breakout_rate": breakout_rate,
                        "note": f"underpowered (n={n_evt} < {MIN_CELL_N})",
                    }
                    continue

                signed_mean = float(signed.mean())
                signed_se = float(signed.std(ddof=1) / np.sqrt(n_evt))
                cohort_se_separation = (
                    abs(signed_mean) / signed_se if signed_se > 0 else float("nan")
                )

                # PF decomposition + block-bootstrap CIs at block ∈ {1, 4, 16}
                decomp = _pf_decomposition(signed)
                ci_sweep = {}
                for block in BLOCK_SIZES:
                    lo, hi = _block_bootstrap_mean_ci(signed, block=block)
                    ci_sweep[f"block{block}"] = [lo, hi]
                p_block4 = _block_bootstrap_pvalue_two_sided(signed, block=PRIMARY_BLOCK)

                # CI-sweep robustness flag (>50% disagreement on width)
                widths = [
                    (ci_sweep[f"block{b}"][1] - ci_sweep[f"block{b}"][0])
                    for b in BLOCK_SIZES
                    if not np.isnan(ci_sweep[f"block{b}"][0])
                ]
                ci_disagrees = (
                    (max(widths) - min(widths)) / max(min(widths), 1e-12) > 0.5
                    if len(widths) == len(BLOCK_SIZES) else False
                )

                cell_results[f"N{N}_K{K}"] = {
                    "cohort_label": cohort_label,
                    "n_events": n_evt,
                    "n_long_break": n_long,
                    "n_short_break": n_short,
                    "breakout_rate": breakout_rate,
                    "signed_mean": signed_mean,
                    "signed_se": signed_se,
                    "cohort_se_separation": cohort_se_separation,
                    "pf_decomposition": decomp,
                    "ci95_block_sweep": ci_sweep,
                    "ci_widths_disagree_gt50pct": bool(ci_disagrees),
                    "p_value_block4": p_block4,
                    "passes_economic_threshold": (
                        abs(signed_mean) >= Q33_SIGNED_MEAN_THRESHOLD
                    ),
                    "passes_p005_block4": (
                        (not np.isnan(p_block4)) and p_block4 < 0.05
                    ),
                    "passes_promote_se_floor": (
                        (not np.isnan(cohort_se_separation))
                        and cohort_se_separation >= Q33_PROMOTE_SE_FLOOR
                    ),
                }
                print(f"  [{cohort_label}] N={N} K={K}: n_evt={n_evt} (long={n_long} short={n_short}) "
                      f"rate={breakout_rate:.3f}")
                print(f"     signed_mean={signed_mean:.5f} SE={signed_se:.5f} "
                      f"separation={cohort_se_separation:.2f}sigma  "
                      f"p(block=4)={p_block4:.4g}  "
                      f"sign-agree={decomp['sign_agreement_4_estimators']}")

        q33["cells"][cohort_label] = cell_results

    # Primary cell evaluation (full cohort, N=20, K=4)
    primary_cell = q33["cells"]["full"].get(f"N{DONCHIAN_PRIMARY_N}_K{FORWARD_PRIMARY_K}", {})
    primary_n = primary_cell.get("n_events", 0)

    if primary_n < Q33_UNDERPOWER_N:
        primary_status = "underpowered"
    elif primary_n <= Q33_MARGINAL_PASS_N_HI:
        primary_status = "marginal_n"
    else:
        primary_status = "expected_n"

    primary_passes_thresholds = (
        primary_cell.get("passes_economic_threshold", False)
        and primary_cell.get("passes_p005_block4", False)
        and primary_cell.get("pf_decomposition", {}).get("sign_agreement_4_estimators", False)
    )
    primary_passes_promote = (
        primary_passes_thresholds
        and primary_cell.get("passes_promote_se_floor", False)
        and primary_status == "expected_n"
    )

    q33["primary_cell_summary"] = {
        "N": DONCHIAN_PRIMARY_N, "K": FORWARD_PRIMARY_K,
        "n_events": primary_n,
        "primary_n_status": primary_status,
        "passes_economic_threshold": primary_cell.get("passes_economic_threshold", False),
        "passes_p005_block4": primary_cell.get("passes_p005_block4", False),
        "passes_pf_sign_agreement": primary_cell.get("pf_decomposition", {}).get(
            "sign_agreement_4_estimators", False
        ),
        "passes_promote_se_floor": primary_cell.get("passes_promote_se_floor", False),
        "primary_passes_thresholds": primary_passes_thresholds,
        "primary_passes_promote": primary_passes_promote,
    }
    results["Q3_3_donchian_followthrough"] = q33

    # ====================================================================
    # Q-3.4 — DOW artifact gate (only fires if Q-3.3 primary passes)
    # ====================================================================
    print("\n=== Q-3.4: DOW artifact gate ===")
    q34 = {
        "fired": False,
        "provenance": (
            "feedback_oanda_dow_feed_artifact.md; 2026-05-02 Stage 2 closures of "
            "OANDA-only DOW candidates (Guardian day_wed, Striker day_mon_wed_thu) "
            "rejected at Pepperstone — commits 93b3c80, 2de9e2c."
        ),
    }

    if primary_passes_thresholds:
        q34["fired"] = True
        # Re-compute the primary-cell signed series with DOW labels
        N, K = DONCHIAN_PRIMARY_N, FORWARD_PRIMARY_K
        long_break = df.loc[cohort_full_idx, f"long_break_N{N}"]
        short_break = df.loc[cohort_full_idx, f"short_break_N{N}"]
        direction = pd.Series(0, index=cohort_full_idx, dtype=float)
        direction[long_break] = 1.0
        direction[short_break] = -1.0
        is_break = direction != 0
        fwd = df.loc[cohort_full_idx, f"next{K}_logret"]
        signed = (direction * fwd).where(is_break)
        dow = df.loc[cohort_full_idx, "ny_dow"]

        agg_sign = np.sign(primary_cell["signed_mean"])

        per_dow = {}
        same_sign_count = 0
        for d, dow_label in zip(range(5), ["Mon", "Tue", "Wed", "Thu", "Fri"]):
            mask = (dow == d) & is_break
            x = signed[mask].dropna().values
            n = int(len(x))
            if n < MIN_CELL_N:
                per_dow[dow_label] = {
                    "n": n, "signed_mean": float("nan"),
                    "same_sign_as_aggregate": False,
                    "passes_half_threshold": False,
                    "note": f"underpowered (n={n} < {MIN_CELL_N})",
                }
                continue
            mean = float(x.mean())
            se = float(x.std(ddof=1) / np.sqrt(n))
            same_sign = (np.sign(mean) == agg_sign) and (mean != 0)
            passes_half = abs(mean) >= Q34_DOW_HALF_THRESHOLD
            counts_for_gate = same_sign and passes_half
            if counts_for_gate:
                same_sign_count += 1
            per_dow[dow_label] = {
                "n": n,
                "signed_mean": mean,
                "signed_se": se,
                "same_sign_as_aggregate": bool(same_sign),
                "passes_half_threshold": bool(passes_half),
                "counts_toward_gate": bool(counts_for_gate),
            }
            print(f"  {dow_label}: n={n} mean={mean:.5f} SE={se:.5f}  "
                  f"same-sign={same_sign}  pass-half-threshold={passes_half}")

        q34["aggregate_sign"] = float(agg_sign)
        q34["per_dow"] = per_dow
        q34["same_sign_count_with_magnitude"] = same_sign_count
        q34["min_required"] = Q34_DOW_MIN_SAMESIGN
        q34["passes_dow_gate"] = same_sign_count >= Q34_DOW_MIN_SAMESIGN
        print(f"  same-sign DOW count = {same_sign_count} / 5  "
              f"min required = {Q34_DOW_MIN_SAMESIGN}  "
              f"DOW gate = {'PASS' if q34['passes_dow_gate'] else 'FAIL (artifact suspect)'}")
    else:
        print("  Q-3.4 not fired (Q-3.3 primary did not pass thresholds).")
    results["Q3_4_dow_artifact_gate"] = q34

    # ====================================================================
    # Decision routing
    # ====================================================================
    print("\n=== Decision routing ===")

    # Check secondary cells for "suggestive" status
    secondary_cells = []
    for cell_name, cell in q33["cells"].get("full", {}).items():
        if cell_name == f"N{DONCHIAN_PRIMARY_N}_K{FORWARD_PRIMARY_K}":
            continue
        if cell.get("passes_economic_threshold") and cell.get("passes_p005_block4") \
                and cell.get("pf_decomposition", {}).get("sign_agreement_4_estimators"):
            secondary_cells.append(cell_name)

    if primary_status == "underpowered":
        verdict = "FORWARD_underpowered"
        rationale = (
            f"Q-3.3 primary cell N={primary_n} < {Q33_UNDERPOWER_N} (underpower floor). "
            f"Line stays Forward as 'underpowered, gather more data'."
        )
    elif not primary_passes_thresholds:
        if secondary_cells:
            verdict = "FORWARD_secondary_only"
            rationale = (
                f"Q-3.3 primary fails thresholds; secondary cell(s) {secondary_cells} "
                f"suggestive. Line stays Forward, NOT promoted; needs replication."
            )
        else:
            verdict = "CLOSED_no_directional_edge"
            rationale = (
                "Q-3.3 primary fails thresholds and no secondary cell suggestive. "
                "Vol-gated structure has no directional edge in OANDA M15 2022-2026."
            )
    elif primary_status == "marginal_n":
        verdict = "FORWARD_marginal_pass"
        rationale = (
            f"Q-3.3 primary passes thresholds but N={primary_n} ∈ "
            f"[{Q33_UNDERPOWER_N}, {Q33_MARGINAL_PASS_N_HI}] (marginal-pass band). "
            f"Threshold and p<0.05 collapse onto each other at this N. "
            f"Forward-not-promoted."
        )
    elif not q34.get("passes_dow_gate", False):
        verdict = "CLOSED_dow_feed_artifact_suspect"
        rationale = (
            f"Q-3.3 primary passes; Q-3.4 DOW gate fails "
            f"(same-sign count = {q34.get('same_sign_count_with_magnitude', 0)} "
            f"< {Q34_DOW_MIN_SAMESIGN}). OANDA DOW feed-artifact suspect; "
            f"line routes Closed (provenance: feedback_oanda_dow_feed_artifact.md)."
        )
    elif not primary_passes_promote:
        verdict = "FORWARD_marginal_pass"
        rationale = (
            "Q-3.3 + Q-3.4 pass thresholds, but cohort-SE separation < "
            f"{Q33_PROMOTE_SE_FLOOR}σ promotion floor. Forward-not-promoted."
        )
    else:
        verdict = "FORWARD_pepperstone_visual_required"
        rationale = (
            "Q-3.3 primary passes (≥3.0σ separation), Q-3.4 DOW gate passes. "
            "Line routes Forward with Pepperstone TradingView visual validation "
            "step pending in this loop. Authoring of Pine indicator + visual-check "
            "note required before Q-USOIL-3 lands. Action escalation requires a "
            "separate strategy-design loop."
        )

    results["routing"] = {
        "verdict": verdict,
        "rationale": rationale,
        "primary_cell": q33["primary_cell_summary"],
        "secondary_suggestive_cells": secondary_cells,
    }
    print(f"VERDICT: {verdict}")
    print(f"  rationale: {rationale}")

    # ====================================================================
    # Plots
    # ====================================================================
    print("\nGenerating plots...")

    # Q-3.1 bar-sign per-bin
    fig, ax = plt.subplots(figsize=(8, 4))
    bins_for_plot = sorted(top3_bins) + ["aggregate"]
    p_hats = []
    cis = []
    ns = []
    for b in bins_for_plot:
        if b == "aggregate":
            sub = df.loc[cohort_full_idx, "bar_sign"].dropna()
        else:
            mask = cohort_full & (df["ny_bin"] == b)
            sub = df.loc[mask, "bar_sign"].dropna()
        n_up_b = int((sub > 0).sum())
        n_down_b = int((sub < 0).sum())
        n_eff_b = n_up_b + n_down_b
        ns.append(n_eff_b)
        if n_eff_b > 0:
            p = n_up_b / n_eff_b
            ci = _bartlett_ci(n_eff_b)
            p_hats.append(p)
            cis.append(ci)
        else:
            p_hats.append(float("nan"))
            cis.append(float("nan"))
    x = np.arange(len(bins_for_plot))
    labels = [f"bin {b}" if b != "aggregate" else "aggregate" for b in bins_for_plot]
    ax.bar(x, p_hats, yerr=cis, capsize=4, color=["steelblue"] * (len(bins_for_plot) - 1) + ["orange"])
    ax.axhline(0.5, color="black", ls="--", lw=0.8, label="null p=0.5")
    ax.axhline(0.5 + Q31_HITRATE_THRESHOLD, color="red", ls=":", lw=0.8,
               label=f"±{Q31_HITRATE_THRESHOLD} threshold")
    ax.axhline(0.5 - Q31_HITRATE_THRESHOLD, color="red", ls=":", lw=0.8)
    for xi, ni in zip(x, ns):
        ax.annotate(f"n={ni}", (xi, 0.45), ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("P(close > open)")
    ax.set_ylim(0.40, 0.60)
    ax.set_title("Q-3.1 bar-sign hit rate (top-3 OANDA bins, conditioning info)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(FINDINGS_DIR / f"{PREFIX}_q3_bar_sign.png", dpi=120)
    plt.close()

    # Q-3.2 PF decomposition
    fig, ax = plt.subplots(figsize=(8, 4))
    decomp_full = q32["full"]
    estimator_labels = ["mean", "median", "trim 5%", "tail-rm (q99)"]
    estimator_vals = [
        decomp_full["mean"], decomp_full["median"],
        decomp_full["trimmed_mean_5pct"], decomp_full["tail_removed_mean"],
    ]
    colors = ["steelblue", "orange", "green", "purple"]
    ax.bar(estimator_labels, estimator_vals, color=colors)
    # Add CI on the mean only
    if not np.isnan(decomp_full["mean_ci95_block4"][0]):
        ax.errorbar(
            [0], [decomp_full["mean"]],
            yerr=[[decomp_full["mean"] - decomp_full["mean_ci95_block4"][0]],
                  [decomp_full["mean_ci95_block4"][1] - decomp_full["mean"]]],
            fmt="none", color="black", capsize=4,
        )
    ax.axhline(0, color="black", lw=0.8)
    ax.axhline(Q32_MEAN_THRESHOLD, color="red", ls=":", lw=0.8,
               label=f"±{Q32_MEAN_THRESHOLD} threshold")
    ax.axhline(-Q32_MEAN_THRESHOLD, color="red", ls=":", lw=0.8)
    ax.set_ylabel("log return (per bar)")
    sign_agree_str = "✓" if decomp_full["sign_agreement_4_estimators"] else "✗"
    ax.set_title(
        f"Q-3.2 PF decomposition (top-3 OANDA full, N={decomp_full['n']}, "
        f"sign-agree={sign_agree_str}, tail-rm dropped n={decomp_full['tail_removed_n_dropped']})"
    )
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(FINDINGS_DIR / f"{PREFIX}_q3_pf_decomp.png", dpi=120)
    plt.close()

    # Q-3.3 Donchian heatmap (signed_mean × N × K) for full cohort
    cells_full = q33["cells"]["full"]
    fig, ax = plt.subplots(figsize=(8, 4))
    Ns = DONCHIAN_NS
    Ks = FORWARD_KS
    Z = np.full((len(Ns), len(Ks)), np.nan)
    Ntext = np.empty((len(Ns), len(Ks)), dtype=object)
    for i, N in enumerate(Ns):
        for j, K in enumerate(Ks):
            cell = cells_full.get(f"N{N}_K{K}", {})
            sm = cell.get("signed_mean", float("nan"))
            ne = cell.get("n_events", 0)
            Z[i, j] = sm
            Ntext[i, j] = f"{sm:.4f}\nn={ne}" if not np.isnan(sm) else f"n={ne}"
    vmax = max(abs(np.nanmin(Z)), abs(np.nanmax(Z)), Q33_SIGNED_MEAN_THRESHOLD)
    im = ax.imshow(Z, cmap="RdBu_r", aspect="auto", vmin=-vmax, vmax=vmax)
    ax.set_xticks(range(len(Ks)))
    ax.set_xticklabels([f"K={k}" for k in Ks])
    ax.set_yticks(range(len(Ns)))
    ax.set_yticklabels([f"N={n}" for n in Ns])
    for i in range(len(Ns)):
        for j in range(len(Ks)):
            ax.text(j, i, Ntext[i, j], ha="center", va="center", fontsize=8)
    # Mark primary cell
    pi = Ns.index(DONCHIAN_PRIMARY_N)
    pj = Ks.index(FORWARD_PRIMARY_K)
    ax.add_patch(plt.Rectangle((pj - 0.48, pi - 0.48), 0.96, 0.96,
                                fill=False, edgecolor="black", linewidth=2))
    ax.set_title(f"Q-3.3 Donchian signed_mean (top-3 OANDA full); primary = N=20 K=4 (boxed)")
    plt.colorbar(im, ax=ax, label="signed_mean log-ret")
    plt.tight_layout()
    plt.savefig(FINDINGS_DIR / f"{PREFIX}_q3_donchian.png", dpi=120)
    plt.close()

    # Q-3.4 DOW gate
    fig, ax = plt.subplots(figsize=(8, 4))
    if q34.get("fired", False):
        labels_dow = ["Mon", "Tue", "Wed", "Thu", "Fri"]
        means = [q34["per_dow"][d].get("signed_mean", float("nan")) for d in labels_dow]
        ses = [q34["per_dow"][d].get("signed_se", 0) for d in labels_dow]
        colors_dow = ["green" if q34["per_dow"][d].get("counts_toward_gate", False)
                      else "lightgray"
                      for d in labels_dow]
        ax.bar(labels_dow, means, yerr=ses, capsize=4, color=colors_dow)
        ax.axhline(Q34_DOW_HALF_THRESHOLD, color="red", ls=":", lw=0.8,
                   label=f"±{Q34_DOW_HALF_THRESHOLD} half-threshold")
        ax.axhline(-Q34_DOW_HALF_THRESHOLD, color="red", ls=":", lw=0.8)
        ax.axhline(0, color="black", lw=0.8)
        ax.set_ylabel(f"signed_mean (N={DONCHIAN_PRIMARY_N}, K={FORWARD_PRIMARY_K})")
        gate_str = "PASS" if q34.get("passes_dow_gate", False) else "FAIL (artifact suspect)"
        ax.set_title(f"Q-3.4 DOW gate: same-sign count = {q34['same_sign_count_with_magnitude']} / 5 → {gate_str}")
        ax.legend(fontsize=8)
    else:
        ax.text(0.5, 0.5, "Q-3.4 not fired\n(Q-3.3 primary did not pass thresholds)",
                ha="center", va="center", transform=ax.transAxes, fontsize=12)
        ax.set_xticks([])
        ax.set_yticks([])
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(FINDINGS_DIR / f"{PREFIX}_q3_dow_gate.png", dpi=120)
    plt.close()

    print(f"plots written to {FINDINGS_DIR}")

    # ---- Persist results ----
    RESULTS_JSON.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\nresults: {RESULTS_JSON}")
    print(f"verdict: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
