"""Roadmap step 2 / H-E1: mismatch-robust burst-support learning on EXISTING development arrays (HE1_PROTOCOL.md).

  python he1.py run [--workers 8]    one write-once record per pool in results/he1/pools
  python he1.py analyze              results/he1/HE1.json

Arm N (nominal, Phase C unchanged): FastParityLearner on the nominal base DEM (p = 0.003, balanced), tau = 1,561.218.
Arm R (robust): estimate a scalar background p_hat from the pool's UNLABELED detector rows (robust trimmed fit of
observed single-detector rates to the base-DEM rate curve), then run the SAME learner and flip stage on the base
DEM at p_hat (balanced), tau unchanged. Nothing is tuned: trim 0.2 is the adaptive/estimation.py default.

Data (development only, no sampling): mismatch Phase A pools (Mlo, Mhi, Mz; 24 burst + 24 burst-free each) and the
Phase B2 matched-model development pools (SC burst = the known support, Q0 burst-free) as the control.
Never reads Phase C evaluation archives (work/c_eval_v1) or any sealed material.
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
OUTS = ROOT.parent
REPO = OUTS.parent
MM = OUTS / "qshift_d5_model_mismatch_v1"
LS = OUTS / "qshift_d5_learned_support_v1"
for p in (ROOT, MM, LS, REPO):
    sys.path.insert(0, str(p))

TRIM = 0.2
P_GRID = np.geomspace(0.0012, 0.0075, 61)
RES = ROOT / "results" / "he1"


def pools():
    out = []
    for c in ("Mlo", "Mhi", "Mz"):
        out += [(c, "burst", k, str(MM / "work/diag_arrays" / f"{c}_burst{k:02d}.npz")) for k in range(24)]
        out += [(c, "q0", k, str(MM / "work/diag_arrays" / f"{c}_q0{k:02d}.npz")) for k in range(24)]
    out += [("CTRL", "burst", k, str(LS / "work/b2_dev/arrays" / f"SC_pool{k:02d}.npz")) for k in range(24)]
    out += [("CTRL", "q0", k, str(LS / "work/b2_dev/arrays" / f"Q0_pool{k:02d}.npz")) for k in range(24)]
    return out


def _unpack(a, n_det=120):
    return np.unpackbits(a, axis=1)[:, :n_det].astype(np.uint8)


def spec_at(p):
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    return m.CodeSpec(distance=5, gate_p=float(p), measurement_p=float(p))


def detector_rates(dem):
    from outputs.qshift_v1_4b_decoder_optimality.mld import dem_mechanisms
    acc = np.zeros(dem.num_detectors)
    for mm in dem_mechanisms(dem):
        for d in mm.detectors:
            acc[d] += np.log1p(-2 * mm.p)
    return (1 - np.exp(acc)) / 2


@lru_cache(maxsize=1)
def rate_grid():
    from outputs.qshift_correlated_decoder_v1_6 import learner as L
    return np.log(np.stack([detector_rates(L.base_dem(spec_at(p))) for p in P_GRID]))


def estimate_p(x):
    """Root in log p of trimmed_mean(log obs_i - log rate_i(p)) = 0 on the precomputed grid."""
    from adaptive.estimation import _trimmed_mean
    n = len(x)
    lo = np.log(np.maximum(x.mean(axis=0), 0.5 / n))
    f = np.array([_trimmed_mean(lo - g, TRIM) for g in rate_grid()])     # decreasing in p
    if f[0] < 0 or f[-1] > 0:
        raise ValueError("p_hat outside grid")
    i = int(np.flatnonzero(f < 0)[0])
    lp = np.log(P_GRID)
    t = f[i - 1] / (f[i - 1] - f[i])
    return float(np.exp(lp[i - 1] + t * (lp[i] - lp[i - 1])))


def load_pool(path, kind):
    z = np.load(path)
    if kind == "q0":
        return _unpack(z["det"]), None, None
    dets = [_unpack(z[f"det_q{i}"]) for i in range(3)]
    labx = [_unpack(z[f"labx_q{i}"]) for i in range(3)]
    laby = [z[f"laby_q{i}"] for i in range(3)]
    return dets, labx, laby


def _learn(spec, classes, x_dets, labx, laby):
    import learner_d5 as LD
    import mm_contract as K
    from outputs.qshift_correlated_decoder_v1_6 import learner as L
    lr = LD.FastParityLearner(classes, L.base_dem(spec), K.tau())
    if labx is None:
        sel = lr.select(x_dets)
        return {"class_index": sel["class_index"], "delta": sel["delta"], "no_burst": sel["class_index"] is None}
    sel = lr.select(np.vstack(x_dets))
    flip = None
    if sel["class_index"] is not None:
        flip = LD.learn_flip(spec, classes[sel["class_index"]], np.vstack(labx), np.concatenate(laby))
    t_idx, t_flip = K.B.truth(classes, K.SUPPORT)
    return {"class_index": sel["class_index"], "delta": sel["delta"], "q_hat": sel["q_hat"],
            "class_correct": sel["class_index"] == t_idx,
            "learned_correct": bool(sel["class_index"] == t_idx and flip is not None and flip["flip"] == t_flip)}


def run_pool(job):
    import mm_contract as K
    c, kind, k, path = job
    out = RES / "pools" / f"{c}_{kind}{k:02d}.json"
    if out.exists():
        raise SystemExit(f"{out.name} exists")
    t0 = time.perf_counter()
    classes = K.B.load_classes()
    x, labx, laby = load_pool(path, kind)
    unlabeled = x if kind == "q0" else np.vstack(x)
    p_hat = estimate_p(unlabeled)
    rec = {"cond": c, "kind": kind, "pool": k, "source": str(Path(path).relative_to(REPO)).replace("\\", "/"),
           "p_hat": p_hat,
           "N": _learn(K.NOMINAL_SPEC, classes, x, labx, laby),
           "R": _learn(spec_at(round(p_hat, 7)), classes, x, labx, laby),
           "seconds": round(time.perf_counter() - t0, 1)}
    out.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    return out.name


def cmd_run(workers):
    if (RES / "pools").exists():
        raise SystemExit("results/he1/pools exists; H-E1 runs once")
    (RES / "pools").mkdir(parents=True)
    t0 = time.perf_counter()
    with get_context("spawn").Pool(workers) as pool:
        for i, name in enumerate(pool.imap_unordered(run_pool, pools()), 1):
            print(name, i, f"{time.perf_counter() - t0:.0f}s", flush=True)
    (RES / "RUN_LOG.json").write_text(json.dumps({"pools": len(pools()), "wall_seconds": round(time.perf_counter() - t0, 1)}))


def cmd_analyze():
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((RES / "pools").glob("*.json"))]
    if len(recs) != len(pools()):
        raise SystemExit("incomplete")
    diag = {r.name: json.loads(r.read_text(encoding="utf-8")) for r in (MM / "results/diag/pools").glob("*.json")}
    true_p = {"Mlo": 0.0025, "Mhi": 0.0035, "Mz": None, "CTRL": 0.003}
    out = {"schema": "qshift-adaptive-robust-he1-v1", "protocol": "HE1_PROTOCOL.md", "conditions": {}}
    ident_ok = True
    for c in ("Mlo", "Mhi", "Mz", "CTRL"):
        b = [r for r in recs if r["cond"] == c and r["kind"] == "burst"]
        z = [r for r in recs if r["cond"] == c and r["kind"] == "q0"]
        if c != "CTRL":       # arm N must reproduce the recorded Phase A diagnostic selections
            for r in b + z:
                d = diag[f"{c}_{'burst' if r['kind'] == 'burst' else 'q0'}{r['pool']:02d}.json"]["selection"]
                ident_ok &= (d["class_index"] == r["N"]["class_index"]) and abs(d["delta"] - r["N"]["delta"]) < 1e-6 * max(1, abs(d["delta"]))
        row = {}
        for arm in ("N", "R"):
            row[arm] = {"class_correct": sum(r[arm]["class_correct"] for r in b),
                        "learned_correct": sum(r[arm]["learned_correct"] for r in b),
                        "none_accepted_burst": sum(r[arm]["class_index"] is None for r in b),
                        "false_accepts_q0": sum(not r[arm]["no_burst"] for r in z),
                        "q0_delta_max": max(r[arm]["delta"] for r in z)}
        ph = np.array([r["p_hat"] for r in b + z])
        row["p_hat"] = {"mean": float(ph.mean()), "sd": float(ph.std(ddof=1)), "true": true_p[c]}
        R = row["R"]
        if c == "CTRL":
            row["verdict"] = ("CONTROL_OK" if R["class_correct"] >= row["N"]["class_correct"] - 2 and R["false_accepts_q0"] <= 1
                              else "CONTROL_DEGRADED")
        else:
            row["verdict"] = "PASS" if R["class_correct"] >= 20 and R["false_accepts_q0"] <= 1 else "FAIL"
        out["conditions"][c] = row
    v = [out["conditions"][c]["verdict"] for c in ("Mlo", "Mhi", "Mz")]
    ctrl = out["conditions"]["CTRL"]["verdict"] == "CONTROL_OK"
    out["identity_check_arm_N_matches_phase_A"] = bool(ident_ok)
    out["overall"] = ("INVALID" if not ident_ok else
                      "H-E1_SUPPORTED" if all(x == "PASS" for x in v) and ctrl else
                      "H-E1_PARTIAL" if any(x == "PASS" for x in v) and ctrl else
                      "H-E1_NOT_SUPPORTED")
    out["wall_seconds"] = json.loads((RES / "RUN_LOG.json").read_text())["wall_seconds"]
    (RES / "HE1.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "analyze"])
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    cmd_run(a.workers) if a.cmd == "run" else cmd_analyze()
