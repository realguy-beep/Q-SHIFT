"""One screen chunk (d, q, chunk). Pre-registered in SCREEN_PROTOCOL.md.

Samples 25,000 labeled dev shots (1,000 for rehearsal), saves detectors/observables
bit-packed (work/, git-ignored), and decodes with Astar, A_nominal, L0-L3 (ldpc) and N3
(NumPy V3, first 4,000 shots). Saves per-shot error bits and a JSON of counts/timings.
Usage: screen_job.py <d> <q> <chunk> [--rehearse]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m  # noqa: E402
from outputs.qshift_scalable_decoder_dev_v3.bposd import BPOSD  # noqa: E402
from outputs.qshift_scalable_decoder_dev_v3_2.ldpc_bposd import LdpcBPOSD  # noqa: E402

CHUNK_SHOTS, REHEARSAL_SHOTS, N3_SHOTS = 25_000, 1_000, 4_000
ASTAR = {"q_dec": 0.0025, "correlations": True}  # Phase 1 selection (both distances)
CANDIDATES = {
    "L0": {"bp_method": "product_sum", "schedule": "parallel", "max_iter": 50, "osd_method": "OSD_CS", "osd_order": 10},
    "L1": {"bp_method": "minimum_sum", "ms_scaling_factor": 0.625, "schedule": "parallel", "max_iter": 50,
           "osd_method": "OSD_CS", "osd_order": 10},
    "L2": {"bp_method": "product_sum", "schedule": "serial", "max_iter": 50, "osd_method": "OSD_CS", "osd_order": 10},
    "L3": {"bp_method": "minimum_sum", "ms_scaling_factor": 0.625, "schedule": "parallel", "max_iter": 50,
           "osd_method": "OSD_CS", "osd_order": 30},
}


def main() -> None:
    d, q, chunk = int(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3])
    rehearse = "--rehearse" in sys.argv[4:]
    seeds = json.loads((ROOT / "SCREEN_SEEDS.json").read_text(encoding="utf-8"))
    lab = f"screen:d{d}:q{q:.2f}:chunk{chunk}"
    seed = int((seeds["rehearsal_seeds"] if rehearse else seeds["seeds"])[lab])
    tag = "screen_rehearsal" if rehearse else "screen"
    work = ROOT / "work" / tag
    res = ROOT / ("work" if rehearse else "results") / f"{tag}_json"
    work.mkdir(parents=True, exist_ok=True)
    res.mkdir(parents=True, exist_ok=True)
    stem = f"d{d}_q{q:.2f}_c{chunk}"
    if (res / f"{stem}.json").exists():
        raise SystemExit(f"{stem} already recorded; refusing to rerun")
    n = REHEARSAL_SHOTS if rehearse else CHUNK_SHOTS
    spec = m.CodeSpec(distance=d)
    qubits = m.burst_qubits(spec, "scaled_v1")
    circuit = m.build_candidate_circuit(spec, q, qubits)
    det, obs = circuit.compile_detector_sampler(seed=seed).sample(shots=n, separate_observables=True)
    det = np.asarray(det, dtype=np.uint8)
    y = np.asarray(obs, dtype=np.uint8)[:, 0]
    np.savez_compressed(work / f"{stem}_shots.npz", detectors=np.packbits(det, axis=1), observables=np.packbits(y),
                        n=n, num_detectors=det.shape[1])
    out = {"d": d, "q": q, "chunk": chunk, "seed": seed, "shots": n, "rehearsal": rehearse, "errors": {},
           "ms_per_shot": {}}
    bits = {}

    def record(name, pred, seconds, rows=None):
        rows = n if rows is None else rows
        err = np.asarray(pred, dtype=np.uint8).reshape(-1) != y[:rows]
        out["errors"][name] = int(err.sum())
        out["ms_per_shot"][name] = 1000 * seconds / rows
        bits[name] = np.packbits(err)

    for name, (qd, corr) in {"Astar": (ASTAR["q_dec"], ASTAR["correlations"]), "A_nominal": (0.0, False)}.items():
        mt = m.build_matching(m.build_decomposed_dem(m.build_candidate_circuit(spec, qd, qubits)))
        t = time.perf_counter()
        record(name, mt.decode_batch(det, enable_correlations=corr), time.perf_counter() - t)
    dem = circuit.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True)
    for name, cfg in CANDIDATES.items():
        dec = LdpcBPOSD(dem, cfg)
        t = time.perf_counter()
        record(name, dec.decode_batch(det)[:, 0], time.perf_counter() - t)
    k = min(n, N3_SHOTS)
    v3 = BPOSD(dem)
    t = time.perf_counter()
    record("N3", v3.decode_batch(det[:k])[:, 0], time.perf_counter() - t, rows=k)
    out["N3_rows"] = k
    np.savez_compressed(work / f"{stem}_errbits.npz", n=n, **bits)
    (res / f"{stem}.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"stem": stem, "errors": out["errors"], "ms": {k2: round(v, 2) for k2, v in out["ms_per_shot"].items()}}), flush=True)


if __name__ == "__main__":
    main()
