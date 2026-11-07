"""Training, validation, and checkpoint routines for Q-SHIFT local development.

This module exposes only train/monitor/calibration/threshold/final-development
splits. There is deliberately no test split or test sampler.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

from models import DirectMLP
from structured_decoder import (DetectorGridEncoder, PositionPreservingConv3DDecoder,
                                StructuredConv3DDecoder)

REGIMES_ALL = ("x_biased", "balanced", "z_biased")


class ResidualPositionCNN(nn.Module):
    """Predict a residual parity bit from syndrome geometry and PM bit."""
    def __init__(self, coords, channels=4, head_width=16, dropout=0.05):
        super().__init__()
        self.geometry = DetectorGridEncoder(coords)
        self.features = nn.Sequential(
            nn.Conv3d(2, channels, 3, padding=1), nn.GELU(),
            nn.Conv3d(channels, channels * 2, 3, padding=1), nn.GELU(),
            nn.Dropout3d(dropout), nn.Flatten(),
        )
        feature_count = channels * 2 * math.prod(self.geometry.grid_shape)
        self.head = nn.Sequential(nn.Linear(feature_count + 1, head_width), nn.GELU(),
                                  nn.Dropout(dropout), nn.Linear(head_width, 1))

    def forward(self, detectors, pymatching_prediction):
        f = self.features(self.geometry(detectors))
        p = pymatching_prediction.to(dtype=f.dtype, device=f.device).reshape(-1, 1)
        return self.head(torch.cat((f, p), dim=1)).squeeze(-1)


def build_model(name, coords, config):
    t = config["training"]
    if name == "position_flat_cnn":
        return PositionPreservingConv3DDecoder(coords, t["channels_position_cnn"],
                                               t["head_width_position_cnn"], dropout=0.05)
    if name == "balanced_mlp":
        return DirectMLP(40)
    if name == "pooled_cnn16_capacity_control":
        return StructuredConv3DDecoder(coords, channels=t["channels_pooled_control"], dropout=0.05)
    if name == "residual_position_cnn":
        return ResidualPositionCNN(coords, t["channels_position_cnn"], t["head_width_position_cnn"], dropout=0.05)
    raise ValueError(f"Unknown model {name}")


def target_for(data, residual: bool):
    y = np.asarray(data["observable"], dtype=np.uint8)
    if not residual:
        return y
    return np.bitwise_xor(y, np.asarray(data["pymatching"], dtype=np.uint8))


def balanced_epoch_batches(data_by_regime, sizes, batch_size, rng, residual=False, shuffle_rng=None):
    jobs = []
    for regime, data in data_by_regime.items():
        labels = target_for(data, residual)[:int(sizes[regime])]
        positives, negatives = np.flatnonzero(labels == 1), np.flatnonzero(labels == 0)
        if not len(positives) or not len(negatives):
            raise RuntimeError(f"Balanced sampler cannot run: missing a class in {regime} training prefix.")
        for start in range(0, len(labels), batch_size):
            count = min(batch_size, len(labels) - start)
            n_pos = (count + 1) // 2
            n_neg = count - n_pos
            ids = np.concatenate((rng.choice(positives, n_pos, replace=len(positives) < n_pos),
                                  rng.choice(negatives, n_neg, replace=len(negatives) < n_neg)))
            rng.shuffle(ids)
            jobs.append((regime, ids.astype(np.int32)))
    (shuffle_rng or rng).shuffle(jobs)
    return [(r, i.tolist()) for r, i in jobs]


def _batch_logits(model, model_name, d, pm, device):
    x = torch.as_tensor(d, dtype=torch.float32, device=device)
    p = torch.as_tensor(pm, dtype=torch.float32, device=device)
    logits = model(x, p) if model_name == "residual_position_cnn" else model(x)
    return logits.float()


def _natural_logit(logits, prevalence):
    p = min(max(float(prevalence), 1e-8), 1.0 - 1e-8)
    return logits + math.log(p / (1.0 - p))


def evaluate_logits(model, model_name, data_by_regime, device, prevalence, residual=False):
    result = {}
    model.eval()
    with torch.inference_mode():
        for regime, data in data_by_regime.items():
            logits = _batch_logits(model, model_name, data["detectors"], data["pymatching"], device)
            logits = _natural_logit(logits, prevalence)
            if not torch.isfinite(logits).all():
                raise FloatingPointError(f"Non-finite logits on {regime} validation stream.")
            result[regime] = logits.detach().cpu().numpy().astype(np.float64)
    return result


def macro_nll(logits_by_regime, data_by_regime, residual=False):
    losses = []
    for regime, logits in logits_by_regime.items():
        y = target_for(data_by_regime[regime], residual).astype(np.float64)
        z = np.clip(np.asarray(logits, dtype=np.float64), -60, 60)
        losses.append(float(np.mean(np.logaddexp(0.0, z) - y * z)))
    return float(np.mean(losses))


def choose_temperature(cal_logits, cal_data, residual=False, grid=None):
    grid = grid or [0.5, 0.7, 0.85, 1.0, 1.2, 1.5, 2.0, 3.0, 4.0]
    scores = []
    for temp in grid:
        by_regime = {r: np.asarray(v) / float(temp) for r, v in cal_logits.items()}
        scores.append((macro_nll(by_regime, cal_data, residual), abs(float(temp) - 1.0), float(temp)))
    return min(scores)[2]


def choose_threshold(probs, threshold_data, residual=False, grid=None):
    grid = grid or [i / 100 for i in range(1, 100)]
    scores = []
    for t in grid:
        lers = []
        for regime, data in threshold_data.items():
            bit = (np.asarray(probs[regime]) >= t).astype(np.uint8)
            pred = np.bitwise_xor(data["pymatching"], bit) if residual else bit
            lers.append(float(np.mean(pred ^ data["observable"])))
        scores.append((float(np.mean(lers)), abs(float(t) - 0.5), float(t)))
    return min(scores)[2]


def confusion(pred, y):
    pred, y = np.asarray(pred, dtype=np.uint8), np.asarray(y, dtype=np.uint8)
    if np.any((pred > 1) | (y > 1)):
        raise ValueError("Confusion inputs must be binary.")
    tp = int(np.sum((pred == 1) & (y == 1))); fp = int(np.sum((pred == 1) & (y == 0)))
    fn = int(np.sum((pred == 0) & (y == 1))); tn = int(np.sum((pred == 0) & (y == 0)))
    return {"tn": tn, "fp": fp, "fn": fn, "tp": tp, "errors": fp + fn,
            "ler": (fp + fn) / len(y), "positive_recall": tp / (tp + fn) if tp + fn else None}


def fit_job(job, root_data, coords, config, device, load_checkpoint, save_checkpoint,
            stop_check, selection_path: Path, predictions_path: Path, final_eval_loader,
            dry_pause_after=None, progress_callback=None):
    """Train/resume a model job; final development labels are touched only last."""
    model_name = job["model"]
    residual = model_name == "residual_position_cnn"
    regimes = tuple(root_data["train"].keys())
    train_sizes = {r: int(job["train_size_per_regime"]) for r in regimes}
    train = {r: {k: v[:train_sizes[r]] for k, v in root_data["train"][r].items()}
             for r in regimes}
    targets = {r: target_for(train[r], residual) for r in regimes}
    total_pos = sum(int(y.sum()) for y in targets.values())
    total_count = sum(len(y) for y in targets.values())
    prevalence = total_pos / total_count
    if not 0 < prevalence < 1:
        raise RuntimeError(f"Invalid training label prevalence {prevalence} for {job['job_id']}.")

    seed = int(job["torch_seed"])
    torch.manual_seed(seed)
    if device.type == "cuda": torch.cuda.manual_seed_all(seed)
    random.seed(seed)
    numpy_rng = np.random.default_rng(int(job["sampling_seed"]))
    shuffle_rng = np.random.default_rng(int(job["shuffle_seed"]))
    model = build_model(model_name, coords, config).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(config["training"]["learning_rate"]),
                                  weight_decay=float(config["training"]["weight_decay"]))
    sched_cfg = config["training"]["scheduler"]
    if sched_cfg.get("type") != "StepLR":
        raise ValueError("Only the frozen StepLR scheduler is supported.")
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer,
        step_size=int(sched_cfg["step_size_epochs"]), gamma=float(sched_cfg["gamma"]))
    state = load_checkpoint(job["job_id"])
    history, best_state, best_nll, best_epoch, patience_count = [], None, float("inf"), None, 0
    epoch, next_batch, epoch_batches, steps, gpu_seconds = 0, 0, None, 0, 0.0
    if state:
        if state.get("job_id") != job["job_id"] or state.get("config_sha256") != job["config_sha256"]:
            raise RuntimeError("Checkpoint belongs to a different job/configuration.")
        model.load_state_dict(state["model_state"])
        optimizer.load_state_dict(state["optimizer_state"])
        if state.get("scheduler_state") is not None:
            scheduler.load_state_dict(state["scheduler_state"])
        epoch, next_batch = int(state["epoch"]), int(state["next_batch"])
        epoch_batches = state["epoch_batches"]
        steps, gpu_seconds = int(state["steps"]), float(state["gpu_seconds"])
        best_state, best_nll = state["best_state"], float(state["best_nll"])
        best_epoch, patience_count, history = state["best_epoch"], int(state["patience_count"]), list(state["history"])
        numpy_rng.bit_generator.state = state["numpy_rng_state"]
        shuffle_rng.bit_generator.state = state["shuffle_rng_state"]
        torch.set_rng_state(state["torch_rng_state"].cpu())
        if device.type == "cuda" and state.get("cuda_rng_state") is not None:
            torch.cuda.set_rng_state_all(state["cuda_rng_state"])
        random.setstate(state["python_rng_state"])
    elif selection_path.exists():
        # Selection is frozen before final evaluation. This branch supports a
        # restart after training/selection has finished but evaluation did not.
        pass

    max_epochs = int(job.get("max_epochs", config["training"]["max_epochs"]))
    batch_size = int(job.get("batch_size", config["training"]["batch_size"]))
    max_steps_per_save = 1 if dry_pause_after is not None else int(config["training"]["checkpoint_every_batches"])
    pause_after = dry_pause_after
    batches_since_save = 0

    def timed_evaluate(label, data, residual_flag):
        nonlocal gpu_seconds
        tic = time.perf_counter()
        out = evaluate_logits(model, model_name, data, device, prevalence, residual_flag)
        if device.type == "cuda":
            torch.cuda.synchronize(device)
            gpu_seconds += time.perf_counter() - tic
        if progress_callback is not None:
            progress_callback({"job_id": job["job_id"], "steps": steps,
                               "gpu_seconds": gpu_seconds, "epoch": epoch,
                               "phase": label})
        return out

    while epoch < max_epochs:
        if epoch_batches is None:
            epoch_batches = balanced_epoch_batches(train, train_sizes, batch_size, numpy_rng, residual, shuffle_rng)
            next_batch = 0
        model.train()
        while next_batch < len(epoch_batches):
            if stop_check():
                save_checkpoint(job["job_id"], _checkpoint_payload(job, state, model, optimizer, epoch,
                    next_batch, epoch_batches, steps, gpu_seconds, best_state, best_nll, best_epoch,
                    patience_count, history, numpy_rng, scheduler, shuffle_rng))
                return {"status": "paused", "job_id": job["job_id"], "steps": steps,
                        "best_epoch": best_epoch, "gpu_seconds": gpu_seconds}
            regime, indices = epoch_batches[next_batch]
            arr = np.asarray(indices, dtype=np.int32)
            d = train[regime]["detectors"][arr]
            pm = train[regime]["pymatching"][arr]
            y = targets[regime][arr].astype(np.float32)
            tic = time.perf_counter()
            optimizer.zero_grad(set_to_none=True)
            logits = _batch_logits(model, model_name, d, pm, device)
            loss = F.binary_cross_entropy_with_logits(logits, torch.as_tensor(y, device=device))
            if not torch.isfinite(loss): raise FloatingPointError("Non-finite training loss.")
            loss.backward()
            if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in model.parameters()):
                raise FloatingPointError("Non-finite gradient; controller stops.")
            optimizer.step()
            if device.type == "cuda":
                torch.cuda.synchronize(device)
                gpu_seconds += time.perf_counter() - tic
            steps += 1; next_batch += 1; batches_since_save += 1
            if progress_callback is not None:
                progress_callback({"job_id": job["job_id"], "steps": steps,
                                   "gpu_seconds": gpu_seconds, "epoch": epoch,
                                   "next_batch": next_batch})
            if batches_since_save >= max_steps_per_save:
                save_checkpoint(job["job_id"], _checkpoint_payload(job, state, model, optimizer, epoch,
                    next_batch, epoch_batches, steps, gpu_seconds, best_state, best_nll, best_epoch,
                    patience_count, history, numpy_rng, scheduler, shuffle_rng))
                batches_since_save = 0
            if pause_after is not None and steps >= pause_after:
                save_checkpoint(job["job_id"], _checkpoint_payload(job, state, model, optimizer, epoch,
                    next_batch, epoch_batches, steps, gpu_seconds, best_state, best_nll, best_epoch,
                    patience_count, history, numpy_rng, scheduler, shuffle_rng))
                return {"status": "paused", "job_id": job["job_id"], "steps": steps,
                        "best_epoch": best_epoch, "gpu_seconds": gpu_seconds}
        monitor_logits = timed_evaluate("monitor", root_data["monitor"], residual)
        nll = macro_nll(monitor_logits, root_data["monitor"], residual)
        if not math.isfinite(nll): raise FloatingPointError("Non-finite monitor NLL.")
        improved = nll < best_nll - 1e-9
        if improved:
            best_nll = nll; best_epoch = epoch + 1; patience_count = 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            patience_count += 1
        history.append({"epoch": epoch + 1, "monitor_nll": nll, "selected": improved})
        scheduler.step()
        epoch += 1; next_batch = 0; epoch_batches = None
        save_checkpoint(job["job_id"], _checkpoint_payload(job, state, model, optimizer, epoch,
            next_batch, epoch_batches, steps, gpu_seconds, best_state, best_nll, best_epoch,
            patience_count, history, numpy_rng, scheduler, shuffle_rng))
        if patience_count >= int(config["training"]["early_stopping_patience"]): break

    if best_state is None: raise RuntimeError("No validation-selected checkpoint exists.")
    model.load_state_dict(best_state)
    if selection_path.exists():
        selection = json.loads(selection_path.read_text(encoding="utf-8"))
        if selection.get("job_id") != job["job_id"] or selection.get("selected_model_state_sha256") != hash_state(best_state):
            raise RuntimeError("Saved selection does not match this model checkpoint.")
        temperature, threshold = float(selection["temperature"]), float(selection["threshold"])
    else:
        calibration = root_data["calibration"]
        cal_logits = timed_evaluate("calibration", calibration, residual)
        temperature = choose_temperature(cal_logits, calibration, residual,
                                        config["calibration_temperature_grid"])
        threshold_data = root_data["threshold_selection"]
        threshold_logits = timed_evaluate("threshold_selection", threshold_data, residual)
        probs = {r: 1.0 / (1.0 + np.exp(-np.clip(threshold_logits[r] / temperature, -60, 60))) for r in regimes}
        threshold = choose_threshold(probs, threshold_data, residual, config["threshold_grid"])
        selection = {"job_id": job["job_id"], "model": model_name, "temperature": temperature,
                     "threshold": threshold, "prevalence": prevalence, "best_epoch": best_epoch,
                     "best_monitor_nll": best_nll,
                     "selection_data": "monitor for checkpoint; calibration for temperature; threshold_selection for decision threshold",
                     "selected_model_state_sha256": hash_state(best_state), "final_development_evaluation_accessed": False}
        atomic_json(selection, selection_path)
    # The final development partition is first read after all model/calibration/
    # threshold choices are frozen in selection_path.
    if stop_check():
        return {"status": "paused", "job_id": job["job_id"], "steps": steps,
                "best_epoch": best_epoch, "gpu_seconds": gpu_seconds,
                "selection_frozen": selection_path.exists()}
    final_data = final_eval_loader()
    final_logits = timed_evaluate("final_development_evaluation", final_data, residual)
    final_probs = {r: 1.0 / (1.0 + np.exp(-np.clip(final_logits[r] / temperature, -60, 60))) for r in regimes}
    predictions, per_regime = {}, {}
    for regime in regimes:
        p = (final_probs[regime] >= threshold).astype(np.uint8)
        pred = np.bitwise_xor(final_data[regime]["pymatching"], p) if residual else p
        y = final_data[regime]["observable"]
        pm = final_data[regime]["pymatching"]
        wrong, pm_wrong = pred ^ y, pm ^ y
        per_regime[regime] = {**confusion(pred, y),
            "pymatching_errors": int(pm_wrong.sum()), "pymatching_ler": float(pm_wrong.mean()),
            "candidate_only": int(np.sum((wrong == 1) & (pm_wrong == 0))),
            "pymatching_only": int(np.sum((wrong == 0) & (pm_wrong == 1))),
            "paired_prediction_disagreements": int(np.sum(pred != pm))}
        predictions[f"observable__{regime}"] = y
        predictions[f"pymatching__{regime}"] = pm
        predictions[f"prediction__{regime}"] = pred
        predictions[f"probability__{regime}"] = final_probs[regime].astype(np.float32)
    save_npz_atomic(predictions_path, predictions)
    result = {"status": "completed", **selection, "final_development_evaluation_accessed": True,
              "shots": sum(len(final_data[r]["observable"]) for r in regimes), "per_regime": per_regime,
              "equal_regime_ler": float(np.mean([per_regime[r]["ler"] for r in regimes])),
              "equal_regime_pymatching_ler": float(np.mean([per_regime[r]["pymatching_ler"] for r in regimes])),
              "paired_ler_difference": float(np.mean([per_regime[r]["ler"]-per_regime[r]["pymatching_ler"] for r in regimes])),
              "candidate_only": sum(per_regime[r]["candidate_only"] for r in regimes),
              "pymatching_only": sum(per_regime[r]["pymatching_only"] for r in regimes),
              "parameter_count": sum(p.numel() for p in model.parameters()), "steps": steps,
              "gpu_training_seconds": gpu_seconds, "history": history}
    return result


def _checkpoint_payload(job, prior, model, optimizer, epoch, next_batch, epoch_batches, steps,
                        gpu_seconds, best_state, best_nll, best_epoch, patience_count, history, rng, scheduler,
                        shuffle_rng):
    return {"job_id": job["job_id"], "config_sha256": job["config_sha256"],
            "model_state": {k: v.detach().cpu().clone() for k, v in model.state_dict().items()},
            "optimizer_state": optimizer.state_dict(), "scheduler_state": scheduler.state_dict(),
            "epoch": epoch, "next_batch": next_batch,
            "epoch_batches": epoch_batches, "steps": steps, "gpu_seconds": gpu_seconds,
            "best_state": best_state, "best_nll": best_nll, "best_epoch": best_epoch,
            "patience_count": patience_count, "history": history,
            "numpy_rng_state": rng.bit_generator.state, "torch_rng_state": torch.get_rng_state().cpu(),
            "shuffle_rng_state": shuffle_rng.bit_generator.state,
            "cuda_rng_state": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None,
            "python_rng_state": random.getstate()}


def hash_state(state):
    h = hashlib.sha256()
    for key in sorted(state):
        h.update(key.encode()); h.update(state[key].detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def save_npz_atomic(path, arrays):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as f:
        np.savez_compressed(f, **arrays); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_json(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)
