"""Frozen aggregate analysis for Stage 4C; all metrics use saved paired arrays."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import torch

from outputs.stage4_noise_adaptive_feasibility_v1.prototype import DetectorProfileEstimator
from .experiment import RUN_DIR, HERE
from .models import (BurstProbabilityCNN, RidgeBurstRegressor, batch_feature_vector,
                     detector_coordinate_map, encode_calibration_batch, parameter_count)
from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit

CONDITIONS = (0.0, 0.004, 0.008, 0.012, 0.016)
METHODS = {"fixed_nominal": "pred_fixed", "stage4b_profile": "pred_profile",
           "ridge": "pred_ridge", "cnn": "pred_cnn", "privileged_true_p": "pred_privileged"}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_models_and_partitions():
    with np.load(RUN_DIR / "training_batches.npz", allow_pickle=False) as z:
        train_d, train_p = z["detectors"], z["probabilities"]
    with np.load(RUN_DIR / "validation_batches.npz", allow_pickle=False) as z:
        valid_d, valid_p = z["detectors"], z["probabilities"]
    profile = DetectorProfileEstimator.fit([(float(p), d) for p, d in zip(train_p, train_d)])
    ridge_j = read_json(RUN_DIR / "ridge_model.json")
    ridge = RidgeBurstRegressor(np.asarray(ridge_j["mean"]), np.asarray(ridge_j["scale"]),
                                np.asarray(ridge_j["coef"]), float(ridge_j["alpha"]))
    circuit = build_spatial_burst_circuit(burst_probability=0.0)
    coords = detector_coordinate_map(circuit.get_detector_coordinates())
    torch.set_num_threads(1)
    cnn = BurstProbabilityCNN().cpu().eval()
    ckpt = torch.load(RUN_DIR / "cnn_checkpoint.pt", map_location="cpu", weights_only=True)
    cnn.load_state_dict(ckpt["state_dict"])
    return profile, ridge, cnn, coords, train_d, train_p, valid_d, valid_p, ckpt


def infer_cnn_batch(model, detectors, coords) -> float:
    x = encode_calibration_batch(detectors, coords)
    with torch.no_grad():
        return float(model(torch.from_numpy(x[None])).item() * 0.02)


def infer_models_on_batch(d, profile, ridge, cnn, coords):
    d = np.asarray(d)
    if d.ndim != 2 or d.shape[1] != 40 or d.shape[0] % 250:
        raise ValueError("detector calibration arrays must be a positive multiple of 250 shots")
    chunks = d.reshape(-1, 250, 40)
    cnn_values = np.asarray([infer_cnn_batch(cnn, x, coords) for x in chunks])
    ridge_values = np.asarray([ridge.predict(batch_feature_vector(x)[None])[0] for x in chunks])
    return {"profile": profile.estimate(d), "ridge": float(ridge_values.mean()),
            "cnn": float(cnn_values.mean()), "cnn_chunks": cnn_values.tolist(),
            "ridge_chunks": ridge_values.tolist()}


def signflip_p(differences: np.ndarray, rng: np.random.Generator, assignments: int = 100000) -> float:
    d = np.asarray(differences, dtype=np.float64)
    if d.shape != (4, 7):
        raise ValueError(f"primary sign-flip expects 4x7 root effects, got {d.shape}")
    observed = float(d.mean())
    signs = rng.choice(np.array([-1.0, 1.0]), size=(assignments, 4, 7), replace=True)
    permuted = (signs * d[None, :, :]).mean(axis=(1, 2))
    extreme = int(np.sum(np.abs(permuted) >= abs(observed) - 1e-15))
    return float((extreme + 1) / (assignments + 1))


def signflip_p_general(differences: np.ndarray, rng: np.random.Generator,
                       assignments: int = 100000) -> float:
    d = np.asarray(differences, dtype=np.float64)
    if d.shape != (4, 7):
        raise ValueError("secondary sign-flip expects four strata and seven roots")
    obs = float(d.mean())
    signs = rng.choice(np.array([-1.0, 1.0]), size=(assignments, 4, 7), replace=True)
    vals = (signs * d[None]).mean(axis=(1, 2))
    return float((np.sum(np.abs(vals) >= abs(obs) - 1e-15) + 1) / (assignments + 1))


def holm_adjust(pvalues: dict[str, float]) -> dict[str, float]:
    ordered = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(ordered)
    adjusted = {}
    running = 0.0
    for i, (name, p) in enumerate(ordered):
        running = max(running, min(1.0, (m - i) * p))
        adjusted[name] = running
    return adjusted


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    status = read_json(RUN_DIR / "status.json")
    if status.get("status") != "completed" or status.get("completed_jobs") != 35 or status.get("independent_test_accessed") != 0:
        raise RuntimeError("cannot analyze incomplete or seal-violating run")
    profile, ridge, cnn, coords, train_d, train_p, valid_d, valid_p, ckpt = load_models_and_partitions()
    val_pred = {"profile": [], "ridge": [], "cnn": []}
    for d in valid_d:
        est = infer_models_on_batch(d, profile, ridge, cnn, coords)
        for name in val_pred:
            val_pred[name].append(est[name])
    validation_metrics = {name: {"mae": float(np.mean(np.abs(np.asarray(v) - valid_p))),
                                  "bias": float(np.mean(np.asarray(v) - valid_p))}
                          for name, v in val_pred.items()}
    train_pred = {"profile": [], "ridge": [], "cnn": []}
    for d in train_d:
        est = infer_models_on_batch(d, profile, ridge, cnn, coords)
        for name in train_pred:
            train_pred[name].append(est[name])
    training_metrics = {name: {"mae": float(np.mean(np.abs(np.asarray(v) - train_p))),
                                "bias": float(np.mean(np.asarray(v) - train_p))}
                        for name, v in train_pred.items()}
    root_rows, condition_rows = [], []
    estimate_matrix = {name: np.zeros((5, 7), dtype=np.float64) for name in ("profile", "ridge", "cnn")}
    ler = {name: np.zeros((5, 7), dtype=np.float64) for name in METHODS}
    errors = {name: np.zeros((5, 7), dtype=np.int64) for name in METHODS}
    raw_errors = np.zeros((5, 7), dtype=np.int64)
    discord = {}
    detailed_pairs = {"cnn_minus_profile": ("cnn", "stage4b_profile"),
                      "cnn_minus_fixed": ("cnn", "fixed_nominal"),
                      "cnn_minus_ridge": ("cnn", "ridge"),
                      "ridge_minus_profile": ("ridge", "stage4b_profile")}
    discord_by_condition = {name: {str(p): {"candidate_only": 0, "comparator_only": 0,
                                           "prediction_disagreements": 0}
                                   for p in CONDITIONS} for name in detailed_pairs}
    root_runtime = []
    for pi, p in enumerate(CONDITIONS):
        for root in range(7):
            path = RUN_DIR / "roots" / f"p{int(round(p*1000)):03d}_root{root:02d}.npz"
            with np.load(path, allow_pickle=False) as z:
                cal, det, obs = z["calibration_detectors"], z["evaluation_detectors"], z["observables"]
                pred = {name: z[key].astype(np.uint8) for name, key in METHODS.items()}
                meta = json.loads(str(z["metadata_json"].item()))
            est = infer_models_on_batch(cal, profile, ridge, cnn, coords)
            for name in estimate_matrix:
                estimate_matrix[name][pi, root] = est[name]
            row = {"probability": p, "root": root, "calibration_shots": len(cal), "evaluation_shots": len(obs),
                   "p_hat_profile": est["profile"], "p_hat_ridge": est["ridge"], "p_hat_cnn": est["cnn"],
                   "profile_abs_p_error": abs(est["profile"] - p), "ridge_abs_p_error": abs(est["ridge"] - p),
                   "cnn_abs_p_error": abs(est["cnn"] - p),
                   "cnn_minus_profile_ler": float(np.mean((pred["cnn"] ^ obs)) - np.mean((pred["stage4b_profile"] ^ obs))),
                   "cnn_minus_ridge_ler": float(np.mean((pred["cnn"] ^ obs)) - np.mean((pred["ridge"] ^ obs))),
                   "cnn_minus_fixed_ler": float(np.mean((pred["cnn"] ^ obs)) - np.mean((pred["fixed_nominal"] ^ obs))),
                   "cnn_estimator_inference_seconds": meta["estimator_inference_seconds"]["cnn"],
                   "profile_estimator_inference_seconds": meta["estimator_inference_seconds"]["profile"],
                   "ridge_estimator_inference_seconds": meta["estimator_inference_seconds"]["ridge"],
                   "cnn_parameters": meta["cnn_parameter_count"]}
            raw_errors[pi, root] = int(obs.sum())
            row["raw_observable_errors"] = int(obs.sum())
            for name, prediction in pred.items():
                e = prediction ^ obs
                errors[name][pi, root] = int(e.sum())
                ler[name][pi, root] = float(e.mean())
                row[f"{name}_errors"] = int(e.sum())
                row[f"{name}_ler"] = float(e.mean())
            for name in ("stage4b_profile", "ridge", "cnn", "privileged_true_p"):
                a = pred[name] ^ obs
                b = pred["fixed_nominal"] ^ obs
                discord[f"{name}_vs_fixed"] = discord.get(f"{name}_vs_fixed", {"candidate_only": 0, "fixed_only": 0, "prediction_disagreements": 0})
                discord[f"{name}_vs_fixed"]["candidate_only"] += int(np.sum(a & ~b))
                discord[f"{name}_vs_fixed"]["fixed_only"] += int(np.sum(~a & b))
                discord[f"{name}_vs_fixed"]["prediction_disagreements"] += int(np.sum(pred[name] != pred["fixed_nominal"]))
                row[f"{name}_candidate_only_vs_fixed"] = int(np.sum(a & ~b))
                row[f"{name}_fixed_only_vs_candidate"] = int(np.sum(~a & b))
                row[f"{name}_prediction_disagreements_vs_fixed"] = int(np.sum(pred[name] != pred["fixed_nominal"]))
            for comp, (candidate, baseline) in detailed_pairs.items():
                a, b = (pred[candidate] ^ obs).astype(bool), (pred[baseline] ^ obs).astype(bool)
                c1, c2 = int(np.sum(a & ~b)), int(np.sum(~a & b))
                disagree = int(np.sum(pred[candidate] != pred[baseline]))
                entry = discord.setdefault(comp, {"candidate_only": 0, "comparator_only": 0,
                                                   "prediction_disagreements": 0})
                entry["candidate_only"] += c1
                entry["comparator_only"] += c2
                entry["prediction_disagreements"] += disagree
                dc = discord_by_condition[comp][str(p)]
                dc["candidate_only"] += c1
                dc["comparator_only"] += c2
                dc["prediction_disagreements"] += disagree
                row[f"{comp}_candidate_only"] = c1
                row[f"{comp}_comparator_only"] = c2
                row[f"{comp}_prediction_disagreements"] = disagree
            root_rows.append(row)
            root_runtime.append(meta["decoder_build_seconds"])
    # Paired root bootstrap. One shared index cube preserves cross-decoder pairing.
    cfg = read_json(HERE / "config.json")
    rng = np.random.default_rng(int(cfg["statistical_plan"]["bootstrap"]["seed"]))
    boot_idx = rng.integers(0, 7, size=(20000, 5, 7))
    pair_names = {"cnn_minus_profile": ("cnn", "stage4b_profile"),
                  "cnn_minus_fixed": ("cnn", "fixed_nominal"),
                  "cnn_minus_ridge": ("cnn", "ridge"),
                  "ridge_minus_profile": ("ridge", "stage4b_profile")}
    pair_deltas = {name: ler[a] - ler[b] for name, (a, b) in pair_names.items()}
    boot_primary = {}
    for name, d in pair_deltas.items():
        boot_by_p = np.empty((20000, 5), dtype=np.float64)
        for pi in range(5):
            boot_by_p[:, pi] = np.mean(d[pi][boot_idx[:, pi, :]], axis=1)
        boot_primary[name] = boot_by_p
    primary_draws = np.mean(boot_primary["cnn_minus_profile"][:, 1:], axis=1)
    primary_delta = float(np.mean(pair_deltas["cnn_minus_profile"][1:]))
    primary_ci = [float(np.quantile(primary_draws, 0.025)), float(np.quantile(primary_draws, 0.975))]
    zero_upper = float(np.quantile(boot_primary["cnn_minus_profile"][:, 0], 0.95))
    sign_rng = np.random.default_rng(int(cfg["statistical_plan"]["primary_test"]["seed"]))
    primary_p = signflip_p(pair_deltas["cnn_minus_profile"][1:], sign_rng)
    secondary_raw = {}
    for name in ("cnn_minus_fixed", "cnn_minus_ridge", "ridge_minus_profile"):
        secondary_raw[name] = signflip_p_general(pair_deltas[name][1:], sign_rng)
    secondary_holm = holm_adjust(secondary_raw)
    method_summary = {}
    for name, values in ler.items():
        nonzero = float(np.mean(values[1:]))
        full = float(np.mean(values))
        boot_cond = np.empty((20000, 5), dtype=np.float64)
        for pi in range(5):
            boot_cond[:, pi] = np.mean(values[pi][boot_idx[:, pi, :]], axis=1)
        method_summary[name] = {
            "total_errors": int(errors[name].sum()), "total_shots": 87500,
            "overall_ler": float(errors[name].sum() / 87500),
            "equal_all_condition_mean_ler": full,
            "equal_nonzero_condition_mean_ler": nonzero,
            "per_condition_errors": {str(p): int(errors[name][i].sum()) for i, p in enumerate(CONDITIONS)},
            "per_condition_shots": {str(p): 17500 for p in CONDITIONS},
            "per_condition_ler": {str(p): float(errors[name][i].sum() / 17500) for i, p in enumerate(CONDITIONS)},
            "per_condition_root_bootstrap_95ci": {str(p): [float(np.quantile(boot_cond[:, i], .025)),
                                                           float(np.quantile(boot_cond[:, i], .975))]
                                                   for i, p in enumerate(CONDITIONS)},
            "root_ler_matrix": values.tolist(),
        }
    comparisons = {}
    for name, d in pair_deltas.items():
        nonzero_draws = np.mean(boot_primary[name][:, 1:], axis=1)
        comparisons[name] = {"equal_weight_nonzero_mean_delta_ler": float(np.mean(d[1:])),
            "bootstrap_95ci": [float(np.quantile(nonzero_draws, .025)), float(np.quantile(nonzero_draws, .975))],
            "per_condition_mean_delta": {str(p): float(np.mean(d[i])) for i,p in enumerate(CONDITIONS)},
            "per_condition_bootstrap_95ci": {str(p): [float(np.quantile(boot_primary[name][:, i], .025)),
                                                          float(np.quantile(boot_primary[name][:, i], .975))]
                                             for i,p in enumerate(CONDITIONS)},
            "per_root_delta_matrix": d.tolist()}
    estimate_summary = {}
    for name, estimates in estimate_matrix.items():
        signed = estimates - np.asarray(CONDITIONS)[:, None]
        absolute = np.abs(signed)
        boot_mae = np.mean(np.stack([absolute[i][boot_idx[:, i, :]].mean(axis=1) for i in range(1,5)], axis=1), axis=1)
        estimate_summary[name] = {"overall_nonzero_mae": float(np.mean(absolute[1:])),
            "overall_nonzero_bias": float(np.mean(signed[1:])),
            "overall_nonzero_mae_bootstrap_95ci": [float(np.quantile(boot_mae,.025)), float(np.quantile(boot_mae,.975))],
            "per_condition_mae": {str(p): float(np.mean(absolute[i])) for i,p in enumerate(CONDITIONS)},
            "per_condition_bias": {str(p): float(np.mean(signed[i])) for i,p in enumerate(CONDITIONS)},
            "estimate_matrix": estimates.tolist()}
    favorable = sum(float(np.mean(pair_deltas["cnn_minus_profile"][i])) < 0 for i in range(1,5))
    validation_cnn_vs_ridge = validation_metrics["cnn"]["mae"] - validation_metrics["ridge"]["mae"]
    gate = {
        "primary_delta_at_most_minus_0.0002": primary_delta <= -0.0002,
        "primary_bootstrap_upper_below_zero": primary_ci[1] < 0,
        "primary_signflip_p_below_0.05": primary_p < 0.05,
        "at_least_3_of_4_nonzero_conditions_favor_cnn": favorable >= 3,
        "zero_burst_one_sided_upper_within_0.0002": zero_upper <= 0.0002,
        "cnn_validation_mae_not_more_than_0.0005_worse_than_ridge": validation_cnn_vs_ridge <= 0.0005,
    }
    keep = all(gate.values())
    if keep:
        recommendation = "CNN KEEP"
    elif primary_delta >= 0 or primary_ci[0] > -0.0002 or zero_upper > 0.0002:
        recommendation = "CNN DROP"
    else:
        recommendation = "CNN INCONCLUSIVE"
    results = {"study": "Q-SHIFT Stage 4C CNN-assisted adaptive PyMatching",
        "status": "ANALYZED_DEVELOPMENT_ONLY", "independent_test_accessed": False,
        "independent_test_accessed_count": 0, "shots": {"training_detector_only": 90000,
            "validation_detector_only": 30000, "evaluation_calibration_detector_only": 70000,
            "paired_evaluation_detector_observables": 87500, "total_unique": 277500},
        "evaluation_roots": 35, "independent_roots_per_condition": 7,
        "condition_probabilities": list(CONDITIONS), "methods": method_summary,
        "paired_discordances_vs_fixed_nominal": discord,
        "paired_discordances_by_condition": discord_by_condition,
        "paired_comparisons": comparisons,
        "primary": {"comparison": "CNN-assisted minus Stage4B profile-assisted PyMatching",
            "estimand": cfg["statistical_plan"]["primary_estimand"], "delta_ler": primary_delta,
            "bootstrap_95ci": primary_ci, "signflip_p_two_sided": primary_p,
            "signflip_assignments": 100000, "bootstrap_resamples": 20000,
            "zero_burst_one_sided_95_upper": zero_upper,
            "nonzero_condition_wins": favorable},
        "secondary_signflip_p_raw": secondary_raw, "secondary_signflip_p_holm": secondary_holm,
        "noise_estimation": estimate_summary, "training_metrics": training_metrics,
        "validation_metrics": validation_metrics,
        "ridge_selection": read_json(RUN_DIR / "ridge_model.json"),
        "cnn_training": read_json(RUN_DIR / "training_diagnostics.json"),
        "cnn_validation_mae_minus_ridge": validation_cnn_vs_ridge,
        "resource": {"elapsed_seconds": status.get("active_runtime_seconds"),
            "peak_rss_bytes": status.get("peak_rss_bytes"), "cnn_parameters": parameter_count(cnn),
            "cnn_checkpoint_sha256": read_json(RUN_DIR / "training_diagnostics.json")["checkpoint_sha256"],
            "decoder_build_seconds_median": {k: float(np.median([r[k] for r in root_runtime])) for k in root_runtime[0]},
            "estimator_inference_seconds_median": {"cnn": float(np.median([r["cnn_estimator_inference_seconds"] for r in root_rows])),
                "profile": float(np.median([r["profile_estimator_inference_seconds"] for r in root_rows])),
                "ridge": float(np.median([r["ridge_estimator_inference_seconds"] for r in root_rows]))}},
        "decision_gate": gate, "recommendation": recommendation,
        "caveats": ["development-only, seven independent evaluation roots per condition",
            "synthetic per-round spatial burst at one code distance, basis and burst pair",
            "Stim categorical two-qubit DEM uses approximate_disjoint_errors=True",
            "CNN training variability is conditional on one frozen training allocation and one initialization seed",
            "profile and supervised estimators use fresh Stage 4C training data; Stage 4B evaluation samples were not reused",
            "no hardware validation or independent confirmation"]}
    (HERE / "STAGE4C_RESULTS.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    write_csv(HERE / "STAGE4C_PER_ROOT.csv", root_rows)
    for pi,p in enumerate(CONDITIONS):
        row = {"probability": p, "roots": 7, "shots": 17500,
               "raw_observable_errors": int(raw_errors[pi].sum())}
        for name in METHODS:
            row[f"{name}_errors"] = int(errors[name][pi].sum())
            row[f"{name}_ler"] = float(errors[name][pi].sum()/17500)
            row[f"{name}_root_bootstrap_ci_low"] = method_summary[name]["per_condition_root_bootstrap_95ci"][str(p)][0]
            row[f"{name}_root_bootstrap_ci_high"] = method_summary[name]["per_condition_root_bootstrap_95ci"][str(p)][1]
        for name in pair_names:
            row[f"{name}_mean_delta"] = comparisons[name]["per_condition_mean_delta"][str(p)]
            row[f"{name}_candidate_only"] = discord_by_condition[name][str(p)]["candidate_only"]
            row[f"{name}_comparator_only"] = discord_by_condition[name][str(p)]["comparator_only"]
            row[f"{name}_prediction_disagreements"] = discord_by_condition[name][str(p)]["prediction_disagreements"]
        condition_rows.append(row)
    write_csv(HERE / "STAGE4C_PER_CONDITION.csv", condition_rows)
    result_lines = ["# Q-SHIFT Stage 4C — Results", "",
        "Exploratory development result only. No independent-test data were accessed.", "",
        f"Unique shots: **277,500** across 90,000 training, 30,000 validation, 70,000 calibration, and 87,500 paired evaluation shots.",
        "The five decoder arms used identical held-out detector/observable arrays.", "",
        "## Paired evaluation by decoder", "", "| Decoder | Errors / shots | LER | Equal-weight nonzero-condition LER |", "|---|---:|---:|---:|"]
    display_names = {"fixed_nominal":"Fixed nominal PyMatching", "stage4b_profile":"Stage 4B profile estimator + PyMatching",
                     "ridge":"Ridge estimator + PyMatching", "cnn":"CNN estimator + PyMatching",
                     "privileged_true_p":"Privileged true-p PyMatching reference"}
    for name, vals in method_summary.items():
        result_lines.append(f"| {display_names[name]} | {vals['total_errors']:,} / 87,500 | {vals['overall_ler']:.6%} | {vals['equal_nonzero_condition_mean_ler']:.6%} |")
    result_lines += ["", "## Results by burst probability", "", "| p | Fixed | Stage4B profile | Ridge | CNN | True-p reference |", "|---:|---:|---:|---:|---:|---:|"]
    for p in CONDITIONS:
        result_lines.append("| " + f"{p:.3f}" + " | " + " | ".join(
            f"{method_summary[m]['per_condition_errors'][str(p)]}/{17500} ({method_summary[m]['per_condition_ler'][str(p)]:.4%})"
            for m in METHODS) + " |")
    c = comparisons["cnn_minus_profile"]
    result_lines += ["", "## Primary paired comparison", "",
        f"Equal-weight CNN-minus-Stage4B-profile LER difference across nonzero conditions: **{primary_delta:+.6%}**.",
        f"Stratified root-bootstrap 95% CI: **[{primary_ci[0]:+.6%}, {primary_ci[1]:+.6%}]**; two-sided root sign-flip p={primary_p:.6g}.",
        f"The CNN favored {favorable}/4 nonzero conditions. At p=0, its one-sided 95% upper difference bound is {zero_upper:+.6%}.",
        "", "Noise-estimation MAE and signed bias by method are in `STAGE4C_RESULTS.json`; per-root paired outcomes are in `STAGE4C_PER_ROOT.csv`.",
        "The true-p arm is privileged and is not a deployable method. DEM conversion approximates disjoint categorical errors; the burst model is synthetic."]
    (HERE / "STAGE4C_RESULTS.md").write_text("\n".join(result_lines)+"\n", encoding="utf-8")
    stat_lines = ["# Stage 4C — Statistical Comparison", "",
        f"**Primary:** CNN-assisted minus Stage4B-profile-assisted PyMatching, equal-weight mean over p={','.join(f'{p:.3f}' for p in CONDITIONS[1:])}.",
        f"Effect={primary_delta:+.8f}; 95% stratified root-bootstrap CI [{primary_ci[0]:+.8f}, {primary_ci[1]:+.8f}]; sign-flip p={primary_p:.6g}.",
        "Resampling unit: independent root, with seven roots resampled within each p stratum. No shot-level bootstrap.", "",
        "| p | CNN − profile ΔLER | 95% root bootstrap CI | Candidate-only | Profile-only | Prediction disagreements |", "|---:|---:|---|---:|---:|---:|"]
    for i,p in enumerate(CONDITIONS):
        lo,hi=comparisons["cnn_minus_profile"]["per_condition_bootstrap_95ci"][str(p)]
        dis=discord_by_condition["cnn_minus_profile"][str(p)]
        stat_lines.append(f"| {p:.3f} | {comparisons['cnn_minus_profile']['per_condition_mean_delta'][str(p)]:+.6%} | [{lo:+.6%}, {hi:+.6%}] | {dis['candidate_only']} | {dis['comparator_only']} | {dis['prediction_disagreements']} |")
    stat_lines += ["", "## Prespecified secondary family (Holm adjusted)", "",
        "| Comparison | Raw two-sided sign-flip p | Holm adjusted p |", "|---|---:|---:|"]
    for name in secondary_raw:
        stat_lines.append(f"| {name.replace('_',' ')} | {secondary_raw[name]:.6g} | {secondary_holm[name]:.6g} |")
    stat_lines += ["", "Condition-specific intervals are descriptive and not individually confirmatory. Primary sign-flip inference assumes independent roots and approximate symmetry of root-level paired effects under its null."]
    (HERE / "STAGE4C_STATISTICAL_COMPARISON.md").write_text("\n".join(stat_lines)+"\n", encoding="utf-8")
    rec_lines = ["# Stage 4C — CNN Recommendation", "", f"**Recommendation: {recommendation}.**", "",
        "| Frozen criterion | Result |", "|---|---|"]
    for key,val in gate.items():
        rec_lines.append(f"| {key.replace('_',' ')} | {'PASS' if val else 'FAIL'} |")
    rec_lines += ["", f"Primary CNN minus Stage 4B profile effect: {primary_delta:+.6%}, 95% root-bootstrap CI [{primary_ci[0]:+.6%}, {primary_ci[1]:+.6%}], p={primary_p:.6g}.",
        f"Validation MAE: CNN {validation_metrics['cnn']['mae']:.6g}; Ridge {validation_metrics['ridge']['mae']:.6g}; profile {validation_metrics['profile']['mae']:.6g}.",
        "", "This decision concerns only a detector-only estimator for the specified synthetic spatial-burst model. The true-probability PyMatching arm is a privileged reference. A CNN is not retained on architecture preference alone. If not kept, the simpler Stage 4B profile method remains the recommended estimator unless Ridge itself has a clear validated benefit.",
        "The experiment is development-only, uses one frozen CNN training allocation and seven paired roots per condition, and does not establish hardware performance or independent confirmation."]
    (HERE / "STAGE4C_FINAL_RECOMMENDATION.md").write_text("\n".join(rec_lines)+"\n", encoding="utf-8")
    print(json.dumps({"recommendation": recommendation, "primary_delta": primary_delta,
        "primary_ci": primary_ci, "primary_p": primary_p, "methods": {k: [v["total_errors"], v["overall_ler"]] for k,v in method_summary.items()}}, indent=2))


if __name__ == "__main__":
    main()
