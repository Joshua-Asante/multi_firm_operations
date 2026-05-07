"""MSEE H7 — Out-of-sample regime forecast.

Q-MSEE-7 from docs/methodology/msee/open_questions.md.

Tests whether week t-1 features predict week t cluster better than
chance, AND whether the predicted-best strategy for the predicted
cluster outperforms the other strategies in week t (out-of-sample).

Falsifier: OOS hit-rate at or below chance (binomial CI excluding
above-chance), OR predicted-best strategy does not outperform peers
significantly OOS.

PRE-Q GATE:
  D: Rolling-origin OOS split (no leakage from future to past).
  S: Lag-1 weekly only initially; longer lags noted as follow-up.
  A: Logistic regression baseline; O(seconds-minutes).

Reproducibility: `python analysis/msee/h7_regime_forecast.py`
  (requires h2_regime_clusters.py to have run first)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "identify" / "2026-04-26"))

from common import STRATEGIES, load_bars, PARAMS  # noqa: E402

ALLOC = {s: PARAMS[s]["risk_pct"] / 100.0 for s in STRATEGIES}

H2_JSON = ROOT / "analysis" / "msee" / "h2_regime_clusters.json"
H2_DAILY_CSV = ROOT / "analysis" / "msee" / "h2_daily_clusters.csv"
DAILY_CSV = ROOT / "analysis" / "msee" / "daily_strategy_returns.csv"
OUT_JSON = ROOT / "analysis" / "msee" / "h7_regime_forecast.json"

INSTRUMENT_BAR = {
    "guardian": "XAUUSD",
    "striker": "US30USD",
    "aegis": "USDJPY",
}
SEED = 2026


def daily_features() -> pd.DataFrame:
    out = None
    for s, sym in INSTRUMENT_BAR.items():
        bars = load_bars(sym)
        bars["date"] = bars.index.normalize().date
        agg = bars.groupby("date").agg(
            close=("close", "last"),
            high=("high", "max"),
            low=("low", "min"),
        )
        bars["log_ret"] = np.log(bars["close"]).diff()
        rv = bars.groupby("date")["log_ret"].std().rename("realized_vol")
        agg = agg.join(rv)
        agg[f"{s}_ret"] = agg["close"].pct_change()
        agg[f"{s}_rv"] = agg["realized_vol"]
        agg[f"{s}_range_pct"] = (agg["high"] - agg["low"]) / agg["close"]
        keep = agg[[f"{s}_ret", f"{s}_rv", f"{s}_range_pct"]]
        out = keep if out is None else out.join(keep, how="outer")
    out.index.name = "date"
    return out.reset_index()


def weekly_aggregate(features: pd.DataFrame, daily_clusters: pd.DataFrame
                     ) -> pd.DataFrame:
    """Aggregate to ISO weeks. Features = mean across business days in
    week. Cluster label = mode (most common) cluster across the week."""
    f = features.copy()
    f["date"] = pd.to_datetime(f["date"])
    f["iso_week"] = f["date"].dt.strftime("%G-W%V")
    feat_cols = [c for c in f.columns if c not in ("date", "iso_week")]
    f_agg = f.groupby("iso_week")[feat_cols].mean().reset_index()
    # Earliest date in each iso_week for ordering.
    week_start = f.groupby("iso_week")["date"].min().reset_index().rename(
        columns={"date": "week_start"}
    )
    f_agg = f_agg.merge(week_start, on="iso_week")

    dc = daily_clusters.copy()
    dc["date"] = pd.to_datetime(dc["exit_date_ny"])
    dc["iso_week"] = dc["date"].dt.strftime("%G-W%V")
    # Mode cluster per week (only on trade-dates with valid cluster).
    valid = dc[dc["cluster"] >= 0].groupby("iso_week")["cluster"].agg(
        lambda x: int(x.mode().iloc[0]) if len(x) else -1
    ).reset_index()

    out = f_agg.merge(valid, on="iso_week", how="inner")
    return out.sort_values("week_start").reset_index(drop=True)


def rolling_origin_forecast(weekly: pd.DataFrame, train_min: int) -> dict:
    """Walk-forward: at each week t, fit on weeks <= t-1, predict week t.

    Features: lagged (week t-1's mean features). Target: week t cluster.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    feat_cols = [c for c in weekly.columns
                 if c not in ("iso_week", "week_start", "cluster")]
    X = weekly[feat_cols].values
    y = weekly["cluster"].values
    n = len(weekly)
    # Lag features by 1 week (use t-1 features to predict t).
    X_lag = np.vstack([np.full(X.shape[1], np.nan), X[:-1]])
    valid = ~np.isnan(X_lag).any(axis=1)

    preds = np.full(n, -1, dtype=int)
    truths = y.copy()
    for t in range(train_min, n):
        if not valid[t]:
            continue
        mask = valid[:t]
        Xt = X_lag[:t][mask]
        yt = y[:t][mask]
        if len(np.unique(yt)) < 2:
            continue
        scaler = StandardScaler().fit(Xt)
        Xtz = scaler.transform(Xt)
        clf = LogisticRegression(max_iter=2000, random_state=SEED)
        clf.fit(Xtz, yt)
        x_pred = scaler.transform(X_lag[t:t + 1])
        preds[t] = int(clf.predict(x_pred)[0])

    eval_mask = (preds >= 0)
    n_eval = int(eval_mask.sum())
    n_correct = int((preds[eval_mask] == truths[eval_mask]).sum())
    chance = float(np.mean([
        np.mean(truths[:t] == truths[t]) for t in range(train_min, n)
        if eval_mask[t]
    ])) if n_eval > 0 else float("nan")

    # Per-class accuracy.
    classes = sorted(np.unique(truths))
    per_class = {}
    for c in classes:
        m = eval_mask & (truths == c)
        if m.sum() == 0:
            per_class[int(c)] = {"n": 0, "recall": float("nan")}
        else:
            per_class[int(c)] = {
                "n": int(m.sum()),
                "recall": float((preds[m] == c).mean()),
            }
    # Binomial CI95 for hit-rate.
    from scipy.stats import beta
    if n_eval > 0:
        lo = float(beta.ppf(0.025, n_correct + 0.5, n_eval - n_correct + 0.5))
        hi = float(beta.ppf(0.975, n_correct + 0.5, n_eval - n_correct + 0.5))
    else:
        lo, hi = float("nan"), float("nan")

    return {
        "n_eval_weeks": n_eval,
        "n_correct": n_correct,
        "hit_rate": (n_correct / n_eval) if n_eval > 0 else float("nan"),
        "hit_rate_ci95": [lo, hi],
        "chance_baseline": chance,
        "per_class_recall": per_class,
        "predictions": preds.tolist(),
        "truths": truths.tolist(),
    }


def predicted_best_strategy_test(weekly: pd.DataFrame, fc: dict, h2: dict,
                                 daily: pd.DataFrame) -> dict:
    """For weeks where forecast was made, check if the predicted-best
    strategy outperforms the other two in that week (OOS by construction).
    """
    k = h2["k_primary"]
    best_per_cluster = {}
    cells = h2["primary_cells"]
    df_cells = pd.DataFrame(cells)
    # Weight mean_R by allocation so we compare portfolio contributions,
    # not raw R-multiples (which scale inversely to risk_pct).
    df_cells["weighted_mean_R"] = df_cells.apply(
        lambda r: r["mean_R"] * ALLOC[r["strategy"]] if pd.notna(r["mean_R"]) else np.nan,
        axis=1,
    )
    for c in range(k):
        sub = df_cells[(df_cells["cluster"] == c)
                       & df_cells["weighted_mean_R"].notna()]
        if sub.empty:
            best_per_cluster[c] = None
            continue
        best_per_cluster[c] = sub.sort_values("weighted_mean_R", ascending=False
                                              ).iloc[0]["strategy"]

    daily = daily.copy()
    daily["date"] = pd.to_datetime(daily["exit_date_ny"])
    daily["iso_week"] = daily["date"].dt.strftime("%G-W%V")

    preds = fc["predictions"]
    weekly = weekly.copy()
    weekly["pred_cluster"] = preds

    eval_rows = []
    for _, w in weekly.iterrows():
        pc = int(w["pred_cluster"])
        if pc < 0 or best_per_cluster.get(pc) is None:
            continue
        pred_best_strat = best_per_cluster[pc]
        wk_trades = daily[daily["iso_week"] == w["iso_week"]]
        if wk_trades.empty:
            continue
        per_strat = {}
        for s in STRATEGIES:
            # Weighted weekly portfolio contribution per strategy.
            r = (wk_trades[f"{s}_R"] * ALLOC[s]).sum()
            per_strat[s] = float(r)
        # Did predicted-best score the highest sum-R that week?
        ranking = sorted(per_strat.items(), key=lambda kv: kv[1], reverse=True)
        rank = next(i for i, (s, _) in enumerate(ranking) if s == pred_best_strat)
        eval_rows.append({
            "iso_week": w["iso_week"],
            "predicted_cluster": pc,
            "predicted_best_strategy": pred_best_strat,
            "actual_top_strategy": ranking[0][0],
            "predicted_best_rank_actual": rank + 1,  # 1-indexed
            "per_strategy_R": per_strat,
        })
    if not eval_rows:
        return {"n_weeks": 0, "verdict": "NO EVALUABLE WEEKS"}
    df = pd.DataFrame(eval_rows)
    n = len(df)
    n_top = int((df["predicted_best_rank_actual"] == 1).sum())
    n_top2 = int((df["predicted_best_rank_actual"] <= 2).sum())
    return {
        "n_weeks": int(n),
        "n_predicted_best_was_actual_top": n_top,
        "rate_predicted_best_was_actual_top": float(n_top / n),
        "rate_predicted_best_in_top2": float(n_top2 / n),
        "chance_top_of_3": 1.0 / len(STRATEGIES),
        "best_cluster_strategy_map": best_per_cluster,
        "verdict": (
            f"POSITIVE: predicted-best was actual-top in "
            f"{n_top}/{n}={n_top/n:.2%} of weeks (chance={1/len(STRATEGIES):.2%})"
            if (n_top / n) > 1.0 / len(STRATEGIES)
            else f"NEGATIVE: predicted-best at-or-below chance "
                 f"({n_top}/{n}={n_top/n:.2%} vs {1/len(STRATEGIES):.2%})"
        ),
    }


def main() -> None:
    if not H2_JSON.exists():
        raise FileNotFoundError(f"{H2_JSON} not found — run h2_regime_clusters.py first.")
    h2 = json.loads(H2_JSON.read_text())

    feats = daily_features()
    feats["date"] = pd.to_datetime(feats["date"])
    daily_clusters = pd.read_csv(H2_DAILY_CSV, parse_dates=["exit_date_ny"])
    daily = pd.read_csv(DAILY_CSV, parse_dates=["exit_date_ny"])

    weekly = weekly_aggregate(feats, daily_clusters)

    train_min = int(len(weekly) * 0.30)
    fc = rolling_origin_forecast(weekly, train_min=train_min)
    pbs = predicted_best_strategy_test(weekly, fc, h2, daily)

    summary = {
        "question": "Q-MSEE-7 — OOS lagged regime forecast (H7)",
        "feed": "OANDA",
        "canonical_status": "PROXY",
        "n_weeks_total": int(len(weekly)),
        "train_min_weeks": train_min,
        "regime_forecast": {k_: v for k_, v in fc.items()
                            if k_ not in ("predictions", "truths")},
        "predicted_best_strategy_oos_test": pbs,
        "verdict": (
            f"H7 SUPPORTED: regime forecast hit-rate "
            f"{fc['hit_rate']:.3f} (CI95=[{fc['hit_rate_ci95'][0]:.3f},"
            f"{fc['hit_rate_ci95'][1]:.3f}]); "
            f"predicted-best top in {pbs.get('rate_predicted_best_was_actual_top', 0):.3f}"
            if (fc["hit_rate"] is not None
                and fc["hit_rate_ci95"][0] > fc.get("chance_baseline", 0)
                and pbs.get("rate_predicted_best_was_actual_top", 0)
                    > 1.0 / len(STRATEGIES))
            else f"H7 NOT SUPPORTED: hit_rate={fc['hit_rate']:.3f} "
                 f"vs chance {fc.get('chance_baseline', float('nan')):.3f}; "
                 f"predicted-best rate "
                 f"{pbs.get('rate_predicted_best_was_actual_top', float('nan')):.3f} "
                 f"vs chance {1/len(STRATEGIES):.3f}"
        ),
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2, default=str))

    print("MSEE H7 — OOS regime forecast")
    print(f"  Weeks total: {len(weekly)}, train_min={train_min} (30%)")
    print()
    print(f"  REGIME-FORECAST")
    print(f"    n_eval={fc['n_eval_weeks']}  hits={fc['n_correct']}  "
          f"hit_rate={fc['hit_rate']:.3f}  "
          f"CI95=[{fc['hit_rate_ci95'][0]:.3f},{fc['hit_rate_ci95'][1]:.3f}]")
    print(f"    chance_baseline={fc['chance_baseline']:.3f}")
    print(f"    per-class recall:")
    for c, r in fc["per_class_recall"].items():
        print(f"      cluster {c}  n={r['n']}  recall={r['recall']:.3f}")
    print()
    print(f"  PREDICTED-BEST-STRATEGY OOS")
    if pbs["n_weeks"] == 0:
        print(f"    {pbs['verdict']}")
    else:
        print(f"    n_weeks={pbs['n_weeks']}  "
              f"predicted-best was actual top in "
              f"{pbs['n_predicted_best_was_actual_top']}/{pbs['n_weeks']}="
              f"{pbs['rate_predicted_best_was_actual_top']:.2%}  "
              f"(chance={pbs['chance_top_of_3']:.2%})")
        print(f"    in top-2: {pbs['rate_predicted_best_in_top2']:.2%}")
        print(f"    cluster->best map: {pbs['best_cluster_strategy_map']}")
    print()
    print(f"  Verdict: {summary['verdict']}")
    print(f"Wrote: {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
