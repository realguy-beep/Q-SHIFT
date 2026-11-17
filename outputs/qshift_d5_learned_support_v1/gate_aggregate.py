"""Aggregate Phase B pool records into the pre-registered gate decision.

  gate_aggregate.py <dev|rehearsal> <out_json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import contract as K  # noqa: E402
import gate_jobs  # noqa: E402


def aggregate(mode: str) -> dict:
    res, _ = gate_jobs.out_dirs(mode)
    pools = K.POOLS if mode == "dev" else K.REHEARSAL_POOLS
    recs = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(res.glob("*.json"))}
    expected = [f"{b}_pool{k:02d}" for b in K.BURSTS for k in range(pools)] + [f"Q0_pool{k:02d}" for k in range(pools)]
    if sorted(recs) != sorted(expected):
        raise SystemExit("pool records incomplete or unexpected")
    seeds = json.loads((ROOT / "DEV_SEEDS.json").read_text(encoding="utf-8"))
    table = seeds["seeds"] if mode == "dev" else seeds["rehearsal_seeds"]
    for stem, r in recs.items():
        used = r["seeds"] if r["burst"] != "Q0" else {K.q0_key(r["pool"]): r["seed"]}
        if any(table[k] != v for k, v in used.items()):
            raise SystemExit(f"seed mismatch in {stem}")
    out = {"schema": "qshift-d5-learned-support-gate-v1", "mode": mode, "pools_per_burst": pools, "bursts": {}}
    g1 = g3 = True
    for b in K.BURSTS:
        rs = [recs[f"{b}_pool{k:02d}"] for k in range(pools)]
        cls_ok = sum(r["class_correct"] for r in rs)
        flip_ok = sum(r["flip_correct"] for r in rs)
        frac = flip_ok / cls_ok if cls_ok else 0.0
        curve = {n: sum(r["curve"][n]["class_index"] == r["true_class"] for r in rs) for n in rs[0]["curve"]}
        qerr = [abs(r["selection_12k"]["q_hat"] - 0.01) for r in rs if r["class_correct"]]
        out["bursts"][b] = {
            "true_support": rs[0]["true_support"], "true_class": rs[0]["true_class"], "true_flip": rs[0]["true_flip"],
            "class_correct": cls_ok, "flip_correct": flip_ok, "flip_fraction_of_class_correct": frac,
            "flip_methods": sorted({r["flip"]["method"] for r in rs if r["flip"]}),
            "curve_class_correct": curve,
            "q_hat_mae_vs_pooled_mean_0.01": (sum(qerr) / len(qerr)) if qerr else None,
            "learned_supports": sorted({tuple(r["learned_support"]) for r in rs if r["learned_support"]}),
            "wrong_selections": [{"pool": r["pool"], "selected": r["selection_12k"]["class_index"],
                                  "delta": r["selection_12k"]["delta"]} for r in rs if not r["class_correct"]],
            "mean_seconds": sum(r["seconds"]["total"] for r in rs) / len(rs),
        }
        need = K.G1_MIN if mode == "dev" else pools
        g1 &= cls_ok >= need
        g3 &= frac >= K.G3_MIN_FRACTION
    q0 = [recs[f"Q0_pool{k:02d}"] for k in range(pools)]
    nb = sum(r["no_burst"] for r in q0)
    out["q0"] = {"no_burst": nb, "curve_no_burst": {n: sum(r["curve"][n]["class_index"] is None for r in q0) for n in q0[0]["curve"]},
                 "false_selections": [{"pool": r["pool"], "selected": r["selection_12k"]["class_index"],
                                       "delta": r["selection_12k"]["delta"]} for r in q0 if not r["no_burst"]],
                 "max_delta": max(r["selection_12k"]["delta"] for r in q0)}
    g2 = nb >= (K.G2_MIN if mode == "dev" else pools)
    out["gates"] = {"G1_class": g1, "G2_q0_no_burst": g2, "G3_flip": g3,
                    "rule": f"G1: each burst >= {K.G1_MIN}/{K.POOLS}; G2: >= {K.G2_MIN}/{K.POOLS}; G3: >= {K.G3_MIN_FRACTION}"}
    out["decision"] = "PASS" if (g1 and g2 and g3) else "STOP"
    out["threshold"] = K.threshold(K.load_classes())
    return out


if __name__ == "__main__":
    mode, target = sys.argv[1], Path(sys.argv[2])
    if target.exists():
        raise SystemExit(f"{target} exists")
    rec = aggregate(mode)
    target.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"decision": rec["decision"], "gates": rec["gates"],
                      "class_correct": {b: v["class_correct"] for b, v in rec["bursts"].items()},
                      "flip_correct": {b: v["flip_correct"] for b, v in rec["bursts"].items()},
                      "q0_no_burst": rec["q0"]["no_burst"]}, indent=2))
