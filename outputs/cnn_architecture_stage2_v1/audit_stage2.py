"""Independent, read-only rescoring of the frozen Stage 2 development evidence.

This module deliberately does not import the Stage 2 runner or its reporting
helpers. It reconstructs the two matching decoders, validates raw split bundles,
recomputes model predictions from frozen weights, and derives all metrics from
the saved final arrays.
"""
from __future__ import annotations

import hashlib
import csv
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pymatching
import stim
import torch

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "dashboard") not in sys.path:
    sys.path.insert(0, str(ROOT / "dashboard"))

from outputs.cnn_architecture_stage1_v1.cnn_architectures import (  # noqa: E402
    FactorizedSpatialTemporalResidualCNN,
    ResidualPositionCNNV2,
)
from outputs.neural_decoder_diagnostic.autonomous_development.experiment import (  # noqa: E402
    ResidualPositionCNN as HistoricalResidualPositionCNN,
)
from outputs.phase3a_correlated_noise_preflight.simulator import (  # noqa: E402
    build_matching,
    build_spatial_burst_circuit,
)

CONFIG = HERE / "stage2_config.json"
INVENTORY = HERE / "seed_inventory.json"
FREEZE = HERE / "FREEZE_IMPLEMENTATION_V4.json"
CONDITIONS = ("nominal", "synthetic_spatial_burst")
MODELS = (
    "historical_residual_position_cnn",
    "residual_position_v2",
    "factorized_spatiotemporal_residual",
)
T_CRIT_DF4_95 = 2.7764451051977987


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def hash_array(value: np.ndarray) -> str:
    arr = np.ascontiguousarray(value)
    h = hashlib.sha256()
    h.update(str(arr.dtype).encode())
    h.update(json.dumps(list(arr.shape), separators=(",", ":")).encode())
    h.update(arr.tobytes())
    return h.hexdigest()


def _binary(a: np.ndarray, label: str) -> np.ndarray:
    out = np.asarray(a)
    if not np.isin(out, (0, 1)).all():
        raise ValueError(f"{label} contains non-binary values")
    return out.astype(np.uint8, copy=False)


def _partition_paths(run_dir: Path, root_id: str, split: str, condition: str) -> tuple[Path, Path]:
    base = run_dir / "raw" / root_id / f"{split}__{condition}"
    return base.with_suffix(".npz"), base.with_suffix(".json")


def _load_partition(run_dir: Path, root_id: str, split: str, condition: str,
                    expected_rows: int, seed_record: dict) -> tuple[dict[str, np.ndarray], dict]:
    archive, meta_path = _partition_paths(run_dir, root_id, split, condition)
    if not archive.is_file() or not meta_path.is_file():
        raise FileNotFoundError(f"Missing split evidence: {archive} or {meta_path}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if sha256_file(archive) != meta.get("archive_sha256"):
        raise ValueError(f"Archive SHA-256 mismatch: {archive}")
    if (meta.get("root_id"), meta.get("split"), meta.get("condition")) != (root_id, split, condition):
        raise ValueError(f"Filename/metadata identity mismatch: {archive}")
    if (meta.get("seed"), meta.get("shots")) != (int(seed_record["seed"]), expected_rows):
        raise ValueError(f"Seed/shot metadata mismatch: {meta_path}")
    with np.load(archive, allow_pickle=False) as z:
        arrays = {key: z[key] for key in z.files}
    required = {"detectors", "observable", "nominal_prediction", "burst_prediction"}
    if not required.issubset(arrays):
        raise ValueError(f"Required arrays missing from {archive}: {sorted(required - set(arrays))}")
    d = _binary(arrays["detectors"], "detectors")
    y = _binary(arrays["observable"], "observable")
    n = len(d)
    if d.shape != (expected_rows, 40) or y.shape != (expected_rows,):
        raise ValueError(f"Detector/observable shape mismatch in {archive}: {d.shape}, {y.shape}")
    for key in ("nominal_prediction", "burst_prediction"):
        if _binary(arrays[key], key).shape != (n,):
            raise ValueError(f"{key} shape mismatch in {archive}")
    hashes = {key: hash_array(arrays[key]) for key in sorted(arrays)}
    if hashes != meta.get("array_sha256"):
        raise ValueError(f"Array content hashes mismatch: {archive}")
    return arrays, meta


def _model(name: str, coords: dict) -> torch.nn.Module:
    if name == MODELS[0]:
        return HistoricalResidualPositionCNN(coords, channels=4, head_width=16, dropout=0.05)
    if name == MODELS[1]:
        return ResidualPositionCNNV2(coords, channels=4, head_width=32, dropout=0.05)
    if name == MODELS[2]:
        return FactorizedSpatialTemporalResidualCNN(coords, channels=4, head_width=32, dropout=0.05)
    raise ValueError(f"Unknown frozen model: {name}")


def _state_dict_hash(state: dict[str, torch.Tensor]) -> str:
    h = hashlib.sha256()
    for key in sorted(state):
        tensor = state[key].detach().cpu().contiguous()
        h.update(key.encode())
        h.update(str(tensor.dtype).encode())
        h.update(np.asarray(tensor.shape, dtype=np.int64).tobytes())
        h.update(tensor.numpy().tobytes())
    return h.hexdigest()


def _build_context(cfg: dict) -> tuple[dict, dict]:
    c = cfg["circuit"]
    circuits = {
        "nominal": build_spatial_burst_circuit(
            memory_basis=c["memory_basis"], regime=c["pauli_regime"], distance=c["distance"],
            rounds=c["rounds"], gate_p=c["gate_probability"], measurement_p=c["measurement_probability"],
            bias_ratio=c["bias_ratio"],
            burst_probability=c["conditions"]["nominal"]["burst_probability_per_round"],
            burst_pair=tuple(c["conditions"]["nominal"]["burst_pair_data_qubits"])),
        "synthetic_spatial_burst": build_spatial_burst_circuit(
            memory_basis=c["memory_basis"], regime=c["pauli_regime"], distance=c["distance"],
            rounds=c["rounds"], gate_p=c["gate_probability"], measurement_p=c["measurement_probability"],
            bias_ratio=c["bias_ratio"],
            burst_probability=c["conditions"]["synthetic_spatial_burst"]["burst_probability_per_round"],
            burst_pair=tuple(c["conditions"]["synthetic_spatial_burst"]["burst_pair_data_qubits"])),
    }
    if any((circuits[k].num_detectors, circuits[k].num_observables) != (40, 1) for k in CONDITIONS):
        raise ValueError("Rebuilt circuit dimensions differ from frozen 40-detector/one-observable signature")
    coords = circuits["nominal"].get_detector_coordinates()
    if coords != circuits["synthetic_spatial_burst"].get_detector_coordinates():
        raise ValueError("Condition-specific detector coordinates differ")
    matchers = {}
    for condition in CONDITIONS:
        dem, matcher = build_matching(circuits[condition], enable_correlations=True)
        if (dem.num_detectors, dem.num_observables, matcher.num_detectors) != (40, 1, 40):
            raise ValueError(f"Invalid rebuilt matching model for {condition}")
        matchers[condition] = matcher
    return {"circuits": circuits, "matchers": matchers, "coordinates": coords}, {
        condition: hashlib.sha256(str(circuit).encode()).hexdigest()
        for condition, circuit in circuits.items()
    }


def _decode(matcher, detectors: np.ndarray) -> np.ndarray:
    pred = np.asarray(matcher.decode_batch(detectors), dtype=np.uint8).reshape(-1)
    if pred.shape != (len(detectors),) or not np.isin(pred, (0, 1)).all():
        raise ValueError("Matching predictions have invalid shape or values")
    return pred


def _nll(logits: np.ndarray, labels: np.ndarray) -> float:
    z = np.clip(np.asarray(logits, dtype=np.float64), -60, 60)
    y = np.asarray(labels, dtype=np.float64)
    return float(np.mean(np.logaddexp(0.0, z) - y * z))


def _model_logits(model: torch.nn.Module, arrays: dict, device: torch.device) -> np.ndarray:
    outputs = []
    model.eval()
    with torch.inference_mode():
        for start in range(0, len(arrays["observable"]), 1024):
            x = torch.as_tensor(arrays["detectors"][start:start + 1024], dtype=torch.float32, device=device)
            pm = torch.as_tensor(arrays["nominal_prediction"][start:start + 1024], dtype=torch.float32, device=device)
            logits = model(x, pm).float()
            if not torch.isfinite(logits).all():
                raise ValueError("Non-finite independently recomputed model logits")
            outputs.append(logits.detach().cpu().numpy().astype(np.float64))
    return np.concatenate(outputs)


def _verify_selection_rules(root_id: str, model_name: str, selection: dict,
                            weights_path: Path, split_arrays: dict, coords: dict,
                            device: torch.device, cfg: dict) -> None:
    """Reproduce monitor checkpoint score and calibration/threshold choices."""
    payload = torch.load(weights_path, map_location="cpu", weights_only=False)
    if payload.get("state_dict_sha256") != selection.get("selected_state_dict_sha256"):
        raise ValueError(f"Selected weight state hash does not match selection record: {root_id}/{model_name}")
    model = _model(model_name, coords).to(device)
    model.load_state_dict(payload["model_state"])
    prevalence = float(selection["pooled_residual_training_prevalence"])
    prior = math.log(max(prevalence, 1e-8) / max(1 - prevalence, 1e-8))

    def logits_for(split: str) -> dict[str, np.ndarray]:
        return {condition: _model_logits(model, split_arrays[(split, condition)], device) + prior
                for condition in CONDITIONS}

    monitor_logits = logits_for("monitor")
    monitor_score = float(np.mean([
        _nll(monitor_logits[c],
             split_arrays[("monitor", c)]["observable"] ^ split_arrays[("monitor", c)]["nominal_prediction"])
        for c in CONDITIONS
    ]))
    if not np.isclose(monitor_score, float(selection["best_monitor_nll"]), rtol=0, atol=2e-6):
        raise ValueError(f"Best-monitor checkpoint score does not reproduce: {root_id}/{model_name}")
    history = selection.get("history", [])
    best_so_far = float("inf")
    expected_epoch = None
    for row in history:
        score = float(row["monitor_equal_condition_nll"])
        if score < best_so_far - 1e-9:
            best_so_far = score
            expected_epoch = int(row["epoch"])
    if expected_epoch != int(selection["best_epoch"]):
        raise ValueError(f"Best-checkpoint epoch does not match monitor history: {root_id}/{model_name}")

    calibration_logits = logits_for("probability_calibration")
    temperatures = []
    for temp in cfg["selection"]["temperature_grid"]:
        score = float(np.mean([
            _nll(calibration_logits[c] / float(temp),
                 split_arrays[("probability_calibration", c)]["observable"] ^
                 split_arrays[("probability_calibration", c)]["nominal_prediction"])
            for c in CONDITIONS
        ]))
        temperatures.append((score, abs(float(temp) - 1.0), float(temp)))
    expected_temp = min(temperatures)[2]
    if expected_temp != float(selection["temperature"]):
        raise ValueError(f"Probability-calibration temperature does not reproduce: {root_id}/{model_name}")

    threshold_logits = logits_for("threshold_selection")
    threshold_candidates = []
    for threshold in (i / 100 for i in range(1, 100)):
        lers = []
        for condition in CONDITIONS:
            p = 1.0 / (1.0 + np.exp(-np.clip(threshold_logits[condition] / expected_temp, -60, 60)))
            residual_hat = (p >= threshold).astype(np.uint8)
            arrays = split_arrays[("threshold_selection", condition)]
            pred = arrays["nominal_prediction"] ^ residual_hat
            lers.append(float(np.mean(pred ^ arrays["observable"])))
        threshold_candidates.append((float(np.mean(lers)), abs(threshold - 0.5), threshold))
    expected_threshold = min(threshold_candidates)[2]
    if expected_threshold != float(selection["threshold"]):
        raise ValueError(f"Threshold-selection result does not reproduce: {root_id}/{model_name}")
    expected_positive_counts = {
        split: {c: int((split_arrays[(split, c)]["observable"] ^
                        split_arrays[(split, c)]["nominal_prediction"]).sum()) for c in CONDITIONS}
        for split in ("training", "monitor", "probability_calibration", "threshold_selection")
    }
    if selection.get("positive_counts_by_split_and_condition") != expected_positive_counts:
        raise ValueError(f"Saved split residual-positive counts do not reproduce: {root_id}/{model_name}")


def _recompute_metrics(y: np.ndarray, pm: np.ndarray, burst: np.ndarray,
                       predictions: dict[str, np.ndarray], probabilities: dict[str, np.ndarray],
                       selections: dict[str, dict], condition: str) -> dict:
    pm_err = pm ^ y
    result = {
        "shots": int(len(y)),
        "observable_positive_count": int(y.sum()),
        "nominal_fixed_errors": int(pm_err.sum()),
        "nominal_fixed_ler": float(pm_err.mean()),
        "burst_informed_errors": int(np.sum(burst ^ y)) if condition == "synthetic_spatial_burst" else None,
        "burst_informed_ler": float(np.mean(burst ^ y)) if condition == "synthetic_spatial_burst" else None,
    }
    if condition == "synthetic_spatial_burst":
        burst_err = burst ^ y
        result["burst_informed_candidate_only"] = int(np.sum((burst_err == 1) & (pm_err == 0)))
        result["burst_informed_nominal_only"] = int(np.sum((burst_err == 0) & (pm_err == 1)))
    for name in MODELS:
        pred = predictions[name]
        prob = np.asarray(probabilities[name], dtype=np.float32)
        if pred.shape != y.shape or not np.isin(pred, (0, 1)).all():
            raise ValueError(f"Prediction shape/value failure for {condition}/{name}")
        if prob.shape != y.shape or not np.isfinite(prob).all() or np.any((prob < 0) | (prob > 1)):
            raise ValueError(f"Probability shape/value failure for {condition}/{name}")
        err = pred ^ y
        correction = pred ^ pm
        residual = y ^ pm
        true_positive_correction = int(np.sum((correction == 1) & (pm_err == 1)))
        residual_logits = np.log(np.clip(prob, 1e-12, 1 - 1e-12) /
                                 np.clip(1 - prob, 1e-12, 1))
        residual_nll = _nll(residual_logits, residual)
        result[name] = {
            "errors": int(err.sum()), "ler": float(err.mean()),
            "prediction_positive_count": int(pred.sum()),
            "residual_positive_count": int(residual.sum()),
            "candidate_only_failures": int(np.sum((err == 1) & (pm_err == 0))),
            "pymatching_only_failures": int(np.sum((err == 0) & (pm_err == 1))),
            "prediction_disagreements": int(np.sum(pred != pm)),
            "useful_corrections": int(np.sum((correction == 1) & (pm_err == 1) & (err == 0))),
            "harmful_corrections": int(np.sum((correction == 1) & (pm_err == 0) & (err == 1))),
            "positive_precision": float(true_positive_correction / max(1, int(np.sum(correction == 1)))),
            "positive_recall": float(true_positive_correction / max(1, int(pm_err.sum()))),
            "brier_score_residual": float(np.mean((prob - residual) ** 2)),
            "residual_nll": float(residual_nll),
            "threshold": float(selections[name]["threshold"]),
            "temperature": float(selections[name]["temperature"]),
        }
    return result


def _mean_t_interval(values: list[float]) -> dict:
    a = np.asarray(values, dtype=np.float64)
    mean = float(a.mean())
    sd = float(a.std(ddof=1)) if len(a) > 1 else None
    margin = T_CRIT_DF4_95 * sd / math.sqrt(len(a)) if sd is not None and len(a) == 5 else None
    return {"mean": mean, "sd": sd,
            "ci95": [mean - margin, mean + margin] if margin is not None else None,
            "n_roots": int(len(a)),
            "interpretation": "descriptive root-level Student-t interval; not a confirmatory test"}


def _assert_json_metrics_close(left: Any, right: Any, where: str = "metrics") -> None:
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            raise ValueError(f"{where}: key sets differ")
        for key in left:
            _assert_json_metrics_close(left[key], right[key], f"{where}.{key}")
        return
    if isinstance(left, (int, np.integer)) or isinstance(right, (int, np.integer)):
        if left != right:
            raise ValueError(f"{where}: integer values differ ({left} vs {right})")
        return
    if isinstance(left, (float, np.floating)) or isinstance(right, (float, np.floating)):
        if left is None or right is None:
            if left is not right:
                raise ValueError(f"{where}: optional values differ")
        elif not np.isclose(float(left), float(right), rtol=1e-7, atol=1e-8):
            raise ValueError(f"{where}: values differ ({left} vs {right})")
        return
    if left != right:
        raise ValueError(f"{where}: values differ ({left!r} vs {right!r})")


def independently_rescore(run_dir: Path, *, write_outputs: bool = True) -> dict:
    run_dir = Path(run_dir)
    failures: list[str] = []
    per_root: dict[str, Any] = {}
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
        freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
        if freeze.get("status") != "FROZEN_IMPLEMENTATION_V4_NOT_EXECUTED":
            raise ValueError("Unexpected pre-sampling freeze status or modified freeze")
        old_freeze = HERE / "FREEZE.json"
        if sha256_file(old_freeze) != freeze.get("historical_original_freeze_sha256"):
            raise ValueError("Superseded historical freeze hash mismatch")
        if sha256_file(HERE / "FREEZE_IMPLEMENTATION_V3.json") != freeze.get("supersedes_freeze_file_sha256"):
            raise ValueError("Immediately superseded V3 freeze hash mismatch")
        for record in freeze["source_and_protocol_files"]:
            path = ROOT / record["path"]
            if not path.is_file() or path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
                raise ValueError(f"Frozen source hash mismatch: {record['path']}")
        streams = inventory["streams"]
        seeds = [int(row["seed"]) for row in streams]
        if len(streams) != 95 or len(set(seeds)) != 95:
            raise ValueError("Seed inventory count/uniqueness failure")
        protocol_body = json.dumps({"files": freeze["source_and_protocol_files"], "inventory": inventory},
                                   sort_keys=True, separators=(",", ":")).encode("utf-8")
        if hashlib.sha256(protocol_body).hexdigest() != freeze.get("protocol_id_sha256"):
            raise ValueError("Implementation freeze protocol ID does not match frozen source and seed inventory")
        seed_lookup = {}
        for row in streams:
            if row["kind"] == "stim_sample_stream":
                seed_lookup[(row["root_id"], row["split"], row["condition"])] = row
        context, circuit_hashes = _build_context(cfg)
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        if not torch.cuda.is_available():
            raise ValueError("CUDA is required by the frozen inference environment")
        status = json.loads((run_dir / "raw" / "status.json").read_text(encoding="utf-8"))
        if status.get("independent_test_accessed") is not False:
            raise ValueError("Persisted status does not affirm sealed independent-test state")
        if status.get("circuit_sha256") != circuit_hashes:
            raise ValueError("Runner circuit hashes differ from independently reconstructed circuits")
        manifest_path = run_dir / "raw" / "selection_manifest_before_final.json"
        selection_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if selection_manifest.get("final_development_accessed_at_freeze") is not False:
            raise ValueError("Selection manifest records final-development access before freeze")
        manifest_check = dict(selection_manifest)
        manifest_digest = manifest_check.pop("manifest_sha256", None)
        if manifest_digest != hashlib.sha256(json.dumps(manifest_check, sort_keys=True, separators=(",", ":")).encode()).hexdigest():
            raise ValueError("Global pre-final selection manifest hash is invalid")
        selection_rows = selection_manifest.get("selections", [])
        expected_pairs = {(f"dev-root-{i:02d}", m) for i in range(5) for m in MODELS}
        if len(selection_rows) != 15 or {(r["root_id"], r["model"]) for r in selection_rows} != expected_pairs:
            raise ValueError("Global selection manifest lacks all 15 model/root selections")
        selection_file_map = {}
        for row in selection_rows:
            rid, model_name = row["root_id"], row["model"]
            selection_path = run_dir / "raw" / rid / "selections" / f"{model_name}.json"
            weight_path = run_dir / "checkpoints" / rid / f"{model_name}_selected.pt"
            if sha256_file(selection_path) != row["selection_sha256"] or sha256_file(weight_path) != row["weights_sha256"]:
                raise ValueError(f"Frozen selection hash mismatch: {rid}/{model_name}")
            selection = json.loads(selection_path.read_text(encoding="utf-8"))
            if selection.get("final_development_data_accessed") is not False:
                raise ValueError(f"Selection metadata permits leakage: {rid}/{model_name}")
            selection_file_map[(rid, model_name)] = (selection, weight_path)

        expected_splits = cfg["shots_per_root_condition"]
        for root_index in range(5):
            root_id = f"dev-root-{root_index:02d}"
            prediction_path = run_dir / "predictions" / f"{root_id}.npz"
            if not prediction_path.is_file():
                raise FileNotFoundError(f"Missing saved prediction evidence: {prediction_path}")
            with np.load(prediction_path, allow_pickle=False) as z:
                saved_predictions = {key: z[key] for key in z.files}
            split_arrays = {}
            # Audit every generated train/monitor/calibration/threshold partition, not just final rows.
            for split, shots in expected_splits.items():
                for condition in CONDITIONS:
                    arrays, meta = _load_partition(
                        run_dir, root_id, split, condition, int(shots),
                        seed_lookup[(root_id, split, condition)])
                    if split == "training" and root_id == "dev-root-00" and condition == "nominal":
                        prefix_path = run_dir / "raw" / root_id / "training__nominal_prefix256.npz"
                        if not prefix_path.is_file():
                            raise FileNotFoundError("Permitted 256-shot training prefix is missing")
                        with np.load(prefix_path, allow_pickle=False) as z:
                            prefix = {key: z[key] for key in z.files}
                        for key in arrays:
                            if not np.array_equal(prefix[key], arrays[key][:256]):
                                raise ValueError("Dry-run prefix is not byte-identical to the allocated training prefix")
                    expected_nominal = _decode(context["matchers"]["nominal"], arrays["detectors"])
                    if not np.array_equal(expected_nominal, arrays["nominal_prediction"]):
                        raise ValueError(f"Nominal matcher predictions do not reproduce on {root_id}/{split}/{condition}")
                    if condition == "synthetic_spatial_burst":
                        expected_burst = _decode(context["matchers"][condition], arrays["detectors"])
                    else:
                        expected_burst = expected_nominal
                    if not np.array_equal(expected_burst, arrays["burst_prediction"]):
                        raise ValueError(f"Burst matcher/nominal alias predictions mismatch on {root_id}/{split}/{condition}")
                    split_arrays[(split, condition)] = arrays
            for model_name in MODELS:
                selection, weights_path = selection_file_map[(root_id, model_name)]
                expected_split_hashes = {
                    split: {condition: {key: hash_array(split_arrays[(split, condition)][key])
                                        for key in sorted(split_arrays[(split, condition)])}
                            for condition in CONDITIONS}
                    for split in ("training", "monitor", "probability_calibration", "threshold_selection")
                }
                if selection.get("shared_partition_array_hashes") != expected_split_hashes:
                    raise ValueError(f"Selection's shared partition hashes do not match: {root_id}/{model_name}")
                _verify_selection_rules(root_id, model_name, selection, weights_path,
                                        split_arrays, context["coordinates"], device, cfg)

            final = {}
            for condition in CONDITIONS:
                arrays, meta = _load_partition(
                    run_dir, root_id, "final_development_evaluation", condition,
                    int(expected_splits["final_development_evaluation"]),
                    seed_lookup[(root_id, "final_development_evaluation", condition)])
                if meta.get("selection_hashes_before_final_sampling") != selection_rows:
                    raise ValueError(f"Final partition is not tied to the global selection freeze: {root_id}/{condition}")
                if not np.array_equal(arrays["nominal_prediction"], _decode(context["matchers"]["nominal"], arrays["detectors"])):
                    raise ValueError(f"Nominal matching output mismatch on final {root_id}/{condition}")
                burst_redecoded = (_decode(context["matchers"][condition], arrays["detectors"])
                                   if condition == "synthetic_spatial_burst"
                                   else arrays["nominal_prediction"])
                if not np.array_equal(arrays["burst_prediction"], burst_redecoded):
                    raise ValueError(f"Burst matching output mismatch on final {root_id}/{condition}")
                for field in ("detectors", "observable", "nominal_prediction", "burst_prediction"):
                    saved = saved_predictions.get(f"{condition}__{field}")
                    if saved is None or not np.array_equal(saved, arrays[field]):
                        raise ValueError(f"Saved paired prediction input mismatch {root_id}/{condition}/{field}")
                final[condition] = arrays

            selection_by_model = {m: selection_file_map[(root_id, m)][0] for m in MODELS}
            independently_recomputed_conditions = {}
            for condition in CONDITIONS:
                data = final[condition]
                y = _binary(data["observable"], "final observable")
                pm = _binary(data["nominal_prediction"], "nominal prediction")
                burst = _binary(data["burst_prediction"], "burst prediction")
                model_predictions, model_probabilities = {}, {}
                for model_name in MODELS:
                    selection, weights_path = selection_file_map[(root_id, model_name)]
                    payload = torch.load(weights_path, map_location="cpu", weights_only=False)
                    if payload.get("config_sha256") != sha256_file(CONFIG):
                        raise ValueError(f"Model config hash mismatch: {root_id}/{model_name}")
                    if payload.get("model_name") != model_name or payload.get("root_id") != root_id:
                        raise ValueError(f"Selected checkpoint identity mismatch: {root_id}/{model_name}")
                    if _state_dict_hash(payload["model_state"]) != selection.get("selected_state_dict_sha256"):
                        raise ValueError(f"Selected checkpoint state hash mismatch: {root_id}/{model_name}")
                    model = _model(model_name, context["coordinates"]).to(device)
                    model.load_state_dict(payload["model_state"])
                    model.eval()
                    outputs = []
                    with torch.inference_mode():
                        for start in range(0, len(y), 1024):
                            x = torch.as_tensor(data["detectors"][start:start + 1024], dtype=torch.float32, device=device)
                            p = torch.as_tensor(pm[start:start + 1024], dtype=torch.float32, device=device)
                            values = model(x, p).float()
                            if not torch.isfinite(values).all():
                                raise ValueError(f"Non-finite recomputed logits: {root_id}/{model_name}")
                            outputs.append(values.detach().cpu().numpy().astype(np.float64))
                    prior = math.log(max(float(selection["pooled_residual_training_prevalence"]), 1e-8) /
                                     max(1 - float(selection["pooled_residual_training_prevalence"]), 1e-8))
                    logits = np.concatenate(outputs) + prior
                    temp = float(selection["temperature"])
                    threshold = float(selection["threshold"])
                    prob = 1.0 / (1.0 + np.exp(-np.clip(logits / temp, -60, 60)))
                    correction = (prob >= threshold).astype(np.uint8)
                    pred = pm ^ correction
                    prefix = f"{condition}__{model_name}__"
                    if not np.allclose(saved_predictions[prefix + "logits"], logits.astype(np.float32), rtol=0, atol=2e-6):
                        raise ValueError(f"Saved neural logits fail independent recomputation: {root_id}/{condition}/{model_name}")
                    if not np.allclose(saved_predictions[prefix + "probability"], prob.astype(np.float32), rtol=0, atol=2e-6):
                        raise ValueError(f"Saved neural probabilities fail independent recomputation: {root_id}/{condition}/{model_name}")
                    if not np.array_equal(saved_predictions[prefix + "prediction"], pred):
                        raise ValueError(f"Saved neural prediction fails independent recomputation: {root_id}/{condition}/{model_name}")
                    # Metrics are rescored from the persisted evidence, after its
                    # probabilities/predictions have been independently reproduced.
                    model_predictions[model_name] = _binary(saved_predictions[prefix + "prediction"], "saved CNN prediction")
                    model_probabilities[model_name] = np.asarray(saved_predictions[prefix + "probability"], dtype=np.float32)
                    del model
                    if device.type == "cuda":
                        torch.cuda.empty_cache()
                independently_recomputed_conditions[condition] = _recompute_metrics(
                    y, pm, burst, model_predictions, model_probabilities, selection_by_model, condition)
            selection_diagnostics = {}
            for model_name in MODELS:
                selection, _ = selection_file_map[(root_id, model_name)]
                selection_diagnostics[model_name] = {
                    "parameter_count": int(selection["parameter_count"]),
                    "best_epoch": int(selection["best_epoch"]),
                    "epochs_completed": int(selection["epochs_completed"]),
                    "optimizer_steps": int(selection["optimizer_steps"]),
                    "temperature": float(selection["temperature"]),
                    "threshold": float(selection["threshold"]),
                    "pooled_residual_training_prevalence": float(selection["pooled_residual_training_prevalence"]),
                    "positive_counts_by_split_and_condition": selection["positive_counts_by_split_and_condition"],
                    "positive_draws_total_by_condition": selection["positive_draws_total_by_condition"],
                    "positive_example_reuse_ratio_by_condition": selection["positive_example_reuse_ratio_by_condition"],
                }
            runner_root_result = json.loads((run_dir / "raw" / "per_root_results.json").read_text(encoding="utf-8")).get(root_id, {})
            per_root[root_id] = {
                "root_id": root_id, "conditions": independently_recomputed_conditions,
                "prediction_archive_sha256": sha256_file(prediction_path),
                "selection_diagnostics": selection_diagnostics,
                "model_runtime": runner_root_result.get("model_runtime", {}),
            }

        if len(per_root) != 5:
            raise ValueError(f"Expected all 5 roots; independently audited {len(per_root)}")
        by_split = {split: int(expected_splits[split]) * 2 * 5 for split in expected_splits}
        if sum(by_split.values()) != int(cfg["total_unique_shot_ceiling"]):
            raise ValueError("Frozen sample allocation does not sum to the total ceiling")
        if status.get("completed_unique_shots") != sum(by_split.values()):
            raise ValueError("Persisted completion shot count differs from independently accounted partitions")
        if len(status.get("completed_jobs", [])) != 15 or status.get("completed_model_root_jobs") != 15:
            raise ValueError("Not all 15 model/root training jobs are accounted for")

        model_summary = {}
        for condition in CONDITIONS:
            model_summary[condition] = {}
            for model_name in MODELS:
                roots = [per_root[f"dev-root-{i:02d}"]["conditions"][condition][model_name] for i in range(5)]
                model_summary[condition][model_name] = {
                    "errors": int(sum(x["errors"] for x in roots)),
                    "shots": int(sum(x["shots"] for x in roots)),
                    "ler": float(sum(x["errors"] for x in roots) / sum(x["shots"] for x in roots)),
                }
        primary_roots = []
        for i in range(5):
            rid = f"dev-root-{i:02d}"
            deltas = []
            for condition in CONDITIONS:
                condition_result = per_root[rid]["conditions"][condition]
                deltas.append(condition_result[MODELS[1]]["ler"] - condition_result["nominal_fixed_ler"])
            primary_roots.append({"root_id": rid, "equal_condition_delta": float(np.mean(deltas)),
                                  "condition_deltas": dict(zip(CONDITIONS, map(float, deltas)))})
        primary_interval = _mean_t_interval([row["equal_condition_delta"] for row in primary_roots])
        paired_comparisons = {}
        for condition in CONDITIONS:
            paired_comparisons[condition] = {}
            for model_name in MODELS:
                deltas = []
                candidate_only = fixed_only = disagreements = shots = candidate_errors = fixed_errors = 0
                for i in range(5):
                    metric = per_root[f"dev-root-{i:02d}"]["conditions"][condition]
                    candidate = metric[model_name]
                    shots += metric["shots"]
                    candidate_errors += candidate["errors"]
                    fixed_errors += metric["nominal_fixed_errors"]
                    candidate_only += candidate["candidate_only_failures"]
                    fixed_only += candidate["pymatching_only_failures"]
                    disagreements += candidate["prediction_disagreements"]
                    deltas.append(candidate["ler"] - metric["nominal_fixed_ler"])
                paired_comparisons[condition][model_name] = {
                    "candidate_errors": candidate_errors, "fixed_errors": fixed_errors,
                    "shots": shots, "candidate_ler": candidate_errors / shots,
                    "fixed_ler": fixed_errors / shots,
                    "paired_absolute_ler_difference": candidate_errors / shots - fixed_errors / shots,
                    "relative_error_reduction": ((fixed_errors - candidate_errors) / fixed_errors) if fixed_errors else None,
                    "candidate_only_failures": candidate_only, "pymatching_only_failures": fixed_only,
                    "prediction_disagreements": disagreements,
                    "per_root_differences": deltas,
                    "root_level_interval": _mean_t_interval(deltas),
                }
        burst_reference = []
        for i in range(5):
            metric = per_root[f"dev-root-{i:02d}"]["conditions"]["synthetic_spatial_burst"]
            burst_reference.append(metric["burst_informed_ler"] - metric["nominal_fixed_ler"])
        primary_mean = primary_interval["mean"]
        wins = sum(row["equal_condition_delta"] < 0 for row in primary_roots)
        condition_harm = {condition: float(np.mean([
            per_root[f"dev-root-{i:02d}"]["conditions"][condition][MODELS[1]]["ler"] -
            per_root[f"dev-root-{i:02d}"]["conditions"][condition]["nominal_fixed_ler"]
            for i in range(5)])) for condition in CONDITIONS}
        gate_pass = (primary_mean <= -0.0002 and wins >= 4 and
                     all(value <= 0.0002 for value in condition_harm.values()))
        failures.clear()
        result = {
            "status": "PASS", "audit_mode": "independent_read_only_recomputation",
            "audited_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "freeze_protocol_id_sha256": freeze["protocol_id_sha256"],
            "config_sha256": sha256_file(CONFIG), "seed_inventory_sha256": sha256_file(INVENTORY),
            "independent_test_accessed": False,
            "root_count": len(per_root), "model_root_jobs": 15,
            "unique_shots_by_split": by_split, "unique_shot_total": sum(by_split.values()),
            "per_condition_model_summary": model_summary,
            "paired_comparisons_against_nominal_fixed": paired_comparisons,
            "burst_informed_reference_on_burst_condition": {
                "per_root_ler_differences_vs_nominal_fixed": burst_reference,
                "root_level_interval": _mean_t_interval(burst_reference),
                "information_status": "privileged model-informed reference; not deployable without burst specification",
            },
            "primary_v2_minus_nominal_fixed": {"per_root": primary_roots, **primary_interval},
            "primary_development_gate": {
                "status": "PASS" if gate_pass else "FAIL",
                "mean_delta_required_at_most": -0.0002,
                "observed_mean_delta": primary_mean,
                "favorable_roots_required": 4,
                "observed_favorable_roots": wins,
                "condition_mean_harm_limit": 0.0002,
                "observed_condition_mean_deltas": condition_harm,
                "note": "Frozen development feasibility gate; not a confirmatory significance test.",
            },
            "per_root": per_root,
            "source_note": "Test predictions and matching baselines were recomputed from saved detector arrays; no independent-test allocation or files were read.",
        }
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")
        result = {"status": "FAIL", "audit_mode": "independent_read_only_recomputation",
                  "failures": failures, "independent_test_accessed": False}

    if write_outputs:
        audit_path = run_dir / "independent_audit.json"
        tmp = audit_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        tmp.replace(audit_path)
        if result.get("status") == "PASS":
            raw = json.loads((run_dir / "raw" / "per_root_results.json").read_text(encoding="utf-8"))
            if set(raw) != set(result["per_root"]):
                result["status"] = "FAIL"
                result["failures"] = ["Runner per-root result inventory differs from independent recomputation"]
            else:
                for rid, record in result["per_root"].items():
                    if raw[rid].get("prediction_archive_sha256") != record["prediction_archive_sha256"]:
                        result["status"] = "FAIL"
                        result["failures"] = [f"Runner prediction archive hash mismatch for {rid}"]
                        break
                    for condition in CONDITIONS:
                        try:
                            _assert_json_metrics_close(raw[rid]["conditions"][condition],
                                                       record["conditions"][condition], f"{rid}/{condition}")
                        except ValueError as exc:
                            result["status"] = "FAIL"
                            result["failures"] = [str(exc)]
                            break
            # Rewrite after cross-checking the runner-produced summary.
            tmp.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
            tmp.replace(audit_path)
            if result.get("status") == "PASS":
                _write_reports(result, run_dir)
    return result


def _write_reports(result: dict, run_dir: Path) -> None:
    lines = [
        "# Q-SHIFT CNN Stage 2 Results\n",
        "Development-only results from five independent roots. The independent test remained sealed. Root intervals are descriptive feasibility summaries, not confirmatory tests.\n",
        "## Aggregate logical errors\n",
        "\n| Condition | Decoder | Errors / shots | LER |\n|---|---|---:|---:|",
    ]
    for condition in CONDITIONS:
        roots = [result["per_root"][f"dev-root-{i:02d}"]["conditions"][condition] for i in range(5)]
        shots = sum(row["shots"] for row in roots)
        fixed_errors = sum(row["nominal_fixed_errors"] for row in roots)
        lines.append(f"| {condition} | Nominal fixed PyMatching | {fixed_errors} / {shots} | {fixed_errors / shots:.6f} |")
        for model_name in MODELS:
            row = result["per_condition_model_summary"][condition][model_name]
            lines.append(f"| {condition} | {model_name} | {row['errors']} / {row['shots']} | {row['ler']:.6f} |")
        if condition == "synthetic_spatial_burst":
            burst_errors = sum(row["burst_informed_errors"] for row in roots)
            lines.append(f"| {condition} | Burst-informed PyMatching (privileged) | {burst_errors} / {shots} | {burst_errors / shots:.6f} |")
    primary = result["primary_v2_minus_nominal_fixed"]
    gate = result["primary_development_gate"]
    lines.extend([
        "\n## Paired comparisons with nominal fixed PyMatching\n",
        "Differences are candidate LER minus fixed-decoder LER on identical shots. Candidate-only and fixed-only counts are paired shot-level discordances. Intervals are across five independent root-level differences.\n",
        "\n| Condition | Candidate | Delta LER | 95% root interval | Candidate-only | Fixed-only | Disagreements | Useful | Harmful |\n|---|---|---:|---|---:|---:|---:|---:|---:|",
    ])
    for condition in CONDITIONS:
        for model_name in MODELS:
            comp = result["paired_comparisons_against_nominal_fixed"][condition][model_name]
            useful = sum(result["per_root"][f"dev-root-{i:02d}"]["conditions"][condition][model_name]["useful_corrections"] for i in range(5))
            harmful = sum(result["per_root"][f"dev-root-{i:02d}"]["conditions"][condition][model_name]["harmful_corrections"] for i in range(5))
            lines.append(
                f"| {condition} | {model_name} | {comp['paired_absolute_ler_difference']:+.6f} | "
                f"{comp['root_level_interval']['ci95']} | {comp['candidate_only_failures']} | "
                f"{comp['pymatching_only_failures']} | {comp['prediction_disagreements']} | {useful} | {harmful} |"
            )
    lines.extend([
        "\n## Frozen primary endpoint and development gate\n",
        f"Equal-condition root mean ResidualPositionCNNV2 minus fixed PyMatching LER difference: **{primary['mean']:+.6f}**, descriptive 95% root-level Student-t interval **{primary['ci95']}** (n=5). Favorable roots: {gate['observed_favorable_roots']}/5. Condition deltas: {gate['observed_condition_mean_deltas']}. Gate: **{gate['status']}**.\n",
        "This is a development feasibility gate and does not establish statistical superiority or authorize independent-test access.\n",
        "\n## Burst-informed reference\n",
        f"On synthetic-burst shots only, burst-informed minus fixed per-root LER differences are {result['burst_informed_reference_on_burst_condition']['per_root_ler_differences_vs_nominal_fixed']}; descriptive 95% root interval {result['burst_informed_reference_on_burst_condition']['root_level_interval']['ci95']}. This reference receives the injected burst specification and is privileged.\n",
        "\n## Per-root decoder LER\n",
        "\n| Root | Condition | Fixed PyMatching | Historical CNN | V2 CNN | Factorized CNN | Burst-informed PM |\n|---|---|---:|---:|---:|---:|---:|",
    ])
    for i in range(5):
        rid = f"dev-root-{i:02d}"
        for condition in CONDITIONS:
            row = result["per_root"][rid]["conditions"][condition]
            burst_value = f"{row['burst_informed_ler']:.6f}" if row["burst_informed_ler"] is not None else "n/a"
            lines.append(
                f"| {rid} | {condition} | {row['nominal_fixed_ler']:.6f} | "
                f"{row[MODELS[0]]['ler']:.6f} | {row[MODELS[1]]['ler']:.6f} | "
                f"{row[MODELS[2]]['ler']:.6f} | {burst_value} |"
            )
    lines.append(
        "\nPer-root optimizer steps, parameters, checkpoint epoch, calibration threshold/temperature, "
        "split-wise residual-positive counts, positive-example reuse ratios, and inference timing are recorded "
        "in the independent audit JSON. Class-balanced minibatches reuse rare examples; they do not add unique shots.\n"
    )
    (HERE / "CNN_STAGE2_RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    audit_md = [
        "# Q-SHIFT CNN Stage 2 Independent Audit\n",
        f"**Status: {result['status']}**\n",
        f"- Roots: {result['root_count']}/5; model/root jobs: {result['model_root_jobs']}/15.",
        f"- Unique shots independently accounted: {result['unique_shot_total']:,} / 260,000.",
        f"- Split totals: {result['unique_shots_by_split']}.",
        "- Independent test accessed: false.",
        "- Both matching models were rebuilt and rescored against saved detectors for each split.",
        "- CNN logits, probabilities, and predictions were independently recomputed from saved detector arrays and frozen model weights.",
        "- Monitor checkpoint selection, calibration temperatures, thresholds, residual-positive counts, seed metadata, hashes, shapes, binary values, and paired sample identity were checked.",
        "- Runner totals were compared with an independent reduction; root-level intervals are descriptive.\n",
    ]
    (HERE / "CNN_STAGE2_INDEPENDENT_AUDIT.md").write_text("\n".join(audit_md), encoding="utf-8", newline="\n")
    with (HERE / "CNN_STAGE2_PER_ROOT.csv").open("w", encoding="utf-8", newline="") as f:
        fields = ["root_id", "condition", "decoder", "shots", "errors", "ler",
                  "candidate_only_failures", "pymatching_only_failures", "prediction_disagreements",
                  "useful_corrections", "harmful_corrections"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for i in range(5):
            rid = f"dev-root-{i:02d}"
            for condition in CONDITIONS:
                row = result["per_root"][rid]["conditions"][condition]
                writer.writerow({"root_id": rid, "condition": condition, "decoder": "nominal_fixed_pymatching",
                                 "shots": row["shots"], "errors": row["nominal_fixed_errors"], "ler": row["nominal_fixed_ler"]})
                for model_name in MODELS:
                    m = row[model_name]
                    writer.writerow({"root_id": rid, "condition": condition, "decoder": model_name,
                                     "shots": row["shots"], "errors": m["errors"], "ler": m["ler"],
                                     "candidate_only_failures": m["candidate_only_failures"],
                                     "pymatching_only_failures": m["pymatching_only_failures"],
                                     "prediction_disagreements": m["prediction_disagreements"],
                                     "useful_corrections": m["useful_corrections"],
                                     "harmful_corrections": m["harmful_corrections"]})
                if condition == "synthetic_spatial_burst":
                    writer.writerow({"root_id": rid, "condition": condition,
                                     "decoder": "burst_informed_pymatching_privileged", "shots": row["shots"],
                                     "errors": row["burst_informed_errors"], "ler": row["burst_informed_ler"],
                                     "candidate_only_failures": row["burst_informed_candidate_only"],
                                     "pymatching_only_failures": row["burst_informed_nominal_only"]})


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python audit_stage2.py <run_v1 directory>")
    audited = independently_rescore(Path(sys.argv[1]), write_outputs=True)
    print(json.dumps({"status": audited.get("status"), "failures": audited.get("failures", [])}, indent=2))
    raise SystemExit(0 if audited.get("status") == "PASS" else 2)
