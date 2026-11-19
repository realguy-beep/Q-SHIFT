"""Write BRT_BURSTS.json (16 fresh held-out bursts) and BRT_SEEDS.json (screened against every prior inventory).

Pool: the RE1 candidate pool (re1_seal.candidate_pool), minus every BRE and BRS burst's class and any support sharing
>= 2 qubits with one of them; one support per class; PER_STRATUM per footprint stratum; public seed. H2 is not read.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

import brt_config as C
import prepare_brs as PS

ROOT = Path(__file__).resolve().parent
NS, NS_REH = "qshift-adaptive-robust-v1:brt", "qshift-adaptive-robust-v1:brt:REHEARSAL"
BURST_SEED_LABEL = "qshift-adaptive-robust-v1:brt:bursts"


def draw_bursts():
    import estimate3 as E3
    import mm_contract as K
    import re1_seal
    classes = K.B.load_classes()
    bre = json.loads((ROOT / "BRE_BURSTS.json").read_text(encoding="utf-8"))
    brs = json.loads((ROOT / "BRS_BURSTS.json").read_text(encoding="utf-8"))
    bre_sup = [tuple(v) for v in list(bre["T"].values()) + list(bre["V"].values()) + list(brs["V"].values())]
    seen = {K.B.truth(classes, s)[0] for s in bre_sup}
    by = {i: [] for i in range(len(C.FOOTPRINT_STRATA))}
    for s in re1_seal.candidate_pool():
        if any(len(set(s) & set(b)) >= 2 for b in bre_sup):
            continue
        ci = K.B.truth(classes, tuple(s))[0]
        if ci in seen:
            continue
        seen.add(ci)
        fp = len(E3.class_detectors(classes[ci]))
        by[next(i for i, (a, b) in enumerate(C.FOOTPRINT_STRATA) if a <= fp <= b)].append(tuple(s))
    seed = int.from_bytes(hashlib.sha256(BURST_SEED_LABEL.encode()).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    V, fps = {}, {}
    for st in range(len(C.FOOTPRINT_STRATA)):
        pool = by[st]
        if len(pool) < C.PER_STRATUM:
            raise SystemExit(f"stratum {st} has only {len(pool)} eligible classes")
        for i in rng.choice(len(pool), size=C.PER_STRATUM, replace=False):
            s = list(pool[int(i)])
            key = f"X{len(V) + 1:02d}"
            V[key] = s
            fps[key] = len(E3.class_detectors(classes[K.B.truth(classes, tuple(s))[0]]))
    return {"schema": "qshift-adaptive-robust-brt-bursts-v1", "V": V, "footprint": fps,
            "strata": [list(s) for s in C.FOOTPRINT_STRATA],
            "stratum_class_counts": {str(k): len(v) for k, v in by.items()},
            "exclusions": "RE1 candidate-pool rules; every BRE and BRS burst class; any support sharing >= 2 qubits with one",
            "draw": {"label": BURST_SEED_LABEL, "seed": seed, "rule": f"{C.PER_STRATUM} per stratum, one per class"},
            "h2_caveat": "H2 (RE1, sealed) was not read and could not be excluded; it is spent for confirmatory use."}


def screened():
    vals, rec, derive = PS.screened()
    raw = (ROOT / "BRS_SEEDS.json").read_bytes()
    b = json.loads(raw)
    v = set(b["seeds"].values()) | set(b["rehearsal_seeds"].values())
    vals |= v
    rec["outputs/qshift_adaptive_robust_v1/BRS_SEEDS.json"] = {"sha256": hashlib.sha256(raw).hexdigest(), "values": len(v)}
    return vals, rec, derive


def main():
    bo, so = ROOT / "BRT_BURSTS.json", ROOT / "BRT_SEEDS.json"
    if bo.exists() or so.exists():
        raise SystemExit("BRT_BURSTS.json / BRT_SEEDS.json exist")
    vals, rec, derive = screened()          # screen first: the class loader below shadows a prior `contract` module
    from multiprocessing import get_context
    with get_context("spawn").Pool(1) as pool:
        b = pool.apply(draw_bursts)
    used, seeds, reh = set(vals), {}, {}
    for k in C.all_keys(b):
        seeds[k] = derive(NS, k, used)
        used.add(seeds[k])
    for k in C.rehearsal_keys(b):
        reh[k] = derive(NS_REH, k, used)
        used.add(reh[k])
    bo.write_text(json.dumps(b, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    so.write_text(json.dumps({"schema": "qshift-adaptive-robust-brt-seeds-v1", "namespace": NS, "seeds": seeds,
                              "rehearsal_seeds": reh, "screened": rec, "union_screened": len(vals)},
                             indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(len(b["V"]), "bursts;", len(seeds), "seeds,", len(reh), "rehearsal; screened", len(vals))


if __name__ == "__main__":
    main()
