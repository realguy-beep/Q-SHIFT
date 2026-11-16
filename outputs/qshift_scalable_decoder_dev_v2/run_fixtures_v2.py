"""Run one predeclared q/d synthetic fixture in an isolated subprocess."""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time

SCRIPT = pathlib.Path(__file__).resolve()
OUTPUT = SCRIPT.parent / "fixture_results.json"
CASES = [(distance, q) for distance in (3, 5, 7) for q in (0.0, 0.01)]
CASE_TIMEOUT_SECONDS = 120


def run_one(distance: int, q: float):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--case", str(distance), str(q)],
        capture_output=True, text=True, timeout=CASE_TIMEOUT_SECONDS,
        cwd=SCRIPT.parents[2], check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"case d={distance}, q={q} exited {result.returncode}: {result.stderr[-2000:]}")
    return json.loads(result.stdout)


def write_checkpoint(output_path, rows):
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    if temporary.exists():
        raise FileExistsError(f"refusing to overwrite temporary evidence: {temporary}")
    with temporary.open("x", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rows, indent=2) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporary, output_path)


def main_parent(output_path=OUTPUT):
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite V2 evidence: {output_path}")
    rows = []
    started = time.monotonic()
    for distance, q in CASES:
        case_started = time.monotonic()
        try:
            row = run_one(distance, q)
            row["wall_seconds"] = time.monotonic() - case_started
            row["exit"] = 0
        except subprocess.TimeoutExpired:
            row = {"distance": distance, "q": q, "exit": "timeout",
                   "wall_seconds": CASE_TIMEOUT_SECONDS}
            rows.append(row)
            write_checkpoint(output_path, rows)
            break
        except Exception as ex:
            row = {"distance": distance, "q": q, "exit": "failure",
                   "wall_seconds": time.monotonic() - case_started,
                   "error": repr(ex)}
            rows.append(row)
            write_checkpoint(output_path, rows)
            break
        rows.append(row)
        write_checkpoint(output_path, rows)
    print(json.dumps({
        "cases_completed": sum(row.get("exit") == 0 for row in rows),
        "cases_total": len(CASES),
        "parent_wall_seconds": time.monotonic() - started,
        "rows": [
            {"distance": row["distance"], "q": row["q"], "exit": row["exit"],
             "converged": row.get("converged_fixtures"),
             "d3_disagreements": row.get("d3_prediction_disagreements"),
             "wall_seconds": row["wall_seconds"]}
            for row in rows
        ],
    }, indent=2))


def run_case(distance: int, q: float):
    import math
    import time
    import numpy as np
    import psutil
    import sys
    root = SCRIPT.parents[2]
    sys.path.insert(0, str(root))
    from factor_bp_v2 import FactorBPV2
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as model
    from outputs.qshift_v1_4b_decoder_optimality.mld import ExactLogicalDecoder

    def incidence_stats(decoder):
        vertex_count = len(decoder.p) + decoder.n
        adjacency = [[] for _ in range(vertex_count)]
        for variable, detector in decoder.edges:
            a, b = variable, len(decoder.p) + detector
            adjacency[a].append(b)
            adjacency[b].append(a)
        seen = set()
        components = 0
        visited = 0
        for start in range(vertex_count):
            if start in seen:
                continue
            components += 1
            seen.add(start)
            stack = [start]
            while stack:
                node = stack.pop()
                visited += 1
                for neighbor in adjacency[node]:
                    if neighbor not in seen:
                        seen.add(neighbor)
                        stack.append(neighbor)
        return {"components_including_isolates": components,
                "cycle_rank": len(decoder.edges) - vertex_count + components,
                "maximum_detector_degree": max((len(x) for x in decoder.by_c), default=0)}

    process = psutil.Process()
    total_started = time.perf_counter()
    spec = model.CodeSpec(distance=distance, rounds=5)
    support = model.burst_qubits(spec, "scaled_v1")
    circuit = model.build_candidate_circuit(spec, q, support)
    dem = circuit.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True)
    construction_started = time.perf_counter()
    decoder = FactorBPV2(dem)
    construction_seconds = time.perf_counter() - construction_started
    burst_events = model.extract_burst_events(spec, support)
    syndromes = [np.zeros(spec.detectors, dtype=np.uint8)]
    for event in burst_events[:5]:
        syndrome = np.zeros(spec.detectors, dtype=np.uint8)
        syndrome[list(event.detector_ids)] = 1
        syndromes.append(syndrome)

    exact = ExactLogicalDecoder(dem) if distance == 3 else None
    exact_started = time.perf_counter()
    exact_results = None
    if exact is not None:
        exact_predictions, exact_p1 = exact.decode(np.stack(syndromes))
        exact_results = [
            {"prediction": int(prediction[0]), "logical_p1_exact": float(probability)}
            for prediction, probability in zip(exact_predictions, exact_p1)
        ]
    exact_seconds = time.perf_counter() - exact_started if exact is not None else None

    inference_started = time.perf_counter()
    results = [decoder.decode_one(syndrome) for syndrome in syndromes]
    inference_seconds = time.perf_counter() - inference_started
    disagreements = None
    probability_errors = None
    if exact_results is not None:
        disagreements = sum(a["prediction_approx"] != b["prediction"] for a, b in zip(results, exact_results))
        probability_errors = [abs(a["logical_p1_approx"] - b["logical_p1_exact"])
                              for a, b in zip(results, exact_results)]
    return {
        "distance": distance, "q": q, "circuit_detectors": spec.detectors,
        "mechanisms": len(decoder.p), "incidence_edges": len(decoder.edges),
        **incidence_stats(decoder),
        "converged_fixtures": sum(result["converged"] for result in results),
        "fixture_count": len(results),
        "iterations": [result["iterations"] for result in results],
        "residuals": [result["message_residual"] for result in results],
        "logical_p1_approx": [result["logical_p1_approx"] for result in results],
        "predictions_approx": [result["prediction_approx"] for result in results],
        "exact_d3": exact_results,
        "d3_prediction_disagreements": disagreements,
        "d3_abs_logical_probability_error": probability_errors,
        "construction_seconds": construction_seconds,
        "exact_reference_seconds": exact_seconds,
        "inference_seconds": inference_seconds,
        "total_seconds": time.perf_counter() - total_started,
        "rss_bytes_at_end_not_peak": process.memory_info().rss,
    }


if len(sys.argv) == 4 and sys.argv[1] == "--case":
    print(json.dumps(run_case(int(sys.argv[2]), float(sys.argv[3]))))
elif len(sys.argv) == 1:
    main_parent()
elif len(sys.argv) == 3 and sys.argv[1] == "--output":
    name = pathlib.Path(sys.argv[2])
    if name.name != sys.argv[2] or name.suffix != ".json":
        raise SystemExit("--output requires a simple .json filename")
    main_parent(SCRIPT.parent / name)
else:
    raise SystemExit("usage: run_fixtures_v2.py [--case DISTANCE Q] [--output FILE.json]")

