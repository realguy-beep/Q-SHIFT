"""Create the one-time v3.4.4 implementation freeze; performs no sampling."""
from __future__ import annotations
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FREEZE = HERE / "SAFETY_FREEZE_V44.json"
SOURCES = [
    "V44_RECOVERY_PROTOCOL.md", "V44_RECOVERY_CONFIG.json",
    "atomic_safety_v44.py", "recovery_core_v44.py", "recovery_service_v44.py",
    "recovery_runner_v44.py", "worker_recovery_v44.py",
    "audit_saved_run_v44.py", "finalize_v44.py",
    "test_recovery_service_v44.py", "run_ownership_regressions_v44.py",
    "prepare_freeze_v44.py",
]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if FREEZE.exists():
        raise FileExistsError("v3.4.4 freeze already exists; preserve it and create a new version")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    config = json.loads((HERE / "V44_RECOVERY_CONFIG.json").read_text(encoding="utf-8"))
    if config["implementation_base_commit"] != head:
        raise RuntimeError(f"implementation base drift: expected {config['implementation_base_commit']}, got {head}")
    historical = {
        "stage5_v2": ROOT / "outputs/stage5_secondary_inference_repair_v1/STAGE5_PRETEST_FREEZE_V2.json",
        "stage5_v3_3": ROOT / "outputs/stage5_execution_safety_v3_3/SAFETY_FREEZE.json",
        "stage5_v3_4_2": ROOT / "outputs/stage5_execution_safety_v3_4_2/SAFETY_FREEZE_V4.json",
        "stage5_v3_4_3": ROOT / "outputs/stage5_execution_safety_v3_4_3/SAFETY_FREEZE_V43_2.json",
    }
    historical_hashes = {key: sha(path) for key, path in historical.items()}
    counts = {key: len(json.loads(path.read_text(encoding="utf-8")).get("sha256", {}))
              for key, path in historical.items() if key != "stage5_v3_4_3"}
    if counts != {"stage5_v2": 53, "stage5_v3_3": 13, "stage5_v3_4_2": 14}:
        raise RuntimeError(f"historical freeze inventory count mismatch: {counts}")
    v43_record = json.loads(historical["stage5_v3_4_3"].read_text(encoding="utf-8"))
    if v43_record.get("original_run_inventory_files_verified") != 265 or v43_record.get("forensic_manifest_entries_verified") != 56:
        raise RuntimeError("v3.4.3 historical preservation audit is incomplete")

    inv_path = ROOT / "outputs/stage5_postfailure_forensics_v1/PRE_INVESTIGATION_SHA256.json"
    inv = json.loads(inv_path.read_text(encoding="utf-8"))
    if inv.get("base_commit") != "8c06750808582137f6a81e2170ad702a552594fb" or inv.get("file_count") != 265:
        raise RuntimeError("original failed-run inventory mismatch")
    for row in inv["files"]:
        path = ROOT / row["path"]
        if not path.is_file() or sha(path) != row["sha256"]:
            raise RuntimeError(f"original failed-run artifact changed: {row['path']}")
    manifest_path = ROOT / "outputs/stage5_postfailure_forensics_v1/FORENSIC_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for rel, expected in manifest["files"].items():
        path = ROOT / rel
        if not path.is_file() or sha(path) != expected:
            raise RuntimeError(f"forensic evidence changed: {rel}")
    if len(manifest["files"]) != 56:
        raise RuntimeError("forensic manifest does not contain the expected 56 entries")

    hashes = {}
    for name in SOURCES:
        path = HERE / name
        if not path.is_file():
            raise FileNotFoundError(path)
        hashes[name] = sha(path)
    freeze = {
        "format": "qshift-stage5-v344-recovery-safety-freeze",
        "revision": "3.4.4",
        "base_commit": "8c06750808582137f6a81e2170ad702a552594fb",
        "implementation_base_commit": head,
        "sha256": hashes,
        "historical_hashes": historical_hashes,
        "historical_v2_hash_count": 53,
        "historical_v3_3_hash_count": 13,
        "historical_v3_4_2_hash_count": 14,
        "historical_v3_4_3_freeze_sha256": historical_hashes["stage5_v3_4_3"],
        "original_run_inventory_sha256": sha(inv_path),
        "original_run_files_verified_before_freeze": 265,
        "forensic_manifest_files_verified_before_freeze": 56,
        "scientific_protocol_changed": False,
        "stage5_recovery_executed": False,
        "stage5_additional_sampling": 0,
        "sealed_test_outcomes_accessed": False,
    }
    FREEZE.write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"freeze": str(FREEZE), "sha256": sha(FREEZE),
                      "source_hash_count": len(hashes), "original_files_verified": 265,
                      "forensic_files_verified": 56, "sampling": 0}, indent=2))


if __name__ == "__main__":
    main()
