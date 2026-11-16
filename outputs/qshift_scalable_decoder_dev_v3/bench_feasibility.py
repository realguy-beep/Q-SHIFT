"""Pre-registered V3 feasibility benchmark: runtime and peak traced memory at d=3/5/7.

No sampler and no random generator. For each distance, 200 deterministic syndromes are
formed by XOR-ing the columns of fixed mechanism-index patterns (1-6 faults, plus one burst
event on every fourth syndrome) of the known-burst-family DEM at q=0.01. Measures
construction time, per-shot decode time (median, p95, max) for variant 'min', the share of
shots needing OSD, and peak tracemalloc memory during decoding. Writes FEASIBILITY.json once.
"""
from __future__ import annotations

import json
import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m  # noqa: E402
from outputs.qshift_scalable_decoder_dev_v3.bposd import BPOSD  # noqa: E402

OUT = ROOT / "FEASIBILITY.json"
SHOTS = 200


def syndromes(dec: BPOSD, events) -> np.ndarray:
    H = dec.dm.H.astype(np.int64)
    n = H.shape[1]
    rows = []
    for k in range(SHOTS):
        count = 1 + k % 6
        cols = {(k * a + b) % n for a, b in ((7, 1), (13, 5), (29, 11), (31, 3), (37, 17), (41, 23))[:count]}
        s = (H[:, sorted(cols)].sum(axis=1) % 2).astype(np.uint8)
        if k % 4 == 0:
            s[list(events[k // 4 % len(events)].detector_ids)] ^= 1
        rows.append(s)
    return np.vstack(rows)


def main() -> None:
    if OUT.exists():
        raise SystemExit("FEASIBILITY.json exists; runs once")
    results = []
    for d in (3, 5, 7):
        spec = m.CodeSpec(distance=d)
        qubits = m.burst_qubits(spec, "scaled_v1")
        dem = m.build_candidate_circuit(spec, 0.01, qubits).detector_error_model(
            decompose_errors=False, approximate_disjoint_errors=True)
        t = time.perf_counter()
        dec = BPOSD(dem)
        build = time.perf_counter() - t
        x = syndromes(dec, m.extract_burst_events(spec, qubits))
        tracemalloc.start()
        per, osd = [], 0
        for row in x:
            t = time.perf_counter()
            out = dec.decode_one(row)
            per.append(time.perf_counter() - t)
            osd += out["used_osd"]
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        per = np.asarray(per)
        results.append({"distance": d, "detectors": int(dem.num_detectors), "columns": int(dec.dm.H.shape[1]),
                        "edges": int(dec.dm.H.sum()), "construction_seconds": build,
                        "median_ms_per_shot": 1000 * float(np.median(per)), "p95_ms_per_shot": 1000 * float(np.quantile(per, 0.95)),
                        "max_ms_per_shot": 1000 * float(per.max()), "osd_fraction": osd / SHOTS,
                        "peak_traced_memory_mib": peak / 2**20})
        print(results[-1], flush=True)
    OUT.write_text(json.dumps({"schema": "qshift-scalable-v3-feasibility-v1", "shots_per_distance": SHOTS,
                               "variant": "min", "results": results,
                               "note": "deterministic synthetic syndromes; timing and tracemalloc peak only; no accuracy claim; single process"},
                              indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
