"""ROB1 T1: IDENT1's M1 in blocks of X models. Covariances are formed directly (no expansion)."""
from __future__ import annotations

import numpy as np

from model import C, Q, bank_signs

BLOCK = 468


def j_values(points, feats, xs, make_base, log=lambda s: None, block=BLOCK, keep=()):
    """xs: [(burst signs, q)] at background p0. -> J (points x models), dropped directions, {(i, j): (w, var_x)} for keep."""
    bases = {}

    def base(p):
        if p not in bases:
            bases[p] = make_base(feats, p)
        return bases[p]
    x0 = base((C.P0, C.P0))
    bank = bank_signs(feats)
    k, nx = len(feats), len(xs)
    J, dropped, kept = np.zeros((len(points), nx)), 0, {}
    for lo in range(0, nx, block):
        part = xs[lo:lo + block]
        mu_x = np.array([Q.model_mean(x0, B, q) for B, q in part])
        W, vs = np.zeros((len(part), len(points), k)), np.zeros((len(points), len(part)))
        for i, (st, p, q) in enumerate(points):
            sol = Q.Solver(Q.model_cov(base(p), bank[st], q))
            dropped += sol.dropped if lo == 0 else 0
            D = mu_x - Q.model_mean(base(p), bank[st], q)
            w = sol.solve(D.T).T
            vs[i] = np.einsum("ij,ij->i", w, D)
            W[:, i, :] = w
        log(f"T1 {k} features, block at {lo}: bank points done")
        for j, (B, q) in enumerate(part):
            vx = np.einsum("ij,ij->i", W[j] @ Q.model_cov(x0, B, q), W[j])
            J[:, lo + j] = Q.j_stat(vs[:, j], vs[:, j], vx)
            for i in range(len(points)):
                if (i, lo + j) in keep:
                    kept[i, lo + j] = (W[j, i].copy(), float(vx[i]))
        log(f"T1 {k} features, block at {lo}: models done")
    return J, dropped, kept
