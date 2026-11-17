"""Phase A development diagnostic (PROTOCOL.md). Informational: the method is fixed and nothing is tuned.

  diag.py run [--workers 8]     sample every diagnostic pool / decode root once (needs committed SEEDS.json)
  diag.py aggregate             DIAG.json (+ printed summary) from the pool records

Per condition: 24 burst pools (calibration recipe; class/flip accuracy), 24 burst-free pools of 12,000 rows
(false-accept rate; residual size), and 3 decode roots x 2,000 shots per q on every arm. Decode roots use the
learned support of that condition's burst pool 00 (declared before sampling), base DEM if none.
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
sys.path.insert(0, str(ROOT))
import mm_contract as K  # noqa: E402
import job as J  # noqa: E402

RES = ROOT / "results" / "diag"
ARR = ROOT / "work" / "diag_arrays"
_S = {}


def seeds():
    return json.loads((ROOT / "SEEDS.json").read_text(encoding="utf-8"))["diag_seeds"]


def _init():
    _S["classes"], _S["learner"] = J.nominal_learner()
    _S["seeds"] = seeds()


def _write_once(name, rec):
    out = RES / "pools" / f"{name}.json"
    if out.exists():
        raise SystemExit(f"{name} exists")
    out.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    return name


def burst_pool(c, k):
    t0 = time.perf_counter()
    spec, dets, labx, laby, used = K.TRUE_SPECS[c], [], [], [], {}
    for qi, q in enumerate(K.QS):
        key = K.diag_burst_key(c, k, qi)
        used[key] = int(_S["seeds"][key])
        x, y = J.sample(spec, q, K.SUPPORT, K.DET_PER_Q + K.LAB_PER_Q, used[key])
        dets.append(x[: K.DET_PER_Q])            # labels of these rows are discarded unread
        labx.append(x[K.DET_PER_Q:])
        laby.append(y[K.DET_PER_Q:])
    np.savez_compressed(ARR / f"{c}_burst{k:02d}.npz", **{f"det_q{i}": np.packbits(d, axis=1) for i, d in enumerate(dets)},
                        **{f"labx_q{i}": np.packbits(d, axis=1) for i, d in enumerate(labx)},
                        **{f"laby_q{i}": y for i, y in enumerate(laby)})
    rec = {"cond": c, "kind": "burst", "pool": k, "seeds": used,
           **J.learn(_S["classes"], _S["learner"], dets, labx, laby), "seconds": time.perf_counter() - t0}
    return _write_once(f"{c}_burst{k:02d}", rec)


def q0_pool(c, k):
    t0 = time.perf_counter()
    key = K.diag_q0_key(c, k)
    seed = int(_S["seeds"][key])
    x, _ = J.sample(K.TRUE_SPECS[c], 0.0, K.SUPPORT, K.Q0_POOL_SHOTS, seed)   # q=0: burst-free; labels unread
    np.savez_compressed(ARR / f"{c}_q0{k:02d}.npz", det=np.packbits(x, axis=1))
    sel = _S["learner"].select(x)
    rec = {"cond": c, "kind": "q0", "pool": k, "seeds": {key: seed},
           "selection": {"class_index": sel["class_index"], "q_hat": sel["q_hat"], "delta": sel["delta"]},
           "no_burst": sel["class_index"] is None, "residuals": J.residual_summary(_S["learner"], x),
           "seconds": time.perf_counter() - t0}
    return _write_once(f"{c}_q0{k:02d}", rec)


def decode_root(c, qi, r):
    pool0 = json.loads((RES / "pools" / f"{c}_burst00.json").read_text(encoding="utf-8"))
    learned = tuple(pool0["learned_support"]) if pool0["learned_support"] is not None else None
    key = K.diag_decode_key(c, qi, r)
    seed = int(_S["seeds"][key])
    x, y = J.sample(K.TRUE_SPECS[c], K.QS[qi], K.SUPPORT, K.DIAG_DECODE_SHOTS, seed)
    res = J.decode_all(K.QS[qi], x, K.SUPPORT, learned)
    rec = {"cond": c, "kind": "decode", "q": K.QS[qi], "root": r, "seeds": {key: seed}, "shots": len(y),
           "learned_support_used": list(learned) if learned else None,
           "errors": {a: int((res[a][0] != y).sum()) for a in K.ARMS},
           "seconds": {a: round(res[a][1], 2) for a in K.ARMS}}
    return _write_once(f"{c}_decode_q{qi}_r{r}", rec)


def _dispatch(job):
    return {"burst": burst_pool, "q0": q0_pool, "decode": decode_root}[job[0]](*job[1:])


def require_committed_seeds():
    rel = "outputs/qshift_d5_model_mismatch_v1/SEEDS.json"
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=K.REPO, capture_output=True).returncode == 0
    clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=K.REPO).returncode == 0
    if not (tracked and clean):
        raise SystemExit("SEEDS.json must be committed and unchanged before the diagnostic")


def run(workers):
    require_committed_seeds()
    if RES.exists():
        raise SystemExit("results/diag exists; the diagnostic runs once")
    (RES / "pools").mkdir(parents=True)
    ARR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    stage1 = [("burst", c, k) for c in K.CONDITIONS for k in range(K.DIAG_POOLS)] + \
             [("q0", c, k) for c in K.CONDITIONS for k in range(K.DIAG_POOLS)]
    stage2 = [("decode", c, qi, r) for c in K.CONDITIONS for qi in range(len(K.QS)) for r in range(K.DIAG_DECODE_ROOTS)]
    with ProcessPoolExecutor(max_workers=workers, initializer=_init) as pool:
        for stage in (stage1, stage2):
            for name in pool.map(_dispatch, stage):
                print(name, flush=True)
    print("seconds", round(time.time() - t0, 1))


def aggregate():
    recs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((RES / "pools").glob("*.json"))]
    out = {"schema": "qshift-d5-model-mismatch-diag-v1", "tau": K.tau(), "true_specs": {c: repr(s) for c, s in K.TRUE_SPECS.items()},
           "nominal_spec": repr(K.NOMINAL_SPEC), "support": list(K.SUPPORT), "conditions": {}}
    for c in K.CONDITIONS:
        b = [r for r in recs if r["cond"] == c and r["kind"] == "burst"]
        z = [r for r in recs if r["cond"] == c and r["kind"] == "q0"]
        d = [r for r in recs if r["cond"] == c and r["kind"] == "decode"]
        if len(b) != K.DIAG_POOLS or len(z) != K.DIAG_POOLS or len(d) != len(K.QS) * K.DIAG_DECODE_ROOTS:
            raise SystemExit(f"incomplete diagnostic for {c}")
        wrong = sorted({r["selection"]["class_index"] for r in b if not r["class_correct"]} - {None})
        false_cls = sorted({r["selection"]["class_index"] for r in z if not r["no_burst"]})
        out["conditions"][c] = {
            "burst_pools": {"class_correct": sum(r["class_correct"] for r in b), "learned_correct": sum(r["learned_correct"] for r in b),
                            "none_accepted": sum(r["selection"]["class_index"] is None for r in b), "wrong_classes": wrong,
                            "delta_min": min(r["selection"]["delta"] for r in b),
                            "q_hat_mean": float(np.mean([r["selection"]["q_hat"] for r in b]))},
            "q0_pools": {"no_burst": sum(r["no_burst"] for r in z), "false_accept_classes": false_cls,
                         "T_max": max(r["selection"]["delta"] for r in z),
                         "T_median": float(np.median([r["selection"]["delta"] for r in z])),
                         "mean_y": float(np.mean([r["residuals"]["mean_y"] for r in z])),
                         "mean_z": float(np.mean([r["residuals"]["mean_z"] for r in z]))},
            "decode": {"learned_support_used": d[0]["learned_support_used"],
                       "errors_by_q": {str(q): {a: sum(r["errors"][a] for r in d if r["q"] == q) for a in K.ARMS} for q in K.QS},
                       "shots_per_q": K.DIAG_DECODE_ROOTS * K.DIAG_DECODE_SHOTS,
                       "seconds_per_shot": {a: sum(r["seconds"][a] for r in d) / (len(d) * K.DIAG_DECODE_SHOTS) for a in K.ARMS}},
        }
    (ROOT / "DIAG.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(out["conditions"], indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run(int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 8)
    elif sys.argv[1] == "aggregate":
        aggregate()
    else:
        raise SystemExit(__doc__)
