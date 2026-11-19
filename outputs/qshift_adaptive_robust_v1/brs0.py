"""BRS-0: E1S re-analysis of the EXISTING BRE pool arrays (PLAN_BRS.md). No sampling. Design check only: BRE is the
data that revealed E1's flag weakness, so nothing here is evidence or a verdict.

  python brs0.py [--workers 8]     -> results/brs/BRS0.json (aggregates; BRE bursts are already public)
"""
from __future__ import annotations

import argparse
import json
import time
from multiprocessing import get_context
from pathlib import Path

import numpy as np

import brs_config as C

ROOT = Path(__file__).resolve().parent
BRE = ROOT / "work" / "bre" / "eval"
OUT = ROOT / "results" / "brs" / "BRS0.json"


def job(name):
    import estimate3 as E3
    import estimate4 as E4
    import mm_contract as K
    rec = json.loads((BRE / "records" / name).read_text(encoding="utf-8"))
    z = np.load(BRE / "arrays" / name.replace(".json", ".npz"))
    x = np.unpackbits(z["det"], axis=1)[:, :120]
    obs, n = E3.rates_from_rows(x)
    f = E4.e1_with_set(obs, n)
    old = rec["fit"]["E1"]
    same = all(f[k] == old[k] for k in ("p_hat", "b_hat", "stat", "excluded", "objective"))
    acc = rec["learn"]["E1"]["class_index"]
    s = E4.structural_flags(f["excluded_set"], acc)
    true_cls = None
    if rec["kind"] == "burst":
        b = json.loads((ROOT / "BRE_BURSTS.json").read_text(encoding="utf-8"))
        sup = tuple((b["T"] | b["V"])[rec["burst"]])
        true_cls = K.B.truth(K.B.load_classes(), sup)[0]
    return {"name": name, "cond": rec["cond"], "kind": rec["kind"], "tuning": rec["tuning"], "in_family": rec["in_family"],
            "reproduces_bre_fit": bool(same), "set_matches_count": f["set_matches_count"], "excluded": f["excluded"],
            "e1_flag": E4.e1_flag(f), **s, "x_is_true_class": s["x_class"] is not None and s["x_class"] == true_cls,
            "accepted": acc, "learned_correct": rec["learn"]["E1"]["learned_correct"]}


def main(workers):
    if OUT.exists():
        raise SystemExit("BRS0.json exists; BRS-0 runs once")
    t0 = time.perf_counter()
    names = sorted(p.name for p in (BRE / "records").glob("*.json"))
    with get_context("spawn").Pool(workers) as pool:
        rows = pool.map(job, names)
    agg = {}
    for c in sorted({r["cond"] for r in rows}):
        rr = [r for r in rows if r["cond"] == c]
        a = {}
        for kind in ("burst", "q0"):
            k = [r for r in rr if r["kind"] == kind]
            fl_e1 = [r["e1_flag"] for r in k]
            fl_s = [r["e1_flag"] or r["S1_shape"] or r["S2_consistency"] for r in k]
            a[kind] = {"pools": len(k), "e1_flagged": sum(fl_e1), "e1s_flagged": sum(fl_s),
                       "S1": sum(r["S1_shape"] for r in k), "S2": sum(r["S2_consistency"] for r in k),
                       "x_is_true_class": sum(r["x_is_true_class"] for r in k),
                       "x_empty": sum(r["excluded"] == 0 for r in k),
                       "e1_learned": sum((not f) and r["learned_correct"] for r, f in zip(k, fl_e1)),
                       "e1s_learned": sum((not f) and r["learned_correct"] for r, f in zip(k, fl_s)),
                       "e1_false_accepts": sum((not f) and r["accepted"] is not None for r, f in zip(k, fl_e1))
                       if kind == "q0" else None,
                       "e1s_false_accepts": sum((not f) and r["accepted"] is not None for r, f in zip(k, fl_s))
                       if kind == "q0" else None}
        agg[c] = a
    out = {"schema": "qshift-adaptive-robust-brs0-v1", "status": "design check on BRE data; not evidence",
           "pools": len(rows), "all_reproduce_bre_fit": all(r["reproduces_bre_fit"] for r in rows),
           "all_set_matches_count": all(r["set_matches_count"] for r in rows), "conditions": agg,
           "wall_seconds": round(time.perf_counter() - t0, 1)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    main(ap.parse_args().workers)
