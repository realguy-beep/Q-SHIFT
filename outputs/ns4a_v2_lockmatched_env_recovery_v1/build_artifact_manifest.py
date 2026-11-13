from __future__ import annotations

import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
FILES = (
    "BELIEFMATCHING_COMPATIBILITY_MATRIX.json",
    "DEPENDENCY_VERIFICATION.json",
    "DETERMINISTIC_PREFLIGHT_RERUN.md",
    "ENVIRONMENT_PROVENANCE.md",
    "INDEPENDENT_PREFLIGHT_VERIFICATION.json",
    "LOCKMATCHED_PREFLIGHT_SUMMARY.json",
    "REPRODUCE.md",
    "SOURCE_INPUT_INVENTORY.json",
    "VALIDATION_SUMMARY.md",
    "record_source_inventory.py",
    "requirements-ns3b.lock.txt",
    "run_lockmatched_preflight.py",
    "verify_artifact_manifest.py",
    "verify_lock_environment.py",
    "verify_lockmatched_preflight.py",
    "build_artifact_manifest.py",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main() -> int:
    missing = [name for name in FILES if not (OUT / name).is_file()]
    if missing:
        raise SystemExit(f"Cannot freeze missing artifact(s): {missing}")
    manifest = {
        "schema": "qshift-ns4a-v2-lockmatched-artifact-manifest-v1",
        "base_commit": "2ba57e83e262ca32afe4cb58063d2e3e63605e3b",
        "branch": "codex/ns4a-v2-lockmatched-env",
        "manifest_self_hash": "excluded by design",
        "hash_convention": "SHA-256 and byte count after CRLF-to-LF normalization",
        "files": {
            name: {
                "sha256": sha(OUT / name),
                "normalized_bytes": len((OUT / name).read_bytes().replace(b"\r\n", b"\n")),
            }
            for name in FILES
        },
    }
    path = OUT / "ARTIFACT_SHA256_MANIFEST.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"file_count": len(FILES), "manifest": str(path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
