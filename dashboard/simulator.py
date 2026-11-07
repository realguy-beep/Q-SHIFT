"""Stim and PyMatching adapters that reuse the frozen Phase 2B generator."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pymatching
import stim

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE2B = REPO_ROOT / "outputs" / "phase2b_pauli_bias"
if str(PHASE2B) not in sys.path:
    sys.path.insert(0, str(PHASE2B))

from noise_model import REGIMES, circuit_noise_record  # noqa: E402
from decoder_bank import build_bank  # noqa: E402

FIXED_INDEX_BY_BASIS = {"x": 0, "z": 2}


def prepare(config: dict):
    basis = config["memory_basis"]
    regime = config["noise_regime"]
    circuit, noise_record = circuit_noise_record(
        basis, regime,
        distance=int(config["distance"]), rounds=int(config["rounds"]),
        gate_p=float(config["gate_p"]), measurement_p=float(config["measurement_p"]),
        bias_ratio=float(config["bias_ratio"]),
    )
    if circuit.num_detectors != 40 or circuit.num_observables != 1:
        raise RuntimeError(f"expected 40 detector bits and 1 logical observable, got {circuit.num_detectors}/{circuit.num_observables}")
    # This fixed baseline is the calibration-selected Phase 2B bank model for
    # the requested memory basis. It is not rebuilt from the hidden generation regime.
    bank, records = build_bank(
        basis, distance=int(config["distance"]), rounds=int(config["rounds"]),
        gate_p=0.003, measurement_p=0.003, bias_ratio=10.0,
    )
    fixed_index = FIXED_INDEX_BY_BASIS[basis]
    saved_selection = json.loads((PHASE2B / "CALIBRATION_SELECTION.json").read_text(encoding="utf-8"))
    saved_index = int(saved_selection["selected_models"][basis]["global_index"])
    if fixed_index != saved_index:
        raise RuntimeError(f"Frozen Phase 2B baseline index mismatch for basis {basis}: {fixed_index} != {saved_index}")
    matching = bank[fixed_index]
    dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
    return circuit, noise_record, dem, matching, fixed_index, records


def sample(circuit: stim.Circuit, seed: int, shots: int) -> tuple[np.ndarray, np.ndarray]:
    sampler = circuit.compile_detector_sampler(seed=int(seed))
    detectors, observables = sampler.sample(shots=int(shots), separate_observables=True)
    d = np.asarray(detectors, dtype=np.uint8)
    y = np.asarray(observables, dtype=np.uint8)
    if d.shape != (int(shots), 40) or y.shape != (int(shots), 1):
        raise RuntimeError(f"unexpected sampled arrays: detectors={d.shape}, observables={y.shape}")
    return d, y[:, 0]


def decode_matching(matching: pymatching.Matching, detectors: np.ndarray) -> np.ndarray:
    pred = np.asarray(matching.decode_batch(np.asarray(detectors, dtype=np.uint8), enable_correlations=True), dtype=np.uint8)
    if pred.ndim == 2:
        if pred.shape[1] != 1:
            raise RuntimeError(f"expected one observable column, got {pred.shape}")
        pred = pred[:, 0]
    if pred.shape != (len(detectors),) or np.any((pred != 0) & (pred != 1)):
        raise RuntimeError(f"invalid PyMatching prediction array: {pred.shape}")
    return pred


def model_identity(circuit: stim.Circuit, dem: stim.DetectorErrorModel) -> dict:
    c_text, d_text = str(circuit), str(dem)
    return {
        "circuit_sha256": hashlib.sha256(c_text.encode()).hexdigest(),
        "dem_sha256": hashlib.sha256(d_text.encode()).hexdigest(),
        "circuit_text": c_text,
        "dem_text": d_text,
        "detectors": circuit.num_detectors,
        "observables": circuit.num_observables,
        "stim_version": stim.__version__,
        "pymatching_version": pymatching.__version__,
        "noise_semantics": "Samples come from categorical PAULI_CHANNEL_1/2 instructions in the frozen Phase 2B circuit generator. The matching baseline uses a Stim DEM with approximate_disjoint_errors=True; this decoder-model approximation does not alter the Stim sampling distribution.",
        "phase2b_source_hashes": {
            name: hashlib.sha256((PHASE2B / name).read_bytes()).hexdigest()
            for name in ("noise_model.py", "decoder_bank.py", "PHASE2B_PROTOCOL.md", "CALIBRATION_SELECTION.json")
        },
    }

