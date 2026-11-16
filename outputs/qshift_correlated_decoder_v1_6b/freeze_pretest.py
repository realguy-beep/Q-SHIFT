"""Create the non-circular V1.6b source/configuration freeze before commit."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
FREEZE_PATH = ROOT / "PRETEST_FREEZE.json"
PKG = "outputs/qshift_correlated_decoder_v1_6b"
V16 = "outputs/qshift_correlated_decoder_v1_6"
FILES = [f"{PKG}/{n}" for n in (
    ".gitattributes", ".gitignore", "config.json", "EXPERIMENT_PROTOCOL.md", "README.md", "contract.py", "common.py",
    "prepare_seeds.py", "seed_inventory.json", "run_eval.py", "run_watchdog.py", "analyze_saved.py", "rehearsal.py",
    "preflight.py", "PREFLIGHT.json", "freeze_pretest.py", "recount_from_scratch.py", "tests/test_v1_6b.py",
)] + [f"{V16}/{n}" for n in (
    "learner.py", "HIDDEN_BURST_COMMITMENT.json", "seal_hidden_burst.py", "DESIGN_PLAN_V1_6B_DRAFT.md",
    "PREREGISTRATION_DEV_V1_6B.md", "dev_gate_v1_6b.py", "DEV_GATE_V1_6B.json", "DEV_GATE_RESULT.md", "tests/test_learner.py",
)] + [
    "outputs/qshift_correlated_decoder_v1_4/model_v14.py",
    "outputs/qshift_v1_4b_decoder_optimality/mld.py",
    "outputs/qshift_correlated_decoder_v1_3/STATIC_SELECTION.json",
    "outputs/phase2b_pauli_bias/noise_model.py",
    "outputs/qshift_correlated_decoder_feasibility_v1/seed_inventory.json",
    "outputs/qshift_correlated_decoder_feasibility_v1_1/seed_inventory.json",
    "outputs/qshift_correlated_decoder_v1_2/seed_inventory.json",
    "outputs/qshift_correlated_decoder_v1_3/seed_inventory.json",
    "outputs/qshift_correlated_decoder_v1_4/GATE_SEEDS.json",
    "outputs/qshift_correlated_decoder_v1_5/seed_inventory.json",
    "outputs/qshift_performance_sprint_v1/seed_inventory.json",
]


def main() -> None:
    hashes = {}
    for relative in FILES:
        path = REPO / relative
        if not path.is_file():
            raise FileNotFoundError(f"freeze input missing: {relative}")
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    freeze = {
        "schema": "qshift-correlated-decoder-v1.6b-pretest-freeze-v1",
        "study": "one 675,000-shot V1.6b development-only evaluation of the exact decoder with device-level learned burst support, on a known and a sealed hidden burst",
        "branch": "codex/qshift-correlated-decoder-v1-6",
        "files": hashes, "file_count": len(hashes),
        "hidden_burst_commitment_sha256": json.loads((REPO / f"{V16}/HIDDEN_BURST_COMMITMENT.json").read_text(encoding="utf-8"))["sha256_of_canonical_plaintext"],
        "non_circular_binding": "Records exact file bytes before commit; excludes its own digest and the final commit SHA. Execution separately requires --expected-head equal to the commit containing this freeze, a clean tree and this complete file map.",
        "sampling_authorization": "None. The owner must separately authorize the single bounded V1.6b evaluation on this exact commit.",
        "v1_6b_sampler_calls_before_freeze": 0,
        "hidden_burst_opened_before_freeze": False,
    }
    FREEZE_PATH.write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"file_count": len(hashes), "freeze_sha256": hashlib.sha256(FREEZE_PATH.read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
