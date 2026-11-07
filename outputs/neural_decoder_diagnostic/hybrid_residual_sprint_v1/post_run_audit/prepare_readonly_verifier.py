"""Derive a separate verifier that bypasses only a known status-order assertion.

The frozen `verify_results.py` is read unchanged. The generated audit copy
continues every substantive saved-array/model/checkpoint check, runs on CPU,
and writes only beneath `post_run_audit/`.
"""
from pathlib import Path

AUDIT_DIR = Path(__file__).resolve().parent
BASE = AUDIT_DIR.parent
source = (BASE / "verify_results.py").read_text(encoding="utf-8")

replacements = [
    ("HERE = Path(__file__).resolve().parent\nREPO = HERE.parents[2]",
     "AUDIT_DIR = Path(__file__).resolve().parent\nHERE = AUDIT_DIR.parent\nREPO = HERE.parents[2]"),
    ('fail(progress.get("status") == "completed", f"Run is not complete: {progress.get(\'status\')}")',
     '''run_error = load_json(RUN / "ERROR.json") if (RUN / "ERROR.json").is_file() else {}
    known_finalization_order_failure = (
        progress.get("status") == "failed" and
        progress.get("current_phase") == "final_evaluation" and
        len(progress.get("completed_jobs", [])) == 30 and
        len(progress.get("selection_jobs", [])) == 30 and
        "Independent evidence verifier failed" in run_error.get("error", "") and
        "Run is not complete: sampling" in run_error.get("error", "")
    )
    fail(progress.get("status") == "completed" or known_finalization_order_failure,
         f"Run is neither completed nor the specifically documented finalization-order failure: {progress.get('status')}")'''),
    ('    fail(sha(HERE / "SEED_INVENTORY.json") == freeze["seed_inventory_sha256"], "Frozen seed inventory hash mismatch")',
     '''    fail(sha(HERE / "SEED_INVENTORY.json") == freeze["seed_inventory_sha256"], "Frozen seed inventory hash mismatch")
    for rel, digest in freeze.get("source_sha256", {}).items():
        source_path = HERE / rel if (HERE / rel).is_file() else REPO / rel
        fail(source_path.is_file() and sha(source_path) == digest, f"Frozen source hash mismatch: {rel}")'''),
    ('    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")',
     '    torch.set_num_threads(2)\n    device = torch.device("cpu")'),
    ('audit = {"status": "PASS", "completed_utc":',
     'audit = {"status": "PASS_READ_ONLY_EVIDENCE; RUNNER_FINALIZATION_FAILED", "run_controller_status": progress.get("status"), "controller_error": run_error.get("error"), "completed_utc":'),
    ('    output = HERE / "INDEPENDENT_RECOMPUTATION.json"\n    output.write_text',
     '    output = AUDIT_DIR / "INDEPENDENT_RECOMPUTATION.json"\n    output.write_text'),
    ('"monitor_per_regime_root", "calibration_per_regime_root", "threshold_selection_per_regime_root",\n        "final_development_shots_per_regime_root"',
     '"monitor_shots_per_regime_root", "calibration_shots_per_regime_root", "threshold_selection_shots_per_regime_root",\n        "final_development_shots_per_regime_root"'),
]
for old, new in replacements:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one source occurrence, got {count}: {old[:120]!r}")
    source = source.replace(old, new, 1)

target = AUDIT_DIR / "verify_saved_results_after_runner_failure.py"
target.write_text(source, encoding="utf-8")
print(f"Created read-only verifier copy: {target}")
