"""Permutation harness for H-NYFBO falsification.

Three estimators per parent brief §5 #8 (>=1000 shuffles required):

1. edge_permutation_pvalue — shuffle the sign of per-trade P&L; null distribution
   of mean P&L. Tests "is the mean significantly different from 0?".

2. correlation_permutation_pvalue — shuffle date alignment of NYFBO daily P&L
   relative to the comparison series; null distribution of Pearson correlation.
   Tests "is the observed correlation significantly different from 0?".

3. rule1_small_cell_ci — variance inflation for any regime sub-sample with n<25
   per parent brief §4 kill #6. Multiplies CI half-width by sqrt(25/n).
   Reference: docs/methodology/findings/2026-05-02_usoil_15min_characterization.md

null-test (--null-test): runs estimator 1 on a synthetic Brownian-motion null;
expects p approx 0.5 (uniform under H0).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


N_PERM_DEFAULT = 1000
RULE1_THRESHOLD = 25  # per parent brief §4 kill #6


@dataclass(frozen=True)
class PermResult:
    observed: float
    p_two_sided: float
    n: int
    n_perm: int
    rule1_inflated: bool


def edge_permutation_pvalue(
    pnl: np.ndarray,
    *,
    n_perm: int = N_PERM_DEFAULT,
    seed: int = 42,
) -> PermResult:
    """Two-sided permutation p-value on mean P&L.

    H0: mean(pnl) = 0. Null is constructed by random sign-flipping each trade
    independently. Equivalent to testing "is the directional edge real, or
    consistent with a zero-mean process with the same magnitude distribution?".

    Returns PermResult with observed mean, two-sided p, and Rule-1 flag.
    """
    pnl = np.asarray(pnl, dtype=float)
    pnl = pnl[~np.isnan(pnl)]
    n = len(pnl)
    if n < 2:
        raise AssertionError(f"edge_permutation_pvalue: n={n} < 2")

    observed = float(pnl.mean())
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm, dtype=float)
    abs_pnl = np.abs(pnl)
    for i in range(n_perm):
        signs = rng.choice([-1.0, 1.0], size=n)
        null[i] = float((signs * abs_pnl).mean())
    p = float((np.abs(null) >= abs(observed)).mean())
    return PermResult(
        observed=observed,
        p_two_sided=p,
        n=n,
        n_perm=n_perm,
        rule1_inflated=n < RULE1_THRESHOLD,
    )


def correlation_permutation_pvalue(
    x: np.ndarray,
    y: np.ndarray,
    *,
    n_perm: int = N_PERM_DEFAULT,
    seed: int = 42,
) -> PermResult:
    """Two-sided permutation p-value on Pearson correlation.

    H0: corr(x, y) = 0. Null is constructed by shuffling y's date alignment
    while preserving x order. Tests "is the observed correlation distinguishable
    from random alignment?".
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.shape != y.shape:
        raise AssertionError(f"correlation_permutation_pvalue: shape mismatch {x.shape} vs {y.shape}")
    mask = ~(np.isnan(x) | np.isnan(y))
    x = x[mask]
    y = y[mask]
    n = len(x)
    if n < 5:
        raise AssertionError(f"correlation_permutation_pvalue: n={n} < 5")

    if x.std(ddof=0) == 0 or y.std(ddof=0) == 0:
        # Degenerate — return p=1.0 (no info)
        return PermResult(
            observed=0.0, p_two_sided=1.0, n=n, n_perm=n_perm,
            rule1_inflated=n < RULE1_THRESHOLD,
        )

    observed = float(np.corrcoef(x, y)[0, 1])
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm, dtype=float)
    for i in range(n_perm):
        y_shuf = rng.permutation(y)
        null[i] = float(np.corrcoef(x, y_shuf)[0, 1])
    p = float((np.abs(null) >= abs(observed)).mean())
    return PermResult(
        observed=observed,
        p_two_sided=p,
        n=n,
        n_perm=n_perm,
        rule1_inflated=n < RULE1_THRESHOLD,
    )


def rule1_inflate_ci_halfwidth(half_width: float, n: int,
                                threshold: int = RULE1_THRESHOLD) -> float:
    """Apply Rule 1 small-cell variance inflation.

    Per parent brief §4 kill #6: any regime sub-sample with n < 25 triggers
    Rule 1. CI half-width is multiplied by sqrt(threshold / n) to inflate
    uncertainty toward the small-cell prior.
    """
    if n >= threshold:
        return half_width
    if n <= 0:
        return float("inf")
    return half_width * float(np.sqrt(threshold / n))


# --- Self-test / null-test ---------------------------------------------------

def _null_test():
    """Null test on synthetic Brownian-motion-like null.

    Generate independent zero-mean noise; expect p approx uniform on [0,1]
    across many seeds, with mean approx 0.5.
    """
    print("=== permutation.py null-test (Brownian zero-mean noise) ===")
    n = 200
    n_seeds = 50
    ps = []
    rng_outer = np.random.default_rng(0)
    for s in range(n_seeds):
        seed = int(rng_outer.integers(0, 1_000_000))
        rng = np.random.default_rng(seed)
        # Zero-mean noise — true null
        noise = rng.standard_normal(n)
        res = edge_permutation_pvalue(noise, n_perm=500, seed=seed + 1)
        ps.append(res.p_two_sided)
    ps = np.array(ps)
    print(f"n_seeds={n_seeds}, n_per_sample={n}")
    print(f"Mean p:    {ps.mean():.3f}  (expected ~0.5 under H0)")
    print(f"Median p:  {np.median(ps):.3f}")
    print(f"Frac p<0.05: {(ps < 0.05).mean():.3f}  (expected ~0.05 under H0)")
    print()

    print("=== Rule-1 inflation probe ===")
    h0 = 0.10  # baseline CI half-width
    for n in [50, 25, 24, 10, 5]:
        infl = rule1_inflate_ci_halfwidth(h0, n)
        print(f"  n={n:3d}  half_width={h0:.3f} -> {infl:.3f}  ({infl/h0:.2f}x)")
    print()

    print("=== Edge perm probe (true positive edge) ===")
    rng = np.random.default_rng(42)
    pnl_pos = rng.standard_normal(150) + 0.30  # +0.3 mean shift
    res = edge_permutation_pvalue(pnl_pos, n_perm=1000, seed=42)
    print(f"  observed_mean={res.observed:.3f}, p={res.p_two_sided:.3f}, n={res.n}")
    print()

    print("=== Correlation perm probe (true positive correlation) ===")
    rng = np.random.default_rng(7)
    x = rng.standard_normal(100)
    y = 0.4 * x + rng.standard_normal(100)
    res = correlation_permutation_pvalue(x, y, n_perm=1000, seed=7)
    print(f"  observed_corr={res.observed:.3f}, p={res.p_two_sided:.3f}, n={res.n}")


if __name__ == "__main__":
    _null_test()
