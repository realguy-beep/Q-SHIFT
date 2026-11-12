"""Freeze the protocol-consistent post-run audit before reading eval labels."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from experiment_core import atomic_json, sha256
from freeze_pretest import verify_freeze

HERE = Path(__file__).resolve().parent
RUN = HERE / "run_recovery_v5"
TARGET = HERE / "POSTRUN_RECONSTRUCTION_FREEZE_V1.json"


def seed(inv: dict, role: str, split: str, p: float, root: int) -> int:
    rows = [x for x in inv["streams"] if x["role"] == role and x["split"] == split
            and x["root"] == root and float(x["probability"]) == float(p)]
    if len(rows) != 1:
        raise ValueError(f"seed mapping is not unique for {role}/{split}/{p}/{root}")
    return int(rows[0]["seed"])


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> None:
    if TARGET.exists():
        raise FileExistsError(f"reconstruction freeze is immutable: {TARGET}")
    original = verify_freeze()
    cfg = json.loads((HERE / "experiment_config.json").read_text(encoding="utf-8"))
    inv = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
    status = json.loads((RUN / "status.json").read_text(encoding="utf-8"))
    if status.get("status") != "sampling_completed" or status.get("sampling_complete") is not True:
        raise RuntimeError("sampling is not complete; cannot freeze reconstruction")
    if (RUN / "INDEPENDENT_AUDIT.json").exists():
        raise RuntimeError("an audit output already exists; do not refreeze after outcome audit")
    probs = list(map(float, cfg["circuit"]["probabilities"]))
    n = int(cfg["partitions"]["evaluation_roots_per_condition"])
    inventories = {"calibration": [], "evaluation": []}
    for p in probs:
        for root in range(n):
            expected_cal = seed(inv, "calibration", "heldout_development", p, root)
            expected_eval = seed(inv, "evaluation", "heldout_development", p, root)
            for partition, role, expected in (
                ("heldout_development_calibration", "calibration", expected_cal),
                ("evaluation", "evaluation", expected_eval),
            ):
                path = RUN / partition / f"p_{p:.3f}" / f"root_{root:03d}.npz"
                marker = path.with_suffix(path.suffix + ".commit.json")
                if not path.is_file() or not marker.is_file():
                    raise FileNotFoundError(f"missing committed {partition} root {p}/{root}")
                md = json.loads(marker.read_text(encoding="utf-8"))
                digest = sha256(path)
                if md.get("sha256") != digest:
                    raise ValueError(f"archive marker mismatch before reconstruction: {path}")
                inventories["calibration" if role == "calibration" else "evaluation"].append({
                    "condition_p": p, "root": root, "seed": expected,
                    "archive": str(path.relative_to(RUN)), "sha256": digest,
                    "marker_sha256": sha256(marker),
                })
    if len(inventories["calibration"]) != 600 or len(inventories["evaluation"]) != 600:
        raise RuntimeError("expected exactly 600 calibration and 600 evaluation archives")
    source_names = [
        "POSTRUN_RECONSTRUCTION_PROTOCOL_V1.md",
        "POSTRUN_AUDIT_ATTEMPT_V1.md",
        "audit_saved_run_reconstruction_v1.py",
        "analyze_results_reconstruction_v1.py",
        "freeze_reconstruction_v1.py",
        "audit_saved_run_v2.py",
        "analyze_results.py",
        "experiment_config.json",
        "seed_inventory.json",
        "run_development.py",
        "PRETEST_FREEZE_V14.json",
    ]
    hashes = {name: sha256(HERE / name) for name in source_names}
    inventories_json = json.dumps(inventories, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    freeze = {
        "schema_version": 1,
        "created_before_corrected_outcome_audit": True,
        "original_pretest_freeze": "PRETEST_FREEZE_V14.json",
        "original_pretest_freeze_sha256": sha256(HERE / "PRETEST_FREEZE_V14.json"),
        "run_status_at_freeze": status,
        "calibration_archive_count": 600,
        "evaluation_archive_count": 600,
        "paired_evaluation_shots": 1_500_000,
        "calibration_shots": 1_200_000,
        "estimator_rule": "independent template profiles p=0,0.01,0.02; estimate once from concatenated calibration detectors only; never use final evaluation observables for fit or selection",
        "runner_deviation_rule": "retain the runner's label-conditioned pooled p/predictions as invalid legacy outputs; reconstruct the protocol-specified pooled arm separately from frozen template profiles",
        "statistics": cfg["statistics"],
        "analysis_bootstrap_seed": next(int(x["seed"]) for x in inv["streams"] if x["role"] == "bootstrap_results"),
        "calibration_and_evaluation_inventory_sha256": sha_bytes(inventories_json),
        "source_sha256": hashes,
        "calibration_archives": inventories["calibration"],
        "evaluation_archives": inventories["evaluation"],
        "sealed_test_access": False,
        "new_sampling": False,
    }
    atomic_json(TARGET, freeze)
    print(json.dumps({"status": "RECONSTRUCTION_FROZEN_BEFORE_OUTCOME_AUDIT",
                      "freeze": str(TARGET), "freeze_sha256": sha256(TARGET),
                      "calibration_archives": 600, "evaluation_archives": 600,
                      "evaluation_shots": 1_500_000}, indent=2))


if __name__ == "__main__":
    main()
