"""Write/verify pre-sampling Stage 4C source/configuration SHA-256 freeze."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FREEZE = HERE / "FREEZE.json"
FILES = [
    ".gitignore",
    "outputs/stage4c_cnn_noise_estimation_v1/CNN_STAGE4C_PROTOCOL.md",
    "outputs/stage4c_cnn_noise_estimation_v1/DATASET_PARTITIONS.md",
    "outputs/stage4c_cnn_noise_estimation_v1/REPRODUCE.md",
    "outputs/stage4c_cnn_noise_estimation_v1/config.json",
    "outputs/stage4c_cnn_noise_estimation_v1/seed_inventory.json",
    "outputs/stage4c_cnn_noise_estimation_v1/seed_audit.json",
    "outputs/stage4c_cnn_noise_estimation_v1/prepare_inventory.py",
    "outputs/stage4c_cnn_noise_estimation_v1/models.py",
    "outputs/stage4c_cnn_noise_estimation_v1/experiment.py",
    "outputs/stage4c_cnn_noise_estimation_v1/analysis.py",
    "outputs/stage4c_cnn_noise_estimation_v1/audit_results.py",
    "outputs/stage4c_cnn_noise_estimation_v1/build_freeze.py",
    "outputs/stage4c_cnn_noise_estimation_v1/tests/__init__.py",
    "outputs/stage4c_cnn_noise_estimation_v1/tests/test_models.py",
    "outputs/stage4c_cnn_noise_estimation_v1/tests/test_statistics.py",
    "outputs/stage4c_cnn_noise_estimation_v1/build_manifest.py",
    "outputs/stage4_noise_adaptive_feasibility_v1/prototype.py",
    "outputs/phase3a_correlated_noise_preflight/simulator.py",
    "outputs/phase2b_pauli_bias/noise_model.py",
    "outputs/stage4_noise_adaptive_development_v1/STAGE4_DEVELOPMENT_PROTOCOL.md",
    "outputs/stage4_noise_adaptive_development_v1/STAGE4_DEVELOPMENT_FREEZE_V2.json",
    "outputs/stage4_noise_adaptive_development_v1/STAGE4_RESULTS.md",
    "outputs/stage4_noise_adaptive_development_v1/STAGE4_INDEPENDENT_AUDIT.md",
    "outputs/stage4_noise_adaptive_development_v1/STAGE4_AUDIT_RECOVERY_NOTE.md",
    "outputs/stage4_noise_adaptive_development_v1/REPRODUCE_AFTER_RECOVERY.md",
    "outputs/stage4_noise_adaptive_development_v1/STAGE4_EXECUTION_REPORT.md",
    "outputs/stage4_noise_adaptive_development_v1/run_stage4.py",
    "outputs/stage4_noise_adaptive_development_v1/audit_stage4_recovery.py",
    "outputs/stage4_noise_adaptive_development_v1/analysis.py",
    "outputs/stage4_noise_adaptive_development_v1/stage4_development_config.json",
    "outputs/stage4_noise_adaptive_development_v1/seed_inventory.json",
    "outputs/stage4_noise_adaptive_development_v1/additional_development_seed_audit.json",
    "outputs/stage4_noise_adaptive_development_v1/RESULTS.json",
    "outputs/stage4_noise_adaptive_development_v1/AUDIT_RESULTS.json",
    "outputs/stage4_noise_adaptive_development_v1/EVIDENCE_MANIFEST.json",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_record() -> dict:
    hashes = {}
    for rel in FILES:
        path = REPO / rel
        if not path.is_file():
            raise FileNotFoundError(f"freeze input missing: {rel}")
        hashes[rel] = digest(path)
    inv = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
    audit = json.loads((HERE / "seed_audit.json").read_text(encoding="utf-8"))
    return {
        "status": "FROZEN_BEFORE_SAMPLING",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "study": "qshift-stage4c-cnn-noise-estimation-v1",
        "frozen_experiment_configuration_sha256": digest(HERE / "config.json"),
        "seed_inventory_sha256": digest(HERE / "seed_inventory.json"),
        "seed_audit_sha256": digest(HERE / "seed_audit.json"),
        "seed_count": inv["unique_seed_count"],
        "historical_collision_audit_status": audit["status"],
        "total_unique_shots": 277500,
        "independent_test_accessed": False,
        "files_sha256": hashes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    current = build_record()
    if args.write:
        run_dir = HERE / "run"
        if run_dir.exists() and any(run_dir.iterdir()):
            raise RuntimeError("run/ already contains artifacts; cannot create a new freeze after sampling")
        FREEZE.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE {FREEZE.relative_to(REPO)} sha256={digest(FREEZE)}")
        return
    if not FREEZE.is_file():
        raise FileNotFoundError("FREEZE.json is missing")
    frozen = json.loads(FREEZE.read_text(encoding="utf-8"))
    if frozen.get("files_sha256") != current["files_sha256"]:
        changed = [k for k, v in frozen.get("files_sha256", {}).items()
                   if current["files_sha256"].get(k) != v]
        raise RuntimeError(f"frozen source/configuration mismatch: {changed}")
    if frozen.get("frozen_experiment_configuration_sha256") != current["frozen_experiment_configuration_sha256"]:
        raise RuntimeError("configuration hash mismatch")
    if frozen.get("seed_inventory_sha256") != current["seed_inventory_sha256"] or frozen.get("seed_audit_sha256") != current["seed_audit_sha256"]:
        raise RuntimeError("seed inventory/audit hash mismatch")
    print(f"PASS {FREEZE.relative_to(REPO)}; {len(current['files_sha256'])} frozen files match")


if __name__ == "__main__":
    main()
