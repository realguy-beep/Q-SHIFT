"""Recompute saved diagnostic totals and policy predictions without new shots."""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
INTEGRATION = ROOT / "outputs/neural_decoder_diagnostic/structured_integration"
OLD_RUN = INTEGRATION / "dev_run_6000"
sys.path.insert(0, str(ROOT / "dashboard"))

from models import DirectMLP
from simulator import prepare, decode_matching
from structured_decoder import StructuredConv3DDecoder
from structured_training import REGIMES, candidate_spec


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def confusion(y, p):
    y = np.asarray(y, dtype=np.uint8); p = np.asarray(p, dtype=np.uint8)
    return {"tn": int(np.count_nonzero((y == 0) & (p == 0))),
            "fp": int(np.count_nonzero((y == 0) & (p == 1))),
            "fn": int(np.count_nonzero((y == 1) & (p == 0))),
            "tp": int(np.count_nonzero((y == 1) & (p == 1)))}


def main():
    record = json.loads((HERE / "diagnostic_results.json").read_text(encoding="utf-8"))
    inventory = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
    patch_record = json.loads((HERE / "SOURCE_CORRECTION.json").read_text(encoding="utf-8"))
    for rel, expected in patch_record["current_source_sha256"].items():
        if sha(ROOT / rel) != expected:
            raise RuntimeError(f"Current source changed after the documented correction: {rel}")
    if inventory["collisions"] != {"within_new_inventory": [], "historical": [],
                                   "prior_small_development": [], "prepared_100k": []}:
        raise RuntimeError("The saved diagnostic seed collision audit is not clean")
    data_path = HERE / "fresh_development_data.npz"
    with np.load(data_path, allow_pickle=False) as z:
        data = {key: z[key].copy() for key in z.files}
    train_n, val_n = len(data["train_observable"]), len(data["validation_observable"])
    if train_n != 9000 or val_n != 4500:
        raise RuntimeError(f"Unexpected saved fresh-data coverage {train_n}/{val_n}")
    for split in ("train", "validation"):
        if data[f"{split}_detectors"].shape != ((train_n if split == "train" else val_n), 40):
            raise RuntimeError(f"Bad detector shape in saved {split} arrays")
        for suffix in ("observable", "pymatching", "regime_id"):
            if len(data[f"{split}_{suffix}"]) != (train_n if split == "train" else val_n):
                raise RuntimeError(f"Misaligned saved {split}_{suffix} array")
    if any(np.any((data[k] != 0) & (data[k] != 1)) for k in (
            "train_detectors", "train_observable", "train_pymatching",
            "validation_detectors", "validation_observable", "validation_pymatching")):
        raise RuntimeError("Nonbinary stored detector/observable/prediction bits")

    # Rebuild the same fixed circuit decoder and verify saved paired PM outputs.
    pm_redecoded = 0
    coords = None
    for ri, regime in enumerate(REGIMES):
        circuit, _, _, matching, fixed_index, _ = prepare({"memory_basis": "z", "noise_regime": regime,
            "distance": 3, "rounds": 5, "gate_p": 0.003, "measurement_p": 0.003,
            "bias_ratio": 10.0, "device": "cpu"})
        current = circuit.get_detector_coordinates()
        if coords is None: coords = current
        elif coords != current: raise RuntimeError("Regime circuit detector coordinates differ")
        if fixed_index != 2: raise RuntimeError("Frozen fixed decoder index changed")
        mask = data["validation_regime_id"] == ri
        pred = decode_matching(matching, data["validation_detectors"][mask])
        if not np.array_equal(pred, data["validation_pymatching"][mask]):
            raise RuntimeError(f"Saved PyMatching predictions fail re-decode for {regime}")
        pm_redecoded += int(mask.sum())

    # Recount the original 24 saved validation archives independently.
    old_results = json.loads((OLD_RUN / "structured_development_results.json").read_text(encoding="utf-8"))
    old_counts = {"identity": {r: 0 for r in REGIMES}, "pymatching": {r: 0 for r in REGIMES}, "candidates": {}}
    for name in old_results["candidates"]: old_counts["candidates"][name] = {r: 0 for r in REGIMES}
    archive_count = 0
    for path in sorted((OLD_RUN / "validation_evidence").glob("*.npz")):
        regime = path.name.split("_batch_")[0]
        with np.load(path, allow_pickle=False) as z:
            y, pm = z["observable"].astype(np.uint8), z["pymatching"].astype(np.uint8)
            old_counts["identity"][regime] += int(y.sum())
            old_counts["pymatching"][regime] += int(np.count_nonzero(pm ^ y))
            for name in old_results["candidates"]:
                spec = candidate_spec(name)
                prob = z[f"probability__{name}"].astype(np.float64)
                correction = (prob >= float(old_results["selected_thresholds"][name])).astype(np.uint8)
                pred = pm ^ correction if spec["kind"] == "residual" else correction
                old_counts["candidates"][name][regime] += int(np.count_nonzero(pred ^ y))
        archive_count += 1
    if archive_count != 24: raise RuntimeError(f"Expected 24 old validation bundles, found {archive_count}")
    for regime in REGIMES:
        if old_counts["identity"][regime] != old_results["comparators"]["identity"]["per_regime"][regime]["errors"]:
            raise RuntimeError(f"Identity aggregate mismatch for {regime}")
        if old_counts["pymatching"][regime] != old_results["comparators"]["pymatching"]["per_regime"][regime]["errors"]:
            raise RuntimeError(f"PyMatching aggregate mismatch for {regime}")
        for name in old_results["candidates"]:
            threshold = str(old_results["selected_thresholds"][name])
            expected = old_results["candidates"][name]["per_regime"][regime]["thresholds"][threshold]["logical_errors"]
            if old_counts["candidates"][name][regime] != expected:
                raise RuntimeError(f"Historical candidate count mismatch {name}/{regime}")

    # Recompute best-validation checkpoints on the saved paired validation data.
    y = data["validation_observable"]
    fixed = data["validation_pymatching"]
    rid = data["validation_regime_id"]
    recomputed = []
    for item in record["scale_comparison_results"]:
        kind = item["model"]
        strategy = item["strategy"]
        size = int(item["training_size_per_regime"])
        path = HERE / "checkpoints" / f"{kind}_{strategy}_{size}_best.pt"
        ck = torch.load(path, map_location="cpu", weights_only=False)
        if ck["model"] != kind or ck["strategy"] != strategy or int(ck["size_per_regime"]) != size:
            raise RuntimeError(f"Checkpoint identity mismatch: {path.name}")
        model = DirectMLP() if kind == "mlp" else StructuredConv3DDecoder(coords, channels=8, dropout=0.0)
        model.load_state_dict(ck["state_dict"]); model.eval()
        with torch.no_grad(): logits = model(torch.as_tensor(data["validation_detectors"], dtype=torch.float32)).numpy()
        if strategy == "weighted": logits = logits - math.log(float(ck["pos_weight"]))
        elif strategy == "balanced": logits = logits + math.log(float(ck["prior"]) / (1-float(ck["prior"])))
        p = 1 / (1 + np.exp(-np.clip(logits, -60, 60)))
        score = {}
        for threshold in np.linspace(0, 1, 201):
            score[float(threshold)] = float(np.mean([
                np.mean(((p[rid == ri] >= threshold).astype(np.uint8) ^ y[rid == ri])) for ri in range(3)]))
        selected = min(score, key=lambda t: (score[t], abs(t - .5), t))
        pred = (p >= selected).astype(np.uint8)
        per_regime = {}
        for ri, regime in enumerate(REGIMES):
            m = rid == ri; wrong = pred[m] ^ y[m]; fixed_wrong = fixed[m] ^ y[m]
            per_regime[regime] = {"errors": int(wrong.sum()),
                                  "candidate_only": int(np.count_nonzero((wrong == 1) & (fixed_wrong == 0))),
                                  "pymatching_only": int(np.count_nonzero((wrong == 0) & (fixed_wrong == 1))),
                                  "prediction_disagreements": int(np.count_nonzero(pred[m] != fixed[m]))}
        aggregate_errors = sum(v["errors"] for v in per_regime.values())
        candidate_only = sum(v["candidate_only"] for v in per_regime.values())
        pm_only = sum(v["pymatching_only"] for v in per_regime.values())
        if abs(selected - float(item["selected_threshold_validation"])) > 1e-10:
            raise RuntimeError(f"Validation threshold mismatch for {kind}/{strategy}/{size}")
        if aggregate_errors != round(float(item["equal_regime_ler"]) * val_n):
            raise RuntimeError(f"Aggregate validation error mismatch for {kind}/{strategy}/{size}")
        if (candidate_only, pm_only) != (int(item["candidate_only"]), int(item["pymatching_only"])):
            raise RuntimeError(f"Paired discordance mismatch for {kind}/{strategy}/{size}")
        for regime in REGIMES:
            stored = item["per_regime"][regime]
            if per_regime[regime]["errors"] != int(stored["errors"]):
                raise RuntimeError(f"Per-regime count mismatch for {kind}/{strategy}/{size}/{regime}")
        recomputed.append({"model": kind, "strategy": strategy, "training_size_per_regime": size,
                           "selected_threshold": float(selected), "errors": aggregate_errors,
                           "candidate_only": candidate_only, "pymatching_only": pm_only,
                           "per_regime": per_regime})
    output = {"status": "PASS", "saved_train_shots": train_n, "saved_validation_shots": val_n,
              "new_test_samples_generated_or_accessed": 0,
              "pymatching_predictions_redecoded": pm_redecoded,
              "historical_validation_bundles_recomputed": archive_count,
              "historical_identity_errors": sum(old_counts["identity"].values()),
              "historical_pymatching_errors": sum(old_counts["pymatching"].values()),
              "fresh_policy_models_recomputed": len(recomputed), "fresh_policy_results": recomputed,
              "note": "Recomputed from saved train/validation arrays, saved checkpoints, and saved historical NPZ evidence; no Stim shots were generated."}
    path = HERE / "SAVED_EVIDENCE_RECOMPUTATION.json"
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: output[k] for k in ("status", "saved_train_shots", "saved_validation_shots",
        "new_test_samples_generated_or_accessed", "pymatching_predictions_redecoded",
        "historical_validation_bundles_recomputed", "historical_identity_errors",
        "historical_pymatching_errors", "fresh_policy_models_recomputed")}, indent=2))


if __name__ == "__main__":
    main()
