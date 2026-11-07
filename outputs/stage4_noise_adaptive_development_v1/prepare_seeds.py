"""Validate the reserved Stage 4 sample seeds and add analysis-only streams."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PREVIOUS_PLAN = REPO / "outputs/stage4_noise_adaptive_feasibility_v1/STAGE4_PROPOSED_SEED_PLAN.json"
OUT_INV = HERE / "seed_inventory.json"
OUT_AUDIT = HERE / "seed_audit.json"

HISTORICAL_SOURCES = [
    "outputs/cnn_architecture_stage2_v1/seed_inventory.json",
    "outputs/cnn_architecture_stage2_v1/seed_audit.json",
    "outputs/cnn_stage3_residual_gate_v1/seed_inventory.json",
    "outputs/cnn_stage3_residual_gate_v1/seed_audit.json",
    "outputs/phase3a_correlated_noise_preflight/config.json",
    "outputs/phase3a_correlated_noise_preflight/PREFLIGHT_RESULTS.json",
    "outputs/stage4_noise_adaptive_feasibility_v1/seed_inventory.json",
    "outputs/stage4_noise_adaptive_feasibility_v1/seed_audit.json",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect_seed_values(obj) -> set[int]:
    out: set[int] = set()
    exact = {"seed", "seeds", "seed_values", "historical_seed_values",
             "formal_preflight_seeds", "unit_test_fixture_seeds",
             "diagnostic_seed_values", "explicit_non_test_seed_values"}
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key.lower() in exact:
                def add(v):
                    if isinstance(v, bool):
                        return
                    if isinstance(v, int) and 0 <= v < 2**32:
                        out.add(v)
                    elif isinstance(v, (list, tuple)):
                        for item in v:
                            add(item)
                    elif isinstance(v, dict):
                        for k, item in v.items():
                            if k.lower() == "seed":
                                add(item)
                add(value)
            out.update(collect_seed_values(value))
    elif isinstance(obj, list):
        for item in obj:
            out.update(collect_seed_values(item))
    return out


def main() -> None:
    if OUT_INV.exists() or OUT_AUDIT.exists():
        raise RuntimeError("Stage 4 seed records already exist; refusing overwrite")
    prior = json.loads(PREVIOUS_PLAN.read_text(encoding="utf-8"))
    if prior["status"] != "PROPOSED_RESERVED_NOT_SAMPLED" or prior["stream_count"] != 79:
        raise RuntimeError("prior Stage 4 allocation plan has unexpected status/size")
    sample_streams = prior["streams"]
    sample_seeds = [int(x["seed"]) for x in sample_streams]
    if sample_seeds != list(range(4200000001, 4200000080)):
        raise RuntimeError("prior Stage 4 sample allocation differs from the frozen sequential plan")
    analysis_streams = [
        {"seed": 4200000080, "kind": "analysis_rng", "purpose": "stratified_root_cluster_bootstrap", "shots": 0},
        {"seed": 4200000081, "kind": "analysis_rng", "purpose": "primary_root_signflip_test", "shots": 0},
        {"seed": 4200000082, "kind": "analysis_rng", "purpose": "calibration_interval_bootstrap", "shots": 0},
    ]
    streams = sample_streams + analysis_streams
    all_seeds = [int(x["seed"]) for x in streams]
    if len(all_seeds) != len(set(all_seeds)) or max(all_seeds) >= 2**32:
        raise RuntimeError("within-allocation duplicate or Stim/RNG range overflow")

    historical: set[int] = set()
    source_records = []
    for rel in HISTORICAL_SOURCES:
        path = REPO / rel
        data = json.loads(path.read_text(encoding="utf-8"))
        values = collect_seed_values(data)
        historical.update(values)
        source_records.append({"path": rel, "sha256": sha256(path), "metadata_only": True,
                               "unique_seed_values_extracted": len(values)})
    collisions = sorted(set(all_seeds) & historical)
    if collisions:
        raise RuntimeError(f"collision with recoverable prior development streams: {collisions}")
    if set(sample_seeds) & set(all_seeds[79:]):
        raise RuntimeError("analysis RNG overlaps simulation seed")
    inventory = {
        "protocol": "qshift-stage4-full-development-v1",
        "status": "FROZEN_BEFORE_SAMPLING",
        "sample_seed_count": 79,
        "analysis_seed_count": 3,
        "total_unique_seed_count": len(all_seeds),
        "unique_seed_count": len(set(all_seeds)),
        "allocation_rule": "Preserve all 79 sample streams from the Stage 4 feasibility proposal exactly; append three analysis-only RNG seeds 4200000080-4200000082.",
        "independent_test_allocated": False,
        "streams": streams,
    }
    audit = {
        "status": "PASS_RECOVERABLE_METADATA_ONLY",
        "prior_proposed_sample_streams_reproduced_exactly": True,
        "proposed_plan_sha256": sha256(PREVIOUS_PLAN),
        "sample_stream_count": len(sample_seeds),
        "analysis_stream_count": len(analysis_streams),
        "candidate_seed_count": len(all_seeds),
        "candidate_seeds_unique": True,
        "candidate_seeds_within_uint32": True,
        "within_allocation_collisions": [],
        "recoverable_historical_seed_count": len(historical),
        "historical_collisions": collisions,
        "historical_metadata_files_examined": source_records,
        "independent_test_files_or_allocations_opened": False,
        "coverage_limit": "Only the listed Stage 2, Stage 3, Phase 3A and Stage 4 feasibility metadata were read. Unrecorded RNG calls cannot be ruled out. No independent-test path, allocation, sample, or label was enumerated or accessed.",
    }
    OUT_INV.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    OUT_AUDIT.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": audit["status"], "sample_streams": len(sample_seeds),
                      "analysis_streams": len(analysis_streams),
                      "historical_values": len(historical), "collisions": collisions}, indent=2))


if __name__ == "__main__":
    main()
