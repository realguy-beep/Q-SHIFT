"""Stim and PyMatching adapters that reuse the frozen Phase 2B generator."""
from __future__ import annotations

import hashlib
import json
import sys
from numbers import Integral
from pathlib import Path

import numpy as np
import pymatching
import stim

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE2B = REPO_ROOT / "outputs" / "phase2b_pauli_bias"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(PHASE2B) not in sys.path:
    sys.path.insert(0, str(PHASE2B))

from qshift_core_v1.pymatching_adapter import PyMatchingDecoder  # noqa: E402

from noise_model import REGIMES, circuit_noise_record  # noqa: E402
from decoder_bank import build_bank  # noqa: E402
from configuration import validate_config  # noqa: E402

FIXED_INDEX_BY_BASIS = {"x": 0, "z": 2}


def prepare(config: dict):
    config = validate_config(config)
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
    if isinstance(seed, bool) or not isinstance(seed, Integral) or not 1 <= int(seed) <= 2_147_483_647:
        raise ValueError("Stim seed must be an integer in [1, 2147483647].")
    if isinstance(shots, bool) or not isinstance(shots, Integral) or int(shots) <= 0:
        raise ValueError("shots must be a positive integer.")
    if int(circuit.num_observables) != 1:
        raise ValueError(f"dashboard requires one logical observable, got {circuit.num_observables}.")
    try:
        sampler = circuit.compile_detector_sampler(seed=int(seed))
        detectors, observables = sampler.sample(shots=int(shots), separate_observables=True)
    except Exception as exc:
        raise RuntimeError(f"Stim batch sampling failed (seed={int(seed)}, shots={int(shots)}).") from exc
    d_raw = np.asarray(detectors)
    y_raw = np.asarray(observables)
    expected_d = (int(shots), int(circuit.num_detectors))
    expected_y = (int(shots), int(circuit.num_observables))
    if d_raw.shape != expected_d or y_raw.shape != expected_y:
        raise RuntimeError(f"unexpected sampled arrays: detectors={d_raw.shape} expected={expected_d}; "
                           f"observables={y_raw.shape} expected={expected_y}")
    if (d_raw.dtype.kind not in "biuf" or y_raw.dtype.kind not in "biuf"
            or not np.isfinite(d_raw).all() or not np.isfinite(y_raw).all()
            or np.any((d_raw != 0) & (d_raw != 1))
            or np.any((y_raw != 0) & (y_raw != 1))):
        raise RuntimeError("Stim returned non-binary detector or observable data.")
    return np.ascontiguousarray(d_raw, dtype=np.uint8), np.ascontiguousarray(y_raw[:, 0], dtype=np.uint8)


def decode_matching(matching: pymatching.Matching, detectors: np.ndarray) -> np.ndarray:
    # Phase 2B's decoder_bank constructs every model with
    # enable_correlations=True. Keep the legacy 1-D, one-observable result
    # shape while routing validation and decode options through the versioned
    # adapter. Do not alter the DEM approximation or noise semantics here.
    adapter = PyMatchingDecoder.from_existing(
        matching,
        detector_count=40,
        observable_count=1,
        constructed_with_correlations=True,
        name="phase2b-fixed-pymatching",
        construction_provenance=(
            "verified Phase 2B decoder_bank.build_bank constructor: "
            "Matching.from_detector_error_model(..., enable_correlations=True)"
        ),
    )
    try:
        prediction = adapter.decode(detectors).bits
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid Phase 2B PyMatching decode input/output: {exc}") from exc
    return prediction[:, 0]


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

