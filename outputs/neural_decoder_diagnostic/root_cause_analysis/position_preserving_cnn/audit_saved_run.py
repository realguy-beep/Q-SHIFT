"""Independent rescoring of saved position-CNN development evidence; no sampling."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "dashboard"))

from models import DirectMLP
from simulator import prepare
from structured_decoder import (StructuredConv3DDecoder, PositionPreservingConv3DDecoder,
                                CoordinateChannelConv3DDecoder)

REGIMES = ("x_biased", "balanced", "z_biased")
ARCHS = ("pooled_cnn8", "pooled_cnn16_capacity_control", "position_flat_cnn",
         "coordinate_channel_cnn", "balanced_mlp")
STRATEGIES = ("balanced_minibatches", "weighted_bce")
TEMPS = [0.5, 0.7, 0.85, 1.0, 1.2, 1.5, 2.0, 3.0, 4.0]
THRESHOLDS = [round(float(x), 2) for x in np.arange(0.01, 1.0, 0.01)]
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def save_json(obj, path):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def build_model(arch, coords):
    if arch == "pooled_cnn8": return StructuredConv3DDecoder(coords, channels=8, dropout=0.05)
    if arch == "pooled_cnn16_capacity_control": return StructuredConv3DDecoder(coords, channels=16, dropout=0.05)
    if arch == "position_flat_cnn": return PositionPreservingConv3DDecoder(coords, channels=4, head_width=16, dropout=0.05)
    if arch == "coordinate_channel_cnn": return CoordinateChannelConv3DDecoder(coords, channels=4, head_width=16, dropout=0.05)
    if arch == "balanced_mlp": return DirectMLP(detector_count=40)
    raise ValueError(arch)


def confusion(pred, y):
    p, y = np.asarray(pred, dtype=np.uint8), np.asarray(y, dtype=np.uint8)
    tp = int(np.sum((p == 1) & (y == 1))); fp = int(np.sum((p == 1) & (y == 0)))
    fn = int(np.sum((p == 0) & (y == 1))); tn = int(np.sum((p == 0) & (y == 0)))
    return {"tn": tn, "fp": fp, "fn": fn, "tp": tp,
            "positive_recall": tp / (tp + fn) if tp + fn else None,
            "logical_errors": fp + fn, "logical_error_rate": (fp + fn) / len(y),
            "predicted_positive_rate": float(np.mean(p))}


def natural_logits(raw, strategy, record):
    if strategy == "weighted_bce":
        return raw - math.log(float(record["weighted_bce_pos_weight"]))
    p = float(record["natural_training_positive_prevalence"])
    return raw + math.log(p / (1.0 - p))


def nll_from_logits(logits, y):
    z, y = np.clip(np.asarray(logits, dtype=np.float64), -60, 60), np.asarray(y, dtype=np.float64)
    return float(np.mean(np.logaddexp(0.0, z) - y * z))


def choose_temperature(logits, labels):
    return min((nll_from_logits(logits / t, labels), abs(t - 1.0), t) for t in TEMPS)[2]


def prob_metrics(prob, y):
    p = np.clip(np.asarray(prob, dtype=np.float64), 1e-9, 1.0 - 1e-9)
    y = np.asarray(y, dtype=np.float64)
    nll = float(np.mean(-y * np.log(p) - (1 - y) * np.log(1 - p)))
    brier = float(np.mean((p - y) ** 2))
    ece = 0.0
    for i in range(10):
        mask = (p >= i / 10) & ((p < (i + 1) / 10) if i < 9 else (p <= 1.0))
        if mask.any(): ece += float(mask.mean() * abs(p[mask].mean() - y[mask].mean()))
    return {"nll": nll, "brier": brier, "ece_10bin": ece}


def ci(values):
    a = np.asarray(values, dtype=np.float64)
    mean = float(a.mean()); sd = float(a.std(ddof=1))
    half = 4.302652729911275 * sd / math.sqrt(len(a))
    return [mean - half, mean + half]


def main():
    results = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    freeze = json.loads((OUT / "freeze.json").read_text(encoding="utf-8"))
    inventory = json.loads((OUT / "seed_inventory.json").read_text(encoding="utf-8"))
    post_patch = json.loads((OUT / "POSTRUN_REPORTING_PATCH.json").read_text(encoding="utf-8"))
    runner_rel = "outputs/neural_decoder_diagnostic/root_cause_analysis/position_preserving_cnn/run_experiment.py"
    for rel, expected in freeze["source_sha256"].items():
        if sha(ROOT / rel) == expected:
            continue
        if rel == runner_rel and sha(OUT / "run_experiment_frozen.py") == expected and \
                sha(OUT / "run_experiment.py") == post_patch["current_runner_sha256"] and \
                sha(OUT / "REPORTING_ONLY_DIFF.txt") == post_patch["diff_sha256"] and \
                post_patch["sampling_or_model_logic_changed"] is False:
            continue
        raise RuntimeError(f"Frozen source hash mismatch for {rel}; saved outputs remain unaudited.")
    if results["status"] != "completed_development_only" or len(results["records"]) != 30:
        raise RuntimeError("Saved run is incomplete; expected 30 model fits.")
    if results.get("test_samples_generated_or_accessed") != 0:
        raise RuntimeError("Test-stream access was recorded; refusing a development-only audit.")
    if not inventory["passed"] or any(bool(v) for v in inventory["collisions"].values()):
        raise RuntimeError("Saved seed inventory is not collision-free.")
    if not (OUT / "RUNNER_PARTIAL_PER_ROOT.csv").exists():
        partial = OUT / "per_root_results.csv"
        if partial.exists(): shutil.copy2(partial, OUT / "RUNNER_PARTIAL_PER_ROOT.csv")

    samples = np.load(OUT / "development_samples.npz", allow_pickle=False)
    stored_records = {(r["replicate"], r["architecture"], r["strategy"]): r for r in results["records"]}
    recomputed, prediction_arrays = [], {}
    config = json.loads((OUT / "config.json").read_text(encoding="utf-8"))
    circuit_cfg = {k: config["circuit"][k] for k in
                   ("distance", "rounds", "memory_basis", "gate_p", "measurement_p", "bias_ratio")}
    circuit, _, _, _, _, _ = prepare({**circuit_cfg, "noise_regime": "balanced", "device": "cpu"})
    coords = circuit.get_detector_coordinates()
    for rep in range(3):
        archive = np.load(OUT / f"predictions_rep{rep}.npz", allow_pickle=False)
        split_data = {}
        for part in ("monitor", "calibration", "threshold"):
            split_data[part] = {}
            for regime in REGIMES:
                idx = samples[f"rep{rep}_validation_{regime}_{part}_indices"]
                split_data[part][regime] = {
                    k: samples[f"rep{rep}_validation_{regime}_{k}"][idx]
                    for k in ("detectors", "observable", "pymatching")}
                block = split_data[part][regime]
                if block["detectors"].shape != (1000, 40) or any(len(block[k]) != 1000 for k in ("observable", "pymatching")):
                    raise RuntimeError(f"Misaligned saved validation partition {rep}/{regime}/{part}")
                if any(np.any((block[k] != 0) & (block[k] != 1)) for k in ("detectors", "observable", "pymatching")):
                    raise RuntimeError(f"Nonbinary saved data at {rep}/{regime}/{part}")
        for arch in ARCHS:
            for strategy in STRATEGIES:
                record = stored_records[(rep, arch, strategy)]
                ckpath = OUT / "checkpoints" / f"rep{rep}_{arch}__{strategy}.pt"
                checkpoint = torch.load(ckpath, map_location="cpu", weights_only=False)
                if checkpoint["architecture"] != arch or checkpoint["strategy"] != strategy:
                    raise RuntimeError(f"Checkpoint identity mismatch: {ckpath.name}")
                model = build_model(arch, coords).to(DEVICE)
                model.load_state_dict(checkpoint["state_dict"]); model.eval()
                if sum(p.numel() for p in model.parameters()) != record["parameter_count"]:
                    raise RuntimeError(f"Parameter count mismatch for {rep}/{arch}/{strategy}")
                logits = {}
                with torch.inference_mode():
                    for part in ("monitor", "calibration", "threshold"):
                        logits[part] = {}
                        for regime in REGIMES:
                            d = split_data[part][regime]["detectors"]
                            raw = model(torch.as_tensor(d, dtype=torch.float32, device=DEVICE)).detach().cpu().numpy().astype(np.float64)
                            corrected = natural_logits(raw, strategy, record)
                            if not np.isfinite(corrected).all(): raise FloatingPointError("Non-finite re-decoded logits")
                            logits[part][regime] = corrected
                cal_y = np.concatenate([split_data["calibration"][r]["observable"] for r in REGIMES])
                cal_logits = np.concatenate([logits["calibration"][r] for r in REGIMES])
                temp = choose_temperature(cal_logits, cal_y)
                if abs(temp - record["temperature"]) > 1e-12: raise RuntimeError("Temperature selection mismatch")
                threshold_y = np.concatenate([split_data["threshold"][r]["observable"] for r in REGIMES])
                threshold_probs = {r: 1.0 / (1.0 + np.exp(-np.clip(logits["threshold"][r] / temp, -60, 60))) for r in REGIMES}
                candidates = []
                for t in THRESHOLDS:
                    score = float(np.mean([np.mean((threshold_probs[r] >= t).astype(np.uint8) ^
                                                      split_data["threshold"][r]["observable"]) for r in REGIMES]))
                    candidates.append((score, abs(t - 0.5), t))
                threshold = min(candidates)[2]
                if abs(threshold - record["selected_threshold"]) > 1e-12: raise RuntimeError("Threshold selection mismatch")
                per_regime = {}
                pred_payload = {}
                for regime in REGIMES:
                    block = split_data["threshold"][regime]
                    prob = threshold_probs[regime].astype(np.float32)
                    pred = (prob >= threshold).astype(np.uint8)
                    suffix = f"{arch}__{strategy}"
                    saved_prob = archive[f"{suffix}__probability__{regime}"]
                    saved_pred = archive[f"{suffix}__prediction__{regime}"]
                    if not np.allclose(prob, saved_prob, rtol=0, atol=2e-6): raise RuntimeError(f"Saved probabilities mismatch {rep}/{suffix}/{regime}")
                    if not np.array_equal(pred, saved_pred): raise RuntimeError(f"Saved predictions mismatch {rep}/{suffix}/{regime}")
                    for field, name in (("observable", "observable"), ("pymatching", "pymatching"), ("detectors", "detectors")):
                        if not np.array_equal(block[field], archive[f"{name}__{regime}"]):
                            raise RuntimeError(f"Paired sample identity mismatch {rep}/{regime}/{field}")
                    cm = confusion(pred, block["observable"])
                    pm_cm = confusion(block["pymatching"], block["observable"])
                    neural_wrong = pred ^ block["observable"]
                    pm_wrong = block["pymatching"] ^ block["observable"]
                    cm.update({"pymatching_confusion": pm_cm,
                               "candidate_only": int(np.sum((neural_wrong == 1) & (pm_wrong == 0))),
                               "pymatching_only": int(np.sum((neural_wrong == 0) & (pm_wrong == 1))),
                               "paired_prediction_disagreements": int(np.sum(pred != block["pymatching"])),
                               "pymatching_ler": float(pm_wrong.mean()),
                               "paired_ler_difference": float(neural_wrong.mean() - pm_wrong.mean())})
                    per_regime[regime] = cm
                    pred_payload[regime] = {"probability": prob, "prediction": pred}
                    old = record["per_regime"][regime]
                    for key in ("tn", "fp", "fn", "tp", "logical_errors", "pymatching_errors", "candidate_only", "pymatching_only"):
                        observed = cm["pymatching_confusion"]["logical_errors"] if key == "pymatching_errors" else cm[key]
                        if int(old[key]) != int(observed): raise RuntimeError(f"Count mismatch {rep}/{suffix}/{regime}/{key}")
                equal_ler = float(np.mean([per_regime[r]["logical_error_rate"] for r in REGIMES]))
                equal_pm = float(np.mean([per_regime[r]["pymatching_ler"] for r in REGIMES]))
                c_only = sum(per_regime[r]["candidate_only"] for r in REGIMES)
                pm_only = sum(per_regime[r]["pymatching_only"] for r in REGIMES)
                if abs(equal_ler - record["equal_regime_ler"]) > 1e-12 or abs(equal_pm-record["equal_regime_pymatching_ler"]) > 1e-12:
                    raise RuntimeError(f"Aggregate LER mismatch {rep}/{suffix}")
                if (c_only, pm_only) != (record["paired_candidate_only"], record["paired_pymatching_only"]):
                    raise RuntimeError(f"Paired discordance mismatch {rep}/{suffix}")
                # Recompute temperature calibration on its independent split and
                # probability metrics on both calibration and threshold partitions.
                raw_cal_p = 1 / (1 + np.exp(-np.clip(cal_logits, -60, 60)))
                post_cal_p = 1 / (1 + np.exp(-np.clip(cal_logits / temp, -60, 60)))
                threshold_p = np.concatenate([threshold_probs[r] for r in REGIMES])
                cal_metrics = {"uncalibrated_on_calibration_partition": prob_metrics(raw_cal_p, cal_y),
                               "temperature_calibrated_on_calibration_partition": prob_metrics(post_cal_p, cal_y),
                               "temperature_calibrated_on_threshold_partition": prob_metrics(threshold_p, threshold_y)}
                rec = {"replicate": rep, "architecture": arch, "strategy": strategy,
                       "parameter_count": record["parameter_count"], "best_epoch": record["best_epoch"],
                       "temperature": temp, "threshold": threshold, "equal_regime_ler": equal_ler,
                       "equal_regime_pymatching_ler": equal_pm,
                       "paired_ler_difference": equal_ler-equal_pm,
                       "candidate_only": c_only, "pymatching_only": pm_only,
                       "per_regime": per_regime, "probability_calibration": cal_metrics}
                recomputed.append(rec)
                # Fresh verified counts are independent of runner aggregate counters.
                if abs(cal_metrics["temperature_calibrated_on_threshold_partition"]["brier"] -
                       record["probability_calibration"]["temperature_calibrated_on_threshold_partition"]["brier"]) > 1e-6:
                    raise RuntimeError(f"Calibration metric mismatch {rep}/{suffix}")

    # Recompute the validation checkpoint choice from recorded epoch losses.
    for (rep, arch, strategy), row in stored_records.items():
        history = row["history"]
        best = min(history, key=lambda x: (x["validation_monitor_nll"], x["validation_monitor_ler_at_0_5"], x["epoch"]))
        if int(best["epoch"]) != int(row["best_epoch"]):
            raise RuntimeError(f"Best-validation epoch mismatch for {rep}/{arch}/{strategy}")

    aggregate = aggregate_results(recomputed)
    verified = {"status": "PASS_INDEPENDENT_RECOMPUTATION", "model_fits": len(recomputed),
                "independent_development_roots": 3, "threshold_evaluation_shots_per_root": 3000,
                "test_samples_generated_or_accessed": 0, "frozen_source_hashes_verified": len(freeze["source_sha256"]),
                "post_run_reporting_patch_verified": True,
                "paired_detector_observable_archives_verified": 9,
                "stored_prediction_arrays_exactly_redecoded": len(recomputed) * len(REGIMES),
                "all_aggregate_counters_recomputed_from_saved_arrays": True,
                "records": recomputed, "aggregate": aggregate,
                "runner_issue": "The execution completed and persisted results; its final CSV export raised KeyError for a missing derived paired_ler_difference field. This independent audit reconstructed CSV/report outputs from saved checkpoints and arrays without simulation."}
    save_json(verified, OUT / "VERIFIED_RESULTS.json")
    write_csv(recomputed, aggregate)
    return verified


def aggregate_results(records):
    tcrit = 4.302652729911275
    out = {}
    keys = sorted({(r["architecture"], r["strategy"]) for r in records})
    for arch, strategy in keys:
        rows = [r for r in records if r["architecture"] == arch and r["strategy"] == strategy]
        delta = np.asarray([r["paired_ler_difference"] for r in rows], dtype=np.float64)
        mean = float(delta.mean()); half = tcrit * float(delta.std(ddof=1)) / math.sqrt(len(delta))
        by_regime = {}
        for regime in REGIMES:
            cell = [r["per_regime"][regime] for r in rows]
            d = np.asarray([c["paired_ler_difference"] for c in cell], dtype=np.float64)
            rm = float(d.mean()); rh = tcrit * float(d.std(ddof=1)) / math.sqrt(len(d))
            by_regime[regime] = {"mean_ler": float(np.mean([c["logical_error_rate"] for c in cell])),
                                 "mean_pymatching_ler": float(np.mean([c["pymatching_ler"] for c in cell])),
                                 "mean_positive_recall": float(np.mean([c["positive_recall"] for c in cell])),
                                 "tn": sum(c["tn"] for c in cell), "fp": sum(c["fp"] for c in cell),
                                 "fn": sum(c["fn"] for c in cell), "tp": sum(c["tp"] for c in cell),
                                 "candidate_only": sum(c["candidate_only"] for c in cell),
                                 "pymatching_only": sum(c["pymatching_only"] for c in cell),
                                 "mean_paired_ler_difference": rm, "root_t_95ci": [rm-rh, rm+rh]}
        out[f"{arch}__{strategy}"] = {"n_roots": len(rows), "parameter_count": rows[0]["parameter_count"],
            "mean_ler": float(np.mean([r["equal_regime_ler"] for r in rows])),
            "mean_pymatching_ler": float(np.mean([r["equal_regime_pymatching_ler"] for r in rows])),
            "mean_paired_ler_difference": mean, "root_t_95ci_paired_difference": [mean-half, mean+half],
            "root_differences": delta.tolist(),
            "mean_positive_recall": float(np.mean([np.mean([r["per_regime"][rg]["positive_recall"] for rg in REGIMES]) for r in rows])),
            "candidate_only": sum(r["candidate_only"] for r in rows), "pymatching_only": sum(r["pymatching_only"] for r in rows),
            "temperature_mean": float(np.mean([r["temperature"] for r in rows])),
            "threshold_mean": float(np.mean([r["threshold"] for r in rows])), "by_regime": by_regime}
    # Paired architecture contrasts on the same root and strategy.
    for strategy in sorted({r["strategy"] for r in records}):
        for arch in ARCHS:
            if arch in ("pooled_cnn8", "pooled_cnn16_capacity_control"): continue
            lhs = {(r["replicate"]): r for r in records if r["architecture"] == arch and r["strategy"] == strategy}
            rhs = {(r["replicate"]): r for r in records if r["architecture"] == "pooled_cnn8" and r["strategy"] == strategy}
            ds = [lhs[i]["equal_regime_ler"] - rhs[i]["equal_regime_ler"] for i in sorted(lhs)]
            m = float(np.mean(ds)); h = tcrit * float(np.std(ds, ddof=1)) / math.sqrt(len(ds))
            out[f"contrast__{arch}_minus_pooled_cnn8__{strategy}"] = {"paired_root_differences": ds,
                "mean_difference": m, "root_t_95ci": [m-h, m+h], "n_roots": len(ds)}
        for arch in ("position_flat_cnn", "coordinate_channel_cnn", "balanced_mlp"):
            a = {r["replicate"]: r for r in records if r["architecture"] == arch and r["strategy"] == strategy}
            b = {r["replicate"]: r for r in records if r["architecture"] == "pooled_cnn16_capacity_control" and r["strategy"] == strategy}
            ds = [a[i]["equal_regime_ler"] - b[i]["equal_regime_ler"] for i in sorted(a)]
            m = float(np.mean(ds)); h = tcrit * float(np.std(ds, ddof=1)) / math.sqrt(len(ds))
            out[f"contrast__{arch}_minus_pooled_cnn16__{strategy}"] = {"paired_root_differences": ds,
                "mean_difference": m, "root_t_95ci": [m-h, m+h], "n_roots": len(ds)}
    # Capacity-control contrast: pooled wider model vs standard pooled CNN.
    for strategy in sorted({r["strategy"] for r in records}):
        a = {r["replicate"]: r for r in records if r["architecture"] == "pooled_cnn16_capacity_control" and r["strategy"] == strategy}
        b = {r["replicate"]: r for r in records if r["architecture"] == "pooled_cnn8" and r["strategy"] == strategy}
        ds = [a[i]["equal_regime_ler"] - b[i]["equal_regime_ler"] for i in sorted(a)]
        m = float(np.mean(ds)); h = tcrit * float(np.std(ds, ddof=1)) / math.sqrt(len(ds))
        out[f"contrast__pooled_cnn16_minus_pooled_cnn8__{strategy}"] = {"paired_root_differences": ds,
            "mean_difference": m, "root_t_95ci": [m-h, m+h], "n_roots": len(ds)}
    return out


def write_csv(records, aggregate):
    fields = ["replicate", "architecture", "strategy", "parameter_count", "best_epoch", "temperature", "threshold",
              "equal_regime_ler", "equal_regime_pymatching_ler", "paired_ler_difference", "candidate_only", "pymatching_only"]
    with (OUT / "per_root_results.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for row in records: w.writerow({k: row[k] for k in fields})
    fields = ["model_strategy", "parameter_count", "n_roots", "mean_ler", "mean_pymatching_ler",
              "mean_paired_difference", "ci95_low", "ci95_high", "mean_positive_recall", "candidate_only", "pymatching_only"]
    with (OUT / "aggregate_results.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for name, row in aggregate.items():
            if name.startswith("contrast__"): continue
            ci95 = row["root_t_95ci_paired_difference"]
            w.writerow({"model_strategy": name, "parameter_count": row["parameter_count"], "n_roots": row["n_roots"],
                        "mean_ler": row["mean_ler"], "mean_pymatching_ler": row["mean_pymatching_ler"],
                        "mean_paired_difference": row["mean_paired_ler_difference"], "ci95_low": ci95[0], "ci95_high": ci95[1],
                        "mean_positive_recall": row["mean_positive_recall"], "candidate_only": row["candidate_only"],
                        "pymatching_only": row["pymatching_only"]})
    with (OUT / "per_regime_results.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["model_strategy", "regime", "mean_ler", "mean_pymatching_ler", "mean_positive_recall",
                  "tn", "fp", "fn", "tp", "candidate_only", "pymatching_only", "mean_paired_difference", "ci95_low", "ci95_high"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for name, row in aggregate.items():
            if name.startswith("contrast__"): continue
            for regime, cell in row["by_regime"].items():
                w.writerow({"model_strategy": name, "regime": regime, "mean_ler": cell["mean_ler"],
                    "mean_pymatching_ler": cell["mean_pymatching_ler"], "mean_positive_recall": cell["mean_positive_recall"],
                    **{k: cell[k] for k in ("tn", "fp", "fn", "tp", "candidate_only", "pymatching_only")},
                    "mean_paired_difference": cell["mean_paired_ler_difference"],
                    "ci95_low": cell["root_t_95ci"][0], "ci95_high": cell["root_t_95ci"][1]})


if __name__ == "__main__":
    result = main()
    print(json.dumps({"status": result["status"], "fits": result["model_fits"],
                      "test_shots": result["test_samples_generated_or_accessed"],
                      "saved_predictions_verified": result["stored_prediction_arrays_exactly_redecoded"]}, indent=2))
