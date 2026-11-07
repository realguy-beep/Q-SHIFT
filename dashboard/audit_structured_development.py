"""Independent, read-only audit of structured validation evidence and checkpoints."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from models import DirectMLP, ResidualMLP
from simulator import decode_matching, prepare, sample
from structured_decoder import StructuredConv3DDecoder

REGIMES = ("x_biased", "balanced", "z_biased")
THRESHOLDS = (0.25, 0.5, 0.75)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def model_from_best(name: str, model_path: Path, coordinates: dict):
    saved = torch.load(model_path, map_location="cpu", weights_only=False)
    spec = saved["spec"]
    if spec["kind"] == "direct":
        model = DirectMLP()
    elif spec["kind"] == "residual":
        model = ResidualMLP()
    else:
        model = StructuredConv3DDecoder(coordinates, channels=int(spec["width"]), dropout=0.05)
    model.load_state_dict(saved["state_dict"])
    model.eval()
    return model, spec, saved


def expected_outputs(model, spec, detectors, fixed):
    x = torch.from_numpy(detectors.astype(np.float32))
    b = torch.from_numpy(fixed.astype(np.float32))
    with torch.inference_mode():
        logits = model(x, b) if spec["kind"] == "residual" else model(x)
        probability = torch.sigmoid(logits).numpy().astype(np.float32)
    pred = (probability >= 0.5).astype(np.uint8)
    if spec["kind"] == "residual":
        pred = np.bitwise_xor(fixed, pred)
    return probability, pred


def empty_metrics():
    return {"n": 0, "positive": 0, "brier": 0.0, "logloss": 0.0,
            "bins": [[0, 0.0, 0.0] for _ in range(10)],
            "confusion": {str(t): {"tn": 0, "fp": 0, "fn": 0, "tp": 0} for t in THRESHOLDS},
            "logical_errors": {str(t): 0 for t in THRESHOLDS},
            "paired": {str(t): {"candidate_only": 0, "fixed_only": 0, "prediction_disagreements": 0}
                       for t in THRESHOLDS}}


def add_metrics(acc, target, probability, final_predictions, logical_y, fixed):
    y = np.asarray(target, dtype=np.uint8)
    p = np.clip(np.asarray(probability, dtype=np.float64), 1e-7, 1 - 1e-7)
    logical_y = np.asarray(logical_y, dtype=np.uint8)
    acc["n"] += len(y)
    acc["positive"] += int(y.sum())
    acc["brier"] += float(np.square(p - y).sum())
    acc["logloss"] += float((-(y * np.log(p) + (1 - y) * np.log(1 - p))).sum())
    bins = np.minimum((p * 10).astype(int), 9)
    for index in range(10):
        m = bins == index
        if m.any():
            acc["bins"][index][0] += int(m.sum())
            acc["bins"][index][1] += float(p[m].sum())
            acc["bins"][index][2] += float(y[m].sum())
    fixed_wrong = fixed ^ logical_y
    for t in THRESHOLDS:
        key = str(t)
        predicted_target = (p >= t).astype(np.uint8)
        c = acc["confusion"][key]
        c["tn"] += int(np.count_nonzero((y == 0) & (predicted_target == 0)))
        c["fp"] += int(np.count_nonzero((y == 0) & (predicted_target == 1)))
        c["fn"] += int(np.count_nonzero((y == 1) & (predicted_target == 0)))
        c["tp"] += int(np.count_nonzero((y == 1) & (predicted_target == 1)))
        logical_pred = final_predictions[t]
        wrong = logical_pred ^ logical_y
        acc["logical_errors"][key] += int(wrong.sum())
        acc["paired"][key]["candidate_only"] += int(np.count_nonzero((wrong == 1) & (fixed_wrong == 0)))
        acc["paired"][key]["fixed_only"] += int(np.count_nonzero((wrong == 0) & (fixed_wrong == 1)))
        acc["paired"][key]["prediction_disagreements"] += int(np.count_nonzero(logical_pred != fixed))


def finish_metrics(acc):
    n = max(1, acc["n"])
    ece = 0.0
    for count, psum, ysum in acc["bins"]:
        if count:
            ece += count / n * abs(psum / count - ysum / count)
    thresholds = {}
    for t, c in acc["confusion"].items():
        denom = c["tp"] + c["fn"]
        thresholds[t] = {**c, "logical_errors": acc["logical_errors"][t],
                         "logical_ler": acc["logical_errors"][t] / n,
                         "predicted_positive_rate": (c["tp"] + c["fp"]) / n,
                         "positive_recall": c["tp"] / denom if denom else None,
                         "paired_vs_pymatching": acc["paired"][t]}
    return {"n": acc["n"], "target_positive_count": acc["positive"],
            "target_positive_rate": acc["positive"] / n, "brier_score": acc["brier"] / n,
            "log_loss": acc["logloss"] / n, "ece_10_equal_width_bins": ece,
            "thresholds": thresholds}


def audit(run_dir: Path) -> dict:
    run_dir = run_dir.resolve()
    cfg = json.loads((run_dir / "structured_resolved_config.json").read_text(encoding="utf-8"))
    inventory = json.loads((run_dir / "structured_seed_inventory.json").read_text(encoding="utf-8"))
    freeze = json.loads((run_dir / "structured_freeze.json").read_text(encoding="utf-8"))
    recorded = json.loads((run_dir / "structured_development_results.json").read_text(encoding="utf-8"))
    seed_path = run_dir / "structured_seed_inventory.json"
    assert sha256_file(seed_path) == freeze["seed_inventory_sha256"], "seed inventory hash mismatch"
    assert freeze["status"].startswith("training protocol frozen before sampling")
    assert recorded["training_only_split_notice"].startswith("The report contains development validation")
    assert recorded["test_access"] if "test_access" in recorded else recorded["training_only_split_notice"]
    assert recorded["cuda_training_verified"] is True
    for relative, expected in freeze["source_sha256"].items():
        assert sha256_file(HERE / relative) == expected, f"source hash mismatch: {relative}"
    assert sha256_file(run_dir / "structured_resolved_config.json")
    assert inventory.get("passed", False)
    # Prepared 100K protocol files remain frozen and test roots are present only
    # in the inventory; no test bundle may be emitted by this worker.
    protocol_freeze_path = ROOT / "outputs" / "neural_decoder_diagnostic" / "structured_diagnostic_freeze.json"
    assert sha256_file(protocol_freeze_path) == freeze["prepared_protocol_freeze_sha256"]
    forbidden_test_artifacts = [p.name for p in run_dir.glob("*test*") if p.suffix in (".npz", ".npy")]
    assert not forbidden_test_artifacts, f"test-like artifacts unexpectedly exist: {forbidden_test_artifacts}"

    environments = {}
    models = {}
    for regime in REGIMES:
        noise = {"distance": 3, "rounds": 5, "memory_basis": "z", "gate_p": 0.003,
                 "measurement_p": 0.003, "bias_ratio": 10.0, "noise_regime": regime}
        circuit, _, _, matching, fixed_index, _ = prepare(noise)
        assert circuit.num_detectors == 40 and circuit.num_observables == 1
        assert fixed_index == 2
        environments[regime] = (circuit, matching)
        coords = circuit.get_detector_coordinates()
        for candidate in cfg["candidates"]:
            if candidate not in models:
                models[candidate] = model_from_best(candidate, run_dir / "best_models" / f"{candidate}.pt", coords)

    per_regime = {name: {regime: empty_metrics() for regime in REGIMES} for name in cfg["candidates"]}
    paired_vectors = {name: {regime: {"candidate_error": [], "fixed_error": []} for regime in REGIMES}
                      for name in cfg["candidates"]}
    baseline = {"identity": {r: 0 for r in REGIMES}, "pymatching": {r: 0 for r in REGIMES}}
    evidence_files = sorted((run_dir / "validation_evidence").glob("*.npz"))
    assert evidence_files, "no saved paired validation evidence"
    shots_by_regime = {r: 0 for r in REGIMES}
    regenerated_batches = 0
    decoded_ok = 0
    model_ok = 0
    for path in evidence_files:
        name = path.stem
        regime = next((r for r in REGIMES if name.startswith(r + "_batch_")), None)
        assert regime is not None, f"unexpected validation evidence filename: {name}"
        batch_index = int(name.split("_batch_")[1])
        stream = next(s for s in inventory["streams"] if s["split"] == "validation" and s["regime"] == regime)
        size_expected = min(int(cfg["batch_size"]), int(stream["shots"]) - batch_index * int(cfg["batch_size"]))
        assert size_expected > 0
        with np.load(path, allow_pickle=False) as data:
            d = np.asarray(data["detectors"])
            y = np.asarray(data["observable"])
            fixed = np.asarray(data["pymatching"])
            assert d.shape == (size_expected, 40) and d.dtype == np.uint8
            assert y.shape == fixed.shape == (size_expected,) and y.dtype == fixed.dtype == np.uint8
            assert np.isin(d, (0, 1)).all() and np.isin(y, (0, 1)).all() and np.isin(fixed, (0, 1)).all()
            seed = int(stream["root"]) + batch_index
            regenerated_d, regenerated_y = sample(environments[regime][0], seed, size_expected)
            assert np.array_equal(d, regenerated_d), f"detector stream mismatch in {path.name}"
            assert np.array_equal(y, regenerated_y), f"observable stream mismatch in {path.name}"
            regenerated_batches += 1
            recomputed_fixed = decode_matching(environments[regime][1], d)
            assert np.array_equal(fixed, recomputed_fixed), f"PyMatching mismatch in {path.name}"
            decoded_ok += 1
            assert np.array_equal(data["identity"], np.zeros(size_expected, dtype=np.uint8))
            baseline["identity"][regime] += int(y.sum())
            baseline["pymatching"][regime] += int(np.count_nonzero(fixed ^ y))
            for candidate, (model, spec, best_meta) in models.items():
                p, predicted05 = expected_outputs(model, spec, d, fixed)
                assert np.array_equal(data[f"prediction__{candidate}"], predicted05), \
                    f"saved prediction differs from restored best weights for {candidate} in {path.name}"
                assert np.allclose(data[f"probability__{candidate}"], p, rtol=1e-6, atol=1e-7), \
                    f"saved probabilities differ from restored best weights for {candidate} in {path.name}"
                model_ok += 1
                target = np.bitwise_xor(fixed, y) if spec["kind"] == "residual" else y
                pred_by_threshold = {}
                for t in THRESHOLDS:
                    pred = (p >= t).astype(np.uint8)
                    pred_by_threshold[t] = np.bitwise_xor(fixed, pred) if spec["kind"] == "residual" else pred
                selected_threshold = float(recorded["selected_thresholds"][candidate])
                selected_prediction = np.bitwise_xor(fixed, (p >= selected_threshold).astype(np.uint8)) \
                    if spec["kind"] == "residual" else (p >= selected_threshold).astype(np.uint8)
                paired_vectors[candidate][regime]["candidate_error"].append(selected_prediction ^ y)
                paired_vectors[candidate][regime]["fixed_error"].append(fixed ^ y)
                add_metrics(per_regime[candidate][regime], target, p, pred_by_threshold, y, fixed)
            shots_by_regime[regime] += size_expected

    summary = {name: {regime: finish_metrics(per_regime[name][regime]) for regime in REGIMES}
               for name in cfg["candidates"]}
    for candidate in cfg["candidates"]:
        for regime in REGIMES:
            expected = recorded["candidates"][candidate]["per_regime"][regime]
            actual = summary[candidate][regime]
            assert actual["n"] == expected["n"]
            for t in map(str, THRESHOLDS):
                assert actual["thresholds"][t]["logical_errors"] == expected["thresholds"][t]["logical_errors"], \
                    f"aggregate logical errors mismatch: {candidate}/{regime}/{t}"
            assert math.isclose(actual["brier_score"], expected["brier_score"], abs_tol=1e-6)
            assert math.isclose(actual["log_loss"], expected["log_loss"], abs_tol=1e-6)
    analysis_seed = 1_180_000_001
    from structured_training import inventory_seed_values, load_prepared_freeze
    assert analysis_seed not in inventory_seed_values(inventory), "bootstrap seed collides with data/model streams"
    assert analysis_seed not in __import__("seed_protocol").historical_seeds(), "bootstrap seed collides with recoverable history"
    _, frozen_inventory = load_prepared_freeze()
    assert analysis_seed not in inventory_seed_values(frozen_inventory), "bootstrap seed collides with frozen 100K allocation"
    rng = np.random.default_rng(analysis_seed)
    bootstrap = {name: {"differences": [], "candidate_ler": [], "fixed_ler": []}
                 for name in cfg["candidates"]}
    repetitions = 10_000
    chunk_size = 500
    prepared_vectors = {}
    for name in cfg["candidates"]:
        prepared_vectors[name] = {}
        for regime in REGIMES:
            cand = np.concatenate(paired_vectors[name][regime]["candidate_error"]).astype(np.float32)
            fixed = np.concatenate(paired_vectors[name][regime]["fixed_error"]).astype(np.float32)
            prepared_vectors[name][regime] = (cand, fixed)
    for start in range(0, repetitions, chunk_size):
        count = min(chunk_size, repetitions - start)
        indexes = {regime: rng.integers(0, shots_by_regime[regime], size=(count, shots_by_regime[regime]))
                   for regime in REGIMES}
        for name in cfg["candidates"]:
            differences = np.zeros(count, dtype=np.float64)
            candidate_ler = np.zeros(count, dtype=np.float64)
            fixed_ler = np.zeros(count, dtype=np.float64)
            for regime in REGIMES:
                cand, fixed = prepared_vectors[name][regime]
                idx = indexes[regime]
                c_rate = cand[idx].mean(axis=1)
                f_rate = fixed[idx].mean(axis=1)
                differences += (c_rate - f_rate) / len(REGIMES)
                candidate_ler += c_rate / len(REGIMES)
                fixed_ler += f_rate / len(REGIMES)
            bootstrap[name]["differences"].extend(differences.tolist())
            bootstrap[name]["candidate_ler"].extend(candidate_ler.tolist())
            bootstrap[name]["fixed_ler"].extend(fixed_ler.tolist())
    bootstrap_summary = {}
    for name in cfg["candidates"]:
        cand_all = np.concatenate([prepared_vectors[name][r][0] for r in REGIMES])
        fixed_all = np.concatenate([prepared_vectors[name][r][1] for r in REGIMES])
        cand_only = int(np.count_nonzero((cand_all == 1) & (fixed_all == 0)))
        fixed_only = int(np.count_nonzero((cand_all == 0) & (fixed_all == 1)))
        diff = float(np.mean([prepared_vectors[name][r][0].mean() - prepared_vectors[name][r][1].mean()
                              for r in REGIMES]))
        bootstrap_summary[name] = {"selected_threshold": float(recorded["selected_thresholds"][name]),
                                   "equal_regime_candidate_ler": float(np.mean([prepared_vectors[name][r][0].mean() for r in REGIMES])),
                                   "equal_regime_fixed_ler": float(np.mean([prepared_vectors[name][r][1].mean() for r in REGIMES])),
                                   "equal_regime_paired_difference": diff,
                                   "candidate_only_failures": cand_only, "fixed_only_failures": fixed_only,
                                   "bootstrap_repetitions": repetitions, "bootstrap_seed": analysis_seed,
                                   "paired_shot_bootstrap_95_ci": [float(np.quantile(bootstrap[name]["differences"], 0.025)),
                                                                   float(np.quantile(bootstrap[name]["differences"], 0.975))],
                                   "candidate_ler_95_ci": [float(np.quantile(bootstrap[name]["candidate_ler"], 0.025)),
                                                           float(np.quantile(bootstrap[name]["candidate_ler"], 0.975))],
                                   "fixed_ler_95_ci": [float(np.quantile(bootstrap[name]["fixed_ler"], 0.025)),
                                                       float(np.quantile(bootstrap[name]["fixed_ler"], 0.975))]}
    result = {"audit_status": "PASS" if decoded_ok == len(evidence_files) and model_ok > 0 else "FAIL",
              "test_samples_generated_or_accessed": 0,
              "evidence_files": len(evidence_files), "regenerated_batches": regenerated_batches,
              "pymatching_predictions_independently_redecoded": decoded_ok,
              "best_checkpoint_predictions_recomputed": model_ok,
              "validation_shots_by_regime": shots_by_regime,
              "per_candidate_per_regime": summary,
              "paired_development_uncertainty": bootstrap_summary,
              "analysis_seed_screen": {"seed": analysis_seed,
                                       "disjoint_from_development_streams": True,
                                       "disjoint_from_recoverable_history": True,
                                       "disjoint_from_frozen_100k_inventory": True},
              "uncertainty_note": "10,000 stratified paired-shot bootstrap resamples are conditional on these three single validation streams; they do not estimate seed-to-seed variability and are not confirmatory because these data select thresholds and models.",
              "baseline_errors": {name: {r: {"shots": shots_by_regime[r], "errors": count,
                                                "ler": count / max(1, shots_by_regime[r])}
                                         for r, count in regimes.items()}
                                  for name, regimes in baseline.items()},
              "source_and_data_hashes_verified": True,
              "limitations": ["These are development-validation metrics used for selection, not independent test results.",
                              "The validation streams are single deterministic roots per regime."]}
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.run_dir)
    output = args.output or args.run_dir / "independent_evidence_audit.json"
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"audit_status": result["audit_status"], "evidence_files": result["evidence_files"],
                      "test_samples_generated_or_accessed": 0, "output": str(output)}, indent=2))


if __name__ == "__main__":
    main()
