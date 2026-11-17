"""d=5 burst-support learner: a thin wrapper over the V1.6 learner (no sampler calls).

- Hypothesis space: V1.6's `signature_classes` (1-3 data-qubit X-bursts, grouped by per-round
  detector signature) evaluated at d=5. The count C is recorded in CLASSES_D5.json.
- Stage 1 (detector-only): the V1.6 parity-moment fit, computed with matrix algebra instead of
  Python loops (`FastParityLearner`). It is tested to give the same base_log, n and selections
  as `learner.ParityLearner` at d=3, and on sampled subsets/classes at d=5.
  Threshold: chi2_1 quantile at 1 - 0.01/C (V1.6b rule with the d=5 class count).
- Stage 2 (labeled), a declared deviation from V1.6b: the exact decoder is infeasible at d=5.
  For a class whose supports all share one logical effect, the flip is determined and no
  labels are used. For a mixed class, decode the labeled shots with L2 BP+OSD at the static
  prior once per flip (lowest-weight representative); fewer errors wins; ties -> the
  detector-only min-weight flip.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import stim
from scipy.stats import chi2

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m  # noqa: E402
from outputs.qshift_correlated_decoder_v1_6 import learner as L  # noqa: E402
from outputs.qshift_scalable_decoder_dev_v3_2.ldpc_bposd import LdpcBPOSD  # noqa: E402
from outputs.qshift_v1_4b_decoder_optimality.mld import dem_mechanisms  # noqa: E402

ALPHA = 0.01
L2 = {"bp_method": "product_sum", "schedule": "serial", "max_iter": 50, "osd_method": "OSD_CS", "osd_order": 10}
STATIC_PRIOR = 0.01  # d=5 Phase 2 Step 0 selection (PHASE2_D5_PRIOR.json)


def threshold(n_classes: int) -> float:
    return float(chi2.ppf(1 - ALPHA / n_classes, df=1))


def _incidence(sets, n_det: int) -> np.ndarray:
    a = np.zeros((len(sets), n_det), dtype=np.float32)
    for i, s in enumerate(sets):
        a[i, list(s)] = 1.0
    return a


class FastParityLearner:
    """Same statistics, fit and selection as learner.ParityLearner; vectorized construction."""

    def __init__(self, classes, dem: stim.DetectorErrorModel, thr: float):
        self.classes = classes
        self.threshold = float(thr)
        self.subsets = L.test_subsets(classes)
        n_det = dem.num_detectors
        mechs = [mm for mm in dem_mechanisms(dem) if mm.detectors]
        S = _incidence(self.subsets, n_det)
        M = _incidence([mm.detectors for mm in mechs], n_det)
        odd = (np.rint(S @ M.T).astype(np.int64) % 2).astype(np.float64)
        self.base_log = odd @ np.log1p(-2 * np.asarray([mm.p for mm in mechs]))
        rounds = len(classes[0].events)
        E = _incidence([sig for c in classes for sig in c.events], n_det)
        par = np.rint(E @ S.T).astype(np.int64) % 2                    # (C*rounds, subsets)
        self.n = par.reshape(len(classes), rounds, -1).sum(axis=1).astype(float)
        self._cols = [np.asarray(a) for a in self.subsets]

    def statistics(self, x: np.ndarray):
        x = np.asarray(x, dtype=np.uint8)
        par = np.stack([np.bitwise_xor.reduce(x[:, a], axis=1) for a in self._cols], axis=1)
        mu = np.clip(1.0 - 2.0 * par.mean(axis=0), 1e-6, None)
        y = np.log(mu) - self.base_log
        var_y = np.clip(1 - mu ** 2, 1e-12, None) / (len(x) * mu ** 2)
        return y, 1.0 / var_y

    def fit_all(self, x: np.ndarray):
        y, w = self.statistics(x)
        num = self.n @ (w * y)
        den = (self.n * self.n) @ w
        with np.errstate(divide="ignore", invalid="ignore"):
            beta = np.where(den > 0, num / den, 0.0)
            delta = np.where((den > 0) & (beta < 0), num * num / den, 0.0)
        q = np.clip((1 - np.exp(beta)) / 2, 0.0, m.MAX_BURST_PROBABILITY)
        q = np.where(den > 0, q, 0.0)
        return q, delta

    def select(self, x: np.ndarray) -> dict:
        q, delta = self.fit_all(x)
        best = int(np.argmax(delta))          # first index among ties, as ParityLearner's (delta, -i) key
        accepted = bool(delta[best] >= self.threshold)
        return {"class_index": best if accepted else None, "q_hat": float(q[best]) if accepted else 0.0,
                "delta": float(delta[best])}


def hyper_dem(spec, q_dec, qubits):
    return m.build_candidate_circuit(spec, q_dec, qubits).detector_error_model(
        decompose_errors=False, approximate_disjoint_errors=True)


def learn_flip(spec, cls: L.SignatureClass, x: np.ndarray, labels: np.ndarray, prior: float = STATIC_PRIOR) -> dict:
    if not cls.supports_flip1:
        return {"flip": 0, "method": "pure_class"}
    if not cls.supports_flip0:
        return {"flip": 1, "method": "pure_class"}
    y = np.asarray(labels, dtype=np.uint8).reshape(-1)
    errors = {}
    for flip in (0, 1):
        pred = LdpcBPOSD(hyper_dem(spec, prior, cls.representative(flip)), L2).decode_batch(np.asarray(x, np.uint8))[:, 0]
        errors[flip] = int((np.asarray(pred, np.uint8) != y).sum())
    flip = 0 if errors[0] < errors[1] else 1 if errors[1] < errors[0] else cls.min_weight_flip()
    return {"flip": flip, "method": "l2_labeled_errors", "errors": errors}


def learned_support(cls: L.SignatureClass, flip: int) -> tuple[int, ...]:
    return cls.representative(flip)


def classes_record(spec) -> dict:
    classes = L.signature_classes(spec)
    body = [{"events": [list(e) for e in c.events], "flip0": [list(s) for s in c.supports_flip0],
             "flip1": [list(s) for s in c.supports_flip1]} for c in classes]
    blob = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    known = {}
    for fam in m.BURST_FAMILIES:
        sup = tuple(m.burst_qubits(spec, fam))
        i = next(i for i, c in enumerate(classes) if sup in c.supports_flip0 + c.supports_flip1)
        c = classes[i]
        known[fam] = {"support": list(sup), "class_index": i, "flip": 0 if sup in c.supports_flip0 else 1,
                      "class_mixed": bool(c.supports_flip0 and c.supports_flip1),
                      "representative": list(c.representative(0 if sup in c.supports_flip0 else 1)),
                      "class_size": len(c.supports_flip0) + len(c.supports_flip1)}
    return {"schema": "qshift-d5-classes-v1", "distance": spec.distance, "rounds": spec.rounds,
            "n_classes": len(classes), "n_supports": sum(len(c["flip0"]) + len(c["flip1"]) for c in body),
            "n_mixed_classes": sum(1 for c in body if c["flip0"] and c["flip1"]),
            "n_test_subsets": len(L.test_subsets(classes)), "threshold": threshold(len(classes)),
            "alpha": ALPHA, "known_families": known, "classes_sha256": hashlib.sha256(blob).hexdigest(),
            "classes": body}


if __name__ == "__main__":
    rec = classes_record(m.CodeSpec(distance=5, gate_p=0.003, measurement_p=0.003))
    (ROOT / "CLASSES_D5.json").write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in rec.items() if k != "classes"}, indent=2))
