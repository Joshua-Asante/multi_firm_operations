"""Permutation testers for Stage 1 gating.

Two test forms:

1. label_permutation_test — for blocked-setup discovery.
   H0: blocked-bar synthetic-R distribution = unblocked-bar distribution.
   Test stat: mean R of the blocked subset.
   Null: 1000× random relabeling of which bars are 'blocked' within the
   eligible-bar population (preserving N_blocked).

2. window_permutation_test — for post-exit excursion.
   H0: post-exit-window MFE distribution = random non-trade-window MFE.
   Test stat: mean MFE of the post-exit set.
   Null: 1000× random samples of the same N from the non-trade pool.

Both return (observed_stat, null_dist_array, two_sided_p).
"""
from __future__ import annotations

import numpy as np


def label_permutation_test(
    population_values: np.ndarray,
    n_blocked: int,
    *,
    n_perm: int = 1000,
    seed: int = 42,
) -> tuple[float, np.ndarray, float]:
    """Two-sided permutation test on a binary-labeled population.

    `population_values[:n_blocked]` is treated as the observed blocked subset.
    Caller is responsible for placing the observed-blocked values first.

    Returns (observed_mean, null_dist, p_two_sided).
    """
    pop = np.asarray(population_values, dtype=float)
    if n_blocked < 2 or n_blocked >= len(pop):
        raise AssertionError(
            f"label_permutation_test: n_blocked={n_blocked} not in (2, len(pop)={len(pop)})"
        )
    observed = float(pop[:n_blocked].mean())

    rng = np.random.default_rng(seed)
    null = np.empty(n_perm, dtype=float)
    n = len(pop)
    for i in range(n_perm):
        idx = rng.choice(n, size=n_blocked, replace=False)
        null[i] = pop[idx].mean()

    pop_mean = pop.mean()
    p = (np.abs(null - pop_mean) >= abs(observed - pop_mean)).mean()
    return observed, null, float(p)


def window_permutation_test(
    observed_values: np.ndarray,
    null_pool_values: np.ndarray,
    *,
    n_perm: int = 1000,
    seed: int = 42,
) -> tuple[float, np.ndarray, float]:
    """Two-sided permutation test by resampling from a null pool.

    Sample N (= len(observed_values)) from `null_pool_values` 1000×; null
    distribution is the per-resample mean.

    Returns (observed_mean, null_dist, p_two_sided).
    """
    obs = np.asarray(observed_values, dtype=float)
    obs = obs[~np.isnan(obs)]
    pool = np.asarray(null_pool_values, dtype=float)
    pool = pool[~np.isnan(pool)]
    if len(obs) < 2 or len(pool) < len(obs):
        raise AssertionError(
            f"window_permutation_test: |obs|={len(obs)}, |pool|={len(pool)}"
        )
    observed = float(obs.mean())

    rng = np.random.default_rng(seed)
    null = np.empty(n_perm, dtype=float)
    n = len(obs)
    for i in range(n_perm):
        idx = rng.choice(len(pool), size=n, replace=False)
        null[i] = pool[idx].mean()

    pool_mean = pool.mean()
    p = (np.abs(null - pool_mean) >= abs(observed - pool_mean)).mean()
    return observed, null, float(p)
