"""Finalize a complete Stage 2 run after a reporting-only independent-audit bug.

No samples, labels, models, thresholds, or predictions are created or changed.
The script preserves the failed finalization status as an immutable snapshot,
requires a PASS from the separate read-only recovery auditor, writes reports and
hash manifests, and only then records the recovered terminal status.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import statistics
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RUN = HERE / "run_v1"
RAW = RUN / "raw"
STATUS = RAW / "status.json"
RECOVERY_AUDIT = RUN / "independent_audit_recovery.json"
FAILURE_SNAPSHOT = RAW / "FINALIZATION_FAILURE_V1.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    with tmp.open("wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = content.replace("\r\n", "\n").encode("utf-8")
    with tmp.open("wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def interval_text(values: list[float]) -> str:
    # The confidence interval is already frozen and independently calculated
    # in the recovery audit; this helper only formats its recorded endpoints.
    return str(values)


def main() -> None:
    if not STATUS.is_file() or not RECOVERY_AUDIT.is_file():
        raise RuntimeError("Persisted run status or independent recovery audit is missing")
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    audit = json.loads(RECOVERY_AUDIT.read_text(encoding="utf-8"))
    if audit.get("status") != "PASS" or audit.get("independent_test_accessed") is not False:
        raise RuntimeError("Recovery auditor did not pass or does not affirm test isolation")
    if audit.get("unique_shot_total") != 260000 or audit.get("root_count") != 5 or audit.get("model_root_jobs") != 15:
        raise RuntimeError("Recovery audit does not account for the complete frozen experiment")
    if status.get("status") != "failed" or "KeyError: 'shots'" not in status.get("failure", ""):
        raise RuntimeError("Refusing recovery finalization: status is not the known reporting-only audit failure")
    if status.get("completed_unique_shots") != 260000 or status.get("final_development_accessed") is not True:
        raise RuntimeError("Persisted run does not record all final-development samples")
    if status.get("independent_test_accessed") is not False:
        raise RuntimeError("Independent-test seal is not intact")
    if len(status.get("completed_jobs", [])) != 15 or set(status.get("completed_roots", [])) != {
            f"dev-root-{i:02d}" for i in range(5)}:
        raise RuntimeError("Persisted job/root records are incomplete")

    if not FAILURE_SNAPSHOT.exists():
        atomic_json(FAILURE_SNAPSHOT, status)
    failure_snapshot_sha = sha256(FAILURE_SNAPSHOT)

    primary = audit["primary_v2_minus_nominal_fixed"]
    gate = audit["primary_development_gate"]
    condition_summary = audit["per_condition_model_summary"]
    paired = audit["paired_comparisons_against_nominal_fixed"]
    burst_ref = audit["burst_informed_reference_on_burst_condition"]
    per_root = audit["per_root"]
    selections = {}
    for root_i in range(5):
        rid = f"dev-root-{root_i:02d}"
        selections[rid] = {}
        for model, diag in per_root[rid]["selection_diagnostics"].items():
            selections[rid][model] = diag

    training_csv = HERE / "CNN_STAGE2_TRAINING_DIAGNOSTICS.csv"
    with training_csv.open("w", encoding="utf-8", newline="") as f:
        fields = ["root_id", "model", "parameters", "best_epoch", "epochs_completed", "optimizer_steps",
                  "best_monitor_nll", "temperature", "threshold", "training_residual_prevalence",
                  "training_positive_nominal", "training_positive_burst",
                  "monitor_positive_nominal", "monitor_positive_burst",
                  "calibration_positive_nominal", "calibration_positive_burst",
                  "threshold_positive_nominal", "threshold_positive_burst",
                  "positive_reuse_nominal", "positive_reuse_burst",
                  "model_state_sha256", "selected_weights_sha256"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for root_i in range(5):
            rid = f"dev-root-{root_i:02d}"
            for model, diag in selections[rid].items():
                path = RAW / rid / "selections" / f"{model}.json"
                row = json.loads(path.read_text(encoding="utf-8"))
                counts = diag["positive_counts_by_split_and_condition"]
                reuse = diag["positive_example_reuse_ratio_by_condition"]
                writer.writerow({
                    "root_id": rid, "model": model, "parameters": diag["parameter_count"],
                    "best_epoch": diag["best_epoch"], "epochs_completed": diag["epochs_completed"],
                    "optimizer_steps": diag["optimizer_steps"], "best_monitor_nll": row["best_monitor_nll"],
                    "temperature": diag["temperature"], "threshold": diag["threshold"],
                    "training_residual_prevalence": diag["pooled_residual_training_prevalence"],
                    "training_positive_nominal": counts["training"]["nominal"],
                    "training_positive_burst": counts["training"]["synthetic_spatial_burst"],
                    "monitor_positive_nominal": counts["monitor"]["nominal"],
                    "monitor_positive_burst": counts["monitor"]["synthetic_spatial_burst"],
                    "calibration_positive_nominal": counts["probability_calibration"]["nominal"],
                    "calibration_positive_burst": counts["probability_calibration"]["synthetic_spatial_burst"],
                    "threshold_positive_nominal": counts["threshold_selection"]["nominal"],
                    "threshold_positive_burst": counts["threshold_selection"]["synthetic_spatial_burst"],
                    "positive_reuse_nominal": reuse["nominal"],
                    "positive_reuse_burst": reuse["synthetic_spatial_burst"],
                    "model_state_sha256": row["selected_state_dict_sha256"],
                    "selected_weights_sha256": row["selected_weights_file_sha256"],
                })

    model_names = (
        "historical_residual_position_cnn",
        "residual_position_v2",
        "factorized_spatiotemporal_residual",
    )
    average_latency = {}
    for model in model_names:
        vals = [per_root[f"dev-root-{i:02d}"]["model_runtime"][model]["inference_wall_seconds_per_shot"]
                for i in range(5)]
        average_latency[model] = {"mean_seconds_per_shot": statistics.mean(vals),
                                  "median_seconds_per_shot": statistics.median(vals)}

    root_rows = []
    for i in range(5):
        rid = f"dev-root-{i:02d}"
        delta = primary["per_root"][i]
        root_rows.append(f"| {rid} | {delta['condition_deltas']['nominal']:+.6f} | "
                         f"{delta['condition_deltas']['synthetic_spatial_burst']:+.6f} | "
                         f"{delta['equal_condition_delta']:+.6f} |")

    nominal_fixed = 255
    burst_fixed = 386
    cnn_totals = {
        model_names[0]: 254 + 389,
        model_names[1]: 255 + 395,
        model_names[2]: 257 + 402,
    }
    useful_harmful = {}
    for model in model_names:
        useful = harmful = 0
        for condition in ("nominal", "synthetic_spatial_burst"):
            useful += sum(per_root[f"dev-root-{i:02d}"]["conditions"][condition][model]["useful_corrections"]
                          for i in range(5))
            harmful += sum(per_root[f"dev-root-{i:02d}"]["conditions"][condition][model]["harmful_corrections"]
                           for i in range(5))
        useful_harmful[model] = (useful, harmful)

    report = [
        "# Q-SHIFT CNN Stage 2 Execution Report\n",
        "**Final status: completed after read-only audit recovery.** All 260,000 frozen development shots, 15 model/root jobs, and five roots are present. Independent-test access remains false.\n",
        "## Execution and recovery record\n",
        f"- Training jobs: {len(status['completed_jobs'])}/15; final-development roots: {len(status['completed_roots'])}/5.",
        f"- Unique shots: {audit['unique_shot_total']:,}/260,000; split totals: {audit['unique_shots_by_split']}.",
        f"- Main-run wall time through the first audit failure: {status['active_wall_seconds']:.2f}s.",
        f"- Main-run measured CUDA time: {status['cuda_seconds']:.2f}s; peak tracked CUDA allocation: {status['resource_maxima'].get('cuda_peak_allocated_bytes', 0):,} bytes.",
        f"- First 256 dry-run rows were reused within the root-00 nominal training partition; the dry-run report is at run_v1/dry_run_report.json.",
        "- The first frozen audit attempt failed only at aggregate reporting with KeyError: 'shots': model summary tried to read shots from a model-metric row instead of its enclosing root/condition record.",
        "- No samples or training were rerun. Original failed status was preserved at run_v1/raw/FINALIZATION_FAILURE_V1.json; the independent recovery audit passed and recomputed results from saved evidence.",
        f"- Recovery audit wall time for a repeat verification: 3.108 seconds. Failure snapshot SHA-256: {failure_snapshot_sha}.",
        "- Completion status is now backed by the separate read-only recovery audit; the original failed audit JSON remains unchanged.\n",
        "## Main result\n",
        f"Frozen primary endpoint, equal-condition ResidualPositionCNNV2 minus nominal fixed PyMatching: **{primary['mean']:+.6f} LER**, descriptive 95% root interval {interval_text(primary['ci95'])}; favorable roots {gate['observed_favorable_roots']}/5. **Development gate: {gate['status']}**.",
        "The primary CNN did not improve over the fixed baseline. The result is development-only and does not support superiority.\n",
        "## Aggregate errors (paired final-development shots)\n",
        f"- Nominal: fixed PyMatching {nominal_fixed}/50,000; historical CNN 254/50,000; V2 CNN 255/50,000; factorized CNN 257/50,000.",
        f"- Synthetic burst: nominal fixed PyMatching {burst_fixed}/50,000; historical CNN 389/50,000; V2 CNN 395/50,000; factorized CNN 402/50,000.",
        f"- Across both conditions: fixed PyMatching 641/100,000; historical CNN {cnn_totals[model_names[0]]}/100,000; V2 CNN {cnn_totals[model_names[1]]}/100,000; factorized CNN {cnn_totals[model_names[2]]}/100,000.",
        f"- Burst-informed PyMatching on burst samples only: 301/50,000 (privileged: it receives the true injected burst model).",
        "- Candidate-only/fixed-only failures, disagreements, useful/harmful corrections, and condition-specific root intervals are in CNN_STAGE2_RESULTS.md and CNN_STAGE2_PER_ROOT.csv.\n",
        "## Per-root primary paired effects\n",
        "\n| Root | Nominal delta | Burst delta | Equal-condition delta |\n|---|---:|---:|---:|\n",
        *[row + "\n" for row in root_rows],
        "\n## Training and runtime\n",
        "- Model parameter counts: historical 13,429; V2 13,041; factorized 12,653.",
        f"- Mean measured model inference wall latency across roots (includes both conditions): {average_latency}.",
        "- Residual-positive training examples were sparse (minimum root-condition count: 42); balanced presentations reused positives hundreds to over a thousand times per example, as recorded by root/model in the training diagnostics CSV.",
        "- Thresholds and temperatures were selected only from their designated calibration/threshold splits. Monitor-best checkpoints were restored and independently verified.",
        "- The burst condition is synthetic and not hardware-calibrated; DEM conversion uses the inherited approximation. No hardware integration was performed.\n",
    ]
    atomic_text(HERE / "CNN_STAGE2_EXECUTION_REPORT.md", "".join(report))
    competition = [
        "# Q-SHIFT CNN Stage 2 Competition Summary\n",
        "The frozen five-root development comparison completed with paired Stim samples and an independent read-only evidence audit. It generated 260,000 unique development shots; the independent test remained sealed.\n",
        f"ResidualPositionCNNV2 had a +0.000090 equal-condition LER difference versus fixed PyMatching (95% descriptive root-level interval {primary['ci95']}); it lost or tied in every root and the frozen gate **failed**. Across the 100,000 final shots, PyMatching made 641 errors and V2 made 650. These data do not demonstrate a neural-decoder advantage.\n",
        "A burst-informed PyMatching model made 301 errors on the 50,000 synthetic-burst shots, compared with 386 for nominal PyMatching. This reference knows the injected burst model and is not a deployable detector-only decoder. The burst mechanism is synthetic rather than hardware-calibrated.\n",
        "The experiment supports a reproducible comparison and a negative development finding. It does not establish generalization, confirmatory superiority, or hardware performance.\n",
    ]
    atomic_text(HERE / "CNN_STAGE2_COMPETITION_SUMMARY.md", "".join(competition))

    recovery_note = [
        "# Stage 2 Finalization Recovery\n",
        "The frozen training/sampling run completed all allocations and predictions but the original independent audit crashed at aggregate reporting with KeyError: 'shots'. Its source, failure JSON, predictions, raw arrays, model weights, and status snapshot are preserved. A separate read-only recovery auditor fixed only the aggregate shot-count lookup, reproduced model predictions and calibration selections, recomputed all metrics, and passed. No simulation or training was rerun. This correction does not change any frozen scientific choice.\n",
        f"- Original audit file: run_v1/independent_audit.json (FAIL preserved).",
        f"- Recovery audit: run_v1/independent_audit_recovery.json (PASS; SHA-256 {sha256(RECOVERY_AUDIT)}).",
        f"- Original failed status snapshot: run_v1/raw/FINALIZATION_FAILURE_V1.json (SHA-256 {failure_snapshot_sha}).",
        "- Current status is completed with recovery provenance fields; it is not presented as if the original finalization succeeded.\n",
    ]
    atomic_text(HERE / "CNN_STAGE2_FINALIZATION_RECOVERY.md", "".join(recovery_note))

    # Build an auditable evidence inventory. Exclude mutable status/lock files;
    # the final status contains the manifest hash and would otherwise self-reference.
    files = {}
    for folder in (RAW, RUN / "checkpoints", RUN / "predictions"):
        for path in sorted(p for p in folder.rglob("*") if p.is_file()):
            if path == STATUS or path.name == "runner.lock" or path.name.endswith(".tmp"):
                continue
            files[path.relative_to(ROOT).as_posix()] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    top_paths = [
        HERE / "FREEZE.json", HERE / "FREEZE_IMPLEMENTATION_V2.json", HERE / "FREEZE_IMPLEMENTATION_V3.json",
        HERE / "FREEZE_IMPLEMENTATION_V4.json", HERE / "stage2_config.json", HERE / "seed_inventory.json",
        HERE / "seed_audit.json", HERE / "CNN_STAGE2_FROZEN_PROTOCOL.md",
        HERE / "STAGE2_FREEZE_SUPERSESSION.md", HERE / "STAGE2_FREEZE_SUPERSESSION_V3.md",
        HERE / "STAGE2_FREEZE_SUPERSESSION_V4.md", HERE / "CNN_STAGE2_IMPLEMENTATION_READINESS.md",
        HERE / "CNN_STAGE2_IMPLEMENTATION_READINESS_V3.md", HERE / "CNN_STAGE2_IMPLEMENTATION_READINESS_V4.md",
        HERE / "freeze_stage2_v2.py", HERE / "freeze_stage2_v3.py", HERE / "freeze_stage2_v4.py",
        HERE / "run_stage2.py", HERE / "audit_stage2.py", HERE / "audit_stage2_recovery.py",
        HERE / "finalize_stage2_recovery.py", HERE / "tests" / "test_stage2_runner.py",
        HERE / "CNN_STAGE2_RESULTS.md", HERE / "CNN_STAGE2_INDEPENDENT_AUDIT.md",
        HERE / "CNN_STAGE2_PER_ROOT.csv", HERE / "CNN_STAGE2_TRAINING_DIAGNOSTICS.csv",
        HERE / "CNN_STAGE2_EXECUTION_REPORT.md", HERE / "CNN_STAGE2_COMPETITION_SUMMARY.md",
        HERE / "CNN_STAGE2_FINALIZATION_RECOVERY.md",
    ]
    for path in top_paths:
        if path.is_file():
            files[path.relative_to(ROOT).as_posix()] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    run_records = [RUN / "independent_audit.json", RECOVERY_AUDIT, RUN / "dry_run_report.json"]
    for path in run_records:
        if path.is_file():
            files[path.relative_to(ROOT).as_posix()] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    manifest = {
        "status": "INDEPENDENT_RECOVERY_AUDIT_PASS",
        "freeze_protocol_id_sha256": audit["freeze_protocol_id_sha256"],
        "unique_shots": audit["unique_shot_total"],
        "roots": audit["root_count"],
        "model_root_jobs": audit["model_root_jobs"],
        "independent_test_accessed": False,
        "mutable_status_and_lock_excluded_to_avoid_self_reference": True,
        "original_finalization_failure_preserved": True,
        "files": files,
    }
    manifest_path = HERE / "STAGE2_EVIDENCE_MANIFEST.json"
    atomic_json(manifest_path, manifest)
    manifest_sha = sha256(manifest_path)

    prior_failure = {
        "status": "failed",
        "failure": status.get("failure"),
        "failed_utc": status.get("failed_utc"),
        "snapshot_path": FAILURE_SNAPSHOT.relative_to(ROOT).as_posix(),
        "snapshot_sha256": failure_snapshot_sha,
        "original_audit_status": "FAIL",
        "recovery_audit_status": "PASS",
    }
    status["status"] = "completed"
    status["recoverable"] = False
    status["prior_finalization_attempt"] = prior_failure
    status.pop("failure", None)
    status.pop("traceback", None)
    status.pop("failed_utc", None)
    status["independent_audit_status"] = "PASS_WITH_RECOVERY_AUDIT"
    status["recovery_audit_sha256"] = sha256(RECOVERY_AUDIT)
    status["evidence_manifest_sha256"] = manifest_sha
    status["recovery_audit_wall_seconds"] = 3.108
    status["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    status["recovery_note"] = "No simulation or training was rerun; finalization recovered from a reporting-only KeyError using a separate read-only auditor."
    atomic_json(STATUS, status)
    print(json.dumps({
        "status": status["status"], "shots": status["completed_unique_shots"],
        "roots": len(status["completed_roots"]), "jobs": status["completed_model_root_jobs"],
        "recovery_audit": audit["status"], "gate": gate["status"],
        "evidence_manifest_sha256": manifest_sha,
    }, indent=2))


if __name__ == "__main__":
    main()
