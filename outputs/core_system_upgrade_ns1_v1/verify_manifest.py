"""Verify the NS-1 engineering manifest without sampling or changing data."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in {".py", ".md", ".json", ".txt"}:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def verify() -> dict:
    manifest = json.loads((HERE / "NS1_ENGINEERING_MANIFEST_V2.json").read_text(encoding="utf-8"))
    mismatches = []
    for item in manifest["files"]:
        path = ROOT / item["path"]
        size = -1
        if path.is_file():
            data = path.read_bytes()
            if path.suffix.lower() in {".py", ".md", ".json", ".txt"}:
                data = data.replace(b"\r\n", b"\n")
            size = len(data)
        if not path.is_file() or size != item["bytes"] or sha256(path) != item["sha256"]:
            mismatches.append(item["path"])
    return {
        "manifest_entries": len(manifest.get("files", [])),
        "mismatches": mismatches,
        "base_commit_recorded": manifest.get("branch_base_commit"),
        "sampling_performed": manifest.get("sampling_performed"),
        "training_performed": manifest.get("training_performed"),
        "search_output_contained_protected_outcome_content": manifest.get(
            "search_output_contained_protected_outcome_content"),
        "complete_protected_non_access_established": manifest.get("complete_protected_non_access_established"),
        "accessed_file_inventory": manifest.get("accessed_file_inventory"),
        "evidence_scope_deviation_disclosed": manifest.get("evidence_scope_deviation_disclosed"),
        "passed": not mismatches and manifest.get("sampling_performed") is False
        and manifest.get("training_performed") is False
        and manifest.get("search_output_contained_protected_outcome_content") is False
        and manifest.get("complete_protected_non_access_established") is False
        and manifest.get("accessed_file_inventory") == "unknown; see NS1_EVIDENCE_SCOPE_INCIDENT_REPORT.md"
        and manifest.get("evidence_scope_deviation_disclosed") is True,
    }


def main() -> None:
    result = verify()
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
