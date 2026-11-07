"""Independent read-only recomputation from the sprint's saved development arrays.

This script does not import runner reporting/aggregation functions and has no
test-data or test-sampling code path.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
AUTO = REPO / "outputs" / "neural_decoder_diagnostic" / "autonomous_development"
sys.path.insert(0, str(REPO / "dashboard"))
sys.path.insert(0, str(AUTO))

from experiment import ResidualPositionCNN
from simulator import decode_matching, prepare

RUN = HERE / "run"
REGIMES = ("x_biased", "balanced", "z_biased")
TCRIT = 2.7764451051977987


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def fail(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def binary(values, name: str):
    a = np.asarray(values)
    fail(np.isfinite(a).all(), f"{name} contains nonfinite data")
    fail(np.all((a == 0) | (a == 1)), f"{name} is not binary")


def metrics(pred, obs, pm) -> dict:
    pred, obs, pm = (np.asarray(a, dtype=np.uint8) for a in (pred, obs, pm))
    binary(pred, "prediction"); binary(obs, "observable"); binary(pm, "PyMatching prediction")
    wrong, pm_wrong = pred ^ obs, pm ^ obs
    flips = pred ^ pm
    beneficial = int(np.sum((flips == 1) & (pm_wrong == 1)))
    harmful = int(np.sum((flips == 1) & (pm_wrong == 0)))
    return {"shots": len(obs), "errors": int(wrong.sum()), "ler": float(wrong.mean()),
        "pymatching_errors": int(pm_wrong.sum()), "pymatching_ler": float(pm_wrong.mean()),
        "paired_difference": float(wrong.mean() - pm_wrong.mean()),
        "candidate_only": int(np.sum((wrong == 1) & (pm_wrong == 0))),
        "pymatching_only": int(np.sum((wrong == 0) & (pm_wrong == 1))),
        "prediction_disagreements": int(np.sum(pred != pm)),
        "residual_positive_examples": int(pm_wrong.sum()),
        "residual_corrections": int(flips.sum()),
        "beneficial_corrections": beneficial, "harmful_corrections": harmful,
        "correction_precision": beneficial / (beneficial + harmful) if beneficial + harmful else None,
        "correction_recall": beneficial / int(pm_wrong.sum()) if pm_wrong.sum() else None}


def root_t(values):
    a = np.asarray(values, dtype=np.float64)
    mean = float(a.mean())
    half = TCRIT * float(a.std(ddof=1)) / math.sqrt(len(a))
    return {"mean": mean, "ci95_low": mean - half, "ci95_high": mean + half,
            "n_roots": len(a), "sd_root": float(a.std(ddof=1))}


def root_bootstrap(values, indices, confidence):
    a = np.asarray(values, dtype=np.float64)
    draws = a[indices].mean(axis=1)
    alpha = 1 - confidence
    return {"low": float(np.quantile(draws, alpha / 2)),
            "high": float(np.quantile(draws, 1 - alpha / 2)),
            "confidence": confidence, "resamples": len(indices)}


def close(a, b, tol=1e-10):
    return abs(float(a) - float(b)) <= tol


def main():
    cfg = load_json(HERE / "config.json")
    inv = load_json(HERE / "SEED_INVENTORY.json")
    freeze = load_json(HERE / "FREEZE.json")
    progress = load_json(RUN / "PROGRESS.json")
    results = load_json(RUN / "RESULTS.json")
    fail(int(progress.get("independent_test_access", -1)) == 0, "Progress reports nonzero/unknown test access")
    fail(results.get("independent_test_access") == 0, "Results report nonzero/unknown test access")
    fail(progress.get("status") == "completed", f"Run is not complete: {progress.get('status')}")
    fail(inv.get("passed") is True and inv.get("unique_derived_seed_count") == inv.get("derived_seed_count"),
         "Frozen seed inventory failed or is not unique")
    fail(sha(HERE / "config.json") == freeze["config_sha256"], "Frozen config hash mismatch")
    fail(sha(HERE / "EXPERIMENT_PROTOCOL.md") == freeze["protocol_sha256"], "Frozen protocol hash mismatch")
    fail(sha(HERE / "SEED_INVENTORY.json") == freeze["seed_inventory_sha256"], "Frozen seed inventory hash mismatch")

    prepared = {}
    for regime in REGIMES:
        c = cfg["circuit"]
        circuit, record, dem, matching, idx, bank = prepare({"memory_basis": c["memory_basis"],
            "noise_regime": regime, "distance": c["distance"], "rounds": c["rounds"],
            "gate_p": c["gate_p"], "measurement_p": c["measurement_p"], "bias_ratio": c["bias_ratio"]})
        prepared[regime] = {"circuit": circuit, "matching": matching, "coords": circuit.get_detector_coordinates()}

    final_data, redecoded_by_regime = {}, {r: 0 for r in REGIMES}
    for root in range(int(cfg["roots"])):
        archive = RUN / "data" / f"final_root_{root:02d}.npz"
        meta_path = archive.with_suffix(".json")
        fail(archive.is_file() and meta_path.is_file(), f"Missing final development arrays for root {root}")
        meta = load_json(meta_path)
        fail(sha(archive) == meta.get("archive_sha256"), f"Final sample archive hash mismatch root {root}")
        fail(meta.get("root") == root and meta.get("split") == "final_development_evaluation", f"Root/split mismatch root {root}")
        fail(meta.get("independent_test_access") == 0, f"Sample metadata test-access mismatch root {root}")
        with np.load(archive, allow_pickle=False) as z:
            arrays = {k: z[k] for k in z.files}
        expected = int(cfg["sampling"]["final_development_shots_per_regime_root"])
        root_data = {}
        for regime in REGIMES:
            d, obs, saved_pm = (arrays[f"detectors__{regime}"], arrays[f"observable__{regime}"], arrays[f"pymatching__{regime}"])
            binary(d, f"root {root} {regime} detector"); binary(obs, f"root {root} {regime} observable"); binary(saved_pm, "saved PM")
            fail(d.shape == (expected, 40) and obs.shape == (expected,) and saved_pm.shape == (expected,),
                 f"Unexpected final shapes root {root}/{regime}: {d.shape}/{obs.shape}/{saved_pm.shape}")
            decoded = np.asarray(decode_matching(prepared[regime]["matching"], d), dtype=np.uint8).reshape(-1)
            fail(np.array_equal(decoded, saved_pm), f"Independent PyMatching re-decode mismatch root {root}/{regime}")
            redecoded_by_regime[regime] += len(decoded)
            root_data[regime] = {"detectors": d, "observable": obs, "pymatching": saved_pm}
        final_data[root] = root_data

    job_rows, prediction_archive_count = [], 0
    policy_groups = {}
    all_jobs = [(root, strategy, int(size)) for root in range(int(cfg["roots"]))
                for strategy in cfg["models"]["strategies"]
                for size in cfg["sampling"]["train_budgets_per_regime_root"]]
    fail(len(all_jobs) == 30, "Expected exactly 30 frozen model jobs")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    for root, strategy, size in all_jobs:
        jid = f"root{root:02d}_{strategy}_{size}"
        selection_path = RUN / "selections" / f"{jid}.json"
        weights_path = RUN / "checkpoints" / f"{jid}.weights.pt"
        pred_path = RUN / "predictions" / f"{jid}.npz"
        pred_meta_path = pred_path.with_suffix(".json")
        fail(selection_path.is_file() and weights_path.is_file() and pred_path.is_file() and pred_meta_path.is_file(),
             f"Missing model evidence for {jid}")
        selection = load_json(selection_path); pmta = load_json(pred_meta_path)
        fail(sha(weights_path) == selection.get("weights_sha256"), f"Selected weights hash mismatch {jid}")
        fail(sha(pred_path) == pmta.get("archive_sha256"), f"Prediction archive hash mismatch {jid}")
        fail(pmta.get("selection_sha256") == sha(selection_path), f"Prediction not bound to selection {jid}")
        fail(selection.get("final_development_evaluation_accessed") is False, f"Selection leaked final data {jid}")
        with np.load(pred_path, allow_pickle=False) as z:
            pred_arrays = {k: z[k] for k in z.files}
        prediction_archive_count += 1
        model = ResidualPositionCNN(prepared["balanced"]["coords"],
            channels=int(cfg["models"]["training"]["channels"]),
            head_width=int(cfg["models"]["training"]["head_width"]),
            dropout=float(cfg["models"]["training"]["dropout"])).to(device)
        model_state = torch.load(weights_path, map_location="cpu", weights_only=True)
        model.load_state_dict(model_state); model.eval()
        eval_rows = []
        with torch.inference_mode():
            for regime in REGIMES:
                data = final_data[root][regime]
                saved_y, saved_pm = pred_arrays[f"observable__{regime}"], pred_arrays[f"pymatching__{regime}"]
                fail(np.array_equal(saved_y, data["observable"]), f"Observable pairing mismatch {jid}/{regime}")
                fail(np.array_equal(saved_pm, data["pymatching"]), f"PyMatching pairing mismatch {jid}/{regime}")
                target = data["observable"] ^ data["pymatching"]
                fail(np.array_equal(pred_arrays[f"residual_target__{regime}"], target), f"Residual target mismatch {jid}/{regime}")
                logits_parts = []
                for start in range(0, len(data["observable"]), int(cfg["models"]["training"]["evaluation_batch_size"])):
                    end = min(start + int(cfg["models"]["training"]["evaluation_batch_size"]), len(data["observable"]))
                    d = torch.as_tensor(data["detectors"][start:end], dtype=torch.float32, device=device)
                    pm = torch.as_tensor(data["pymatching"][start:end], dtype=torch.float32, device=device)
                    logits_parts.append((model(d, pm).float().cpu().numpy().astype(np.float64) +
                                         float(selection["logit_prior_correction"])))
                logits = np.concatenate(logits_parts)
                reconstructed_probs = 1.0 / (1.0 + np.exp(-np.clip(logits / float(selection["temperature"]), -60, 60)))
                saved_probs = pred_arrays[f"probability__{regime}"].astype(np.float64)
                fail(np.allclose(reconstructed_probs, saved_probs, rtol=0, atol=2e-5),
                     f"Checkpoint probability re-inference mismatch {jid}/{regime}")
                policy_thresholds = {"min_ler": float(selection["threshold_min_ler"])}
                if strategy == "balanced_minibatch":
                    policy_thresholds["confidence_gate"] = float(selection["confidence_gate"]["threshold"])
                for policy, threshold in policy_thresholds.items():
                    residual = (saved_probs >= threshold).astype(np.uint8)
                    pred = saved_pm ^ residual
                    stored = pred_arrays[f"prediction_{policy}__{regime}"]
                    stored_residual = pred_arrays[f"residual_prediction_{policy}__{regime}"]
                    fail(np.array_equal(stored_residual, residual), f"Stored correction rule mismatch {jid}/{policy}/{regime}")
                    fail(np.array_equal(stored, pred), f"Stored logical prediction mismatch {jid}/{policy}/{regime}")
                    m = metrics(pred, data["observable"], data["pymatching"])
                    row = {"root": root, "strategy": strategy, "train_size_per_regime": size,
                           "policy": policy, "regime": regime,
                           "threshold": threshold, **m}
                    job_rows.append(row)
                    policy_groups.setdefault((strategy, size, policy), []).append(row)

    paired_csv = list(csv.DictReader((RUN / "PAIRED_EVALUATION.csv").open("r", encoding="utf-8", newline="")))
    fail(len(paired_csv) == len(job_rows), f"CSV row count mismatch {len(paired_csv)} != {len(job_rows)}")
    idx = {(r["root"], r["strategy"], r["train_size_per_regime"], r["policy"], r["regime"]): r for r in job_rows}
    integer_metrics = ("shots", "errors", "pymatching_errors", "candidate_only", "pymatching_only",
                       "prediction_disagreements", "residual_positive_examples", "residual_corrections",
                       "beneficial_corrections", "harmful_corrections")
    for saved in paired_csv:
        key = (int(saved["root"]), saved["strategy"], int(saved["train_size_per_regime"]), saved["policy"], saved["regime"])
        fresh = idx[key]
        for field in integer_metrics:
            fail(int(float(saved[field])) == int(fresh[field]), f"CSV mismatch {field} for {key}")
        fail(close(saved["ler"], fresh["ler"]) and close(saved["paired_difference"], fresh["paired_difference"]),
             f"CSV rate mismatch for {key}")

    # Recompute all aggregate and seed-level analyses from the saved NPZ arrays.
    b = int(cfg["analysis"]["bootstrap_resamples"]); seed = int(cfg["analysis"]["bootstrap_seed"])
    rng = np.random.default_rng(seed)
    boot_idx = rng.integers(0, int(cfg["roots"]), size=(b, int(cfg["roots"])), dtype=np.int16)
    summaries = []
    for key in sorted(policy_groups):
        cell = policy_groups[key]
        root_ler, root_pm, root_delta = [], [], []
        for root in range(int(cfg["roots"])):
            rr = [r for r in cell if r["root"] == root]
            fail(len(rr) == len(REGIMES), f"Missing root/regime cells for {key}/{root}")
            root_ler.append(float(np.mean([x["ler"] for x in rr])))
            root_pm.append(float(np.mean([x["pymatching_ler"] for x in rr])))
            root_delta.append(float(np.mean([x["paired_difference"] for x in rr])))
        summaries.append({"strategy": key[0], "train_size_per_regime": key[1], "policy": key[2],
            "shots": sum(x["shots"] for x in cell), "pooled_errors": sum(x["errors"] for x in cell),
            "pooled_ler": sum(x["errors"] for x in cell) / sum(x["shots"] for x in cell),
            "root_equal_regime_ler": root_t(root_ler),
            "root_equal_regime_pymatching_ler": root_t(root_pm),
            "root_paired_delta": root_t(root_delta),
            "root_paired_bootstrap_ci95": root_bootstrap(root_delta, boot_idx, float(cfg["analysis"]["bootstrap_confidence"])),
            "roots_won_vs_pm": sum(x < 0 for x in root_delta),
            "roots_lost_vs_pm": sum(x > 0 for x in root_delta),
            "roots_tied_vs_pm": sum(x == 0 for x in root_delta),
            "candidate_only": sum(x["candidate_only"] for x in cell),
            "pymatching_only": sum(x["pymatching_only"] for x in cell),
            "beneficial_corrections": sum(x["beneficial_corrections"] for x in cell),
            "harmful_corrections": sum(x["harmful_corrections"] for x in cell),
            "root_deltas": root_delta})
    expected_summaries = results["summary"]
    fail(len(expected_summaries) == len(summaries) == 9, "Expected nine frozen candidate-policy-size summaries")
    by_key = {(x["strategy"], int(x["train_size_per_regime"]), x["policy"]): x for x in expected_summaries}
    for actual in summaries:
        saved = by_key[(actual["strategy"], actual["train_size_per_regime"], actual["policy"])]
        for f in ("shots", "pooled_errors", "candidate_only", "pymatching_only", "beneficial_corrections", "harmful_corrections"):
            fail(int(saved[f]) == int(actual[f]), f"Aggregate mismatch {f} for {actual['strategy']}/{actual['policy']}/{actual['train_size_per_regime']}")
        fail(close(saved["pooled_ler"], actual["pooled_ler"]), "Aggregate LER mismatch")
        fail(np.allclose(saved["root_deltas"], actual["root_deltas"], rtol=0, atol=1e-12), "Root-level paired deltas mismatch")
        fail(close(saved["root_paired_delta"]["ci95_low"], actual["root_paired_delta"]["ci95_low"]) and
             close(saved["root_paired_delta"]["ci95_high"], actual["root_paired_delta"]["ci95_high"]), "Root t interval mismatch")
        fail(close(saved["root_paired_bootstrap_ci95"]["low"], actual["root_paired_bootstrap_ci95"]["low"]) and
             close(saved["root_paired_bootstrap_ci95"]["high"], actual["root_paired_bootstrap_ci95"]["high"]), "Root bootstrap mismatch")

    production_shots = sum(int(cfg["sampling"][k]) for k in (
        "monitor_per_regime_root", "calibration_per_regime_root", "threshold_selection_per_regime_root",
        "final_development_shots_per_regime_root"))
    production_shots = (production_shots + max(int(x) for x in cfg["sampling"]["train_budgets_per_regime_root"])) * int(cfg["roots"]) * len(REGIMES)
    fail(int(results["unique_production_shots"]) == production_shots == 1665000,
         f"Production shot accounting mismatch: {results['unique_production_shots']} != {production_shots}")
    fail(prediction_archive_count == 30, f"Expected 30 prediction archives, found {prediction_archive_count}")
    fail(sum(redecoded_by_regime.values()) == 225000, "Final sample count/redecode coverage mismatch")
    audit = {"status": "PASS", "completed_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "roots_verified": int(cfg["roots"]), "model_jobs_verified": len(all_jobs),
        "prediction_archives_verified": prediction_archive_count, "paired_metric_rows_recomputed": len(job_rows),
        "final_development_shots": production_shots // 5,
        "final_development_shots_total": 225000,
        "all_saved_pymatching_predictions_independently_redecoded": True,
        "all_model_probabilities_recomputed_from_selected_weights": True,
        "all_logical_predictions_and_paired_metrics_recomputed": True,
        "root_bootstrap_and_t_intervals_recomputed": True,
        "independent_test_access": 0,
        "coverage": "Only new development partitions and the explicitly test-free historical seed inventories in the freeze were read; independent-test seed/sample files were not accessed."}
    output = HERE / "INDEPENDENT_RECOMPUTATION.json"
    output.write_text(json.dumps(audit, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
