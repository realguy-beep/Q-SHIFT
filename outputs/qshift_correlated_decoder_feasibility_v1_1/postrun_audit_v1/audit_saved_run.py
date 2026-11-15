"""Read-only independent audit of the preserved V1.1 evaluation archives.

This module does not import the frozen runner or analyzer. It writes only to a
separate audit directory and refuses output paths inside the original run.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

QS = (0.0, 0.01, 0.02)
ARMS = ("A", "A2", "B", "C")
N_ROOTS = 10
SHOTS_PER_ROOT = 2000
N_BOOT = 20_000
CSV_FIELDS = (
    "q", "root", "shots", "detector_sha256", "A_errors", "A_ler",
    "A2_errors", "A2_ler", "B_errors", "B_ler", "C_errors", "C_ler",
    "B_minus_A", "B_minus_A2", "A_B_prediction_disagreements",
    "A2_B_prediction_disagreements", "B_only_errors_vs_A", "A_only_errors_vs_B",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def root_scores(detectors: np.ndarray, labels: np.ndarray,
                predictions: dict[str, np.ndarray], q: float, root: int) -> dict[str, Any]:
    """Calculate one paired root row from arrays, with no decoder code involved."""
    n = len(labels)
    y = labels[:, 0]
    errors = {arm: predictions[arm][:, 0] != y for arm in ARMS}
    row: dict[str, Any] = {
        "q": float(q), "root": int(root), "shots": int(n),
        "detector_sha256": sha256_bytes(np.ascontiguousarray(detectors).tobytes()),
    }
    for arm in ARMS:
        count = int(np.count_nonzero(errors[arm]))
        row[f"{arm}_errors"] = count
        row[f"{arm}_ler"] = count / n
    row["B_minus_A"] = row["B_ler"] - row["A_ler"]
    row["B_minus_A2"] = row["B_ler"] - row["A2_ler"]
    row["A_B_prediction_disagreements"] = int(np.count_nonzero(predictions["A"] != predictions["B"]))
    row["A2_B_prediction_disagreements"] = int(np.count_nonzero(predictions["A2"] != predictions["B"]))
    row["B_only_errors_vs_A"] = int(np.count_nonzero(errors["B"] & ~errors["A"]))
    row["A_only_errors_vs_B"] = int(np.count_nonzero(errors["A"] & ~errors["B"]))
    return row


def stratified_bootstrap(root_diffs: dict[float, list[float]], seed: int,
                         replicates: int = N_BOOT) -> tuple[float, list[float], dict[str, list[float]]]:
    """Frozen root-stratified paired percentile bootstrap; each q is resampled separately."""
    rng = np.random.default_rng(int(seed))
    arrays = {q: np.asarray(root_diffs[q], dtype=np.float64) for q in QS}
    if any(x.shape != (N_ROOTS,) for x in arrays.values()):
        raise ValueError("each condition must contain exactly ten root-paired differences")
    by_q = {q: np.empty(replicates, dtype=np.float64) for q in QS}
    primary = np.empty(replicates, dtype=np.float64)
    for b in range(replicates):
        for q in QS:
            idx = rng.integers(0, N_ROOTS, size=N_ROOTS)
            by_q[q][b] = arrays[q][idx].mean()
        primary[b] = (by_q[0.01][b] + by_q[0.02][b]) / 2.0
    estimate = float((arrays[0.01].mean() + arrays[0.02].mean()) / 2.0)
    primary_ci = np.quantile(primary, [0.025, 0.975], method="linear").tolist()
    q_ci = {str(q): np.quantile(by_q[q], [0.025, 0.975], method="linear").tolist() for q in QS}
    return estimate, primary_ci, q_ci


def zero_condition_bounds(root_diffs: list[float], seed: int,
                          replicates: int = N_BOOT) -> list[float]:
    x = np.asarray(root_diffs, dtype=np.float64)
    if x.shape != (N_ROOTS,):
        raise ValueError("zero-burst condition must contain exactly ten roots")
    rng = np.random.default_rng(int(seed))
    samples = np.empty(replicates, dtype=np.float64)
    for b in range(replicates):
        samples[b] = x[rng.integers(0, N_ROOTS, size=N_ROOTS)].mean()
    return np.quantile(samples, [0.05, 0.95], method="linear").tolist()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path.name}")
    return value


def _validate_binary(name: str, array: np.ndarray, shape: tuple[int, ...]) -> None:
    if array.shape != shape or array.dtype != np.uint8:
        raise ValueError(f"{name} must have shape {shape} and dtype uint8; got {array.shape}/{array.dtype}")
    if not np.isin(array, (0, 1)).all():
        raise ValueError(f"{name} contains non-binary values")


def _close_enough(left: Any, right: Any) -> bool:
    try:
        return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=1e-14)
    except (TypeError, ValueError):
        return False


def audit(run_dir: Path, output_dir: Path, package_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve(strict=True)
    output_dir = output_dir.resolve()
    if output_dir == run_dir or run_dir in output_dir.parents:
        raise ValueError("audit outputs must be outside the preserved original run directory")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"audit output directory is not empty: {output_dir}")

    status_path = run_dir / "status.json"
    status = _read_json(status_path)
    if status.get("state") != "failed" or status.get("phase") != "independent_saved_array_analysis":
        raise ValueError("original failed-run status does not match the recorded analysis-finalization failure")
    failure = status.get("failure", {})
    if failure.get("type") != "KeyError" or failure.get("message") != "'global_A_qhat'":
        raise ValueError("unexpected finalization failure; do not infer around a different failure")
    if (status.get("shots_started"), status.get("shots_committed"), status.get("completed_roots")) != (60_000, 60_000, 30):
        raise ValueError("persisted allocation counters are not exactly 60,000 shots/30 roots")
    if status.get("sampler_calls_started") is None or len(status["sampler_calls_started"]) != 30:
        raise ValueError("persisted sampler call count is not 30")
    if (run_dir / "analysis.json").exists() or (run_dir / "run_manifest.json").exists():
        raise ValueError("unexpected analysis/final manifest already exists; preserve and investigate")

    identity = _read_json(run_dir / "execution_identity.json")
    if identity.get("evaluation_labels_exposed_to_decoders") is not False:
        raise ValueError("execution identity does not assert the frozen detector-only decoder boundary")
    models = _read_json(run_dir / "models_frozen.json")
    if models.get("model_choice_frozen_before_evaluation") is not True:
        raise ValueError("saved model record does not state that choice preceded evaluation")
    if "A_global_qhat" not in models or "global_A_qhat" in models:
        raise ValueError("the recorded model-key mismatch is not the expected known defect")

    inventory = _read_json(package_dir / "seed_inventory.json")
    seed_map = inventory.get("seeds", {})
    expected_keys = {f"evaluation:q{q:.2f}:root{r:02d}" for q in QS for r in range(N_ROOTS)}
    calls = status["sampler_calls_started"]
    call_map = {call.get("key"): call for call in calls}
    if len(call_map) != 30 or set(call_map) != expected_keys:
        raise ValueError("sampler-call identity set is incomplete or duplicated")
    call_ids = [call.get("sample_id") for call in calls]
    seeds = [int(call["seed"]) for call in calls]
    if len(set(call_ids)) != 30 or len(set(seeds)) != 30:
        raise ValueError("duplicate evaluation sample ID or seed")
    for key, call in call_map.items():
        expected_seed = int(seed_map[key])
        expected_id = hashlib.sha256(f"qshift-v1.1:{key}:{expected_seed}".encode("utf-8")).hexdigest()
        if int(call["seed"]) != expected_seed or call.get("sample_id") != expected_id:
            raise ValueError(f"seed/sample identity mismatch for {key}")
        if call.get("state") != "committed" or int(call.get("shots", -1)) != SHOTS_PER_ROOT:
            raise ValueError(f"call was not committed at the frozen 2,000-shot allocation: {key}")

    registered = {item["path"]: item for item in status.get("archives", [])}
    if len(registered) != 30:
        raise ValueError("status archive registry is not exactly 30 entries")
    evaluation_dir = run_dir / "evaluation"
    actual_npz = {p.name for p in evaluation_dir.iterdir() if p.is_file() and p.suffix == ".npz"}
    expected_names = {f"eval_q{qi}_r{ri:02d}.npz" for qi in range(3) for ri in range(N_ROOTS)}
    if actual_npz != expected_names:
        raise ValueError("evaluation archive filenames are missing or unregistered")

    rows: list[dict[str, Any]] = []
    hashes: dict[str, dict[str, Any]] = {}
    total_errors = {arm: 0 for arm in ARMS}
    paired_diffs = {q: [] for q in QS}
    condition_errors = {q: {arm: 0 for arm in ARMS} for q in QS}
    condition_disagreements = {q: {"A_B": 0, "A2_B": 0, "B_only_vs_A": 0, "A_only_vs_B": 0} for q in QS}

    for qi, q in enumerate(QS):
        for ri in range(N_ROOTS):
            key = f"evaluation:q{q:.2f}:root{ri:02d}"
            name = f"eval_q{qi}_r{ri:02d}.npz"
            path = evaluation_dir / name
            rel = f"evaluation/{name}"
            call = call_map[key]
            digest = sha256_file(path)
            byte_count = path.stat().st_size
            record = registered.get(rel)
            if not record or call.get("archive") != rel:
                raise ValueError(f"archive mapping mismatch for {name}")
            if digest != call.get("archive_sha256") or byte_count != call.get("archive_bytes"):
                raise ValueError(f"archive hash/byte mismatch against call journal for {name}")
            if digest != record.get("sha256") or byte_count != record.get("bytes") or record.get("shots") != SHOTS_PER_ROOT:
                raise ValueError(f"archive hash/byte/shot mismatch against status registry for {name}")

            with np.load(path, allow_pickle=False) as archive:
                required = {"detectors", "observables", *(f"pred_{arm}" for arm in ARMS)}
                if set(archive.files) != required:
                    raise ValueError(f"unexpected NPZ member set for {name}")
                arrays = {key: np.asarray(archive[key]) for key in required}
            detectors = arrays["detectors"]
            labels = arrays["observables"]
            _validate_binary("detectors", detectors, (SHOTS_PER_ROOT, 40))
            _validate_binary("observables", labels, (SHOTS_PER_ROOT, 1))
            predictions = {arm: arrays[f"pred_{arm}"] for arm in ARMS}
            for arm, pred in predictions.items():
                _validate_binary(f"prediction {arm}", pred, (SHOTS_PER_ROOT, 1))
            row = root_scores(detectors, labels, predictions, q, ri)
            rows.append(row)
            paired_diffs[q].append(float(row["B_minus_A"]))
            for arm in ARMS:
                total_errors[arm] += row[f"{arm}_errors"]
                condition_errors[q][arm] += row[f"{arm}_errors"]
            for key_metric in condition_disagreements[q]:
                source = {"A_B": "A_B_prediction_disagreements", "A2_B": "A2_B_prediction_disagreements",
                          "B_only_vs_A": "B_only_errors_vs_A", "A_only_vs_B": "A_only_errors_vs_B"}[key_metric]
                condition_disagreements[q][key_metric] += row[source]
            hashes[name] = {"sha256": digest, "bytes": byte_count, "samples": SHOTS_PER_ROOT}

    original_csv = run_dir / "paired_results.csv"
    csv_rows = list(csv.DictReader(original_csv.open("r", newline="", encoding="utf-8")))
    if len(csv_rows) != 30 or tuple(csv_rows[0].keys()) != CSV_FIELDS:
        raise ValueError("pre-failure paired_results.csv has unexpected shape or fields")
    csv_map = {(float(r["q"]), int(r["root"])): r for r in csv_rows}
    if len(csv_map) != 30:
        raise ValueError("pre-failure paired_results.csv contains duplicate root keys")
    csv_checks = 0
    for row in rows:
        old = csv_map[(row["q"], row["root"])]
        for field in CSV_FIELDS:
            value = row[field]
            if isinstance(value, float):
                ok = _close_enough(value, old[field])
            else:
                ok = str(value) == old[field]
            if not ok:
                raise ValueError(f"independent recomputation differs from persisted CSV at {field}, q={row['q']}, root={row['root']}")
            csv_checks += 1

    seed_primary = int(seed_map["statistics:primary-bootstrap"])
    seed_zero = int(seed_map["statistics:zero-bootstrap"])
    primary_est, primary_ci, condition_ci = stratified_bootstrap(paired_diffs, seed_primary)
    zero_bounds = zero_condition_bounds(paired_diffs[0.0], seed_zero)
    rates = {arm: total_errors[arm] / 60_000 for arm in ARMS}
    nonzero = {arm: (condition_errors[0.01][arm] / 20_000 + condition_errors[0.02][arm] / 20_000) / 2 for arm in ARMS}
    a_nz_errors = condition_errors[0.01]["A"] + condition_errors[0.02]["A"]
    b_better_both = all(condition_errors[q]["B"] < condition_errors[q]["A"] for q in (0.01, 0.02))
    complete_criteria = (
        a_nz_errors >= 100 and primary_ci[1] < 0 and b_better_both and zero_bounds[1] < 0.0005
    )
    if primary_ci[0] >= 0 or zero_bounds[0] > 0.0005:
        if complete_criteria:
            raise AssertionError("contradictory frozen criteria")
        criteria_if_complete = "NO_GO"
    elif complete_criteria:
        criteria_if_complete = "GO_DEVELOPMENT_ONLY"
    else:
        criteria_if_complete = "INCONCLUSIVE"

    calibration = _read_json(run_dir / "calibration_diagnostics.json")
    global_qhat = float(models["A_global_qhat"])
    output = {
        "schema": "qshift-correlated-decoder-v1.1-postrun-independent-audit-v1",
        "audit_scope": "read-only verification and independent recomputation from committed saved arrays and predictions",
        "original_run_state": status["state"],
        "original_run_phase": status["phase"],
        "original_run_failure": failure,
        "run_completion_status": "INCOMPLETE_ANALYSIS_FINALIZATION_FAILED",
        "sampler_calls": len(calls), "committed_roots": len(rows), "unique_shots": 60_000,
        "archive_hashes_and_bytes": hashes,
        "pre_failure_csv_sha256": sha256_file(original_csv),
        "per_root_csv_reconciliation": {"matched_fields": csv_checks, "expected_fields": 30 * len(CSV_FIELDS), "status": "PASS"},
        "per_root_results": rows,
        "arm_totals": {arm: {"errors": total_errors[arm], "shots": 60_000, "ler": rates[arm]} for arm in ARMS},
        "condition_results": {
            str(q): {
                "arms": {arm: {"errors": condition_errors[q][arm], "shots": 20_000,
                                "ler": condition_errors[q][arm] / 20_000} for arm in ARMS},
                "paired_B_minus_A_mean_root_ler": float(np.mean(paired_diffs[q])),
                "paired_disagreements_and_harm": condition_disagreements[q],
                "B_minus_A_root_bootstrap_95_interval_at_all_q": condition_ci[str(q)],
            } for q in QS
        },
        "primary": {
            "estimand": "equal-weight mean of q=0.01 and q=0.02 root-paired LER(B)-LER(A)",
            "estimate": primary_est, "two_sided_95_percentile_interval": primary_ci,
            "bootstrap_replicates": N_BOOT, "bootstrap_rng_seed": seed_primary,
            "root_stratified_pairing_preserved": True, "quantile_method": "linear",
        },
        "zero_burst_safety": {
            "estimate": float(np.mean(paired_diffs[0.0])), "bootstrap_5th_95th_percentiles": zero_bounds,
            "bootstrap_rng_seed": seed_zero, "harm_tolerance": 0.0005,
        },
        "equal_weight_nonzero_ler": nonzero,
        "relative_reduction_B_vs_A_descriptive": (nonzero["A"] - nonzero["B"]) / nonzero["A"] if nonzero["A"] else None,
        "A_nonzero_error_count": int(a_nz_errors), "B_lower_point_ler_both_nonzero_conditions": bool(b_better_both),
        "calibration_estimation_summary_from_saved_diagnostics": calibration["estimation_summary"],
        "global_A_qhat": global_qhat,
        "frozen_decision_criteria_if_complete": criteria_if_complete,
        "protocol_decision": "INCONCLUSIVE",
        "decision_reason": "The frozen run status is failed during independent analysis; incomplete evidence is explicitly INCONCLUSIVE even though saved arrays support recomputation.",
        "limitations": [
            "This independent audit recovers descriptive and prespecified development statistics from saved outputs; it does not repair status.json or create the missing frozen analysis/run manifest.",
            "Ten roots per condition and one synthetic noise mechanism are exploratory, not independent confirmation.",
            "The checkpointed labels and predictions are trusted only after archive checksum, schema, identity, and paired_results.csv reconciliation; decoder execution itself is not repeated.",
            "The original analyzer's KeyError was caused by model metadata key naming: writer stores A_global_qhat; analyzer requests global_A_qhat.",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=False) if not output_dir.exists() else None
    (output_dir / "independent_audit.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (output_dir / "per_root_results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        "schema": "qshift-v1.1-postrun-audit-input-manifest-v1",
        "inputs": {name: {"sha256": sha256_file(path), "bytes": path.stat().st_size}
                   for name, path in {
                       "status.json": status_path,
                       "execution_identity.json": run_dir / "execution_identity.json",
                       "models_frozen.json": run_dir / "models_frozen.json",
                       "calibration_diagnostics.json": run_dir / "calibration_diagnostics.json",
                       "training_summary.json": run_dir / "training_summary.json",
                       "paired_results.csv": original_csv,
                       "seed_inventory.json": package_dir / "seed_inventory.json",
                       "config.json": package_dir / "config.json",
                       "EXPERIMENT_PROTOCOL.md": package_dir / "EXPERIMENT_PROTOCOL.md",
                       "PRETEST_FREEZE.json": package_dir / "PRETEST_FREEZE.json",
                   }.items()},
        "audit_outputs": {},
        "original_run_modified": False,
    }
    for name in ("independent_audit.json", "per_root_results.csv"):
        path = output_dir / name
        manifest["audit_outputs"][name] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    (output_dir / "evidence_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--package-dir", required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.run_dir, args.output_dir, args.package_dir)
    print(json.dumps({key: result[key] for key in (
        "run_completion_status", "sampler_calls", "committed_roots", "unique_shots",
        "primary", "zero_burst_safety", "arm_totals", "protocol_decision",
    )}, indent=2))


if __name__ == "__main__":
    main()
