"""AD1 stream: per-block true models and sampling (PLAN_AD1.md). Piecewise-constant noise; one block = fixed model."""
from __future__ import annotations

import numpy as np

import ad1_config as C


def block_truth(schedule, t):
    """(true-model kwargs, burst support or None) for block t of a schedule."""
    kw, bid = C.SCHEDULES[schedule](t)
    return kw, (C.BURSTS[bid] if bid else None)


def sample_block(schedule, t, n, seed):
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    kw, sup = block_truth(schedule, t)
    spec = C.spec(**kw)
    c = m.build_candidate_circuit(spec, C.BURST_Q, tuple(sup)) if sup else m.build_base_circuit(spec)
    d, o = c.compile_detector_sampler(seed=seed).sample(shots=n, separate_observables=True)
    return np.asarray(d, np.uint8), np.asarray(o, np.uint8)[:, 0]
