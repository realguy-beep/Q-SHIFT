"""Finalize the bounded neural-collapse audit without generating new samples."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OLD_MANIFEST = ROOT / "outputs/neural_decoder_diagnostic/structured_integration/FINAL_MANIFEST.json"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    old = json.loads(OLD_MANIFEST.read_text(encoding="utf-8"))
    entries = old["files"]
    checked, mismatches, missing = [], [], []
    for item in entries:
        path = ROOT / item["path"]
        if not path.is_file():
            missing.append(item["path"])
            continue
        current = sha(path)
        row = {"path": item["path"], "historical_sha256": item["sha256"],
               "current_sha256": current, "historical_bytes": item.get("bytes"),
               "current_bytes": path.stat().st_size}
        checked.append(row)
        if current != item["sha256"]:
            mismatches.append(row)

    expected = {"dashboard/structured_training.py", "dashboard/tests/test_structured_training.py"}
    actual = {m["path"] for m in mismatches}
    if missing or actual != expected:
        raise SystemExit(f"Unexpected historical integrity state: missing={missing}, mismatches={sorted(actual)}")

    correction = {
        "status": "intentional prospective correction; historical artifacts preserved",
        "reason": "Correct positive-weighted BCE logit odds shift before interpreting outputs as natural probabilities; add inference and historical-checkpoint regression coverage.",
        "changed_files": mismatches,
        "all_other_historical_manifest_entries_match": len(entries) - len(mismatches),
        "current_source_sha256": {m["path"]: m["current_sha256"] for m in mismatches},
        "historical_manifest_path": str(OLD_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "historical_manifest_sha256": sha(OLD_MANIFEST),
    }
    (HERE / "SOURCE_CORRECTION.json").write_text(json.dumps(correction, indent=2) + "\n", encoding="utf-8")

    preservation = {
        "status": "PASS_WITH_DOCUMENTED_SOURCE_CORRECTION",
        "historical_entries": len(entries), "matched": len(entries) - len(mismatches),
        "expected_source_or_test_hash_changes": mismatches, "unexpected_mismatches": [],
        "missing": [], "historical_data_or_result_changes": [],
        "note": "The original manifest was verified 71/71 before the correction. Current mismatches are only the training implementation and its direct regression tests; result/data/checkpoint files retain their historical hashes.",
    }
    (HERE / "HISTORICAL_PRESERVATION_AUDIT.json").write_text(json.dumps(preservation, indent=2) + "\n", encoding="utf-8")

    listed = []
    for item in entries:
        path = ROOT / item["path"]
        listed.append({"path": item["path"], "sha256": sha(path), "bytes": path.stat().st_size,
                       "historical_sha256": item["sha256"],
                       "status": "intentional_source_correction" if item["path"] in expected else "matches_historical_manifest"})
    # Include every generated evidence artifact in this audit, excluding caches and the manifest itself.
    for path in sorted(HERE.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.name == "MANIFEST.json":
            continue
        rel = path.relative_to(ROOT).as_posix()
        if any(row["path"] == rel for row in listed):
            continue
        listed.append({"path": rel, "sha256": sha(path), "bytes": path.stat().st_size,
                       "status": "new_root_cause_evidence"})
    listed.extend([
        {"path": "dashboard/structured_training.py", "sha256": sha(ROOT / "dashboard/structured_training.py"), "bytes": (ROOT / "dashboard/structured_training.py").stat().st_size, "status": "current_corrected_source"},
        {"path": "dashboard/tests/test_structured_training.py", "sha256": sha(ROOT / "dashboard/tests/test_structured_training.py"), "bytes": (ROOT / "dashboard/tests/test_structured_training.py").stat().st_size, "status": "current_regression_tests"},
    ])
    manifest = {"manifest_version": 1, "purpose": "Root cause audit evidence and explicit preservation audit; excludes generated runtime caches.",
                "historical_manifest": {"path": correction["historical_manifest_path"], "sha256": correction["historical_manifest_sha256"], "entries": len(entries)},
                "historical_integrity": {"matched": len(entries) - len(mismatches), "documented_source_changes": sorted(actual), "missing": missing},
                "files": listed}
    (HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    audit_failures = [row["path"] for row in listed if sha(ROOT / row["path"]) != row["sha256"]]
    if audit_failures:
        raise SystemExit(f"New evidence manifest verification failed: {audit_failures}")
    print(json.dumps({"historical_entries": len(entries), "matched": len(entries)-len(mismatches),
                      "documented_changes": sorted(actual), "missing": missing,
                      "new_audit_files": len(listed)-len(entries),
                      "current_manifest_files_verified": len(listed)}, indent=2))


if __name__ == "__main__":
    main()
