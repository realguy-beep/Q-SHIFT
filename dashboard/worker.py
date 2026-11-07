"""One isolated, resumable training process per dashboard run."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from configuration import validate_config
from models import DirectMLP, ResidualMLP
from seed_protocol import batch_seed, seed_plan, screen_plan
from simulator import decode_matching, model_identity, prepare, sample
from qshift_stats import compare_predictions
from telemetry import device_snapshot


def emit(event: dict):
    print(json.dumps(event, separators=(",", ":"), allow_nan=False), flush=True)


def atomic_torch_save(payload, path: Path):
    tmp = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, tmp)
    os.replace(tmp, path)


def atomic_json_write(payload, path: Path):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def split_samples(circuit, matching, plan, split, count, batch_size, progress_callback=None):
    ds, ys, ps = [], [], []
    sample_seconds = 0.0
    decode_seconds = 0.0
    remaining = int(count)
    index = 0
    while remaining > 0:
        size = min(batch_size, remaining)
        tick = time.perf_counter()
        d, y = sample(circuit, batch_seed(plan, split, index), size)
        sample_seconds += time.perf_counter() - tick
        if progress_callback:
            progress_callback("simulation", split, count - remaining + size, count,
                              sample_seconds, decode_seconds)
        tick = time.perf_counter()
        p = decode_matching(matching, d)
        decode_seconds += time.perf_counter() - tick
        ds.append(d)
        ys.append(y)
        ps.append(p)
        remaining -= size
        index += 1
        if progress_callback:
            progress_callback("decoding", split, count - remaining, count,
                              sample_seconds, decode_seconds)
    return np.concatenate(ds), np.concatenate(ys), np.concatenate(ps), {
        "stim_generation_seconds": sample_seconds,
        "pymatching_decode_seconds": decode_seconds,
    }


def save_checkpoint(path, *, cfg_hash, direct, residual, opt_direct, opt_residual,
                    scaler, step, processed, losses, best_val, model_seed):
    payload = {
        "schema_version": 1, "config_sha256": cfg_hash, "completed_steps": int(step),
        "training_samples_processed": int(processed),
        "direct_state": direct.state_dict(), "residual_state": residual.state_dict() if residual is not None else None,
        "optimizer_direct": opt_direct.state_dict(),
        "optimizer_residual": opt_residual.state_dict() if opt_residual is not None else None,
        "scaler_state": scaler.state_dict(), "loss_history": losses,
        "best_validation_ler": best_val, "model_seed": int(model_seed),
        "torch_rng_state": torch.get_rng_state(),
        "cuda_rng_state_all": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
        "numpy_rng_state": np.random.get_state(), "python_rng_state": random.getstate(),
    }
    atomic_torch_save(payload, path)


def evaluate_models(d, y, fixed_pred, direct, residual, device):
    direct.eval()
    if residual is not None:
        residual.eval()
    x = torch.from_numpy(np.asarray(d, dtype=np.float32)).to(device)
    b = torch.from_numpy(np.asarray(fixed_pred, dtype=np.float32)).to(device)
    direct_seconds = 0.0
    residual_seconds = 0.0
    with torch.inference_mode():
        if device.type == "cuda":
            torch.cuda.synchronize(device)
        tick = time.perf_counter()
        direct_logits = direct(x)
        direct_pred = (torch.sigmoid(direct_logits) >= 0.5).to(torch.uint8).cpu().numpy()
        if device.type == "cuda":
            torch.cuda.synchronize(device)
        direct_seconds = time.perf_counter() - tick
        if residual is not None:
            if device.type == "cuda":
                torch.cuda.synchronize(device)
            tick = time.perf_counter()
            residual_logits = residual(x, b)
            correction = (torch.sigmoid(residual_logits) >= 0.5).to(torch.uint8).cpu().numpy()
            residual_pred = np.bitwise_xor(fixed_pred, correction)
            if device.type == "cuda":
                torch.cuda.synchronize(device)
            residual_seconds = time.perf_counter() - tick
        else:
            residual_pred = None
    direct.train()
    if residual is not None:
        residual.train()
    return direct_pred, residual_pred, {
        "direct_neural_inference_seconds": direct_seconds,
        "residual_neural_inference_seconds": residual_seconds,
    }


def run(config_path: Path, run_dir: Path, resume: bool = False):
    cfg = validate_config(json.loads(config_path.read_text(encoding="utf-8")))
    run_dir.mkdir(parents=True, exist_ok=True)
    cfg_bytes = json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()
    cfg_hash = hashlib.sha256(cfg_bytes).hexdigest()
    plan = seed_plan(cfg["seed"], cfg["training_shots"], cfg["validation_shots"],
                     cfg["test_shots"], cfg["batch_size"])
    inventory_path = run_dir / "seed_inventory.json"
    if inventory_path.exists():
        saved_inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        if saved_inventory.get("plan") != plan:
            raise RuntimeError("Saved seed inventory does not match this run configuration.")
        screen = saved_inventory.get("screen", screen_plan(plan))
    else:
        screen = screen_plan(plan)
    if not screen["passed"]:
        raise RuntimeError(f"seed collision preflight failed: {screen['collisions'][:5]}")
    atomic_json_write({"plan": plan, "screen": screen}, run_dir / "seed_inventory.json")

    want_cuda = cfg["device"] == "cuda" or (cfg["device"] == "auto" and torch.cuda.is_available())
    if cfg["device"] == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested, but torch.cuda.is_available() is false. Select Auto or CPU, or install a CUDA-enabled PyTorch build.")
    device = torch.device("cuda" if want_cuda else "cpu")
    cuda_training_verified = False
    cuda_device_name = None
    if device.type == "cuda":
        torch.cuda.set_device(0)
        torch.cuda.reset_peak_memory_stats(0)
        cuda_device_name = torch.cuda.get_device_name(0)
    model_seed = int(cfg["seed"] + 70_000_000)
    random.seed(model_seed)
    np.random.seed(model_seed % (2**32))
    torch.manual_seed(model_seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(model_seed)

    circuit, noise_record, dem, matching, fixed_index, bank_records = prepare(cfg)
    noiseless = circuit.without_noise()
    nd, ny = noiseless.compile_detector_sampler(seed=1).sample(shots=8, separate_observables=True)
    if np.any(nd) or np.any(ny):
        raise RuntimeError("Noiseless circuit validation failed: detector or observable bit was nonzero.")
    zero_pred = decode_matching(matching, np.zeros((8, 40), dtype=np.uint8))
    if np.any(zero_pred):
        raise RuntimeError("Frozen PyMatching baseline did not return a zero correction for the zero syndrome.")

    total_shots = int(cfg["training_shots"] + cfg["validation_shots"] + cfg["test_shots"])
    started = time.perf_counter()
    processed = 0
    last_emit = started
    progress = {"generated_training": int(processed), "generated_validation": 0,
                "generated_test": 0, "decoded_training": int(processed),
                "decoded_validation": 0, "decoded_test": 0, "trained": int(processed),
                "analysis_completed": 0}

    def emit_progress(phase, phase_completed=None, phase_total=None, split=None):
        generated = progress["generated_training"] + progress["generated_validation"] + progress["generated_test"]
        completed_work = progress["trained"] + progress["decoded_validation"] + progress["decoded_test"]
        elapsed = max(1e-9, time.perf_counter() - started)
        speed = completed_work / elapsed if completed_work else 0.0
        remaining_work = max(0, total_shots - completed_work)
        eta = remaining_work / speed if speed > 0 else None
        event = {"type": "progress", "status": "running", "phase": phase,
                 "run_id": run_dir.name, "total_shots": total_shots,
                 # A shot is complete only once its relevant generation/decoding
                 # (and training use, for train shots) has finished. Generated
                 # volume is reported separately and never drives completion ETA.
                 "completed_shots": completed_work, "processed_shots": completed_work,
                 "generated_shots": generated,
                 "progress_percent": completed_work * 100.0 / total_shots if total_shots else None,
                 "phase_completed_shots": phase_completed, "phase_total_shots": phase_total,
                 "split": split, "generated_training_shots": progress["generated_training"],
                 "training_samples_processed": progress["trained"],
                 "generated_validation_shots": progress["generated_validation"],
                 "generated_test_shots": progress["generated_test"],
                 "total_training_shots": cfg["training_shots"],
                 "throughput_shots_s": speed, "elapsed_seconds": elapsed,
                 "eta_seconds": eta,
                 "stage_counts": {"simulation": generated, "decoding": progress["decoded_training"] +
                                  progress["decoded_validation"] + progress["decoded_test"],
                                  "analysis": progress["analysis_completed"]},
                 "device": str(device), "cuda_training_verified": cuda_training_verified,
                 "cuda_device_name": cuda_device_name, "python_executable": sys.executable,
                 "gpu_telemetry": device_snapshot(), "model_selection": cfg["model_selection"]}
        emit(event)

    def split_progress(phase, split, done, total, sample_seconds, decode_seconds):
        generated_key = f"generated_{split}"
        decoded_key = f"decoded_{split}"
        progress[generated_key] = max(progress[generated_key], int(done)) if phase == "simulation" else progress[generated_key]
        if phase == "decoding": progress[decoded_key] = max(progress[decoded_key], int(done))
        emit_progress(f"{phase}_{split}", done, total, split)

    emit_progress("preparing")
    steps_total = (cfg["training_shots"] + cfg["batch_size"] - 1) // cfg["batch_size"]
    val_d, val_y, val_match, val_generation_metrics = split_samples(circuit, matching, plan, "validation",
                                                                     cfg["validation_shots"], cfg["batch_size"],
                                                                     progress_callback=split_progress)
    progress["decoded_validation"] = len(val_y)
    val_direct, val_residual, = (None, None)
    direct = DirectMLP().to(device)
    use_residual = cfg["model_selection"] == "direct_plus_residual"
    residual = ResidualMLP().to(device) if use_residual else None
    opt_direct = torch.optim.AdamW(direct.parameters(), lr=cfg["learning_rate"], weight_decay=1e-4)
    opt_residual = torch.optim.AdamW(residual.parameters(), lr=cfg["learning_rate"], weight_decay=1e-4) if residual is not None else None
    amp_enabled = bool(cfg["mixed_precision"] and device.type == "cuda")
    scaler = torch.amp.GradScaler("cuda", enabled=amp_enabled)
    start_step, processed, loss_history, best_val = 0, 0, [], None
    checkpoint_path = run_dir / "checkpoint.pt"
    if resume:
        if not checkpoint_path.is_file():
            raise RuntimeError("Resume requested, but no safe checkpoint exists.")
        state = torch.load(checkpoint_path, map_location=device, weights_only=False)
        if state.get("config_sha256") != cfg_hash:
            raise RuntimeError("Checkpoint configuration hash does not match the saved run configuration.")
        direct.load_state_dict(state["direct_state"])
        if residual is not None and state.get("residual_state") is not None:
            residual.load_state_dict(state["residual_state"])
        opt_direct.load_state_dict(state["optimizer_direct"])
        if opt_residual is not None and state.get("optimizer_residual") is not None:
            opt_residual.load_state_dict(state["optimizer_residual"])
        scaler.load_state_dict(state["scaler_state"])
        start_step = int(state["completed_steps"])
        processed = int(state["training_samples_processed"])
        loss_history = list(state.get("loss_history", []))
        best_val = state.get("best_validation_ler")
        torch.set_rng_state(state["torch_rng_state"].cpu())
        if device.type == "cuda" and state.get("cuda_rng_state_all") is not None:
            torch.cuda.set_rng_state_all(state["cuda_rng_state_all"])
        np.random.set_state(state["numpy_rng_state"])
        random.setstate(state["python_rng_state"])

    progress["generated_training"] = int(processed)
    progress["decoded_training"] = int(processed)
    progress["trained"] = int(processed)

    identity_val = np.zeros_like(val_y, dtype=np.uint8)
    baseline_val_errors = int(np.count_nonzero(val_match ^ val_y))
    baseline_val_ler = baseline_val_errors / len(val_y)
    last_emit = time.perf_counter()
    seen_total = processed
    emit({"type": "progress", "status": "running", "run_id": run_dir.name,
          "generated_training_shots": processed, "training_samples_processed": processed,
          "training_sample_passes": processed * (2 if residual is not None else 1),
          "total_training_shots": cfg["training_shots"], "generated_validation_shots": len(val_y),
          "generated_test_shots": 0, "step": start_step, "steps_total": steps_total,
          "epoch": 1, "training_pass": 1, "train_loss": None, "validation_ler": None,
          "pymatching_validation_ler": baseline_val_ler, "throughput_shots_s": 0.0,
          "elapsed_seconds": 0.0, "eta_seconds": None, "device": str(device),
          "cuda_training_verified": cuda_training_verified, "cuda_device_name": cuda_device_name,
          "python_executable": sys.executable,
          "gpu_telemetry": device_snapshot(), "model_selection": cfg["model_selection"],
          "phase": "training", "total_shots": total_shots,
          "completed_shots": progress["decoded_validation"],
          "generated_shots": progress["generated_validation"],
          "processed_shots": progress["decoded_validation"],
          "progress_percent": progress["decoded_validation"] * 100.0 / total_shots,
          "phase_completed_shots": processed, "phase_total_shots": cfg["training_shots"],
          "stage_counts": {"simulation": progress["generated_validation"],
                           "decoding": progress["decoded_validation"], "analysis": 0}})

    for step_idx in range(start_step, steps_total):
        stop_file = run_dir / "control.request"
        request = stop_file.read_text(encoding="utf-8").strip() if stop_file.exists() else ""
        batch_start = step_idx * cfg["batch_size"]
        count = min(cfg["batch_size"], cfg["training_shots"] - batch_start)
        d_np, y_np = sample(circuit, batch_seed(plan, "train", step_idx), count)
        progress["generated_training"] += count
        match_np = decode_matching(matching, d_np)
        progress["decoded_training"] += count
        x = torch.from_numpy(d_np.astype(np.float32)).to(device)
        y = torch.from_numpy(y_np.astype(np.float32)).to(device)
        m = torch.from_numpy(match_np.astype(np.float32)).to(device)
        if device.type == "cuda":
            if not (x.is_cuda and y.is_cuda and m.is_cuda):
                raise RuntimeError("CUDA was selected, but training batch tensors are not on CUDA.")
            if not all(parameter.is_cuda for parameter in direct.parameters()):
                raise RuntimeError("CUDA was selected, but the training model parameters are not on CUDA.")
        direct.train()
        opt_direct.zero_grad(set_to_none=True)
        with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=amp_enabled):
            logits = direct(x)
            direct_loss = F.binary_cross_entropy_with_logits(logits.float(), y)
        scaler.scale(direct_loss).backward()
        scaler.step(opt_direct)
        if residual is not None:
            residual.train()
            opt_residual.zero_grad(set_to_none=True)
            target_residual = torch.bitwise_xor(m.to(torch.uint8), y.to(torch.uint8)).float()
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=amp_enabled):
                r_logits = residual(x, m)
                residual_loss = F.binary_cross_entropy_with_logits(r_logits.float(), target_residual)
            scaler.scale(residual_loss).backward()
            scaler.step(opt_residual)
        scaler.update()
        if device.type == "cuda" and not cuda_training_verified:
            # Verify after an actual forward/backward/optimizer step, rather
            # than inferring training from GPU detection alone.
            torch.cuda.synchronize(device)
            cuda_training_verified = bool(x.is_cuda and direct_loss.is_cuda and
                                          all(parameter.is_cuda for parameter in direct.parameters()))
            if not cuda_training_verified:
                raise RuntimeError("Could not verify that the first optimization step executed on CUDA.")
        step = step_idx + 1
        processed += count
        progress["trained"] = processed
        loss_value = float((direct_loss.detach().float() + (residual_loss.detach().float() if residual is not None else 0)) /
                           (2 if residual is not None else 1))
        loss_history.append(loss_value)

        do_validation = step % cfg["validation_frequency_steps"] == 0 or step == steps_total
        val_ler = None
        if do_validation:
            val_direct, val_residual, _ = evaluate_models(val_d, val_y, val_match, direct, residual, device)
            val_errors = int(np.count_nonzero(val_direct ^ val_y))
            val_ler = val_errors / len(val_y)
            if residual is not None:
                val_errors_r = int(np.count_nonzero(val_residual ^ val_y))
                val_ler_res = val_errors_r / len(val_y)
            else:
                val_ler_res = None
            best_val = min([x for x in [val_ler, val_ler_res] if x is not None] + ([best_val] if best_val is not None else []))
            np.savez_compressed(run_dir / "validation_evidence.npz", detectors=val_d, observable=val_y,
                                pymatching=val_match, direct=val_direct,
                                residual=val_residual if val_residual is not None else np.empty((0,), dtype=np.uint8))

        checkpoint_requested = (run_dir / "checkpoint.request").exists()
        do_checkpoint = (step % cfg["checkpoint_frequency_steps"] == 0 or step == steps_total
                         or bool(request) or checkpoint_requested)
        if do_checkpoint:
            save_checkpoint(checkpoint_path, cfg_hash=cfg_hash, direct=direct, residual=residual,
                            opt_direct=opt_direct, opt_residual=opt_residual, scaler=scaler,
                            step=step, processed=processed, losses=loss_history,
                            best_val=best_val, model_seed=model_seed)
            if (run_dir / "checkpoint.request").exists():
                (run_dir / "checkpoint.request").unlink(missing_ok=True)
        if request in ("pause", "stop"):
            stop_file.unlink(missing_ok=True)
            emit({"type": "paused" if request == "pause" else "stopped", "status": "paused" if request == "pause" else "stopped",
                  "run_id": run_dir.name, "summary": {"checkpoint": str(checkpoint_path),
                                                        "training_samples_processed": processed,
                                                        "completed_steps": step}})
            return

        now = time.perf_counter()
        if do_validation or do_checkpoint or now - last_emit >= 1.0 or step == steps_total:
            elapsed = max(1e-9, now - started)
            speed = processed / elapsed
            remain = max(0, cfg["training_shots"] - processed)
            event = {"type": "progress", "status": "running", "run_id": run_dir.name,
                     "generated_training_shots": progress["generated_training"], "training_samples_processed": processed,
                     "training_sample_passes": processed * (2 if residual is not None else 1),
                     "total_training_shots": cfg["training_shots"], "generated_validation_shots": len(val_y),
                     "generated_test_shots": 0, "step": step, "steps_total": steps_total,
                     "epoch": 1, "training_pass": 1, "train_loss": loss_value,
                     "validation_ler": val_ler,
                     "validation_residual_ler": val_ler_res if do_validation else None,
                     "pymatching_validation_ler": baseline_val_ler,
                     "validation_shots": len(val_y), "throughput_shots_s": speed,
                     "elapsed_seconds": elapsed, "eta_seconds": remain / max(1e-9, speed),
                     "device": str(device), "mixed_precision": amp_enabled,
                     "cuda_training_verified": cuda_training_verified,
                     "cuda_device_name": cuda_device_name, "python_executable": sys.executable,
                     "gpu_telemetry": device_snapshot(), "model_selection": cfg["model_selection"],
                     "checkpoint_saved": do_checkpoint,
                     "phase": "training", "total_shots": total_shots,
                     "completed_shots": processed + progress["decoded_validation"],
                     "generated_shots": progress["generated_training"] + progress["generated_validation"],
                     "processed_shots": processed + progress["decoded_validation"],
                     "progress_percent": (processed + progress["decoded_validation"]) * 100.0 / total_shots,
                     "phase_completed_shots": processed, "phase_total_shots": cfg["training_shots"],
                     "throughput_shots_s": (processed + progress["decoded_validation"]) / max(elapsed, 1e-9),
                     "stage_counts": {"simulation": progress["generated_training"] + progress["generated_validation"],
                                      "decoding": progress["decoded_training"] + progress["decoded_validation"],
                                      "analysis": progress["analysis_completed"]}}
            remaining_work = max(0, total_shots - int(event["processed_shots"]))
            event["eta_seconds"] = (remaining_work / event["throughput_shots_s"]
                                    if event["throughput_shots_s"] > 0 else None)
            emit(event)
            last_emit = now

    # Test is generated and read only after all gradient updates are complete.
    test_d, test_y, test_match, test_generation_metrics = split_samples(circuit, matching, plan, "test",
                                                                         cfg["test_shots"], cfg["batch_size"],
                                                                         progress_callback=split_progress)
    progress["decoded_test"] = len(test_y)
    progress["generated_test"] = len(test_y)
    emit_progress("analysis", 0, 1, "test")
    direct_pred, residual_pred, test_inference_metrics = evaluate_models(test_d, test_y, test_match, direct, residual, device)
    predictions = {"identity_no_decode": np.zeros_like(test_y, dtype=np.uint8),
                   "pymatching": test_match, "direct_neural": direct_pred}
    if residual_pred is not None:
        predictions["pymatching_neural_residual"] = residual_pred
    comparison = compare_predictions(test_y, predictions)
    progress["analysis_completed"] = 1
    emit_progress("analysis", 1, 1, "test")
    evidence_path = run_dir / "test_evidence.npz"
    np.savez_compressed(evidence_path, detectors=test_d, observable=test_y,
                        identity_no_decode=predictions["identity_no_decode"], pymatching=test_match,
                        direct_neural=direct_pred,
                        pymatching_neural_residual=residual_pred if residual_pred is not None else np.empty((0,), dtype=np.uint8))
    test_evidence_sha256 = sha256_file(evidence_path)
    dashboard_source_names = ("configuration.py", "models.py", "simulator.py", "worker.py",
                              "seed_protocol.py", "qshift_stats.py", "telemetry.py")
    dashboard_source_hashes = {name: sha256_file(Path(__file__).with_name(name)) for name in dashboard_source_names}
    identity = model_identity(circuit, dem)
    metadata = {
        "run_id": run_dir.name, "config": cfg, "config_sha256": cfg_hash,
        "seed_plan": plan, "seed_screen": screen, "noise_record": noise_record,
        "circuit_sha256": identity["circuit_sha256"], "dem_sha256": identity["dem_sha256"],
        "detector_count": identity["detectors"], "observable_count": identity["observables"],
        "phase2b_fixed_decoder_index": fixed_index,
        "phase2b_fixed_decoder_selection": "Calibration-selected fixed model from archived Phase 2B CALIBRATION_SELECTION.json; X memory index 0, Z memory index 2.",
        "phase2b_bank_records": bank_records,
        "dem_approximation_note": identity["noise_semantics"],
        "software": {"python": sys.version.split()[0], "torch": torch.__version__,
                     "stim": identity["stim_version"], "pymatching": identity["pymatching_version"],
                     "numpy": np.__version__},
        "python_executable": sys.executable,
        "device": str(device), "cuda_available": torch.cuda.is_available(),
        "cuda_device_name": cuda_device_name, "cuda_training_verified": cuda_training_verified,
        "amp_enabled": amp_enabled, "metrics": comparison,
        "test_evidence_path": str(evidence_path.relative_to(run_dir)),
        "test_evidence_sha256": test_evidence_sha256,
        "checkpoint_sha256": sha256_file(checkpoint_path) if checkpoint_path.is_file() else None,
        "dashboard_source_hashes": dashboard_source_hashes,
        "timings": {**test_generation_metrics, **test_inference_metrics,
                    "validation_stim_generation_seconds": val_generation_metrics["stim_generation_seconds"],
                    "validation_pymatching_decode_seconds": val_generation_metrics["pymatching_decode_seconds"]},
        "test_access_policy": "Test samples were not generated or evaluated until after training completed.",
        "inference_claim": "Neural models are static decoders trained for this configured data distribution; this run does not implement adaptive noise-regime selection.",
    }
    atomic_json_write(metadata, run_dir / "run_metadata.json")
    if device.type == "cuda":
        gpu_peak = int(torch.cuda.max_memory_allocated(0))
        gpu_reserved = int(torch.cuda.max_memory_reserved(0))
    else:
        gpu_peak, gpu_reserved = None, None
    summary = {"status": "completed", "metrics": comparison,
               "generated_training_shots": processed, "generated_validation_shots": len(val_y),
               "generated_test_shots": len(test_y), "training_samples_processed": processed,
               "training_sample_passes": processed * (2 if residual is not None else 1),
               "test_evidence_path": str(evidence_path), "metadata_path": str(run_dir / "run_metadata.json"),
               "gpu_peak_allocated_bytes": gpu_peak, "gpu_peak_reserved_bytes": gpu_reserved,
               "device": str(device), "cuda_available": torch.cuda.is_available(),
               "cuda_device_name": cuda_device_name, "cuda_training_verified": cuda_training_verified,
               "python_executable": sys.executable, "torch_version": torch.__version__,
               "model_seed": model_seed, "validation_baseline_ler": baseline_val_ler,
               "total_elapsed_seconds": time.perf_counter() - started}
    emit({"type": "completed", "status": "completed", "run_id": run_dir.name,
          "summary": summary, "metrics": comparison,
          "generated_training_shots": processed, "training_samples_processed": processed,
          "generated_validation_shots": len(val_y), "generated_test_shots": len(test_y),
          "training_sample_passes": summary["training_sample_passes"],
          "gpu_peak_allocated_bytes": gpu_peak, "gpu_peak_reserved_bytes": gpu_reserved,
          "device": str(device), "cuda_available": torch.cuda.is_available(),
          "cuda_device_name": cuda_device_name, "cuda_training_verified": cuda_training_verified,
          "python_executable": sys.executable, "torch_version": torch.__version__})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    try:
        run(args.config.resolve(), args.run_dir.resolve(), args.resume)
    except Exception as exc:
        detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        emit({"type": "failed", "status": "failed", "run_id": args.run_dir.name,
              "error": str(exc), "traceback": detail[-12000:]})
        raise


if __name__ == "__main__":
    main()

