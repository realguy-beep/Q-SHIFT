"""Independently verify the V3 explicit file inventory and locked environment."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

PACKAGE_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_DIR.parents[1]
BASE_MANIFEST = REPOSITORY_ROOT / "outputs/ns4a_v2_integrated_runner_v1/SOURCE_HASH_MANIFEST_V2.json"
MANIFEST = PACKAGE_DIR / "SOURCE_HASH_MANIFEST_V3.json"
EXPECTED_V2_MANIFEST_SHA256 = "897ba2e57622be52c93c2a73859ef087688aea3472f86c7feb42b91a4c1e7f49"
ADDITIONAL_PATHS = {
    "outputs/ns4a_v2_integrated_runner_v1/qshift_ns4a_v2_runner/benchmark.py",
    "outputs/ns4a_v2_integrated_runner_v1/tests/test_benchmark_readiness.py",
    "outputs/ns4a_v2_final_readiness_v1/BENCHMARK_PROTOCOL.json",
    "outputs/ns4a_v2_final_readiness_v1/BENCHMARK_SEED_INVENTORY_TEMPLATE.json",
    "outputs/ns4a_v2_final_readiness_v1/CANDIDATE_EXECUTION_MANIFEST_SCHEMA_V1.json",
    "outputs/ns4a_v2_final_readiness_v1/DETERMINISTIC_REHEARSAL_VALIDATION.json",
    "outputs/ns4a_v2_final_readiness_v1/SEED_AND_COLLISION_SCREENING.md",
    "outputs/ns4a_v2_final_readiness_v1/build_source_manifest_v3.py",
    "outputs/ns4a_v2_final_readiness_v1/verify_source_manifest_v3.py",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    base = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
    recorded = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected_paths = {row["path"] for row in base["files"]} | ADDITIONAL_PATHS
    rows = recorded.get("files")
    paths = [row.get("path") for row in rows] if isinstance(rows, list) else []
    if (recorded.get("schema") != "qshift-ns4a-v2-source-manifest-v1"
            or recorded.get("readiness_revision") != "NS-4A V2 final-readiness V3"
            or set(paths) != expected_paths or len(paths) != len(expected_paths)
            or recorded.get("file_count") != len(expected_paths)
            or digest(BASE_MANIFEST) != EXPECTED_V2_MANIFEST_SHA256
            or recorded.get("supersedes_source_manifest_v2_sha256") != EXPECTED_V2_MANIFEST_SHA256):
        raise SystemExit("V3 manifest schema, exact allowlist, or historical base-manifest digest failed")
    for row in rows:
        target = (REPOSITORY_ROOT / row["path"]).resolve()
        if REPOSITORY_ROOT not in target.parents or not target.is_file() or digest(target) != row.get("sha256"):
            raise SystemExit(f"V3 file hash failed: {row.get('path')}")
    sys.path.insert(0, str(REPOSITORY_ROOT / "outputs/ns4a_v2_integrated_runner_v1"))
    from qshift_ns4a_v2_runner.integrity import runtime_fingerprint

    if recorded.get("environment") != runtime_fingerprint():
        raise SystemExit("V3 locked environment fingerprint changed")
    for field in ("sampling_authorized", "sampling_performed", "numeric_production_seeds_allocated", "benchmark_seed_values_allocated"):
        if recorded.get(field) is not False:
            raise SystemExit(f"V3 boundary field {field} is not false")
    print(json.dumps({"status": "PASS", "verified_files": len(rows), "manifest_sha256": digest(MANIFEST),
                      "sampling_performed": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
