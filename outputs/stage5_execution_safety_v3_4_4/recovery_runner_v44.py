"""Versioned, explicit-authorization recovery-copy runner for Stage 5.

No sampling command is enabled by default. Production work can only target the
single named recovery copy, never the historical failed run directory.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
V42 = ROOT / "outputs/stage5_execution_safety_v3_4_2"
RECOVERY_TARGET = ROOT / "outputs/stage5_secondary_inference_repair_v1/run_recovery_v3_4_4"
V44_FREEZE = HERE / "SAFETY_FREEZE_V44.json"
sys.path.insert(0, str(HERE))
from atomic_safety_v44 import atomic_write_json, sha256_file  # noqa: E402
from recovery_service_v44 import (  # noqa: E402
    SOURCE_RUN, SOURCE_INVENTORY, _read_only_source_quiescence,
    check_recovery_provenance, frozen_input_hashes, prepare_recovery_copy,
)


def verify_v44_freeze() -> dict:
    if not V44_FREEZE.is_file():
        raise RuntimeError("v3.4.4 source freeze is missing")
    record = json.loads(V44_FREEZE.read_text(encoding="utf-8"))
    if record.get("format") != "qshift-stage5-v344-recovery-safety-freeze":
        raise RuntimeError("unrecognized v3.4.4 freeze format")
    for rel, expected in record.get("sha256", {}).items():
        path = HERE / rel
        if not path.is_file() or sha256_file(path) != expected:
            raise RuntimeError(f"v3.4.4 source hash mismatch: {rel}")
    frozen = frozen_input_hashes()
    if len(frozen) != 53 or record.get("historical_v2_hash_count") != 53:
        raise RuntimeError("historical Stage 5 v2 frozen hash count changed")
    # Reuse v3.4.2's independently versioned historical/process preflight.
    sys.path.insert(0, str(V42))
    import safety_runner_v4
    safety = safety_runner_v4.verify_safety_sources()
    if len(safety.get("sha256", {})) != 14:
        raise RuntimeError("historical v3.4.2 safety inventory count changed")
    if record.get("historical_v3_3_hash_count") != 13 or record.get("historical_v3_4_2_hash_count") != 14:
        raise RuntimeError("historical v3.3/v3.4.2 safety inventory counts changed")
    v43_freeze = ROOT / "outputs/stage5_execution_safety_v3_4_3/SAFETY_FREEZE_V43_2.json"
    if sha256_file(v43_freeze) != record.get("historical_v3_4_3_freeze_sha256"):
        raise RuntimeError("historical v3.4.3.2 freeze hash changed")
    safety_runner_v4.verify_frozen_inputs()
    return {"v44_source_hashes": len(record["sha256"]),
            "stage5_v2_hashes": len(frozen),
            "v342_safety_hashes": len(safety["sha256"]),
            "base_commit": record.get("base_commit")}


def preflight() -> dict:
    freeze = verify_v44_freeze()
    with _read_only_source_quiescence(SOURCE_RUN):
        inventory = json.loads(SOURCE_INVENTORY.read_text(encoding="utf-8"))
        status = json.loads((SOURCE_RUN / "status.json").read_text(encoding="utf-8"))
        source_state = {"manifest_file_count": int(inventory.get("file_count", -1)),
                        "status": status.get("status"),
                        "original_run_path": str(SOURCE_RUN),
                        "target_exists": RECOVERY_TARGET.exists()}
    if source_state["manifest_file_count"] != 265 or source_state["status"] != "worker_failed":
        raise RuntimeError("source no longer matches the documented paused failure state")
    return {"status": "PASS_NO_SAMPLING_PREFLIGHT", "freeze": freeze,
            "source": source_state, "stage5_evaluation_samples_generated_by_preflight": 0,
            "recovery_or_sampling_executed": False}


def run_recovery_copy(run_dir: Path) -> dict:
    """Run only a manifest-proven recovery copy, subject to a separate CLI flag."""
    run_dir = Path(run_dir).resolve()
    if run_dir == SOURCE_RUN.resolve() or run_dir != RECOVERY_TARGET.resolve():
        raise RuntimeError("runner is restricted to the dedicated v3.4.4 recovery-copy path")
    verify_v44_freeze()
    check_recovery_provenance(run_dir)
    status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
    cfg = json.loads((ROOT / "outputs/stage5_secondary_inference_repair_v1/STAGE5_REPAIR_CONFIG.json").read_text(encoding="utf-8"))
    max_seconds = float(cfg["resources"]["wall_seconds_max"])
    already = float(status.get("cumulative_runtime_seconds", 0.0))
    remaining = max_seconds - already
    if remaining <= 0:
        raise TimeoutError("frozen Stage 5 wall-clock budget is already exhausted")

    sys.path.insert(0, str(V42))
    import safety_runner_v4
    safety_runner_v4.verify_safety_sources()
    safety_runner_v4.verify_frozen_inputs()
    safety_runner_v4.WORKER = HERE / "worker_recovery_v44.py"
    safety_runner_v4.AUDITOR = HERE / "audit_saved_run_v44.py"
    safety_runner_v4.FINALIZER = HERE / "finalize_v44.py"
    # The v4.2 pre-worker reconciler mutates historical status with its old
    # single-write path. v4.4 delegates all checkpoint/status reconciliation
    # to the new worker under its owned child lock and v4.4 CAS writer.
    safety_runner_v4.reconcile_uncommitted = lambda *_a, **_k: {"state": "delegated_to_v44_worker"}

    runner_deadline = time.monotonic() + remaining

    def safe_status_json(path, value):
        path = Path(path)
        try:
            path.resolve().relative_to(run_dir)
        except ValueError as exc:
            raise ValueError("supervisor status write escaped recovery copy") from exc
        return atomic_write_json(path, value, run_dir=run_dir,
                                 expected_old_sha256=sha256_file(path),
                                 deadline_monotonic=runner_deadline)

    safety_runner_v4.atomic_json = safe_status_json
    return safety_runner_v4.safe_execute(run_dir, timeout_seconds=remaining,
                                         recover_uncommitted=False)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--prepare-recovery-copy", action="store_true")
    parser.add_argument("--recovery-copy", type=Path)
    parser.add_argument("--authorize-stage5-recovery", action="store_true")
    args = parser.parse_args(argv)
    if args.preflight:
        print(json.dumps(preflight(), indent=2))
        return 0
    if args.prepare_recovery_copy:
        if RECOVERY_TARGET.exists():
            raise FileExistsError(f"recovery copy already exists; refusing overwrite: {RECOVERY_TARGET}")
        result = prepare_recovery_copy(RECOVERY_TARGET)
        print(json.dumps({"recovery_copy": str(RECOVERY_TARGET),
                          "source_inventory_sha256": result["source_inventory_sha256"],
                          "copied_file_count": result["copied_file_count"],
                          "sampling_performed": False}, indent=2))
        return 0
    if args.recovery_copy is not None and args.authorize_stage5_recovery:
        result = run_recovery_copy(args.recovery_copy)
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("status") == "completed" else 1
    parser.error("Use --preflight, or a separately authorized --recovery-copy PATH --authorize-stage5-recovery")


if __name__ == "__main__":
    raise SystemExit(main())
