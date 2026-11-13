from __future__ import annotations

import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
FILES = [
    "PREFLIGHT_REPORT.md",
    "VALIDATION_SUMMARY.md",
    "VALIDATION_SUMMARY.json",
    "COMPATIBILITY_MATRIX.json",
    "SOURCE_INPUT_INVENTORY.json",
    "run_deterministic_preflight.py",
    "record_source_inventory.py",
    "build_preflight_manifest.py",
    "verify_preflight_artifacts.py",
]


def canonical_text(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def main() -> None:
    records = []
    for rel in FILES:
        data = canonical_text((OUT / rel).read_bytes())
        records.append(
            {
                "path": rel,
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )
    manifest = {
        "schema": "qshift-ns4a-v2-deterministic-preflight-manifest-v1",
        "base_commit": "612c5e1381d75ca069bc6952d057c798ab10e9ab",
        "branch": "codex/ns4a-v2-deterministic-preflight",
        "sampling_performed": False,
        "sealed_outcome_access": False,
        "self_hash_excluded": True,
        "files": records,
    }
    with (OUT / "PREFLIGHT_ARTIFACT_HASHES.json").open(
        "w", encoding="utf-8", newline="\n"
    ) as f:
        f.write(json.dumps(manifest, indent=2) + "\n")
    print(f"hashed {len(records)} artifacts; self hash excluded")


if __name__ == "__main__":
    main()
