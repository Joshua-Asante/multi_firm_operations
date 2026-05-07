"""MSEE H2 — Regime cluster decomposition.

Q-MSEE-2 from docs/methodology/msee/open_questions.md (also tests P3).

Builds daily feature vectors from 15m bars (XAU/US30/USDJPY: daily ret,
realized vol, range%) and assigns each business day to one of k=4
clusters via k-means. Then maps each strategy's daily R back to clusters
and tests whether strategy PF differs significantly across clusters and
whether strategies have NON-OVERLAPPING "best-day" cluster.

Storage-effect condition (1) — species-specific environmental response —
is satisfied iff strategies have different best clusters AND the cluster
× strategy interaction on daily R is significant. This script's
strategy_x_cluster table feeds h6_storage_conditions.py.

Falsifier: clusters do not separate per-strategy PFs; rank-ordering of
strategies across clusters is unstable.

PRE-Q GATE:
  D: Bar-feature universe restricted to dates in the foundation
     primitive's panel window.
  S: k=4 anchored to "trend / chop / event / quiet" prior; sensitivity
     to k logged.
  A: sklearn KMeans, O(seconds); reproducible with fixed seed.

Reproducibility: `python analysis/msee/h2_regime_clusters.py`
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "identify" / "2026-04-26"))

from common import STRATEGIES, load_bars  # noqa: E402

DAILY_CSV = ROOT / "analysis" / "msee" / "daily_strategy_returns.csv"
OUT_JSON = ROOT / "analysis" / "msee" / "h2_regime_clusters.json"
OUT_CSV = ROOT / "analysis" / "msee" / "h2_daily_clusters.csv"

K = 4
K_SWEEP = (3, 4, 5, 6)
SEED = 2026

INSTRUMENT_BAR = {
    "guardian": "XAUUSD",
    "striker": "US30USD",
    "aegis": "USDJPY",
}


def daily_features() -> pd.DataFrame:
    """For each business day, compute 9 features: ret, realized vol, range%
    per instrument."""
    out = None
    for s, sym in INSTRUMENT_BAR.items():
        bars = load_bars(sym)
        bars["date"] = bars.index.normalize().date
        agg = bars.groupby("date").agg(
            close=("close", "last"),
            high=("high", "max"),
            low=("low", "min"),
        )
        # Realized vol = std of intraday 15m log-returns.
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


def cluster_features(features: pd.DataFrame, k: int, seed: int
                     ) -> tuple[np.ndarray, object]:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    feat_cols = [c for c in features.columns if c != "date"]
    X = features[feat_cols].values
    mask = np.isfinite(X).all(axis=1)
    Xz = StandardScaler().fit_transform(X[mask])
    km = KMeans(n_clusters=k, random_state=seed, n_init=10).fit(Xz)
    labels = np.full(len(features), -1, dtype=int)
    labels[mask] = km.labels_
    return labels, km


def per_strategy_per_cluster(daily: pd.DataFrame, k: int) -> pd.DataFrame:
    """For each (strategy, cluster), compute mean R, n_trade_days, gross_R,
    win_rate, PF (gross_wins / |gross_losses|). Expects 'cluster' column
    already on the dataframe."""
    rows = []
    for s in STRATEGIES:
        for c in range(k):
            sub = daily[(daily["cluster"] == c)
                        & (daily[f"{s}_n_trades"] > 0)]
            if len(sub) == 0:
                rows.append(dict(strategy=s, cluster=c, n_trade_days=0,
                                 mean_R=np.nan, gross_R=np.nan,
                                 win_rate=np.nan, pf=np.nan))
                continue
            r = sub[f"{s}_R"]
            wins = r[r > 0].sum()
            losses = -r[r < 0].sum()
            pf = float(wins / losses) if losses > 0 else float("inf")
            rows.append(dict(
                strategy=s, cluster=c,
                n_trade_days=int(len(sub)),
                mean_R=float(r.mean()),
                gross_R=float(r.sum()),
                win_rate=float((r > 0).mean()),
                pf=pf,
            ))
    return pd.DataFrame(rows)


def cluster_descriptions(features: pd.DataFrame, labels: np.ndarray, k: int
                         ) -> dict:
    """Mean of each feature within each cluster — for human-readable
    cluster names."""
    feat_cols = [c for c in features.columns if c != "date"]
    out = {}
    for c in range(k):
        mask = labels == c
        if mask.sum() == 0:
            out[c] = {"n_days": 0}
            continue
        means = features.loc[mask, feat_cols].mean()
        out[c] = {"n_days": int(mask.sum()),
                  **{col: float(v) for col, v in means.items()}}
    return out


def two_way_anova_p(daily: pd.DataFrame, k: int) -> dict:
    """Permutation test for cluster-x-strategy interaction on daily R.

    Tests whether the mean R within (strategy, cluster) cells differs
    by more than chance under cluster-shuffling. Coarse but
    distribution-free.
    """
    rng = np.random.default_rng(SEED)
    obs = []
    for s in STRATEGIES:
        for c in range(k):
            sub = daily[(daily["cluster"] == c)
                        & (daily[f"{s}_n_trades"] > 0)]
            obs.append(float(sub[f"{s}_R"].mean()) if len(sub) else 0.0)
    obs = np.array(obs)
    obs_var = float(np.var(obs))

    n_perm = 500
    perm_vars = []
    for _ in range(n_perm):
        perm_clusters = daily["cluster"].sample(frac=1.0,
                                                random_state=int(rng.integers(2**31))
                                                ).reset_index(drop=True).values
        d2 = daily.copy()
        d2["cluster"] = perm_clusters
        means = []
        for s in STRATEGIES:
            for c in range(k):
                sub = d2[(d2["cluster"] == c) & (d2[f"{s}_n_trades"] > 0)]
                means.append(float(sub[f"{s}_R"].mean()) if len(sub) else 0.0)
        perm_vars.append(float(np.var(means)))
    p = float(np.mean([v >= obs_var for v in perm_vars]))
    return {"observed_var_of_cell_means": obs_var,
            "permutation_p_value": p,
            "n_permutations": n_perm}


def main() -> None:
    feats = daily_features()
    daily = pd.read_csv(DAILY_CSV, parse_dates=["exit_date_ny"])
    daily["date"] = daily["exit_date_ny"].dt.date

    # Coerce date types so merges work cleanly.
    feats["date"] = pd.to_datetime(feats["date"]).dt.date

    # Sweep k
    sweep_results = {}
    for k in K_SWEEP:
        labels, _ = cluster_features(feats, k, SEED)
        clusters = feats[["date"]].assign(cluster=labels)
        clusters = clusters[clusters["cluster"] >= 0]
        merged = daily.merge(clusters, on="date", how="left")
        merged["cluster"] = merged["cluster"].fillna(-1).astype(int)
        cell = per_strategy_per_cluster(merged, k)
        # Per strategy, find best cluster by mean_R
        best_by_strat = (
            cell.dropna(subset=["mean_R"])
                .sort_values("mean_R", ascending=False)
                .groupby("strategy").first()["cluster"].to_dict()
        )
        sweep_results[k] = {
            "best_cluster_per_strategy": {k_: int(v) for k_, v in best_by_strat.items()},
            "best_clusters_distinct": (len(set(best_by_strat.values())) == len(STRATEGIES)),
            "cells": cell.to_dict(orient="records"),
        }

    # Primary k=4
    labels, km = cluster_features(feats, K, SEED)
    clusters = feats[["date"]].assign(cluster=labels)
    clusters = clusters[clusters["cluster"] >= 0]
    merged = daily.merge(clusters, on="date", how="left")
    merged["cluster"] = merged["cluster"].fillna(-1).astype(int)

    cell = per_strategy_per_cluster(merged, K)
    descs = cluster_descriptions(feats, labels, K)
    perm = two_way_anova_p(merged, K)

    # Output the merged daily-cluster file for h6 to consume.
    merged_out = merged[["exit_date_ny", "guardian_R", "striker_R", "aegis_R",
                         "guardian_n_trades", "striker_n_trades",
                         "aegis_n_trades", "cluster"]]
    merged_out.to_csv(OUT_CSV, index=False)

    summary = {
        "question": "Q-MSEE-2 — regime cluster decomposition (H2, P3)",
        "feed": "OANDA",
        "canonical_status": "PROXY",
        "k_primary": K,
        "k_sweep": list(K_SWEEP),
        "seed": SEED,
        "n_business_days_clustered": int((labels >= 0).sum()),
        "n_trade_dates_assigned": int((merged["cluster"] >= 0).sum()),
        "cluster_descriptions": descs,
        "permutation_test": perm,
        "primary_cells": cell.to_dict(orient="records"),
        "k_sweep_summary": {
            k: {
                "best_cluster_per_strategy": v["best_cluster_per_strategy"],
                "best_clusters_distinct": v["best_clusters_distinct"],
            }
            for k, v in sweep_results.items()
        },
    }
    summary["verdict"] = (
        f"POSITIVE: best clusters are distinct across strategies (k={K}) "
        f"AND permutation p={perm['permutation_p_value']:.3f} "
        f"=> cluster x strategy interaction is significant — H2 supported"
        if (sweep_results[K]["best_clusters_distinct"]
            and perm["permutation_p_value"] < 0.05)
        else f"WEAK or NEGATIVE: best clusters distinct={sweep_results[K]['best_clusters_distinct']}, "
             f"permutation p={perm['permutation_p_value']:.3f}"
    )
    OUT_JSON.write_text(json.dumps(summary, indent=2, default=str))

    print("MSEE H2 — Regime cluster decomposition")
    print(f"  k_primary={K}, sweep={K_SWEEP}, seed={SEED}")
    print(f"  Business days clustered: {(labels >= 0).sum()}")
    print(f"  Trade-dates assigned to a cluster: {(merged['cluster'] >= 0).sum()}")
    print()
    print(f"  Cluster descriptions (k={K}):")
    for c in range(K):
        d = descs[c]
        print(f"    cluster {c}  n={d['n_days']}  "
              f"XAU_ret={d.get('guardian_ret', float('nan')):+.4f}  "
              f"XAU_rv={d.get('guardian_rv', float('nan')):.4f}  "
              f"DJ30_ret={d.get('striker_ret', float('nan')):+.4f}  "
              f"DJ30_rv={d.get('striker_rv', float('nan')):.4f}  "
              f"USDJPY_ret={d.get('aegis_ret', float('nan')):+.4f}  "
              f"USDJPY_rv={d.get('aegis_rv', float('nan')):.4f}")
    print()
    print(f"  Per-strategy mean R / PF / n by cluster (primary k={K}):")
    pivot = cell.pivot(index="strategy", columns="cluster",
                       values=["mean_R", "pf", "n_trade_days"])
    for s in STRATEGIES:
        rR = " ".join(f"{pivot.loc[s,('mean_R',c)]:+.3f}" for c in range(K))
        rPF = " ".join(f"{pivot.loc[s,('pf',c)]:5.2f}" if not np.isnan(pivot.loc[s,('pf',c)]) else "  nan"
                       for c in range(K))
        rN = " ".join(f"{int(pivot.loc[s,('n_trade_days',c)]):4d}" for c in range(K))
        print(f"    {s:10s}  meanR=[{rR}]  PF=[{rPF}]  n=[{rN}]")
    print()
    print(f"  Best-cluster per strategy:")
    for s, c in sweep_results[K]["best_cluster_per_strategy"].items():
        print(f"    {s:10s}  -> cluster {c}")
    print(f"  Best clusters distinct: {sweep_results[K]['best_clusters_distinct']}")
    print()
    print(f"  k-sweep best-cluster distinctness:")
    for k, v in sweep_results.items():
        print(f"    k={k}  best_per_strat={v['best_cluster_per_strategy']}  "
              f"distinct={v['best_clusters_distinct']}")
    print()
    print(f"  Permutation test (cluster x strategy interaction):")
    print(f"    observed_var_of_cell_means = {perm['observed_var_of_cell_means']:.4f}")
    print(f"    p-value (n={perm['n_permutations']}) = {perm['permutation_p_value']:.4f}")
    print()
    print(f"  Verdict: {summary['verdict']}")
    print(f"Wrote: {OUT_JSON.relative_to(ROOT)}")
    print(f"       {OUT_CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
