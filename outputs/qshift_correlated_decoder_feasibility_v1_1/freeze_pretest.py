"""Create the non-circular V1.1 source/configuration freeze before commit."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
FREEZE_PATH = ROOT / "PRETEST_FREEZE.json"
FILES = [
    "outputs/qshift_correlated_decoder_feasibility_v1_1/.gitignore",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/.gitattributes",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/config.json",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/EXPERIMENT_PROTOCOL.md",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/README.md",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/PREFLIGHT_RESULTS.md",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/requirements.txt",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/model.py",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/prepare_seeds.py",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/verify_reuse.py",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/preflight.py",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/run_eval.py",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/run_watchdog.py",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/analyze_saved.py",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/publish_results.py",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/freeze_pretest.py",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/seed_inventory.json",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/REUSE_VERIFICATION.json",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/REUSE_CALIBRATION_PREFLIGHT.json",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/tests/test_estimator.py",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/tests/test_deterministic_model.py",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/tests/test_analyze_saved.py",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/tests/test_runner_gate.py",
    "outputs/phase3a_correlated_noise_preflight/simulator.py",
    "outputs/phase2b_pauli_bias/noise_model.py",
]


def main() -> None:
    file_hashes = {}
    for relative in FILES:
        path = REPO / relative
        if not path.is_file():
            raise FileNotFoundError(f"freeze input missing: {relative}")
        file_hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    freeze = {
        "schema": "qshift-correlated-decoder-v1.1-pretest-freeze-v1",
        "study": "one 60,000-shot V1.1 development-only paired evaluation after reusing V1 detector arrays",
        "source_base_commit": "0da212941ce4cce43cc4d27821e3a59c0acb6cd2",
        "v1_source_attempt_commit": "bfd971d06d0deadaac965086c3a6cbdca58eeb4b",
        "branch": "codex/qshift-correlated-decoder-feasibility-v1-1",
        "files": file_hashes,
        "file_count": len(file_hashes),
        "non_circular_binding": "This freeze records exact file bytes before commit and deliberately excludes its own digest and the final commit SHA. Execution separately requires --expected-head to equal the exact commit that contains this freeze, a clean tree, and this complete file map.",
        "sampling_authorization": "Provided by the owner for one bounded V1.1 evaluation only after all frozen checks pass; this file does not grant broader authority.",
        "sampler_calls_before_freeze": 0,
        "new_evaluation_shots_before_freeze": 0,
        "v1_reuse_archive_count": 33,
        "v1_reuse_archive_verification_sha256": file_hashes["outputs/qshift_correlated_decoder_feasibility_v1_1/REUSE_VERIFICATION.json"],
        "evaluation_seed_inventory_sha256": file_hashes["outputs/qshift_correlated_decoder_feasibility_v1_1/seed_inventory.json"],
    }
    FREEZE_PATH.write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"freeze": FREEZE_PATH.as_posix(), "file_count": len(file_hashes),
                      "freeze_sha256": hashlib.sha256(FREEZE_PATH.read_bytes()).hexdigest(),
                      "sampling_authorized_by_this_file": False}, indent=2))


if __name__ == "__main__":
    main()
