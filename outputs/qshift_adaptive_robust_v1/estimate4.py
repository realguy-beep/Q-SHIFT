"""E1S = E1 + structural misfit rules (PLAN_BRS.md). estimate3.py (frozen in BRE) is imported, not modified.

  e1_with_set(obs, n)                 E1 exactly as in BRE, plus the excluded detector set X (residual > cutoff at
                                      the final fit; equals E1's final mask when E1 reached its fixed point)
  structural_flags(x_set, accepted)   SUBSET rule (owner-approved deviation after BRS-0; BRS_PROTOCOL.md):
                                      S1 shape: X non-empty and contained in no signature-class detector set
                                      S2 consistency: X empty but a class accepted, or X non-empty and the accepted
                                      class's detector set does not contain X (or nothing accepted)
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

import brs_config as C
import estimate3 as E3


@lru_cache(maxsize=1)
def class_sets():
    import mm_contract as K
    return {frozenset(E3.class_detectors(c)): i for i, c in enumerate(K.B.load_classes())}


def e1_with_set(obs, n):
    f = E3.fit_e1(obs, n)
    r = E3.std_residuals(obs, n, f["p_hat"], f["b_hat"])
    x = tuple(int(i) for i in np.flatnonzero(r > C.B.E1_CUTOFF))
    return {**f, "excluded_set": list(x), "set_matches_count": len(x) == f["excluded"]}


def e1_flag(f):
    return f["excluded"] > C.E1_MAX_EXCLUDED or f["stat"] > C.E1_STAT_THRESHOLD


@lru_cache(maxsize=1)
def _sets_by_class():
    return {i: s for s, i in class_sets().items()}


def structural_flags(x_set, accepted):
    xs = frozenset(int(v) for v in x_set)
    exact = class_sets().get(xs) if xs else None
    if not xs:
        return {"S1_shape": False, "S2_consistency": accepted is not None, "x_class": None, "x_exact_class": None}
    s1 = not any(xs <= s for s in class_sets())
    s2 = accepted is None or not xs <= _sets_by_class()[accepted]
    return {"S1_shape": bool(s1), "S2_consistency": bool(s2), "x_class": accepted if not s2 else None,
            "x_exact_class": exact}
