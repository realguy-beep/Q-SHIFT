"""Freeze code/config/seed material before any study-partition sampling."""
from __future__ import annotations

import json
from pathlib import Path

from experiment_core import sha256, atomic_json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FREEZE_V1 = HERE / "PRETEST_FREEZE.json"
FREEZE_V2 = HERE / "PRETEST_FREEZE_V2.json"
FREEZE_V3 = HERE / "PRETEST_FREEZE_V3.json"
FREEZE_V4 = HERE / "PRETEST_FREEZE_V4.json"
FREEZE_V5 = HERE / "PRETEST_FREEZE_V5.json"
FREEZE_V6 = HERE / "PRETEST_FREEZE_V6.json"
FREEZE_V7 = HERE / "PRETEST_FREEZE_V7.json"
FREEZE_V8 = HERE / "PRETEST_FREEZE_V8.json"
FREEZE_V9 = HERE / "PRETEST_FREEZE_V9.json"
FREEZE_V10 = HERE / "PRETEST_FREEZE_V10.json"
FREEZE_V11 = HERE / "PRETEST_FREEZE_V11.json"
FREEZE_V12 = HERE / "PRETEST_FREEZE_V12.json"
FREEZE_V13 = HERE / "PRETEST_FREEZE_V13.json"
FREEZE_V14 = HERE / "PRETEST_FREEZE_V14.json"

FILES = [
    "outputs/strong_fixed_baselines_v1/STRONG_BASELINE_PROTOCOL.md",
    "outputs/strong_fixed_baselines_v1/BASELINE_FAIRNESS_MATRIX.md",
    "outputs/strong_fixed_baselines_v1/STATISTICAL_ANALYSIS_PLAN.md",
    "outputs/strong_fixed_baselines_v1/EXPERIMENT_IMPLEMENTATION_PLAN.md",
    "outputs/strong_fixed_baselines_v1/RESEARCH_RISK_REGISTER.md",
    "outputs/strong_fixed_baselines_v1/experiment_config.json",
    "outputs/strong_fixed_baselines_v1/prepare_seed_inventory.py",
    "outputs/strong_fixed_baselines_v1/seed_inventory.json",
    "outputs/strong_fixed_baselines_v1/experiment_core.py",
    "outputs/strong_fixed_baselines_v1/run_development.py",
    "outputs/strong_fixed_baselines_v1/audit_saved_run.py",
    "outputs/strong_fixed_baselines_v1/analyze_results.py",
    "outputs/strong_fixed_baselines_v1/benchmark_pipeline.py",
    "outputs/strong_fixed_baselines_v1/test_experiment.py",
    "outputs/strong_fixed_baselines_v1/audit_partial_run.py",
    "outputs/strong_fixed_baselines_v1/prepare_resume_copy.py",
    "outputs/strong_fixed_baselines_v1/prepare_recovery_copy_v4.py",
    "outputs/strong_fixed_baselines_v1/STUDY_FAILURE_V1.md",
    "outputs/strong_fixed_baselines_v1/partial_failure_audit/FAILED_RUN_PARTIAL_AUDIT.json",
    "outputs/strong_fixed_baselines_v1/freeze_pretest.py",
    "outputs/strong_fixed_baselines_v1/BENCHMARK_RESULTS.json",
    "outputs/strong_fixed_baselines_v1/BENCHMARK_FAILURE_V2.md",
    "outputs/strong_fixed_baselines_v1/BENCHMARK_FAILURE_V3.md",
    "outputs/strong_fixed_baselines_v1/BENCHMARK_RESULTS_V4.json",
    "outputs/strong_fixed_baselines_v1/BENCHMARK_RESOURCE_PROJECTION.md",
    "outputs/phase3a_correlated_noise_preflight/simulator.py",
    "outputs/phase2b_pauli_bias/noise_model.py",
    "outputs/stage4_noise_adaptive_feasibility_v1/prototype.py",
]


def expected_hashes() -> dict[str, str]:
    result = {}
    for relative in FILES:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"Cannot freeze missing file: {relative}")
        result[relative] = sha256(path)
    return result


def verify_freeze() -> dict:
    freeze_path = next((p for p in [FREEZE_V14, FREEZE_V13, FREEZE_V12, FREEZE_V11, FREEZE_V10, FREEZE_V9, FREEZE_V8, FREEZE_V7, FREEZE_V6, FREEZE_V5, FREEZE_V4, FREEZE_V3, FREEZE_V2, FREEZE_V1] if p.is_file()), FREEZE_V1)
    if not freeze_path.is_file():
        raise RuntimeError("PRETEST_FREEZE.json is missing")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    actual = expected_hashes()
    if actual != freeze.get("sha256"):
        mismatches = [k for k in sorted(set(actual) | set(freeze.get("sha256", {}))
                                         if isinstance(freeze.get("sha256"), dict) else set(actual))
                      if actual.get(k) != freeze.get("sha256", {}).get(k)]
        raise RuntimeError(f"Frozen source/config drift detected: {mismatches}")
    return freeze


def main() -> None:
    if FREEZE_V14.exists():
        raise FileExistsError("pretest freeze v14 already exists and is immutable")
    inventory = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
    if inventory.get("collisions") or inventory.get("sampling_performed"):
        raise RuntimeError("Seed inventory is invalid or indicates prior sampling")
    freeze = {
        "schema_version": 1,
        "created_before_sampling": True,
        "sampling_performed_at_freeze": False,
        "sealed_test_access": False,
        "study": "strong fixed-baseline development v1",
        "supersedes": ["PRETEST_FREEZE_V13.json", "run_recovery_v4/pre-sampling resume failure"],
        "supersession_reason": "V13's independent recovery copy verified 958 committed arrays and re-decoded 4.5M candidate prediction bits. The first resume attempt in run_recovery_v4 stopped before sampling because immutable JSON comparison did not normalize numeric dictionary keys to their on-disk string form. V14 canonicalizes JSON keys before comparison and adds a focused regression test. The V4 copy remains preserved, and V14 targets a new copy from the audited V3 source; its copied streams are the same seed allocations and are not double-counted. No final evaluation samples exist. The Windows atomic replacement retry remains. Scientific conditions, allocations, seeds, selection rules and endpoints remain unchanged. V14 is frozen before any further study sampling.",
        "recovery_target": "run_recovery_v5/",
        "original_failed_run_preserved": True,
        "partial_raw_shots_to_reuse_once": 510000,
        "new_shots_remaining_if_recovery_copy_passes": 3150000,
        "sampling_under_this_freeze": False,
        "config_sha256": sha256(HERE / "experiment_config.json"),
        "seed_inventory_sha256": sha256(HERE / "seed_inventory.json"),
        "sha256": expected_hashes(),
    }
    target = FREEZE_V14
    atomic_json(target, freeze)
    print(json.dumps({"status": "PRETEST_FREEZE_CREATED", "files": len(freeze["sha256"]),
                      "freeze_path": str(target), "freeze_sha256": sha256(target)}, indent=2))


if __name__ == "__main__":
    main()
