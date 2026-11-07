"""Create a non-test Stage 4 feasibility seed ledger and audit it."""
from __future__ import annotations

import json
import argparse
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT_INV = HERE / "seed_inventory.json"
OUT_AUDIT = HERE / "seed_audit.json"
OUT_FUTURE = HERE / "STAGE4_PROPOSED_SEED_PLAN.json"
INITIAL_AUDIT = HERE / "SEED_AUDIT_INITIAL_EXTRACTION_BUG.json"
INITIAL_INV = HERE / "SEED_INVENTORY_INITIAL.json"
INITIAL_FUTURE = HERE / "STAGE4_PROPOSED_SEED_PLAN_INITIAL.json"

STREAMS: list[dict] = []
_next = 4_100_000_001


def add(kind: str, **meta) -> None:
    global _next
    STREAMS.append({"seed": _next, "kind": kind, **meta})
    _next += 1


for p in (0.002, 0.010, 0.018):
    for rep in range(2):
        add("profile_calibration_detectors", probability=p, replicate=rep, shots=2000)
for p in (0.006, 0.014):
    for root in range(3):
        add("unseen_parameter_calibration_detectors", probability=p, root=root, shots=2000)
        add("unseen_parameter_paired_evaluation", probability=p, root=root, shots=4000)
add("bootstrap_rng", purpose="calibration_row_percentile_interval", shots=0)

assert len(STREAMS) == 19
assert len({x["seed"] for x in STREAMS}) == 19

SOURCES = [
    "outputs/cnn_architecture_stage2_v1/seed_inventory.json",
    "outputs/cnn_architecture_stage2_v1/seed_audit.json",
    "outputs/cnn_stage3_residual_gate_v1/seed_inventory.json",
    "outputs/cnn_stage3_residual_gate_v1/seed_audit.json",
    "outputs/phase3a_correlated_noise_preflight/config.json",
    "outputs/phase3a_correlated_noise_preflight/PREFLIGHT_RESULTS.json",
]


def seed_values(obj) -> set[int]:
    found: set[int] = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            k = key.lower()
            if k in {"seed", "seeds", "seed_values", "historical_seed_values",
                     "formal_preflight_seeds", "unit_test_fixture_seeds",
                     "diagnostic_seed_values", "explicit_non_test_seed_values"}:
                def collect(v):
                    if isinstance(v, bool):
                        return
                    if isinstance(v, int):
                        if 0 <= v < 2**32:
                            found.add(v)
                    elif isinstance(v, list):
                        for item in v:
                            collect(item)
                    elif isinstance(v, dict):
                        for kk, vv in v.items():
                            if kk.lower() == "seed":
                                collect(vv)
                collect(value)
            found.update(seed_values(value))
    elif isinstance(obj, list):
        for item in obj:
            found.update(seed_values(item))
    return found


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-before-freeze", action="store_true")
    args = parser.parse_args()
    existing = any(p.exists() for p in (OUT_INV, OUT_AUDIT, OUT_FUTURE))
    if existing:
        if not args.refresh_before_freeze:
            raise RuntimeError("seed records already exist; use --refresh-before-freeze only before freeze/sampling")
        if (HERE / "STAGE4_FEASIBILITY_FREEZE.json").exists() or (HERE / "run_v1").exists():
            raise RuntimeError("cannot refresh seed records after freezing or sampling")
        for source, backup in ((OUT_INV, INITIAL_INV), (OUT_AUDIT, INITIAL_AUDIT), (OUT_FUTURE, INITIAL_FUTURE)):
            if source.exists() and not backup.exists():
                shutil.copy2(source, backup)
    historical: set[int] = set()
    source_records = []
    for rel in SOURCES:
        p = REPO / rel
        if not p.is_file():
            raise FileNotFoundError(rel)
        data = json.loads(p.read_text(encoding="utf-8"))
        vals = seed_values(data)
        historical |= vals
        source_records.append({"path": rel, "metadata_only": True,
                               "seed_values_extracted": len(vals)})
    candidates = [int(row["seed"]) for row in STREAMS]
    collisions = sorted(set(candidates) & historical)
    if collisions:
        raise RuntimeError(f"historical seed collisions: {collisions}")
    proposed = []
    future_seed = 4_200_000_001
    for p in (0.0, 0.01, 0.02):
        for root in range(3):
            proposed.append({"seed": future_seed, "kind": "profile_development_detectors",
                             "probability": p, "root": root, "shots": 2000})
            future_seed += 1
    for p in (0.0, 0.004, 0.008, 0.012, 0.016):
        for root in range(7):
            proposed.append({"seed": future_seed, "kind": "stage4_calibration_detectors",
                             "probability": p, "root": root, "shots": 2000})
            future_seed += 1
            proposed.append({"seed": future_seed, "kind": "stage4_paired_evaluation",
                             "probability": p, "root": root, "shots": 2500})
            future_seed += 1
    proposed_seeds = [int(row["seed"]) for row in proposed]
    future_historical_collisions = sorted(set(proposed_seeds) & historical)
    pilot_future_collisions = sorted(set(proposed_seeds) & set(candidates))
    if future_historical_collisions or pilot_future_collisions or len(set(proposed_seeds)) != len(proposed_seeds):
        raise RuntimeError(f"proposed Stage 4 seed collision: historical={future_historical_collisions}, pilot={pilot_future_collisions}")
    inventory = {
        "protocol": "qshift-stage4-noise-adaptive-feasibility-v1",
        "status": "reserved_before_sampling",
        "allocation_rule": "Sequential explicit IDs 4100000001 through 4100000019; no offsets or reuse.",
        "stream_count": len(STREAMS), "unique_seed_count": len(set(candidates)),
        "maximum_seed": max(candidates), "streams": STREAMS,
        "independent_test_allocated": False,
    }
    audit = {
        "status": "PASS_RECOVERABLE_METADATA_ONLY",
        "candidate_seed_count": len(candidates),
        "candidate_seeds_unique": len(set(candidates)) == len(candidates),
        "candidate_seeds_within_uint32": max(candidates) < 2**32,
        "within_allocation_collisions": [],
        "recoverable_historical_seed_count": len(historical),
        "historical_collisions": collisions,
        "initial_audit_superseded": INITIAL_AUDIT.exists(),
        "initial_audit_note": "The first pre-freeze seed extraction omitted nested seed records. It is preserved at SEED_AUDIT_INITIAL_EXTRACTION_BUG.json; this corrected audit recursively collects nested stream records.",
        "proposed_stage4_seed_count": len(proposed_seeds),
        "proposed_stage4_seed_range": [min(proposed_seeds), max(proposed_seeds)],
        "proposed_stage4_historical_collisions": future_historical_collisions,
        "proposed_stage4_pilot_collisions": pilot_future_collisions,
        "proposed_stage4_seeds_unique": len(set(proposed_seeds)) == len(proposed_seeds),
        "historical_metadata_files_examined": source_records,
        "independent_test_files_or_allocations_opened": False,
        "coverage_limit": "This audit reuses seed metadata from Stage 2, Stage 3, and Phase 3A only. Unrecorded historical RNG uses cannot be ruled out. No independent-test paths or artifacts were enumerated or opened.",
    }
    OUT_INV.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    OUT_AUDIT.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    OUT_FUTURE.write_text(json.dumps({
        "status": "PROPOSED_RESERVED_NOT_SAMPLED",
        "allocation_rule": "Explicit sequential seed IDs 4200000001 through 4200000079; stream records are listed below.",
        "stream_count": len(proposed), "unique_seed_count": len(set(proposed_seeds)),
        "seed_range": [min(proposed_seeds), max(proposed_seeds)],
        "planned_unique_shots": 175500,
        "independent_test_allocated": False,
        "streams": proposed,
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": audit["status"], "streams": len(candidates),
                      "recoverable_historical_values": len(historical), "collisions": collisions,
                      "proposed_stage4_streams": len(proposed), "proposed_collisions": future_historical_collisions}, indent=2))


if __name__ == "__main__":
    main()
