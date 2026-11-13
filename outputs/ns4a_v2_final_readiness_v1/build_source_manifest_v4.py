"""Create final hardened V4 source manifest without overwriting the V3 draft."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

PACKAGE_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_DIR.parents[1]
BASE_MANIFEST = PACKAGE_DIR / "SOURCE_HASH_MANIFEST_V3.json"
OUTPUT = PACKAGE_DIR / "SOURCE_HASH_MANIFEST_V4.json"
EXPECTED_V3_MANIFEST_SHA256 = "277bcf663abff1d60aedda1ef5da04ecce5f5f77359598743dbaa642cb147d3b"
ADDITIONAL_PATHS = (
    "outputs/ns4a_v2_final_readiness_v1/SOURCE_HASH_MANIFEST_V3.json",
    "outputs/ns4a_v2_final_readiness_v1/build_source_manifest_v4.py",
    "outputs/ns4a_v2_final_readiness_v1/verify_source_manifest_v4.py",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit("V4 manifest already exists; refusing overwrite")
    if sha256(BASE_MANIFEST) != EXPECTED_V3_MANIFEST_SHA256:
        raise SystemExit("V3 historical manifest does not match its recorded hash; refusing V4 derivation")
    base = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
    if base.get("schema") != "qshift-ns4a-v2-source-manifest-v1" or not isinstance(base.get("files"), list):
        raise SystemExit("V3 source manifest schema is unsupported")
    paths = {row["path"] for row in base["files"] if isinstance(row, dict) and isinstance(row.get("path"), str)}
    if len(paths) != len(base["files"]):
        raise SystemExit("V3 source manifest rows are malformed or duplicated")
    paths.update(ADDITIONAL_PATHS)
    rows = []
    for relative in sorted(paths):
        target = (REPOSITORY_ROOT / relative).resolve()
        if REPOSITORY_ROOT not in target.parents or not target.is_file():
            raise SystemExit(f"V4 allowlisted file missing/outside repository: {relative}")
        rows.append({"path": relative.replace("\\", "/"), "sha256": sha256(target)})

    sys.path.insert(0, str(REPOSITORY_ROOT / "outputs/ns4a_v2_integrated_runner_v1"))
    from qshift_ns4a_v2_runner.integrity import runtime_fingerprint

    payload = {
        "schema": "qshift-ns4a-v2-source-manifest-v1",
        "readiness_revision": "NS-4A V2 final-readiness V4",
        "purpose": "final hardened implementation and deterministic validation provenance; no experiment authorization",
        "source_base_commit": "79ac849dc0295cfd702c3e53f131e30f1e306425",
        "supersedes_source_manifest_v3_sha256": EXPECTED_V3_MANIFEST_SHA256,
        "file_count": len(rows),
        "files": rows,
        "environment": runtime_fingerprint(),
        "sampling_authorized": False,
        "sampling_performed": False,
        "numeric_production_seeds_allocated": False,
        "benchmark_seed_values_allocated": False,
        "manifest_self_hash": "excluded by design",
        "final_readiness_report": "excluded by design; this report records the V4 manifest digest",
    }
    encoded = json.dumps(payload, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"
    OUTPUT.write_bytes(encoded)
    print(json.dumps({"status": "PASS", "path": str(OUTPUT), "sha256": hashlib.sha256(encoded).hexdigest(),
                      "verified_input_files": len(rows), "sampling_performed": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
