"""Create the non-circular V1.5 source/configuration freeze before commit."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
FREEZE_PATH = ROOT / "PRETEST_FREEZE.json"
PKG = "outputs/qshift_correlated_decoder_v1_5"
V11 = "outputs/qshift_correlated_decoder_feasibility_v1_1"
FILES = [f"{PKG}/{name}" for name in (
    ".gitattributes", ".gitignore", "config.json", "EXPERIMENT_PROTOCOL.md", "README.md",
    "contract.py", "common.py", "prepare_seeds.py", "seed_inventory.json", "run_eval.py", "run_watchdog.py",
    "analyze_saved.py", "rehearsal.py", "preflight.py", "PREFLIGHT.json", "freeze_pretest.py",
    "recount_from_scratch.py", "posthoc_reference.py",
    "tests/test_rehearsal.py", "tests/test_gates_and_records.py",
)] + [
    f"{V11}/model.py", f"{V11}/verify_reuse.py", f"{V11}/REUSE_VERIFICATION.json",
    f"{V11}/seed_inventory.json", f"{V11}/PRETEST_FREEZE.json",
    "outputs/qshift_correlated_decoder_v1_3/multi_prior.py",
    "outputs/qshift_correlated_decoder_v1_3/STATIC_SELECTION.json",
    "outputs/qshift_correlated_decoder_v1_3/PRETEST_FREEZE.json",
    "outputs/qshift_correlated_decoder_v1_3/seed_inventory.json",
    "outputs/qshift_correlated_decoder_v1_3/results_v1/RESULTS.md",
    "outputs/qshift_correlated_decoder_v1_4/GATE_SEEDS.json",
    "outputs/qshift_v1_4b_decoder_optimality/mld.py",
    "outputs/qshift_v1_4b_decoder_optimality/PREREGISTRATION.md",
    "outputs/qshift_v1_4b_decoder_optimality/DECISION.md",
    "outputs/qshift_v1_4b_decoder_optimality/tests/test_mld.py",
    "outputs/qshift_correlated_decoder_v1_2/seed_inventory.json",
    "outputs/qshift_correlated_decoder_feasibility_v1/seed_inventory.json",
    "outputs/qshift_performance_sprint_v1/seed_inventory.json",
    "outputs/phase3a_correlated_noise_preflight/simulator.py",
    "outputs/phase2b_pauli_bias/noise_model.py",
]


def main() -> None:
    hashes = {}
    for relative in FILES:
        path = REPO / relative
        if not path.is_file():
            raise FileNotFoundError(f"freeze input missing: {relative}")
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    freeze = {
        "schema": "qshift-correlated-decoder-v1.5-pretest-freeze-v1",
        "study": "one 324,000-shot (36,000 calibration + 288,000 paired evaluation) V1.5 development-only evaluation of the exact DEM logical-class decoder against the best V1.3 decoder and the strongest static matcher",
        "branch": "codex/qshift-correlated-decoder-v1-5",
        "files": hashes,
        "file_count": len(hashes),
        "frozen_v1_3_settings": json.loads((REPO / "outputs/qshift_correlated_decoder_v1_3/STATIC_SELECTION.json").read_text(encoding="utf-8"))["selected"],
        "non_circular_binding": "Records exact file bytes before commit; excludes its own digest and the final commit SHA. Execution separately requires --expected-head equal to the commit containing this freeze, a clean tree and this complete file map.",
        "sampling_authorization": "None. The owner must separately authorize the single bounded V1.5 evaluation on this exact commit.",
        "v1_5_sampler_calls_before_freeze": 0,
    }
    FREEZE_PATH.write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"file_count": len(hashes),
                      "freeze_sha256": hashlib.sha256(FREEZE_PATH.read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
