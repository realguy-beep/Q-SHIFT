"""One Phase 2 root job: sample (or fake-sample) one root at one q and decode it with every arm.

Usage: eval_job.py <mode: eval|rehearsal|fake> <qi> <root> <run_dir> [--expected-head SHA]
Writes <run_dir>/archives/<stem>.npz (packed detectors, observables, packed per-arm predictions) and
<run_dir>/roots/<stem>.json (counts, timings, seed, archive hash). Refuses to overwrite. In eval mode it
verifies HEAD == --expected-head and every FREEZE.json file hash before sampling.
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
import contract as K  # noqa: E402
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m  # noqa: E402
from outputs.qshift_scalable_decoder_dev_v3.bposd import dem_to_matrix  # noqa: E402
from outputs.qshift_scalable_decoder_dev_v3_2.ldpc_bposd import LdpcBPOSD  # noqa: E402


def verify_freeze(expected_head: str) -> None:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    if head != expected_head:
        raise SystemExit(f"HEAD {head} != expected {expected_head}")
    freeze = json.loads((ROOT / "FREEZE.json").read_text(encoding="utf-8"))
    for rel, digest in freeze["files"].items():
        if hashlib.sha256((REPO / rel).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"frozen file changed: {rel}")


def dem_at(spec, q_dec, qubits):
    return m.build_candidate_circuit(spec, q_dec, qubits).detector_error_model(
        decompose_errors=False, approximate_disjoint_errors=True)


def fake_sample(spec, q, qubits, n, seed):
    """Pipeline-test sampler: independent Bernoulli faults on the merged DEM columns (no stim sampler call)."""
    dm = dem_to_matrix(dem_at(spec, q, qubits), merge=True)
    rng = np.random.default_rng(seed)
    e = (rng.random((n, dm.H.shape[1])) < dm.p).astype(np.int64)
    det = ((e @ dm.H.T.astype(np.int64)) % 2 ^ dm.offset_detectors).astype(np.uint8)
    y = ((e @ dm.L.astype(np.int64)) % 2 ^ dm.offset_logical).astype(np.uint8)
    return det, y


def decode_all(spec, q, qubits, det):
    """Return {arm: (pred uint8 [n], seconds)} for every frozen arm."""
    out = {}
    for name, qd, corr in (("Astar", K.ASTAR_Q_DEC, True), ("A_nominal", 0.0, False)):
        mt = m.build_matching(m.build_decomposed_dem(m.build_candidate_circuit(spec, qd, qubits)))
        t = time.perf_counter()
        pred = np.asarray(mt.decode_batch(det, enable_correlations=corr)).reshape(-1).astype(np.uint8)
        out[name] = (pred, time.perf_counter() - t)
    for name, qd, cfg in (("L2s", K.STATIC_Q_DEC, K.L2), ("L2o", q, K.L2), ("L0s", K.STATIC_Q_DEC, K.L0)):
        dec = LdpcBPOSD(dem_at(spec, qd, qubits), cfg)
        t = time.perf_counter()
        out[name] = (np.asarray(dec.decode_batch(det)[:, 0], dtype=np.uint8), time.perf_counter() - t)
    base = m.build_matching(m.build_decomposed_dem(m.build_base_circuit(spec)))
    ff = m.FiveFactorDecoder(base, m.extract_burst_events(spec, qubits), spec.detectors, correlations=False)
    t = time.perf_counter()
    out["BoffStatic"] = (ff.decode_rows(det, {"p": K.BOFF_PRIOR})["p"][:, 0].astype(np.uint8), time.perf_counter() - t)
    return out


def run(mode: str, qi: int, r: int, run_dir: Path) -> dict:
    alloc = K.MODES[mode]
    if not (0 <= qi < len(K.QS) and 0 <= r < alloc.roots_per_q):
        raise SystemExit("root index out of range for mode")
    seeds = json.loads((ROOT / "SEEDS.json").read_text(encoding="utf-8"))
    key = K.root_key(qi, r)
    if mode == "eval":
        seed = int(seeds["seeds"][key])
    elif mode == "rehearsal":
        seed = int(seeds["rehearsal_seeds"][key])
    else:
        seed = int(seeds["rehearsal_seeds"]["p2d5:fake"]) * 1000 + qi * 100 + r
    s = K.stem(qi, r)
    js_path, npz_path = run_dir / "roots" / f"{s}.json", run_dir / "archives" / f"{s}.npz"
    if js_path.exists() or npz_path.exists():
        raise SystemExit(f"{s} already recorded; refusing to rerun")
    js_path.parent.mkdir(parents=True, exist_ok=True)
    npz_path.parent.mkdir(parents=True, exist_ok=True)
    q, n = K.QS[qi], alloc.shots_per_root
    spec = m.CodeSpec(distance=K.DISTANCE)
    qubits = m.burst_qubits(spec, K.BURST_FAMILY)
    t = time.perf_counter()
    if mode == "fake":
        det, y = fake_sample(spec, q, qubits, n, seed)
    else:
        d, o = m.build_candidate_circuit(spec, q, qubits).compile_detector_sampler(seed=seed).sample(
            shots=n, separate_observables=True)
        det, y = np.asarray(d, dtype=np.uint8), np.asarray(o, dtype=np.uint8)[:, 0]
    sample_s = time.perf_counter() - t
    res = decode_all(spec, q, qubits, det)
    arrays = {"detectors": np.packbits(det, axis=1), "observables": y,
              **{f"pred_{a}": np.packbits(res[a][0]) for a in K.ARMS}}
    np.savez_compressed(npz_path, **arrays)
    rec = {"mode": mode, "qi": qi, "q": q, "root": r, "key": key, "seed": seed, "shots": n,
           "num_detectors": int(det.shape[1]), "sampling_seconds": sample_s,
           "errors": {a: int((res[a][0] != y).sum()) for a in K.ARMS},
           "ms_per_shot": {a: 1000 * res[a][1] / n for a in K.ARMS},
           "archive": f"archives/{s}.npz", "archive_sha256": hashlib.sha256(npz_path.read_bytes()).hexdigest()}
    js_path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    return rec


def main() -> None:
    mode, qi, r, run_dir = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), Path(sys.argv[4])
    if mode not in K.MODES:
        raise SystemExit("unknown mode")
    if mode == "eval":
        if "--expected-head" not in sys.argv:
            raise SystemExit("eval mode requires --expected-head")
        verify_freeze(sys.argv[sys.argv.index("--expected-head") + 1])
    rec = run(mode, qi, r, run_dir)
    print(json.dumps({k: rec[k] for k in ("key", "shots", "errors")}), flush=True)


if __name__ == "__main__":
    main()
