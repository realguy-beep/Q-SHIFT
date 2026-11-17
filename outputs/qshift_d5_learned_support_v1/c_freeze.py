"""Write the non-circular Phase C freeze (C_FREEZE.json) before commit."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
PKG = "outputs/qshift_d5_learned_support_v1"
FILES = [f"{PKG}/{n}" for n in (
    ".gitattributes", ".gitignore", "PHASE_A_RESULTS.md", "learner_d5.py", "CLASSES_D5.json", "contract.py",
    "prepare_dev_seeds.py", "DEV_SEEDS.json", "DEV_PROTOCOL.md", "DEV_GATE.json", "DEV_RESULTS.md",
    "GATE_B2_PLAN_DRAFT.md", "GATE_B2_PROTOCOL.md", "b2.py", "B2_SEEDS.json", "NULL_THRESHOLD.json",
    "DEV_GATE_B2.json", "DEV_RESULTS_B2.md", "c_seal.py", "HIDDEN_COMMITMENT_C.json", "c_contract.py", "c_seeds.py",
    "C_SEEDS.json", "c_job.py", "c_run_all.py", "c_analyze.py", "c_recount.py", "c_preflight.py", "C_PREFLIGHT.json",
    "c_freeze.py", "PHASE_C_PROTOCOL.md", "tests/test_phase_c.py",
)] + [
    "outputs/qshift_correlated_decoder_v1_4/model_v14.py",
    "outputs/qshift_correlated_decoder_v1_4/BURST_SUPPORT.json",
    "outputs/qshift_correlated_decoder_v1_6/learner.py",
    "outputs/qshift_v1_4b_decoder_optimality/mld.py",
    "outputs/qshift_scalable_decoder_dev_v3/bposd.py",
    "outputs/qshift_scalable_decoder_dev_v3_2/ldpc_bposd.py",
    "outputs/qshift_scalable_decoder_dev_v3_2/ENVIRONMENT_DELTA.txt",
    "outputs/phase2b_pauli_bias/noise_model.py",
    "outputs/qshift_scalable_decoder_eval_d57_v1/PHASE2_D5_PRIOR.json",
    "outputs/qshift_scalable_decoder_eval_d5_phase2_v1/contract.py",
]


def main() -> None:
    hashes = {}
    for rel in FILES:
        p = REPO / rel
        if not p.is_file():
            raise FileNotFoundError(f"freeze input missing: {rel}")
        hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    freeze = {
        "schema": "qshift-d5-learned-support-C-freeze-v1",
        "study": ("one 1,200,096-shot d=5 evaluation: L2 BP+OSD with a LEARNED burst support (null-calibrated learner) "
                  "vs correlated PyMatching with the true support; conditions K (known scaled_v1) and H (sealed hidden)"),
        "branch": "codex/qshift-correlated-decoder-v1-6", "files": hashes, "file_count": len(hashes),
        "non_circular_binding": ("Records exact file bytes before commit; excludes its own digest and the commit SHA. "
                                 "Execution requires --expected-head equal to the commit containing this freeze, a clean "
                                 "tree, --open-hidden-seal, and every file hash above (checked by each job)."),
        "sampling_authorization": "None. The owner must separately authorize the single Phase C run and opening H's seal.",
        "phase_c_eval_sampler_calls_before_freeze": 0,
        "hidden_seal_opened_before_freeze": False,
    }
    (ROOT / "C_FREEZE.json").write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"file_count": len(hashes),
                      "freeze_sha256": hashlib.sha256((ROOT / "C_FREEZE.json").read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
