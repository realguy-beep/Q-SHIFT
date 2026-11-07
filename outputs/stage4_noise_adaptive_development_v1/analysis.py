"""Frozen root-cluster statistics and development-gate helpers."""
from __future__ import annotations

from itertools import product

import numpy as np

NONZERO_P = (0.004, 0.008, 0.012, 0.016)
ALL_P = (0.0,) + NONZERO_P


def stratified_primary(differences: dict[float, np.ndarray]) -> float:
    if set(differences) != set(NONZERO_P):
        raise ValueError("primary statistic requires exactly four nonzero p strata")
    arrays = [np.asarray(differences[p], dtype=np.float64) for p in NONZERO_P]
    if any(a.shape != (7,) for a in arrays):
        raise ValueError("each stratum must have seven root-cluster paired effects")
    return float(np.mean([a.mean() for a in arrays]))


def stratified_cluster_bootstrap(differences: dict[float, np.ndarray], *, rng: np.random.Generator,
                                 resamples: int = 20000) -> np.ndarray:
    if set(differences) != set(NONZERO_P):
        raise ValueError("bootstrap requires exactly four nonzero strata")
    cells = [np.asarray(differences[p], dtype=np.float64) for p in NONZERO_P]
    if any(a.shape != (7,) for a in cells):
        raise ValueError("each stratum must have seven root effects")
    out = np.zeros(resamples, dtype=np.float64)
    for a in cells:
        idx = rng.integers(0, len(a), size=(resamples, len(a)))
        out += a[idx].mean(axis=1) / len(cells)
    return out


def root_mean_bootstrap(values: np.ndarray, *, rng: np.random.Generator,
                        resamples: int = 20000) -> np.ndarray:
    a = np.asarray(values, dtype=np.float64)
    if a.shape != (7,):
        raise ValueError("zero-burst harm interval requires seven independent roots")
    idx = rng.integers(0, len(a), size=(resamples, len(a)))
    return a[idx].mean(axis=1)


def monte_carlo_signflip(differences: dict[float, np.ndarray], *, rng: np.random.Generator,
                         assignments: int = 100000, chunk_size: int = 10000) -> tuple[float, float]:
    """Two-sided root-level sign-flip MC test; signs are independent within p strata."""
    observed = stratified_primary(differences)
    flattened = np.concatenate([np.asarray(differences[p], dtype=np.float64) for p in NONZERO_P])
    extreme = 0
    done = 0
    while done < assignments:
        n = min(chunk_size, assignments - done)
        signs = rng.integers(0, 2, size=(n, len(flattened)), dtype=np.int8) * 2 - 1
        stats = (signs * flattened[None, :]).mean(axis=1)
        extreme += int(np.count_nonzero(np.abs(stats) >= abs(observed) - 1e-15))
        done += n
    p = (extreme + 1) / (assignments + 1)
    return observed, p


def exact_stratum_signflip(values: np.ndarray) -> float:
    a = np.asarray(values, dtype=np.float64)
    if a.shape != (7,):
        raise ValueError("exact stratum test requires seven root differences")
    observed = abs(float(a.mean()))
    extreme = 0
    total = 2 ** len(a)
    for signs in product((-1.0, 1.0), repeat=len(a)):
        if abs(float(np.mean(a * signs))) >= observed - 1e-15:
            extreme += 1
    return extreme / total


def holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    items = sorted(p_values.items(), key=lambda kv: kv[1])
    n = len(items)
    adjusted = {}
    running = 0.0
    for rank, (name, p) in enumerate(items):
        value = min(1.0, (n - rank) * float(p))
        running = max(running, value)
        adjusted[name] = running
    return adjusted


def evaluate_gate(*, nonzero_mae: float, nonzero_bias: float,
                  within_005_by_stratum: dict[float, int], primary_mean: float,
                  primary_ci_upper: float, nonzero_stratum_means: dict[float, float],
                  zero_harm_ci_upper: float, median_rebuild_seconds: float,
                  peak_rss_bytes: int) -> dict:
    checks = {
        "nonzero_estimation_mae": nonzero_mae <= 0.0025,
        "nonzero_estimation_bias": abs(nonzero_bias) <= 0.0015,
        "at_least_5_of_7_within_0.005_each_nonzero_stratum": all(within_005_by_stratum[p] >= 5 for p in NONZERO_P),
        "primary_mean_improvement_at_least_0.0002": primary_mean <= -0.0002,
        "primary_cluster_ci_upper_below_zero": primary_ci_upper < 0.0,
        "all_4_nonzero_strata_favorable": sum(nonzero_stratum_means[p] < 0 for p in NONZERO_P) == 4,
        "no_nonzero_stratum_harm_above_0.0002": max(nonzero_stratum_means[p] for p in NONZERO_P) <= 0.0002,
        "zero_burst_one_sided_harm_upper_within_0.0002": zero_harm_ci_upper <= 0.0002,
        "median_decoder_rebuild_under_1s": median_rebuild_seconds < 1.0,
        "peak_rss_under_2gib": peak_rss_bytes < 2 * 1024**3,
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}

