"""Confidence-calibrated regime classification with an explicit UNKNOWN outcome (hypothesis H-E3).

Each candidate regime is a predicted per-detector flip-rate vector (from a DEM the controller is allowed to
know: nominal or detector-calibrated, never the true generating parameters). For one block of detector
rows the classifier computes the independent-Bernoulli log-likelihood of the per-detector counts under each
regime, a posterior with a flat prior, and a goodness-of-fit deviance for the best regime.

If the best regime's deviance is implausible under its own model (upper-tail p-value below `fit_alpha`),
the block is classified UNKNOWN and the controller must fall back. This separates "which known regime" from
"none of them": a classifier that only reports argmax posterior is overconfident out of distribution.
Independence across detectors is an approximation (bursts and hyperedges correlate detectors); the
deviance test therefore tends to flag correlated blocks as UNKNOWN, which is the safe direction.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import erf, sqrt

import numpy as np

UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RegimeResult:
    label: str
    posterior: dict[str, float]
    confidence: float          # posterior of the label (0 for UNKNOWN)
    fit_pvalue: float          # upper-tail p-value of the best regime's deviance


def _loglik(counts: np.ndarray, n: int, rates: np.ndarray) -> float:
    r = np.clip(rates, 1e-12, 1 - 1e-12)
    return float(np.sum(counts * np.log(r) + (n - counts) * np.log1p(-r)))


def _deviance(counts: np.ndarray, n: int, rates: np.ndarray) -> float:
    """Binomial deviance vs the saturated model."""
    r = np.clip(rates, 1e-12, 1 - 1e-12)
    phat = counts / n
    with np.errstate(divide="ignore", invalid="ignore"):
        t1 = np.where(counts > 0, counts * np.log(phat / r), 0.0)
        t2 = np.where(n - counts > 0, (n - counts) * np.log((1 - phat) / (1 - r)), 0.0)
    return float(2 * np.sum(t1 + t2))


def _chi2_upper(x: float, k: int) -> float:
    """Wilson-Hilferty normal approximation to the chi-square upper tail (no scipy dependency)."""
    if k <= 0:
        return 1.0
    z = ((x / k) ** (1 / 3) - (1 - 2 / (9 * k))) / sqrt(2 / (9 * k))
    return 0.5 * (1 - erf(z / sqrt(2)))


class RegimeClassifier:
    def __init__(self, regimes: dict[str, np.ndarray], *, fit_alpha: float = 1e-3, min_confidence: float = 0.9):
        if not regimes:
            raise ValueError("at least one regime is required")
        lens = {len(v) for v in regimes.values()}
        if len(lens) != 1:
            raise ValueError("all regimes must predict the same detector count")
        self.regimes = {k: np.asarray(v, dtype=float) for k, v in regimes.items()}
        self.fit_alpha, self.min_confidence = fit_alpha, min_confidence

    def classify(self, detectors: np.ndarray) -> RegimeResult:
        d = np.asarray(detectors, dtype=np.uint8)
        n = d.shape[0]
        counts = d.sum(axis=0).astype(float)
        ll = {k: _loglik(counts, n, r) for k, r in self.regimes.items()}
        m = max(ll.values())
        w = {k: np.exp(v - m) for k, v in ll.items()}
        z = sum(w.values())
        post = {k: float(v / z) for k, v in w.items()}
        best = max(post, key=post.get)
        pval = _chi2_upper(_deviance(counts, n, self.regimes[best]), len(counts))
        if pval < self.fit_alpha or post[best] < self.min_confidence:
            return RegimeResult(UNKNOWN, post, 0.0, pval)
        return RegimeResult(best, post, post[best], pval)
