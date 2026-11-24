"""ROB1 T2: exact binomial rejection bound. Every step is a separate function so that the tests can break it."""
from __future__ import annotations

import numpy as np
from scipy.stats import binom

ALPHA = 0.005


def tail(m):
    return ALPHA / (2 * m)


def interval(n, r, a):
    """Smallest and largest accepted count; each tail outside has probability at most a."""
    return binom.ppf(a, n, r), binom.isf(a, n, r)


def hull(lo, hi):
    """Union over grid points (axis 0) as one range."""
    return lo.min(axis=0), hi.max(axis=0)


def accept(n, x, lo, hi):
    """P(lo <= count <= hi), count ~ binomial(n, x)."""
    return np.clip(binom.cdf(hi, n, x) - binom.cdf(lo - 1, n, x), 0, 1)


def least(p):
    """-> (B, index of the feature that attains it), over the last axis."""
    i = p.argmin(axis=-1)
    return np.take_along_axis(p, i[..., None], -1)[..., 0], i


def bound(n, x, bank):
    """x: (models, features) rates of X; bank: (points, features) rates of one state. -> B, feature, (lo, hi per point)."""
    lo, hi = interval(n, bank, tail(bank.shape[1]))
    a, b = hull(lo, hi)
    B, f = least(accept(n, x, a, b))
    return B, f, (lo, hi)
