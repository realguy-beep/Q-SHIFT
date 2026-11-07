"""Hash Phase 3A outputs and independently recheck historical manifests."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
REPAIR = REPO / "outputs/phase3a_controller_repair"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    auto = REPO / "outputs/neural_decoder_diagnostic/autonomous_development"
    auto_run = auto / "run"
    auto_progress = json.loads((auto_run / "progress.json").read_text(encoding="utf-8"))
    auto_manifest_path = auto_run / "RUN_MANIFEST.json"
    auto_manifest = json.loads(auto_manifest_path.read_text(encoding="utf-8"))
    auto_entries = []
    for rel, expected in sorted(auto_manifest["file_sha256"].items()):
        path = auto_run / Path(rel)
        actual = sha(path) if path.is_file() else None
        status = "PASS" if actual == expected else "MISMATCH"
        classification = ""
        if rel == "controller.stdout.log" and expected == hashlib.sha256(b"").hexdigest():
            try:
                stdout_status = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                stdout_status = {}
            if actual and stdout_status.get("status") == "completed" and stdout_status.get("independent_test_access") == 0:
                classification = "post-manifest status stdout; file was empty when RUN_MANIFEST was written"
                status = "EXPECTED_POST_MANIFEST_LOG"
        auto_entries.append({"path": rel, "expected_sha256": expected,
            "actual_sha256": actual, "status": status, "classification": classification})

    sprint = REPO / "outputs/neural_decoder_diagnostic/hybrid_residual_sprint_v1"
    sprint_run = sprint / "run"
    sprint_progress = json.loads((sprint_run / "PROGRESS.json").read_text(encoding="utf-8"))
    sprint_manifest_path = sprint / "post_run_audit/FINAL_EVIDENCE_MANIFEST.json"
    sprint_manifest = json.loads(sprint_manifest_path.read_text(encoding="utf-8"))
    sprint_entries = []
    for entry in sprint_manifest["files"]:
        path = REPO / Path(entry["path"])
        actual = sha(path) if path.is_file() else None
        status = "PASS" if actual == entry["sha256"] and path.stat().st_size == entry["bytes"] else "MISMATCH"
        sprint_entries.append({"path": entry["path"], "expected_sha256": entry["sha256"],
            "actual_sha256": actual, "expected_bytes": entry["bytes"],
            "actual_bytes": path.stat().st_size if path.is_file() else None, "status": status})

    history = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "independent_test_access": 0,
        "autonomous_750k": {
            "progress_status": auto_progress.get("status"),
            "completed_jobs": len(auto_progress.get("completed_jobs", [])),
            "test_access": auto_progress.get("independent_test_access"),
            "run_manifest_sha256": sha(auto_manifest_path),
            "entries": len(auto_entries),
            "matching_entries": sum(x["status"] == "PASS" for x in auto_entries),
            "expected_post_manifest_logs": sum(x["status"] == "EXPECTED_POST_MANIFEST_LOG" for x in auto_entries),
            "unexplained_mismatches": [x for x in auto_entries if x["status"] == "MISMATCH"],
            "entries_detail": auto_entries,
        },
        "hybrid_residual_sprint": {
            "progress_status_preserved": sprint_progress.get("status"),
            "completed_jobs": len(sprint_progress.get("completed_jobs", [])),
            "prior_audit_manifest_sha256": sha(sprint_manifest_path),
            "entries": len(sprint_entries),
            "matching_entries": sum(x["status"] == "PASS" for x in sprint_entries),
            "mismatches": [x for x in sprint_entries if x["status"] != "PASS"],
            "entries_detail": sprint_entries,
        },
    }
    (HERE / "HISTORICAL_PRESERVATION_AUDIT.json").write_text(
        json.dumps(history, indent=2) + "\n", encoding="utf-8")

    output_files = []
    for root in (REPAIR, HERE):
        for path in root.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            if path.name == "PHASE3A_MANIFEST.json":
                continue
            output_files.append(path)
    records = []
    for path in sorted(set(output_files), key=lambda x: str(x).lower()):
        records.append({"path": path.relative_to(REPO).as_posix(),
                        "bytes": path.stat().st_size, "sha256": sha(path)})
    manifest = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "Q-SHIFT Phase 3A preflight and controller repair",
        "status": "diagnostic_preflight_passed; Phase3B_not_executed",
        "independent_test_access": 0,
        "production_shots": 0,
        "formal_diagnostic_shots": {"draws": 2880, "distinct_records": 2592},
        "historical_preservation_audit": "outputs/phase3a_correlated_noise_preflight/HISTORICAL_PRESERVATION_AUDIT.json",
        "manifest_self_hash_excluded": True,
        "files_hashed": len(records),
        "files": records,
    }
    (HERE / "PHASE3A_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "phase3a_files_hashed": len(records),
        "historical_750k_entries": len(auto_entries),
        "historical_750k_explained_post_manifest_logs": history["autonomous_750k"]["expected_post_manifest_logs"],
        "historical_750k_unexplained_mismatches": len(history["autonomous_750k"]["unexplained_mismatches"]),
        "historical_sprint_entries": len(sprint_entries),
        "historical_sprint_mismatches": len(history["hybrid_residual_sprint"]["mismatches"]),
        "independent_test_access": 0}, indent=2))


if __name__ == "__main__":
    main()
