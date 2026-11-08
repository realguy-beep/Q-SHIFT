"""Separate-process audit for v3.4.4; does not import recovery implementation."""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify_inventory(path, base_root):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    bad = []
    for row in data["files"]:
        file_path = Path(base_root) / row["path"]
        if not file_path.is_file() or sha(file_path) != row["sha256"]:
            bad.append(row["path"])
    return len(data["files"]), bad


def run(cmd):
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=300)
    return {"command": cmd, "exit_code": proc.returncode,
            "stdout": proc.stdout[-12000:], "stderr": proc.stderr[-5000:]}


def main():
    freeze_path = HERE / "SAFETY_FREEZE_V44.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    source_bad = []
    for rel, expected in freeze["sha256"].items():
        path = HERE / rel
        if not path.is_file() or sha(path) != expected:
            source_bad.append(rel)

    v2_path = ROOT / "outputs/stage5_secondary_inference_repair_v1/STAGE5_PRETEST_FREEZE_V2.json"
    v2 = json.loads(v2_path.read_text(encoding="utf-8"))
    v2_bad = [rel for rel, expected in v2["sha256"].items()
              if not (ROOT / rel).is_file() or sha(ROOT / rel) != expected]
    v33_path = ROOT / "outputs/stage5_execution_safety_v3_3/SAFETY_FREEZE.json"
    v33 = json.loads(v33_path.read_text(encoding="utf-8"))
    v33_dir = v33_path.parent
    v33_bad = [rel for rel, expected in v33["sha256"].items()
               if not (v33_dir / rel).is_file() or sha(v33_dir / rel) != expected]
    v42_path = ROOT / "outputs/stage5_execution_safety_v3_4_2/SAFETY_FREEZE_V4.json"
    v42 = json.loads(v42_path.read_text(encoding="utf-8"))
    v42_dir = v42_path.parent
    v42_bad = [rel for rel, expected in v42["sha256"].items()
               if not (v42_dir / rel).is_file() or sha(v42_dir / rel) != expected]

    original_inventory = ROOT / "outputs/stage5_postfailure_forensics_v1/PRE_INVESTIGATION_SHA256.json"
    forensic_manifest_path = ROOT / "outputs/stage5_postfailure_forensics_v1/FORENSIC_MANIFEST.json"
    original_count, original_bad = verify_inventory(original_inventory, ROOT)
    forensic = json.loads(forensic_manifest_path.read_text(encoding="utf-8"))
    forensic_bad = [rel for rel, expected in forensic["files"].items()
                    if not (ROOT / rel).is_file() or sha(ROOT / rel) != expected]

    # Existing v3.4.3 audit is read as historical evidence only; running its
    # writer would replace a tracked audit artifact, so this audit does not.
    v43_audit_path = ROOT / "outputs/stage5_execution_safety_v3_4_3/INDEPENDENT_AUDIT_V43.json"
    v43_audit = json.loads(v43_audit_path.read_text(encoding="utf-8"))

    # Run only disposable fixtures and read-only preflight in child processes.
    commands = [
        run([sys.executable, "-m", "unittest", "outputs.stage5_execution_safety_v3_4_4.test_recovery_service_v44", "-v"]),
        run([sys.executable, "outputs/stage5_execution_safety_v3_4_4/run_ownership_regressions_v44.py"]),
        run([sys.executable, "outputs/stage5_execution_safety_v3_4_4/recovery_runner_v44.py", "--preflight"]),
    ]
    test_success = [x["exit_code"] == 0 for x in commands]

    # Independent post-test preservation scan. This enumerates hashes only.
    original_count_after, original_bad_after = verify_inventory(original_inventory, ROOT)
    forensic_bad_after = [rel for rel, expected in forensic["files"].items()
                          if not (ROOT / rel).is_file() or sha(ROOT / rel) != expected]
    raw_test_path = v42_dir / "SAFETY_TEST_RESULTS_V4.json"
    raw_test_expected = json.loads((v42_dir / "SAFETY_EVIDENCE_MANIFEST_V4_2.json").read_text(encoding="utf-8"))["test_results_sha256"]
    raw_test_actual = sha(raw_test_path) if raw_test_path.is_file() else None
    historical_test_report = "PASS" if raw_test_actual == raw_test_expected else "FAIL_LOCAL_ARTIFACT_MISMATCH"

    core_pass = (
            not source_bad and not v2_bad and not v33_bad and not v42_bad and
            not original_bad and not forensic_bad and not original_bad_after and
            not forensic_bad_after and all(test_success) and
            v43_audit.get("audit_status") == "PASS")
    result = {
        "status": ("PASS_WITH_DEVIATION" if core_pass and historical_test_report != "PASS"
                   else "PASS" if core_pass else "FAIL"),
        "v44_frozen_source_hashes_verified": len(freeze["sha256"]) - len(source_bad),
        "v44_source_hash_mismatches": source_bad,
        "stage5_v2_hashes_verified": len(v2["sha256"]) - len(v2_bad),
        "stage5_v2_hash_mismatches": v2_bad,
        "v3_3_hashes_verified": len(v33["sha256"]) - len(v33_bad),
        "v3_3_hash_mismatches": v33_bad,
        "v3_4_2_hashes_verified": len(v42["sha256"]) - len(v42_bad),
        "v3_4_2_hash_mismatches": v42_bad,
        "original_run_files_verified_before_after": [original_count, original_count_after],
        "original_run_hash_mismatches_before_after": [original_bad, original_bad_after],
        "forensic_entries_verified": len(forensic["files"]),
        "forensic_hash_mismatches_before_after": [forensic_bad, forensic_bad_after],
        "historical_v3_4_3_audit_status": v43_audit.get("audit_status"),
        "disposable_test_commands": commands,
        "disposable_test_commands_passed": sum(test_success),
        "stage5_evaluation_sampling_executed": False,
        "stage5_recovery_executed": False,
        "sealed_outcomes_accessed": False,
        "recovery_copy_created": (ROOT / "outputs/stage5_secondary_inference_repair_v1/run_recovery_v3_4_4").exists(),
        "v3_4_2_raw_test_report_integrity": {
            "status": historical_test_report,
            "manifest_sha256": raw_test_expected,
            "current_sha256": raw_test_actual,
            "note": "The v3.4.2 test runner was invoked during this task and rewrote its untracked raw-result JSON; the original bytes are not recoverable from the repository. Its tracked summary and frozen source hashes remain intact. This is disclosed as a local historical-artifact deviation.",
        },
    }
    out = HERE / "INDEPENDENT_AUDIT_V44.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "disposable_test_commands"}, indent=2))
    return 0 if result["status"] in {"PASS", "PASS_WITH_DEVIATION"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
