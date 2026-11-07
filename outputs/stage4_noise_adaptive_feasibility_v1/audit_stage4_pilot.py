"""Independent read-only rescoring of the saved Stage 4 feasibility pilot."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

import numpy as np

from outputs.stage4_noise_adaptive_feasibility_v1.freeze_stage4 import HERE, REPO, verify as verify_freeze
from outputs.stage4_noise_adaptive_feasibility_v1.prototype import (
    DetectorProfileEstimator,
    build_decoder,
    decode_prediction,
    logical_error_mask,
)

RAW = HERE / "run_v1"
RESULTS = HERE / "STAGE4_FEASIBILITY_PILOT_RESULTS.json"
INVENTORY = HERE / "seed_inventory.json"
PUBLIC_AUDIT = HERE / "STAGE4_PILOT_INDEPENDENT_AUDIT.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def paired_counts(pred: np.ndarray, base: np.ndarray, obs: np.ndarray) -> dict:
    e = logical_error_mask(pred, obs)
    b = logical_error_mask(base, obs)
    return {
        "errors": int(e.sum()),
        "disagreements": int(np.count_nonzero(pred != base)),
        "candidate_only": int(np.count_nonzero(e & ~b)),
        "fixed_only": int(np.count_nonzero(~e & b)),
    }


def t_interval(values: list[float]) -> list[float] | None:
    if len(values) < 2:
        return None
    mean = statistics.mean(values)
    half = {1: 12.7062, 2: 4.3027, 3: 3.1824}.get(len(values) - 1)
    if half is None:
        return None
    half *= statistics.stdev(values) / math.sqrt(len(values))
    return [mean - half, mean + half]


def run() -> dict:
    freeze_status = verify_freeze()
    result = json.loads(RESULTS.read_text(encoding="utf-8"))
    inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    audit_seed = json.loads((HERE / "seed_audit.json").read_text(encoding="utf-8"))
    if result["status"] != "FEASIBILITY_PILOT_COMPLETE" or result["unique_shots"] != 48000:
        raise RuntimeError("result record does not contain the exact frozen pilot allocation")
    if inv["unique_seed_count"] != 19 or not audit_seed["candidate_seeds_unique"] or audit_seed["historical_collisions"]:
        raise RuntimeError("pilot seed audit invalid")
    if result["independent_test_accessed"] or result["independent_test_enumerated"]:
        raise RuntimeError("independent-test boundary violation recorded")

    seed_map = inv["streams"]
    def allocated_seed(kind: str, p: float, *, replicate: int | None = None, root: int | None = None) -> int:
        found = [int(s["seed"]) for s in seed_map if s["kind"] == kind and
                 float(s.get("probability", -1)) == p and
                 (replicate is None or s.get("replicate") == replicate) and
                 (root is None or s.get("root") == root)]
        if len(found) != 1:
            raise RuntimeError(f"seed mapping invalid for {kind}, p={p}, replicate={replicate}, root={root}")
        return found[0]

    profile_archive = load_npz(RAW / "profile_calibration.npz")
    profile_batches = []
    expected_profile_keys = []
    profile_rows = []
    for p in (0.002, 0.010, 0.018):
        for rep in range(2):
            key = f"profile_p{p:.3f}_rep{rep}"
            expected_profile_keys.append(key)
            d = profile_archive[key]
            if d.shape != (2000, 40) or not np.isin(d, (0, 1)).all():
                raise RuntimeError(f"invalid saved profile batch {key}: {d.shape}")
            raw_path = RAW / "samples" / f"{key}.npz"
            raw = load_npz(raw_path)
            if not np.array_equal(raw["detectors"], d):
                raise RuntimeError(f"profile archive differs from per-stream file {key}")
            expected_seed = allocated_seed("profile_calibration_detectors", p, replicate=rep)
            if not np.array_equal(d, raw["detectors"]):
                raise RuntimeError(f"profile stream values are not identical to archived raw evidence: {key}")
            expected_hash = hashlib.sha256(d.tobytes()).hexdigest()
            if result["integrity"]["sample_array_hashes"].get(key) != expected_hash:
                raise RuntimeError(f"profile sample-array hash mismatch: {key}")
            profile_batches.append((p, d))
            profile_rows.append({"name": key, "probability": p, "shots": int(len(d)),
                                 "seed": expected_seed, "sha256": sha256(raw_path)})
    if set(profile_archive) != set(expected_profile_keys):
        raise RuntimeError("profile archive contains missing or unexpected streams")
    estimator = DetectorProfileEstimator.fit(profile_batches)

    fixed_cache = {0.0: build_decoder(0.0)[2]}
    mismatch_grid = [0.0, 0.002, 0.006, 0.010, 0.014, 0.018]
    for p in mismatch_grid:
        if p not in fixed_cache:
            fixed_cache[p] = build_decoder(p)[2]
    bootstrap_rng = np.random.default_rng(4100000019)
    root_records = []
    verified_files = list(profile_rows)
    for p in (0.006, 0.014):
        for root in range(3):
            name = f"eval_p{p:.3f}_root{root}"
            path = RAW / "samples" / f"{name}.npz"
            arrays = load_npz(path)
            required = {"calibration_detectors", "evaluation_detectors", "observable",
                        "prediction_fixed", "prediction_estimated", "prediction_oracle"}
            if not required.issubset(arrays):
                raise RuntimeError(f"missing arrays in {path.name}: {required - set(arrays)}")
            cal = arrays["calibration_detectors"]
            d = arrays["evaluation_detectors"]
            obs = arrays["observable"].reshape(-1)
            if cal.shape != (2000, 40) or d.shape != (4000, 40) or obs.shape != (4000,):
                raise RuntimeError(f"invalid paired/calibration dimensions in {path.name}")
            if not all(np.isin(x, (0, 1)).all() for x in (cal, d, obs)):
                raise RuntimeError(f"nonbinary input arrays in {path.name}")
            old = next(x for x in result["per_root"] if x["true_probability_for_analysis_only"] == p and x["root"] == root)
            expected_cal_seed = allocated_seed("unseen_parameter_calibration_detectors", p, root=root)
            expected_eval_seed = allocated_seed("unseen_parameter_paired_evaluation", p, root=root)
            if old["calibration_seed"] != expected_cal_seed or old["evaluation_seed"] != expected_eval_seed:
                raise RuntimeError(f"seed-to-root mapping mismatch in {path.name}")
            if old["evidence_sha256"] != sha256(path):
                raise RuntimeError(f"result archive hash mismatch in {path.name}")
            expected_hash = hashlib.sha256(d.tobytes() + obs.tobytes()).hexdigest()
            if result["integrity"]["sample_array_hashes"].get(name) != expected_hash:
                raise RuntimeError(f"evaluation sample-array hash mismatch in {path.name}")
            p_hat = estimator.estimate(cal)
            lo, hi = estimator.bootstrap_interval(cal, rng=bootstrap_rng, replicates=500)
            estimated_decoder = build_decoder(p_hat)[2]
            pred_fixed = decode_prediction(fixed_cache[0.0], d)
            pred_est = decode_prediction(estimated_decoder, d)
            pred_oracle = decode_prediction(fixed_cache[p], d)
            if not np.array_equal(pred_fixed, arrays["prediction_fixed"]):
                raise RuntimeError(f"fixed prediction mismatch in {path.name}")
            if not np.array_equal(pred_est, arrays["prediction_estimated"]):
                raise RuntimeError(f"estimated prediction mismatch in {path.name}")
            if not np.array_equal(pred_oracle, arrays["prediction_oracle"]):
                raise RuntimeError(f"oracle prediction mismatch in {path.name}")
            grid_counts = {}
            for q in mismatch_grid:
                key = f"prediction_p{q:.3f}"
                if key not in arrays:
                    raise RuntimeError(f"mismatch prediction missing in {path.name}: {key}")
                pred = decode_prediction(fixed_cache[q], d)
                if not np.array_equal(pred, arrays[key]):
                    raise RuntimeError(f"mismatch-grid prediction mismatch in {path.name}: p={q}")
                grid_counts[str(q)] = int(logical_error_mask(pred, obs).sum())
            fixed_errors = int(logical_error_mask(pred_fixed, obs).sum())
            estimated = paired_counts(pred_est, pred_fixed, obs)
            oracle = paired_counts(pred_oracle, pred_fixed, obs)
            entry = {
                "probability_analysis_only": p,
                "root": root,
                "estimated_probability_recomputed": p_hat,
                "bootstrap_interval_recomputed": [lo, hi],
                "fixed_errors_recomputed": fixed_errors,
                "estimated_pair_counts_recomputed": estimated,
                "oracle_pair_counts_recomputed": oracle,
                "mismatch_grid_errors_recomputed": grid_counts,
                "evaluation_shots": int(len(obs)),
                "archive_sha256": sha256(path),
                "calibration_observable_accessed": False,
                "same_samples_all_arms": True,
            }
            for actual, expected, key in [
                (p_hat, old["estimated_probability"], "estimated p"),
                ([lo, hi], old["bootstrap_95_interval"], "bootstrap CI"),
                (fixed_errors, old["fixed_nominal_errors"], "fixed errors"),
                (estimated["errors"], old["estimated_model_errors"], "estimated errors"),
                (estimated["candidate_only"], old["estimated_candidate_only_failures"], "candidate-only"),
                (estimated["fixed_only"], old["estimated_fixed_only_failures"], "fixed-only"),
                (estimated["disagreements"], old["estimated_disagreements_with_fixed"], "disagreements"),
                (oracle["errors"], old["oracle_errors"], "oracle errors"),
            ]:
                if isinstance(actual, list):
                    equal = np.allclose(actual, expected, atol=1e-14, rtol=0)
                else:
                    equal = actual == expected
                if not equal:
                    raise RuntimeError(f"runner result mismatch ({key}) in {path.name}: {actual} != {expected}")
            root_records.append(entry)
            verified_files.append({"name": name, "shots": len(obs), "sha256": sha256(path)})

    by_p = {}
    for p in (0.006, 0.014):
        roots = [r for r in root_records if r["probability_analysis_only"] == p]
        shots = sum(r["evaluation_shots"] for r in roots)
        fixed_errs = sum(r["fixed_errors_recomputed"] for r in roots)
        est_errs = sum(r["estimated_pair_counts_recomputed"]["errors"] for r in roots)
        oracle_errs = sum(r["oracle_pair_counts_recomputed"]["errors"] for r in roots)
        diffs = [(r["estimated_pair_counts_recomputed"]["errors"] - r["fixed_errors_recomputed"]) / r["evaluation_shots"] for r in roots]
        by_p[str(p)] = {
            "roots": len(roots), "shots": shots,
            "fixed_errors": fixed_errs, "fixed_ler": fixed_errs / shots,
            "estimated_errors": est_errs, "estimated_ler": est_errs / shots,
            "estimated_minus_fixed_ler": (est_errs - fixed_errs) / shots,
            "estimated_candidate_only": sum(r["estimated_pair_counts_recomputed"]["candidate_only"] for r in roots),
            "estimated_fixed_only": sum(r["estimated_pair_counts_recomputed"]["fixed_only"] for r in roots),
            "estimated_prediction_disagreements": sum(r["estimated_pair_counts_recomputed"]["disagreements"] for r in roots),
            "estimated_paired_root_differences": diffs,
            "estimated_root_t_interval_descriptive": t_interval(diffs),
            "oracle_errors": oracle_errs, "oracle_ler": oracle_errs / shots,
            "mean_estimate": statistics.mean(r["estimated_probability_recomputed"] for r in roots),
            "mean_absolute_p_error": statistics.mean(abs(r["estimated_probability_recomputed"] - p) for r in roots),
            "mean_signed_p_error": statistics.mean(r["estimated_probability_recomputed"] - p for r in roots),
            "bootstrap_interval_contains_true_p": sum(r["bootstrap_interval_recomputed"][0] <= p <= r["bootstrap_interval_recomputed"][1] for r in roots),
        }
    mismatch = {}
    for q in [0.0, 0.002, 0.006, 0.010, 0.014, 0.018]:
        mismatch[str(q)] = {}
        for p in (0.006, 0.014):
            roots = [r for r in root_records if r["probability_analysis_only"] == p]
            e = sum(r["mismatch_grid_errors_recomputed"][str(q)] for r in roots)
            n = sum(r["evaluation_shots"] for r in roots)
            mismatch[str(q)][str(p)] = {"errors": e, "shots": n, "ler": e / n}

    n_profile = sum(x["shots"] for x in profile_rows)
    n_cal = sum(r["evaluation_shots"] // 2 for r in root_records)
    n_eval = sum(r["evaluation_shots"] for r in root_records)
    if n_profile + n_cal + n_eval != 48000:
        raise RuntimeError("unique shot accounting does not sum to 48,000")
    audit = {
        "status": "PASS",
        "audit_method": "separate script; rebuild profile estimator and all PyMatching DEMs; re-decode saved arrays and recompute XOR residuals",
        "verified_freeze": freeze_status,
        "verified_unique_shots": n_profile + n_cal + n_eval,
        "verified_profile_calibration_shots": n_profile,
        "verified_unseen_calibration_shots": n_cal,
        "verified_paired_evaluation_shots": n_eval,
        "verified_roots": len(root_records),
        "raw_evidence_files_verified": verified_files,
        "per_root_recomputation": root_records,
        "aggregate_recomputation": by_p,
        "mismatch_sensitivity": mismatch,
        "same_paired_evaluation_samples_across_arms": True,
        "calibration_estimator_inputs_detector_only": True,
        "observable_labels_used_only_for_scoring": True,
        "independent_test_accessed": False,
        "independent_test_enumerated": False,
        "limitations": ["Pilot results have three roots per unseen parameter and are feasibility-only.",
                        "Independent scorer was written after the frozen pilot samples existed; it implements the already-frozen XOR/paired-count definitions and did not tune any policy.",
                        "Calibration bootstrap interval conditions on the estimated template profile and omits template-generation uncertainty."],
    }
    PUBLIC_AUDIT.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    with (HERE / "STAGE4_PARAMETER_ESTIMATES.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["true_probability_analysis_only", "root", "estimated_probability", "absolute_error", "signed_error", "bootstrap_low", "bootstrap_high", "interval_contains_true"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in root_records:
            p = r["probability_analysis_only"]
            lo, hi = r["bootstrap_interval_recomputed"]
            phat = r["estimated_probability_recomputed"]
            w.writerow({"true_probability_analysis_only": p, "root": r["root"], "estimated_probability": phat,
                        "absolute_error": abs(phat-p), "signed_error": phat-p,
                        "bootstrap_low": lo, "bootstrap_high": hi, "interval_contains_true": lo <= p <= hi})
    with (HERE / "STAGE4_MISMATCH_SENSITIVITY.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["assumed_burst_probability", "true_probability_analysis_only", "errors", "shots", "ler"]); w.writeheader()
        for q, strata in mismatch.items():
            for p, cell in strata.items():
                w.writerow({"assumed_burst_probability": q, "true_probability_analysis_only": p, **cell})
    write_findings(by_p, mismatch, audit)
    write_manifest()
    print(json.dumps({"status": audit["status"], "shots": audit["verified_unique_shots"],
                      "by_probability": by_p, "mismatch_sensitivity": mismatch}, indent=2))
    return audit


def write_findings(by_p: dict, mismatch: dict, audit: dict) -> None:
    lines = ["# Stage 4 Feasibility Pilot Findings", "",
        "**Scope:** 48,000-shot development-only detector-identifiability and decoder-rebuild pilot. This is not the full Stage 4 study and not confirmatory evidence.", "",
        "## Audit", "",
        f"Independent saved-array audit: **{audit['status']}**; all {audit['verified_unique_shots']:,} shots, six roots, estimator values, decoder predictions, and paired residual counts were recomputed. The independent test was not enumerated or accessed.", "",
        "## Detector-only burst-probability estimation", "",
        "Estimator templates used p=0.002, 0.010, 0.018. Evaluation probabilities 0.006 and 0.014 were not template knots and used independent calibration/evaluation seeds. Per-root calibration-batch bootstrap intervals condition on the fitted template profile and are diagnostic only.", "",
        "| Generating p (analysis only) | Roots | Calibration shots | Paired evaluation shots | Mean p-hat | MAE | Bias | 95% calibration intervals covering p |", "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for p, r in by_p.items():
        lines.append(f"| {p} | {r['roots']} | 6,000 | {r['shots']:,} | {r['mean_estimate']:.5f} | {r['mean_absolute_p_error']:.5f} | {r['mean_signed_p_error']:+.5f} | {r['bootstrap_interval_contains_true_p']}/3 |")
    lines += ["", "## Paired decoder feasibility (descriptive)", "",
        "The estimator-assisted arm and fixed nominal PyMatching decoded identical held-out arrays within each root. True p was used only to build the privileged reference and for offline error scoring.", "",
        "| True p | Decoder | Errors / shots | LER | Assisted-minus-fixed LER | Candidate-only / fixed-only | Prediction disagreements | Root paired differences | Descriptive root t interval |", "|---:|---|---:|---:|---:|---:|---:|---|---|"]
    for p, r in by_p.items():
        lines.append(f"| {p} | Fixed nominal | {r['fixed_errors']:,}/{r['shots']:,} | {r['fixed_ler']:.6f} | — | — | — | — | — |")
        lines.append(f"| {p} | Detector-estimated model | {r['estimated_errors']:,}/{r['shots']:,} | {r['estimated_ler']:.6f} | {r['estimated_minus_fixed_ler']:+.6f} | {r['estimated_candidate_only']}/{r['estimated_fixed_only']} | {r['estimated_prediction_disagreements']} | {r['estimated_paired_root_differences']} | {r['estimated_root_t_interval_descriptive']} |")
        lines.append(f"| {p} | Privileged true-p model | {r['oracle_errors']:,}/{r['shots']:,} | {r['oracle_ler']:.6f} | diagnostic only | see audit JSON | — | — | — |")
    lines += ["", "These rates suggest that the detector profiles contain information about the held-out burst probability and that rebuilding matching at the estimate can change useful corrections. All six calibration bootstrap intervals cover the corresponding true p, but the intervals for the two p strata overlap; with only three roots per stratum this is suggestive, not a reliable separation test. The root-level LER intervals are also descriptive and unstable with df=2. The counts are a feasibility signal, not evidence of statistical superiority or generalization beyond the simulator. The true-p matcher is not a guaranteed performance lower bound: the hindsight mismatch grid at assumed p=0.010 had 58 errors versus 62 for true p=0.006, and assumed p=0.018 had 69 versus 72 for true p=0.014. This may reflect finite-distance/DEM approximation effects and shot variability; it shows that recovering physical p and minimizing matching LER are distinct objectives. The mismatch grid is not a deployable selection policy.", "",
        "## Parameter-mismatch sensitivity", "",
        "The following grid is an offline diagnostic; it uses assumed p values selected by the analyst, not an inference-time rule. Lower LER is not a calibrated estimate of a general optimum.", "",
        "| Assumed p in matcher | LER at true p=0.006 | LER at true p=0.014 |", "|---:|---:|---:|"]
    for q, strata in mismatch.items():
        lines.append(f"| {q} | {strata['0.006']['ler']:.6f} ({strata['0.006']['errors']}/{strata['0.006']['shots']}) | {strata['0.014']['ler']:.6f} ({strata['0.014']['errors']}/{strata['0.014']['shots']}) |")
    lines += ["", "## Compute and limits", "",
        f"The frozen pilot completed in {json.loads(RESULTS.read_text(encoding='utf-8'))['runtime_seconds']['total']:.2f} seconds in the installed CPU Stim/PyMatching environment. DEM records preserve 40 detectors and one observable across p; the five burst edges have error probabilities equal to p and weights `log((1-p)/p)`. Decoder construction is an explicit Stim DEM rebuild followed by PyMatching construction.", "",
        "The proposed Stage 4 CNN estimator was not implemented: for one scalar noise parameter with fixed event geometry, the profile estimator is a more interpretable baseline. Reconsider a CNN only if a larger development study identifies a decoder-relevant deficiency in the scalar estimator.", "",
        "## Recommendation", "",
        "**CONDITIONAL GO for designing a bounded Stage 4 development study; NO authorization to execute it yet.** The pilot supports detector-level identifiability over two unseen probabilities and demonstrates valid decoder reconstruction, but small root counts, synthetic-noise assumptions, template uncertainty, and the very small pilot prevent a superiority claim. Before the 180,000-shot proposal, preflight estimation precision and rebuild costs using the frozen rules, and check its proposed seed namespace against any permitted future allocation records without opening sealed test material.", ""]
    (HERE / "STAGE4_FEASIBILITY_PILOT_FINDINGS.md").write_text("\n".join(lines), encoding="utf-8")


def write_manifest() -> None:
    files = {}
    for path in sorted(HERE.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.name == "STAGE4_FEASIBILITY_MANIFEST.json":
            continue
        if "run_v1" in path.parts:
            continue
        rel = path.relative_to(REPO).as_posix()
        files[rel] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    raw_files = {}
    for path in sorted(RAW.rglob("*")):
        if path.is_file():
            rel = path.relative_to(REPO).as_posix()
            raw_files[rel] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    manifest = {
        "status": "EVIDENCE_HASHES_RECORDED",
        "freeze_sha256": sha256(HERE / "STAGE4_FEASIBILITY_FREEZE.json"),
        "independent_audit_sha256": sha256(PUBLIC_AUDIT),
        "public_files": files,
        "local_raw_evidence_files": raw_files,
        "independent_test_accessed": False,
    }
    (HERE / "STAGE4_FEASIBILITY_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    run()

