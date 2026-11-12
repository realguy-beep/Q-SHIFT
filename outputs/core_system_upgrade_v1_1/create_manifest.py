"""Create a lightweight source/report manifest for the v1.1 correction only."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PATHS = [
    "qshift_core_v1/controller.py",
    "qshift_core_v1/evaluation.py",
    "dashboard/tests/test_core_system_v1.py",
    "outputs/core_system_upgrade_v1_1/CORRECTIVE_REVIEW_REPORT.md",
    "outputs/core_system_upgrade_v1_1/V2_4_HOLD_CONFIRMATION.md",
    "outputs/core_system_upgrade_v1_1/NS0_ENGINEERING_READINESS.md",
    "outputs/core_system_upgrade_v1_1/UNRESOLVED_INTEGRATION_RISKS.md",
    "outputs/core_system_upgrade_v1_1/REPRODUCE.md",
    "outputs/core_system_upgrade_v1_1/V2_4_HOLD_AUDIT.json",
    "outputs/core_system_upgrade_v1_1/audit_v2_4_hold.py",
    "outputs/core_system_upgrade_v1_1/create_manifest.py",
    "outputs/core_system_upgrade_v1_1/verify_manifest.py",
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
            raise FileNotFoundError(f"Required v1.1 manifest input is missing: {relative}")
        files.append({"path": relative, "sha256": sha256(path), "bytes": path.stat().st_size})
    result = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "branch": "codex/core-system-upgrade",
        "reviewed_base_commit": "feb8c23715f0270e9c9ce1bb6444e414a26976bc",
        "scope": "deterministic decoder-contract corrections and NS-0 handoff; no experiment evidence",
        "sampling_performed": False,
        "protected_outcomes_accessed": False,
        "files": files,
        "manifest_self_hash_note": "MANIFEST.json is excluded from the file list; hash it separately.",
    }
    target = OUT / "MANIFEST.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)
    print(f"Wrote {target} with {len(files)} v1.1 hashes.")


if __name__ == "__main__":
    main()
