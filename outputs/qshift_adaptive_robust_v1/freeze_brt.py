"""Write the non-circular BRT freeze (BRT_FREEZE.json) before commit."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
PKG = "outputs/qshift_adaptive_robust_v1"
FILES = [f"{PKG}/{n}" for n in (
    ".gitignore", "PLAN_BRT.md", "BRT_PROTOCOL.md", "brt_config.py", "brt.py", "brt0.py", "estimate5.py",
    "prepare_brt.py", "preflight_brt.py", "freeze_brt.py", "BRT_BURSTS.json", "BRT_SEEDS.json", "BRT_PREFLIGHT.json",
    "tests/test_brt.py", "results/brt/BRT0.json",
    "brs_config.py", "brs.py", "estimate4.py", "prepare_brs.py", "BRS_BURSTS.json", "BRS_SEEDS.json",
    "results/bre/ANALYSIS.json",
    "bre_config.py", "bre.py", "estimate3.py", "prepare_bre.py", "BRE_BURSTS.json", "BRE_SEEDS.json",
    "re1_seal.py", "re1_config.py", "prepare_re1.py", "RE1_SEEDS.json",
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
    fz = {"schema": "qshift-adaptive-robust-brt-freeze-v1",
          "study": "BRT-1 threshold-free E1 flag (arms B2, E1, E1S, E1T; 16 fresh held-out bursts; widened p range)",
          "branch": "codex/qshift-adaptive-robust-v1", "files": hashes, "file_count": len(hashes),
          "non_circular_binding": "Excludes its own digest and the commit SHA; runs require --expected-head = the commit "
                                  "containing this file, a clean tree, and every hash above (checked by each job).",
          "sampling_authorization": "None. Owner must separately authorize 'Run BRT' on this commit.",
          "study_samples_before_freeze": 0}
    (ROOT / "BRT_FREEZE.json").write_text(json.dumps(fz, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(len(hashes), "files;", hashlib.sha256((ROOT / "BRT_FREEZE.json").read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
