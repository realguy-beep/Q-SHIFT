"""Create and collision-screen the prospective Stage 4C RNG inventory.

Only explicitly listed historical development metadata are read. No test-data
directory or shot archive is enumerated or opened.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASE_SEED = 4_230_000_001

# The exact recoverable development-only files documented by the completed
# Stage 4B seed-coverage audit. Do not add sealed or independent-test paths.
HISTORICAL_FILES = [
    "outputs/cnn_architecture_stage2_v1/seed_inventory.json",
    "outputs/cnn_architecture_stage2_v1/seed_audit.json",
    "outputs/cnn_stage3_residual_gate_v1/seed_inventory.json",
    "outputs/cnn_stage3_residual_gate_v1/seed_audit.json",
    "outputs/phase3a_correlated_noise_preflight/config.json",
    "outputs/phase3a_correlated_noise_preflight/PREFLIGHT_RESULTS.json",
    "outputs/stage4_noise_adaptive_feasibility_v1/seed_inventory.json",
    "outputs/stage4_noise_adaptive_feasibility_v1/seed_audit.json",
    "outputs/cnn_architecture_stage1_v1/seed_inventory.json",
    "outputs/neural_decoder_diagnostic/root_cause_analysis/seed_inventory.json",
    "outputs/neural_decoder_diagnostic/root_cause_analysis/position_preserving_cnn/seed_inventory.json",
    "outputs/neural_decoder_diagnostic/structured_seed_inventory.json",
    "outputs/neural_decoder_diagnostic/structured_integration/dev_run_6000/structured_seed_inventory.json",
]
STAGE4B_FILES = [
    "outputs/stage4_noise_adaptive_development_v1/seed_inventory.json",
    "outputs/stage4_noise_adaptive_development_v1/seed_audit.json",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_seed_values(value, under_seed_key: bool = False) -> list[int]:
    found: list[int] = []
    if isinstance(value, dict):
        for key, item in value.items():
            is_seed_key = "seed" in str(key).lower() or "rng" in str(key).lower()
            found.extend(extract_seed_values(item, under_seed_key or is_seed_key))
    elif isinstance(value, list):
        for item in value:
            found.extend(extract_seed_values(item, under_seed_key))
    elif under_seed_key and isinstance(value, (int, float)) and not isinstance(value, bool):
        number = int(value)
        if float(value) == number and 0 <= number < 2**32:
            found.append(number)
    return found


def make_inventory() -> dict:
    streams: list[dict] = []
    next_seed = BASE_SEED
    for p in (0.0, 0.01, 0.02):
        for batch in range(120):
            streams.append({"kind": "training_detector_batch", "probability": p,
                            "batch": batch, "shots": 250, "seed": next_seed})
            next_seed += 1
    for p in (0.005, 0.015):
        for batch in range(60):
            streams.append({"kind": "validation_detector_batch", "probability": p,
                            "batch": batch, "shots": 250, "seed": next_seed})
            next_seed += 1
    for kind, shots in (("evaluation_calibration_detectors", 2000),
                        ("paired_evaluation_detectors_observables", 2500)):
        for p in (0.0, 0.004, 0.008, 0.012, 0.016):
            for root in range(7):
                streams.append({"kind": kind, "probability": p, "root": root,
                                "shots": shots, "seed": next_seed})
                next_seed += 1
    rngs = {
        "torch_initialization": next_seed,
        "torch_batch_order": next_seed + 1,
        "bootstrap": next_seed + 2,
        "primary_signflip": next_seed + 3,
    }
    all_seeds = [int(s["seed"]) for s in streams] + list(rngs.values())
    if len(all_seeds) != 554 or len(set(all_seeds)) != len(all_seeds):
        raise RuntimeError("prospective seed allocation is not 554 unique values")
    return {
        "status": "PROSPECTIVE_SCREENED_BEFORE_SAMPLING",
        "seed_algorithm": "Sequential uint32 seeds beginning at 4230000001; stream order is training, validation, calibration, paired evaluation, then analysis/model RNGs.",
        "base_seed": BASE_SEED,
        "stream_count": len(streams),
        "analysis_rngs": rngs,
        "unique_seed_count": len(all_seeds),
        "seed_min": min(all_seeds),
        "seed_max": max(all_seeds),
        "total_simulation_shots": sum(int(s["shots"]) for s in streams),
        "streams": streams,
    }


def audit_inventory(inventory: dict) -> dict:
    prospective = sorted([int(s["seed"]) for s in inventory["streams"]]
                         + [int(v) for v in inventory["analysis_rngs"].values()])
    if len(prospective) != len(set(prospective)):
        raise RuntimeError("internal Stage 4C seed collision")
    records = []
    historical: set[int] = set()
    for rel in HISTORICAL_FILES + STAGE4B_FILES:
        path = REPO / rel
        if not path.is_file():
            raise FileNotFoundError(f"required development seed metadata missing: {rel}")
        values = extract_seed_values(json.loads(path.read_text(encoding="utf-8")))
        historical.update(values)
        records.append({"path": rel, "sha256": sha256(path),
                        "unique_seed_values_extracted": len(set(values)),
                        "extracted_values": sorted(set(values)),
                        "scope": "recoverable development metadata; no shot arrays or sealed-test paths"})
    collisions = sorted(set(prospective) & historical)
    if collisions:
        raise RuntimeError(f"Stage 4C seeds collide with recoverable historical values: {collisions}")
    if any(s >= 2**32 or s < 0 for s in prospective):
        raise RuntimeError("Stim RNG seed outside uint32 range")
    # Enforce expected partition totals independently of stream generation.
    totals = {kind: sum(int(s["shots"]) for s in inventory["streams"] if s["kind"] == kind)
              for kind in sorted({s["kind"] for s in inventory["streams"]})}
    return {
        "status": "PASS_RECOVERABLE_DEVELOPMENT_METADATA",
        "historical_files_examined": records,
        "historical_unique_seed_count": len(historical),
        "stage4c_seed_count": len(prospective),
        "stage4c_seed_min": min(prospective),
        "stage4c_seed_max": max(prospective),
        "stage4c_seeds_unique": True,
        "stage4c_historical_collisions": collisions,
        "partition_shot_totals": totals,
        "total_simulation_shots": sum(totals.values()),
        "unresolved_coverage": "Only the development metadata listed above and Stage 4B's recoverable seed inventory were checked. Unrecorded RNG use cannot be ruled out. No independent-test allocation or raw sample was opened, read, or enumerated.",
    }


def main() -> None:
    inventory = make_inventory()
    audit = audit_inventory(inventory)
    (HERE / "seed_inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    (HERE / "seed_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: audit[k] for k in ("status", "historical_unique_seed_count", "stage4c_seed_count", "stage4c_seed_min", "stage4c_seed_max", "stage4c_historical_collisions", "partition_shot_totals", "total_simulation_shots")}, indent=2))


if __name__ == "__main__":
    main()
