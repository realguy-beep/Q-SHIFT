"""Local Q-SHIFT science-exhibition demo using real Stim and PyMatching runs."""
from __future__ import annotations

import logging
import re
import secrets
import threading
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import pymatching
import stim
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
EVALUATION_SHOT_CHOICES = (1_000, 5_000, 10_000)
SUPPORTED_BURST_PROBABILITIES = (0.0, 0.004, 0.008, 0.012, 0.016)
CALIBRATION_SHOTS = 2_000
PROFILE_GRID = tuple(float(x) for x in np.linspace(0.0, 0.016, 17))
PROFILE_SHOTS_PER_SETTING = 1_200
PROFILE_REFERENCE_SHOTS = len(PROFILE_GRID) * PROFILE_SHOTS_PER_SETTING
PROFILE_FEATURE_SCALE_FLOOR = 0.012
EVALUATION_BATCH_SIZE = 500

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("qshift.exhibition")

app = FastAPI(title="Q-SHIFT Exhibition Demo", version="1.0.0")
_job_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="qshift-simulation")


class RunRequest(BaseModel):
    shots: int = Field(ge=1_000, le=10_000, strict=True)
    burst: float = Field(ge=0.0, le=0.016)
    calibration_shots: int = Field(default=CALIBRATION_SHOTS, ge=200, le=5_000, strict=True)


def make_circuit(burst_probability: float) -> stim.Circuit:
    """Build the demo circuit; this is explicitly not the frozen Stage 5 generator."""
    if not 0.0 <= float(burst_probability) <= 0.016:
        raise ValueError("Burst probability must be between 0 and 0.016")

    base = stim.Circuit.generated(
        "surface_code:rotated_memory_z",
        distance=3,
        rounds=5,
        after_clifford_depolarization=0.003,
        before_measure_flip_probability=0.003,
    )
    out = stim.Circuit()
    boundaries = 0
    for instruction in base.flattened():
        out.append(instruction)
        if instruction.name == "MR":
            boundaries += 1
            if burst_probability:
                out.append(
                    "CORRELATED_ERROR",
                    [stim.target_x(8), stim.target_x(10)],
                    float(burst_probability),
                )

    if boundaries != 5:
        raise RuntimeError(f"Expected five measurement boundaries, found {boundaries}")
    if out.num_detectors != 40 or out.num_observables != 1:
        raise RuntimeError(
            f"Unexpected circuit dimensions: {out.num_detectors} detectors, "
            f"{out.num_observables} observables"
        )
    return out


def build_decoder(burst_probability: float) -> pymatching.Matching:
    """Build an ordinary PyMatching graph; correlation decoding is disabled."""
    circuit = make_circuit(burst_probability)
    dem = circuit.detector_error_model(
        decompose_errors=True,
        approximate_disjoint_errors=True,
    )
    # This construction does not enable PyMatching's correlated decoder mode.
    # Therefore production calls use decode_batch(detectors) with no
    # enable_correlations=True argument. This is compatible with PyMatching 2.4.0.
    return pymatching.Matching.from_detector_error_model(dem)


def estimate_burst_probability(
    calibration_detectors: np.ndarray,
    profile_means: np.ndarray,
) -> tuple[float, int]:
    """Fit the nearest standardized detector profile without logical labels."""
    calibration_detectors = np.asarray(calibration_detectors)
    profile_means = np.asarray(profile_means)
    if calibration_detectors.ndim != 2 or calibration_detectors.shape[1] != 40:
        raise ValueError("Calibration detectors must have shape (shots, 40)")
    if profile_means.shape != (len(PROFILE_GRID), 40):
        raise ValueError("Profile means must have shape (17, 40)")
    if calibration_detectors.shape[0] == 0:
        raise ValueError("At least one calibration shot is required")

    observed = calibration_detectors.mean(axis=0)
    scales = np.maximum(np.std(profile_means, axis=0), PROFILE_FEATURE_SCALE_FLOOR)
    distances = np.sum(((profile_means - observed) / scales) ** 2, axis=1)
    selected = int(np.argmin(distances))  # deterministic: first grid point wins ties
    return PROFILE_GRID[selected], selected


def decode_paired(
    detectors: np.ndarray,
    observables: np.ndarray,
    fixed_decoder: pymatching.Matching,
    adaptive_decoder: pymatching.Matching,
    privileged_decoder: pymatching.Matching | None = None,
) -> dict[str, int]:
    """Decode the same detector rows with both models and score against one label array."""
    detectors = np.asarray(detectors, dtype=np.uint8)
    observables = np.asarray(observables, dtype=np.uint8).reshape(-1)
    if detectors.ndim != 2 or detectors.shape[1] != 40:
        raise ValueError("Evaluation detectors must have shape (shots, 40)")
    if len(detectors) != len(observables):
        raise ValueError("Detector and observable shot counts do not match")

    # Do not pass enable_correlations=True: these decoders were constructed with
    # correlation decoding disabled. Both arms receive the identical detector matrix.
    fixed_predictions = np.asarray(fixed_decoder.decode_batch(detectors), dtype=np.uint8).reshape(-1)
    adaptive_predictions = np.asarray(adaptive_decoder.decode_batch(detectors), dtype=np.uint8).reshape(-1)
    if len(fixed_predictions) != len(observables) or len(adaptive_predictions) != len(observables):
        raise RuntimeError("Decoder output length did not match the paired evaluation batch")

    fixed_failures = fixed_predictions ^ observables
    adaptive_failures = adaptive_predictions ^ observables
    result = {
        "fixed_errors": int(np.count_nonzero(fixed_failures)),
        "adaptive_errors": int(np.count_nonzero(adaptive_failures)),
        "prediction_disagreements": int(np.count_nonzero(fixed_predictions ^ adaptive_predictions)),
    }
    if privileged_decoder is not None:
        privileged_predictions = np.asarray(
            privileged_decoder.decode_batch(detectors), dtype=np.uint8
        ).reshape(-1)
        if privileged_predictions.shape != (len(observables),) or not np.isin(
            privileged_predictions, (0, 1)
        ).all():
            raise RuntimeError("Privileged reference returned invalid predictions")
        result["privileged_errors"] = int(
            np.count_nonzero(privileged_predictions ^ observables)
        )
    return result


def deterministic_dem_fixture() -> dict[str, Any]:
    """Decode one fixed DEM mechanism without sampling a circuit shot.

    The selected event is illustrative and DEM-level. It is not represented as
    a draw from the circuit distribution or as a Stage 5 observation.
    """
    circuit = make_circuit(0.008)
    dem = circuit.detector_error_model(
        decompose_errors=True,
        approximate_disjoint_errors=True,
    )
    selected = None
    for instruction in dem:
        if instruction.type != "error":
            continue
        rendered = str(instruction)
        if "^" in rendered:
            continue
        detector_ids = [int(x) for x in re.findall(r"\bD(\d+)\b", rendered)]
        if detector_ids:
            observable_ids = [int(x) for x in re.findall(r"\bL(\d+)\b", rendered)]
            selected = (detector_ids, observable_ids)
            break
    if selected is None:
        raise RuntimeError("No unsplit detector-bearing DEM mechanism is available for the fixture")

    detector_ids, observable_ids = selected
    syndrome = np.zeros(circuit.num_detectors, dtype=np.uint8)
    for detector_id in detector_ids:
        if not 0 <= detector_id < circuit.num_detectors:
            raise RuntimeError(f"DEM fixture detector index is out of range: {detector_id}")
        syndrome[detector_id] ^= 1
    true_observable_parity = len(observable_ids) % 2
    decoder = pymatching.Matching.from_detector_error_model(dem)
    prediction = int(np.asarray(decoder.decode(syndrome)).reshape(-1)[0])
    return {
        "fixture_kind": "single DEM mechanism; deterministic, no sampled shot",
        "representation": "decomposed approximate DEM from the exhibition circuit at burst p=0.008",
        "detector_indices": detector_ids,
        "syndrome": syndrome.astype(int).tolist(),
        "observable_parity_for_mechanism": true_observable_parity,
        "predicted_observable_correction": prediction,
        "logical_success_for_fixture": prediction == true_observable_parity,
        "decoder": "PyMatching ordinary matching; correlation mode disabled",
        "limitation": "DEM mechanism fixture, not an exact circuit-level sampled history or Stage 5 result",
    }


def _snapshot(job_id: str) -> dict[str, Any]:
    with _job_lock:
        if job_id not in _jobs:
            raise HTTPException(status_code=404, detail="Unknown run ID. The local server may have restarted.")
        result = dict(_jobs[job_id])
    started = result.pop("_started_monotonic", None)
    if started is not None and result["status"] in {"queued", "running"}:
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return result


def _update_job(job_id: str, **updates: Any) -> None:
    with _job_lock:
        _jobs[job_id].update(updates)


def _worker(job_id: str, req: RunRequest) -> None:
    started = time.monotonic()
    seed = secrets.randbelow(2**31 - 20_000)
    try:
        circuit = make_circuit(req.burst)
        _update_job(
            job_id,
            status="running",
            phase="calibration",
            seed=seed,
            detector_count=circuit.num_detectors,
            observable_count=circuit.num_observables,
        )

        calibration_start = time.perf_counter()
        calibration_detectors = circuit.compile_detector_sampler(seed=seed).sample(
            req.calibration_shots
        ).astype(np.uint8, copy=False)
        _update_job(
            job_id,
            calibration_shots_completed=int(len(calibration_detectors)),
            calibration_seconds=round(time.perf_counter() - calibration_start, 4),
            phase="reference profiles",
        )

        # Independent detector-only reference profiles are additional samples,
        # not evaluation shots and not part of the requested calibration batch.
        profile_start = time.perf_counter()
        profile_means = []
        for index, probability in enumerate(PROFILE_GRID):
            reference_circuit = make_circuit(probability)
            reference = reference_circuit.compile_detector_sampler(
                seed=seed + 100 + index
            ).sample(PROFILE_SHOTS_PER_SETTING)
            profile_means.append(reference.mean(axis=0))
        profile_means_array = np.asarray(profile_means, dtype=np.float64)
        profile_seconds = time.perf_counter() - profile_start
        p_hat, profile_index = estimate_burst_probability(
            calibration_detectors, profile_means_array
        )
        _update_job(
            job_id,
            profile_reference_shots=PROFILE_REFERENCE_SHOTS,
            profile_seconds=round(profile_seconds, 4),
            p_hat=p_hat,
            selected_profile_index=profile_index,
            phase="decoder construction",
        )

        decoder_start = time.perf_counter()
        fixed_decoder = build_decoder(0.0)
        adaptive_decoder = build_decoder(p_hat)
        privileged_decoder = build_decoder(req.burst)
        _update_job(job_id, decoder_build_seconds=round(time.perf_counter() - decoder_start, 4))

        evaluation_sampler = circuit.compile_detector_sampler(seed=seed + 10_000)
        fixed_errors = 0
        adaptive_errors = 0
        privileged_errors = 0
        disagreements = 0
        generated_shots = 0
        completed_shots = 0
        detector_events = 0
        eval_started = time.perf_counter()
        _update_job(job_id, phase="evaluation")

        while completed_shots < req.shots:
            batch_size = min(EVALUATION_BATCH_SIZE, req.shots - completed_shots)
            detectors, observables = evaluation_sampler.sample(
                batch_size,
                separate_observables=True,
            )
            detectors = np.asarray(detectors, dtype=np.uint8)
            observables = np.asarray(observables, dtype=np.uint8).reshape(-1)
            generated_shots += len(detectors)
            _update_job(job_id, generated_shots=generated_shots)
            # Generated and completed are separate: a row only counts as
            # completed once both decoders and residual scoring finish.
            batch = decode_paired(
                detectors, observables, fixed_decoder, adaptive_decoder,
                privileged_decoder=privileged_decoder,
            )
            detector_events += int(np.count_nonzero(detectors))
            fixed_errors += batch["fixed_errors"]
            adaptive_errors += batch["adaptive_errors"]
            privileged_errors += batch["privileged_errors"]
            disagreements += batch["prediction_disagreements"]
            completed_shots += len(detectors)
            last_detector_indices = np.flatnonzero(detectors[-1]).astype(int).tolist()
            _update_job(
                job_id,
                generated_shots=generated_shots,
                completed_shots=completed_shots,
                fixed_errors=fixed_errors,
                adaptive_errors=adaptive_errors,
                privileged_errors=privileged_errors,
                prediction_disagreements=disagreements,
                detector_events=detector_events,
                last_detector_indices=last_detector_indices,
                evaluation_seconds=round(time.perf_counter() - eval_started, 4),
            )

        total_elapsed = time.monotonic() - started
        _update_job(
            job_id,
            status="completed",
            phase="complete",
            completed_shots=completed_shots,
            generated_shots=generated_shots,
            elapsed_seconds=round(total_elapsed, 3),
            evaluation_seconds=round(time.perf_counter() - eval_started, 4),
            fixed_ler=fixed_errors / completed_shots,
            adaptive_ler=adaptive_errors / completed_shots,
            privileged_errors=privileged_errors,
            privileged_ler=privileged_errors / completed_shots,
            adaptive_minus_fixed_ler=(adaptive_errors - fixed_errors) / completed_shots,
        )
        logger.info(
            "run completed id=%s shots=%d burst=%.3f p_hat=%.5f fixed=%d adaptive=%d elapsed=%.3fs",
            job_id,
            completed_shots,
            req.burst,
            p_hat,
            fixed_errors,
            adaptive_errors,
            total_elapsed,
        )
    except Exception as exc:  # failure is shown to the visitor; full traceback stays in local log
        elapsed = time.monotonic() - started
        logger.exception("run failed id=%s", job_id)
        _update_job(
            job_id,
            status="error",
            phase="failed",
            error=f"{type(exc).__name__}: {exc}",
            elapsed_seconds=round(elapsed, 3),
        )


def _engine_status() -> dict[str, str]:
    return {
        "engine": "ready",
        "stim": getattr(stim, "__version__", "installed"),
        "pymatching": getattr(pymatching, "__version__", "installed"),
        "python": __import__("platform").python_version(),
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "index.html")


@app.get("/api/health")
@app.get("/api/status")
def health() -> dict[str, str]:
    try:
        return _engine_status()
    except ImportError as exc:  # kept for clear dependency diagnostics
        logger.exception("simulation dependency import failed")
        raise HTTPException(status_code=503, detail=f"Simulation dependencies unavailable: {exc}") from exc


@app.get("/api/fixture")
def fixture() -> dict[str, Any]:
    """Return a deterministic model-mechanism walkthrough; this endpoint does not sample."""
    try:
        return deterministic_dem_fixture()
    except Exception as exc:
        logger.exception("deterministic fixture failed")
        raise HTTPException(status_code=500, detail=f"Deterministic DEM fixture unavailable: {exc}") from exc


@app.post("/api/run", status_code=202)
def run(req: RunRequest) -> dict[str, str]:
    if req.shots not in EVALUATION_SHOT_CHOICES:
        raise HTTPException(status_code=422, detail="Choose 1,000, 5,000, or 10,000 evaluation shots")
    if not any(abs(req.burst - probability) <= 1e-9 for probability in SUPPORTED_BURST_PROBABILITIES):
        raise HTTPException(status_code=422, detail="Choose one of the supported burst probabilities")

    with _job_lock:
        if any(job["status"] in {"queued", "running"} for job in _jobs.values()):
            raise HTTPException(status_code=429, detail="A simulation is already running. Please wait for it to finish.")
        job_id = secrets.token_hex(8)
        now = time.monotonic()
        _jobs[job_id] = {
            "id": job_id,
            "status": "queued",
            "phase": "queued",
            "shots": req.shots,
            "burst": req.burst,
            "calibration_shots_requested": req.calibration_shots,
            "calibration_shots_completed": 0,
            "profile_shots_per_probability": PROFILE_SHOTS_PER_SETTING,
            "profile_probability_count": len(PROFILE_GRID),
            "profile_reference_shots": PROFILE_REFERENCE_SHOTS,
            "generated_shots": 0,
            "completed_shots": 0,
            "fixed_errors": 0,
            "adaptive_errors": 0,
            "privileged_errors": 0,
            "prediction_disagreements": 0,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "_started_monotonic": now,
        }
        _pool.submit(_worker, job_id, req)
    return {"id": job_id}


@app.get("/api/run/{job_id}")
def run_status(job_id: str) -> dict[str, Any]:
    return _snapshot(job_id)


def _open_browser_when_ready() -> None:
    """Open the local page only after this server responds to its health check."""
    import urllib.request

    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8765/api/health", timeout=0.5) as response:
                if response.status == 200:
                    webbrowser.open("http://127.0.0.1:8765")
                    return
        except Exception:
            time.sleep(0.2)
    logger.warning("Server did not become ready within 20 seconds; open http://127.0.0.1:8765 manually")


if __name__ == "__main__":
    threading.Thread(target=_open_browser_when_ready, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
