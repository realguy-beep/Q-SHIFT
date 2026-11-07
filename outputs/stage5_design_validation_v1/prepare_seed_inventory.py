"""Collision-screen disposable statistical and full-pipeline benchmark seeds."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCES = [
    "outputs/stage4_noise_adaptive_development_v1/seed_inventory.json",
    "outputs/stage4_noise_adaptive_development_v1/seed_audit.json",
    "outputs/stage4_noise_adaptive_development_v1/additional_development_seed_audit.json",
    "outputs/stage4c_cnn_noise_estimation_v1/seed_inventory.json",
    "outputs/stage4c_cnn_noise_estimation_v1/seed_audit.json",
    "outputs/stage5_independent_confirmation/seed_inventory.json",
    "outputs/stage5_independent_confirmation/seed_audit.json",
    "outputs/stage5_preexecution_v1/seed_inventory.json",
    "outputs/stage5_preexecution_v1/STAGE5_V2_CONFIG.json",
    "outputs/stage5_preexecution_v1/POWER_RECOMPUTATION.json",
]
STATS = json.loads((HERE / "DESIGN_SIMULATION_CONFIG.json").read_text(encoding="utf-8"))
BENCH = json.loads((HERE / "BENCHMARK_CONFIG.json").read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect_ints(obj):
    if isinstance(obj, bool):
        return
    if isinstance(obj, int):
        yield obj
    elif isinstance(obj, float) and obj.is_integer():
        yield int(obj)
    elif isinstance(obj, list):
        for value in obj:
            yield from collect_ints(value)
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from collect_ints(value)


historical: set[int] = set()
source_records = []
for rel in SOURCES:
    path = ROOT / rel
    if not path.is_file():
        raise FileNotFoundError(f"required, nonsealed seed record missing: {rel}")
    parsed = json.loads(path.read_text(encoding="utf-8"))
    values = {value for value in collect_ints(parsed) if value >= 1_000_000}
    historical |= values
    source_records.append({"path": rel, "sha256": sha(path), "integer_values_ge_1m_scanned": len(values)})

welch_seeds = [int(STATS["rng"]["welch_seed_base"]) + i * 100 for i in range(len(STATS["scenarios"]))]
bootstrap_seeds = [int(STATS["rng"]["bootstrap_seed_base"]) + i * 100 for i in range(len(STATS["bootstrap_t_scenarios"]))]
p0_seed = int(STATS["rng"]["p0_seed_base"])
analysis_seeds = welch_seeds + bootstrap_seeds + [p0_seed]
preflight_fixture_seeds = [8610000001]  # consumed only for the one-shot large-integer Stim seed acceptance check
streams = []
base = int(BENCH["seed_allocation"]["base"])
roots = int(BENCH["roots_per_probability"])
for p_index, probability in enumerate(BENCH["probabilities"]):
    for root in range(roots):
        i = p_index * roots + root
        calibration = base + 2 * i
        evaluation = calibration + 1
        streams.extend([
            {"kind": "calibration_detector_only", "probability": float(probability), "root": root, "seed": calibration},
            {"kind": "paired_evaluation_detector_observable", "probability": float(probability), "root": root, "seed": evaluation},
        ])
proposed = set(analysis_seeds + preflight_fixture_seeds) | {int(row["seed"]) for row in streams}
if len(proposed) != len(analysis_seeds) + len(preflight_fixture_seeds) + len(streams):
    raise RuntimeError("proposed statistical/benchmark seed streams collide internally")
collisions = sorted(proposed & historical)
if collisions:
    raise RuntimeError(f"disposable validation seed collision(s): {collisions}")

inventory = {
    "purpose": "design-simulation RNG and disposable full-pipeline benchmark only",
    "stage5_evaluation_seed_namespace_used": False,
    "sealed_test_accessed": False,
    "historical_seed_collision_count": len(collisions),
    "historical_seed_collisions": collisions,
    "analysis_rngs": {
        "welch_scenario_seeds": welch_seeds,
        "bootstrap_t_scenario_seeds": bootstrap_seeds,
        "p0_safety_seed": p0_seed,
    },
    "preflight_fixture_seeds_already_consumed": preflight_fixture_seeds,
    "benchmark_streams": streams,
    "unique_proposed_seed_count": len(proposed),
    "historical_union_count_scanned": len(historical),
    "historical_sources": source_records,
}
(HERE / "VALIDATION_SEED_INVENTORY.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
print(f"PASS: {len(proposed)} proposed seeds unique; {len(historical)} historical values scanned; 0 collisions")
print("Sources: " + ", ".join(SOURCES))
