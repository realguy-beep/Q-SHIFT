"""IDENT1 sections 3 and 5: exact parity moments and covariances from a DEM, and the feature families. No sampling."""
from __future__ import annotations

import numpy as np

import split as S
from split import C, SPEC, m


def circuit(sup, p=None, q=None):
    sp = SPEC if p is None else C.spec(gate_p=p, measurement_p=p)
    return m.build_base_circuit(sp) if not sup else m.build_candidate_circuit(sp, 0.01 if q is None else q, tuple(sup))


def errors(dem, n):
    """-> (E: errors x detectors bool, w: log(1 - 2p)). Observables are ignored."""
    rows, w = [], []
    for inst in dem.flattened():
        if inst.type != "error":
            continue
        v = np.zeros(n, bool)
        for t in inst.targets_copy():
            if t.is_relative_detector_id():
                v[t.val] ^= True
        p = inst.args_copy()[0]
        if not 0 <= p < 0.5:
            raise ValueError(f"error probability {p}")
        if p > 0 and v.any():
            rows.append(v)
            w.append(np.log1p(-2 * p))
    return np.array(rows, bool).reshape(-1, n), np.array(w)


def dem_errors(sup, p=None, q=None):
    c = circuit(sup, p, q)
    return errors(c.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True), c.num_detectors)


def signs(E, feats):
    """(-1)^(overlap) for every feature (tuple of detectors) and error."""
    x = np.zeros((len(feats), len(E)), bool)
    for i, f in enumerate(feats):
        for d in f:
            x[i] ^= E[:, d]
    return 1.0 - 2.0 * x


def means(A, w):
    return np.exp(0.5 * (w.sum() - A @ w))


def covariance(A, w):
    """cov of the +-1 parities of one row: m_(S xor T) - m_S m_T."""
    G = (A * w) @ A.T
    G -= w.sum()
    G *= -0.5
    np.exp(G, out=G)
    mu = means(A, w)
    G -= np.outer(mu, mu)
    return G


def families():
    co = m.build_base_circuit(SPEC).get_detector_coordinates()
    n = len(co)
    f0 = [(d,) for d in range(n)]
    pairs = [(a, b) for a in range(n) for b in range(a + 1, n)]
    near = [(a, b) for a, b in pairs if abs(co[a][2] - co[b][2]) <= 1 and
            max(abs(co[a][0] - co[b][0]), abs(co[a][1] - co[b][1])) <= 4]
    return {"F0": f0, "F1": f0 + near, "F2": f0 + pairs}


def single_rates(sup, p=None, q=None):
    E, w = dem_errors(sup, p, q)
    return (1 - means(signs(E, [(d,) for d in range(E.shape[1])]), w)) / 2


__all__ = ["S", "circuit", "covariance", "dem_errors", "errors", "families", "means", "signs", "single_rates"]
