"""Read-only diagnostics for a completed run; writes outside its run directory."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from models import DirectMLP, ResidualMLP
from seed_protocol import batch_seed
from simulator import decode_matching, prepare, sample


def confusion(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    y_true, y_pred = np.asarray(y_true, dtype=np.uint8), np.asarray(y_pred, dtype=np.uint8)
    if y_true.shape != y_pred.shape or not np.isin(y_true, [0, 1]).all() or not np.isin(y_pred, [0, 1]).all():
        raise ValueError("Expected equal-shaped binary labels and predictions.")
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    return {"matrix_true_rows_predicted_columns": [[tn, fp], [fn, tp]],
            "tn": tn, "fp": fp, "fn": fn, "tp": tp}


def calibration_summary(y_true: np.ndarray, probability: np.ndarray, bins: int = 10) -> dict:
    y = np.asarray(y_true, dtype=np.float64)
    p = np.clip(np.asarray(probability, dtype=np.float64), 1e-7, 1 - 1e-7)
    if y.shape != p.shape or not np.isin(y, [0, 1]).all():
        raise ValueError("Calibration inputs must be equal-shaped binary labels and probabilities.")
    brier = float(np.mean((p - y) ** 2))
    log_loss = float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    edges = np.linspace(0.0, 1.0, bins + 1)
    indices = np.minimum(np.digitize(p, edges[1:-1], right=False), bins - 1)
    table, ece = [], 0.0
    for index in range(bins):
        mask = indices == index
        count = int(mask.sum())
        if count:
            confidence = float(p[mask].mean())
            observed_rate = float(y[mask].mean())
            ece += count / len(y) * abs(confidence - observed_rate)
        else:
            confidence = observed_rate = None
        table.append({"low": float(edges[index]), "high": float(edges[index + 1]), "count": count,
                      "mean_probability": confidence, "observed_positive_rate": observed_rate})
    return {"brier_score": brier, "log_loss": log_loss, "ece_10_bins": float(ece),
            "probability_quantiles": {str(q): float(np.quantile(p, q)) for q in (0, .25, .5, .75, .9, .99, 1)},
            "probability_histogram_10_bins": [int(np.sum(indices == i)) for i in range(bins)],
            "reliability_bins": table}


def _predict(model: torch.nn.Module, detectors: np.ndarray, matching: np.ndarray | None = None,
             batch_size: int = 2048) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    logits, corrections = [], []
    with torch.inference_mode():
        for lo in range(0, len(detectors), batch_size):
            hi = min(len(detectors), lo + batch_size)
            x = torch.as_tensor(detectors[lo:hi], dtype=torch.float32)
            if matching is None:
                out = model(x)
                logits.append(out.numpy())
                corrections.append((out >= 0).to(torch.uint8).numpy())
            else:
                m = torch.as_tensor(matching[lo:hi], dtype=torch.float32)
                out = model(x, m)
                logits.append(out.numpy())
                residual = (out >= 0).to(torch.uint8).numpy()
                corrections.append(np.bitwise_xor(matching[lo:hi], residual))
    return np.concatenate(logits), np.concatenate(corrections)


def _hash_arrays(*arrays: np.ndarray) -> str:
    h = hashlib.sha256()
    for array in arrays:
        canonical = np.ascontiguousarray(array)
        h.update(str(canonical.shape).encode())
        h.update(canonical.dtype.str.encode())
        h.update(canonical.tobytes())
    return h.hexdigest()


def _split_report(name: str, detectors: np.ndarray, labels: np.ndarray, matching: np.ndarray,
                  direct_logits: np.ndarray, direct_prediction: np.ndarray,
                  residual_prediction: np.ndarray | None,
                  residual_logits: np.ndarray | None) -> dict:
    probabilities = 1.0 / (1.0 + np.exp(-np.clip(direct_logits, -80, 80)))
    residual_target = np.bitwise_xor(matching, labels)
    direct_stats = confusion(labels, direct_prediction)
    py_stats = confusion(labels, matching)
    residual_correction = np.bitwise_xor(matching, residual_prediction) if residual_prediction is not None else None
    result = {
        "shots": int(len(labels)),
        "observable_positive_count": int(labels.sum()),
        "observable_positive_rate": float(labels.mean()),
        "detector_bit_density": float(detectors.mean()),
        "direct_prediction_positive_count": int(direct_prediction.sum()),
        "direct_prediction_positive_rate": float(direct_prediction.mean()),
        "direct_prediction_histogram": {"0": int(len(labels) - direct_prediction.sum()), "1": int(direct_prediction.sum())},
        "direct_confusion": direct_stats,
        "direct_error_count": int(np.count_nonzero(direct_prediction ^ labels)),
        "direct_accuracy": float(np.mean(direct_prediction == labels)),
        "direct_calibration": calibration_summary(labels, probabilities),
        "direct_logit_quantiles": {str(q): float(np.quantile(direct_logits, q)) for q in (0, .01, .1, .5, .9, .99, 1)},
        "pymatching_prediction_histogram": {"0": int(len(labels) - matching.sum()), "1": int(matching.sum())},
        "pymatching_confusion": py_stats,
        "pymatching_error_count": int(np.count_nonzero(matching ^ labels)),
        "pymatching_failure_prevalence": float(np.mean(matching ^ labels)),
        "residual_target_positive_count": int(residual_target.sum()),
        "residual_target_positive_rate": float(residual_target.mean()),
        "residual_prediction_positive_count": int(residual_correction.sum()) if residual_correction is not None else None,
        "residual_prediction_positive_rate": float(residual_correction.mean()) if residual_correction is not None else None,
        "residual_correction_histogram": ({"0": int(len(labels) - residual_correction.sum()),
                                           "1": int(residual_correction.sum())}
                                          if residual_correction is not None else None),
        "residual_correction_confusion": confusion(residual_target, residual_correction) if residual_correction is not None else None,
        "residual_calibration": (calibration_summary(residual_target,
                                                      1.0 / (1.0 + np.exp(-np.clip(residual_logits, -80, 80))))
                                 if residual_logits is not None else None),
        "residual_final_prediction_histogram": ({"0": int(len(labels) - residual_prediction.sum()),
                                                 "1": int(residual_prediction.sum())}
                                                if residual_prediction is not None else None),
        "residual_final_confusion": confusion(labels, residual_prediction) if residual_prediction is not None else None,
        "residual_final_error_count": int(np.count_nonzero(residual_prediction ^ labels)) if residual_prediction is not None else None,
        "paired_arrays_sha256": _hash_arrays(detectors, labels, matching),
    }
    return result


def analyze(run_dir: Path, output_dir: Path | None = None) -> dict:
    run_dir = run_dir.resolve()
    cfg = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    checkpoint = torch.load(run_dir / "checkpoint.pt", map_location="cpu", weights_only=False)
    circuit, _, _, matching_model, _, _ = prepare(cfg)

    train_d, train_y, train_m = [], [], []
    plan = metadata["seed_plan"]
    remaining = int(cfg["training_shots"])
    for batch_index in range(plan["batches"]["train"]):
        count = min(int(cfg["batch_size"]), remaining)
        d, y = sample(circuit, batch_seed(plan, "train", batch_index), count)
        train_d.append(d)
        train_y.append(y)
        train_m.append(decode_matching(matching_model, d))
        remaining -= count
    splits = {
        "train": (np.concatenate(train_d), np.concatenate(train_y), np.concatenate(train_m), None, None),
    }
    for name in ("validation", "test"):
        path = run_dir / f"{name}_evidence.npz"
        with np.load(path) as archive:
            key = "direct" if name == "validation" else "direct_neural"
            residual_key = "residual" if name == "validation" else "pymatching_neural_residual"
            d, y, matching = archive["detectors"].copy(), archive["observable"].copy(), archive["pymatching"].copy()
            stored_direct = archive[key].copy()
            stored_residual = archive[residual_key].copy()
        residual_arg = stored_residual if stored_residual.shape == y.shape else None
        splits[name] = (d, y, matching, stored_direct, residual_arg)

    direct = DirectMLP()
    direct.load_state_dict(checkpoint["direct_state"])
    residual = ResidualMLP() if checkpoint.get("residual_state") is not None else None
    if residual is not None:
        residual.load_state_dict(checkpoint["residual_state"])
    split_results = {}
    for name, (d, y, matching, stored_direct, stored_residual) in splits.items():
        independent_matching = decode_matching(matching_model, d)
        if not np.array_equal(independent_matching, matching):
            raise AssertionError(f"Saved/reconstructed PyMatching predictions differ in {name} split.")
        direct_logits, direct_pred = _predict(direct, d)
        if stored_direct is not None and not np.array_equal(direct_pred, stored_direct):
            raise AssertionError(f"Direct checkpoint predictions do not reproduce saved {name} predictions.")
        if residual is not None:
            residual_logits, residual_pred = _predict(residual, d, matching)
            if stored_residual is not None and not np.array_equal(residual_pred, stored_residual):
                raise AssertionError(f"Residual checkpoint predictions do not reproduce saved {name} predictions.")
        else:
            residual_logits, residual_pred = None, None
        split_results[name] = _split_report(name, d, y, matching, direct_logits, direct_pred,
                                            residual_pred, residual_logits)

    loss_history = [float(value) for value in checkpoint.get("loss_history", [])]
    result = {
        "run_id": metadata["run_id"], "audit_scope": "read-only retrospective audit; test split is not used for model selection",
        "configuration": cfg, "software": metadata.get("software"), "device": metadata.get("device"),
        "cuda_training_verified": metadata.get("cuda_training_verified"),
        "seed_screen_passed": metadata.get("seed_screen", {}).get("passed"),
        "split_results": split_results,
        "per_regime": {cfg["noise_regime"]: {name: values for name, values in split_results.items()}},
        "learning_diagnostics": {"completed_steps": checkpoint.get("completed_steps"),
                                 "training_samples_processed": checkpoint.get("training_samples_processed"),
                                 "loss_history_count": len(loss_history),
                                 "batch_loss_history": loss_history,
                                 "first_batch_loss": loss_history[0] if loss_history else None,
                                 "last_batch_loss": loss_history[-1] if loss_history else None,
                                 "minimum_batch_loss": min(loss_history) if loss_history else None,
                                 "best_validation_ler_recorded": checkpoint.get("best_validation_ler")},
        "limitations": ["Only the saved balanced regime is represented; no other regime's samples were generated for this audit.",
                        "Test diagnostics describe the already completed smoke test and were not used to tune the new structured model.",
                        "This is a single-root 1,000-shot test, not evidence of generalization or statistical superiority."],
    }
    output_dir = output_dir or (run_dir.parent.parent / "analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{metadata['run_id']}_neural_diagnostics.json"
    md_path = output_dir / f"{metadata['run_id']}_neural_diagnostics.md"
    result["outputs"] = {"json": str(json_path), "markdown": str(md_path)}
    json_path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    test = split_results["test"]
    md = [f"# Neural decoder audit — {metadata['run_id']}", "",
          "Read-only analysis. The test split was not used for model selection.", "",
          "| Split | shots | observable positives | direct positives | direct errors | matching errors | residual targets | residual final errors |",
          "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, item in split_results.items():
        md.append(f"| {name} | {item['shots']} | {item['observable_positive_count']} | {item['direct_prediction_positive_count']} | "
                  f"{item['direct_error_count']} | {item['pymatching_error_count']} | {item['residual_target_positive_count']} | "
                  f"{item['residual_final_error_count']} |")
    md += ["", f"Test direct confusion matrix (true rows, predicted columns): `{test['direct_confusion']['matrix_true_rows_predicted_columns']}`.",
           f"Test direct Brier/log-loss/ECE: {test['direct_calibration']['brier_score']:.6f} / "
           f"{test['direct_calibration']['log_loss']:.6f} / {test['direct_calibration']['ece_10_bins']:.6f}.",
           f"Test direct probability histogram (10 equal-width bins): `{test['direct_calibration']['probability_histogram_10_bins']}`.", "",
           "Only the saved balanced regime is available in this run. Other regimes are explicitly not measured.",
           "The JSON contains split-specific confusion matrices, calibration bins, prediction histograms, and training-loss summaries.", ""]
    md_path.write_text("\n".join(md), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    result = analyze(args.run_dir, args.output_dir)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
