"""Write BRE_BURSTS.json (public burst sets) and BRE_SEEDS.json (screened against every prior inventory).

Bursts: T = K, M0, M1, CR + N_RANDOM_T random; V = N_V random. Random members come from the RE1 candidate pool
(re1_seal.candidate_pool: excludes the development/Phase C classes, anything within one qubit of them, and the
rehearsal support), one support per signature class, stratified by footprint (the detector set of the support's
class, i.e. the detectors the burst flips). Drawn with a public seed. H2 is NOT read, so it cannot be excluded.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

import bre_config as C
import prepare_re1 as P1

ROOT = Path(__file__).resolve().parent
NS, NS_REH = "qshift-adaptive-robust-v1:bre", "qshift-adaptive-robust-v1:bre:REHEARSAL"
BURST_SEED_LABEL = "qshift-adaptive-robust-v1:bre:bursts"


def _classes():
    import mm_contract as K
    return K.B.load_classes()


def class_of(classes, s):
    import mm_contract as K
    return K.B.truth(classes, tuple(s))[0]


def draw_bursts():
    import estimate3 as E3
    import re1_seal
    classes = _classes()
    size = {i: len(E3.class_detectors(c)) for i, c in enumerate(classes)}
    fixed_cls = {class_of(classes, s) for s in C.FIXED_T.values()}
    by_stratum = {i: [] for i in range(len(C.FOOTPRINT_STRATA))}
    seen = set(fixed_cls)
    for s in re1_seal.candidate_pool():          # sorted; first support of each class kept
        ci = class_of(classes, s)
        if ci in seen:
            continue
        seen.add(ci)
        fp = size[ci]
        st = next(i for i, (a, b) in enumerate(C.FOOTPRINT_STRATA) if a <= fp <= b)
        by_stratum[st].append(tuple(s))
    seed = int.from_bytes(hashlib.sha256(BURST_SEED_LABEL.encode()).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    n_st = len(C.FOOTPRINT_STRATA)
    t_per, v_per = C.N_RANDOM_T // n_st, C.N_V // n_st
    T = {k: list(v) for k, v in C.FIXED_T.items()}
    V = {}
    for st in range(n_st):
        pool = by_stratum[st]
        if len(pool) < t_per + v_per:
            raise SystemExit(f"stratum {st} has only {len(pool)} classes")
        pick = rng.choice(len(pool), size=t_per + v_per, replace=False)
        for j, i in enumerate(pick):
            s = list(pool[int(i)])
            if j < t_per:
                T[f"T{len(T) - len(C.FIXED_T) + 1:02d}"] = s
            else:
                V[f"V{len(V) + 1:02d}"] = s
    fps = {k: size[class_of(classes, v)] for k, v in (T | V).items()}
    return {"schema": "qshift-adaptive-robust-bre-bursts-v1", "T": T, "V": V, "footprint": fps,
            "e1_max_excluded": max(size.values()),
            "e1_max_excluded_rule": "largest burst detector set over all signature classes (data-independent)",
            "strata": [list(s) for s in C.FOOTPRINT_STRATA],
            "stratum_class_counts": {str(k): len(v) for k, v in by_stratum.items()},
            "draw": {"label": BURST_SEED_LABEL, "seed": seed, "rule": "per stratum, without replacement: first "
                     f"{t_per} -> T, next {v_per} -> V; one support per class"},
            "h2_caveat": "H2 (RE1, sealed) was not read and could not be excluded; it is spent for confirmatory use."}


def screened():
    vals, rec, derive = P1.screened()
    raw = (ROOT / "RE1_SEEDS.json").read_bytes()
    r1 = json.loads(raw)
    v = set(r1["seeds"].values()) | set(r1["rehearsal_seeds"].values())
    vals |= v
    rec["outputs/qshift_adaptive_robust_v1/RE1_SEEDS.json"] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(v)}
    return vals, rec, derive


def main():
    bo, so = ROOT / "BRE_BURSTS.json", ROOT / "BRE_SEEDS.json"
    if bo.exists() or so.exists():
        raise SystemExit("BRE_BURSTS.json / BRE_SEEDS.json exist")
    from multiprocessing import get_context
    with get_context("spawn").Pool(1) as pool:      # separate process: two prior packages both ship `contract.py`
        b = pool.apply(draw_bursts)
    bo.write_text(json.dumps(b, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    vals, rec, derive = screened()
    used, seeds, reh = set(vals), {}, {}
    for k in C.all_keys(b):
        seeds[k] = derive(NS, k, used)
        used.add(seeds[k])
    for k in C.rehearsal_keys():
        reh[k] = derive(NS_REH, k, used)
        used.add(reh[k])
    so.write_text(json.dumps({"schema": "qshift-adaptive-robust-bre-seeds-v1", "namespace": NS, "seeds": seeds,
                              "rehearsal_seeds": reh, "screened": rec, "union_screened": len(vals)},
                             indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(len(b["T"]), "T,", len(b["V"]), "V;", len(seeds), "seeds,", len(reh), "rehearsal; screened", len(vals))


if __name__ == "__main__":
    main()
