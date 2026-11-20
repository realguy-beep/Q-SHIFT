"""RE2 burst pool (PLAN_RE2.md rev 2). Public data only: the class table, RE1's committed candidate pool
(re1_seal.candidate_pool, which does not read RE1's seal) and the public development bursts. Never reads H2.

  eligible()           class index -> (representative support, footprint), after the development exclusions
  rehearsal_bursts()   one public deterministic rehearsal burst per stratum (first eligible class in index order)
  pools()              stratum -> sorted class indices, rehearsal classes removed (the draw pools)
  pool_doc()           the committed description, including the pool hash
Call inside a spawn subprocess when another package's `contract` module may already be imported.
"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache

import re2_config as C

DEV_BURST_FILES = (("BRE_BURSTS.json", ("T", "V")), ("BRS_BURSTS.json", ("V",)), ("BRT_BURSTS.json", ("V",)))


def dev_bursts():
    sup = [tuple(C.KNOWN)]
    for f, keys in DEV_BURST_FILES:
        d = json.loads((C.ROOT / f).read_text(encoding="utf-8"))
        for k in keys:
            sup += [tuple(v) for v in d[k].values()]
    return sup


@lru_cache(maxsize=1)
def eligible():
    import estimate3 as E3
    import mm_contract as K
    import re1_seal
    cl = K.B.load_classes()
    dev = dev_bursts()
    seen = {K.B.truth(cl, s)[0] for s in dev}
    out = {}
    for s in re1_seal.candidate_pool():
        if any(len(set(s) & set(b)) >= 2 for b in dev):
            continue
        ci = K.B.truth(cl, tuple(s))[0]
        if ci in seen or ci in out:
            continue
        out[ci] = (tuple(int(v) for v in s), len(E3.class_detectors(cl[ci])))
    return out


def stratum_of(fp):
    return next((h for h, (a, b) in C.STRATA.items() if a <= fp <= b), None)


def _by_stratum():
    by = {h: [] for h in C.STRATA}
    for ci in sorted(eligible()):
        h = stratum_of(eligible()[ci][1])
        if h:
            by[h].append(ci)
    return by


def rehearsal_bursts():
    """Public rehearsal burst per stratum: the lowest-index eligible class. Removed from the draw pools."""
    return {h: eligible()[v[0]][0] for h, v in _by_stratum().items()}


def pools():
    return {h: v[1:] for h, v in _by_stratum().items()}


def pool_doc():
    el = eligible()
    pl = pools()
    canon = json.dumps({h: [[ci, list(el[ci][0])] for ci in v] for h, v in pl.items()}, sort_keys=True,
                       separators=(",", ":"))
    return {"eligible_classes": len(el), "strata": {h: list(r) for h, r in C.STRATA.items()},
            "stratum_sizes_before_rehearsal_removal": {h: len(v) for h, v in _by_stratum().items()},
            "draw_pool_sizes": {h: len(v) for h, v in pl.items()},
            "rehearsal_bursts": {h: list(s) for h, s in rehearsal_bursts().items()},
            "pool_sha256": hashlib.sha256(canon.encode()).hexdigest(),
            "pool_canonical_form": "json of {stratum: [[class_index, representative_support], ...]}, sorted keys, "
                                   "compact separators",
            "exclusions": "RE1 candidate pool; every BRE/BRS/BRT burst class and K; any support sharing >= 2 qubits "
                          "with one of them; one representative support per class; rehearsal classes removed",
            "h2": "not read; RE1's seal stays closed (owner decision 2026-11-20)"}
