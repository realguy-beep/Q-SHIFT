"""V3.1 pre-registered gates: E1 (72,000 d=3 rows), E2 (600 feasibility syndromes), feasibility.

E1 compares V3.1 predictions with the stored V3 predictions (work files of the V3 d=3
benchmark; detector rows re-read from the hash-checked V1.5 archives). E2 compares
predictions and posterior LLRs with the V3 single-shot implementation. The feasibility
gate re-measures d=3/5/7 runtime and peak traced memory on the same deterministic syndromes.
Writes V3_1_GATES.json once. Usage: verify_and_bench.py <V1.5 package dir>
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1]))
from outputs.qshift_correlated_decoder_feasibility_v1_1.model import build_base_circuit, build_candidate_circuit  # noqa: E402
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m  # noqa: E402
from outputs.qshift_scalable_decoder_dev_v3.bench_feasibility import syndromes  # noqa: E402
from outputs.qshift_scalable_decoder_dev_v3.bposd import BPOSD  # noqa: E402
from outputs.qshift_scalable_decoder_dev_v3_1.bposd_batched import BatchedBPOSD  # noqa: E402

OUT = ROOT / "V3_1_GATES.json"
V3_WORK = ROOT.parent / "qshift_scalable_decoder_dev_v3" / "work" / "d3"
ROWS = 1000


def e1(v15: Path) -> dict:
    records = v15 / "results_v1" / "run_records"
    status = json.loads((records / "status.json").read_text(encoding="utf-8"))
    qhat = json.loads((records / "models_frozen.json").read_text(encoding="utf-8"))["root_qhat"]
    calls = {c["archive"]: c for c in status["sampler_calls_started"] if c["phase"] == "evaluation"}
    mismatches = {"min": 0, "lc": 0}
    rows = 0
    for qi in range(3):
        for r in range(24):
            rel = f"evaluation/eval_q{qi}_r{r:02d}.npz"
            path = v15 / "pilot_runs" / "attempt_001" / rel
            if hashlib.sha256(path.read_bytes()).hexdigest() != calls[rel]["archive_sha256"]:
                raise RuntimeError(f"archive hash mismatch: {rel}")
            with np.load(path, allow_pickle=False) as z:
                x = np.asarray(z["detectors"][:ROWS], dtype=np.uint8)
            with np.load(V3_WORK / f"root_q{qi}_r{r:02d}.npz") as z:
                ref = {"min": z["V3_min"], "lc": z["V3_lc"]}
            q = float(qhat[f"q{qi}_r{r:02d}"])
            circuit = build_base_circuit() if q <= 0 else build_candidate_circuit(q)
            dec = BatchedBPOSD(circuit.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True))
            for variant in ("min", "lc"):
                mismatches[variant] += int(np.count_nonzero(dec.decode_batch(x, variant)[:, 0] != ref[variant]))
            rows += len(x)
    return {"rows": rows, "prediction_mismatches": mismatches, "pass": all(v == 0 for v in mismatches.values())}


def e2_and_feasibility() -> tuple[dict, list]:
    e2 = {"syndromes": 0, "prediction_mismatches": {"min": 0, "lc": 0}, "max_abs_llr_difference": 0.0}
    feas = []
    for d in (3, 5, 7):
        spec = m.CodeSpec(distance=d)
        qubits = m.burst_qubits(spec, "scaled_v1")
        dem = m.build_candidate_circuit(spec, 0.01, qubits).detector_error_model(
            decompose_errors=False, approximate_disjoint_errors=True)
        v3 = BPOSD(dem)
        v31 = BatchedBPOSD(dem)
        x = syndromes(v3, m.extract_burst_events(spec, qubits))
        ref_llr = np.vstack([v3.bp.posterior_llr(row)[0] for row in x])
        llr = v31.bp.posterior_llr(x)[0]
        e2["max_abs_llr_difference"] = max(e2["max_abs_llr_difference"], float(np.max(np.abs(llr - ref_llr))))
        for variant in ("min", "lc"):
            ref = np.asarray([v3.decode_one(row, variant)["prediction"] for row in x])
            e2["prediction_mismatches"][variant] += int(np.count_nonzero(v31.decode_batch(x, variant)[:, 0] != ref))
        e2["syndromes"] += len(x)
        tracemalloc.start()
        t = time.perf_counter()
        _, info = v31.decode_batch(x, "min", timing=True)
        wall = time.perf_counter() - t
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        per = info["per_shot_seconds"]
        feas.append({"distance": d, "batch": len(x), "batch_wall_seconds": wall, "bp_seconds": info["bp_seconds"],
                     "median_ms_per_shot": 1000 * float(np.median(per)), "p95_ms_per_shot": 1000 * float(np.quantile(per, 0.95)),
                     "max_ms_per_shot": 1000 * float(per.max()), "osd_fraction": float(info["used_osd"].mean()),
                     "bp_nonconverged": int((~info["bp"]["converged"]).sum()), "peak_traced_memory_mib": peak / 2**20})
        print(feas[-1], flush=True)
    e2["pass"] = all(v == 0 for v in e2["prediction_mismatches"].values()) and e2["max_abs_llr_difference"] <= 1e-8
    return e2, feas


def main() -> None:
    if OUT.exists():
        raise SystemExit("V3_1_GATES.json exists; runs once")
    e2, feas = e2_and_feasibility()
    print("E2", e2, flush=True)
    r1 = e1(Path(sys.argv[1]).resolve())
    print("E1", r1, flush=True)
    d7 = next(f for f in feas if f["distance"] == 7)
    feas_pass = d7["median_ms_per_shot"] <= 50 and max(f["peak_traced_memory_mib"] for f in feas) <= 1024
    decision = ("GO" if (r1["pass"] and e2["pass"] and feas_pass) else
                "REVISE" if (r1["pass"] and e2["pass"]) else "STOP")
    OUT.write_text(json.dumps({"schema": "qshift-scalable-v3-1-gates-v1", "E1": r1, "E2": e2, "feasibility": feas,
                               "feasibility_pass": feas_pass, "decision": decision,
                               "note": "E3 (unit tests) recorded separately; timing single-process, this machine"},
                              indent=2) + "\n", encoding="utf-8", newline="\n")
    print("DECISION", decision)


if __name__ == "__main__":
    main()
