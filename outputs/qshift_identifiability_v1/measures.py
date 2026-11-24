"""IDENT1 M1 and M2 under amendment A2. Exact DEM moments, Gaussian/chi-square approximations, no sampling.

A burst adds five independent errors to the base model, so log-moments add: L_X = L_base(p) + burst(q). That gives every
model from five base matrices (tested against the full DEM)."""
from __future__ import annotations

import numpy as np
import scipy.linalg as sl
from scipy.stats import binom, chi2, ncx2, norm

import moments as M
from split import C

N = 2_000
P_GRID = tuple(round(f * C.P0, 10) for f in (0.90, 0.95, 1.00, 1.05, 1.10))
Q_GRID = (0.005, 0.0075, 0.01, 0.015, 0.02)
RCOND = 1e-9
AMBIGUOUS, SEPARATED, ACCEPT = 10.8, 21.6, 0.05


def grid(state):
    return [(p, q) for p in P_GRID for q in (Q_GRID if state != "OFF" else (None,))]


class Base:
    """Burst-free model at background p over a feature family."""

    def __init__(self, feats, p):
        E, w = M.dem_errors(None, p)
        A = M.signs(E, feats)
        self.lm = 0.5 * (w.sum() - A @ w)
        L = (A * w) @ A.T
        L -= w.sum()
        L *= -0.5
        self.L = L


def burst_signs(sig, feats):
    """Signs of the five burst errors. sig: {(round, detector)}."""
    E = np.zeros((5, 120), bool)
    for r, d in sig:
        E[r, d] = True
    return M.signs(E, feats)


def model_mean(base, B=None, q=None):
    lm = base.lm if B is None else base.lm + 0.5 * np.log1p(-2 * q) * (5 - B.sum(axis=1))
    return np.exp(lm)


def model_cov(base, B=None, q=None):
    K = base.L.copy()
    if B is not None:
        K += 0.5 * np.log1p(-2 * q) * (5 - B @ B.T)
    np.exp(K, out=K)
    mu = model_mean(base, B, q)
    K -= np.outer(mu, mu)
    return K


class Solver:
    """Sigma^-1 by Cholesky, or on the eigenvectors above 1e-9 of the largest when badly conditioned."""

    def __init__(self, K, force_eig=False):
        self.dim, self.dropped, self.V = len(K), 0, None
        try:
            if force_eig:
                raise np.linalg.LinAlgError
            self.c = sl.cho_factor(K, lower=True, check_finite=False)
            rc, info = sl.lapack.dpocon(self.c[0], np.abs(K).sum(axis=0).max(), uplo="L")
            if info or rc <= RCOND:
                raise np.linalg.LinAlgError
        except np.linalg.LinAlgError:
            e, V = sl.eigh(K, check_finite=False)
            keep = e > RCOND * e[-1]
            self.dropped, self.dim = int((~keep).sum()), int(keep.sum())
            self.V = V[:, keep] / np.sqrt(e[keep])

    def solve(self, D):
        if self.V is None:
            return sl.cho_solve(self.c, D, check_finite=False)
        return self.V @ (self.V.T @ D)


def j_stat(wd, var_s, var_x):
    """Per row: 4 (w.d)^2 / (sd_s + sd_x)^2 for the statistic w = Sigma_s^-1 d. Zero distance gives 0."""
    sd = np.sqrt(np.maximum(var_s, 0)) + np.sqrt(np.maximum(var_x, 0))
    return np.divide(4 * wd ** 2, sd ** 2, out=np.zeros_like(wd), where=sd > 0)


def accept_probability(ncp, dim):
    return float(ncx2.cdf(chi2.ppf(0.995, dim), dim, ncp)) if ncp > 0 else 0.995


def label(J):
    return "AMBIGUOUS" if J < AMBIGUOUS else "MARGINAL" if J < SEPARATED else "SEPARATED"


def best_detector_check():
    """Section 8 (A2): per ordered bank pair, the best F0 detector: M1's error against the exact binomial."""
    rate = {s: M.single_rates(C.support(s)) for s in C.STATES}
    k, rows = np.arange(N + 1), []
    for s in C.STATES:
        for x in C.STATES:
            if s == x:
                continue
            a, b = rate[s], rate[x]
            sa, sb = np.sqrt(a * (1 - a)), np.sqrt(b * (1 - b))
            J = 4 * N * (a - b) ** 2 / (sa + sb) ** 2
            d = int(J.argmax())
            approx = float(norm.cdf(-np.sqrt(J[d]) / 2))
            exact = float(0.5 * np.minimum(binom.pmf(k, N, a[d]), binom.pmf(k, N, b[d])).sum())
            rows.append({"state": s, "other": x, "detector": d, "approx": approx, "exact": exact,
                         "ok": exact < 1e-6 or 0.5 <= approx / exact <= 2})
    return {"ok": all(r["ok"] for r in rows), "rows": rows}
