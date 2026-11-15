"""Verify the failed pre-evaluation attempt without touching evaluation labels."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
RUN = ROOT / "pilot_runs" / "attempt_001"
SUPPORTS = ((5, 7, 10), (13, 15, 18), (21, 23, 26), (29, 31, 34), (37, 38, 39))


def features(path):
    with np.load(path, allow_pickle=False) as z:
        x = np.asarray(z["detectors"], dtype=np.uint8)
    if x.ndim != 2 or x.shape[1] != 40:
        raise ValueError(f"bad detector archive shape: {path.name}")
    return float(np.column_stack([np.all(x[:, s] == 1, axis=1) for s in SUPPORTS]).mean())


def main():
    status = json.loads((RUN / "status.json").read_text(encoding="utf-8"))
    identity = json.loads((RUN / "execution_identity.json").read_text(encoding="utf-8"))
    if status["state"] != "inconclusive_calibration_gate":
        raise SystemExit("unexpected attempt terminal state")
    calls = status["sampler_calls_started"]
    if len(calls) != 33 or any(c["phase"] == "evaluation" for c in calls):
        raise SystemExit("unexpected call count or evaluation sampling")
    if any(c["state"] != "committed" for c in calls):
        raise SystemExit("uncommitted call present; do not classify this as a clean gate stop")
    seed_values = [c["seed"] for c in calls]
    if len(seed_values) != len(set(seed_values)):
        raise SystemExit("duplicate sampler seed in attempt")
    hashes = []
    for item in status["archives"]:
        path = RUN.parent / item["path"]
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != item["sha256"]:
            raise SystemExit(f"archive hash mismatch: {item['path']}")
        hashes.append({"path": item["path"], "sha256": digest, "bytes": len(raw), "shots": item["shots"]})
    if sum(x["shots"] for x in hashes) != 18000:
        raise SystemExit("unexpected committed shot count")
    eval_files = list((RUN / "evaluation").glob("*.npz"))
    if eval_files:
        raise SystemExit("evaluation archive exists despite pre-evaluation gate")

    train_rates = []
    for qi, q in enumerate((0.0, 0.01, 0.02)):
        train_rates.append(features(RUN / "training" / f"train_q{qi}.npz"))
    cal_rates = {}
    for qi, q in enumerate((0.0, 0.01, 0.02)):
        cal_rates[str(q)] = [features(RUN / "calibration" / f"cal_q{qi}_r{ri:02d}.npz") for ri in range(10)]
    fitted = np.polyfit(np.asarray([0.0, 0.01, 0.02]), np.asarray(train_rates), deg=1)
    correct_slope, correct_intercept = map(float, fitted)
    estimator_file = json.loads((RUN / "training" / "estimator.json").read_text(encoding="utf-8"))
    reversed_assignment_confirmed = (
        abs(estimator_file["intercept"] - correct_slope) < 1e-12 and
        abs(estimator_file["slope"] - correct_intercept) < 1e-12
    )
    calibration_mean_rates = {q: float(np.mean(v)) for q, v in cal_rates.items()}
    corrected_mean_qhat = {
        q: float(np.clip((mean - correct_intercept) / correct_slope, 0.0, 0.02))
        for q, mean in calibration_mean_rates.items()
    }
    diagnostics = json.loads((RUN / "calibration" / "diagnostics.json").read_text(encoding="utf-8"))
    total_bytes = sum(x["bytes"] for x in hashes)
    report = {
        "schema": "qshift-correlated-decoder-failed-attempt-evidence-v1",
        "classification": "inconclusive; stopped at frozen calibration gate; no evaluation or LER analysis",
        "run_id": status["run_id"],
        "source_commit": identity["git_head"],
        "pretest_freeze_sha256": identity["pretest_freeze_sha256"],
        "terminal_state": status["state"],
        "sampler_calls_started": len(calls),
        "sampler_calls_committed": sum(c["state"] == "committed" for c in calls),
        "shots_started": status["shots_started"],
        "shots_committed": status["shots_committed"],
        "partition_shots": {"training": 3000, "calibration": 15000, "evaluation": 0},
        "evaluation_archive_count": 0,
        "evaluation_labels_read_for_scoring": False,
        "training_feature_rates_by_q": train_rates,
        "stored_estimator": estimator_file,
        "independent_polyfit_coefficients": {"slope": correct_slope, "intercept": correct_intercept},
        "reversed_coefficient_assignment_confirmed": reversed_assignment_confirmed,
        "calibration_mean_feature_rates_by_q": calibration_mean_rates,
        "stored_mean_qhat_by_condition": diagnostics["mean_qhat_by_condition"],
        "corrected_algebra_mean_qhat_diagnostic_only": corrected_mean_qhat,
        "calibration_order_gate_passed_as_run": diagnostics["condition_order_gate_passed"],
        "artifact_bytes_hashed": total_bytes,
        "archive_manifest": hashes,
        "pilot_wall_seconds_from_watchdog": 5.265,
        "peak_rss_persisted": False,
        "notes": [
            "The exact implementation assigned numpy.polyfit output [slope, intercept] to [intercept, slope], reversing the coefficients.",
            "The corrected mean q-hat calculation is a post-run training/calibration-only algebra diagnostic; it was not used to run decoders or select evaluation outcomes.",
            "The original source freeze and run artifacts remain unchanged; this manifest is a separate audit artifact."
        ]
    }
    target = ROOT / "FAILED_ATTEMPT_EVIDENCE_MANIFEST.json"
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: report[k] for k in ("terminal_state", "sampler_calls_started", "shots_committed", "partition_shots", "evaluation_archive_count", "reversed_coefficient_assignment_confirmed", "training_feature_rates_by_q", "calibration_mean_feature_rates_by_q", "corrected_algebra_mean_qhat_diagnostic_only", "artifact_bytes_hashed")}, indent=2))


if __name__ == "__main__":
    main()
