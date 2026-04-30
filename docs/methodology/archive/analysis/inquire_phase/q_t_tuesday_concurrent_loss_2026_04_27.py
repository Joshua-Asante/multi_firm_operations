"""Q-T — Tuesday-cohort bar-level concurrent-loss falsifiability — 2026-04-27.

Tests whether O4's bar-level adverse-window autocorrelation (lags 1-4 z>5-14,
15.6x iid run-length excess) translates into a multi-strategy concurrent-loss
rate that EXCEEDS Q14's daily-level finding (7.5% vs 7.1%, MW p=0.19) when we
restrict attention to Tuesdays — the one weekday where all three strategies
can be session-active.

Pre-Q gate (per brief, INQHIORI v2 §3):
  D: Delete non-Tuesday days (temporal scope, permitted §5) and single-strategy-active
     windows on Tuesdays (out-of-scope D-test: question is overlap-day concurrency).
     NOT deleting by mechanism plausibility, macro-event tag, signal strength, or
     model fit (forbidden self-check).
  S: Compress to per-overlap-window binary indicator concurrent_loss[t]=1 iff
     >=2 session-active strategies' instruments are simultaneously 1σ-adverse-down.
  A: Reuse Q14's per-instrument adversity definition (rolling 60-day std, 1σ
     threshold, long-only down direction) — direct comparability is the
     preservation criterion in S.

Halt conditions (any one halts execution):
  1. Phase 0 provenance fails on any bar file.
  2. Tuesday-overlap window count < 100.
  3. Q14's adversity threshold cannot be reproduced from the existing definition.
  4. Forbidden D-test surfaces during implementation.
  5. Time budget breach.

Per AMENDMENT_oanda_rescope.md: OANDA-proxy substrate. canonical_status=PROXY
end-to-end. NO Action verdict admissible regardless of result.

Operational metadata (schedules) sourced from:
  - analysis/notice_phase/findings_2026-04-26.md §G2 (Q14 closure):
    Guardian Mon/Tue/Thu, Striker Tue/Fri, Aegis Mon/Tue/Wed.
  - scripts/identify/2026-04-26/filters.py (locked-Pine reconstruction —
    operational metadata, NOT a Rule 0 read; Rule 0 does not bind on Q-T):
    * Guardian session 08:00-16:00 NY chart-TZ, Mon/Tue/Thu.
    * Striker  session 13:00-17:00 UTC,        Tue/Fri.
    * Aegis    session 10:00-13:45 NY chart-TZ, Mon/Tue/Wed.

Reproduce: python analysis/inquire_phase/q_t_tuesday_concurrent_loss_2026_04_27.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
PARENT_REPO = REPO_ROOT.parent.parent.parent
BAR_DIR = PARENT_REPO / "data" / "bar_data"
TV_DIR = REPO_ROOT / "data" / "tv_exports" / "oanda"
OUT_JSON = REPO_ROOT / "analysis" / "inquire_phase" / "q_t_tuesday_2026_04_27.json"

# Phase 0 manifest (identical to Notice 2026-04-27 phase0 — re-verify at run).
MANIFEST = {
    "XAUUSD": {"path": BAR_DIR / "XAUUSD.csv", "n_rows": 101461,
               "first": "2022-01-02", "last": "2026-04-19", "broker": "OANDA"},
    "US30USD": {"path": BAR_DIR / "US30USD.csv", "n_rows": 101245,
                "first": "2022-01-02", "last": "2026-04-19", "broker": "OANDA"},
    "USDJPY": {"path": BAR_DIR / "USDJPY.csv", "n_rows": 106820,
               "first": "2022-01-02", "last": "2026-04-19", "broker": "OANDA"},
}
SYM_FOR_STRAT = {"guardian": "XAUUSD", "striker": "US30USD", "aegis": "USDJPY"}
TV_PREFIX = {
    "XAUUSD": "Guardian_Gold_v5.5_OANDA_XAUUSD",
    "US30USD": "Striker_DJ30_v4.4_OANDA_US30USD",
    "USDJPY": "Aegis_USDJPY_v4.3_OANDA_USDJPY",
}

# Q14-equivalent adversity parameters (reproduced from
# scripts/identify/2026-04-26/o4_bar_correlation.py simultaneous_adverse()).
ROLLING_WINDOW_BARS = 60 * 24 * 4   # 60 days × 24h × 4 bars/h = 5760
ROLLING_MIN_PERIODS = 500
SIGMA_THRESHOLD = 1.0
THIN_FLOOR_N = 100


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def phase0_verify() -> dict:
    """Re-verify bar files vs manifest. Halt on any failure."""
    files = []
    for sym, info in MANIFEST.items():
        path = info["path"]
        if not path.exists():
            files.append({"symbol": sym, "PASS": False, "reason": f"missing: {path}"})
            continue
        sha = sha256_file(path)
        df = pd.read_csv(path)
        first = pd.to_datetime(df["time"].iloc[0]).date().isoformat()
        last = pd.to_datetime(df["time"].iloc[-1]).date().isoformat()
        tv_matches = list(TV_DIR.glob(f"{TV_PREFIX[sym]}*.csv"))
        checks = {
            "row_count_matches_manifest": len(df) == info["n_rows"],
            "first_ts_matches_manifest": first == info["first"],
            "last_ts_matches_manifest": last == info["last"],
            "tv_export_oanda_present": (
                len(tv_matches) == 1 and "oanda" in tv_matches[0].name.lower()
            ),
        }
        files.append({
            "symbol": sym, "path": str(path), "sha256": sha, "n_rows": len(df),
            "first_ts": first, "last_ts": last, "broker_via_tv_export": info["broker"],
            "checks": checks, "PASS": all(checks.values()),
        })
    return {
        "scope": "Q-T Inquire 2026-04-27 over OANDA-proxy corpus",
        "amendment_binding": (
            "docs/methodology/identify_corpus/2026-04-26/AMENDMENT_oanda_rescope.md"
        ),
        "canonical_status": "PROXY",
        "files": files,
        "all_pass": all(f["PASS"] for f in files),
    }


def build_returns_panel() -> pd.DataFrame:
    """Inner-join 15min log-return panel across the three instruments."""
    closes = {}
    for sym in ["XAUUSD", "US30USD", "USDJPY"]:
        df = pd.read_csv(BAR_DIR / f"{sym}.csv")
        df["time"] = pd.to_datetime(df["time"], utc=True, format="ISO8601")
        df = df.set_index("time").sort_index()
        closes[sym] = df["close"]
    px = pd.concat(closes, axis=1).dropna()
    rets = np.log(px / px.shift(1)).dropna()
    return rets


def per_instrument_adverse(rets: pd.DataFrame) -> pd.DataFrame:
    """Q14-equivalent per-instrument 1σ-adverse flags (long-only → down)."""
    rolling_std = rets.rolling(ROLLING_WINDOW_BARS, min_periods=ROLLING_MIN_PERIODS).std()
    adverse = rets < -SIGMA_THRESHOLD * rolling_std
    return adverse.astype(int)


def session_active_flags(idx: pd.DatetimeIndex) -> pd.DataFrame:
    """Per-bar session-active flag per strategy.

    Day filter + session window per locked schedule. Hour-block filters from
    Pine (e.g. Guardian H12 latch, Aegis TueH10) are NOT applied here — the
    question is "could this strategy potentially trade in this 15min window?"
    at the schedule level. This matches the brief's "session-active per locked
    schedules (... in EMA-session windows / in 13-17 UTC / 10:00-13:45 EST)"
    framing, which references session windows, not bar-level filter blocks.
    """
    # Pine dayofweek convention (Mon=0..Sun=6 in Python):
    py_dow_utc = pd.Series(idx.dayofweek, index=idx)  # UTC dow
    ny = idx.tz_convert("America/New_York")
    py_dow_ny = pd.Series(ny.dayofweek, index=idx)
    ny_hour = pd.Series(ny.hour, index=idx)
    ny_minute = pd.Series(ny.minute, index=idx)
    utc_hour = pd.Series(idx.hour, index=idx)

    # Guardian: Mon/Tue/Thu × 08:00-16:00 NY
    guardian_active = (
        py_dow_ny.isin([0, 1, 3]) & (ny_hour >= 8) & (ny_hour < 16)
    ).astype(int)

    # Striker: Tue/Fri (UTC) × 13:00-17:00 UTC
    striker_active = (
        py_dow_utc.isin([1, 4]) & (utc_hour >= 13) & (utc_hour < 17)
    ).astype(int)

    # Aegis: Mon/Tue/Wed × 10:00-13:45 NY (minute-precise end)
    ny_min_of_day = ny_hour * 60 + ny_minute
    aegis_active = (
        py_dow_ny.isin([0, 1, 2]) & (ny_min_of_day >= 10 * 60) & (ny_min_of_day < 13 * 60 + 45)
    ).astype(int)

    return pd.DataFrame({
        "guardian_active": guardian_active,
        "striker_active": striker_active,
        "aegis_active": aegis_active,
    }, index=idx)


def macro_event_descriptive(times: pd.Series) -> dict:
    """Descriptive composition of macro-event windows in the cohort.
    NOT a deletion criterion — tag-and-preserve (brief forbidden-D-test rule)."""
    if len(times) == 0:
        return {"n": 0, "pct_nfp": 0.0, "pct_fomc": 0.0}
    dow = times.dt.dayofweek
    hour = times.dt.hour
    minute = times.dt.minute
    dom = times.dt.day
    nfp_mask = (dow == 4) & (dom <= 7) & (
        ((hour == 12) & (minute >= 30)) | ((hour == 13) & (minute <= 30))
    )
    fomc_mask = (dow == 2) & (hour >= 18) & (hour <= 19)
    return {
        "n": int(len(times)),
        "pct_in_nfp_first_fri_1230_1330_utc": float(nfp_mask.mean()),
        "pct_in_fomc_wed_1800_1959_utc": float(fomc_mask.mean()),
    }


def two_sample_test(a: np.ndarray, b: np.ndarray) -> dict:
    """Mann-Whitney U on two binary arrays."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if len(a) == 0 or len(b) == 0:
        return {"n_a": int(len(a)), "n_b": int(len(b)), "mw_u": None, "mw_p": None}
    res = {
        "n_a": int(len(a)),
        "n_b": int(len(b)),
        "rate_a": float(a.mean()),
        "rate_b": float(b.mean()),
        "diff_pp": float((a.mean() - b.mean()) * 100),
    }
    try:
        from scipy.stats import mannwhitneyu
        u, p = mannwhitneyu(a, b, alternative="two-sided")
        res["mw_u"] = float(u)
        res["mw_p"] = float(p)
    except ImportError:
        res["mw_u"], res["mw_p"] = None, None
    return res


def bootstrap_ci_diff(a: np.ndarray, b: np.ndarray, n_resamples: int = 1000,
                      seed: int = 42) -> dict:
    """Bootstrap 95% CI on rate(a) - rate(b)."""
    rng = np.random.default_rng(seed)
    diffs = np.empty(n_resamples)
    for i in range(n_resamples):
        sa = rng.choice(a, size=len(a), replace=True)
        sb = rng.choice(b, size=len(b), replace=True)
        diffs[i] = sa.mean() - sb.mean()
    return {
        "n_resamples": n_resamples,
        "ci_lower_pp": float(np.percentile(diffs, 2.5) * 100),
        "ci_upper_pp": float(np.percentile(diffs, 97.5) * 100),
        "median_pp": float(np.percentile(diffs, 50) * 100),
    }


def main():
    # Phase 0
    p0 = phase0_verify()
    if not p0["all_pass"]:
        print("HALT: Phase 0 provenance failed.", file=sys.stderr)
        print(json.dumps(p0, indent=2), file=sys.stderr)
        sys.exit(1)

    # Phase 1: cohort
    rets = build_returns_panel()
    adv = per_instrument_adverse(rets)
    sess = session_active_flags(rets.index)

    # Drop bars without enough rolling history (NaN std)
    valid = adv.notna().all(axis=1)
    adv = adv.loc[valid]
    sess = sess.loc[valid]
    rets = rets.loc[valid]

    n_active = sess.sum(axis=1)
    is_overlap = (n_active >= 2)

    # Pine dayofweek (Mon=0) over the index, in NY chart-TZ for "Tuesday"
    # interpretation. (Tuesday is locally-day-specific; we use NY-local.)
    ny = rets.index.tz_convert("America/New_York")
    is_tuesday = (ny.dayofweek == 1)

    # Phase 2: concurrent-loss indicator per overlap window
    # concurrent_loss = (sum of adverse flags among session-active strategies) >= 2
    adv_active_count = (
        adv["XAUUSD"].values * sess["guardian_active"].values
        + adv["US30USD"].values * sess["striker_active"].values
        + adv["USDJPY"].values * sess["aegis_active"].values
    )
    concurrent_loss = (adv_active_count >= 2).astype(int)

    overlap_idx = is_overlap.values
    tue_overlap = overlap_idx & is_tuesday
    non_tue_overlap = overlap_idx & ~is_tuesday

    n_tue = int(tue_overlap.sum())
    n_non_tue = int(non_tue_overlap.sum())

    # Phase 4 thin-cohort gate (early — halt if Tuesday count below floor)
    if n_tue < THIN_FLOOR_N:
        print(f"HALT: Tuesday-overlap windows n={n_tue} < {THIN_FLOOR_N}.", file=sys.stderr)
        sys.exit(2)

    cl_tue = concurrent_loss[tue_overlap]
    cl_non_tue = concurrent_loss[non_tue_overlap]

    # Phase 3: stats
    test = two_sample_test(cl_tue, cl_non_tue)
    boot = bootstrap_ci_diff(cl_tue, cl_non_tue, n_resamples=1000, seed=42)

    # Day breakdown of non-Tuesday overlap (descriptive — Mon is the only
    # other day where ≥2 strategies can both be session-active given the
    # locked schedules: Guardian∩Aegis on Mon).
    dow_breakdown = {}
    for d, name in zip(range(7), ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        mask = overlap_idx & (ny.dayofweek == d)
        dow_breakdown[name] = {
            "n_overlap_windows": int(mask.sum()),
            "n_concurrent_loss": int(concurrent_loss[mask].sum()),
            "concurrent_loss_rate": (
                float(concurrent_loss[mask].mean()) if mask.sum() > 0 else None
            ),
        }

    # Macro-event composition of Tuesday-cohort (descriptive, no deletion)
    tue_times = pd.Series(rets.index[tue_overlap])
    macro_tue = macro_event_descriptive(tue_times)

    # K-level decomposition (descriptive, no deletion). Mon overlap ALWAYS has
    # K=2 (Guardian+Aegis only; Striker is Tue/Fri). Tue overlap can have K=2
    # or K=3. Reporting the K=2-only sub-cohort comparison surfaces whether
    # the headline Δ is partially mechanical (≥2-of-3 vs ≥2-of-2).
    n_active_arr = sess.sum(axis=1).values
    k2_mask = (n_active_arr == 2)
    k3_mask = (n_active_arr == 3)
    tue_k2 = tue_overlap & k2_mask
    tue_k3 = tue_overlap & k3_mask
    mon_k2 = non_tue_overlap & k2_mask  # all non-Tue overlap is Mon, always K=2
    cl_tue_k2 = concurrent_loss[tue_k2]
    cl_tue_k3 = concurrent_loss[tue_k3]
    cl_mon_k2 = concurrent_loss[mon_k2]

    k_decomp = {
        "tuesday_K2_n": int(tue_k2.sum()),
        "tuesday_K2_concurrent_loss_rate": (
            float(cl_tue_k2.mean()) if tue_k2.sum() > 0 else None
        ),
        "tuesday_K3_n": int(tue_k3.sum()),
        "tuesday_K3_concurrent_loss_rate": (
            float(cl_tue_k3.mean()) if tue_k3.sum() > 0 else None
        ),
        "monday_K2_n": int(mon_k2.sum()),
        "monday_K2_concurrent_loss_rate": (
            float(cl_mon_k2.mean()) if mon_k2.sum() > 0 else None
        ),
        "matched_K2_test": (
            two_sample_test(cl_tue_k2, cl_mon_k2)
            if (tue_k2.sum() >= THIN_FLOOR_N and mon_k2.sum() >= THIN_FLOOR_N)
            else {"note": "K=2 sub-cohort below thin-floor for one or both"}
        ),
        "matched_K2_bootstrap_ci_pp": (
            bootstrap_ci_diff(cl_tue_k2, cl_mon_k2, n_resamples=1000, seed=42)
            if (tue_k2.sum() >= THIN_FLOOR_N and mon_k2.sum() >= THIN_FLOOR_N)
            else None
        ),
        "note": (
            "Mon overlap is always K=2 (G+A); Tue overlap can be K=2 or K=3. "
            "≥2-adverse-of-3 is mechanically higher-probability than "
            "≥2-adverse-of-2 even under iid — descriptive only, no deletion."
        ),
    }

    # Hypothesis branching
    delta_pp = test["diff_pp"]
    p = test["mw_p"]
    if abs(delta_pp) <= 1.0 and (p is not None and p > 0.05):
        verdict = "H_null supported"
        routing = ("Closed: Q14 robust at Tuesday-cohort resolution; daily-level "
                   "finding holds at the day-cohort with maximum schedule overlap.")
    elif delta_pp > 4.0 and (p is not None and p < 0.05):
        verdict = "H_alt_1 supported"
        routing = ("Forward (Pepperstone re-verification gated): OANDA-proxy "
                   "Tuesday cohort shows concurrent-loss elevation; Pepperstone "
                   "canonical re-verification required before any operational "
                   "implication. NO overlay or sizing modulation admissible.")
    else:
        verdict = "H_inconclusive"
        routing = ("Wait-state: re-evaluate when next ~6mo OANDA bars accumulate, "
                   "or fold into Q-G/Q-A Pepperstone re-verification when one fires.")

    out = {
        "scope": "Q-T Tuesday-cohort bar-level concurrent-loss — Inquire 2026-04-27",
        "feed": "OANDA",
        "canonical_status": "PROXY",
        "amendment_binding": (
            "docs/methodology/identify_corpus/2026-04-26/AMENDMENT_oanda_rescope.md"
        ),
        "panel_window": "2022-01-02_2026-04-19",
        "phase_0": p0,
        "adversity_definition": {
            "rolling_window_bars": ROLLING_WINDOW_BARS,
            "rolling_min_periods": ROLLING_MIN_PERIODS,
            "sigma_threshold": SIGMA_THRESHOLD,
            "direction": "down (long-only universe)",
            "source": ("scripts/identify/2026-04-26/o4_bar_correlation.py "
                       "simultaneous_adverse() — Q14-equivalent, not re-derived"),
        },
        "schedules_used": {
            "guardian": "Mon/Tue/Thu × 08:00-16:00 NY",
            "striker":  "Tue/Fri × 13:00-17:00 UTC",
            "aegis":    "Mon/Tue/Wed × 10:00-13:45 NY",
            "source": ("findings_2026-04-26.md §G2 + filters.py operational "
                       "metadata; Rule 0 does not bind on Q-T"),
        },
        "cohort_sizes": {
            "n_panel_bars_with_valid_rolling_std": int(valid.sum()),
            "n_overlap_windows": int(overlap_idx.sum()),
            "n_tuesday_overlap": n_tue,
            "n_non_tuesday_overlap": n_non_tue,
            "thin_floor_n": THIN_FLOOR_N,
            "thin_floor_passed": bool(n_tue >= THIN_FLOOR_N),
        },
        "concurrent_loss_rates": {
            "rate_tuesday": test["rate_a"],
            "rate_non_tuesday": test["rate_b"],
            "delta_pp": delta_pp,
            "mw_u": test["mw_u"],
            "mw_p": test["mw_p"],
            "bootstrap_95ci_pp": boot,
        },
        "dow_breakdown_overlap_windows": dow_breakdown,
        "macro_event_composition_tuesday": {
            **macro_tue,
            "note": "tag-and-preserve per brief; no deletion applied",
        },
        "k_level_decomposition": k_decomp,
        "hypothesis_branching": {
            "thresholds": {
                "H_null": "abs(delta) <= 1pp AND p > 0.05",
                "H_alt_1": "delta > 4pp AND p < 0.05",
                "else": "H_inconclusive",
            },
            "verdict": verdict,
            "routing_recommendation": routing,
        },
        "non_actions_mandatory": [
            "no overlay proposal",
            "no allocation modulation",
            "no dd_protection touch",
            "no parameter change",
        ],
    }

    OUT_JSON.write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
