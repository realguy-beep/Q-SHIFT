"""Seal-closed H2 contamination probability for RE2 (PLAN_RE2.md rev 2) -> results/re2/OVERLAP.json.

H2 is never read. It is treated as uniform over RE1's committed 1,998-support candidate pool (its true draw
distribution, per HIDDEN_COMMITMENT_RE1.json), and is not conditioned on any published RE1 diagnostic.
A drawn class c is "contaminated" by H2 = h if c is h's class or c's representative support shares >= 2 qubits with h.
"""
from __future__ import annotations

import json
from multiprocessing import get_context

import re2_config as C

OUT = C.ROOT / "results" / "re2" / "OVERLAP.json"


def compute():
    import mm_contract as K
    import re1_seal
    import re2_pool as P
    cl = K.B.load_classes()
    base = re1_seal.candidate_pool()
    el, pl = P.eligible(), P.pools()
    hcls = {h: K.B.truth(cl, tuple(h))[0] for h in base}
    frac = {}
    for name, pool in pl.items():
        frac[name] = [sum(ci == hcls[h] or len(set(el[ci][0]) & set(h)) >= 2 for ci in pool) / len(pool) for h in base]
    same = {name: sum(sum(ci == hcls[h] for ci in pool) / len(pool) for h in base) / len(base)
            for name, pool in pl.items()}
    either = [1 - (1 - a) * (1 - b) for a, b in zip(frac["H3"], frac["H4"])]
    n = len(base)
    return {"schema": "qshift-adaptive-robust-re2-overlap-v1", "h2_prior": "uniform over RE1's committed candidate pool",
            "h2_read": False, "candidate_pool_size": n, "draw_pool_sizes": {k: len(v) for k, v in pl.items()},
            "rule": "contaminated if same class as H2, or representative shares >= 2 qubits with H2",
            "P_same_class": same,
            "P_contaminated_uniform_prior": {k: sum(v) / n for k, v in frac.items()} | {"either": sum(either) / n},
            "P_contaminated_worst_case": {k: max(v) for k, v in frac.items()} | {"either": max(either)},
            "not_conditioned_on": "RE1's published R6 diagnostics (deliberately; that would infer about H2)"}


def main():
    if OUT.exists():
        raise SystemExit("OVERLAP.json exists")
    with get_context("spawn").Pool(1) as pool:
        out = pool.apply(compute)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(out["P_contaminated_uniform_prior"]), json.dumps(out["P_contaminated_worst_case"]))


if __name__ == "__main__":
    main()
