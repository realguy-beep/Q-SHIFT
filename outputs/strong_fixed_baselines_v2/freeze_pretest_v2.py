"""Verify the prospective, review-only V2 pre-sampling freeze."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FREEZE_PATH = HERE / "PRETEST_FREEZE_V2.json"
CONFIG_PATH = HERE / "experiment_config_v2.json"
INVENTORY_PATH = HERE / "seed_inventory_v2_r2.json"
REQUIRED_HASHES = {
    "outputs/strong_fixed_baselines_v2/experiment_config_v2.json",
    "outputs/strong_fixed_baselines_v2/seed_inventory_v2_r2.json",
    "outputs/strong_fixed_baselines_v2/run_development_v2.py",
    "outputs/strong_fixed_baselines_v2/pooled_calibration_v2.py",
    "outputs/strong_fixed_baselines_v2/prepare_seed_inventory_v2.py",
    "outputs/strong_fixed_baselines_v2/audit_saved_arrays_v2.py",
    "outputs/strong_fixed_baselines_v2/freeze_pretest_v2.py",
    "outputs/strong_fixed_baselines_v2/create_pretest_freeze_v2.py",
    "outputs/strong_fixed_baselines_v2/test_pooled_calibration_v2.py",
    "outputs/strong_fixed_baselines_v2/test_saved_array_audit_v2.py",
    "outputs/strong_fixed_baselines_v2/test_seed_inventory_v2.py",
    "outputs/strong_fixed_baselines_v2/PROSPECTIVE_REPLICATION_PLAN_V2.md",
    "outputs/strong_fixed_baselines_v2/FAIRNESS_AND_LEAKAGE_REVIEW_V2.md",
    "outputs/strong_fixed_baselines_v2/INDEPENDENT_AUDIT_PLAN_V2.md",
    "outputs/strong_fixed_baselines_v2/SEED_COLLISION_AUDIT_V2.md",
    "outputs/strong_fixed_baselines_v2/README.md",
    "outputs/strong_fixed_baselines_v1/experiment_core.py",
    "outputs/phase3a_correlated_noise_preflight/simulator.py",
    "outputs/stage4_noise_adaptive_feasibility_v1/prototype.py",
    "outputs/stage5_secondary_inference_repair_v1/STAGE5_SAMPLE_SEED_INVENTORY.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_freeze() -> dict:
    if not FREEZE_PATH.is_file():
        raise RuntimeError("review-only V2 pre-sampling freeze is missing")
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    if freeze.get("freeze_status") != "PRETEST_FREEZE_REVIEW_ONLY":
        raise RuntimeError("V2 freeze has an unexpected status")
    if freeze.get("sampling_performed_at_freeze") is not False or freeze.get("sampling_authorized") is not False:
        raise RuntimeError("V2 candidate freeze must record no sampling and no authorization")
    if config.get("execution", {}).get("sampling_authorized") is not False:
        raise RuntimeError("V2 config is not sampling-disabled")
    if config.get("seeds", {}).get("inventory_path") != str(INVENTORY_PATH.relative_to(ROOT)).replace("\\", "/"):
        raise RuntimeError("V2 config inventory path differs from the frozen inventory")
    if inventory.get("sampling_performed") is not False or inventory.get("sealed_test_access") is not False:
        raise RuntimeError("V2 inventory provenance is invalid")
    if inventory.get("allowlisted_metadata_sources_verified") is not True:
        raise RuntimeError("recoverable historical metadata allowlist was not verified")
    if inventory.get("historical_coverage_complete") is not False:
        raise RuntimeError("inventory must disclose incomplete undocumented historical coverage")
    if inventory.get("historical_collisions") or inventory.get("candidate_internal_collisions"):
        raise RuntimeError("V2 seed inventory reports a collision")
    seeds = [int(row["seed"]) for row in inventory.get("streams", [])]
    if len(seeds) != len(set(seeds)) or len(seeds) != int(inventory.get("candidate_unique_seed_count", -1)):
        raise RuntimeError("V2 seed inventory uniqueness count mismatch")
    if inventory.get("expected_unique_shots") != int(config["allocation"]["unique_shots"]):
        raise RuntimeError("V2 seed inventory allocation differs from config")
    if inventory.get("configuration_sha256") != sha256(CONFIG_PATH):
        raise RuntimeError("V2 seed inventory was built from a different config")
    hashes = freeze.get("sha256", {})
    if set(hashes) != REQUIRED_HASHES:
        missing = sorted(REQUIRED_HASHES - set(hashes))
        extra = sorted(set(hashes) - REQUIRED_HASHES)
        raise RuntimeError(f"V2 freeze file inventory mismatch; missing={missing}; extra={extra}")
    for relative, expected in hashes.items():
        path = ROOT / relative
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"V2 frozen file missing or changed: {relative}")
    if freeze.get("primary_contrast") != config["statistics"]["primary_contrast"]:
        raise RuntimeError("V2 frozen primary contrast differs from config")
    if freeze.get("primary_benefit_boundary") != config["statistics"]["primary_benefit_boundary"]:
        raise RuntimeError("V2 frozen practical-benefit boundary differs from config")
    return freeze


if __name__ == "__main__":
    verified = verify_freeze()
    print(json.dumps({
        "status": verified["freeze_status"],
        "sampling_authorized": verified["sampling_authorized"],
        "hashes_verified": len(verified["sha256"]),
        "primary_contrast": verified["primary_contrast"],
    }, indent=2))
