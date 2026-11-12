"""Shared, bounded helpers for strong fixed-baseline development study v1."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np
import stim

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit
from outputs.stage4_noise_adaptive_feasibility_v1.prototype import (
    DetectorProfileEstimator,
    build_decoder,
    decode_prediction,
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _replace_with_retry(source: str | Path, destination: str | Path,
                        retries: int = 6, initial_delay_seconds: float = 0.025) -> None:
    """Retry transient Windows sharing/access denial without weakening atomicity.

    Retries only PermissionError from os.replace, keeps the same fully flushed
    temporary payload, and never deletes the destination or falls back to a
    non-atomic write. Persistent denial is surfaced to the caller.
    """
    for attempt in range(retries + 1):
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            if attempt >= retries:
                raise
            time.sleep(initial_delay_seconds * (2 ** attempt))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(value)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        _replace_with_retry(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def atomic_npz(path: Path, **arrays: np.ndarray) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            np.savez_compressed(f, **arrays)
            f.flush()
            os.fsync(f.fileno())
        _replace_with_retry(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    return sha256(path)


def validate_binary(name: str, value: np.ndarray, shape: tuple[int, ...] | None = None) -> np.ndarray:
    a = np.asarray(value)
    if shape is not None and a.shape != shape:
        raise ValueError(f"{name} shape {a.shape}, expected {shape}")
    if a.dtype.kind not in "bui" or not np.isin(a, (0, 1)).all():
        raise ValueError(f"{name} must contain binary values")
    return a.astype(np.uint8, copy=False)


def make_circuit(probability: float, config: dict[str, Any]) -> stim.Circuit:
    c = config["circuit"]
    circuit = build_spatial_burst_circuit(
        memory_basis=c["memory_basis"], regime=c["regime"], distance=int(c["distance"]),
        rounds=int(c["rounds"]), gate_p=float(c["gate_p"]),
        measurement_p=float(c["measurement_p"]), bias_ratio=float(c["bias_ratio"]),
        burst_probability=float(probability), burst_pair=tuple(c["burst_pair"]),
    )
    if (circuit.num_detectors, circuit.num_observables) != (int(c["detectors"]), int(c["observables"])):
        raise RuntimeError("generated circuit detector/observable dimensions differ from frozen configuration")
    return circuit


def dem_kwargs(config: dict[str, Any]) -> dict[str, Any]:
    # PyMatching's enable_correlations is a graph-construction setting, not a Stim DEM option.
    return {k: v for k, v in config["circuit"]["dem"].items() if k != "enable_correlations"}


def sample_arrays(probability: float, seed: int, shots: int, config: dict[str, Any], *, labels: bool):
    """Sample a fresh Stim stream. Calibration callers discard observables immediately."""
    if shots <= 0:
        raise ValueError("shots must be positive")
    circuit = make_circuit(probability, config)
    sampler = circuit.compile_detector_sampler(seed=int(seed))
    if labels:
        detectors, observables = sampler.sample(shots=int(shots), separate_observables=True)
        d = validate_binary("detectors", detectors, (shots, int(config["circuit"]["detectors"])))
        o = validate_binary("observables", observables, (shots, int(config["circuit"]["observables"])))
        if o.shape[1] != 1:
            raise ValueError("v1 scoring requires exactly one logical observable")
        return d, o[:, 0]
    detectors, _discarded_observables = sampler.sample(shots=int(shots), separate_observables=True)
    d = validate_binary("calibration detectors", detectors, (shots, int(config["circuit"]["detectors"])))
    # Never return or persist calibration observables.
    return d


def build_models(probabilities: list[float]) -> dict[float, Any]:
    result = {}
    for p in probabilities:
        p = float(p)
        if p not in result:
            result[p] = build_decoder(p)[2]
    return result


def score_models(detectors: np.ndarray, models: dict[float, Any]) -> np.ndarray:
    d = validate_binary("detectors", detectors)
    return np.stack([decode_prediction(model, d) for model in models.values()]).astype(np.uint8)


def decode_candidate_grid(detectors: np.ndarray, models: dict[float, Any]) -> tuple[list[float], np.ndarray]:
    """Decode one shared batch with every candidate, in the bank's frozen order."""
    d = validate_binary("detectors", detectors)
    probabilities = [float(p) for p in models]
    if len(probabilities) != len(set(probabilities)) or not probabilities:
        raise ValueError("candidate model bank is empty or contains duplicate p keys")
    predictions = np.stack([decode_prediction(models[p], d) for p in probabilities]).astype(np.uint8)
    if predictions.shape != (len(probabilities), d.shape[0]):
        raise RuntimeError("candidate grid output is not aligned to its shared detector batch")
    return probabilities, predictions


def root_errors(prediction: np.ndarray, observable: np.ndarray) -> dict[str, int | float]:
    p = validate_binary("prediction", prediction)
    o = validate_binary("observable", observable)
    if p.shape != o.shape:
        raise ValueError("prediction/observable shot alignment mismatch")
    residual = p ^ o
    return {
        "errors": int(residual.sum()),
        "shots": int(residual.size),
        "ler": float(residual.mean()),
        "candidate_only": int(np.sum((p == 1) & (o == 0))),
        "baseline_only": int(np.sum((p == 0) & (o == 1))),
    }


def select_safety_constrained_static(candidate_probabilities: list[float],
                                     zero_burst_lers: dict[float, np.ndarray],
                                     nonzero_condition_lers: dict[float, dict[float, np.ndarray]],
                                     zero_harm_limit: float) -> tuple[float, dict[float, dict[str, float]]]:
    """Development-only fixed-model selector with deterministic lower-p tie break."""
    if 0.0 not in zero_burst_lers:
        raise ValueError("p=0 candidate LERs are required")
    reference = np.asarray(zero_burst_lers[0.0], dtype=np.float64)
    diagnostics = {}
    eligible = []
    if reference.ndim != 1 or reference.size < 2:
        raise ValueError("selection requires at least two independent p=0 roots")
    for p in candidate_probabilities:
        p = float(p)
        values = np.asarray(zero_burst_lers[p], dtype=np.float64)
        if values.shape != reference.shape:
            raise ValueError("all p=0 candidates must use identical paired roots")
        harm = float(np.mean(values - reference))
        condition_means = []
        for condition in sorted(nonzero_condition_lers):
            by_p = nonzero_condition_lers[condition]
            x = np.asarray(by_p[p], dtype=np.float64)
            if x.ndim != 1 or x.size < 2:
                raise ValueError("nonzero candidate LERs need independent paired roots")
            condition_means.append(float(x.mean()))
        objective = float(np.mean(condition_means))
        diagnostics[p] = {"p0_harm": harm, "equal_nonzero_mean_ler": objective}
        if harm <= float(zero_harm_limit):
            eligible.append((objective, p))
    chosen = min(eligible, key=lambda item: (item[0], item[1]))[1] if eligible else 0.0
    return float(chosen), diagnostics


def safety_validation_accept(chosen_probability: float, one_sided_upper: float,
                             harm_limit: float) -> tuple[float, bool]:
    """Validation may accept or fall back only; it must never reselect."""
    if not np.isfinite(one_sided_upper):
        raise ValueError("validation upper bound must be finite")
    accepted = float(chosen_probability) == 0.0 or float(one_sided_upper) <= float(harm_limit)
    return (float(chosen_probability) if accepted else 0.0), bool(accepted)


def detector_profile_estimator(template_batches: list[tuple[float, np.ndarray]]) -> DetectorProfileEstimator:
    return DetectorProfileEstimator.fit(template_batches)


def current_rss_bytes() -> int:
    try:
        import psutil
        return int(psutil.Process().memory_info().rss)
    except ImportError as e:
        raise RuntimeError("psutil is required to enforce the configured RSS limit") from e


def acquire_exclusive_lock(path: Path) -> int:
    """Create-only lock; stale locks fail closed and require manual inspection."""
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    fd = os.open(path, flags, 0o600)
    os.write(fd, canonical_json_bytes({"pid": os.getpid(), "created_unix": time.time()}))
    os.fsync(fd)
    return fd

