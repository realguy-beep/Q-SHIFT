"""Local-only FastAPI service for the Q-SHIFT training dashboard."""
from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import json
import logging
import os
import socket
import uuid
from pathlib import Path
from queue import Empty

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import storage
from configuration import DEFAULT_CONFIG, PRESETS, needs_confirmation, validate_config
from manager import WorkerManager, RUNS_DIR
from seed_protocol import screen_plan, seed_plan
from telemetry import device_snapshot

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"
# This is a separate, read-only run owned by the autonomous controller. The
# dashboard never starts, pauses, resumes, or otherwise controls it.
AUTONOMOUS_RUN_DIR = HERE.parent / "outputs" / "neural_decoder_diagnostic" / "autonomous_development" / "run"
AUTONOMOUS_TOTAL_JOBS = 50
manager = WorkerManager()
security_logger = logging.getLogger("qshift.security")
app = FastAPI(title="Q-SHIFT Training Console", version="0.1.0", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class StartRequest(BaseModel):
    config: dict = Field(default_factory=dict)
    confirmed_large: bool = False
    confirmed_extreme: bool = False


class ControlRequest(BaseModel):
    action: str


_AUTONOMOUS_MODEL_LABELS = {
    "position_flat_cnn": "Position-preserving CNN",
    "balanced_mlp": "Balanced MLP",
    "pooled_cnn16_capacity_control": "Pooled CNN · capacity control",
    "residual_position_cnn": "Hybrid residual CNN + PyMatching",
}


def _stable_json(path: Path):
    """Read a committed JSON snapshot, declining files being replaced/written."""
    try:
        before = path.stat()
        raw = path.read_bytes()
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            return None
        value = json.loads(raw.decode("utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _stable_sha256(path: Path):
    """Hash a stable file; return None if it is missing or changing."""
    try:
        before = path.stat()
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            return None
        return digest.hexdigest()
    except OSError:
        return None


def _verified_recorded_shots(metadata_path: Path, arrays_path: Path, shot_map: dict):
    """Return persisted shot counts only when the associated array hash matches."""
    metadata = _stable_json(metadata_path)
    if not metadata or not metadata.get("sha256"):
        return None
    actual = _stable_sha256(arrays_path)
    if actual is None or actual != metadata.get("sha256"):
        return None
    return shot_map(metadata)


def autonomous_run_snapshot(run_dir: Path | None = None) -> dict:
    """Build a read-only view from persisted controller and verified result files."""
    run_dir = Path(run_dir or AUTONOMOUS_RUN_DIR)
    progress = _stable_json(run_dir / "progress.json")
    if progress is None:
        return {
            "available": False, "status": "unknown", "source": "autonomous controller persisted files",
            "completed_jobs": 0, "total_jobs": AUTONOMOUS_TOTAL_JOBS,
            "verified_jobs": 0, "current_root": None, "current_job": None,
            "active_runtime_seconds": None, "gpu_training_seconds": None,
            "shot_counts": None, "results": [], "independent_test_status": "not recorded",
            "warnings": ["Controller progress is missing, partial, or temporarily unavailable."],
        }

    raw_status = str(progress.get("status", "unknown")).lower()
    status = raw_status if raw_status in {"running", "completed", "paused", "failed"} else (
        "failed" if raw_status in {"stopped", "interrupted", "error"} else "unknown")
    completed_ids = progress.get("completed_jobs")
    if not isinstance(completed_ids, list):
        completed_ids = []
    completed_ids = [str(job) for job in completed_ids if isinstance(job, str)]
    completed_set = set(completed_ids)
    warnings = []

    results = []
    results_dir = run_dir / "job_results"
    predictions_dir = run_dir / "predictions"
    if results_dir.is_dir():
        for result_path in sorted(results_dir.glob("*.json")):
            result = _stable_json(result_path)
            if not result or result.get("status") != "completed":
                continue
            job_id = result.get("job_id")
            if not isinstance(job_id, str) or result_path.stem != job_id or job_id not in completed_set:
                continue
            prediction_path = predictions_dir / f"{job_id}.npz"
            recorded_hash = result.get("predictions_sha256")
            if not recorded_hash or _stable_sha256(prediction_path) != recorded_hash:
                warnings.append(f"Result {job_id} withheld until its prediction file is stable and hash-verified.")
                continue
            model = str(result.get("model", "unknown"))
            per_regime = result.get("per_regime") if isinstance(result.get("per_regime"), dict) else {}
            safe_regimes = {}
            for regime, metrics in per_regime.items():
                if not isinstance(metrics, dict):
                    continue
                safe_regimes[str(regime)] = {
                    key: metrics.get(key) for key in (
                        "shots", "errors", "ler", "positive_recall", "pymatching_errors",
                        "pymatching_ler", "candidate_only", "pymatching_only",
                        "paired_prediction_disagreements") if key in metrics
                }
            history = result.get("history") if isinstance(result.get("history"), list) else []
            safe_history = [
                {"epoch": point.get("epoch"), "monitor_nll": point.get("monitor_nll")}
                for point in history if isinstance(point, dict)
                and isinstance(point.get("epoch"), (int, float))
                and isinstance(point.get("monitor_nll"), (int, float))
            ]
            results.append({
                "job_id": job_id, "root_id": result.get("root_id"), "model": model,
                "model_label": _AUTONOMOUS_MODEL_LABELS.get(model, model),
                "train_size_per_regime": result.get("train_size_per_regime"),
                "shots": result.get("shots"), "gpu_training_seconds": result.get("gpu_training_seconds"),
                "per_regime": safe_regimes, "history": safe_history,
                "evidence": "completed result and prediction SHA-256 verified",
            })

    # Count only generated sample records whose paired NPZ is present and hash-valid.
    shot_counts = {"train": 0, "monitor": 0, "calibration": 0, "threshold_selection": 0,
                   "final_development_evaluation": 0, "verified_roots": 0}
    data_dir = run_dir / "data"
    if data_dir.is_dir():
        for root_meta_path in sorted(data_dir.glob("root_[0-9][0-9].json")):
            root_id_text = root_meta_path.stem.removeprefix("root_")
            if not root_id_text.isdigit():
                continue
            root_id = int(root_id_text)
            metadata = _stable_json(root_meta_path)
            if metadata is None or metadata.get("root_id") != root_id:
                continue
            actual = _stable_sha256(data_dir / f"root_{root_id:02d}.npz")
            if actual is None or actual != metadata.get("sha256"):
                continue
            root_counts = {key: 0 for key in shot_counts if key != "verified_roots"}
            for split_name, record in (metadata.get("splits") or {}).items():
                if not isinstance(record, dict) or not isinstance(record.get("shots"), int):
                    continue
                for split in root_counts:
                    if split_name.startswith(f"{split}__"):
                        root_counts[split] += record["shots"]
            final_path = data_dir / f"final_root_{root_id:02d}.json"
            final_meta = _stable_json(final_path)
            if final_meta and final_meta.get("root_id") == root_id:
                final_actual = _stable_sha256(data_dir / f"final_root_{root_id:02d}.npz")
                if final_actual is not None and final_actual == final_meta.get("sha256"):
                    root_counts["final_development_evaluation"] = sum(
                        int(item.get("shots", 0)) for item in (final_meta.get("regimes") or {}).values()
                        if isinstance(item, dict) and isinstance(item.get("shots"), int))
            for key, value in root_counts.items():
                shot_counts[key] += value
            shot_counts["verified_roots"] += 1
    if not shot_counts["verified_roots"]:
        shot_counts = None
        warnings.append("No complete, hash-verified generation records are currently available.")

    test_access = progress.get("independent_test_access")
    if test_access == 0:
        test_status = "SEALED — controller records zero independent-test access; no test data read by dashboard."
    elif isinstance(test_access, (int, float)):
        test_status = f"Controller records {test_access} independent-test accesses; dashboard does not read test data."
    else:
        test_status = "Independent-test access status is not recorded; dashboard does not read test data."

    return {
        "available": True, "status": status, "source": "autonomous controller persisted files",
        "completed_jobs": len(completed_set), "total_jobs": AUTONOMOUS_TOTAL_JOBS,
        "verified_jobs": len(results), "current_root": progress.get("current_root"),
        "current_job": progress.get("current_job"),
        "active_runtime_seconds": progress.get("active_wall_seconds"),
        "gpu_training_seconds": progress.get("gpu_training_seconds"),
        "last_progress_step": progress.get("last_progress_step"),
        "shot_counts": shot_counts, "results": results,
        "independent_test_status": test_status, "warnings": warnings,
    }


def resolve_config(raw: dict) -> dict:
    """Apply the selected preset's budgets when the client omits overrides."""
    values = dict(raw or {})
    preset_name = values.get("preset", DEFAULT_CONFIG["preset"])
    if preset_name in PRESETS:
        for key in ("training_shots", "validation_shots", "test_shots"):
            values.setdefault(key, PRESETS[preset_name][key])
    return validate_config(values)


def is_loopback(client_host: str | None) -> bool:
    # Starlette's in-process test transport uses this sentinel. Real network
    # requests are accepted only by parsing the socket peer as an IP address.
    if client_host == "testclient":
        return True
    if not client_host:
        return False
    try:
        address = ipaddress.ip_address(client_host)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped.is_loopback
    return address.is_loopback


def attach_execution_identity(run: dict) -> dict:
    """Expose actual run hardware without changing stored historical records."""
    if not run:
        return run
    run = dict(run)
    run_dir = RUNS_DIR / run["id"]
    metadata_path = run_dir / "run_metadata.json"
    meta = {}
    if metadata_path.is_file():
        try:
            meta = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = {}
    state = run.get("state") or {}
    progress = state.get("progress") or {}
    summary = state.get("summary") or {}
    device = meta.get("device") or summary.get("device") or progress.get("device")
    cuda_available = meta.get("cuda_available", summary.get("cuda_available"))
    training_verified = meta.get("cuda_training_verified", summary.get("cuda_training_verified"))
    if device == "cuda" and training_verified:
        label = f"CUDA training · {meta.get('cuda_device_name') or summary.get('cuda_device_name') or 'GPU'}"
    elif device == "cpu":
        label = "Historical CPU run" if meta.get("software", {}).get("torch", "").endswith("+cpu") else "CPU run"
    elif cuda_available is False:
        label = "CPU run · CUDA unavailable in worker"
    else:
        label = "Device not recorded"
    run["execution"] = {"device": device, "cuda_available": cuda_available,
                        "cuda_training_verified": training_verified,
                        "python_executable": meta.get("python_executable") or progress.get("python_executable"),
                        "label": label}
    return run


def _safe_header(request, name: str) -> str | None:
    value = request.headers.get(name)
    return value[:256] if value else None


def _log_rejected_request(kind: str, client_host: str | None, request):
    # Forwarded values are logged only as untrusted diagnostics. They are
    # never used to grant access; repr formatting escapes control characters.
    security_logger.warning(
        "Rejected non-loopback %s peer=%r request_host=%r host_header=%r "
        "x_forwarded_for=%r x_forwarded_proto=%r x_forwarded_host=%r path=%r",
        kind, client_host, getattr(getattr(request, "url", None), "hostname", None),
        _safe_header(request, "host"), _safe_header(request, "x-forwarded-for"),
        _safe_header(request, "x-forwarded-proto"), _safe_header(request, "x-forwarded-host"),
        getattr(getattr(request, "url", None), "path", None))


def _bind_loopback_sockets(port: int) -> list[socket.socket]:
    """Bind separate IPv4 and IPv6 loopback listeners, never a public interface."""
    listeners: list[socket.socket] = []
    selected_port = int(port)
    try:
        for family in (socket.AF_INET, socket.AF_INET6):
            address = (("127.0.0.1", selected_port) if family == socket.AF_INET
                       else ("::1", selected_port, 0, 0))
            listener = socket.socket(family, socket.SOCK_STREAM)
            try:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if family == socket.AF_INET6:
                    listener.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                listener.bind(address)
                if selected_port == 0:
                    selected_port = listener.getsockname()[1]
                listener.listen(socket.SOMAXCONN)
                listener.setblocking(False)
                listeners.append(listener)
            except Exception:
                listener.close()
                raise
    except Exception:
        for listener in listeners:
            listener.close()
        raise
    return listeners


def _uvicorn_config(port: int):
    import uvicorn
    return uvicorn.Config(app, host="127.0.0.1", port=port, proxy_headers=False,
                          forwarded_allow_ips="", reload=False,
                          access_log=False, log_level="info")


@app.middleware("http")
async def local_only(request: Request, call_next):
    client_host = request.client.host if request.client else None
    if not is_loopback(client_host):
        _log_rejected_request("HTTP", client_host, request)
        return JSONResponse(status_code=403, content={"detail": "Q-SHIFT controls accept localhost connections only."})
    return await call_next(request)


@app.on_event("startup")
async def startup():
    storage.init_db()
    storage.mark_orphaned_runs_interrupted()


@app.on_event("shutdown")
async def shutdown():
    manager.shutdown()


@app.get("/")
async def home():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "qshift-local-dashboard", "telemetry": device_snapshot(),
            "presets": PRESETS}


@app.get("/api/state")
async def state():
    active = manager.active_run()
    return {"active_run": attach_execution_identity(active) if active else None,
            "runs": [attach_execution_identity(run) for run in storage.list_runs(limit=20)],
            "telemetry": device_snapshot(), "presets": PRESETS}


@app.get("/api/autonomous-research")
async def autonomous_research():
    """Read-only status and hash-verified development evidence for the frozen run."""
    return autonomous_run_snapshot()


@app.get("/api/runs")
async def list_runs():
    return {"runs": [attach_execution_identity(run) for run in storage.list_runs(limit=100)]}


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    run = storage.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    return {"run": attach_execution_identity(run), "metrics": storage.get_metrics(run_id, limit=2000)}


@app.get("/api/runs/{run_id}/progress")
async def get_run_progress(run_id: str):
    """Small persisted snapshot for polling and WebSocket recovery."""
    run = storage.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    state = run.get("state") or {}
    return {"run_id": run_id, "status": run["status"], "updated_at": run["updated_at"],
            "progress": state.get("progress"), "summary": state.get("summary"),
            "error": run.get("error"), "worker_pid": run.get("worker_pid")}


@app.post("/api/runs", status_code=201)
async def start_run(request: StartRequest):
    active = manager.active_run()
    if active is not None:
        raise HTTPException(status_code=409, detail=f"Run {active['id']} is already active.")
    try:
        cfg = resolve_config(request.config)
        structured_worker = cfg.get("worker_kind") == "structured_3d_cnn"
        if structured_worker:
            # This pathway is the frozen prospective 100K multi-regime plan:
            # 70K train + 15K validation; the 15K test allocation is reserved
            # for a later independent evaluation and is never sampled here.
            cfg.update({"worker_kind": "structured_3d_cnn", "mode": "official_100k",
                        "training_shots": 70_000, "validation_shots": 15_000,
                        "test_shots": 15_000, "batch_size": 256,
                        "model_selection": "structured_3d_cnn"})
            if not request.confirmed_large:
                raise HTTPException(status_code=428, detail="Explicit confirmation is required for the 70K structured multi-regime training run.")
            from structured_training import load_prepared_freeze, screen_inventory
            _, structured_inventory = load_prepared_freeze()
            prior = manager.allocations()
            screening = screen_inventory(structured_inventory, prior, candidate_count=6)
            if not screening["passed"]:
                raise HTTPException(status_code=409, detail={"message": "Structured seed inventory collided; run is blocked.",
                                                            "collisions": screening["collisions"][:10]})
            range_records = {
                f"{stream['split']}_{stream['regime']}": stream["seed_range_inclusive"]
                for stream in structured_inventory["streams"]}
            model_rng = screening["candidate_model_rng_seeds"]
            range_records["candidate_model_rng"] = [min(model_rng), max(model_rng)]
            diagnostic_rng = screening["diagnostic_seeds"]
            range_records["circuit_diagnostics"] = [min(diagnostic_rng), max(diagnostic_rng)]
            plan = {"method": "frozen structured multi-regime allocation; test roots reserved but unused",
                    "stream_ranges_inclusive": range_records,
                    "shots": {"train": 70_000, "validation": 15_000, "test_reserved": 15_000},
                    "candidate_model_rng_seeds": model_rng,
                    "diagnostic_seeds": diagnostic_rng}
            run_id = uuid.uuid4().hex
            run_dir = RUNS_DIR / run_id
            run_dir.mkdir(parents=True, exist_ok=False)
            cfg_path = run_dir / "config.json"
            cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
            (run_dir / "seed_inventory.json").write_text(json.dumps(
                {"plan": plan, "screen": screening, "inventory": structured_inventory}, indent=2) + "\n",
                encoding="utf-8")
            storage.create_run(run_id, cfg, plan)
            pid = manager.start(run_id, cfg_path)
            return {"run_id": run_id, "status": "running", "worker_pid": pid,
                    "seed_plan": plan, "seed_screen": screening,
                    "run_directory": str(run_dir), "test_samples_generated": 0}
        confirm = needs_confirmation(cfg["training_shots"])
        if confirm == "large" and not request.confirmed_large:
            raise HTTPException(status_code=428, detail="Explicit large-run confirmation is required.")
        if confirm == "extreme" and not (request.confirmed_large and request.confirmed_extreme):
            raise HTTPException(status_code=428, detail="Two explicit confirmations are required for 100M/1B training presets.")
        plan = seed_plan(cfg["seed"], cfg["training_shots"], cfg["validation_shots"],
                         cfg["test_shots"], cfg["batch_size"])
        prior = manager.allocations()
        screening = screen_plan(plan, prior)
        if not screening["passed"]:
            raise HTTPException(status_code=409, detail={"message": "Seed collision detected; choose a fresh seed.",
                                                        "collisions": screening["collisions"][:10]})
        run_id = uuid.uuid4().hex
        run_dir = RUNS_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        cfg_path = run_dir / "config.json"
        cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        (run_dir / "seed_inventory.json").write_text(json.dumps({"plan": plan, "screen": screening}, indent=2) + "\n",
                                                     encoding="utf-8")
        storage.create_run(run_id, cfg, plan)
        pid = manager.start(run_id, cfg_path)
        return {"run_id": run_id, "status": "running", "worker_pid": pid,
                "seed_plan": plan, "seed_screen": screening,
                "run_directory": str(run_dir)}
    except HTTPException:
        raise
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/runs/{run_id}/control")
async def control_run(run_id: str, request: ControlRequest):
    try:
        result = manager.control(run_id, request.action)
        return {"run_id": run_id, "action": request.action, "result": result,
                "run": storage.get_run(run_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.websocket("/ws/{run_id}")
async def websocket_run(websocket: WebSocket, run_id: str):
    host = websocket.client.host if websocket.client else None
    if not is_loopback(host):
        _log_rejected_request("WebSocket", host, websocket)
        await websocket.close(code=1008, reason="localhost only")
        return
    if not storage.get_run(run_id):
        await websocket.close(code=1008, reason="unknown run")
        return
    await websocket.accept()
    q = manager.subscribe(run_id)
    try:
        # Subscribe before taking the durable snapshot. An event racing this
        # read is then represented by the snapshot, the queue, or both.
        run = storage.get_run(run_id)
        if not run:
            await websocket.close(code=1008, reason="unknown run")
            return
        await websocket.send_json({"type": "snapshot", "run": run,
                                   "metrics": storage.get_metrics(run_id, limit=2000)})
        while True:
            try:
                item = await asyncio.to_thread(q.get, True, 15)
                await websocket.send_json(item)
            except Empty:
                await websocket.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        pass
    finally:
        manager.unsubscribe(run_id, q)


def main():
    import uvicorn
    port = int(os.environ.get("QSHIFT_PORT", "8765"))
    sockets = _bind_loopback_sockets(port)
    try:
        uvicorn.Server(_uvicorn_config(port)).run(sockets=sockets)
    finally:
        for listener in sockets:
            listener.close()


if __name__ == "__main__":
    main()

