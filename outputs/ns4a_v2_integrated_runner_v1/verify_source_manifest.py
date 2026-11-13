"""Independently verify the NS-4A integrated source hash inventory."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


PACKAGE_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_DIR.parents[1]
sys.path.insert(0, str(PACKAGE_DIR))
from build_source_manifest import (  # noqa: E402
    DETERMINISTIC_MODULES, DETERMINISTIC_TESTS, FIXED_FILES,
    INTEGRATED_MODULES, INTEGRATED_TESTS,
)
from qshift_ns4a_v2_runner.integrity import runtime_fingerprint  # noqa: E402


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def expected_paths() -> set[str]:
    paths = set(FIXED_FILES)
    paths.update(
        f"outputs/ns4a_v2_deterministic_implementation_v1/qshift_ns4a_v2_deterministic/{name}"
        for name in DETERMINISTIC_MODULES
    )
    paths.update(
        f"outputs/ns4a_v2_deterministic_implementation_v1/tests/{name}"
        for name in DETERMINISTIC_TESTS
    )
    paths.update(
        f"outputs/ns4a_v2_integrated_runner_v1/qshift_ns4a_v2_runner/{name}"
        for name in INTEGRATED_MODULES
    )
    paths.update(
        f"outputs/ns4a_v2_integrated_runner_v1/tests/{name}"
        for name in INTEGRATED_TESTS
    )
    return paths


def main() -> int:
    manifest_path = PACKAGE_DIR / "SOURCE_HASH_MANIFEST_V2.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema") != "qshift-ns4a-v2-integrated-source-manifest-v1":
        raise SystemExit("unsupported source manifest schema")
    rows = payload.get("files")
    if not isinstance(rows, list) or len(rows) != payload.get("file_count"):
        raise SystemExit("source manifest row count is incomplete")
    paths = [row.get("path") for row in rows if isinstance(row, dict)]
    if len(paths) != len(rows) or set(paths) != expected_paths() or len(paths) != len(set(paths)):
        raise SystemExit("source manifest does not match the explicit allowlist")
    for row in rows:
        target = (REPOSITORY_ROOT / row["path"]).resolve()
        if REPOSITORY_ROOT not in target.parents or not target.is_file() or digest(target) != row.get("sha256"):
            raise SystemExit(f"source hash verification failed: {row.get('path')}")
    runtime = runtime_fingerprint()
    env = payload.get("environment", {})
    expected_env = {
        "python": runtime["python"],
        "locked_distribution_count": runtime["locked_distribution_count"],
        "distributions": runtime["distributions"],
        "dependency_lock_sha256": runtime["dependency_lock_sha256"],
        "beliefmatching_upstream_commit": runtime["beliefmatching_upstream_commit"],
        "beliefmatching_provenance_kind": runtime["beliefmatching_provenance_kind"],
        "beliefmatching_core_source_sha256_lf": runtime["beliefmatching_core_source_sha256_lf"],
    }
    if env != expected_env or payload.get("sampling_authorized") is not False or payload.get("sampling_performed") is not False:
        raise SystemExit("environment identity or sampling boundary differs from the recorded source manifest")
    print(json.dumps({"status": "PASS", "verified_files": len(rows),
                      "manifest_sha256": digest(manifest_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
