"""Strict v2 freeze verification; no sampling or freeze creation occurs here."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FREEZE_PATH = HERE / "PRETEST_FREEZE_V2.json"
CONFIG_PATH = HERE / "experiment_config_v2.json"
INVENTORY_PATH = HERE / "seed_inventory_v2.json"
REQUIRED_HASHES = {
    "outputs/strong_fixed_baselines_v2/experiment_config_v2.json",
    "outputs/strong_fixed_baselines_v2/seed_inventory_v2.json",
    "outputs/strong_fixed_baselines_v2/run_development_v2.py",
    "outputs/strong_fixed_baselines_v2/pooled_calibration_v2.py",
    "outputs/strong_fixed_baselines_v2/freeze_pretest_v2.py",
    "outputs/strong_fixed_baselines_v2/test_pooled_calibration_v2.py",
    "outputs/strong_fixed_baselines_v2/PROSPECTIVE_REPLICATION_PLAN_V1.md",
    "outputs/strong_fixed_baselines_v1/experiment_core.py",
    "outputs/phase3a_correlated_noise_preflight/simulator.py",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_freeze() -> dict:
    if not FREEZE_PATH.is_file():
        raise RuntimeError("v2 is a review candidate: prospective seed inventory and pre-sampling freeze are not yet approved")
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    if freeze.get("sampling_performed_at_freeze") is not False:
        raise RuntimeError("v2 freeze was not recorded before sampling")
    if freeze.get("sampling_authorized") is not True:
        raise RuntimeError("v2 sampling is not authorized")
    if not INVENTORY_PATH.is_file():
        raise RuntimeError("v2 seed inventory is missing")
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    if inventory.get("sampling_performed") is not False or inventory.get("collisions"):
        raise RuntimeError("v2 seed inventory is invalid or already sampled")
    if inventory.get("historical_coverage_complete") is not True:
        raise RuntimeError("v2 seed collision coverage is incomplete")
    expected = freeze.get("sha256", {})
    if not REQUIRED_HASHES.issubset(expected):
        raise RuntimeError("v2 freeze omits required source, configuration, seed or protocol hashes")
    for rel, digest in expected.items():
        path = ROOT / rel
        if not path.is_file() or sha256(path) != digest:
            raise RuntimeError(f"v2 frozen file missing or changed: {rel}")
    return freeze
