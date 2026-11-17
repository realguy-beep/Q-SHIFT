"""Phase B2: null-calibrated development gate (GATE_B2_PROTOCOL.md).

  b2.py seeds                                   write B2_SEEDS.json (once)
  b2.py null <dev|rehearsal> [--workers 8]       null calibration -> NULL_THRESHOLD.json (dev) once
  b2.py gate <dev|rehearsal> [--workers 8]       gate pools (needs committed NULL_THRESHOLD.json in dev)
  b2.py aggregate <dev|rehearsal> <out_json>     gate decision
Phase B files (gate_jobs.py, gate_aggregate.py, DEV_SEEDS.json) are not modified; this reuses their logic
with B2 seeds, B2 output folders and the calibrated threshold tau.
"""
from __future__ import annotations

import json
import subprocess
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
import prepare_dev_seeds as PB  # noqa: E402
from learner_d5 import L, m  # noqa: E402

SEEDS = ROOT / "B2_SEEDS.json"
THRESH = ROOT / "NULL_THRESHOLD.json"
NAMESPACE = "qshift-d5-learned-support-b2-2026-11-17"
REHEARSAL_NAMESPACE = "qshift-d5-learned-support-b2-REHEARSAL-2026-11-17"
N_NULL, NULL_SHOTS, TAU_MAX = 500, 12_000, 3_000.0
REHEARSAL_NULL = 2
_STATE = {}


def null_key(k):
    return f"d5ls:b2:null:pool{k:03d}"


def gate_keys(pools):
    return [k.replace("d5ls:dev:", "d5ls:b2:dev:") for k in K.all_keys(pools)]


def gkey(key):
    return key.replace("d5ls:dev:", "d5ls:b2:dev:")


def all_keys(mode):
    n_null, pools = (N_NULL, K.POOLS) if mode == "dev" else (REHEARSAL_NULL, K.REHEARSAL_POOLS)
    return [null_key(k) for k in range(n_null)] + gate_keys(pools)


def make_seeds():
    if SEEDS.exists():
        raise SystemExit("B2_SEEDS.json exists")
    screened, rec = PB.screened_values()
    raw = (ROOT / "DEV_SEEDS.json").read_bytes()
    pb = json.loads(raw)
    phase_b = set(pb["seeds"].values()) | set(pb["rehearsal_seeds"].values())
    rec["outputs/qshift_d5_learned_support_v1/DEV_SEEDS.json"] = {"sha256": PB.hashlib.sha256(raw).hexdigest(),
                                                                  "values": len(phase_b)}
    screened |= phase_b
    used = set(screened)
    out = {}
    for name, ns, mode in (("seeds", NAMESPACE, "dev"), ("rehearsal_seeds", REHEARSAL_NAMESPACE, "rehearsal")):
        out[name] = {}
        for key in all_keys(mode):
            out[name][key] = PB.derive(ns, key, used)
            used.add(out[name][key])
    SEEDS.write_text(json.dumps({"schema": "qshift-d5-learned-support-b2-seeds-v1", "namespace": NAMESPACE, **out,
                                 "screened": rec, "union_screened": len(screened)}, indent=2, sort_keys=True) + "\n",
                     encoding="utf-8", newline="\n")
    print(len(out["seeds"]), "seeds,", len(out["rehearsal_seeds"]), "rehearsal; screened", len(screened))


def seed_table(mode):
    s = json.loads(SEEDS.read_text(encoding="utf-8"))
    return s["seeds"] if mode == "dev" else s["rehearsal_seeds"]


def dirs(mode):
    res = ROOT / ("results" if mode == "dev" else "work") / f"b2_{mode}"
    arr = ROOT / "work" / f"b2_{mode}" / "arrays"
    return res, arr


def _init(tau):
    classes = K.load_classes()
    _STATE["classes"] = classes
    _STATE["learner"] = LD.FastParityLearner(classes, L.base_dem(K.SPEC), tau)


def _sample(qubits, q, n, seed):
    d, o = m.build_candidate_circuit(K.SPEC, q, qubits).compile_detector_sampler(seed=seed).sample(
        shots=n, separate_observables=True)
    return np.asarray(d, np.uint8), np.asarray(o, np.uint8)[:, 0]


def _sel(x):
    s = _STATE["learner"].select(x)
    return {"class_index": s["class_index"], "q_hat": s["q_hat"], "delta": s["delta"]}


# ---------------------------------------------------------------- null calibration
def null_job(args):
    mode, k = args
    seed = int(seed_table(mode)[null_key(k)])
    x, _ = _sample(K.BURSTS["SC"], 0.0, NULL_SHOTS, seed)   # q=0: burst-free base circuit; labels unread
    q, delta = _STATE["learner"].fit_all(x)
    i = int(np.argmax(delta))
    return {"pool": k, "seed": seed, "T": float(delta[i]), "argmax_class": i, "q_hat_at_argmax": float(q[i])}


def run_null(mode, workers):
    res, _ = dirs(mode)
    target = THRESH if mode == "dev" else res / "NULL_THRESHOLD_rehearsal.json"
    if target.exists():
        raise SystemExit(f"{target.name} exists; null calibration runs once")
    res.mkdir(parents=True, exist_ok=True)
    n = N_NULL if mode == "dev" else REHEARSAL_NULL
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers, initializer=_init, initargs=(float("inf"),)) as pool:
        recs = list(pool.map(null_job, [(mode, k) for k in range(n)]))
    ts = [r["T"] for r in recs]
    tau = max(ts)
    out = {"schema": "qshift-d5-learned-support-null-threshold-v1", "mode": mode, "n_pools": n,
           "shots_per_pool": NULL_SHOTS, "tau": tau, "tau_rule": "max of null T = max_c Delta_c over pools",
           "viable": 0.0 < tau < TAU_MAX, "tau_max": TAU_MAX,
           "T_quantiles": {str(p): float(np.quantile(ts, p)) for p in (0.5, 0.9, 0.95, 0.99)},
           "T_zero_pools": sum(t == 0.0 for t in ts), "seconds": time.time() - t0, "pools": recs}
    target.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in out.items() if k != "pools"}, indent=2))


def load_tau(mode):
    if mode == "dev":
        rel = "outputs/qshift_d5_learned_support_v1/NULL_THRESHOLD.json"
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=REPO, capture_output=True).returncode == 0
        clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=REPO).returncode == 0
        if not (tracked and clean):
            raise SystemExit("NULL_THRESHOLD.json must be committed (and unchanged) before the B2 gate")
        rec = json.loads(THRESH.read_text(encoding="utf-8"))
    else:
        rec = json.loads((dirs(mode)[0] / "NULL_THRESHOLD_rehearsal.json").read_text(encoding="utf-8"))
    if not rec["viable"]:
        raise SystemExit(f"tau {rec['tau']} >= {TAU_MAX}: pre-declared viability check failed; B2 stops")
    return float(rec["tau"])


# ---------------------------------------------------------------- gate
def burst_job(args):
    mode, b, k = args
    res, arr = dirs(mode)
    stem = f"{b}_pool{k:02d}"
    out = res / "pools" / f"{stem}.json"
    if out.exists():
        raise SystemExit(f"{stem} exists")
    table, classes = seed_table(mode), _STATE["classes"]
    t0 = time.perf_counter()
    dets, labx, laby, used = [], [], [], {}
    for qi, q in enumerate(K.QS):
        key = gkey(K.burst_key(b, k, qi))
        used[key] = int(table[key])
        x, y = _sample(K.BURSTS[b], q, K.DET_PER_Q + K.LAB_PER_Q, used[key])
        dets.append(x[: K.DET_PER_Q])                 # labels of these rows are discarded unread
        labx.append(x[K.DET_PER_Q:])
        laby.append(y[K.DET_PER_Q:])
    np.savez_compressed(arr / f"{stem}.npz", **{f"det_q{qi}": np.packbits(d, axis=1) for qi, d in enumerate(dets)},
                        **{f"labx_q{qi}": np.packbits(d, axis=1) for qi, d in enumerate(labx)},
                        **{f"laby_q{qi}": y for qi, y in enumerate(laby)})
    true_idx, true_flip = K.truth(classes, K.BURSTS[b])
    curve = {str(3 * n): _sel(np.vstack([d[:n] for d in dets])) for n in K.CURVE_PER_Q}
    main = curve[str(3 * K.DET_PER_Q)]
    flip = None
    if main["class_index"] is not None:
        flip = LD.learn_flip(K.SPEC, classes[main["class_index"]], np.vstack(labx), np.concatenate(laby))
    class_ok = main["class_index"] == true_idx
    rec = {"burst": b, "pool": k, "mode": mode, "seeds": used, "true_support": list(K.BURSTS[b]),
           "true_class": true_idx, "true_flip": true_flip, "selection_12k": main, "curve": curve,
           "class_correct": class_ok, "flip": flip,
           "flip_correct": bool(class_ok and flip is not None and flip["flip"] == true_flip),
           "learned_support": (list(classes[main["class_index"]].representative(flip["flip"]))
                               if flip is not None else None),
           "seconds": time.perf_counter() - t0}
    out.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    return stem


def q0_job(args):
    mode, k = args
    res, arr = dirs(mode)
    stem = f"Q0_pool{k:02d}"
    out = res / "pools" / f"{stem}.json"
    if out.exists():
        raise SystemExit(f"{stem} exists")
    key = gkey(K.q0_key(k))
    seed = int(seed_table(mode)[key])
    t0 = time.perf_counter()
    x, _ = _sample(K.BURSTS["SC"], 0.0, K.Q0_POOL_SHOTS, seed)
    np.savez_compressed(arr / f"{stem}.npz", det=np.packbits(x, axis=1))
    curve = {str(3 * n): _sel(x[: 3 * n]) for n in K.CURVE_PER_Q}
    rec = {"burst": "Q0", "pool": k, "mode": mode, "seeds": {key: seed}, "selection_12k": curve[str(K.Q0_POOL_SHOTS)],
           "curve": curve, "no_burst": curve[str(K.Q0_POOL_SHOTS)]["class_index"] is None,
           "seconds": time.perf_counter() - t0}
    out.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    return stem


def _dispatch(job):
    return burst_job(job[1:]) if job[0] == "burst" else q0_job(job[1:])


def run_gate(mode, workers):
    tau = load_tau(mode)
    res, arr = dirs(mode)
    if (res / "pools").exists() and any((res / "pools").iterdir()):
        raise SystemExit("B2 gate outputs exist; the gate runs once")
    (res / "pools").mkdir(parents=True, exist_ok=True)
    arr.mkdir(parents=True, exist_ok=True)
    pools = K.POOLS if mode == "dev" else K.REHEARSAL_POOLS
    jobs = [("burst", mode, b, k) for b in ("M0", "M1", "SC", "CR") for k in range(pools)] + \
           [("q0", mode, k) for k in range(pools)]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers, initializer=_init, initargs=(tau,)) as pool:
        for stem in pool.map(_dispatch, jobs):
            print(stem, round(time.time() - t0, 1), flush=True)
    print("DONE", len(jobs), round(time.time() - t0, 1), "tau", tau)


# ---------------------------------------------------------------- aggregate
def aggregate(mode):
    res, _ = dirs(mode)
    pools = K.POOLS if mode == "dev" else K.REHEARSAL_POOLS
    recs = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((res / "pools").glob("*.json"))}
    expected = [f"{b}_pool{k:02d}" for b in K.BURSTS for k in range(pools)] + [f"Q0_pool{k:02d}" for k in range(pools)]
    if sorted(recs) != sorted(expected):
        raise SystemExit("pool records incomplete or unexpected")
    table = seed_table(mode)
    for stem, r in recs.items():
        if any(table[k] != v for k, v in r["seeds"].items()):
            raise SystemExit(f"seed mismatch in {stem}")
    tau = load_tau(mode)
    out = {"schema": "qshift-d5-learned-support-gate-b2-v1", "mode": mode, "tau": tau, "pools_per_burst": pools,
           "bursts": {}}
    g1 = g3 = True
    for b in K.BURSTS:
        rs = [recs[f"{b}_pool{k:02d}"] for k in range(pools)]
        cls_ok, flip_ok = sum(r["class_correct"] for r in rs), sum(r["flip_correct"] for r in rs)
        frac = flip_ok / cls_ok if cls_ok else 0.0
        qerr = [abs(r["selection_12k"]["q_hat"] - 0.01) for r in rs if r["class_correct"]]
        out["bursts"][b] = {
            "true_support": rs[0]["true_support"], "true_class": rs[0]["true_class"], "true_flip": rs[0]["true_flip"],
            "class_correct": cls_ok, "flip_correct": flip_ok, "flip_fraction_of_class_correct": frac,
            "flip_methods": sorted({r["flip"]["method"] for r in rs if r["flip"]}),
            "curve_class_correct": {n: sum(r["curve"][n]["class_index"] == r["true_class"] for r in rs) for n in rs[0]["curve"]},
            "q_hat_mae_vs_pooled_mean_0.01": (sum(qerr) / len(qerr)) if qerr else None,
            "min_delta_12k": min(r["selection_12k"]["delta"] for r in rs),
            "learned_supports": sorted({tuple(r["learned_support"]) for r in rs if r["learned_support"]}),
            "wrong_selections": [{"pool": r["pool"], "selected": r["selection_12k"]["class_index"],
                                  "delta": r["selection_12k"]["delta"]} for r in rs if not r["class_correct"]],
            "mean_seconds": sum(r["seconds"] for r in rs) / len(rs)}
        g1 &= cls_ok >= (K.G1_MIN if mode == "dev" else pools)
        g3 &= frac >= K.G3_MIN_FRACTION
    q0 = [recs[f"Q0_pool{k:02d}"] for k in range(pools)]
    nb = sum(r["no_burst"] for r in q0)
    out["q0"] = {"no_burst": nb,
                 "curve_no_burst": {n: sum(r["curve"][n]["class_index"] is None for r in q0) for n in q0[0]["curve"]},
                 "false_selections": [{"pool": r["pool"], "selected": r["selection_12k"]["class_index"],
                                       "delta": r["selection_12k"]["delta"]} for r in q0 if not r["no_burst"]],
                 "max_delta": max(r["selection_12k"]["delta"] for r in q0)}
    g2 = nb >= (K.G2_MIN if mode == "dev" else pools)
    out["gates"] = {"G1_class": g1, "G2_q0_no_burst": g2, "G3_flip": g3,
                    "rule": f"G1: each burst >= {K.G1_MIN}/{K.POOLS}; G2: >= {K.G2_MIN}/{K.POOLS}; G3: >= {K.G3_MIN_FRACTION}"}
    out["decision"] = "PASS" if (g1 and g2 and g3) else "STOP"
    return out


if __name__ == "__main__":
    cmd = sys.argv[1]
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 8
    if cmd == "seeds":
        make_seeds()
    elif cmd == "null":
        run_null(sys.argv[2], workers)
    elif cmd == "gate":
        run_gate(sys.argv[2], workers)
    elif cmd == "aggregate":
        target = Path(sys.argv[3])
        if target.exists():
            raise SystemExit(f"{target} exists")
        rec = aggregate(sys.argv[2])
        target.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({"decision": rec["decision"], "gates": rec["gates"], "tau": rec["tau"],
                          "class_correct": {b: v["class_correct"] for b, v in rec["bursts"].items()},
                          "q0_no_burst": rec["q0"]["no_burst"]}, indent=2))
    else:
        raise SystemExit(__doc__)
