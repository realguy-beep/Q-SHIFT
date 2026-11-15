"""Create the explicit V1.1 recovery source identity before the Git commit."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pymatching
import stim

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from recovery_support_v1_1 import RECOVERY, V1_MANIFEST_SHA256, sha_file, verify_v1_manifest

FILES = (
    "RECOVERY_V1_1_OPERATIONAL_AMENDMENT.md",
    "RECOVERY_INPUT_INVENTORY_V1_1.json",
    "RECOVERY_SOURCE_MANIFEST_V1_1_PREVALIDATION.json",
    "prepare_recovery_input_v1_1.py",
    "recovery_support_v1_1.py",
    "run_recovery_v1_1.py",
    "analyze_recovery_v1_1.py",
    "audit_recovery_v1_1.py",
    "freeze_recovery_v1_1.py",
    "tests/test_recovery_v1_1.py",
)
SUPERSEDED_CANDIDATE_SHA256 = "de42ec6ae4badfdbec22ab1617d18d39351ba53a42c4dec14a1cc6dbfb4af7d5"


def create() -> dict:
    if RECOVERY.exists():
        raise RuntimeError("recovery output already exists; refusing to refreeze or resume")
    verify_v1_manifest()
    files = {}
    for rel in FILES:
        path = ROOT / rel
        if not path.is_file():
            raise RuntimeError(f"required recovery source is missing: {rel}")
        files[rel] = sha_file(path)
    inventory = ROOT / "RECOVERY_INPUT_INVENTORY_V1_1.json"
    calibration = ROOT / "calibration_estimates.json"
    superseded_path = ROOT / "RECOVERY_SOURCE_MANIFEST_V1_1_PREVALIDATION.json"
    if sha_file(superseded_path) != SUPERSEDED_CANDIDATE_SHA256:
        raise RuntimeError("superseded prevalidation manifest hash mismatch")
    manifest = {
        "schema": "qshift-performance-recovery-source-freeze-v1.1",
        "purpose": "single controlled deterministic-seed replay and remaining V1 evaluation partitions",
        "v1_source_manifest_sha256": V1_MANIFEST_SHA256,
        "recovery_input_inventory_sha256": sha_file(inventory),
        "superseded_prevalidation_manifest_sha256": sha_file(superseded_path),
        "preserved_calibration_estimates_sha256": sha_file(calibration),
        "base_commit": "5c9f8b639ff7b7ab7be7cd01839db4b581ed3082",
        "files": files,
        "environment": {"python": sys.version, "stim": stim.__version__,
                        "pymatching": pymatching.__version__, "numpy": np.__version__},
        "source_manifest_rule": "manifest self-hash excluded; actual run commit is captured in run_start.json after publication",
        "sampling_policy": "50 recovery calls only; exact original 50 evaluation labels/seeds; no resume or seed substitution",
    }
    out = ROOT / "RECOVERY_SOURCE_MANIFEST_V1_1.json"
    if out.exists():
        raise RuntimeError("recovery manifest already exists; do not overwrite")
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"manifest": str(out), "sha256": sha_file(out), "files": len(files)}


if __name__ == "__main__":
    print(json.dumps(create(), indent=2, sort_keys=True))
