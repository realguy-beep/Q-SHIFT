"""Build a deterministic hash inventory for lightweight study evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

FILES = [
    "README.md",
    "RESEARCH_STATUS.md",
    "EXPERIMENT_INDEX.md",
    "outputs/strong_fixed_baselines_v1/STRONG_BASELINE_PROTOCOL.md",
    "outputs/strong_fixed_baselines_v1/experiment_config.json",
    "outputs/strong_fixed_baselines_v1/PRETEST_FREEZE_V14.json",
    "outputs/strong_fixed_baselines_v1/seed_inventory.json",
    "outputs/strong_fixed_baselines_v1/POSTRUN_AUDIT_ATTEMPT_V1.md",
    "outputs/strong_fixed_baselines_v1/POSTRUN_RECONSTRUCTION_PROTOCOL_V1.md",
    "outputs/strong_fixed_baselines_v1/POSTRUN_RECONSTRUCTION_FREEZE_V1.json",
    "outputs/strong_fixed_baselines_v1/POSTRUN_RECONSTRUCTION_VERIFICATION_V1.json",
    "outputs/strong_fixed_baselines_v1/verify_reconstruction_outputs_v1.py",
    "outputs/strong_fixed_baselines_v1/test_experiment.py",
    "outputs/strong_fixed_baselines_v1/FINAL_RESULTS_AND_INTERPRETATION.md",
    "outputs/strong_fixed_baselines_v1/RUNNER_DEVIATION_AND_RESULTS.md",
    "outputs/strong_fixed_baselines_v1/REPRODUCE.md",
    "outputs/strong_fixed_baselines_v1/STUDY_VALIDATION.md",
    "outputs/strong_fixed_baselines_v1/TEACHER_SUMMARY.md",
    "outputs/strong_fixed_baselines_v1/report_reconstruction_v1/RESULTS.md",
    "outputs/strong_fixed_baselines_v1/report_reconstruction_v1/RESULTS.json",
    "outputs/strong_fixed_baselines_v1/report_reconstruction_v1/PER_CONDITION.csv",
    "outputs/strong_fixed_baselines_v1/report_reconstruction_v1/PER_ROOT.csv",
    "outputs/strong_fixed_baselines_v1/report_reconstruction_v1/REPORT_MANIFEST.json",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    files = {}
    for rel in FILES:
        path = ROOT / rel
        if not path.is_file():
            raise FileNotFoundError(f"required evidence file is missing: {rel}")
        files[rel.replace("\\", "/")] = {
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
    result = json.loads((HERE / "report_reconstruction_v1" / "RESULTS.json").read_text(encoding="utf-8"))
    verify = json.loads((HERE / "POSTRUN_RECONSTRUCTION_VERIFICATION_V1.json").read_text(encoding="utf-8"))
    manifest = {
        "schema_version": 1,
        "study": "Q-SHIFT strong fixed-baseline burst comparison v1",
        "classification": "development feasibility with declared runner deviation; not confirmatory",
        "sampling_performed_by_manifest_builder": False,
        "sealed_stage5_access": False,
        "unique_study_shots": result["total_unique_shots"],
        "paired_final_development_shots": result["final_paired_evaluation_shots"],
        "verified_prediction_values": verify["corrected_prediction_values_verified"],
        "verified_roots": 600,
        "numerical_audit_status": verify["audit_status"],
        "deviation_status": "confirmed pooled-calibration implementation deviation; corrected reconstruction retained separately",
        "historical_freeze_sha256": "2fd6fa631a452c9a00002b8b3365f4ae2b26ad910e7f08ff3e5a92a679a6c5a8",
        "reconstruction_freeze_sha256": "7d8b50218118ec0c56f3930efe3804d6cf1fb1669f720353620d06e910fe9aaf",
        "files": files,
        "excluded_local_evidence": [
            "raw NPZ detector/observable arrays and commit markers",
            "corrected per-shot prediction archives",
            "runtime status and logs",
            "Stage 5 independent-test material (not accessed)",
        ],
    }
    out = HERE / "FINAL_EVIDENCE_MANIFEST.json"
    out.write_text(json.dumps(manifest, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} with {len(files)} SHA-256 entries")


if __name__ == "__main__":
    main()
