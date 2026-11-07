"""Bounded multi-root development comparison of position-aware CNN variants.

This script has no test-stream sampler. It freezes config, seeds, and source
hashes before any fresh Stim shot is generated and refuses to overwrite a run.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import sys
import time
from pathlib import Path

import numpy as np
import psutil
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "dashboard"))

from models import DirectMLP
from seed_protocol import MAX_STIM_SEED, historical_seeds
from simulator import decode_matching, prepare, sample
from structured_decoder import (StructuredConv3DDecoder, PositionPreservingConv3DDecoder,
                                CoordinateChannelConv3DDecoder)

REGIMES = ("x_biased", "balanced", "z_biased")
STRATEGIES = ("balanced_minibatches", "weighted_bce")
ARCHS = ("pooled_cnn8", "pooled_cnn16_capacity_control", "position_flat_cnn",
         "coordinate_channel_cnn", "balanced_mlp")
TRAIN_SHOTS = 3000
VALIDATION_SHOTS = 3000
BATCH_SIZE = 256
MAX_EPOCHS = 12
PATIENCE = 4
MAX_RUNTIME_SECONDS = 1800
BASE_NOISE = {"distance": 3, "rounds": 5, "memory_basis": "z", "gate_p": 0.003,
              "measurement_p": 0.003, "bias_ratio": 10.0}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_config_and_freeze():
    if (OUT / "freeze.json").exists() or (OUT / "development_samples.npz").exists():
        raise RuntimeError("This output already contains a frozen run; refusing to overwrite it.")
    config = {
        "status": "prospective development-only freeze",
        "circuit": {**BASE_NOISE, "noise_regimes": list(REGIMES)},
        "train_shots_per_regime_per_root": TRAIN_SHOTS,
        "validation_shots_per_regime_per_root": VALIDATION_SHOTS,
        "validation_partition": "equal thirds by deterministic per-root permutation: checkpoint-selection, temperature-calibration, threshold-selection",
        "batch_size": BATCH_SIZE, "max_epochs": MAX_EPOCHS, "early_stopping_patience": PATIENCE,
        "strategies": list(STRATEGIES), "architectures": list(ARCHS),
        "position_model": {"channels": 4, "head_width": 16, "dropout": 0.05},
        "coordinate_channels": ["syndrome", "occupancy", "normalized_time", "normalized_y", "normalized_x"],
        "temperature_grid": [0.5, 0.7, 0.85, 1.0, 1.2, 1.5, 2.0, 3.0, 4.0],
        "threshold_grid": [round(x, 2) for x in np.arange(0.01, 1.0, 0.01)],
        "model_selection": "minimum mean per-regime validation NLL on checkpoint-selection partition; ties broken by lower equal-regime LER then earlier epoch",
        "threshold_selection": "minimum equal-regime LER on the disjoint threshold-selection validation partition; ties closest to 0.5 then lower threshold",
        "primary_comparison": "position_flat_cnn and coordinate_channel_cnn versus pooled_cnn8 and balanced_mlp, paired on identical per-root shots",
        "test_access": "none; no test samples generated or opened",
        "runtime_limit_seconds": MAX_RUNTIME_SECONDS,
        "uncertainty": "root-level paired differences across three independent development roots; t interval with 2 df, descriptive feasibility only",
        "probability_calibration": "temperature-only grid fit on the distinct calibration partition; report calibration metrics on calibration and threshold partitions separately",
    }
    inventory = make_seed_inventory()
    if not inventory["passed"]:
        raise RuntimeError(f"Seed collision screen failed: {inventory['collisions']}")
    atomic_json(config, OUT / "config.json")
    atomic_json(inventory, OUT / "seed_inventory.json")
    source_paths = [
        OUT / "run_experiment.py",
        ROOT / "dashboard/structured_decoder.py",
        ROOT / "dashboard/models.py",
        ROOT / "dashboard/simulator.py",
        ROOT / "dashboard/structured_training.py",
        ROOT / "dashboard/tests/test_structured_training.py",
        ROOT / "outputs/neural_decoder_diagnostic/root_cause_analysis/ROOT_CAUSE_REPORT.md",
        ROOT / "outputs/neural_decoder_diagnostic/root_cause_analysis/SAVED_EVIDENCE_RECOMPUTATION.json",
    ]
    freeze = {"status": "frozen before new Stim sampling", "config_sha256": sha(OUT / "config.json"),
              "seed_inventory_sha256": sha(OUT / "seed_inventory.json"),
              "source_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p) for p in source_paths},
              "sampling_started": False, "created_unix": time.time()}
    atomic_json(freeze, OUT / "freeze.json")
    return config, inventory, freeze


def make_seed_inventory():
    batch_count_train = math.ceil(TRAIN_SHOTS / BATCH_SIZE)
    batch_count_val = math.ceil(VALIDATION_SHOTS / BATCH_SIZE)
    streams = []
    all_seeds = []
    for replicate in range(3):
        for split, root_base, count in (("train", 1_200_000_001, batch_count_train),
                                        ("validation", 1_400_000_001, batch_count_val)):
            for ri, regime in enumerate(REGIMES):
                root = root_base + replicate * 1_000_000 + ri * 20_000
                seeds = list(range(root, root + count))
                streams.append({"replicate": replicate, "split": split, "regime": regime,
                                "shots": TRAIN_SHOTS if split == "train" else VALIDATION_SHOTS,
                                "batch_size": BATCH_SIZE, "root": root, "seeds": seeds})
                all_seeds.extend(seeds)
    fits = []
    for replicate in range(3):
        for ai, arch in enumerate(ARCHS):
            for si, strategy in enumerate(STRATEGIES):
                root = 1_600_000_001 + replicate * 10_000 + ai * 100 + si * 10
                fits.append({"replicate": replicate, "architecture": arch, "strategy": strategy,
                             "torch_seed": root, "sampling_seed": root + 1, "shuffle_seed": root + 2})
                all_seeds.extend((root, root + 1, root + 2))
    partition_seeds = [1_800_000_001 + i for i in range(3)]
    diagnostic_seeds = [1_700_000_001 + i for i in range(3)]
    all_seeds.extend(partition_seeds + diagnostic_seeds)
    historical = historical_seeds()
    try:
        from structured_protocol import build_inventory
        from structured_training import inventory_seed_values
        prepared = inventory_seed_values(build_inventory())
    except Exception as exc:
        raise RuntimeError(f"Could not screen against prepared protocol inventory: {exc}") from exc
    collisions = {
        "within_new_inventory": sorted(s for s in set(all_seeds) if all_seeds.count(s) > 1),
        "historical": sorted(set(all_seeds) & historical),
        "prepared_protocol": sorted(set(all_seeds) & prepared),
        "outside_stim_seed_range": [s for s in all_seeds if not 1 <= s <= MAX_STIM_SEED],
        "train_validation_overlap": [],
    }
    train_values = {s for st in streams if st["split"] == "train" for s in st["seeds"]}
    val_values = {s for st in streams if st["split"] == "validation" for s in st["seeds"]}
    collisions["train_validation_overlap"] = sorted(train_values & val_values)
    return {"allocation": "three independent train/validation roots; per-batch Stim seeds; separate model, batch-sampling, shuffle, partition, and circuit-diagnostic RNG streams",
            "replicates": 3, "streams": streams, "model_streams": fits,
            "partition_seeds": partition_seeds, "diagnostic_seeds": diagnostic_seeds,
            "unique_seed_count": len(set(all_seeds)), "proposed_seed_count": len(all_seeds),
            "recoverable_historical_seed_values_checked": len(historical),
            "prepared_protocol_seed_values_checked": len(prepared), "collisions": collisions,
            "passed": not any(collisions.values()),
            "test_stream": "not allocated or sampled in this development study"}


def build_circuits(config, diagnostic_seeds):
    envs, coords, fingerprint = {}, None, {}
    for ri, regime in enumerate(REGIMES):
        circuit, noise, dem, matching, selected, _ = prepare({**BASE_NOISE, "noise_regime": regime, "device": "cpu"})
        if (circuit.num_detectors, circuit.num_observables, selected) != (40, 1, 2):
            raise RuntimeError(f"Invalid frozen circuit/decoder structure for {regime}.")
        current = circuit.get_detector_coordinates()
        if coords is None:
            coords = current
        elif coords != current:
            raise RuntimeError("Detector coordinates vary across generating regimes.")
        d0, y0 = circuit.without_noise().compile_detector_sampler(seed=diagnostic_seeds[ri]).sample(
            shots=32, separate_observables=True)
        if np.any(d0) or np.any(y0):
            raise RuntimeError(f"Noiseless circuit check failed for {regime}.")
        envs[regime] = {"circuit": circuit, "matching": matching}
        fingerprint[regime] = {"noise_record": noise, "dem_sha256": hashlib.sha256(str(dem).encode()).hexdigest(),
                               "circuit_sha256": hashlib.sha256(str(circuit).encode()).hexdigest(),
                               "detectors": circuit.num_detectors, "observables": circuit.num_observables,
                               "fixed_decoder_index": selected}
    return envs, coords, fingerprint


def generate_split(envs, inventory, replicate, split):
    result = {}
    for regime in REGIMES:
        item = next(s for s in inventory["streams"] if s["replicate"] == replicate and
                    s["split"] == split and s["regime"] == regime)
        n = int(item["shots"])
        ds, ys, ps = [], [], []
        for start in range(0, n, BATCH_SIZE):
            batch = min(BATCH_SIZE, n - start)
            seed = item["root"] + start // BATCH_SIZE
            d, y = sample(envs[regime]["circuit"], seed, batch)
            pred = decode_matching(envs[regime]["matching"], d)
            if d.shape != (batch, 40) or y.shape != (batch,) or pred.shape != (batch,):
                raise RuntimeError("Invalid detector/observable/matching array alignment.")
            if any(np.any((a != 0) & (a != 1)) for a in (d, y, pred)):
                raise RuntimeError("Nonbinary labels or detector samples detected.")
            ds.append(d); ys.append(y); ps.append(pred)
        result[regime] = {"detectors": np.concatenate(ds), "observable": np.concatenate(ys),
                          "pymatching": np.concatenate(ps)}
    return result


def build_model(arch, coords):
    if arch == "pooled_cnn8":
        return StructuredConv3DDecoder(coords, channels=8, dropout=0.05)
    if arch == "pooled_cnn16_capacity_control":
        return StructuredConv3DDecoder(coords, channels=16, dropout=0.05)
    if arch == "position_flat_cnn":
        return PositionPreservingConv3DDecoder(coords, channels=4, head_width=16, dropout=0.05)
    if arch == "coordinate_channel_cnn":
        return CoordinateChannelConv3DDecoder(coords, channels=4, head_width=16, dropout=0.05)
    if arch == "balanced_mlp":
        return DirectMLP(detector_count=40)
    raise ValueError(arch)


def natural_logit(logits, strategy, positive_weight, train_prevalence):
    if strategy == "weighted_bce":
        return logits - math.log(positive_weight)
    # Balanced minibatches impose a 50:50 training prior. Restore the natural
    # training prior before interpreting sigmoid outputs as posterior scores.
    return logits + math.log(train_prevalence / (1.0 - train_prevalence))


def val_logits(model, data, device, strategy, positive_weight, train_prevalence):
    model.eval()
    out = {}
    with torch.inference_mode():
        for regime in REGIMES:
            d = data[regime]["detectors"]
            x = torch.as_tensor(d, dtype=torch.float32, device=device)
            logits = model(x).float()
            logits = natural_logit(logits, strategy, positive_weight, train_prevalence)
            if not torch.isfinite(logits).all():
                raise FloatingPointError("Non-finite validation logits.")
            out[regime] = logits.detach().cpu().numpy().astype(np.float64)
    return out


def make_batches(data, strategy, batch_size, rng):
    jobs = []
    for regime in REGIMES:
        y = data[regime]["observable"]
        if strategy == "weighted_bce":
            order = rng.permutation(len(y))
            batches = [order[i:i + batch_size] for i in range(0, len(y), batch_size)]
        else:
            pos, neg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
            if len(pos) == 0 or len(neg) == 0:
                raise RuntimeError(f"Balanced sampling impossible in {regime}: missing a class.")
            batches = []
            for _ in range(math.ceil(len(y) / batch_size)):
                half = batch_size // 2
                ids = np.concatenate((rng.choice(pos, half, replace=len(pos) < half),
                                      rng.choice(neg, batch_size - half, replace=len(neg) < batch_size - half)))
                rng.shuffle(ids)
                batches.append(ids)
        jobs.extend((regime, ids) for ids in batches)
    rng.shuffle(jobs)
    return jobs


def equal_regime_nll(logit_map, data):
    values = []
    for regime in REGIMES:
        y = data[regime]["observable"].astype(np.float64)
        l = np.clip(logit_map[regime], -60, 60)
        values.append(float(np.mean(np.logaddexp(0.0, l) - y * l)))
    return float(np.mean(values))


def confusion_and_error(pred, labels):
    p = np.asarray(pred, dtype=np.uint8); y = np.asarray(labels, dtype=np.uint8)
    tp = int(np.sum((p == 1) & (y == 1))); fp = int(np.sum((p == 1) & (y == 0)))
    fn = int(np.sum((p == 0) & (y == 1))); tn = int(np.sum((p == 0) & (y == 0)))
    return {"tn": tn, "fp": fp, "fn": fn, "tp": tp,
            "positive_recall": tp / (tp + fn) if tp + fn else None,
            "logical_errors": fp + fn, "logical_error_rate": (fp + fn) / len(y),
            "predicted_positive_rate": float(np.mean(p))}


def calibrate_temperature(logits, labels):
    y = np.asarray(labels, dtype=np.float64)
    candidates = [0.5, 0.7, 0.85, 1.0, 1.2, 1.5, 2.0, 3.0, 4.0]
    rows = []
    for temp in candidates:
        z = np.clip(np.asarray(logits, dtype=np.float64) / temp, -60, 60)
        nll = float(np.mean(np.logaddexp(0.0, z) - y * z))
        rows.append((nll, abs(temp - 1.0), temp))
    return min(rows)[2]


def prob_metrics(prob, labels):
    p = np.clip(np.asarray(prob, dtype=np.float64), 1e-9, 1 - 1e-9)
    y = np.asarray(labels, dtype=np.float64)
    nll = float(np.mean(-y * np.log(p) - (1 - y) * np.log(1 - p)))
    brier = float(np.mean((p - y) ** 2))
    ece = 0.0
    for lo in np.linspace(0, 0.9, 10):
        hi = lo + 0.1
        mask = (p >= lo) & ((p < hi) if hi < 1 else (p <= hi))
        if np.any(mask):
            ece += float(mask.mean() * abs(p[mask].mean() - y[mask].mean()))
    return {"nll": nll, "brier": brier, "ece_10bin": ece}


def fit_one(data_train, data_val, coords, spec, model_seed, sampling_seed, shuffle_seed, device, started):
    torch.manual_seed(model_seed)
    np.random.seed(model_seed % (2**32))
    random.seed(model_seed)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(model_seed)
    model = build_model(spec["architecture"], coords).to(device)
    parameter_count = sum(int(p.numel()) for p in model.parameters())
    total_pos = sum(int(data_train[r]["observable"].sum()) for r in REGIMES)
    total_n = sum(len(data_train[r]["observable"]) for r in REGIMES)
    prevalence = total_pos / total_n
    if not 0.0 < prevalence < 1.0:
        raise RuntimeError(f"Invalid direct-label training prevalence: {prevalence}")
    pos_weight = (1.0 - prevalence) / prevalence
    pw = torch.tensor(pos_weight, dtype=torch.float32, device=device) if spec["strategy"] == "weighted_bce" else None
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.003, weight_decay=1e-4)
    sampling_rng = np.random.default_rng(sampling_seed)
    shuffle_rng = random.Random(shuffle_seed)
    best_state, best_nll, best_ler, best_epoch = None, float("inf"), float("inf"), None
    history, patience = [], 0
    for epoch in range(1, MAX_EPOCHS + 1):
        if time.perf_counter() - started > MAX_RUNTIME_SECONDS:
            raise TimeoutError("30-minute experiment budget reached; runner stopped before further training.")
        model.train()
        epoch_losses = []
        jobs = make_batches(data_train, spec["strategy"], BATCH_SIZE, sampling_rng)
        shuffle_rng.shuffle(jobs)
        for regime, ids in jobs:
            d = data_train[regime]["detectors"][ids]
            y = data_train[regime]["observable"][ids].astype(np.float32)
            x_t = torch.as_tensor(d, dtype=torch.float32, device=device)
            y_t = torch.as_tensor(y, dtype=torch.float32, device=device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(x_t).float()
            loss = F.binary_cross_entropy_with_logits(logits, y_t, pos_weight=pw)
            if not torch.isfinite(loss):
                raise FloatingPointError("Non-finite training loss; stopped immediately.")
            loss.backward()
            if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in model.parameters()):
                raise FloatingPointError("Non-finite model gradient; stopped immediately.")
            optimizer.step()
            if device.type == "cuda":
                torch.cuda.synchronize(device)
            epoch_losses.append(float(loss.detach().cpu()))
        monitor_logits = val_logits(model, data_val["monitor"], device, spec["strategy"], pos_weight, prevalence)
        nll = equal_regime_nll(monitor_logits, data_val["monitor"])
        monitor_ler = []
        for regime in REGIMES:
            pred = (1.0 / (1.0 + np.exp(-np.clip(monitor_logits[regime], -60, 60))) >= 0.5).astype(np.uint8)
            monitor_ler.append(float(np.mean(pred ^ data_val["monitor"][regime]["observable"])))
        ler = float(np.mean(monitor_ler))
        improved = nll < best_nll - 1e-8 or (abs(nll - best_nll) <= 1e-8 and ler < best_ler)
        if improved:
            best_nll, best_ler, best_epoch = nll, ler, epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            patience = 0
        else:
            patience += 1
        history.append({"epoch": epoch, "mean_train_loss": float(np.mean(epoch_losses)),
                        "validation_monitor_nll": nll, "validation_monitor_ler_at_0_5": ler,
                        "checkpoint_selected": improved})
        if patience >= PATIENCE:
            break
    if best_state is None:
        raise RuntimeError("No finite best-validation checkpoint was produced.")
    model.load_state_dict(best_state)
    model.eval()
    cal_logits = val_logits(model, data_val["calibration"], device, spec["strategy"], pos_weight, prevalence)
    flat_cal_y = np.concatenate([data_val["calibration"][r]["observable"] for r in REGIMES])
    flat_cal_l = np.concatenate([cal_logits[r] for r in REGIMES])
    temp = calibrate_temperature(flat_cal_l, flat_cal_y)
    threshold_logits = val_logits(model, data_val["threshold"], device, spec["strategy"], pos_weight, prevalence)
    threshold_probs = {r: 1.0 / (1.0 + np.exp(-np.clip(threshold_logits[r] / temp, -60, 60))) for r in REGIMES}
    candidates = [round(float(t), 2) for t in np.arange(0.01, 1.0, 0.01)]
    threshold_scores = []
    for threshold in candidates:
        ler = np.mean([np.mean((threshold_probs[r] >= threshold).astype(np.uint8) ^
                               data_val["threshold"][r]["observable"]) for r in REGIMES])
        threshold_scores.append((float(ler), abs(threshold - 0.5), threshold))
    selected_threshold = min(threshold_scores)[2]
    predictions = {}
    per_regime = {}
    flat_base_cal, flat_cal_y, flat_temp_cal = [], [], []
    for r in REGIMES:
        base_cal = 1.0 / (1.0 + np.exp(-np.clip(cal_logits[r], -60, 60)))
        calibrated_cal = 1.0 / (1.0 + np.exp(-np.clip(cal_logits[r] / temp, -60, 60)))
        flat_base_cal.append(base_cal); flat_temp_cal.append(calibrated_cal)
        d = data_val["threshold"][r]
        prob = threshold_probs[r].astype(np.float32)
        pred = (prob >= selected_threshold).astype(np.uint8)
        counts = confusion_and_error(pred, d["observable"])
        wrong, fixed_wrong = pred ^ d["observable"], d["pymatching"] ^ d["observable"]
        counts.update({"pymatching_errors": int(fixed_wrong.sum()),
                       "pymatching_ler": float(fixed_wrong.mean()),
                       "pymatching_confusion": confusion_and_error(d["pymatching"], d["observable"]),
                       "candidate_only": int(np.count_nonzero((wrong == 1) & (fixed_wrong == 0))),
                       "pymatching_only": int(np.count_nonzero((wrong == 0) & (fixed_wrong == 1))),
                       "paired_prediction_disagreements": int(np.count_nonzero(pred != d["pymatching"])),
                       "paired_ler_difference": float(wrong.mean() - fixed_wrong.mean())})
        per_regime[r] = counts
        predictions[f"probability__{r}"] = prob
        predictions[f"prediction__{r}"] = pred
    cal_y = np.concatenate([data_val["calibration"][r]["observable"] for r in REGIMES])
    base_cal_all = np.concatenate(flat_base_cal)
    temp_cal_all = np.concatenate(flat_temp_cal)
    calibration_metrics = {"uncalibrated_on_calibration_partition": prob_metrics(base_cal_all, cal_y),
                           "temperature_calibrated_on_calibration_partition": prob_metrics(temp_cal_all, cal_y)}
    # The threshold partition is not used to fit temperature; report probability
    # calibration there as the cross-partition check.
    threshold_y = np.concatenate([data_val["threshold"][r]["observable"] for r in REGIMES])
    threshold_p = np.concatenate([threshold_probs[r] for r in REGIMES])
    calibration_metrics["temperature_calibrated_on_threshold_partition"] = prob_metrics(threshold_p, threshold_y)
    total_errors = sum(v["logical_errors"] for v in per_regime.values())
    total_pm_errors = sum(v["pymatching_errors"] for v in per_regime.values())
    record = {"architecture": spec["architecture"], "strategy": spec["strategy"],
              "parameter_count": parameter_count, "best_epoch": best_epoch,
              "best_monitor_nll": best_nll, "best_monitor_equal_regime_ler_at_0_5": best_ler,
              "natural_training_positive_prevalence": prevalence, "weighted_bce_pos_weight": pos_weight if spec["strategy"] == "weighted_bce" else None,
              "logit_prior_correction": "subtract log(pos_weight)" if spec["strategy"] == "weighted_bce" else "add logit(natural_train_prevalence)",
              "temperature": temp, "selected_threshold": selected_threshold,
              "threshold_partition_shots_per_regime": VALIDATION_SHOTS // 3,
              "errors": total_errors, "shots": sum(len(data_val["threshold"][r]["observable"]) for r in REGIMES),
              "equal_regime_ler": float(np.mean([per_regime[r]["logical_error_rate"] for r in REGIMES])),
              "pymatching_errors": total_pm_errors,
              "equal_regime_pymatching_ler": float(np.mean([per_regime[r]["pymatching_ler"] for r in REGIMES])),
              "paired_candidate_only": sum(v["candidate_only"] for v in per_regime.values()),
              "paired_pymatching_only": sum(v["pymatching_only"] for v in per_regime.values()),
              "per_regime": per_regime, "probability_calibration": calibration_metrics, "history": history}
    ckpt = {"architecture": spec["architecture"], "strategy": spec["strategy"],
            "state_dict": best_state, "best_epoch": best_epoch, "temperature": temp,
            "threshold": selected_threshold, "parameter_count": parameter_count,
            "training_prevalence": prevalence, "pos_weight": pos_weight if spec["strategy"] == "weighted_bce" else None}
    return record, predictions, ckpt


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    started = time.perf_counter()
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    config, inventory, freeze = write_config_and_freeze()
    print(f"Freeze created before sampling: {sha(OUT / 'freeze.json')}", flush=True)
    envs, coords, fingerprints = build_circuits(config, inventory["diagnostic_seeds"])
    # Geometry and label sanity gate before full development generation.
    if len(coords) != 40:
        raise RuntimeError("Stim detector map is not 40 detectors.")
    train_by_rep, validation_by_rep, partitions = {}, {}, {}
    for rep in range(3):
        train_by_rep[rep] = generate_split(envs, inventory, rep, "train")
        validation_by_rep[rep] = generate_split(envs, inventory, rep, "validation")
        partitions[rep] = {}
        rng = np.random.default_rng(inventory["partition_seeds"][rep])
        for regime in REGIMES:
            n = len(validation_by_rep[rep][regime]["observable"])
            ids = rng.permutation(n)
            partitions[rep][regime] = {"monitor": ids[:n//3], "calibration": ids[n//3:2*n//3],
                                       "threshold": ids[2*n//3:]}
    data_arrays = {}
    for rep in range(3):
        for split_name, group in (("train", train_by_rep[rep]), ("validation", validation_by_rep[rep])):
            for regime, block in group.items():
                for key, value in block.items():
                    data_arrays[f"rep{rep}_{split_name}_{regime}_{key}"] = value
        for regime, splits in partitions[rep].items():
            for part, indices in splits.items():
                data_arrays[f"rep{rep}_validation_{regime}_{part}_indices"] = indices.astype(np.int32)
    np.savez_compressed(OUT / "development_samples.npz", **data_arrays)

    all_records, best_checkpoints = [], {}
    predictions_by_rep = {}
    for rep in range(3):
        data_train, data_val = train_by_rep[rep], {}
        for part in ("monitor", "calibration", "threshold"):
            data_val[part] = {r: {k: v[partitions[rep][r][part]] for k, v in validation_by_rep[rep][r].items()}
                              for r in REGIMES}
        predictions_by_rep[rep] = {}
        for arch in ARCHS:
            for strategy in STRATEGIES:
                if time.perf_counter() - started > MAX_RUNTIME_SECONDS:
                    raise TimeoutError("30-minute wall-time budget reached before all model fits completed.")
                seed = next(f for f in inventory["model_streams"] if f["replicate"] == rep and
                            f["architecture"] == arch and f["strategy"] == strategy)
                spec = {"architecture": arch, "strategy": strategy}
                record, preds, checkpoint = fit_one(data_train, data_val, coords, spec,
                    seed["torch_seed"], seed["sampling_seed"], seed["shuffle_seed"], device, started)
                record["replicate"] = rep
                record["cuda_training_verified"] = device.type == "cuda"
                all_records.append(record)
                name = f"{arch}__{strategy}"
                predictions_by_rep[rep][name] = preds
                ckpt_path = OUT / "checkpoints" / f"rep{rep}_{name}.pt"
                ckpt_path.parent.mkdir(parents=True, exist_ok=True)
                torch.save(checkpoint, ckpt_path)
                best_checkpoints[f"rep{rep}_{name}"] = str(ckpt_path.relative_to(ROOT)).replace("\\", "/")
                print(f"rep={rep} {name}: LER={record['equal_regime_ler']:.5f}, PM={record['equal_regime_pymatching_ler']:.5f}, best_epoch={record['best_epoch']}", flush=True)
        # Store all policies' predictions on the common threshold-validation samples.
        pred_payload = {}
        for r in REGIMES:
            pred_payload[f"observable__{r}"] = data_val["threshold"][r]["observable"]
            pred_payload[f"pymatching__{r}"] = data_val["threshold"][r]["pymatching"]
            pred_payload[f"detectors__{r}"] = data_val["threshold"][r]["detectors"]
        for name, values in predictions_by_rep[rep].items():
            for regime in REGIMES:
                pred_payload[f"{name}__probability__{regime}"] = values[f"probability__{regime}"]
                pred_payload[f"{name}__prediction__{regime}"] = values[f"prediction__{regime}"]
        np.savez_compressed(OUT / f"predictions_rep{rep}.npz", **pred_payload)

    aggregate = aggregate_results(all_records)
    elapsed = time.perf_counter() - started
    resources = {"host_peak_rss_bytes": int(psutil.Process().memory_info().rss),
                 "cuda_peak_allocated_bytes": int(torch.cuda.max_memory_allocated(device)) if device.type == "cuda" else None,
                 "cuda_peak_reserved_bytes": int(torch.cuda.max_memory_reserved(device)) if device.type == "cuda" else None}
    results = {"status": "completed_development_only", "test_samples_generated_or_accessed": 0,
               "runtime_seconds": elapsed, "runtime_budget_seconds": MAX_RUNTIME_SECONDS,
               "device": str(device), "cuda_device": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
               "cuda_training_verified": device.type == "cuda", "resources": resources,
               "source_freeze_sha256": sha(OUT / "freeze.json"), "circuit_fingerprints": fingerprints,
               "records": all_records, "aggregate": aggregate,
               "checkpoints": best_checkpoints,
               "data_note": "Matched detector/observable samples are stored in development_samples.npz and predictions_rep*.npz; no test stream was sampled."}
    atomic_json(results, OUT / "results.json")
    write_csv(all_records, aggregate)
    print(json.dumps({"status": results["status"], "fits": len(all_records), "runtime_seconds": elapsed,
                      "device": str(device), "test_shots": 0}, indent=2), flush=True)


def aggregate_results(records):
    names = sorted({(r["architecture"], r["strategy"]) for r in records})
    out = {}
    tcrit_df2 = 4.302652729911275
    for arch, strategy in names:
        rows = [r for r in records if r["architecture"] == arch and r["strategy"] == strategy]
        deltas = [r["equal_regime_ler"] - r["equal_regime_pymatching_ler"] for r in rows]
        mean = float(np.mean(deltas)); sd = float(np.std(deltas, ddof=1))
        half = tcrit_df2 * sd / math.sqrt(len(deltas)) if len(deltas) > 1 else None
        by_regime = {}
        for regime in REGIMES:
            rr = [r["per_regime"][regime] for r in rows]
            regime_d = np.asarray([x["paired_ler_difference"] for x in rr], dtype=np.float64)
            rmean = float(regime_d.mean()); rsd = float(regime_d.std(ddof=1))
            rhalf = tcrit_df2 * rsd / math.sqrt(len(regime_d))
            by_regime[regime] = {"mean_ler": float(np.mean([x["logical_error_rate"] for x in rr])),
                                 "mean_pymatching_ler": float(np.mean([x["pymatching_ler"] for x in rr])),
                                 "mean_positive_recall": float(np.mean([x["positive_recall"] for x in rr if x["positive_recall"] is not None])),
                                 "paired_candidate_only": int(sum(x["candidate_only"] for x in rr)),
                                 "paired_pymatching_only": int(sum(x["pymatching_only"] for x in rr)),
                                 "mean_paired_ler_difference": rmean,
                                 "root_t_95ci_paired_difference": [rmean-rhalf, rmean+rhalf]}
        out[f"{arch}__{strategy}"] = {"n_independent_roots": len(rows), "parameter_count": rows[0]["parameter_count"],
            "mean_equal_regime_ler": float(np.mean([r["equal_regime_ler"] for r in rows])),
            "mean_equal_regime_pymatching_ler": float(np.mean([r["equal_regime_pymatching_ler"] for r in rows])),
            "mean_paired_ler_difference": mean,
            "root_t_95ci_paired_difference": [mean-half, mean+half],
            "root_differences": deltas, "by_regime": by_regime,
            "mean_positive_recall": float(np.mean([np.mean([r["per_regime"][rg]["positive_recall"] for rg in REGIMES]) for r in rows])),
            "mean_candidate_only": int(sum(r["paired_candidate_only"] for r in rows)),
            "mean_pymatching_only": int(sum(r["paired_pymatching_only"] for r in rows)),
            "temperature_mean": float(np.mean([r["temperature"] for r in rows])),
            "threshold_mean": float(np.mean([r["selected_threshold"] for r in rows]))}
    return out


def write_csv(records, aggregate):
    import csv
    with (OUT / "per_root_results.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["replicate", "architecture", "strategy", "parameter_count", "best_epoch", "temperature",
                  "selected_threshold", "equal_regime_ler", "equal_regime_pymatching_ler",
                  "paired_ler_difference", "paired_candidate_only", "paired_pymatching_only"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in records:
            w.writerow({k: r[k] for k in fields})
    with (OUT / "aggregate_results.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["model_strategy", "parameter_count", "n_roots", "mean_ler", "mean_pymatching_ler",
                  "mean_paired_difference", "ci95_low", "ci95_high", "mean_positive_recall",
                  "candidate_only", "pymatching_only"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for name, r in aggregate.items():
            w.writerow({"model_strategy": name, "parameter_count": r["parameter_count"], "n_roots": r["n_independent_roots"],
                "mean_ler": r["mean_equal_regime_ler"], "mean_pymatching_ler": r["mean_equal_regime_pymatching_ler"],
                "mean_paired_difference": r["mean_paired_ler_difference"], "ci95_low": r["root_t_95ci_paired_difference"][0],
                "ci95_high": r["root_t_95ci_paired_difference"][1], "mean_positive_recall": r["mean_positive_recall"],
                "candidate_only": r["mean_candidate_only"], "pymatching_only": r["mean_pymatching_only"]})


if __name__ == "__main__":
    main()
