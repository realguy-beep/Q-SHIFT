"""Finite-envelope, root-level secondary inference used only in design validation."""
from __future__ import annotations

import math
import numpy as np


def dkw_epsilon(sample_count: int, family_count: int, delta_total: float) -> float:
    if sample_count <= 0 or family_count <= 0 or not 0 < delta_total < 1:
        raise ValueError("invalid DKW parameters")
    return math.sqrt(math.log(2.0 * family_count / delta_total) / (2.0 * sample_count))


def envelope_p(sorted_reference_cdfs: list[np.ndarray], epsilon: float, statistic: np.ndarray) -> np.ndarray:
    """Conservative max of upper empirical CDFs; ties use right-continuous ranks."""
    t = np.asarray(statistic, dtype=np.float64)
    out = np.zeros(t.shape, dtype=np.float64)
    for reference in sorted_reference_cdfs:
        ranks = np.searchsorted(reference, t, side="right")
        out = np.maximum(out, ranks / len(reference) + epsilon)
    return np.minimum(1.0, out)


def statistic(mean: np.ndarray, sd: np.ndarray, n: int) -> np.ndarray:
    mean = np.asarray(mean, dtype=np.float64)
    sd = np.asarray(sd, dtype=np.float64)
    out = np.empty(np.broadcast_shapes(mean.shape, sd.shape), dtype=np.float64)
    mean, sd = np.broadcast_arrays(mean, sd)
    positive = sd > 0
    out[positive] = math.sqrt(n) * mean[positive] / sd[positive]
    out[~positive] = np.where(mean[~positive] < 0, -np.inf, np.inf)
    return out


def holm_reject(pvalues: np.ndarray, alpha: float = 0.05) -> np.ndarray:
    p = np.asarray(pvalues, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 4 or np.any(~np.isfinite(p)) or np.any((p < 0) | (p > 1)):
        raise ValueError("Holm expects an N x 4 matrix of finite p-values in [0,1]")
    ordered = np.sort(p, axis=1)
    alive = np.ones(p.shape[0], dtype=bool)
    rejected = np.zeros_like(p, dtype=bool)
    for rank in range(p.shape[1]):
        pass_step = alive & (ordered[:, rank] <= alpha / (p.shape[1] - rank))
        rejected |= pass_step[:, None] & (np.arange(p.shape[1])[None, :] == rank)
        alive &= pass_step
    # Return rejection flags in original condition order, not rank order.
    order = np.argsort(p, axis=1, kind="stable")
    original = np.zeros_like(rejected)
    for rank in range(p.shape[1]):
        original[np.arange(p.shape[0]), order[:, rank]] = rejected[:, rank]
    return original


def wilson(successes: int, trials: int, confidence: float = 0.95, *, one_sided: bool = False) -> tuple[float, float]:
    if trials <= 0 or not 0 <= successes <= trials:
        raise ValueError("invalid binomial count")
    from scipy.stats import norm
    z = float(norm.ppf(confidence if one_sided else (1.0 + confidence) / 2.0))
    p = successes / trials
    den = 1.0 + z * z / trials
    mid = (p + z * z / (2.0 * trials)) / den
    half = z * math.sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials)) / den
    return max(0.0, mid - half), min(1.0, mid + half)


def simultaneous_wilson(successes: int, trials: int, family_cells: int, confidence: float = 0.95) -> tuple[float, float]:
    """Bonferroni-adjusted two-sided Wilson interval across a prespecified family."""
    from scipy.stats import norm
    if family_cells <= 0:
        raise ValueError("family_cells must be positive")
    z = float(norm.ppf(1.0 - (1.0 - confidence) / (2.0 * family_cells)))
    p = successes / trials
    den = 1.0 + z * z / trials
    mid = (p + z * z / (2.0 * trials)) / den
    half = z * math.sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials)) / den
    return max(0.0, mid - half), min(1.0, mid + half)


def wilson_one_sided_simultaneous(successes: int, trials: int, family_cells: int, confidence: float = 0.95) -> tuple[float, float]:
    """One-sided Bonferroni Wilson bounds across a prespecified family."""
    from scipy.stats import norm
    if family_cells <= 0:
        raise ValueError("family_cells must be positive")
    z = float(norm.ppf(1.0 - (1.0 - confidence) / family_cells))
    p = successes / trials
    den = 1.0 + z * z / trials
    mid = (p + z * z / (2.0 * trials)) / den
    half = z * math.sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials)) / den
    return max(0.0, mid - half), min(1.0, mid + half)


def conservative_cutoff(sorted_reference_cdfs: list[np.ndarray], epsilon: float, alpha: float) -> float:
    """First statistic where any upper empirical CDF exceeds alpha.

    The rejection region is strictly below this value. Using the first crossing
    (rather than the last accepted order statistic) keeps inversion conservative
    when a discrete reference CDF has an atom at its threshold.
    """
    if not 0 < alpha <= 1:
        raise ValueError("alpha must be in (0,1]")
    threshold_count = math.floor((alpha - epsilon) * len(sorted_reference_cdfs[0]))
    shape_crossings = []
    for ref in sorted_reference_cdfs:
        j = min(max(threshold_count, 0), len(ref) - 1)
        # If the threshold count falls inside a tie, the tied value's inclusive
        # CDF is already above alpha; that value is the crossing as required.
        candidate = ref[j]
        if np.searchsorted(ref, candidate, side="right") <= threshold_count:
            j = int(np.searchsorted(ref, candidate, side="right"))
            if j >= len(ref):
                shape_crossings.append(math.inf)
                continue
            candidate = ref[j]
        shape_crossings.append(float(candidate))
    return min(shape_crossings)

