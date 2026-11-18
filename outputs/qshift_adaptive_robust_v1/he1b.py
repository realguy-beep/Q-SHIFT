"""H-E1b: bias-aware re-basing of the Phase C learner on EXISTING development arrays (HE1B_PROTOCOL.md).

  python he1b.py run [--workers 8]    one write-once record per pool in results/he1b/pools
  python he1b.py analyze              results/he1b/HE1B.json

Arm B: fit (p, bias) jointly from the pool's UNLABELED detector rows by minimizing a trimmed sum of squared
standardized log-rate residuals over a fixed grid of z_biased base models (bias 1 == balanced, verified), then run
the unchanged learner and flip stage on the base DEM at (p_hat, bias_hat), tau unchanged. Same pools as H-E1.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from functools import lru_cache
from multiprocessing import get_context
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import he1 as H  # noqa: E402  (pools, loaders, rates, learner wrapper; unchanged)

P_GRID = np.geomspace(0.0012, 0.0075, 61)
B_GRID = (1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0, 15.0, 20.0, 30.0)
TRIM = 0.2                         # fraction of largest squared residuals dropped (burst-robust)
RES = ROOT / "results" / "he1b"


def spec_at(p, b):
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    return m.CodeSpec(distance=5, gate_p=float(p), measurement_p=float(p), regime="z_biased", bias_ratio=float(b))


@lru_cache(maxsize=1)
def grid():
    from outputs.qshift_correlated_decoder_v1_6 import learner as L
    return np.stack([[np.log(H.detector_rates(L.base_dem(spec_at(p, b)))) for p in P_GRID] for b in B_GRID])


def fit(x):
    n = len(x)
    obs = np.maximum(x.mean(axis=0), 0.5 / n)
    lo = np.log(obs)
    w = n * obs                                   # 1 / var(log rate) ~ n * rate
    r2 = (lo[None, None, :] - grid()) ** 2 * w    # (bias, p, detectors)
    k = int(np.floor(TRIM * r2.shape[-1]))
    obj = np.sort(r2, axis=-1)[..., : r2.shape[-1] - k].sum(axis=-1)
    bi, pi = np.unravel_index(int(np.argmin(obj)), obj.shape)
    return float(P_GRID[pi]), float(B_GRID[bi]), float(obj[bi, pi])


def run_pool(job):
    import mm_contract as K
    c, kind, k, path = job
    out = RES / "pools" / f"{c}_{kind}{k:02d}.json"
    if out.exists():
        raise SystemExit(f"{out.name} exists")
    t0 = time.perf_counter()
    classes = K.B.load_classes()
    x, labx, laby = H.load_pool(path, kind)
    p_hat, b_hat, obj = fit(x if kind == "q0" else np.vstack(x))
    rec = {"cond": c, "kind": kind, "pool": k, "p_hat": p_hat, "bias_hat": b_hat, "fit_objective": obj,
           "B": H._learn(spec_at(p_hat, b_hat), classes, x, labx, laby), "seconds": round(time.perf_counter() - t0, 1)}
    out.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    return out.name


def cmd_run(workers):
    if (RES / "pools").exists():
        raise SystemExit("results/he1b/pools exists; H-E1b runs once")
    (RES / "pools").mkdir(parents=True)
    t0 = time.perf_counter()
    with get_context("spawn").Pool(workers) as pool:
        for i, name in enumerate(pool.imap_unordered(run_pool, H.pools()), 1):
            print(name, i, f"{time.perf_counter() - t0:.0f}s", flush=True)
    (RES / "RUN_LOG.json").write_text(json.dumps({"pools": len(H.pools()), "wall_seconds": round(time.perf_counter() - t0, 1)}))


def cmd_analyze():
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((RES / "pools").glob("*.json"))]
    if len(recs) != len(H.pools()):
        raise SystemExit("incomplete")
    he1 = json.loads((ROOT / "results/he1/HE1.json").read_text(encoding="utf-8"))["conditions"]
    out = {"schema": "qshift-adaptive-robust-he1b-v1", "protocol": "HE1B_PROTOCOL.md", "grids":
           {"p": [float(P_GRID[0]), float(P_GRID[-1]), len(P_GRID)], "bias": list(B_GRID)}, "conditions": {}}
    for c in ("Mlo", "Mhi", "Mz", "CTRL"):
        b = [r for r in recs if r["cond"] == c and r["kind"] == "burst"]
        z = [r for r in recs if r["cond"] == c and r["kind"] == "q0"]
        B = {"class_correct": sum(r["B"]["class_correct"] for r in b),
             "learned_correct": sum(r["B"]["learned_correct"] for r in b),
             "none_accepted_burst": sum(r["B"]["class_index"] is None for r in b),
             "false_accepts_q0": sum(not r["B"]["no_burst"] for r in z),
             "q0_delta_max": max(r["B"]["delta"] for r in z)}
        bh = [r["bias_hat"] for r in b + z]
        row = {"B": B, "H-E1_R": he1[c]["R"],
               "p_hat": {"mean": float(np.mean([r["p_hat"] for r in b + z])), "sd": float(np.std([r["p_hat"] for r in b + z], ddof=1))},
               "bias_hat": {"median": float(np.median(bh)), "min": min(bh), "max": max(bh),
                            "counts": {str(v): bh.count(v) for v in sorted(set(bh))}}}
        if c == "Mz":
            row["verdict"] = "PASS" if B["class_correct"] >= 20 and B["false_accepts_q0"] <= 1 else "FAIL"
        else:
            row["verdict"] = "NO_DEGRADATION" if B["class_correct"] >= 22 and B["false_accepts_q0"] <= 1 else "DEGRADED"
        out["conditions"][c] = row
    v = {c: out["conditions"][c]["verdict"] for c in out["conditions"]}
    others_ok = all(v[c] == "NO_DEGRADATION" for c in ("Mlo", "Mhi", "CTRL"))
    out["overall"] = ("H-E1b_SUPPORTED" if v["Mz"] == "PASS" and others_ok else
                      "H-E1b_PARTIAL" if v["Mz"] == "PASS" or others_ok else "H-E1b_NOT_SUPPORTED")
    out["wall_seconds"] = json.loads((RES / "RUN_LOG.json").read_text())["wall_seconds"]
    (RES / "HE1B.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze"])
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    cmd_run(a.workers) if a.cmd == "run" else cmd_analyze()
