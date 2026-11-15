"""Create the pre-sampling source/configuration freeze; does not sample."""
from __future__ import annotations
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
BRANCH = "codex/qshift-correlated-decoder-feasibility-v1"
REFERENCE = "2a8b03bd410245e1c3d9de9336cf3bcb78a92e5c"
FILES = [
    "outputs/qshift_correlated_decoder_feasibility_v1/.gitignore",
    "outputs/qshift_correlated_decoder_feasibility_v1/README.md",
    "outputs/qshift_correlated_decoder_feasibility_v1/config.json",
    "outputs/qshift_correlated_decoder_feasibility_v1/EXPERIMENT_PROTOCOL.md",
    "outputs/qshift_correlated_decoder_feasibility_v1/PREFLIGHT_RESULTS.md",
    "outputs/qshift_correlated_decoder_feasibility_v1/MATHEMATICAL_MODEL.md",
    "outputs/qshift_correlated_decoder_feasibility_v1/requirements.txt",
    "outputs/qshift_correlated_decoder_feasibility_v1/correlated_model.py",
    "outputs/qshift_correlated_decoder_feasibility_v1/run_deterministic_preflight.py",
    "outputs/qshift_correlated_decoder_feasibility_v1/deterministic_preflight.json",
    "outputs/qshift_correlated_decoder_feasibility_v1/prepare_seed_inventory.py",
    "outputs/qshift_correlated_decoder_feasibility_v1/freeze_pretest.py",
    "outputs/qshift_correlated_decoder_feasibility_v1/seed_inventory.json",
    "outputs/qshift_correlated_decoder_feasibility_v1/analyze_saved.py",
    "outputs/qshift_correlated_decoder_feasibility_v1/run_pilot.py",
    "outputs/qshift_correlated_decoder_feasibility_v1/run_watchdog.py",
    "outputs/qshift_correlated_decoder_feasibility_v1/tests/test_deterministic.py",
    "outputs/qshift_correlated_decoder_feasibility_v1/tests/test_saved_array_audit.py",
    "outputs/phase3a_correlated_noise_preflight/simulator.py",
    "outputs/phase2b_pauli_bias/noise_model.py",
    "outputs/qshift_performance_sprint_v1/seed_inventory.json",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=REPO, text=True).strip()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if branch != BRANCH or head != REFERENCE:
        raise SystemExit("freeze creation must start from the pinned reference commit on the dedicated branch")
    files = {}
    for rel in FILES:
        path = REPO / rel
        if not path.is_file():
            raise SystemExit(f"missing allowlisted freeze input: {rel}")
        files[rel] = sha(path)
    payload = {
        "schema": "qshift-correlated-decoder-pretest-freeze-v1",
        "classification": "development-only; not confirmatory; not Stage 5",
        "reference_commit": REFERENCE,
        "required_branch": BRANCH,
        "execution_binding": "run_pilot requires the exact post-freeze commit SHA via --expected-head; commit identity is recorded at execution to avoid a self-referential commit hash",
        "freeze_file_excluded_from_self_hash": True,
        "sampler_authorization": "single bounded 78,000-shot pilot as authorized in this task; no automatic retry or resume",
        "allocation": {"training": 3000, "calibration": 15000, "evaluation": 60000,
                       "total_unique_shots": 78000, "sampler_calls": 63},
        "files": files,
    }
    target = ROOT / "PRETEST_FREEZE.json"
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"pretest_freeze": str(target), "file_count": len(files),
                      "sha256": sha(target), "source_files": files}, indent=2))


if __name__ == "__main__":
    main()
