"""Write the non-circular RE1 freeze (RE1_FREEZE.json) before commit."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
PKG = "outputs/qshift_adaptive_robust_v1"
FILES = [f"{PKG}/{n}" for n in (
    ".gitignore", "PLAN_EVAL.md", "RE1_PROTOCOL.md", "re1_config.py", "re1_seal.py", "prepare_re1.py", "re1.py",
    "freeze_re1.py", "RE1_SEEDS.json", "HIDDEN_COMMITMENT_RE1.json", "RE1_PREFLIGHT.json", "tests/test_re1.py",
    "dev2_config.py", "prepare_dev2.py", "estimate2.py", "DEV2_SEEDS.json", "FLAG_THRESHOLD.json", "he1.py", "he1b.py",
    "adaptive/estimation.py",
)] + [
    "outputs/qshift_d5_model_mismatch_v1/mm_contract.py",
    "outputs/qshift_d5_learned_support_v1/learner_d5.py",
    "outputs/qshift_d5_learned_support_v1/b2.py",
    "outputs/qshift_d5_learned_support_v1/c_contract.py",
    "outputs/qshift_d5_learned_support_v1/contract.py",
    "outputs/qshift_d5_learned_support_v1/CLASSES_D5.json",
    "outputs/qshift_d5_learned_support_v1/NULL_THRESHOLD.json",
    "outputs/qshift_correlated_decoder_v1_6/learner.py",
    "outputs/qshift_correlated_decoder_v1_4/model_v14.py",
    "outputs/qshift_correlated_decoder_v1_4/BURST_SUPPORT.json",
    "outputs/qshift_scalable_decoder_dev_v3/bposd.py",
    "outputs/qshift_scalable_decoder_dev_v3_2/ldpc_bposd.py",
    "outputs/qshift_v1_4b_decoder_optimality/mld.py",
    "outputs/phase2b_pauli_bias/noise_model.py",
]


def main() -> None:
    hashes = {}
    for rel in FILES:
        p = REPO / rel
        if not p.is_file():
            raise FileNotFoundError(f"freeze input missing: {rel}")
        hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    fz = {"schema": "qshift-adaptive-robust-re1-freeze-v1",
          "study": "RE1 frozen evaluation of the mismatch-robust learned-support pipeline (6 gated conditions incl. sealed hidden burst H2)",
          "branch": "codex/qshift-adaptive-robust-v1", "files": hashes, "file_count": len(hashes),
          "non_circular_binding": "Excludes its own digest and the commit SHA; runs require --expected-head = the commit "
                                  "containing this file, a clean tree, and every hash above (checked by each job).",
          "sampling_authorization": "None. Owner must separately authorize 'Run RE1' (with --open-hidden-seal) on this commit.",
          "study_samples_before_freeze": 0}
    (ROOT / "RE1_FREEZE.json").write_text(json.dumps(fz, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(len(hashes), "files;", hashlib.sha256((ROOT / "RE1_FREEZE.json").read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
