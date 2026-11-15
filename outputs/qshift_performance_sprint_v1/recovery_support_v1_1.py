"""Fail-closed validation of the preserved V1 inputs for a single V1.1 replay."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SAMPLES = ROOT / "samples"
RECOVERY = SAMPLES / "recovery_v1_1"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
V1_MANIFEST_SHA256 = "74ed5a099c9269bb58f38eb1b4c3884095e9680b0f433c4af81ae8400681c926"
INVENTORY_PATH = ROOT / "RECOVERY_INPUT_INVENTORY_V1_1.json"
RECOVERY_MANIFEST = ROOT / "RECOVERY_SOURCE_MANIFEST_V1_1.json"


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_identity() -> dict:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, text=True,
                          capture_output=True, check=True).stdout.strip()
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=REPO, text=True,
                            capture_output=True, check=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, text=True,
                           capture_output=True, check=True).stdout.strip()
    if dirty:
        raise RuntimeError("recovery source checkout must be clean before sampling")
    return {"commit": head, "branch": branch, "clean": True}


def verify_v1_manifest() -> dict:
    path = ROOT / "source_manifest.json"
    if sha_file(path) != V1_MANIFEST_SHA256:
        raise RuntimeError("historical V1 source manifest hash mismatch")
    manifest = load_json(path)
    freeze = load_json(ROOT / "PRETEST_FREEZE.json")
    if freeze.get("source_manifest_sha256") != V1_MANIFEST_SHA256:
        raise RuntimeError("historical V1 pretest freeze no longer binds its manifest")
    if manifest.get("files") != freeze.get("source_files"):
        raise RuntimeError("historical V1 manifest and freeze inventory differ")
    for rel, expected in manifest["files"].items():
        path = REPO / rel
        if not path.is_file() or sha_file(path) != expected:
            raise RuntimeError(f"historical V1 source changed: {rel}")
    return manifest


def verify_recovery_manifest() -> dict:
    manifest = load_json(RECOVERY_MANIFEST)
    if manifest.get("schema") != "qshift-performance-recovery-source-freeze-v1.1":
        raise RuntimeError("unexpected V1.1 recovery source-manifest schema")
    if manifest.get("v1_source_manifest_sha256") != V1_MANIFEST_SHA256:
        raise RuntimeError("V1.1 recovery manifest is not bound to the original V1 freeze")
    if manifest.get("recovery_input_inventory_sha256") != sha_file(INVENTORY_PATH):
        raise RuntimeError("V1.1 recovery input inventory hash mismatch")
    for rel, expected in manifest["files"].items():
        path = ROOT / rel
        if not path.is_file() or sha_file(path) != expected:
            raise RuntimeError(f"V1.1 recovery source hash mismatch: {rel}")
    return manifest


def verify_recovery_inputs(*, require_no_output: bool = True) -> dict:
    verify_v1_manifest()
    manifest = verify_recovery_manifest()
    inventory = load_json(INVENTORY_PATH)
    if inventory.get("schema") != "qshift-performance-recovery-input-inventory-v1.1":
        raise RuntimeError("unexpected recovery input inventory schema")
    status_path = SAMPLES / "status.json"
    if sha_file(status_path) != inventory.get("original_attempt_status_sha256"):
        raise RuntimeError("preserved failed-attempt status changed")
    status = load_json(status_path)
    if (status.get("status") != "incomplete" or status.get("error_type") != "ValueError"
            or status.get("sampler_calls_started") != 56
            or status.get("shots_started") != 32000 or status.get("roots_complete") != 0):
        raise RuntimeError("failed-attempt state does not match the V1.1 recovery case")
    expected_files = {entry["path"].split("/", 1)[1] for entry in inventory["training_and_calibration_archives"]}
    expected_files.update({"status.json", "run_start.json", "trained_estimator.json"})
    actual_files = {p.name for p in SAMPLES.iterdir() if p.is_file()}
    if actual_files != expected_files:
        raise RuntimeError(f"original sample directory contains unexpected/missing files: {sorted(actual_files ^ expected_files)}")
    for entry in inventory["training_and_calibration_archives"]:
        path = ROOT / entry["path"]
        if not path.is_file() or sha_file(path) != entry["sha256"]:
            raise RuntimeError(f"preserved V1 archive hash mismatch: {entry['path']}")
    estimates_path = ROOT / "calibration_estimates.json"
    if sha_file(estimates_path) != inventory.get("calibration_estimates_sha256"):
        raise RuntimeError("preserved calibration estimate record changed")
    if inventory.get("persisted_evaluation_archives") != 0:
        raise RuntimeError("inventory does not document the expected empty evaluation state")
    if require_no_output and RECOVERY.exists():
        raise RuntimeError("V1.1 recovery output already exists; no automatic resume or overwrite")
    return {"inventory": inventory, "status": status, "manifest": manifest}


def load_training_and_fit():
    from estimator import RidgeProfile
    train_path = SAMPLES / "training_detector_only.npz"
    with np.load(train_path, allow_pickle=False) as data:
        detectors = np.asarray(data["detectors"], dtype=np.uint8)
        targets = np.asarray(data["p_targets"], dtype=np.float64)
    if detectors.shape != (5000, 40) or targets.shape != (5000,):
        raise RuntimeError("preserved training arrays have invalid shapes")
    model = RidgeProfile.fit(detectors, targets, alpha=10.0, clip=(0.0, 0.016))
    stored = load_json(SAMPLES / "trained_estimator.json")
    if model.to_dict() != stored:
        raise RuntimeError("reconstructed estimator differs from preserved fitted model")
    return model


def reconstruct_calibration(model) -> dict:
    p_values = (0.0, 0.004, 0.008, 0.012, 0.016)
    saved = load_json(ROOT / "calibration_estimates.json")
    if len(saved.get("estimates", [])) != 50:
        raise RuntimeError("preserved calibration estimate count mismatch")
    out = []
    all_x = []
    for i, p in enumerate(p_values):
        for root in range(10):
            path = SAMPLES / f"cal_p{i}_r{root:02d}.npz"
            with np.load(path, allow_pickle=False) as data:
                x = np.asarray(data["detectors"], dtype=np.uint8)
            if x.shape != (500, 40) or not np.isin(x, [0, 1]).all():
                raise RuntimeError(f"invalid preserved calibration array p{i}/r{root:02d}")
            p_hat = model.predict_mean(x)
            old = saved["estimates"][i * 10 + root]
            if old.get("p_index") != i or old.get("root") != root:
                raise RuntimeError("calibration record ordering mismatch")
            if abs(float(old["p_hat"]) - p_hat) > 1e-12:
                raise RuntimeError("recomputed calibration estimate differs from preserved record")
            out.append({"p_index": i, "root": root, "p": p, "p_hat": p_hat,
                        "seed_label": f"cal:p{i}:r{root:02d}"})
            all_x.append(x)
    p_global = model.predict_mean(np.concatenate(all_x, axis=0))
    if abs(float(saved["p_global"]) - p_global) > 1e-12:
        raise RuntimeError("recomputed pooled estimate differs from preserved record")
    return {"estimates": out, "p_global": p_global,
            "saved_record_sha256": sha_file(ROOT / "calibration_estimates.json")}
