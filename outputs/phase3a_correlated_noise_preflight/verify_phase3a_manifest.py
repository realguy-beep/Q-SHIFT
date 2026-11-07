"""Independent verifier for the Phase 3A evidence manifest.

Does not read historical experiment samples. It rehashes only the paths
explicitly listed in PHASE3A_MANIFEST.json and checks the preservation audit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    manifest_path = HERE / "PHASE3A_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = []
    checked = 0
    for entry in manifest["files"]:
        path = REPO / Path(entry["path"])
        checked += 1
        if not path.is_file():
            errors.append({"path": entry["path"], "reason": "missing"})
            continue
        actual_bytes = path.stat().st_size
        actual_hash = sha256(path)
        if actual_bytes != entry["bytes"] or actual_hash != entry["sha256"]:
            errors.append({"path": entry["path"], "reason": "size_or_sha256_mismatch",
                           "expected_bytes": entry["bytes"], "actual_bytes": actual_bytes,
                           "expected_sha256": entry["sha256"], "actual_sha256": actual_hash})

    hist_path = HERE / "HISTORICAL_PRESERVATION_AUDIT.json"
    hist = json.loads(hist_path.read_text(encoding="utf-8"))
    auto = hist["autonomous_750k"]
    sprint = hist["hybrid_residual_sprint"]
    historical_ok = (
        auto["progress_status"] == "completed"
        and auto["completed_jobs"] == 50
        and auto["test_access"] == 0
        and auto["matching_entries"] == 376
        and auto["expected_post_manifest_logs"] == 1
        and not auto["unexplained_mismatches"]
        and sprint["progress_status_preserved"] == "failed"
        and sprint["completed_jobs"] == 30
        and sprint["matching_entries"] == 292
        and not sprint["mismatches"]
        and hist["independent_test_access"] == 0
    )
    if not historical_ok:
        errors.append({"path": "HISTORICAL_PRESERVATION_AUDIT.json",
                       "reason": "historical_status_or_integrity_check_failed"})

    result = {
        "status": "PASS" if not errors else "FAIL",
        "manifest_entries_checked": checked,
        "manifest_sha256": sha256(manifest_path),
        "historical_audit_sha256": sha256(hist_path),
        "historical_preservation_checks_pass": historical_ok,
        "errors": errors,
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
