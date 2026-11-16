"""V1.6 two-stage burst learner (d=3 hypothesis space; no sampler calls).

Hypotheses: per-round X-bursts on 1-3 data qubits. Supports with identical per-round
detector signatures form a *signature class* (119 detectable supports -> 15 classes);
every class contains supports with both logical effects, which detector data cannot
distinguish.

Stage 1 (detector-only): signature class and rate q by a parity-moment fit. For
independent DEM mechanisms m with probability p_m and detector set D_m, and any detector
subset A, E[(-1)^{x_A}] = prod_m (1 - 2 p_m)^{[|D_m & A| odd]} exactly. A burst class c
with per-round events sigma_j multiplies this by (1 - 2q)^{n_A(c)}, n_A(c) = #{j :
|sigma_j & A| odd}. With y_A = log(observed / base-predicted), a weighted least-squares
fit y_A ~ n_A(c) * beta gives beta_c and improvement Delta_c = (sum w n y)^2 / sum w n^2
(beta_c < 0 required). The class with the largest Delta is accepted if Delta exceeds a
pre-registered threshold; otherwise "no burst".

Stage 2 (labeled): logical effect flip in {0, 1} for the accepted class by the exact
joint likelihood sum log P(s, l) of labeled calibration shots under the base DEM plus the
class's mechanism at q-hat (exact decoder from V1.4B).
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass

import numpy as np
import stim

from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
from outputs.qshift_v1_4b_decoder_optimality.mld import ExactLogicalDecoder, dem_mechanisms

SPEC = m.CodeSpec()


@dataclass(frozen=True)
class SignatureClass:
    events: tuple[tuple[int, ...], ...]       # per-round detector signatures
    supports_flip0: tuple[tuple[int, ...], ...]
    supports_flip1: tuple[tuple[int, ...], ...]

    def representative(self, flip: int) -> tuple[int, ...]:
        pool = self.supports_flip0 if flip == 0 else self.supports_flip1
        return min(pool, key=lambda s: (len(s), s))

    def min_weight_flip(self) -> int:
        """Detector-only heuristic: logical effect of the lowest-weight support (ties -> 0)."""
        w0 = min(len(s) for s in self.supports_flip0) if self.supports_flip0 else 99
        w1 = min(len(s) for s in self.supports_flip1) if self.supports_flip1 else 99
        return 0 if w0 <= w1 else 1


def signature_classes(spec: m.CodeSpec = SPEC) -> list[SignatureClass]:
    data = sorted(m.data_qubit_grid(spec).values())
    groups: dict[tuple, dict[int, list]] = {}
    for k in (1, 2, 3):
        for sub in itertools.combinations(data, k):
            try:
                events = m.extract_burst_events(spec, sub)
            except RuntimeError:
                continue  # detector-invisible support
            flips = {e.observable_flip for e in events}
            if len(flips) != 1:
                raise RuntimeError("per-round logical effect varies within one support")
            key = tuple(e.detector_ids for e in events)
            groups.setdefault(key, {0: [], 1: []})[flips.pop()].append(sub)
    return [SignatureClass(key, tuple(g[0]), tuple(g[1])) for key, g in sorted(groups.items())]


def base_dem(spec: m.CodeSpec = SPEC) -> stim.DetectorErrorModel:
    return m.build_base_circuit(spec).detector_error_model(decompose_errors=False, approximate_disjoint_errors=True)


def test_subsets(classes: list[SignatureClass]) -> list[tuple[int, ...]]:
    """All odd-size subsets of every class's event signatures (common statistic set)."""
    subsets = set()
    for c in classes:
        for sig in c.events:
            for r in range(1, len(sig) + 1, 2):
                subsets.update(itertools.combinations(sig, r))
    return sorted(subsets)


class ParityLearner:
    def __init__(self, classes: list[SignatureClass], dem: stim.DetectorErrorModel, threshold: float):
        self.classes = classes
        self.threshold = float(threshold)
        self.subsets = test_subsets(classes)
        mechs = dem_mechanisms(dem)
        self.base_log = np.asarray([
            sum(math.log1p(-2 * mm.p) for mm in mechs if len(set(mm.detectors) & set(a)) % 2) for a in self.subsets])
        self.n = np.asarray([[sum(len(set(sig) & set(a)) % 2 for sig in c.events) for a in self.subsets]
                             for c in classes], dtype=float)

    def statistics(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        x = np.asarray(x, dtype=np.uint8)
        par = np.stack([np.bitwise_xor.reduce(x[:, list(a)], axis=1) for a in self.subsets], axis=1)
        mu = 1.0 - 2.0 * par.mean(axis=0)
        mu = np.clip(mu, 1e-6, None)
        y = np.log(mu) - self.base_log
        var_y = np.clip(1 - mu ** 2, 1e-12, None) / (len(x) * mu ** 2)
        return y, 1.0 / var_y

    def fit_class(self, x: np.ndarray, index: int) -> tuple[float, float]:
        """Return (q-hat, Delta) for one class; q-hat clipped to [0, 0.02]."""
        y, w = self.statistics(x)
        n = self.n[index]
        denom = float((w * n * n).sum())
        if denom == 0:
            return 0.0, 0.0
        beta = float((w * n * y).sum()) / denom
        delta = float((w * n * y).sum()) ** 2 / denom if beta < 0 else 0.0
        q = min(max((1 - math.exp(beta)) / 2, 0.0), m.MAX_BURST_PROBABILITY)
        return q, delta

    def select(self, x: np.ndarray) -> dict:
        scores = [self.fit_class(x, i) for i in range(len(self.classes))]
        best = max(range(len(scores)), key=lambda i: (scores[i][1], -i))
        q, delta = scores[best]
        accepted = delta >= self.threshold
        return {"class_index": best if accepted else None, "q_hat": q if accepted else 0.0,
                "delta": delta, "all_deltas": [s[1] for s in scores]}


def class_dem(spec: m.CodeSpec, cls: SignatureClass, flip: int, q: float) -> stim.DetectorErrorModel:
    circuit = m.build_candidate_circuit(spec, q, cls.representative(flip))
    return circuit.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True)


def learn_flip(spec: m.CodeSpec, cls: SignatureClass, q: float, x: np.ndarray, labels: np.ndarray) -> dict:
    """Stage 2: flip by exact joint log-likelihood of labeled calibration shots."""
    ll = {}
    for flip in (0, 1):
        pool = cls.supports_flip0 if flip == 0 else cls.supports_flip1
        if not pool or q <= 0:
            ll[flip] = -math.inf
            continue
        dec = ExactLogicalDecoder(class_dem(spec, cls, flip, q))
        log_scale, table = dec.joint(np.asarray(x, dtype=np.uint8))
        y = np.asarray(labels, dtype=np.int64).reshape(-1)
        ll[flip] = float((log_scale + np.log(table[np.arange(len(y)), y])).sum())
    flip = 0 if ll[0] >= ll[1] else 1
    return {"flip": flip, "log_likelihood": ll, "log_likelihood_ratio_1_minus_0": ll[1] - ll[0]}
