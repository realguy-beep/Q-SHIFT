"""Freeze only the prespecified validation scripts/configs before running them."""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import scipy
import stim
import pymatching

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FILES = [
    "outputs/stage5_design_validation_v1/DESIGN_SIMULATION_CONFIG.json",
    "outputs/stage5_design_validation_v1/BENCHMARK_CONFIG.json",
    "outputs/stage5_design_validation_v1/PROPOSED_256_ALLOCATION.json",
    "outputs/stage5_design_validation_v1/VALIDATION_SEED_INVENTORY.json",
    "outputs/stage5_design_validation_v1/STAGE5_ENDPOINT_B_AMENDMENT_CANDIDATE_V1.md",
    "outputs/stage5_design_validation_v1/design_simulation.py",
    "outputs/stage5_design_validation_v1/pipeline_benchmark.py",
    "outputs/stage5_design_validation_v1/audit_dynamic.py",
    "outputs/stage5_design_validation_v1/integrity.py",
    "outputs/stage5_design_validation_v1/prepare_seed_inventory.py",
    "outputs/stage5_design_validation_v1/freeze_candidate.py",
    "outputs/stage5_design_validation_v1/test_dynamic_audit.py",
    "outputs/stage5_design_validation_v1/test_seed_inventory.py",
    "outputs/stage5_endpoint_review_v1/PROPOSED_STAGE5_STATISTICAL_AMENDMENT_V1.md",
    "outputs/stage5_preexecution_v1/STAGE5_V2_FREEZE.json",
    "outputs/stage5_preexecution_v1/FROZEN_PROFILE_ESTIMATOR.json",
    "outputs/stage5_preexecution_v1/stage5_saved_array_audit.py",
    "outputs/stage5_preexecution_v1/stage5_runner.py",
]

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

inventory = json.loads((HERE / "VALIDATION_SEED_INVENTORY.json").read_text(encoding="utf-8"))
if inventory.get("historical_seed_collision_count") != 0 or inventory.get("stage5_evaluation_seed_namespace_used") is not False:
    raise RuntimeError("seed collision/namespace preflight failed")
if len(set(inventory["analysis_rngs"]["welch_scenario_seeds"] + inventory["analysis_rngs"]["bootstrap_t_scenario_seeds"] +
           [inventory["analysis_rngs"]["p0_safety_seed"]] + inventory["preflight_fixture_seeds_already_consumed"] +
           [x["seed"] for x in inventory["benchmark_streams"]])) != inventory["unique_proposed_seed_count"]:
    raise RuntimeError("proposed seed uniqueness check failed")
hashes = {}
for rel in FILES:
    path = ROOT / rel
    if not path.is_file():
        raise FileNotFoundError(rel)
    hashes[rel] = sha(path)
freeze = {
    "study": "Stage 5 design validation v1",
    "status": "presampling design/benchmark freeze; explicitly not Stage 5 sampling authorization",
    "created_before_design_simulation_and_benchmark": True,
    "stage5_evaluation_shots_generated": 0,
    "sealed_historical_test_accessed": False,
    "stage5_v2_freeze_preserved_sha256": hashes["outputs/stage5_preexecution_v1/STAGE5_V2_FREEZE.json"],
    "seed_audit_summary": {
        "proposed_unique_seed_count": inventory["unique_proposed_seed_count"],
        "recoverable_historical_integer_values_scanned": inventory["historical_union_count_scanned"],
        "collisions": 0,
        "seed_source_files": inventory["historical_sources"],
    },
    "software": {"python": sys.version.split()[0], "platform": platform.platform(),
        "numpy": np.__version__, "scipy": scipy.__version__, "stim": stim.__version__, "pymatching": pymatching.__version__},
    "sha256": hashes,
    "freeze_self_hash": "omitted by design",
}
(HERE / "DESIGN_VALIDATION_FREEZE.json").write_text(json.dumps(freeze, indent=2) + "\n", encoding="utf-8")
print(f"Wrote pre-execution freeze with {len(hashes)} SHA-256 records; no Stage 5 samples authorized")
