"""DB1 core: sampling, template fit statistic, state identification and the logical-risk gate (pure functions).

Separation of the three checks (PLAN_DB1.md):
  change detection  AD3's two-sample G (ad3.g_stat) of block u against its segment, tau = 163.13: resets the segment
  identification    G_fit of the pooled segment rows against each bank state's fixed detector-rate template;
                    plausible set P = {s : G_fit_s <= tau_fit[L]} (L = segment blocks, at most 6)
  logical risk      act with the key minimising the worst development LER over P (risk table R[state][key]);
                    keep the current key unless another lowers that worst case by more than KAPPA.
                    P empty -> unknown -> AD's own accepted estimate (open-set learning), else hold the current key.
"""
from __future__ import annotations

import numpy as np

import db_config as C


def sample(state, n, sd):
    """Rows from the background at p0 with burst `state` (None/"OFF" = burst-free), as ad2.sample_block does."""
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    sp = C.spec(gate_p=C.P0, measurement_p=C.P0)
    sup = C.support(state)
    c = m.build_candidate_circuit(sp, C.BURST_Q, tuple(sup)) if sup else m.build_base_circuit(sp)
    d, o = c.compile_detector_sampler(seed=sd).sample(shots=n, separate_observables=True)
    return np.asarray(d, np.uint8), np.asarray(o, np.uint8)[:, 0]


def counts(rows):
    rows = np.asarray(rows, np.uint8)
    return rows.sum(axis=0).astype(np.int64), int(len(rows))


def pool(cs):
    return sum(c[0] for c in cs), sum(c[1] for c in cs)


def template(k, n):
    """Per-detector firing-rate template (add-half smoothing)."""
    return (np.asarray(k, float) + 0.5) / (n + 1.0)


def g_fit(k, n, p):
    """Goodness of fit of counts (k of n per detector) to fixed rates p: 2 [ll(own rates) - ll(p)]."""
    k = np.asarray(k, float)
    p = np.clip(np.asarray(p, float), 1e-12, 1 - 1e-12)
    q = np.clip(k / n, 1e-12, 1 - 1e-12)
    ll = lambda r: k * np.log(r) + (n - k) * np.log1p(-r)   # noqa: E731
    return float(2 * (ll(q) - ll(p)).sum())


def plausible(gfits, L, tau_fit):
    return [s for s in C.STATES if gfits[s] <= tau_fit[str(L)]]


def bank_decide(gfits, L, tau_fit, risk, prev, kappa=C.KAPPA):
    """-> (key or None for unknown, plausible set). Keys are bank state names."""
    P = plausible(gfits, L, tau_fit)
    if not P:
        return None, P
    worst = {a: max(risk[s][a] for s in P) for a in C.STATES}
    best = min(C.STATES, key=lambda a: (worst[a], C.STATES.index(a)))
    if prev in worst and worst[prev] <= worst[best] + kappa:
        return prev, P
    return best, P


def id_decide(gfits, L, tau_fit):
    """Ablation without the risk gate: the best-fitting state if it is plausible, else unknown."""
    s = min(C.STATES, key=lambda a: (gfits[a], C.STATES.index(a)))
    return (s if gfits[s] <= tau_fit[str(L)] else None), plausible(gfits, L, tau_fit)


_TRUTH = {}


def class_flip(sup, classes):
    """(class index, flip) of a support, as AD1's learned_correct defines correctness; None for burst-free."""
    if sup is None:
        return None
    k = tuple(sorted(int(q) for q in sup))
    if k not in _TRUTH:
        import mm_contract as K
        try:
            _TRUTH[k] = tuple(K.B.truth(classes, tuple(int(q) for q in sup)))
        except KeyError:
            _TRUTH[k] = tuple(K.B.truth(classes, k))
    return _TRUTH[k]


def acceptable(action_support, true_state, classes):
    """An action is correct for a state if its support has the state's (class, flip); burst-free for OFF."""
    return class_flip(action_support, classes) == class_flip(C.support(true_state), classes)
