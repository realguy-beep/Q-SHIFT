"""Verify this package's file hashes and its read-only V7 source reference."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
MANIFEST_PATH = PACKAGE_ROOT / "SOURCE_HASH_MANIFEST.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_record(path: Path, row: dict[str, Any]) -> bool:
    raw = path.read_bytes()
    clean = raw.replace(b"\r\n", b"\n")
    raw_ok = (
        len(raw) == row.get("size_bytes")
        and hashlib.sha256(raw).hexdigest() == row.get("sha256")
    )
    blob_size = row.get("git_blob_size_bytes", len(clean))
    blob_sha = row.get("git_blob_sha256", row.get("sha256"))
    clean_ok = (
        len(clean) == blob_size
        and hashlib.sha256(clean).hexdigest() == blob_sha
    )
    return raw_ok or clean_ok


def verify(manifest_path: Path = MANIFEST_PATH) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "qshift-ns4a-v2-engineering-corrections-v1":
        raise ValueError("unsupported source manifest schema")
    records = manifest.get("package_files")
    if not isinstance(records, list) or not records:
        raise ValueError("manifest package_files must be a nonempty list")
    seen: set[str] = set()
    for row in records:
        relative = row.get("path")
        if not isinstance(relative, str) or relative in seen:
            raise ValueError("manifest path is missing or duplicated")
        seen.add(relative)
        path = (PACKAGE_ROOT / relative).resolve()
        if PACKAGE_ROOT not in path.parents or not path.is_file():
            raise ValueError(f"manifest path is absent or escapes package: {relative}")
        if not _verify_record(path, row):
            raise ValueError(f"package source hash mismatch: {relative}")
    external = manifest.get("read_only_reference_files", [])
    for row in external:
        relative = row.get("path")
        path = (REPOSITORY_ROOT / relative).resolve()
        if REPOSITORY_ROOT not in path.parents or not path.is_file():
            raise ValueError(f"reference path is absent or escapes repository: {relative}")
        if not _verify_record(path, row):
            raise ValueError(f"read-only reference changed: {relative}")
    return {
        "status": "PASS",
        "package_file_count": len(records),
        "reference_file_count": len(external),
        "manifest_self_hash": "excluded",
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
