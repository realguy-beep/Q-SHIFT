"""Write the non-circular Stage E freeze (EVAL_FREEZE.json) before commit."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
PKG = "outputs/qshift_d5_lowp_regime_v1"
FILES = [f"{PKG}/{n}" for n in (
    ".gitattributes", ".gitignore", "PLAN_DRAFT.md", "STAGE_S_PROTOCOL.md", "DEV_SEEDS.json", "DEV_SELECTION.json",
    "DEV_RESULTS.md", "contract.py", "prepare_dev_seeds.py", "dev_jobs.py", "dev_aggregate.py", "run_dev.py",
    "tests/test_stage_s.py", "PROTOCOL.md", "eval_contract.py", "prepare_eval_seeds.py", "EVAL_SEEDS.json",
    "eval_job.py", "run_all.py", "analyze.py", "recount.py", "preflight.py", "EVAL_PREFLIGHT.json", "freeze.py",
    "tests/test_stage_e.py",
)] + [
    "outputs/qshift_correlated_decoder_v1_4/model_v14.py",
    "outputs/qshift_correlated_decoder_v1_4/BURST_SUPPORT.json",
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
        "schema": "qshift-d5-lowp-regime-freeze-v1",
        "study": ("one 2,892,888-shot d=5 evaluation in a burst-dominated regime: L2 BP+OSD (static prior, true support) "
                  "vs re-selected correlated PyMatching at p=0.001 (L10) and p=0.0015 (L15); 95% target at L10"),
        "branch": "codex/qshift-correlated-decoder-v1-6", "files": hashes, "file_count": len(hashes),
        "non_circular_binding": ("Records exact file bytes before commit; excludes its own digest and the commit SHA. "
                                 "Execution requires --expected-head equal to the commit containing this freeze, a clean "
                                 "tree, and every file hash above (checked by each job)."),
        "sampling_authorization": "None. The owner must separately authorize the single Stage E run on this exact commit.",
        "stage_e_eval_sampler_calls_before_freeze": 0,
    }
    (ROOT / "EVAL_FREEZE.json").write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"file_count": len(hashes),
                      "freeze_sha256": hashlib.sha256((ROOT / "EVAL_FREEZE.json").read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
