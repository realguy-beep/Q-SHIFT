"""Deterministically compare selected burst detector supports in Q-SHIFT DEMs.

This constructs Stim circuits and detector error models only. It does not sample
shots, decode syndromes, or calculate logical outcomes. Run from any directory:

    python outputs/qshift_method_landscape_research_v1/deterministic_dem_support_audit.py
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path

import stim

REPO_ROOT = Path(__file__).resolve().parents[2]
SIMULATOR_DIR = REPO_ROOT / "outputs" / "phase3a_correlated_noise_preflight"
if str(SIMULATOR_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATOR_DIR))

from simulator import build_spatial_burst_circuit  # noqa: E402


BURST_PAIRS = ((8, 10), (16, 18), (24, 26), (32, 34), (36, 38))


def build_support_counts(burst_probability: float):
    circuit = build_spatial_burst_circuit(
        memory_basis="z",
        regime="balanced",
        distance=3,
        rounds=5,
        gate_p=0.003,
        measurement_p=0.003,
        bias_ratio=10.0,
        burst_probability=burst_probability,
        burst_pair=(8, 10),
    )
    dem = circuit.detector_error_model(
        decompose_errors=True,
        approximate_disjoint_errors=True,
    )
    supports: dict[tuple[int, ...], list[float]] = collections.defaultdict(list)
    for instruction in dem:
        if instruction.type != "error":
            continue
        detector_support = tuple(
            sorted(
                target.val
                for target in instruction.targets_copy()
                if target.is_relative_detector_id()
            )
        )
        probability = float(instruction.args_copy()[0])
        supports[detector_support].append(probability)
    return circuit, dem, supports


def main() -> None:
    baseline_circuit, baseline_dem, baseline = build_support_counts(0.0)
    burst_circuit, burst_dem, burst = build_support_counts(0.01)
    print(f"stim_version={stim.__version__}")
    print(
        "baseline_dem: "
        f"detectors={baseline_circuit.num_detectors}, "
        f"observables={baseline_circuit.num_observables}, "
        f"error_mechanisms={sum(map(len, baseline.values()))}"
    )
    print(
        "burst_dem: "
        f"detectors={burst_circuit.num_detectors}, "
        f"observables={burst_circuit.num_observables}, "
        f"error_mechanisms={sum(map(len, burst.values()))}"
    )
    for pair in BURST_PAIRS:
        baseline_probabilities = baseline.get(pair, [])
        burst_probabilities = burst.get(pair, [])
        print(
            f"detector_support={pair} "
            f"baseline_probabilities={baseline_probabilities} "
            f"burst_inclusive_probabilities={burst_probabilities}"
        )
        if baseline_probabilities or burst_probabilities != [0.01]:
            raise RuntimeError(f"unexpected detector-support mapping for {pair}")
    if baseline_dem.num_detectors != burst_dem.num_detectors:
        raise RuntimeError("DEM detector count changed between compared templates")
    if baseline_dem.num_observables != burst_dem.num_observables:
        raise RuntimeError("DEM observable count changed between compared templates")
    if sum(map(len, baseline.values())) != 586 or sum(map(len, burst.values())) != 591:
        raise RuntimeError("DEM mechanism counts differ from the recorded configuration")


if __name__ == "__main__":
    main()
