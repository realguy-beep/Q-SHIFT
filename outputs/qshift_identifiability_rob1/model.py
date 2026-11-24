"""ROB1 section 4: exact noise model (strict Stim error model), separate gate and measurement p, grids. No sampling."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
IDENT = ROOT.parent / "qshift_identifiability_v1"
for _p in (ROOT, IDENT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import split as S  # noqa: E402,I001  (blocks every sampler)
import measures as Q  # noqa: E402
import moments as M  # noqa: E402
from split import C, m, stim  # noqa: E402

P_FACTORS = (0.70, 0.80, 0.90, 1.00, 1.10, 1.20, 1.30)
Q_GRID = (0.0025, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.04)
QX = (0.0025, 0.005, 0.01, 0.02)
SLICE = (0.8, 1.0, 1.2)


def exact_circuit(c):
    """PAULI_CHANNEL_1/2 -> DEPOLARIZE1/2 of the same total. Unequal probabilities stop."""
    out = stim.Circuit()
    for i in c.flattened():
        if i.name in ("PAULI_CHANNEL_1", "PAULI_CHANNEL_2"):
            a = i.gate_args_copy()
            if max(a) - min(a) > 1e-15:
                raise ValueError("channel with unequal probabilities")
            out.append("DEPOLARIZE" + i.name[-1], i.targets_copy(), sum(a))
        else:
            out.append(i)
    return out


def exact_errors(sup, gate_p, meas_p, q=None):
    sp = C.spec(gate_p=gate_p, measurement_p=meas_p)
    c = exact_circuit(m.build_candidate_circuit(sp, min(q, m.MAX_BURST_PROBABILITY), tuple(sup)) if sup else m.build_base_circuit(sp))
    if sup and q > m.MAX_BURST_PROBABILITY:                 # the builder's own limit: set the burst probability afterwards
        d = stim.Circuit()
        for i in c:
            d.append(i.name, i.targets_copy(), [q] if i.name == "E" else i.gate_args_copy())
        c = d
    return M.errors(c.detector_error_model(decompose_errors=False, approximate_disjoint_errors=False), c.num_detectors)


class ExactBase:
    """As measures.Base, exact model."""

    def __init__(self, feats, point):
        E, w = exact_errors(None, *point)
        A = M.signs(E, feats)
        self.lm = 0.5 * (w.sum() - A @ w)
        L = (A * w) @ A.T
        L -= w.sum()
        L *= -0.5
        self.L = L


def old_base(feats, point):
    """IDENT1's approximate model, for the reproduction check only."""
    return Q.Base(feats, point[0])


def main_grid():
    """[(state, (gate p, measurement p), q)], grouped by background."""
    ps = [round(f * C.P0, 10) for f in P_FACTORS]
    return [(s, (p, p), q) for p in ps for s in C.STATES for q in ((None,) if s == "OFF" else Q_GRID)]


def slice_grid():
    ps = [round(f * C.P0, 10) for f in SLICE]
    return [(s, (g, r), None if s == "OFF" else 0.01) for g in ps for r in ps for s in C.STATES]


def is_edge(pt):
    """Edge of the main grid."""
    _, (p, _), q = pt
    ps = [round(f * C.P0, 10) for f in P_FACTORS]
    return p in (ps[0], ps[-1]) or q in (Q_GRID[0], Q_GRID[-1])


def bank_signatures():
    one = S.single_signatures()
    return {s: S.signature(C.support(s), one)[0] for s in C.STATES[1:]}


def bank_signs(feats):
    return {"OFF": None, **{s: Q.burst_signs(v, feats) for s, v in bank_signatures().items()}}


def features(fam):
    return M.families()[fam]


def rates(means, feats):
    """Firing rate of each single detector and co-firing rate of each pair, from parities. means: (..., features)."""
    one = {f[0]: i for i, f in enumerate(feats) if len(f) == 1}
    out = (1 - np.asarray(means, float)) / 2
    ix = [i for i, f in enumerate(feats) if len(f) == 2]
    if ix:
        a, b = ([one[feats[i][j]] for i in ix] for j in (0, 1))
        mu = np.asarray(means, float)
        out[..., ix] = (1 - mu[..., a] - mu[..., b] + mu[..., ix]) / 4
    if out.min() < -1e-12 or out.max() > 1 + 1e-12:
        raise ValueError("rate outside [0, 1]")
    return np.clip(out, 0, 1)
