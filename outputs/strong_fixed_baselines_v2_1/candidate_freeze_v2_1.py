"""Verify the separately versioned V2.1 authorization-launch candidate.

The original V2 scientific freeze remains authoritative and is verified first.
This layer binds only the launch/approval plumbing and does not alter science.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from outputs.strong_fixed_baselines_v2.freeze_pretest_v2 import (
    CONFIG_PATH as V2_CONFIG_PATH,
    INVENTORY_PATH as V2_INVENTORY_PATH,
    ROOT,
    verify_freeze as verify_v2_freeze,
)

HERE = Path(__file__).resolve().parent
FREEZE_PATH = HERE / "PRETEST_FREEZE_V2_1.json"
ORIGINAL_FREEZE_PATH = V2_CONFIG_PATH.parent / "PRETEST_FREEZE_V2.json"
FILES_TO_HASH = {
    ".gitignore",
    "outputs/strong_fixed_baselines_v2/PRETEST_FREEZE_V2.json",
    "outputs/strong_fixed_baselines_v2/experiment_config_v2.json",
    "outputs/strong_fixed_baselines_v2/seed_inventory_v2_r2.json",
    "outputs/strong_fixed_baselines_v2/run_development_v2.py",
    "outputs/strong_fixed_baselines_v2/pooled_calibration_v2.py",
    "outputs/strong_fixed_baselines_v2/audit_saved_arrays_v2.py",
    "outputs/strong_fixed_baselines_v2_1/authorization_v2_1.py",
    "outputs/strong_fixed_baselines_v2_1/candidate_freeze_v2_1.py",
    "outputs/strong_fixed_baselines_v2_1/create_pretest_freeze_v2_1.py",
    "outputs/strong_fixed_baselines_v2_1/run_development_v2_1.py",
    "outputs/strong_fixed_baselines_v2_1/audit_saved_arrays_v2_1.py",
    "outputs/strong_fixed_baselines_v2_1/test_authorization_v2_1.py",
    "outputs/strong_fixed_baselines_v2_1/AUTHORIZATION_PROTOCOL_V2_1.md",
    "outputs/strong_fixed_baselines_v2_1/RUNTIME_PROVENANCE_V2_1.md",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_hash_map(root: Path, recorded: dict[str, str], expected_paths: set[str]) -> None:
    if set(recorded) != expected_paths:
        raise RuntimeError("V2.1 freeze hash inventory does not match its declared file set")
    for relative, expected in recorded.items():
        path = root / relative
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"V2.1 frozen file missing or changed: {relative}")


def verify_candidate_freeze() -> dict:
    if not FREEZE_PATH.is_file():
        raise RuntimeError("V2.1 review-only candidate freeze is missing")
    original = verify_v2_freeze()
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if freeze.get("freeze_status") != "AUTHORIZATION_CANDIDATE_REVIEW_ONLY":
        raise RuntimeError("unexpected V2.1 candidate freeze status")
    if freeze.get("sampling_authorized") is not False or freeze.get("sampling_performed") is not False:
        raise RuntimeError("V2.1 candidate freeze must remain unauthorized and unsampled")
    if freeze.get("original_v2_freeze_sha256") != sha256(ORIGINAL_FREEZE_PATH):
        raise RuntimeError("V2.1 candidate points at a different original V2 freeze")
    if freeze.get("scientific_configuration_sha256") != sha256(V2_CONFIG_PATH):
        raise RuntimeError("V2.1 candidate configuration differs from original V2")
    if freeze.get("seed_inventory_sha256") != sha256(V2_INVENTORY_PATH):
        raise RuntimeError("V2.1 candidate seed inventory differs from original V2")
    if freeze.get("primary_contrast") != original.get("primary_contrast"):
        raise RuntimeError("V2.1 candidate changed the frozen primary contrast")
    hashes = freeze.get("sha256", {})
    verify_hash_map(ROOT, hashes, FILES_TO_HASH)
    return freeze


if __name__ == "__main__":
    result = verify_candidate_freeze()
    print(json.dumps({
        "freeze_status": result["freeze_status"],
        "sampling_authorized": result["sampling_authorized"],
        "hashes_verified": len(result["sha256"]),
        "original_v2_freeze_sha256": result["original_v2_freeze_sha256"],
    }, indent=2))
