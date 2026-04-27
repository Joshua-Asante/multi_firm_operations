"""O4 — Bar-level simultaneous-adverse temporal autocorrelation, Notice 2026-04-27.

Q14 (04-26) tested at the per-day P&L level with no portfolio-DD signal. This
extension tests at the 15min bar level — does the 213-event simultaneous-adverse
window set cluster temporally at lags 1-4 windows (15min, 30min, 45min, 1h)?

Per brief: thin-cohort floor 50 events (we have 213; pass).
Forbidden D-test guard: do not delete clusters aligned with macro events
(FOMC, BOJ, NFP). Tag and preserve.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
PARENT_REPO = REPO_ROOT.parent.parent.parent
BAR_DIR = PARENT_REPO / "data" / "bar_data"
CORPUS = REPO_ROOT / "docs" / "methodology" / "identify_corpus" / "2026-04-26"

LAGS = [1, 2, 3, 4]


def build_universe() -> pd.DatetimeIndex:
    """Universe = 15min bars where all three instruments have a bar."""
    dfs = []
    for sym in ["XAUUSD", "US30USD", "USDJPY"]:
        df = pd.read_csv(BAR_DIR / f"{sym}.csv", parse_dates=["time"])
        df = df.set_index("time")
        df.index = df.index.tz_convert("UTC") if df.index.tz else df.index.tz_localize("UTC")
        dfs.append(df.index)
    common = dfs[0].intersection(dfs[1]).intersection(dfs[2])
    return common.sort_values()


def autocorr_binary(x: np.ndarray, lag: int) -> float:
    """Sample autocorrelation of a binary 0/1 array at given lag."""
    if lag == 0:
        return 1.0
    n = len(x)
    if n <= lag:
        return float("nan")
    x_centered = x - x.mean()
    num = (x_centered[:-lag] * x_centered[lag:]).sum()
    denom = (x_centered ** 2).sum()
    return float(num / denom) if denom > 0 else float("nan")


def run_length_distribution(x: np.ndarray) -> dict:
    """Distribution of consecutive-1s run lengths."""
    runs = []
    cur = 0
    for v in x:
        if v == 1:
            cur += 1
        else:
            if cur > 0:
                runs.append(cur)
            cur = 0
    if cur > 0:
        runs.append(cur)
    if not runs:
        return {"max_run": 0, "n_runs_ge2": 0, "n_runs_ge3": 0, "n_runs_ge4": 0}
    return {
        "max_run": int(max(runs)),
        "n_runs_ge2": int(sum(r >= 2 for r in runs)),
        "n_runs_ge3": int(sum(r >= 3 for r in runs)),
        "n_runs_ge4": int(sum(r >= 4 for r in runs)),
        "n_total_runs": len(runs),
    }


def expected_run_counts(p: float, n: int) -> dict:
    """Under iid Bernoulli(p), expected number of runs of length >= k."""
    # E[#runs >= k] ~ N * (1-p) * p^k * (1-p) for long sequences (approx)
    # Equivalently: E[runs of exactly length k] ~ N * (1-p)^2 * p^k
    # For >= k: sum from k to inf of N*(1-p)^2*p^j = N*(1-p)*p^k
    return {
        "expected_runs_ge2": n * (1 - p) * (p ** 2),
        "expected_runs_ge3": n * (1 - p) * (p ** 3),
        "expected_runs_ge4": n * (1 - p) * (p ** 4),
    }


def main():
    adv_df = pd.read_csv(CORPUS / "O4_simultaneous_adverse_windows.csv",
                         parse_dates=["utc_window"])
    adv_df["utc_window"] = pd.to_datetime(adv_df["utc_window"], utc=True)
    adverse_set = set(adv_df["utc_window"])

    universe = build_universe()
    if universe.tz is None:
        universe = universe.tz_localize("UTC")

    bar_index = pd.DataFrame({"time": universe})
    bar_index["adverse"] = bar_index["time"].isin(adverse_set).astype(int)

    n = len(bar_index)
    n_adv = int(bar_index["adverse"].sum())
    p_adv = n_adv / n

    # Autocorrelation at lags 1-4 over the full panel
    arr = bar_index["adverse"].values
    se_iid = 1.0 / np.sqrt(n)
    acf = {}
    for k in LAGS:
        rho = autocorr_binary(arr, k)
        z = rho / se_iid if se_iid > 0 else float("nan")
        acf[f"lag_{k}"] = {
            "rho": rho,
            "z_vs_iid_se": z,
            "iid_se": se_iid,
            "significant_2sigma": abs(z) > 2,
        }

    # Run-length distribution vs iid Bernoulli(p_adv)
    runs = run_length_distribution(arr)
    expected = expected_run_counts(p_adv, n)

    # Macro-event tag: are flagged clusters aligned with FOMC/BOJ/NFP?
    # The bar timestamps are UTC; FOMC press conferences are 18:00-19:30 UTC,
    # NFP is typically 12:30 UTC first Friday of month, BOJ varies.
    # We tag: percentage of adverse windows that fall on first-Friday-of-month
    # at 12:25-13:30 UTC (NFP-adjacent), and 18:00-19:45 UTC any Wednesday
    # (FOMC-window). This is descriptive-only, no deletion.
    adv_times = adv_df["utc_window"]
    adv_dow = adv_times.dt.dayofweek
    adv_hour = adv_times.dt.hour
    adv_min = adv_times.dt.minute
    adv_dom = adv_times.dt.day

    nfp_window_mask = (adv_dow == 4) & (adv_dom <= 7) & (
        ((adv_hour == 12) & (adv_min >= 30)) | ((adv_hour == 13) & (adv_min <= 30))
    )
    fomc_window_mask = (adv_dow == 2) & (adv_hour >= 18) & (adv_hour <= 19)
    pct_nfp = float(nfp_window_mask.mean())
    pct_fomc = float(fomc_window_mask.mean())

    out = {
        "scope": "O4 simultaneous-adverse autocorrelation — Notice 2026-04-27",
        "feed": "OANDA",
        "canonical_status": "PROXY",
        "n_universe_bars": n,
        "n_adverse_events": n_adv,
        "p_adverse": p_adv,
        "thin_floor_n": 50,
        "thin_floor_passed": n_adv >= 50,
        "autocorrelation": acf,
        "run_lengths": runs,
        "expected_under_iid": expected,
        "macro_event_tag": {
            "pct_in_nfp_window_first_fri_1230_to_1330_utc": pct_nfp,
            "pct_in_fomc_window_wed_1800_to_1959_utc": pct_fomc,
            "note": "tag-and-preserve per brief; no deletion applied",
        },
    }

    flagged = []
    for k in LAGS:
        info = acf[f"lag_{k}"]
        if info["significant_2sigma"]:
            flagged.append({
                "type": "autocorr_significant",
                "lag_15min_bars": k,
                "rho": info["rho"],
                "z_vs_iid_se": info["z_vs_iid_se"],
            })
    # Run-length excess: observed >= 2-runs vs expected
    if runs["n_runs_ge2"] > 0 and expected["expected_runs_ge2"] > 0:
        ratio_ge2 = runs["n_runs_ge2"] / expected["expected_runs_ge2"]
        if ratio_ge2 > 1.5 or ratio_ge2 < 0.67:
            flagged.append({
                "type": "run_length_ge2_excess",
                "observed": runs["n_runs_ge2"],
                "expected_iid": expected["expected_runs_ge2"],
                "ratio": ratio_ge2,
            })
    if runs["n_runs_ge3"] > 0 and expected["expected_runs_ge3"] > 0:
        ratio_ge3 = runs["n_runs_ge3"] / expected["expected_runs_ge3"]
        if ratio_ge3 > 1.5 or ratio_ge3 < 0.67:
            flagged.append({
                "type": "run_length_ge3_excess",
                "observed": runs["n_runs_ge3"],
                "expected_iid": expected["expected_runs_ge3"],
                "ratio": ratio_ge3,
            })

    out["flagged_top3"] = flagged[:3]
    out["total_flagged"] = len(flagged)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
