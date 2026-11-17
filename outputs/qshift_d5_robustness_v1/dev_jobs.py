"""Step D jobs (DEV_PROTOCOL.md).

  dev_jobs.py sample <cond> <qi> [--rehearse]        sample, save shots, decode the static matching grid
  dev_jobs.py l2 <cond> <qi> <prior> [--rehearse]    decode saved shots with L2 at a static prior
Each output is written once; reruns are refused.
"""
from __future__ import annotations

import json
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
from outputs.qshift_scalable_decoder_dev_v3_2.ldpc_bposd import LdpcBPOSD  # noqa: E402


def paths(rehearse: bool):
    tag = "dev_rehearsal" if rehearse else "dev"
    work, res = ROOT / "work" / tag, ROOT / ("work" if rehearse else "results") / f"{tag}_json"
    work.mkdir(parents=True, exist_ok=True)
    res.mkdir(parents=True, exist_ok=True)
    return work, res


def sample(cond: str, qi: int, rehearse: bool) -> dict:
    work, res = paths(rehearse)
    stem = f"{cond}_q{qi}"
    if (res / f"{stem}_match.json").exists() or (work / f"{stem}_shots.npz").exists():
        raise SystemExit(f"{stem} already sampled; refusing to rerun")
    seeds = json.loads((ROOT / "DEV_SEEDS.json").read_text(encoding="utf-8"))
    seed = int((seeds["rehearsal_seeds"] if rehearse else seeds["seeds"])[K.dev_key(cond, qi)])
    n = K.DEV_REHEARSAL_SHOTS if rehearse else K.DEV_SHOTS
    spec, qubits = K.spec(cond)
    q = K.QS[qi]
    d, o = m.build_candidate_circuit(spec, q, qubits).compile_detector_sampler(seed=seed).sample(
        shots=n, separate_observables=True)
    det, y = np.asarray(d, dtype=np.uint8), np.asarray(o, dtype=np.uint8)[:, 0]
    np.savez_compressed(work / f"{stem}_shots.npz", detectors=np.packbits(det, axis=1), observables=y,
                        num_detectors=det.shape[1])
    errs, bits = {}, {}
    for qd in K.Q_DEC_MATCH:
        mt = m.build_matching(m.build_decomposed_dem(m.build_candidate_circuit(spec, qd, qubits)))
        for corr in (True, False):
            err = np.asarray(mt.decode_batch(det, enable_correlations=corr)).reshape(-1).astype(np.uint8) != y
            name = f"match_{'on' if corr else 'off'}_{qd}"
            errs[name] = int(err.sum())
            bits[name] = np.packbits(err)
    np.savez_compressed(work / f"{stem}_match_errbits.npz", **bits)
    rec = {"cond": cond, "qi": qi, "q": q, "seed": seed, "shots": n, "rehearsal": rehearse, "matching_errors": errs}
    (res / f"{stem}_match.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    return rec


def l2(cond: str, qi: int, prior: float, rehearse: bool) -> dict:
    if prior not in K.L2_PRIORS:
        raise SystemExit("prior not in the pre-registered grid")
    work, res = paths(rehearse)
    stem = f"{cond}_q{qi}"
    out = res / f"{stem}_l2_{prior:.4f}.json"
    if out.exists():
        raise SystemExit(f"{out.name} exists; refusing to rerun")
    with np.load(work / f"{stem}_shots.npz") as z:
        det = np.unpackbits(z["detectors"], axis=1)[:, : int(z["num_detectors"])]
        y = z["observables"]
    spec, qubits = K.spec(cond)
    dem = m.build_candidate_circuit(spec, prior, qubits).detector_error_model(
        decompose_errors=False, approximate_disjoint_errors=True)
    dec = LdpcBPOSD(dem, K.L2)
    t = time.perf_counter()
    err = np.asarray(dec.decode_batch(det)[:, 0], dtype=np.uint8) != y
    sec = time.perf_counter() - t
    np.savez_compressed(work / f"{stem}_l2_{prior:.4f}_errbits.npz", err=np.packbits(err))
    rec = {"cond": cond, "qi": qi, "prior": prior, "shots": len(y), "errors": int(err.sum()),
           "ms_per_shot": 1000 * sec / len(y), "rehearsal": rehearse}
    out.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8", newline="\n")
    return rec


if __name__ == "__main__":
    rh = "--rehearse" in sys.argv
    if sys.argv[1] == "sample":
        r = sample(sys.argv[2], int(sys.argv[3]), rh)
        print(json.dumps({"cond": r["cond"], "qi": r["qi"], "shots": r["shots"]}))
    elif sys.argv[1] == "l2":
        print(json.dumps(l2(sys.argv[2], int(sys.argv[3]), float(sys.argv[4]), rh)))
    else:
        raise SystemExit("unknown job")
