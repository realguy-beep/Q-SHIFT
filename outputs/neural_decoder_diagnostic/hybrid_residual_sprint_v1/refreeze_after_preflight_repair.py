"""Create a superseding pre-production freeze after a diagnostic-only repair.

This script does not sample data. It preserves and authenticates the original
preflight freeze, seed inventory, and the 384 already generated diagnostic
shots, then hashes the repaired runner before any production partition exists.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import sys
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
import prepare_freeze


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(value: dict, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def main() -> None:
    freeze_path = HERE / "FREEZE.json"
    initial_copy = HERE / "FREEZE_PREFLIGHT_ATTEMPT_1.json"
    if not freeze_path.is_file() or not initial_copy.is_file():
        raise RuntimeError("Original freeze and preserved attempt-1 copy are both required.")
    old = json.loads(freeze_path.read_text(encoding="utf-8"))
    old_hash = sha(freeze_path)
    if sha(initial_copy) != old_hash:
        raise RuntimeError("Preserved attempt-1 freeze differs from the original freeze.")
    if old.get("status") != "FROZEN BEFORE ALL NEW SAMPLING":
        raise RuntimeError("Unexpected initial freeze status.")

    cfg_path = HERE / "config.json"
    inv_path = HERE / "SEED_INVENTORY.json"
    audit_path = HERE / "HISTORICAL_SEED_AUDIT.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    inv = json.loads(inv_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if sha(cfg_path) != old.get("config_sha256") or sha(HERE / "EXPERIMENT_PROTOCOL.md") != old.get("protocol_sha256"):
        raise RuntimeError("Frozen experiment configuration or protocol changed.")
    if sha(inv_path) != old.get("seed_inventory_sha256") or sha(audit_path) != old.get("historical_seed_audit_sha256"):
        raise RuntimeError("The original seed inventory or historical audit changed.")
    if not inv.get("passed") or inv.get("historical_collisions") or inv.get("derived_seed_count") != inv.get("unique_derived_seed_count"):
        raise RuntimeError("The frozen seed inventory is not collision-free.")
    if audit.get("status") != "PASS" or audit.get("historical_collisions"):
        raise RuntimeError("The historical collision audit does not pass.")

    diag_path = HERE / "preflight" / "diagnostic_samples.npz"
    diag_meta_path = HERE / "preflight" / "diagnostic_samples.json"
    diag_meta = json.loads(diag_meta_path.read_text(encoding="utf-8"))
    if (sha(diag_path) != diag_meta.get("archive_sha256") or
            int(diag_meta.get("shots", -1)) != 384 or
            diag_meta.get("seed_ids") != inv.get("diagnostic_seeds") or
            int(diag_meta.get("independent_test_access", -1)) != 0):
        raise RuntimeError("The preserved diagnostic archive is not authenticated by its metadata.")
    run_dir = HERE / "run"
    production_files = [p for p in run_dir.rglob("*") if p.is_file()]
    if production_files:
        raise RuntimeError("Production run files exist; this diagnostic-only superseding freeze is unsafe.")

    local = list(prepare_freeze.LOCAL_FILES) + ["refreeze_after_preflight_repair.py"]
    external = list(prepare_freeze.EXTERNAL_FILES)
    evidence = ["FREEZE_PREFLIGHT_ATTEMPT_1.json", "preflight/ATTEMPT_01_FAILURE.md",
                "preflight/diagnostic_samples.npz", "preflight/diagnostic_samples.json",
                "preflight/diagnostic_samples.sidecar_attempt_1.json.tmp"]
    paths = [HERE / rel for rel in local + evidence]
    paths += [REPO / rel for rel in external]
    paths += [inv_path, audit_path]
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise FileNotFoundError("Cannot freeze missing source/evidence: " + ", ".join(missing))
    source_hashes = {str(p.relative_to(REPO)): sha(p) for p in paths}

    packages = {name: importlib.metadata.version(name)
                for name in ("torch", "stim", "pymatching", "numpy", "psutil")}
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; refusing the production freeze.")
    device = torch.cuda.get_device_name(0)
    if device != old.get("cuda_device"):
        raise RuntimeError("CUDA device differs from initial preflight freeze.")
    freeze = dict(old)
    freeze.update({
        "status": "FROZEN BEFORE PRODUCTION SAMPLING; PREFLIGHT DIAGNOSTICS PRESERVED",
        "created_unix": time.time(),
        "supersedes_freeze_sha256": old_hash,
        "supersession_reason": "Windows atomic-json fsync fix and idempotent recovery of already authenticated preflight diagnostics; no scientific configuration, seed, model, or endpoint changed.",
        "preflight_diagnostic_shots_already_generated": 384,
        "preflight_diagnostic_archive_sha256": sha(diag_path),
        "preflight_failure_record_sha256": sha(HERE / "preflight" / "ATTEMPT_01_FAILURE.md"),
        "config_sha256": sha(cfg_path),
        "protocol_sha256": sha(HERE / "EXPERIMENT_PROTOCOL.md"),
        "failure_analysis_sha256": sha(HERE / "FAILURE_ANALYSIS.md"),
        "seed_inventory_sha256": sha(inv_path),
        "historical_seed_audit_sha256": sha(audit_path),
        "source_sha256": source_hashes,
        "python_executable": sys.executable,
        "python_version": sys.version,
        "packages": packages,
        "cuda_available": True,
        "cuda_device": device,
        "cuda_total_memory_bytes": int(torch.cuda.get_device_properties(0).total_memory),
        "production_sampling_started": False,
        "independent_test_access": 0,
    })
    atomic_json(freeze, freeze_path)
    print(json.dumps({"status": freeze["status"], "freeze_sha256": sha(freeze_path),
                      "supersedes": old_hash, "diagnostic_shots_preserved": 384,
                      "production_sampling_started": False,
                      "seed_inventory_sha256": sha(inv_path)}, indent=2))


if __name__ == "__main__":
    main()
