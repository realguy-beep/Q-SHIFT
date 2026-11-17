"""Mismatch-study sampling and learning primitives.

The ONLY difference from Phase C: `sample` draws from TRUE_SPECS[cond]. Learning uses Phase C's
FastParityLearner on the nominal base DEM with tau unchanged; decoding is Phase C's c_job.decode_all,
which builds every decoder from the nominal spec.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import mm_contract as K  # noqa: E402
import c_job  # noqa: E402  (Phase C, read-only)
import learner_d5 as LD  # noqa: E402
from learner_d5 import L, m  # noqa: E402

decode_all = c_job.decode_all                   # nominal-spec decoders, identical to Phase C


def sample(spec, q, qubits, n, seed):
    d, o = m.build_candidate_circuit(spec, q, qubits).compile_detector_sampler(seed=seed).sample(
        shots=n, separate_observables=True)
    return np.asarray(d, np.uint8), np.asarray(o, np.uint8)[:, 0]


def nominal_learner(thr=None):
    classes = K.B.load_classes()
    return classes, LD.FastParityLearner(classes, L.base_dem(K.NOMINAL_SPEC), K.tau() if thr is None else thr)


def learn(classes, learner, dets, labx, laby):
    """Phase C calibration logic (c_job.calibrate) on given arrays: stage 1 on detector rows, stage 2 flip."""
    sel = learner.select(np.vstack(dets))
    flip = learned = None
    if sel["class_index"] is not None:
        flip = LD.learn_flip(K.NOMINAL_SPEC, classes[sel["class_index"]], np.vstack(labx), np.concatenate(laby))
        learned = list(classes[sel["class_index"]].representative(flip["flip"]))
    t_idx, t_flip = K.B.truth(classes, K.SUPPORT)
    return {"selection": {"class_index": sel["class_index"], "q_hat": sel["q_hat"], "delta": sel["delta"]},
            "flip": flip, "learned_support": learned,
            "class_correct": sel["class_index"] == t_idx,
            "learned_correct": bool(sel["class_index"] == t_idx and flip is not None and flip["flip"] == t_flip)}


def residual_summary(learner, x):
    """Size of the nominal-model mismatch signal: parity-moment residuals y over all test subsets."""
    y, w = learner.statistics(x)
    z = y * np.sqrt(w)
    return {"mean_y": float(y.mean()), "mean_abs_z": float(np.abs(z).mean()), "mean_z": float(z.mean()),
            "frac_y_negative": float((y < 0).mean())}
