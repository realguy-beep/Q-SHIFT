from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
import stim
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

WEBAPP_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = WEBAPP_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from outputs.stage4_noise_adaptive_feasibility_v1.prototype import (  # noqa: E402
    DetectorProfileEstimator,
    build_decoder,
    decode_prediction,
    logical_error_mask,
)

app = FastAPI(title="Q-SHIFT Local Lab", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class SimulationRequest(BaseModel):
    burst_probability: float = Field(ge=0.0, le=0.02)
    shots: int = Field(default=2000, ge=100, le=10000)
    calibration_shots: int = Field(default=1000, ge=500, le=5000)
    seed: int = Field(default=7, ge=0, le=100000)


@app.middleware("http")
async def local_only(request: Request, call_next):
    """Localhost-only boundary; forwarded headers are deliberately ignored."""
    client = request.client.host if request.client else ""
    if client not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        return JSONResponse({"detail": "Q-SHIFT demo accepts localhost connections only."}, status_code=403)
    return await call_next(request)


def _seed_block(user_seed: int) -> list[int]:
    # A separate demo-only namespace, disjoint from the recorded Stage 4 seed block.
    base = 4_280_000_000 + user_seed * 16
    values = list(range(base + 1, base + 6))
    if len(set(values)) != 5 or values[-1] >= 2**32:
        raise ValueError("seed is outside the supported demo namespace")
    return values


def _wilson(errors: int, shots: int, z: float = 1.959963984540054) -> list[float]:
    p = errors / shots
    den = 1 + z * z / shots
    mid = (p + z * z / (2 * shots)) / den
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * shots)) / shots) / den
    return [max(0.0, mid - half), min(1.0, mid + half)]


def _exact_mcnemar(a_only: int, b_only: int) -> float:
    n = a_only + b_only
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(a_only, b_only) + 1)) / (2**n)
    return min(1.0, 2 * tail)


def _sample(circuit: stim.Circuit, shots: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    det, obs = circuit.compile_detector_sampler(seed=seed).sample(
        shots=shots, separate_observables=True
    )
    if det.shape != (shots, 40) or obs.shape != (shots, 1):
        raise RuntimeError(f"unexpected Stim result shapes: {det.shape}, {obs.shape}")
    return det.astype(np.uint8, copy=False), obs[:, 0].astype(np.uint8, copy=False)


def _metrics(detectors: np.ndarray, obs: np.ndarray, predictions: dict[str, np.ndarray]) -> dict:
    fixed = predictions["fixed_nominal"]
    rows = []
    fixed_bad = logical_error_mask(fixed, obs)
    for name, pred in predictions.items():
        bad = logical_error_mask(pred, obs)
        errors = int(bad.sum())
        cand_only = int(np.count_nonzero(bad & ~fixed_bad)) if name != "fixed_nominal" else 0
        fixed_only = int(np.count_nonzero(~bad & fixed_bad)) if name != "fixed_nominal" else 0
        rows.append({
            "id": name,
            "label": {
                "fixed_nominal": "Fixed nominal PyMatching",
                "detector_estimated": "Detector-estimated PyMatching",
                "privileged_reference": "Privileged true-probability reference",
            }[name],
            "errors": errors,
            "shots": int(len(obs)),
            "ler": errors / len(obs),
            "wilson_95": _wilson(errors, len(obs)),
            "prediction_disagreements_vs_fixed": int(np.count_nonzero(pred != fixed)),
            "candidate_only_vs_fixed": cand_only,
            "fixed_only_vs_candidate": fixed_only,
            "mcnemar_exact_p_vs_fixed": _exact_mcnemar(cand_only, fixed_only),
        })
    no_decode_errors = int(obs.sum())
    return {
        "methods": rows,
        "no_decoding_reference": {"label": "Raw observable failures (identity/no correction)",
                                  "errors": no_decode_errors, "shots": int(len(obs)),
                                  "ler": no_decode_errors / len(obs)},
        "detectors": int(detectors.shape[1]),
        "observable_count": 1,
    }


@lru_cache(maxsize=3)
def _profile_model(profile_seed: int, profile_shots: int) -> DetectorProfileEstimator:
    probs = (0.0, 0.01, 0.02)
    batches = []
    for j, p in enumerate(probs):
        circuit, _, _ = build_decoder(p)
        det, _ = _sample(circuit, profile_shots, profile_seed + j)
        batches.append((p, det))
    return DetectorProfileEstimator.fit(batches)


def run_live_simulation(req: SimulationRequest) -> dict:
    started = time.perf_counter()
    seeds = _seed_block(req.seed)
    p = req.burst_probability
    profile_shots = 1000
    profile_seed = seeds[0]
    estimator = _profile_model(profile_seed, profile_shots)

    circuit, _, _ = build_decoder(p)
    calibration, _ = _sample(circuit, req.calibration_shots, seeds[3])
    p_hat = estimator.estimate(calibration)

    _, _, fixed = build_decoder(0.0)
    _, _, estimated = build_decoder(p_hat)
    _, _, privileged = build_decoder(p)

    # Create paired evaluation outcomes once. Observable labels are not passed to any estimator.
    eval_det, eval_obs = _sample(circuit, req.shots, seeds[4])
    coordinate_map = circuit.get_detector_coordinates()
    by_time: dict[float, list[int]] = {}
    for detector_id, coords in coordinate_map.items():
        by_time.setdefault(float(coords[2]), []).append(int(detector_id))
    time_slices = [{"time": t, "detector_ids": sorted(ids)} for t, ids in sorted(by_time.items())]
    predictions = {
        "fixed_nominal": decode_prediction(fixed, eval_det),
        "detector_estimated": decode_prediction(estimated, eval_det),
        "privileged_reference": decode_prediction(privileged, eval_det),
    }
    scored = _metrics(eval_det, eval_obs, predictions)
    scored.update({
        "mode": "live_simulation",
        "generating_burst_probability": p,
        "estimated_burst_probability": p_hat,
        "estimation_error": p_hat - p,
        "calibration_shots": req.calibration_shots,
        "profile_shots_per_probability": profile_shots,
        "evaluation_shots": req.shots,
        "paired_evaluation": True,
        "seed_block_id": req.seed,
        "derived_seeds": {"profile_p0": seeds[0], "profile_p001": seeds[1],
                          "profile_p002": seeds[2], "detector_calibration": seeds[3],
                          "paired_evaluation": seeds[4]},
        "runtime_seconds": round(time.perf_counter() - started, 4),
        "software": {"stim": stim.__version__},
        "limitations": [
            "Synthetic independent-per-round spatial burst on data qubits 8 and 10.",
            "Stim DEM conversion uses approximate_disjoint_errors=True.",
            "Privileged reference uses the generating probability and is not deployable.",
            "Simulation result; no quantum hardware is involved.",
        ],
        "records": [
            {"index": i, "detectors": "".join(map(str, eval_det[i].tolist())),
             "observable": int(eval_obs[i]),
             "fixed_prediction": int(predictions["fixed_nominal"][i]),
             "estimated_prediction": int(predictions["detector_estimated"][i]),
             "privileged_prediction": int(predictions["privileged_reference"][i]),
             "fixed_residual_error": int(predictions["fixed_nominal"][i] ^ eval_obs[i]),
             "estimated_residual_error": int(predictions["detector_estimated"][i] ^ eval_obs[i]),
             "detector_slices": [
                 {"time": item["time"], "detector_ids": item["detector_ids"],
                  "bits": "".join(str(int(eval_det[i, detector_id])) for detector_id in item["detector_ids"])}
                 for item in time_slices
             ]}
            for i in range(min(12, req.shots))
        ],
    })
    return scored


@app.get("/api/health")
def health():
    try:
        import pymatching
        versions = {"stim": stim.__version__, "pymatching": pymatching.__version__}
        c, d, m = build_decoder(0.0)
        ready = (c.num_detectors, c.num_observables, d.num_detectors,
                 m.num_detectors, m.num_fault_ids) == (40, 1, 40, 40, 1)
        return {"status": "ready" if ready else "invalid", "local_only": True,
                "sealed_test_loaded": False, "software": versions}
    except Exception as exc:
        return JSONResponse({"status": "unavailable", "error": str(exc),
                             "local_only": True, "sealed_test_loaded": False}, status_code=503)


@app.get("/api/research")
def research_summary():
    evidence_dir = REPO_ROOT / "outputs" / "stage4_noise_adaptive_development_v1"
    path = evidence_dir / "RESULTS.json"
    if not path.is_file():
        raise HTTPException(status_code=503, detail="Committed Stage 4B summary is unavailable")
    data = json.loads(path.read_text(encoding="utf-8"))
    audit_path = evidence_dir / "AUDIT_RESULTS.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.is_file() else {}
    result_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    audit_status = audit.get("status", "UNAVAILABLE")
    summary_hash_matches_audit = audit.get("results_sha256") == result_hash
    coverage_matches_audit = int(audit.get("verified_evaluation_shots", -1)) == int(data["aggregate"]["paired_evaluation_shots"])
    return {"mode": "saved_replay", "study": data["study"], "status": data["status"],
            "gate_status": data["gate_status"], "aggregate": data["aggregate"],
            "estimation_diagnostics": data["estimation_diagnostics"],
            "statistics": data["statistics"], "per_condition": data["per_condition"],
            "source": "outputs/stage4_noise_adaptive_development_v1/RESULTS.json",
            "audit": audit_status, "summary_hash_matches_audit": summary_hash_matches_audit,
            "coverage_matches_audit": coverage_matches_audit,
            "independent_test_accessed": bool(audit.get("independent_test_accessed", True)),
            "claim_boundary": "Simulation-based development evidence only; not hardware validation or independent confirmation."}


@app.get("/api/dataset/schema")
def dataset_schema():
    return {"source": "Live local Stim generation", "sealed_test_included": False,
            "record_fields": ["40 detector bits", "one observable label", "paired decoder predictions"],
            "note": "Sample rows appear only after a live simulation. Stage 4B raw arrays are not bundled into the web worktree."}


@app.post("/api/simulate")
def simulate(req: SimulationRequest):
    try:
        return run_live_simulation(req)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Local simulation failed: {type(exc).__name__}: {exc}") from exc


FRONTEND_DIST = WEBAPP_DIR / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def frontend(path: str):
        candidate = FRONTEND_DIST / path
        if path and candidate.is_file() and FRONTEND_DIST in candidate.resolve().parents:
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
