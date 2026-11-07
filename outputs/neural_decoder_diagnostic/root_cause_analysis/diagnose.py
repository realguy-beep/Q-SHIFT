"""Reproduce old validation evidence and run bounded development-only collapse diagnostics.

This script has no test-split sampler. It uses the historical small development
training stream only for tiny-set memorization, then a fresh, collision-screened
train/validation stream for balanced/weighted training comparisons.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import sys
import threading
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
import psutil
from scipy.stats import binomtest

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
INTEGRATION = REPO / "outputs/neural_decoder_diagnostic/structured_integration"
OLD_RUN = INTEGRATION / "dev_run_6000"
sys.path.insert(0, str(REPO / "dashboard"))

from models import DirectMLP
from seed_protocol import historical_seeds
from simulator import prepare, sample, decode_matching
from structured_decoder import StructuredConv3DDecoder, residual_training_target
from structured_training import REGIMES, candidate_spec, make_model, inventory_seed_values
from neural_collapse_diagnostics import (balanced_batch_indices, confusion_counts,
                                         debias_weighted_logits, group_label_bound)

TRAIN_COUNTS = {r: 3000 for r in REGIMES}
VAL_COUNTS = {r: 1500 for r in REGIMES}
BATCH = 256
ROOTS = {"train": 1_180_000_001, "validation": 1_183_000_001}
MODEL_SEED_BASE = 1_186_000_001
DIAGNOSTIC_SEEDS = [1_187_000_001, 1_187_000_002, 1_187_000_003]
SELECTION_SEED = 1_188_000_001
MAX_BUDGET_SECONDS = 2400
START = time.monotonic()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def check_budget():
    if time.monotonic() - START > MAX_BUDGET_SECONDS:
        raise TimeoutError(f"Diagnostic exceeded its {MAX_BUDGET_SECONDS}s hard budget.")


def start_resource_monitor():
    process = psutil.Process(os.getpid())
    stop = threading.Event()
    state = {"peak_rss_bytes": int(process.memory_info().rss)}
    def sample_usage():
        while not stop.is_set():
            try:
                state["peak_rss_bytes"] = max(state["peak_rss_bytes"], int(process.memory_info().rss))
            except (psutil.Error, OSError):
                pass
            stop.wait(0.5)
    thread = threading.Thread(target=sample_usage, daemon=True)
    thread.start()
    return stop, thread, state


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_prior_manifest() -> dict:
    manifest = read_json(INTEGRATION / "FINAL_MANIFEST.json")
    missing, mismatches = [], []
    for entry in manifest["files"]:
        path = REPO / entry["path"]
        if not path.is_file():
            missing.append(entry["path"])
        elif sha256(path) != entry["sha256"]:
            mismatches.append(entry["path"])
    if missing or mismatches:
        raise RuntimeError(f"Prior manifest integrity failure; missing={missing}, mismatches={mismatches}")
    return {"status": "PASS", "entries": len(manifest["files"]), "missing": missing,
            "hash_mismatches": mismatches}


def inventory_seed_sets() -> tuple[dict, set[int]]:
    streams, used = [], []
    for split, amount_by_regime in (("train", TRAIN_COUNTS), ("validation", VAL_COUNTS)):
        for i, regime in enumerate(REGIMES):
            root = ROOTS[split] + i * 100_000
            count = amount_by_regime[regime]
            batch_count = math.ceil(count / BATCH)
            seeds = list(range(root, root + batch_count))
            streams.append({"split": split, "regime": regime, "root": root, "shots": count,
                            "batch_size": BATCH, "batch_count": batch_count,
                            "seed_range_inclusive": [root, root + batch_count - 1], "seeds": seeds})
            used.extend(seeds)
    model_seeds = list(range(MODEL_SEED_BASE, MODEL_SEED_BASE + 64))
    all_proposed = used + DIAGNOSTIC_SEEDS + model_seeds + [SELECTION_SEED]
    historical = set(historical_seeds())
    old = read_json(OLD_RUN / "structured_seed_inventory.json")
    frozen = read_json(INTEGRATION / "official_100k_config_seed_inventory.json")
    old_values = inventory_seed_values(old)
    frozen_values = inventory_seed_values(frozen)
    collisions = {
        "within_new_inventory": sorted(x for x in set(all_proposed) if all_proposed.count(x) > 1),
        "historical": sorted(set(all_proposed) & historical),
        "prior_small_development": sorted(set(all_proposed) & old_values),
        "prepared_100k": sorted(set(all_proposed) & frozen_values),
    }
    if any(collisions.values()):
        raise RuntimeError(f"New development seed collision: {collisions}")
    inventory = {"status": "screen_pass", "allocation": "fresh development-only train/validation streams; no test stream",
                 "regimes": list(REGIMES), "train_shots_by_regime": TRAIN_COUNTS,
                 "validation_shots_by_regime": VAL_COUNTS, "batch_size": BATCH,
                 "streams": streams, "diagnostic_stim_seeds": DIAGNOSTIC_SEEDS,
                 "model_rng_seeds": model_seeds, "subset_selection_seed": SELECTION_SEED,
                 "unique_proposed_rng_values": len(set(all_proposed)), "collisions": collisions,
                 "historical_seed_values_checked": len(historical),
                 "old_development_seed_values_checked": len(old_values),
                 "prepared_100k_seed_values_checked": len(frozen_values),
                 "coverage_limit": "recoverable historical scan and saved run inventories only"}
    return inventory, set(all_proposed)


def prepare_envs(device: str = "cpu"):
    envs, coords = {}, None
    fingerprints = {}
    for i, regime in enumerate(REGIMES):
        circuit, noise_record, dem, matching, fixed_index, records = prepare({
            "memory_basis": "z", "noise_regime": regime, "distance": 3, "rounds": 5,
            "gate_p": 0.003, "measurement_p": 0.003, "bias_ratio": 10.0, "device": device})
        current = circuit.get_detector_coordinates()
        if coords is None:
            coords = current
        elif coords != current:
            raise RuntimeError("Stim detector coordinates differ between noise regimes")
        if circuit.num_detectors != 40 or circuit.num_observables != 1 or len(current) != 40:
            raise RuntimeError(f"Unexpected circuit schema for {regime}")
        d0, y0 = circuit.without_noise().compile_detector_sampler(seed=DIAGNOSTIC_SEEDS[i]).sample(
            shots=32, separate_observables=True)
        if np.any(d0) or np.any(y0):
            raise RuntimeError(f"Noiseless Stim sample was nonzero for {regime}")
        envs[regime] = {"circuit": circuit, "matching": matching, "fixed_index": fixed_index}
        fingerprints[regime] = {"circuit_sha256": hashlib.sha256(str(circuit).encode()).hexdigest(),
                                "dem_sha256": hashlib.sha256(str(dem).encode()).hexdigest(),
                                "detectors": circuit.num_detectors, "observables": circuit.num_observables,
                                "fixed_decoder_index": fixed_index}
    return envs, coords, fingerprints


def collect_split(envs: dict, inventory: dict, split: str, counts: dict):
    d_all, y_all, pm_all, r_all = [], [], [], []
    streams = {(s["split"], s["regime"]): s for s in inventory["streams"]}
    for regime_id, regime in enumerate(REGIMES):
        stream = streams[(split, regime)]
        n = int(counts[regime])
        chunks = [[], [], []]
        for batch_index, start in enumerate(range(0, n, BATCH)):
            size = min(BATCH, n - start)
            seed = stream["root"] + batch_index
            d, y = sample(envs[regime]["circuit"], seed, size)
            pm = decode_matching(envs[regime]["matching"], d)
            if d.shape != (size, 40) or y.shape != (size,) or pm.shape != (size,):
                raise RuntimeError("Stim/PyMatching sample alignment or dimensions failed")
            if any(np.any((a != 0) & (a != 1)) for a in (d, y, pm)):
                raise RuntimeError("Nonbinary detector, observable, or PyMatching values")
            chunks[0].append(d); chunks[1].append(y); chunks[2].append(pm)
        d, y, pm = [np.concatenate(x, axis=0) for x in chunks]
        if len(d) != n or len(y) != n or len(pm) != n:
            raise RuntimeError("A generated development split has the wrong shot count")
        d_all.append(d); y_all.append(y); pm_all.append(pm); r_all.append(np.full(n, regime_id, np.uint8))
    return {"detectors": np.concatenate(d_all), "observable": np.concatenate(y_all),
            "pymatching": np.concatenate(pm_all), "regime_id": np.concatenate(r_all)}


def save_npz_atomic(path: Path, **arrays):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as f:
        np.savez_compressed(f, **arrays)
    os.replace(tmp, path)


def reproduce_old_saved_validation() -> dict:
    expected = read_json(OLD_RUN / "structured_development_results.json")
    found = {"identity": {r: 0 for r in REGIMES}, "pymatching": {r: 0 for r in REGIMES}}
    candidate = {name: {r: {"errors": 0, "target_positive": 0, "predicted_positive_bins": [0] * 10,
                            "class_conditional_bce_sum": [0.0, 0.0], "class_conditional_n": [0, 0],
                            "confusion": {"tn": 0, "fp": 0, "fn": 0, "tp": 0},
                            "candidate_only": 0, "fixed_only": 0, "prediction_disagreements": 0}
                         for r in REGIMES} for name in expected["candidates"]}
    evidence_files = sorted((OLD_RUN / "validation_evidence").glob("*.npz"))
    for path in evidence_files:
        regime = path.name.split("_batch_")[0]
        with np.load(path, allow_pickle=False) as z:
            d, y, fixed = z["detectors"], z["observable"].astype(np.uint8), z["pymatching"].astype(np.uint8)
            if d.shape != (len(y), 40) or fixed.shape != y.shape:
                raise RuntimeError(f"Malformed old evidence bundle: {path.name}")
            found["identity"][regime] += int(y.sum())
            found["pymatching"][regime] += int(np.count_nonzero(fixed ^ y))
            for name in candidate:
                prob = z[f"probability__{name}"].astype(np.float64)
                pred05 = z[f"prediction__{name}"].astype(np.uint8)
                spec = candidate_spec(name)
                target = np.bitwise_xor(fixed, y) if spec["kind"] == "residual" else y
                expected05 = (np.bitwise_xor(fixed, (prob >= 0.5).astype(np.uint8))
                              if spec["kind"] == "residual" else (prob >= 0.5).astype(np.uint8))
                if not np.array_equal(pred05, expected05):
                    raise RuntimeError(f"Stored prediction/score convention mismatch in {path.name}/{name}")
                selected_threshold = float(expected["selected_thresholds"][name])
                correction = (prob >= selected_threshold).astype(np.uint8)
                pred = np.bitwise_xor(fixed, correction) if spec["kind"] == "residual" else correction
                c = candidate[name][regime]
                c["errors"] += int(np.count_nonzero(pred ^ y))
                c["target_positive"] += int(target.sum())
                c["predicted_positive_bins"] = (np.asarray(c["predicted_positive_bins"]) +
                    np.histogram(prob, bins=np.linspace(0, 1, 11))[0]).tolist()
                clipped = np.clip(prob, 1e-12, 1 - 1e-12)
                losses = -(target * np.log(clipped) + (1 - target) * np.log(1 - clipped))
                for cls in (0, 1):
                    mask = target == cls
                    c["class_conditional_bce_sum"][cls] += float(losses[mask].sum())
                    c["class_conditional_n"][cls] += int(mask.sum())
                c["confusion"] = {k: c["confusion"][k] + v for k, v in
                                   confusion_counts(target, (prob >= 0.5).astype(np.uint8)).items()}
                wrong, fixed_wrong = pred ^ y, fixed ^ y
                c["candidate_only"] += int(np.count_nonzero((wrong == 1) & (fixed_wrong == 0)))
                c["fixed_only"] += int(np.count_nonzero((wrong == 0) & (fixed_wrong == 1)))
                c["prediction_disagreements"] += int(np.count_nonzero(pred != fixed))
    if len(evidence_files) != 24:
        raise RuntimeError(f"Expected 24 previous validation evidence batches, found {len(evidence_files)}")
    normalized = {"identity": {}, "pymatching": {}, "candidates": {}}
    for metric, key in (("identity", "identity"), ("pymatching", "pymatching")):
        for reg in REGIMES:
            normalized[metric][reg] = found[key][reg]
            old = expected["comparators"][key]["per_regime"][reg]["errors"]
            if found[key][reg] != old:
                raise RuntimeError(f"Recomputed old {metric} count mismatch for {reg}: {found[key][reg]} != {old}")
    for name, regimes in candidate.items():
        normalized["candidates"][name] = {}
        for reg, m in regimes.items():
            old = expected["candidates"][name]["per_regime"][reg]
            threshold = str(expected["selected_thresholds"][name])
            if m["errors"] != old["thresholds"][threshold]["logical_errors"]:
                raise RuntimeError(f"Recomputed old candidate error count mismatch: {name}/{reg}")
            n = sum(m["class_conditional_n"])
            normalized["candidates"][name][reg] = {
                "n": n, "logical_errors": m["errors"], "ler": m["errors"] / n,
                "target_positive_count": m["target_positive"],
                "target_positive_rate": m["target_positive"] / n,
                "predicted_positive_histogram_at_0_5": m["predicted_positive_bins"],
                "class_conditional_bce": [m["class_conditional_bce_sum"][i] / max(1, m["class_conditional_n"][i]) for i in (0, 1)],
                "confusion_at_0_5": m["confusion"],
                "candidate_only_vs_pm": m["candidate_only"], "pm_only_vs_candidate": m["fixed_only"],
                "prediction_disagreements_vs_pm": m["prediction_disagreements"]}
    normalized["validation_shots_by_regime"] = {r: expected["comparators"]["identity"]["per_regime"][r]["n"] for r in REGIMES}
    normalized["validation_total_shots"] = sum(normalized["validation_shots_by_regime"].values())
    normalized["test_samples_accessed"] = 0
    return normalized


def _array_model(model_name: str, coords: dict, run_path: Path, device):
    artifact = torch.load(run_path / "best_models" / f"{model_name}.pt", map_location=device, weights_only=False)
    model = make_model(artifact["spec"], coords).to(device)
    model.load_state_dict(artifact["state_dict"])
    model.eval()
    return model, artifact


def model_output_logits(model, name, d, fixed, device):
    with torch.no_grad():
        x = torch.as_tensor(d, dtype=torch.float32, device=device)
        f = torch.as_tensor(fixed, dtype=torch.float32, device=device)
        raw = model(x, f) if name == "residual_mlp" else model(x)
    return raw.detach()


def bias_and_gradient_diagnostics(train, coords, device) -> dict:
    results = {}
    for name in ("direct_mlp", "residual_mlp", "structured_ch8_unweighted", "structured_ch8_weighted"):
        model, artifact = _array_model(name, coords, OLD_RUN, device)
        spec = artifact["spec"]
        layer = model.net[-1]
        target = np.bitwise_xor(train["pymatching"], train["observable"]) if spec["kind"] == "residual" else train["observable"]
        grad = {}
        for cls in (0, 1):
            ids = np.flatnonzero(target == cls)[:256]
            if not len(ids):
                grad[str(cls)] = {"n": 0, "global_l2_norm": None}
                continue
            model.zero_grad(set_to_none=True)
            x = torch.as_tensor(train["detectors"][ids], dtype=torch.float32, device=device)
            f = torch.as_tensor(train["pymatching"][ids], dtype=torch.float32, device=device)
            y = torch.as_tensor(target[ids], dtype=torch.float32, device=device)
            out = model(x, f) if spec["kind"] == "residual" else model(x)
            weight = None
            if name == "structured_ch8_weighted":
                weight = torch.tensor([float(read_json(OLD_RUN / "structured_development_results.json")["candidate_fits"][name]["positive_weight"])], device=device)
            loss = F.binary_cross_entropy_with_logits(out, y, pos_weight=weight)
            loss.backward()
            norm = math.sqrt(sum(float(torch.sum(p.grad.detach().float() ** 2).item()) for p in model.parameters() if p.grad is not None))
            grad[str(cls)] = {"n": int(len(ids)), "mean_loss": float(loss.item()), "global_l2_norm": norm}
        results[name] = {"best_epoch": int(artifact["best_epoch"]),
                         "last_layer_bias": float(layer.bias.detach().cpu().reshape(-1)[0]),
                         "residual_target": spec["kind"] == "residual", "class_gradient_norms": grad}
    return results


def unique_class_indices(detectors, labels, cls: int, count: int, rng: np.random.Generator):
    order = rng.permutation(len(labels))
    selected, seen = [], set()
    for idx in order:
        if int(labels[idx]) != cls:
            continue
        key = np.packbits(detectors[idx], bitorder="little").tobytes()
        if key in seen:
            continue
        seen.add(key); selected.append(int(idx))
        if len(selected) == count:
            return np.asarray(selected, dtype=np.int64)
    raise RuntimeError(f"Only {len(selected)} unique detector patterns found for class {cls}; need {count}")


def make_tiny_sets(train):
    rng = np.random.default_rng(SELECTION_SEED)
    y = train["observable"]
    neg_128 = unique_class_indices(train["detectors"], y, 0, 128, rng)
    pos_128 = unique_class_indices(train["detectors"], y, 1, 128, rng)
    balanced = np.concatenate((neg_128, pos_128))
    rng.shuffle(balanced)
    neg_240 = unique_class_indices(train["detectors"], y, 0, 240, rng)
    pos_16 = unique_class_indices(train["detectors"], y, 1, 16, rng)
    natural = np.concatenate((neg_240, pos_16))
    rng.shuffle(natural)
    return balanced, natural


def build_tiny_model(kind: str, coords: dict, seed: int, device):
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    if kind == "mlp":
        model = DirectMLP()
    else:
        model = StructuredConv3DDecoder(coords, channels=8, dropout=0.0)
    for module in model.modules():
        if isinstance(module, torch.nn.Dropout):
            module.p = 0.0
        elif isinstance(module, torch.nn.Dropout3d):
            module.p = 0.0
    return model.to(device)


def train_tiny_case(name: str, kind: str, indices: np.ndarray, data: dict, lr: float,
                    weighted: bool, seed: int, coords: dict, device, max_epochs=800) -> dict:
    y_all = data["observable"]
    x_np, y_np = data["detectors"][indices], y_all[indices]
    model = build_tiny_model(kind, coords, seed, device)
    x = torch.as_tensor(x_np, dtype=torch.float32, device=device)
    y = torch.as_tensor(y_np, dtype=torch.float32, device=device)
    weight_value = float((len(y_np) - int(y_np.sum())) / max(1, int(y_np.sum()))) if weighted else 1.0
    weight = torch.tensor([weight_value], dtype=torch.float32, device=device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.0)
    best, best_state, stable = -1.0, None, 0
    records = []
    for epoch in range(1, max_epochs + 1):
        check_budget()
        model.train(); opt.zero_grad(set_to_none=True)
        logits = model(x)
        loss = F.binary_cross_entropy_with_logits(logits, y, pos_weight=weight)
        loss.backward(); opt.step()
        if epoch % 10 == 0 or epoch == 1 or epoch == max_epochs:
            model.eval()
            with torch.no_grad():
                p = torch.sigmoid(model(x)).cpu().numpy()
            pred = (p >= 0.5).astype(np.uint8)
            acc = float(np.mean(pred == y_np))
            cm = confusion_counts(y_np, pred)
            if acc > best:
                best = acc
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stable = stable + 1 if acc == 1.0 else 0
            if epoch in (1, 10, 50, 100, 200, 400, 800) or stable == 3:
                records.append({"epoch": epoch, "loss": float(loss.item()), "accuracy": acc,
                                "confusion": cm, "positive_recall": cm["tp"] / max(1, cm["tp"] + cm["fn"]),
                                "negative_recall": cm["tn"] / max(1, cm["tn"] + cm["fp"])})
            if stable >= 3:
                break
    if best_state is None:
        raise RuntimeError("Tiny memorization fit produced no checkpoint")
    model.load_state_dict(best_state); model.eval()
    with torch.no_grad():
        final_logits = model(x)
        p = torch.sigmoid(final_logits).cpu().numpy()
    pred = (p >= 0.5).astype(np.uint8)
    cm = confusion_counts(y_np, pred)
    final_bce = float(F.binary_cross_entropy_with_logits(final_logits, y, pos_weight=weight).item())
    return {"case": name, "model": kind, "n": int(len(indices)), "positive_count": int(y_np.sum()),
            "negative_count": int(len(y_np) - y_np.sum()), "learning_rate": lr,
            "positive_weight": weight_value, "epochs_run": epoch,
            "train_accuracy": float(np.mean(pred == y_np)), "confusion_at_0_5": cm,
            "positive_recall": cm["tp"] / max(1, cm["tp"] + cm["fn"]),
            "negative_recall": cm["tn"] / max(1, cm["tn"] + cm["fp"]),
            "bce_final": final_bce,
            "epoch_trace": records}


def sigmoid_np(z):
    z = np.asarray(z, dtype=np.float64)
    return 1.0 / (1.0 + np.exp(-np.clip(z, -60, 60)))


def make_policy_training_batches(y, indices, strategy: str, batch_size: int, rng):
    if strategy == "balanced":
        for _ in range(math.ceil(len(indices) / batch_size)):
            local = balanced_batch_indices(y[indices], batch_size, rng)
            yield indices[local]
    else:
        order = rng.permutation(indices)
        for start in range(0, len(order), batch_size):
            yield order[start:start + batch_size]


def stratified_bootstrap(diff_by_regime: dict, seed: int, reps: int = 5000):
    rng = np.random.default_rng(seed)
    means = np.zeros(reps, dtype=np.float64)
    for values in diff_by_regime.values():
        a = np.asarray(values, dtype=np.float32)
        ix = rng.integers(0, len(a), size=(reps, len(a)), dtype=np.int32)
        means += a[ix].mean(axis=1) / len(diff_by_regime)
    return [float(x) for x in np.quantile(means, [0.025, 0.975])]


def evaluate_policy(model, kind, strategy, weight, prior, train_data, val_data, val_labels, val_fixed,
                    val_regimes, device, name, size, epochs):
    model.eval()
    with torch.no_grad():
        logits = []
        for start in range(0, len(val_data), 512):
            x = torch.as_tensor(val_data[start:start+512], dtype=torch.float32, device=device)
            logits.append(model(x).detach().cpu().numpy())
    raw = np.concatenate(logits)
    corrected = raw.copy()
    if strategy == "weighted":
        corrected = debias_weighted_logits(corrected, weight)
    elif strategy == "balanced":
        # Correct the sampled class prior (0.5) back to the natural pooled prior.
        corrected = corrected + math.log(prior / (1 - prior))
    prob = sigmoid_np(corrected)
    y = np.asarray(val_labels, dtype=np.uint8)
    thresholds = np.linspace(0.0, 1.0, 201)
    score = {}
    for t in thresholds:
        score[float(t)] = float(np.mean([np.mean(((prob[val_regimes == ri] >= t).astype(np.uint8) ^ y[val_regimes == ri]))
                                         for ri in range(len(REGIMES))]))
    selected = min(score, key=lambda t: (score[t], abs(t - 0.5), t))
    pred = (prob >= selected).astype(np.uint8)
    all_diff, per_regime = {}, {}
    for ri, regime in enumerate(REGIMES):
        m = val_regimes == ri
        wrong = pred[m] ^ y[m]
        fixed_wrong = val_fixed[m] ^ y[m]
        diff = wrong.astype(np.int8) - fixed_wrong.astype(np.int8)
        per_regime[regime] = {"n": int(m.sum()), "errors": int(wrong.sum()), "ler": float(wrong.mean()),
                              "pymatching_errors": int(fixed_wrong.sum()), "pymatching_ler": float(fixed_wrong.mean()),
                              "candidate_only": int(np.count_nonzero((wrong == 1) & (fixed_wrong == 0))),
                              "pymatching_only": int(np.count_nonzero((wrong == 0) & (fixed_wrong == 1))),
                              "prediction_disagreements": int(np.count_nonzero(pred[m] != val_fixed[m])),
                              "predicted_positive_rate": float(pred[m].mean()),
                              "target_positive_rate": float(y[m].mean()),
                              "confusion": confusion_counts(y[m], pred[m]),
                              "brier": float(np.mean((prob[m] - y[m]) ** 2)),
                              "log_loss": float(np.mean(-(y[m] * np.log(np.clip(prob[m], 1e-12, 1)) +
                                                          (1-y[m]) * np.log(np.clip(1-prob[m], 1e-12, 1))))) }
        all_diff[regime] = diff
    a = sum(v["candidate_only"] for v in per_regime.values())
    b = sum(v["pymatching_only"] for v in per_regime.values())
    delta = float(np.mean([per_regime[r]["ler"] - per_regime[r]["pymatching_ler"] for r in REGIMES]))
    return {"model": kind, "strategy": strategy, "training_size_per_regime": int(size),
            "epochs_requested": int(epochs), "selected_threshold_validation": float(selected),
            "equal_regime_ler": float(np.mean([per_regime[r]["ler"] for r in REGIMES])),
            "equal_regime_pymatching_ler": float(np.mean([per_regime[r]["pymatching_ler"] for r in REGIMES])),
            "paired_delta_ler_candidate_minus_pymatching": delta,
            "candidate_only": int(a), "pymatching_only": int(b),
            "paired_disagreements": int(sum(x["prediction_disagreements"] for x in per_regime.values())),
            "mcnemar_exact_two_sided_p_descriptive": float(binomtest(a, a+b, 0.5).pvalue) if a+b else 1.0,
            "conditional_stratified_shot_bootstrap_95ci": stratified_bootstrap(all_diff, SELECTION_SEED + size + epochs),
            "per_regime": per_regime,
            "probability_histogram_10_bins": np.histogram(prob, bins=np.linspace(0, 1, 11))[0].tolist()}


def run_policy_fit(kind, strategy, size, epochs, train, val, coords, device, seed):
    model = build_tiny_model(kind, coords, seed, device)
    # The scaled diagnostic uses the production dropout value; tiny-set tests above disable dropout.
    for module in model.modules():
        if isinstance(module, torch.nn.Dropout): module.p = 0.05
        elif isinstance(module, torch.nn.Dropout3d): module.p = 0.05
    xreg = train["regime_id"]
    sub_idx = []
    local_rng = np.random.default_rng(seed)
    for ri in range(len(REGIMES)):
        ids = np.flatnonzero(xreg == ri)
        sub_idx.extend(local_rng.permutation(ids)[:size].tolist())
    sub_idx = np.asarray(sub_idx, dtype=np.int64)
    y_train = train["observable"]
    labels = y_train[sub_idx]
    prior = float(labels.mean())
    if not 0 < prior < 1:
        raise RuntimeError("Train sample unexpectedly lacks one class")
    weight = float((1 - prior) / prior) if strategy == "weighted" else 1.0
    opt = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.0001)
    best_loss, best_state, best_epoch = float("inf"), None, None
    val_reg = val["regime_id"]
    y_val = val["observable"]
    fixed_val = val["pymatching"]
    # Validation checkpointing uses proper unweighted log loss after undoing any
    # known training reweighting/prior shift. No test data path exists here.
    for epoch in range(1, epochs + 1):
        check_budget(); model.train()
        rng = np.random.default_rng(seed + epoch * 1009)
        for ix in make_policy_training_batches(labels, np.arange(len(sub_idx)), strategy, 256, rng):
            absolute = sub_idx[ix]
            x = torch.as_tensor(train["detectors"][absolute], dtype=torch.float32, device=device)
            y = torch.as_tensor(y_train[absolute], dtype=torch.float32, device=device)
            opt.zero_grad(set_to_none=True)
            logits = model(x)
            pos_w = torch.tensor([weight], dtype=torch.float32, device=device) if strategy == "weighted" else None
            loss = F.binary_cross_entropy_with_logits(logits, y, pos_weight=pos_w)
            loss.backward(); opt.step()
        model.eval()
        with torch.no_grad():
            val_logits = []
            for start in range(0, len(y_val), 512):
                x = torch.as_tensor(val["detectors"][start:start+512], dtype=torch.float32, device=device)
                val_logits.append(model(x).cpu().numpy())
        vl = np.concatenate(val_logits)
        if strategy == "weighted": vl = debias_weighted_logits(vl, weight)
        elif strategy == "balanced": vl = vl + math.log(prior / (1-prior))
        vp = sigmoid_np(vl)
        vloss = float(np.mean(-(y_val*np.log(np.clip(vp,1e-12,1)) + (1-y_val)*np.log(np.clip(1-vp,1e-12,1)))))
        if vloss < best_loss:
            best_loss, best_epoch = vloss, epoch
            best_state = {k: v.detach().cpu().clone() for k,v in model.state_dict().items()}
    if best_state is None: raise RuntimeError("No best-validation checkpoint selected")
    model.load_state_dict(best_state)
    run_policy_fit.last_best = {"state_dict": best_state, "epoch": best_epoch, "validation_log_loss": best_loss,
                                "model": kind, "strategy": strategy, "size_per_regime": size,
                                "max_epochs": epochs, "seed": seed, "pos_weight": weight, "prior": prior}
    return evaluate_policy(model, kind, strategy, weight, prior, train, val["detectors"], y_val, fixed_val,
                           val_reg, device, f"{kind}_{strategy}_{size}_{epochs}", size, epochs)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    integrity = verify_prior_manifest()
    inventory, _ = inventory_seed_sets()
    atomic_json(OUT / "seed_inventory.json", inventory)
    config = {"distance": 3, "rounds": 5, "memory_basis": "z", "gate_p": 0.003,
              "measurement_p": 0.003, "bias_ratio": 10.0,
              "train": TRAIN_COUNTS, "validation": VAL_COUNTS,
              "tiny_balanced_n": 256, "tiny_natural_n": 256,
              "tiny_learning_rates": [0.001, 0.01], "tiny_max_epochs": 800,
              "scale_sizes_per_regime": [1500, 3000], "scale_max_epochs": 15,
              "scale_strategies": ["natural_unweighted", "natural_weighted", "balanced_minibatches"],
              "scale_models": ["direct_mlp", "structured_cnn_ch8"],
              "seed_inventory_sha256": sha256(OUT / "seed_inventory.json"),
              "reserved_test_access": "none; no test stream was allocated or sampled",
              "max_runtime_seconds": MAX_BUDGET_SECONDS}
    atomic_json(OUT / "diagnostic_config.json", config)
    atomic_json(OUT / "pre_sampling_freeze.json", {
        "status": "development diagnostic freeze; created before fresh Stim sampling",
        "config_sha256": sha256(OUT / "diagnostic_config.json"),
        "seed_inventory_sha256": sha256(OUT / "seed_inventory.json"),
        "source_sha256": {"diagnose.py": sha256(Path(__file__)),
                          "neural_collapse_diagnostics.py": sha256(REPO / "dashboard/neural_collapse_diagnostics.py"),
                          "structured_training.py": sha256(REPO / "dashboard/structured_training.py"),
                          "structured_decoder.py": sha256(REPO / "dashboard/structured_decoder.py"),
                          "simulator.py": sha256(REPO / "dashboard/simulator.py")},
        "test_access": "none"})
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.set_num_threads(min(4, os.cpu_count() or 1))
    old_det = torch.are_deterministic_algorithms_enabled()
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    if device.type == "cuda":
        torch.cuda.set_device(0)
        torch.cuda.reset_peak_memory_stats(0)
    resource_stop, resource_thread, resource_state = start_resource_monitor()
    envs, coords, circuit_fingerprints = prepare_envs()
    xs, ys, ts = sorted({v[0] for v in coords.values()}), sorted({v[1] for v in coords.values()}), sorted({v[2] for v in coords.values()})
    # The actual circuit has six coordinate time slices (including boundaries),
    # four x values, four y values and 40 occupied detector positions.
    geom = StructuredConv3DDecoder(coords, channels=8, dropout=0.0).geometry
    if geom.grid_shape != (len(ts), len(ys), len(xs)) or int(geom.occupancy.sum()) != 40:
        raise RuntimeError("CNN coordinate mapping does not match Stim detector coordinates")
    train = collect_split(envs, inventory, "train", TRAIN_COUNTS)
    val = collect_split(envs, inventory, "validation", VAL_COUNTS)
    save_npz_atomic(OUT / "fresh_development_data.npz", **{f"train_{k}": v for k,v in train.items()},
                    **{f"validation_{k}": v for k,v in val.items()})
    data_checks = {"stim_detector_shape": list(train["detectors"].shape),
                   "stim_observable_shape": list(train["observable"].shape),
                   "pymatching_prediction_shape": list(train["pymatching"].shape),
                   "all_binary": bool(all(np.all((train[k] == 0) | (train[k] == 1))
                                           for k in ("detectors", "observable", "pymatching"))),
                   "train_validation_seed_disjoint": True,
                   "regime_counts": {r: {"train": int(np.count_nonzero(train["regime_id"] == i)),
                                          "validation": int(np.count_nonzero(val["regime_id"] == i))}
                                     for i,r in enumerate(REGIMES)},
                   "coordinate_summary": {"detector_count": len(coords), "x_values": xs, "y_values": ys,
                                          "time_values": ts, "grid_shape_time_y_x": list(geom.grid_shape),
                                          "occupied_cells": int(geom.occupancy.sum())},
                   "circuits": circuit_fingerprints}
    target_prev = {}
    contradictions = {}
    for ri, regime in enumerate(REGIMES):
        m = train["regime_id"] == ri
        residual = train["observable"][m] ^ train["pymatching"][m]
        target_prev[regime] = {"n": int(m.sum()), "direct_positive": int(train["observable"][m].sum()),
                               "direct_prevalence": float(train["observable"][m].mean()),
                               "residual_positive": int(residual.sum()), "residual_prevalence": float(residual.mean())}
        contradictions[regime] = {"direct": group_label_bound(train["detectors"][m], train["observable"][m]),
                                  "residual": group_label_bound(train["detectors"][m], residual)}
    contradictions["pooled"] = {"direct": group_label_bound(train["detectors"], train["observable"]),
                                "residual": group_label_bound(train["detectors"], train["observable"] ^ train["pymatching"])}
    old_reproduced = reproduce_old_saved_validation()
    gradient_diagnostics = bias_and_gradient_diagnostics(train, coords, device)
    balanced_ix, natural_ix = make_tiny_sets(train)
    tiny_bound = {"balanced_subset": group_label_bound(train["detectors"][balanced_ix], train["observable"][balanced_ix]),
                  "natural_subset": group_label_bound(train["detectors"][natural_ix], train["observable"][natural_ix])}
    tiny_results = []
    model_seed = MODEL_SEED_BASE
    # Fixed, class-balanced 256-example memorization probe: 128 examples/class.
    for kind in ("mlp", "cnn"):
        for lr in (0.001, 0.01):
            tiny_results.append(train_tiny_case(f"balanced_lr_{lr}", kind, balanced_ix, train, lr,
                                                weighted=False, seed=model_seed, coords=coords,
                                                device=device, max_epochs=800))
            model_seed += 1
    # Natural-prevalence 256-example control: 16 positive and 240 negative cases.
    for kind in ("mlp", "cnn"):
        for lr in (0.001, 0.01):
            for weighted in (False, True):
                tiny_results.append(train_tiny_case(f"natural_lr_{lr}_weighted_{weighted}", kind,
                                                    natural_ix, train, lr, weighted, model_seed,
                                                    coords, device, max_epochs=800))
                model_seed += 1
    tiny_gate = all(any(x["model"] == kind and x["case"].startswith("balanced") and
                        x["train_accuracy"] >= 0.98 and x["positive_recall"] >= 0.95 and
                        x["negative_recall"] >= 0.95 for x in tiny_results) for kind in ("mlp", "cnn"))
    scale_results = []
    if tiny_gate:
        model_seed = MODEL_SEED_BASE + 32
        val_data_labels = val["observable"]
        for size in (1500, 3000):
            for kind in ("mlp", "cnn"):
                for strategy in ("natural", "weighted", "balanced"):
                    result = run_policy_fit(kind, strategy, size, 15, train, val, coords, device, model_seed)
                    scale_results.append(result)
                    best = run_policy_fit.last_best
                    save = OUT / "checkpoints" / f"{kind}_{strategy}_{size}_best.pt"
                    save.parent.mkdir(parents=True, exist_ok=True)
                    tmp = save.with_suffix(".pt.tmp")
                    torch.save(best, tmp); os.replace(tmp, save)
                    model_seed += 1
                    check_budget()
    else:
        scale_status = "SKIPPED: tiny-set memorization gate failed for at least one architecture"
    if tiny_gate:
        scale_status = "COMPLETED: bounded development-only size/epoch comparison; one fresh validation stream; not confirmatory"
    old_result = read_json(OLD_RUN / "structured_development_results.json")
    resource_stop.set()
    resource_thread.join(timeout=2)
    try:
        resource_state["peak_rss_bytes"] = max(resource_state["peak_rss_bytes"], int(psutil.Process(os.getpid()).memory_info().rss))
    except (psutil.Error, OSError):
        pass
    final = {"status": "completed_development_diagnostics", "test_samples_generated_or_accessed": 0,
             "old_manifest_integrity": integrity, "data_checks": data_checks,
             "old_saved_validation_recomputation": old_reproduced,
             "original_report_values": {"identity_errors": 156, "pymatching_errors": 11,
                 "direct_mlp_errors": 156, "unweighted_cnn_errors": 156,
                 "weighted_cnn_errors_at_0_5": 183, "residual_errors": 11},
             "old_training_prevalence": old_result["training_prevalence"],
             "old_output_and_gradient_diagnostics": gradient_diagnostics,
             "fresh_training_prevalence": target_prev,
             "feature_label_determinism_bounds": contradictions,
             "tiny_subset_feature_bounds": tiny_bound,
             "tiny_set_gate": {"passed": tiny_gate,
                 "criterion": "for both MLP and CNN, at least one balanced 256-example trial must have >=98% accuracy and >=95% recall for each class",
                 "results": tiny_results},
             "scale_comparison_status": scale_status,
             "scale_comparison_results": scale_results,
             "runtime_seconds": time.monotonic() - START,
             "device": str(device), "cuda_available": torch.cuda.is_available(),
             "cuda_device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
             "resource_usage": {"host_peak_rss_bytes": resource_state["peak_rss_bytes"],
                                "cuda_peak_allocated_bytes": int(torch.cuda.max_memory_allocated(0)) if device.type == "cuda" else None,
                                "cuda_peak_reserved_bytes": int(torch.cuda.max_memory_reserved(0)) if device.type == "cuda" else None,
                                "monitor_interval_seconds": 0.5},
             "torch_version": torch.__version__, "numpy_version": np.__version__,
             "source_sha256": {"diagnose.py": sha256(Path(__file__)),
                               "neural_collapse_diagnostics.py": sha256(REPO / "dashboard/neural_collapse_diagnostics.py"),
                               "structured_training.py": sha256(REPO / "dashboard/structured_training.py"),
                               "structured_decoder.py": sha256(REPO / "dashboard/structured_decoder.py"),
                               "simulator.py": sha256(REPO / "dashboard/simulator.py")}}
    atomic_json(OUT / "diagnostic_results.json", final)
    atomic_json(OUT / "data_integrity.json", data_checks)
    atomic_json(OUT / "feature_determinism.json", {"feature_label_determinism_bounds": contradictions,
                                                    "tiny_subset_feature_bounds": tiny_bound})
    (OUT / "tiny_set_results.csv").write_text(
        "model,case,n,positive_count,learning_rate,positive_weight,epochs_run,accuracy,positive_recall,negative_recall,tn,fp,fn,tp\n" +
        "\n".join(",".join(str(v) for v in [x["model"], x["case"], x["n"], x["positive_count"], x["learning_rate"],
            x["positive_weight"], x["epochs_run"], x["train_accuracy"], x["positive_recall"], x["negative_recall"],
            x["confusion_at_0_5"]["tn"], x["confusion_at_0_5"]["fp"], x["confusion_at_0_5"]["fn"], x["confusion_at_0_5"]["tp"]]) for x in tiny_results) + "\n", encoding="utf-8")
    print(json.dumps({"status": final["status"], "old_manifest": integrity,
                      "fresh_train": len(train["observable"]), "fresh_validation": len(val["observable"]),
                      "test_access": 0, "tiny_gate": tiny_gate, "scale_status": scale_status,
                      "device": str(device), "runtime_seconds": final["runtime_seconds"],
                      "seed_inventory": "PASS", "output": str(OUT / "diagnostic_results.json")}, indent=2))


if __name__ == "__main__":
    main()
