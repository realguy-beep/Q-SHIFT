"""Phase B gate jobs (DEV_PROTOCOL.md).

  gate_jobs.py run <dev|rehearsal> [--workers 8]
Runs every pool job once (burst pools and q=0 pools), writing <out>/pools/<stem>.json once each and
raw arrays to work/<mode>/arrays/. Refuses to start if any pool output exists.
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO))
import contract as K  # noqa: E402
import learner_d5 as LD  # noqa: E402
from learner_d5 import L, m  # noqa: E402

_STATE = {}


def out_dirs(mode):
    res = ROOT / ("results" if mode == "dev" else "work") / f"gate_{mode}" / "pools"
    arr = ROOT / "work" / f"gate_{mode}" / "arrays"
    return res, arr


def _init():
    classes = K.load_classes()
    _STATE["classes"] = classes
    _STATE["learner"] = LD.FastParityLearner(classes, L.base_dem(K.SPEC), K.threshold(classes))


def _sample(qubits, q, n, seed):
    d, o = m.build_candidate_circuit(K.SPEC, q, qubits).compile_detector_sampler(seed=seed).sample(
        shots=n, separate_observables=True)
    return np.asarray(d, np.uint8), np.asarray(o, np.uint8)[:, 0]


def _sel(learner, x):
    s = learner.select(x)
    return {"class_index": s["class_index"], "q_hat": s["q_hat"], "delta": s["delta"]}


def burst_job(args):
    mode, b, k = args
    res, arr = out_dirs(mode)
    stem = f"{b}_pool{k:02d}"
    if (res / f"{stem}.json").exists():
        raise SystemExit(f"{stem} exists")
    seeds = json.loads((ROOT / "DEV_SEEDS.json").read_text(encoding="utf-8"))
    table = seeds["seeds"] if mode == "dev" else seeds["rehearsal_seeds"]
    classes, learner = _STATE["classes"], _STATE["learner"]
    t0 = time.perf_counter()
    dets, labx, laby, used = [], [], [], {}
    for qi, q in enumerate(K.QS):
        seed = int(table[K.burst_key(b, k, qi)])
        used[K.burst_key(b, k, qi)] = seed
        x, y = _sample(K.BURSTS[b], q, K.DET_PER_Q + K.LAB_PER_Q, seed)
        dets.append(x[: K.DET_PER_Q])                 # labels of these rows are discarded unread
        labx.append(x[K.DET_PER_Q:])
        laby.append(y[K.DET_PER_Q:])
    t_sample = time.perf_counter() - t0
    np.savez_compressed(arr / f"{stem}.npz", **{f"det_q{qi}": np.packbits(d, axis=1) for qi, d in enumerate(dets)},
                        **{f"labx_q{qi}": np.packbits(d, axis=1) for qi, d in enumerate(labx)},
                        **{f"laby_q{qi}": y for qi, y in enumerate(laby)})
    true_idx, true_flip = K.truth(classes, K.BURSTS[b])
    curve = {}
    for n in K.CURVE_PER_Q:
        curve[str(3 * n)] = _sel(learner, np.vstack([d[:n] for d in dets]))
    main = curve[str(3 * K.DET_PER_Q)]
    t1 = time.perf_counter()
    flip = None
    if main["class_index"] is not None:
        flip = LD.learn_flip(K.SPEC, classes[main["class_index"]], np.vstack(labx), np.concatenate(laby))
    t_flip = time.perf_counter() - t1
    class_ok = main["class_index"] == true_idx
    rec = {"burst": b, "pool": k, "mode": mode, "seeds": used, "true_support": list(K.BURSTS[b]),
           "true_class": true_idx, "true_flip": true_flip, "selection_12k": main, "curve": curve,
           "class_correct": class_ok, "flip": flip,
           "flip_correct": bool(class_ok and flip is not None and flip["flip"] == true_flip),
           "learned_support": (list(classes[main["class_index"]].representative(flip["flip"]))
                               if flip is not None else None),
           "seconds": {"sample": t_sample, "flip": t_flip, "total": time.perf_counter() - t0}}
    (res / f"{stem}.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    return stem


def q0_job(args):
    mode, k = args
    res, arr = out_dirs(mode)
    stem = f"Q0_pool{k:02d}"
    if (res / f"{stem}.json").exists():
        raise SystemExit(f"{stem} exists")
    seeds = json.loads((ROOT / "DEV_SEEDS.json").read_text(encoding="utf-8"))
    seed = int((seeds["seeds"] if mode == "dev" else seeds["rehearsal_seeds"])[K.q0_key(k)])
    t0 = time.perf_counter()
    x, _ = _sample(K.BURSTS["SC"], 0.0, K.Q0_POOL_SHOTS, seed)   # q=0: burst-free circuit (labels unread)
    np.savez_compressed(arr / f"{stem}.npz", det=np.packbits(x, axis=1))
    curve = {str(3 * n): _sel(_STATE["learner"], x[: 3 * n]) for n in K.CURVE_PER_Q}
    rec = {"burst": "Q0", "pool": k, "mode": mode, "seed": seed, "selection_12k": curve[str(K.Q0_POOL_SHOTS)],
           "curve": curve, "no_burst": curve[str(K.Q0_POOL_SHOTS)]["class_index"] is None,
           "seconds": {"total": time.perf_counter() - t0}}
    (res / f"{stem}.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    return stem


def _dispatch(job):
    return burst_job(job[1:]) if job[0] == "burst" else q0_job(job[1:])


def main() -> None:
    mode = sys.argv[2]
    if sys.argv[1] != "run" or mode not in ("dev", "rehearsal"):
        raise SystemExit(__doc__)
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 8
    pools = K.POOLS if mode == "dev" else K.REHEARSAL_POOLS
    res, arr = out_dirs(mode)
    if res.exists() and any(res.iterdir()):
        raise SystemExit(f"{res} not empty; the gate runs once")
    res.mkdir(parents=True, exist_ok=True)
    arr.mkdir(parents=True, exist_ok=True)
    # Mixed-class bursts first (they carry the L2 flip decodes).
    jobs = [("burst", mode, b, k) for b in ("M0", "M1", "SC", "CR") for k in range(pools)] + \
           [("q0", mode, k) for k in range(pools)]
    started = time.time()
    with ProcessPoolExecutor(max_workers=workers, initializer=_init) as pool:
        for stem in pool.map(_dispatch, jobs):
            print(stem, round(time.time() - started, 1), flush=True)
    print("DONE", len(jobs), round(time.time() - started, 1))


if __name__ == "__main__":
    main()
