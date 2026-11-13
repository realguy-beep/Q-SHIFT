"""Verify final V4 source hashes and compatibility with the execution loader."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

PACKAGE_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_DIR.parents[1]
BASE_MANIFEST = PACKAGE_DIR / "SOURCE_HASH_MANIFEST_V3.json"
MANIFEST = PACKAGE_DIR / "SOURCE_HASH_MANIFEST_V4.json"
EXPECTED_V3_MANIFEST_SHA256 = "277bcf663abff1d60aedda1ef5da04ecce5f5f77359598743dbaa642cb147d3b"
ADDITIONAL_PATHS = {
    "outputs/ns4a_v2_final_readiness_v1/SOURCE_HASH_MANIFEST_V3.json",
    "outputs/ns4a_v2_final_readiness_v1/build_source_manifest_v4.py",
    "outputs/ns4a_v2_final_readiness_v1/verify_source_manifest_v4.py",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    if digest(BASE_MANIFEST) != EXPECTED_V3_MANIFEST_SHA256:
        raise SystemExit("V3 historical manifest digest changed")
    base = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = {row["path"] for row in base["files"]} | ADDITIONAL_PATHS
    rows = payload.get("files")
    paths = [row.get("path") for row in rows] if isinstance(rows, list) else []
    if (payload.get("schema") != "qshift-ns4a-v2-source-manifest-v1"
            or payload.get("readiness_revision") != "NS-4A V2 final-readiness V4"
            or set(paths) != expected or len(paths) != len(expected)
            or payload.get("file_count") != len(expected)
            or payload.get("supersedes_source_manifest_v3_sha256") != EXPECTED_V3_MANIFEST_SHA256):
        raise SystemExit("V4 exact source allowlist or historical manifest binding failed")
    for row in rows:
        target = (REPOSITORY_ROOT / row["path"]).resolve()
        if REPOSITORY_ROOT not in target.parents or not target.is_file() or digest(target) != row.get("sha256"):
            raise SystemExit(f"V4 source hash failed: {row.get('path')}")
    sys.path.insert(0, str(REPOSITORY_ROOT / "outputs/ns4a_v2_integrated_runner_v1"))
    from qshift_ns4a_v2_runner.integrity import runtime_fingerprint

    if payload.get("environment") != runtime_fingerprint():
        raise SystemExit("V4 lock-matched environment fingerprint changed")
    for field in ("sampling_authorized", "sampling_performed", "numeric_production_seeds_allocated", "benchmark_seed_values_allocated"):
        if payload.get(field) is not False:
            raise SystemExit(f"V4 boundary field {field} must be false")
    print(json.dumps({"status": "PASS", "verified_files": len(rows), "manifest_sha256": digest(MANIFEST),
                      "sampling_performed": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
