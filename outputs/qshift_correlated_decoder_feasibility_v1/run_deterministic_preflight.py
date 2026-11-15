"""Sampler-free model/decoder feasibility check on algebraic syndrome fixtures."""
from __future__ import annotations

import itertools
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from outputs.qshift_correlated_decoder_feasibility_v1.correlated_model import (
    BurstEnumerationDecoder,
    PROBE_PROBABILITY,
    build_base_circuit,
    build_candidate_circuit,
    build_decomposed_dem,
    build_matching,
    extract_burst_events,
)


ROOT = Path(__file__).resolve().parent


def main() -> None:
    started = time.perf_counter()
    events = extract_burst_events()
    base_circuit = build_base_circuit()
    candidate_circuit = build_candidate_circuit(PROBE_PROBABILITY)
    background_dem = build_decomposed_dem(base_circuit)
    candidate_dem = build_decomposed_dem(candidate_circuit)
    background = build_matching(background_dem)
    static = build_matching(candidate_dem)
    model_construction_seconds = time.perf_counter() - started
    factor = BurstEnumerationDecoder(background, events, PROBE_PROBABILITY)

    burst_only = []
    for mask in range(1 << len(events)):
        syndrome = np.zeros(40, dtype=np.uint8)
        for index, event in enumerate(events):
            if (mask >> index) & 1:
                syndrome[list(event.detector_ids)] ^= 1
        burst_only.append(syndrome)

    background_signatures = []
    for line in (line for line in str(background_dem).splitlines() if line.startswith("error(")):
        detector_ids = [int(value) for value in re.findall(r"D(\d+)", line)]
        if detector_ids:
            syndrome = np.zeros(40, dtype=np.uint8)
            syndrome[detector_ids] ^= 1
            background_signatures.append(syndrome)
    background_signatures = background_signatures[:100]
    if len(background_signatures) != 100:
        raise RuntimeError("expected at least 100 background DEM fault signatures")

    composite = []
    for base in background_signatures:
        for mask in (0,) + tuple(1 << index for index in range(len(events))):
            syndrome = base.copy()
            for index, event in enumerate(events):
                if (mask >> index) & 1:
                    syndrome[list(event.detector_ids)] ^= 1
            composite.append(syndrome)

    decode_started = time.perf_counter()
    burst_only_differences = 0
    for syndrome in burst_only:
        a = int(np.asarray(static.decode(syndrome, enable_correlations=True)).reshape(-1)[0])
        b = factor.decode_one(syndrome)
        burst_only_differences += a != b
    composite_differences = 0
    for syndrome in composite:
        a = int(np.asarray(static.decode(syndrome, enable_correlations=True)).reshape(-1)[0])
        b = factor.decode_one(syndrome)
        composite_differences += a != b
    decode_seconds = time.perf_counter() - decode_started

    correlated_lines = [line for line in str(candidate_dem).splitlines()
                        if line.startswith(f"error({PROBE_PROBABILITY:g}) ")]
    result = {
        "schema": "qshift-correlated-decoder-deterministic-preflight-v1",
        "candidate": {
            "qubits": [8, 12, 15], "probability": PROBE_PROBABILITY,
            "detectors": candidate_circuit.num_detectors,
            "observables": candidate_circuit.num_observables,
            "five_detector_signatures": [list(event.detector_ids) for event in events],
            "event_observable_flips": [event.observable_flip for event in events],
            "un-decomposed_event_support": 3,
            "decomposed_event_lines": correlated_lines,
        },
        "decoder_models": {
            "baseline": "PyMatching from full Stim DEM, decompose_errors=True, approximate_disjoint_errors=True, correlations enabled at build and decode",
            "candidate": "enumerate 2^5 burst-factor subsets; score each with background correlation-aware MWPM edge cost plus burst log-odds",
            "candidate_is_exact_full_circuit_ml": False,
        },
        "deterministic_patterns": {
            "all_burst_subset_patterns": len(burst_only),
            "burst_only_prediction_disagreements": burst_only_differences,
            "background_fault_plus_one_burst_patterns": len(composite),
            "composite_prediction_disagreements": composite_differences,
        },
        "observed_costs": {
            "model_construction_seconds": model_construction_seconds,
            "decode_seconds_for_632_patterns": decode_seconds,
            "end_to_end_seconds": time.perf_counter() - started,
            "timing_scope": "single local deterministic run; not a production throughput benchmark",
        },
        "sampler_calls": 0,
        "logical_labels_used": False,
        "full_syndrome_space_enumeration": "not feasible: 2^40 detector patterns; enumerated all 32 burst subsets and 600 constructed valid fault-combination patterns instead",
    }
    with (ROOT / "deterministic_preflight.json").open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "output": str(ROOT / "deterministic_preflight.json"),
        "all_burst_subset_patterns": len(burst_only),
        "burst_only_disagreements": burst_only_differences,
        "composite_patterns": len(composite),
        "composite_disagreements": composite_differences,
        "sampler_calls": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
