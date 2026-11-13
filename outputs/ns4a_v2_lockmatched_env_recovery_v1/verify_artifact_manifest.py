from __future__ import annotations

import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
MANIFEST = OUT / "ARTIFACT_SHA256_MANIFEST.json"


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures = []
    expected = set(manifest.get("files", {}))
    for name, entry in manifest.get("files", {}).items():
        path = OUT / name
        if not path.is_file():
            failures.append({"path": name, "error": "missing"})
            continue
        data = path.read_bytes().replace(b"\r\n", b"\n")
        actual = hashlib.sha256(data).hexdigest()
        if actual != entry.get("sha256") or len(data) != entry.get("normalized_bytes"):
            failures.append({"path": name, "error": "hash_or_size_mismatch", "actual_sha256": actual})
    actual_files = {
        p.relative_to(OUT).as_posix()
        for p in OUT.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    permitted = expected | {MANIFEST.name}
    if actual_files != permitted:
        failures.append({
            "path": ".",
            "error": "artifact_allowlist_mismatch",
            "unexpected": sorted(actual_files - permitted),
            "missing_from_directory": sorted(permitted - actual_files),
        })
    if manifest.get("manifest_self_hash") != "excluded by design":
        failures.append({"path": MANIFEST.name, "error": "self_hash_exclusion_marker_missing"})
    if manifest.get("hash_convention") != "SHA-256 and byte count after CRLF-to-LF normalization":
        failures.append({"path": MANIFEST.name, "error": "hash_convention_missing_or_unexpected"})
    result = {
        "schema": "qshift-ns4a-v2-lockmatched-artifact-verification-v1",
        "listed_files": len(expected),
        "overall": "PASS" if not failures else "FAIL",
        "failures": failures,
        "manifest_self_hash_excluded": True,
    }
    print(json.dumps(result, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
