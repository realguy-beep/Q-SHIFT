"""Write the non-circular Phase 2 (d=5) source/configuration freeze (FREEZE.json) before commit."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
PKG = "outputs/qshift_scalable_decoder_eval_d5_phase2_v1"
D57 = "outputs/qshift_scalable_decoder_eval_d57_v1"
FILES = [f"{PKG}/{n}" for n in (
    ".gitattributes", ".gitignore", "PROTOCOL.md", "contract.py", "prepare_seeds.py", "SEEDS.json", "eval_job.py",
    "run_all.py", "analyze.py", "recount.py", "freeze.py", "preflight.py", "PREFLIGHT.json", "tests/test_phase2.py",
)] + [f"{D57}/{n}" for n in (
    "PHASE2_D5_PLAN_DRAFT.md", "STEP0_PROTOCOL.md", "PHASE2_D5_PRIOR.json", "PHASE1_RESULTS.json",
    "SCREEN_RESULTS.json", "PHASE1_SEEDS.json", "SCREEN_SEEDS.json",
)] + [
    "outputs/qshift_correlated_decoder_v1_4/model_v14.py",
    "outputs/qshift_scalable_decoder_dev_v3/bposd.py",
    "outputs/qshift_scalable_decoder_dev_v3_2/ldpc_bposd.py",
    "outputs/qshift_scalable_decoder_dev_v3_2/ENVIRONMENT_DELTA.txt",
    "outputs/phase2b_pauli_bias/noise_model.py",
]


def main() -> None:
    hashes = {}
    for rel in FILES:
        p = REPO / rel
        if not p.is_file():
            raise FileNotFoundError(f"freeze input missing: {rel}")
        hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    freeze = {
        "schema": "qshift-d5-phase2-freeze-v1",
        "study": "one 600,048-shot d=5 Phase 2 evaluation: L2 BP+OSD at static q_dec=0.01 vs correlated PyMatching (Astar_5)",
        "branch": "codex/qshift-correlated-decoder-v1-6",
        "files": hashes, "file_count": len(hashes),
        "non_circular_binding": ("Records exact file bytes before commit; excludes its own digest and the commit SHA. "
                                 "Execution requires --expected-head equal to the commit containing this freeze, a clean "
                                 "tree, and every file hash above (checked by each job)."),
        "sampling_authorization": "None. The owner must separately authorize the single Phase 2 run on this exact commit.",
        "phase2_eval_sampler_calls_before_freeze": 0,
    }
    (ROOT / "FREEZE.json").write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"file_count": len(hashes),
                      "freeze_sha256": hashlib.sha256((ROOT / "FREEZE.json").read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
