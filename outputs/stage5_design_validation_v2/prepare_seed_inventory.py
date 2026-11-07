from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONFIG = json.loads((HERE / "DESIGN_SIMULATION_CONFIG.json").read_text(encoding="utf-8"))

# Explicit metadata-only sources. No sealed evaluation arrays or directories are opened.
SAFE_SOURCES = [
    "outputs/stage4_noise_adaptive_development_v1/seed_inventory.json",
    "outputs/stage4_noise_adaptive_development_v1/seed_audit.json",
    "outputs/stage4_noise_adaptive_development_v1/additional_development_seed_audit.json",
    "outputs/stage4c_cnn_noise_estimation_v1/seed_inventory.json",
    "outputs/stage4c_cnn_noise_estimation_v1/seed_audit.json",
    "outputs/stage5_preexecution_v1/seed_inventory.json",
    "outputs/stage5_preexecution_v1/STAGE5_V2_CONFIG.json",
    "outputs/stage5_design_validation_v1/VALIDATION_SEED_INVENTORY.json",
    "outputs/stage5_design_validation_v1/DESIGN_SIMULATION_CONFIG.json",
    "outputs/stage5_design_validation_v1/DESIGN_SIMULATION_RESULTS.json",
    "outputs/stage5_design_validation_v1/benchmark_run/ROOT_ARCHIVE_MANIFEST.json",
    "outputs/stage5_endpoint_review_v1/POWER_SENSITIVITY.json",
]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def ints(value):
    if isinstance(value, bool):
        return
    if isinstance(value, int) and value >= 1_000_000:
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from ints(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from ints(item)


historical = set()
source_records = []
for rel in SAFE_SOURCES:
    path = ROOT / rel
    if not path.is_file():
        raise FileNotFoundError(f"Required nonsealed seed metadata missing: {rel}")
    data = json.loads(path.read_text(encoding="utf-8"))
    found = list(ints(data))
    historical.update(found)
    source_records.append({"path": rel, "sha256": sha(path), "integer_values_ge_1m_scanned": len(found)})

entries = []
base = int(CONFIG["rng"]["seed_namespace_start"])

def add(kind: str, key: str):
    entries.append({"stream": kind, "cell": key, "seed": base + len(entries)})

allocations = CONFIG["allocations_roots_per_stratum"]
for n in allocations:
    for scenario in CONFIG["null_scenarios"]:
        key = f"n{n}/{scenario['name']}"
        add("primary_null_calibration", key)
        add("primary_null_validation", key)
    for scenario in CONFIG["power_scenarios"]:
        for effect in CONFIG["power_effects"]:
            add("primary_power", f"n{n}/{scenario['name']}/delta{effect}")
    for scenario in CONFIG["p0_no_harm"]["scenarios"]:
        key = f"n{n}/{scenario['name']}"
        add("p0_null_calibration", key)
        add("p0_null_validation", key)
        for effect in CONFIG["p0_no_harm"]["power_true_effects"]:
            add("p0_safety_power", f"n{n}/{scenario['name']}/effect{effect}")
for family in ["normal", "student_t5", "student_t3", "lognormal_sigma1", "zero_inflated65_normal", "tied_asymmetric65"]:
    add("independent_generator_check", family)
add("independent_statistic_fixture", "fixed-small-matrix")

seeds = [x["seed"] for x in entries]
collisions = sorted(set(seeds) & historical)
if collisions:
    raise RuntimeError(f"New design simulation seeds collide with recoverable metadata: {collisions[:20]}")
if len(seeds) != len(set(seeds)):
    raise RuntimeError("New design simulation seeds are not unique")

inventory = {
    "purpose": "synthetic statistical design validation only; never Stage 5 Stim sampling",
    "stage5_evaluation_seeds_allocated": False,
    "stage5_evaluation_shots_generated": 0,
    "sealed_historical_test_accessed": False,
    "historical_coverage": "Explicit, nonsealed seed/config/result metadata listed below; sealed test arrays/directories are excluded and not opened.",
    "historical_sources_checked": source_records,
    "recoverable_integer_values_ge_1m_scanned": len(historical),
    "collision_count": 0,
    "rng_stream_count": len(entries),
    "rng_streams": entries,
    "rng": {"bit_generator": "PCG64", "namespace_start": base, "namespace_end": base + len(entries) - 1},
}
(HERE / "DESIGN_SEED_INVENTORY.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
print(f"PASS: {len(entries)} unique prospective design-only streams; {len(historical)} recoverable integers scanned; zero collisions")
