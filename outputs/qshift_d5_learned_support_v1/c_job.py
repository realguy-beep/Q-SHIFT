"""Phase C jobs (PHASE_C_PROTOCOL.md).

  c_job.py calibrate <mode> <cond> <run_dir> [--expected-head SHA] [--open-hidden-seal]
  c_job.py root <mode> <cond> <qi> <r> <run_dir> [--expected-head SHA] [--open-hidden-seal]
Each output is written once. Eval mode verifies HEAD and every C_FREEZE.json hash first.
Fake and rehearsal modes never open the hidden seal (H uses SURROGATE_H).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO))
import c_contract as C  # noqa: E402
import contract as B  # noqa: E402
import learner_d5 as LD  # noqa: E402
from learner_d5 import L, m  # noqa: E402
from outputs.qshift_scalable_decoder_dev_v3.bposd import dem_to_matrix  # noqa: E402
from outputs.qshift_scalable_decoder_dev_v3_2.ldpc_bposd import LdpcBPOSD  # noqa: E402


def verify_freeze(expected_head: str) -> None:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    if head != expected_head:
        raise SystemExit(f"HEAD {head} != expected {expected_head}")
    freeze = json.loads((ROOT / "C_FREEZE.json").read_text(encoding="utf-8"))
    for rel, digest in freeze["files"].items():
        if hashlib.sha256((REPO / rel).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"frozen file changed: {rel}")


def seeds(mode):
    s = json.loads((ROOT / "C_SEEDS.json").read_text(encoding="utf-8"))
    return s["seeds"] if mode == "eval" else s["rehearsal_seeds"]


def circuit(q, qubits):
    return m.build_candidate_circuit(C.SPEC, q, qubits) if qubits is not None else m.build_base_circuit(C.SPEC)


def hyper_dem(q, qubits):
    return circuit(q, qubits).detector_error_model(decompose_errors=False, approximate_disjoint_errors=True)


def sample(mode, q, qubits, n, seed):
    if mode == "fake":
        dm = dem_to_matrix(hyper_dem(q, qubits), merge=True)
        rng = np.random.default_rng(seed)
        e = (rng.random((n, dm.H.shape[1])) < dm.p).astype(np.int64)
        det = ((e @ dm.H.T.astype(np.int64)) % 2 ^ dm.offset_detectors).astype(np.uint8)
        y = ((e @ dm.L.astype(np.int64)) % 2 ^ dm.offset_logical).astype(np.uint8)
        return det, y
    d, o = circuit(q, qubits).compile_detector_sampler(seed=seed).sample(shots=n, separate_observables=True)
    return np.asarray(d, np.uint8), np.asarray(o, np.uint8)[:, 0]


def fake_seed(mode, key):
    base = int(seeds(mode)["d5ls:C:fake"])
    return base * 1000 + int(hashlib.sha256(key.encode()).hexdigest()[:6], 16) % 1000


def seed_for(mode, key):
    return fake_seed(mode, key) if mode == "fake" else int(seeds(mode)[key])


# ------------------------------------------------------------------ calibration (learning)
def calibrate(mode, cond, run_dir: Path, hidden_ok: bool) -> dict:
    out = run_dir / "learned" / f"{cond}.json"
    if out.exists():
        raise SystemExit(f"{out} exists; calibration runs once")
    out.parent.mkdir(parents=True, exist_ok=True)
    truth = C.true_support(cond, mode, hidden_ok)
    classes = B.load_classes()
    learner = LD.FastParityLearner(classes, L.base_dem(C.SPEC), C.tau())
    dets, labx, laby, used = [], [], [], {}
    for qi, q in enumerate(C.QS):
        key = C.cal_key(cond, qi)
        used[key] = seed_for(mode, key)
        x, y = sample(mode, q, truth, C.CAL_DET_PER_Q + C.CAL_LAB_PER_Q, used[key])
        dets.append(x[: C.CAL_DET_PER_Q])            # labels of these rows are discarded unread
        labx.append(x[C.CAL_DET_PER_Q:])
        laby.append(y[C.CAL_DET_PER_Q:])
    sel = learner.select(np.vstack(dets))
    flip = learned = None
    if sel["class_index"] is not None:
        flip = LD.learn_flip(C.SPEC, classes[sel["class_index"]], np.vstack(labx), np.concatenate(laby))
        learned = list(classes[sel["class_index"]].representative(flip["flip"]))
    t_idx, t_flip = B.truth(classes, truth)
    rec = {"mode": mode, "cond": cond, "seeds": used, "tau": C.tau(), "selection": sel_summary(sel), "flip": flip,
           "learned_support": learned,
           "learned_correct": bool(sel["class_index"] == t_idx and flip is not None and flip["flip"] == t_flip),
           "surrogate_used_for_H": cond == "H" and mode != "eval"}
    out.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    return rec


def sel_summary(sel):
    return {"class_index": sel["class_index"], "q_hat": sel["q_hat"], "delta": sel["delta"]}


def learned_support(run_dir: Path, cond: str):
    rec = json.loads((run_dir / "learned" / f"{cond}.json").read_text(encoding="utf-8"))
    return tuple(rec["learned_support"]) if rec["learned_support"] is not None else None


# ------------------------------------------------------------------ evaluation roots
def decode_all(q, det, truth, learned):
    out = {}
    for name, qd, sup, corr in (("Astar", C.ASTAR_Q_DEC, truth, C.ASTAR_CORRELATIONS),
                                ("Astar_L", C.ASTAR_Q_DEC, learned, C.ASTAR_CORRELATIONS),
                                ("A_nominal", 0.0, None, False)):
        mt = m.build_matching(m.build_decomposed_dem(circuit(qd, sup)))
        t = time.perf_counter()
        out[name] = (np.asarray(mt.decode_batch(det, enable_correlations=corr)).reshape(-1).astype(np.uint8),
                     time.perf_counter() - t)
    for name, sup in (("L2L", learned), ("L2s", truth)):
        dec = LdpcBPOSD(hyper_dem(C.L2_PRIOR, sup), C.L2)
        t = time.perf_counter()
        out[name] = (np.asarray(dec.decode_batch(det)[:, 0], dtype=np.uint8), time.perf_counter() - t)
    return out


def root(mode, cond, qi, r, run_dir: Path, hidden_ok: bool) -> dict:
    alloc = C.MODES[mode]
    if cond not in C.CONDITIONS or not (0 <= qi < len(C.QS) and 0 <= r < alloc.roots_per_q):
        raise SystemExit("job index out of range for mode")
    s = C.stem(cond, qi, r)
    js_path, npz_path = run_dir / "roots" / f"{s}.json", run_dir / "archives" / f"{s}.npz"
    if js_path.exists() or npz_path.exists():
        raise SystemExit(f"{s} already recorded; refusing to rerun")
    js_path.parent.mkdir(parents=True, exist_ok=True)
    npz_path.parent.mkdir(parents=True, exist_ok=True)
    truth, learned = C.true_support(cond, mode, hidden_ok), learned_support(run_dir, cond)
    key = C.root_key(cond, qi, r)
    seed = seed_for(mode, key)
    q, n = C.QS[qi], alloc.shots_per_root
    t = time.perf_counter()
    det, y = sample(mode, q, truth, n, seed)
    sample_s = time.perf_counter() - t
    res = decode_all(q, det, truth, learned)
    np.savez_compressed(npz_path, detectors=np.packbits(det, axis=1), observables=y,
                        **{f"pred_{a}": np.packbits(res[a][0]) for a in C.ARMS})
    rec = {"mode": mode, "cond": cond, "qi": qi, "q": q, "root": r, "key": key, "seed": seed, "shots": n,
           "num_detectors": int(det.shape[1]), "sampling_seconds": sample_s,
           "errors": {a: int((res[a][0] != y).sum()) for a in C.ARMS},
           "ms_per_shot": {a: 1000 * res[a][1] / n for a in C.ARMS},
           "archive": f"archives/{s}.npz", "archive_sha256": hashlib.sha256(npz_path.read_bytes()).hexdigest()}
    js_path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    return rec


def main() -> None:
    cmd, mode = sys.argv[1], sys.argv[2]
    if mode not in C.MODES:
        raise SystemExit("unknown mode")
    hidden_ok = "--open-hidden-seal" in sys.argv
    if hidden_ok and mode != "eval":
        raise SystemExit("--open-hidden-seal is only valid in eval mode")
    if mode == "eval":
        if "--expected-head" not in sys.argv:
            raise SystemExit("eval mode requires --expected-head")
        verify_freeze(sys.argv[sys.argv.index("--expected-head") + 1])
    if cmd == "calibrate":
        rec = calibrate(mode, sys.argv[3], Path(sys.argv[4]), hidden_ok)
        print(json.dumps({"cond": rec["cond"], "accepted": rec["learned_support"] is not None}), flush=True)
    elif cmd == "root":
        rec = root(mode, sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), Path(sys.argv[6]), hidden_ok)
        print(json.dumps({k: rec[k] for k in ("key", "shots", "errors")}), flush=True)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
