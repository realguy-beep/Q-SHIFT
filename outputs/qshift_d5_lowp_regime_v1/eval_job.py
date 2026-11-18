"""One Stage E root job: sample (or fake-sample) one (condition, q, root) and decode it with every arm.

Usage: eval_job.py <mode: eval|rehearsal|fake> <cond> <qi> <root> <run_dir> [--expected-head SHA]
Writes <run_dir>/archives/<stem>.npz and <run_dir>/roots/<stem>.json once. In eval mode verifies HEAD and
every EVAL_FREEZE.json file hash before sampling.
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
import contract as D  # noqa: E402
import eval_contract as K  # noqa: E402
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m  # noqa: E402
from outputs.qshift_scalable_decoder_dev_v3.bposd import dem_to_matrix  # noqa: E402
from outputs.qshift_scalable_decoder_dev_v3_2.ldpc_bposd import LdpcBPOSD  # noqa: E402


def verify_freeze(expected_head: str) -> None:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    if head != expected_head:
        raise SystemExit(f"HEAD {head} != expected {expected_head}")
    freeze = json.loads((ROOT / "EVAL_FREEZE.json").read_text(encoding="utf-8"))
    for rel, digest in freeze["files"].items():
        if hashlib.sha256((REPO / rel).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"frozen file changed: {rel}")


def hyper_dem(spec, q_dec, qubits):
    return m.build_candidate_circuit(spec, q_dec, qubits).detector_error_model(
        decompose_errors=False, approximate_disjoint_errors=True)


def fake_sample(spec, q, qubits, n, seed):
    """Pipeline-test sampler: independent Bernoulli faults on merged DEM columns (no stim sampler call)."""
    dm = dem_to_matrix(hyper_dem(spec, q, qubits), merge=True)
    rng = np.random.default_rng(seed)
    e = (rng.random((n, dm.H.shape[1])) < dm.p).astype(np.int64)
    det = ((e @ dm.H.T.astype(np.int64)) % 2 ^ dm.offset_detectors).astype(np.uint8)
    y = ((e @ dm.L.astype(np.int64)) % 2 ^ dm.offset_logical).astype(np.uint8)
    return det, y


def decode_all(cond, q, det):
    spec, qubits = D.spec(cond)
    sel = K.SELECTION[cond]
    out = {}
    for name, qd, corr in (("Astar", sel["astar_q_dec"], sel["astar_correlations"]), ("A_nominal", 0.0, False)):
        mt = m.build_matching(m.build_decomposed_dem(m.build_candidate_circuit(spec, qd, qubits)))
        t = time.perf_counter()
        out[name] = (np.asarray(mt.decode_batch(det, enable_correlations=corr)).reshape(-1).astype(np.uint8),
                     time.perf_counter() - t)
    for name, qd in (("L2s", sel["l2_prior"]), ("L2o", q)):
        dec = LdpcBPOSD(hyper_dem(spec, qd, qubits), K.L2)
        t = time.perf_counter()
        out[name] = (np.asarray(dec.decode_batch(det)[:, 0], dtype=np.uint8), time.perf_counter() - t)
    return out


def run(mode: str, cond: str, qi: int, r: int, run_dir: Path) -> dict:
    alloc = K.MODES[mode]
    if cond not in K.CONDITIONS or not (0 <= qi < len(K.QS) and 0 <= r < alloc.roots_per_q):
        raise SystemExit("job index out of range for mode")
    seeds = json.loads((ROOT / "EVAL_SEEDS.json").read_text(encoding="utf-8"))
    key = K.root_key(cond, qi, r)
    if mode == "eval":
        seed = int(seeds["seeds"][key])
    elif mode == "rehearsal":
        seed = int(seeds["rehearsal_seeds"][key])
    else:
        seed = int(seeds["rehearsal_seeds"]["d5lowp:fake"]) * 1000 + K.CONDITIONS.index(cond) * 300 + qi * 100 + r
    s = K.stem(cond, qi, r)
    js_path, npz_path = run_dir / "roots" / f"{s}.json", run_dir / "archives" / f"{s}.npz"
    if js_path.exists() or npz_path.exists():
        raise SystemExit(f"{s} already recorded; refusing to rerun")
    js_path.parent.mkdir(parents=True, exist_ok=True)
    npz_path.parent.mkdir(parents=True, exist_ok=True)
    q, n = K.QS[qi], alloc.shots(cond)
    spec, qubits = D.spec(cond)
    t = time.perf_counter()
    if mode == "fake":
        det, y = fake_sample(spec, q, qubits, n, seed)
    else:
        d, o = m.build_candidate_circuit(spec, q, qubits).compile_detector_sampler(seed=seed).sample(
            shots=n, separate_observables=True)
        det, y = np.asarray(d, dtype=np.uint8), np.asarray(o, dtype=np.uint8)[:, 0]
    sample_s = time.perf_counter() - t
    res = decode_all(cond, q, det)
    np.savez_compressed(npz_path, detectors=np.packbits(det, axis=1), observables=y,
                        **{f"pred_{a}": np.packbits(res[a][0]) for a in K.ARMS})
    rec = {"mode": mode, "cond": cond, "qi": qi, "q": q, "root": r, "key": key, "seed": seed, "shots": n,
           "num_detectors": int(det.shape[1]), "sampling_seconds": sample_s,
           "errors": {a: int((res[a][0] != y).sum()) for a in K.ARMS},
           "ms_per_shot": {a: 1000 * res[a][1] / n for a in K.ARMS},
           "archive": f"archives/{s}.npz", "archive_sha256": hashlib.sha256(npz_path.read_bytes()).hexdigest()}
    js_path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    return rec


def main() -> None:
    mode, cond, qi, r, run_dir = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), Path(sys.argv[5])
    if mode not in K.MODES:
        raise SystemExit("unknown mode")
    if mode == "eval":
        if "--expected-head" not in sys.argv:
            raise SystemExit("eval mode requires --expected-head")
        verify_freeze(sys.argv[sys.argv.index("--expected-head") + 1])
    rec = run(mode, cond, qi, r, run_dir)
    print(json.dumps({k: rec[k] for k in ("key", "shots", "errors")}), flush=True)


if __name__ == "__main__":
    main()
