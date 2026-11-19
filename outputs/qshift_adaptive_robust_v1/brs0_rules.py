"""BRS-0 rule comparison on the EXISTING BRE arrays (no sampling; design check, not evidence).

BRS0.json (brs0.py) was produced with the plan's EXACT shape rule, before the owner chose the subset rule. This script
compares three shape rules on the same 672 pools, and checks that the final estimate4.structural_flags equals the
subset rule here:
  exact        X equals the accepted class's detector set
  per_round_1  every round event of the accepted class misses at most 1 detector of X, and at most one extra
               detector per round (the plan's pre-declared fallback)
  subset       X is contained in the accepted class's detector set (chosen)
In all three, X empty with a class accepted, or X non-empty with none accepted, is flagged.

  python brs0_rules.py [--workers 8]  -> results/brs/BRS0_RULES.json
"""
from __future__ import annotations

import argparse
import json
from multiprocessing import get_context
from pathlib import Path

import numpy as np

import brs_config as C  # noqa: F401

ROOT = Path(__file__).resolve().parent
BRE = ROOT / "work" / "bre" / "eval"
OUT = ROOT / "results" / "brs" / "BRS0_RULES.json"
RULES = ("exact", "per_round_1", "subset")


def job(name):
    import estimate3 as E3
    import estimate4 as E4
    import mm_contract as K
    rec = json.loads((BRE / "records" / name).read_text(encoding="utf-8"))
    z = np.load(BRE / "arrays" / name.replace(".json", ".npz"))
    obs, n = E3.rates_from_rows(np.unpackbits(z["det"], axis=1)[:, :120])
    f = E4.e1_with_set(obs, n)
    X = set(f["excluded_set"])
    acc = rec["learn"]["E1"]["class_index"]
    cl = K.B.load_classes()
    flags = {}
    for rule in RULES:
        if not X:
            flags[rule] = acc is not None
        elif acc is None:
            flags[rule] = True
        else:
            S = set(E3.class_detectors(cl[acc]))
            ev = [set(int(d) for d in e) for e in cl[acc].events]
            flags[rule] = not {"exact": X == S, "subset": X <= S,
                               "per_round_1": len(X - S) <= len(ev) and all(len(e - X) <= 1 for e in ev)}[rule]
    st = E4.structural_flags(sorted(X), acc)
    final = st["S1_shape"] or st["S2_consistency"]
    return {"cond": rec["cond"], "kind": rec["kind"], "e1_flag": E4.e1_flag(f), "accepted": acc,
            "learned_correct": rec["learn"]["E1"]["learned_correct"], **flags, "final_equals_subset": final == flags["subset"]}


def main(workers):
    if OUT.exists():
        raise SystemExit("BRS0_RULES.json exists")
    names = sorted(p.name for p in (BRE / "records").glob("*.json"))
    with get_context("spawn").Pool(workers) as pool:
        rows = pool.map(job, names)
    out = {"schema": "qshift-adaptive-robust-brs0-rules-v1", "status": "design check on BRE data; not evidence",
           "final_rule_equals_subset_everywhere": all(r["final_equals_subset"] for r in rows), "rules": {}}
    for rule in RULES:
        res = {}
        for c in sorted({r["cond"] for r in rows}):
            b = [r for r in rows if r["cond"] == c and r["kind"] == "burst"]
            z = [r for r in rows if r["cond"] == c and r["kind"] == "q0"]
            fb = [r["e1_flag"] or r[rule] for r in b]
            fz = [r["e1_flag"] or r[rule] for r in z]
            res[c] = {"burst_pools": len(b), "burst_flagged": sum(fb),
                      "burst_learned": sum((not f) and r["learned_correct"] for r, f in zip(b, fb)),
                      "q0_pools": len(z), "q0_flagged": sum(fz),
                      "q0_false_accepts": sum((not f) and r["accepted"] is not None for r, f in zip(z, fz))}
        out["rules"][rule] = res
    OUT.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({r: {c: [v["burst_flagged"], v["q0_false_accepts"]] for c, v in out["rules"][r].items()}
                      for r in RULES}), out["final_rule_equals_subset_everywhere"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    main(ap.parse_args().workers)
