"""Create an engineering-source SHA-256 manifest; performs no experiment work."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PATHS = [
    "qshift_core_v1/__init__.py",
    "qshift_core_v1/baselines.py",
    "qshift_core_v1/contracts.py",
    "qshift_core_v1/controller.py",
    "qshift_core_v1/evaluation.py",
    "qshift_core_v1/pymatching_adapter.py",
    "qshift_core_v1/seeds.py",
    "dashboard/configuration.py",
    "dashboard/seed_protocol.py",
    "dashboard/simulator.py",
    "dashboard/tests/test_core_system_v1.py",
    "dashboard/static/index.html",
    "dashboard/static/styles.css",
    "README.md",
    "RESEARCH_STATUS.md",
    "EXPERIMENT_INDEX.md",
    "outputs/core_system_upgrade_v1/ARCHITECTURE_INVENTORY.md",
    "outputs/core_system_upgrade_v1/RESEARCH_DECODER_INTEGRATION_CONTRACT.md",
    "outputs/core_system_upgrade_v1/IMPLEMENTATION_REPORT.md",
    "outputs/core_system_upgrade_v1/VALIDATION.md",
    "outputs/core_system_upgrade_v1/LIMITATIONS.md",
    "outputs/core_system_upgrade_v1/REPRODUCE.md",
    "outputs/core_system_upgrade_v1/TEACHER_SUMMARY.md",
    "outputs/core_system_upgrade_v1/FROZEN_V2_4_HASH_AUDIT.md",
    "outputs/core_system_upgrade_v1/create_manifest.py",
    "outputs/core_system_upgrade_v1/verify_manifest.py",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    files = []
    for relative in PATHS:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"Required manifest file is missing: {relative}")
        files.append({"path": relative, "sha256": sha256(path), "bytes": path.stat().st_size})
    freeze_path = ROOT / "outputs/strong_fixed_baselines_v2_4/PRETEST_FREEZE_V2_4.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    result = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "branch": "codex/core-system-upgrade",
        "base_commit": "0ff77c70e38a7e6c2ff547958aee00b0ae5c1fe5",
        "scope": "engineering source, deterministic tests, and documentation; no simulation evidence",
        "sampling_performed": False,
        "protected_evaluation_access": False,
        "v2_4_authorization_flags": {
            "sampling_authorized": freeze.get("sampling_authorized"),
            "sampling_performed": freeze.get("sampling_performed"),
            "sealed_test_access": freeze.get("sealed_test_access"),
        },
        "files": files,
        "manifest_self_hash_note": "MANIFEST.json is excluded from its own file list; verify its SHA-256 separately.",
    }
    target = OUT / "MANIFEST.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    print(f"Wrote {target} with {len(files)} source/document hashes.")


if __name__ == "__main__":
    main()
