"""Independent verification of v3.4.3 freeze, tests, and historical immutability.

This file intentionally does not import atomic_safety_v43 or recovery_v43.
It recomputes file hashes and reruns the disposable subprocess test suite.
"""
from __future__ import annotations
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FREEZE = HERE / "SAFETY_FREEZE_V43_2.json"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify_hash_map(path, base, count):
    obj = json.loads(path.read_text(encoding="utf-8"))
    rows = obj.get("sha256")
    if not isinstance(rows, dict) or len(rows) != count:
        raise AssertionError(f"wrong frozen hash count for {path}")
    mismatches = []
    for rel, expected in rows.items():
        file_path = base / rel
        if not file_path.is_file() or sha(file_path) != expected:
            mismatches.append(rel)
    return {"declared": len(rows), "verified": len(rows) - len(mismatches), "mismatches": mismatches}


def verify_original_evidence():
    snapshot_path = ROOT / "outputs/stage5_postfailure_forensics_v1/PRE_INVESTIGATION_SHA256.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    rows = snapshot.get("files", [])
    modified, missing = [], []
    for row in rows:
        path = ROOT / row["path"]
        if not path.is_file():
            missing.append(row["path"])
            continue
        if path.stat().st_size != row["size_bytes"] or sha(path) != row["sha256"]:
            modified.append(row["path"])
    forensic_path = ROOT / "outputs/stage5_postfailure_forensics_v1/FORENSIC_MANIFEST.json"
    forensic = json.loads(forensic_path.read_text(encoding="utf-8"))
    forensic_bad = []
    for rel, expected in forensic.get("files", {}).items():
        if not (ROOT / rel).is_file() or sha(ROOT / rel) != expected:
            forensic_bad.append(rel)
    return {
        "preinvestigation_inventory_declared": snapshot.get("file_count"),
        "preinvestigation_inventory_verified": len(rows) - len(modified) - len(missing),
        "preinvestigation_modified": modified,
        "preinvestigation_missing": missing,
        "preinvestigation_inventory_sha256": sha(snapshot_path),
        "forensic_manifest_declared": len(forensic.get("files", {})),
        "forensic_manifest_verified": len(forensic.get("files", {})) - len(forensic_bad),
        "forensic_manifest_mismatches": forensic_bad,
        "preserved": (len(rows) == 265 and not modified and not missing and not forensic_bad),
    }


def verify_no_sampler_api():
    source_path = HERE / "recovery_v43.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = []
    sample_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name.lower() for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append((node.module or "").lower())
        elif isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Attribute) and fn.attr.lower() in {"sample", "compile_detector_sampler"}:
                sample_calls.append(fn.attr)
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "complete_evaluation_checkpoint"]
    if len(functions) != 1:
        return {"passed": False, "reason": "recovery completion function not uniquely found"}
    fn = functions[0]
    args = [arg.arg for arg in fn.args.args]
    serialized = ast.dump(fn, include_attributes=False)
    passed = (not any("stim" in module for module in imported) and not sample_calls
              and "sampler" not in args
              and "estimate_fn" in serialized and "decode_fn" in serialized
              and "calibration_detectors" in serialized and "evaluation_detectors" in serialized
              and "observables" not in " ".join(args))
    # Explicitly assert estimator/decode callbacks receive detector arrays only.
    calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id in {"estimate_fn", "decode_fn", "prediction_verifier"}]
    inputs = [ast.dump(arg, include_attributes=False) for call in calls for arg in call.args]
    labels_passed = any("observables" in arg or "labels" in arg for arg in inputs)
    return {"passed": passed and not labels_passed, "sampler_calls": sample_calls,
            "stim_imported": any("stim" in module for module in imported),
            "callback_label_arguments": labels_passed,
            "complete_function_arguments": args}


def run_tests_independently():
    command = [sys.executable, "-m", "unittest", "-v",
               "outputs.stage5_execution_safety_v3_4_3.test_recovery_v43"]
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=180)
    output = proc.stdout + proc.stderr
    count_match = re.search(r"Ran (\d+) tests?", output)
    tests = re.findall(r"^(test_[A-Za-z0-9_]+) \(.*\) \.\.\. (ok|FAIL|ERROR|skipped.*)$", output, re.M)
    return {"command": "python -m unittest -v outputs.stage5_execution_safety_v3_4_3.test_recovery_v43",
            "exit_code": proc.returncode, "test_count": int(count_match.group(1)) if count_match else None,
            "tests_reported": len(tests), "test_records": [{"name": a, "status": b} for a, b in tests],
            "passed": proc.returncode == 0 and count_match is not None and "OK" in output,
            "output": output[-6000:]}


def main():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    superseded_freeze = HERE / "SAFETY_FREEZE_V43_1.json"
    superseded_hash_ok = superseded_freeze.is_file() and sha(superseded_freeze) == freeze.get("superseded_freeze_sha256")
    previous = json.loads(superseded_freeze.read_text(encoding="utf-8")) if superseded_hash_ok else {}
    chain_hash_ok = (superseded_hash_ok and previous.get("supersedes") == "SAFETY_FREEZE_V43.json"
                     and sha(HERE / "SAFETY_FREEZE_V43.json") == previous.get("superseded_freeze_sha256"))
    source_hash_checks = {}
    for rel, expected in freeze["new_sources_and_configuration_sha256"].items():
        path = HERE / rel
        source_hash_checks[rel] = path.is_file() and sha(path) == expected
    historical = {
        "stage5_v2_53": verify_hash_map(ROOT / "outputs/stage5_secondary_inference_repair_v1/STAGE5_PRETEST_FREEZE_V2.json", ROOT, 53),
        "stage5_v3_3_13": verify_hash_map(ROOT / "outputs/stage5_execution_safety_v3_3/SAFETY_FREEZE.json", ROOT / "outputs/stage5_execution_safety_v3_3", 13),
        "stage5_v3_4_2_14": verify_hash_map(ROOT / "outputs/stage5_execution_safety_v3_4_2/SAFETY_FREEZE_V4.json", ROOT / "outputs/stage5_execution_safety_v3_4_2", 14),
    }
    original = verify_original_evidence()
    status = json.loads((ROOT / "outputs/stage5_secondary_inference_repair_v1/run/status.json").read_text(encoding="utf-8"))
    inflight = json.loads((ROOT / "outputs/stage5_postfailure_forensics_v1/INFLIGHT_ROOT_AUDIT.json").read_text(encoding="utf-8"))
    seed_inventory = json.loads((ROOT / "outputs/stage5_secondary_inference_repair_v1/STAGE5_SAMPLE_SEED_INVENTORY.json").read_text(encoding="utf-8"))
    cfg = json.loads((HERE / "V43_SAFETY_CONFIG.json").read_text(encoding="utf-8"))
    reserved = {int(row["seed"]) for row in seed_inventory["streams"]}
    fixture_seeds = set(map(int, cfg["test_fixtures"]["fixture_seed_ids"] + cfg["test_fixtures"]["fixture_numpy_rng_ids"]))
    collisions = len(reserved & fixture_seeds)
    no_sampler = verify_no_sampler_api()
    tests = run_tests_independently()
    recorded_tests = json.loads((HERE / "TEST_RESULTS_V43.json").read_text(encoding="utf-8"))
    recorded_test_summary_ok = (
        recorded_tests.get("status") == "PASS"
        and recorded_tests.get("fixtures_disposable_only") is True
        and recorded_tests.get("stage5_sampling_performed") is False
        and recorded_tests.get("test_count") == tests.get("test_count")
        and recorded_tests.get("exit_code") == 0
    )
    results = {
        "audit_status": "PASS" if (
            all(source_hash_checks.values())
            and chain_hash_ok
            and all(item["verified"] == item["declared"] and not item["mismatches"] for item in historical.values())
            and original["preserved"] and status.get("status") == "worker_failed"
            and inflight.get("audit_status") == "PASS_INFLIGHT_IDENTITY"
            and collisions == 0 and no_sampler["passed"] and tests["passed"]
            and recorded_test_summary_ok
            and tests["test_count"] == tests["tests_reported"]
        ) else "FAIL",
        "base_commit": "8c06750808582137f6a81e2170ad702a552594fb",
        "source_hash_checks": source_hash_checks,
        "superseded_freeze_chain_verified": chain_hash_ok,
        "historical_freeze_checks": historical,
        "original_evidence": original,
        "original_stage5_run_state": {
            "status": status.get("status"),
            "completed_roots": status.get("completed_roots"),
            "status_accounted_shots": status.get("unique_shots_generated"),
            "forensic_archived_rows": inflight.get("array_rows_persisted"),
            "forensic_partial_root_phase": inflight.get("in_flight_archive_phase"),
            "stage5_shots_generated_by_v43": 0,
            "recovery_executed": False,
            "full_study_statistics_run": False,
        },
        "fixture_seed_collision_audit": {
            "historical_reserved_values_screened": len(reserved),
            "benchmark_fixture_identifiers_screened": len(fixture_seeds),
            "collisions": collisions,
            "seed_values_emitted": False,
        },
        "no_sampling_code_audit": no_sampler,
        "recorded_test_summary_matches_independent_rerun": recorded_test_summary_ok,
        "recorded_test_summary": {k: recorded_tests.get(k) for k in ("status", "test_count", "exit_code", "stage5_sampling_performed", "fixtures_disposable_only")},
        "independent_subprocess_test_run": tests,
        "audit_method": "separate implementation; no imports from atomic_safety_v43 or recovery_v43",
        "limitations": [
            "This is an independent scripted audit in the same workspace, not an external human or second-agent review.",
            "Repair primitives are not integrated into the frozen Stage 5 worker, supervisor, auditor, or finalizer.",
            "No production recovery or full-scale run was performed.",
        ],
    }
    out = HERE / "INDEPENDENT_AUDIT_V43.json"
    out.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"audit_status": results["audit_status"],
                      "historical_verified": {k: v["verified"] for k, v in historical.items()},
                      "original_files_verified": original["preinvestigation_inventory_verified"],
                      "forensic_files_verified": original["forensic_manifest_verified"],
                      "test_count": tests["test_count"], "fixture_seed_collisions": collisions,
                      "stage5_shots_generated_by_v43": 0}, sort_keys=True))
    return 0 if results["audit_status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
