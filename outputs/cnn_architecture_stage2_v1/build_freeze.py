"""Create/verify the prospective Stage 2 seed audit and hash freeze.

This utility only reads protocol/source metadata and hashes files. It does not
construct circuits, sample Stim shots, train models, or access test material.
It refuses to overwrite a previously created inventory, audit, or freeze.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
MAX_STIM_SEED = 2_147_483_647
BASE = 2_000_000_000
ROOT_STRIDE = 1_000
ROOTS = 5
CONDITIONS = ("nominal", "synthetic_spatial_burst")
MODELS = (
    "historical_residual_position_cnn",
    "residual_position_v2",
    "factorized_spatiotemporal_residual",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def write_or_verify(path: Path, expected: dict) -> None:
    encoded = json.dumps(expected, indent=2) + "\n"
    if path.exists():
        actual = json.loads(path.read_text(encoding="utf-8"))
        if actual != expected:
            raise RuntimeError(f"Refusing to overwrite frozen metadata: {path.relative_to(ROOT)}")
        return
    path.write_text(encoded, encoding="utf-8", newline="\n")


def derive_inventory() -> dict:
    streams: list[dict] = []
    sample_offsets = {
        "training": {"nominal": 1, "synthetic_spatial_burst": 2},
        "monitor": {"nominal": 10, "synthetic_spatial_burst": 11},
        "probability_calibration": {"nominal": 20, "synthetic_spatial_burst": 21},
        "threshold_selection": {"nominal": 30, "synthetic_spatial_burst": 31},
        "final_development_evaluation": {"nominal": 40, "synthetic_spatial_burst": 41},
    }
    for root_index in range(ROOTS):
        root_id = f"dev-root-{root_index:02d}"
        root_base = BASE + ROOT_STRIDE * root_index
        for split, by_condition in sample_offsets.items():
            for condition in CONDITIONS:
                streams.append({
                    "root_id": root_id,
                    "kind": "stim_sample_stream",
                    "split": split,
                    "condition": condition,
                    "seed": root_base + by_condition[condition],
                })
        for model_index, model in enumerate(MODELS):
            for purpose, offset_delta in (("torch", 0), ("balanced_sampling", 1), ("batch_order", 2)):
                streams.append({
                    "root_id": root_id,
                    "kind": "model_rng_stream",
                    "model": model,
                    "purpose": purpose,
                    "seed": root_base + 100 + 3 * model_index + offset_delta,
                })
    return {
        "protocol_version": "1.0-prospective-freeze",
        "status": "reserved_not_sampled",
        "allocation_rule": "seed = 2000000000 + 1000*root_index + stream_offset; root_index=0..4; all offsets are explicitly listed by this inventory generator",
        "root_ids": [f"dev-root-{i:02d}" for i in range(ROOTS)],
        "condition_order": list(CONDITIONS),
        "model_order": list(MODELS),
        "stream_count": len(streams),
        "unique_seed_count": len({item["seed"] for item in streams}),
        "max_stim_seed": MAX_STIM_SEED,
        "streams": streams,
        "independent_test_seed_allocated": False,
        "shots_generated": 0,
    }


def historical_seed_audit(candidate_seeds: set[int]) -> dict:
    history_path = ROOT / "outputs/headroom_feasibility/HISTORICAL_SEED_SCAN.json"
    phase3a_path = ROOT / "outputs/phase3a_correlated_noise_preflight/PREFLIGHT_RESULTS.json"
    stage1_seed_path = ROOT / "outputs/cnn_architecture_stage1_v1/seed_inventory.json"
    history = json.loads(history_path.read_text(encoding="utf-8"))
    phase3a = json.loads(phase3a_path.read_text(encoding="utf-8"))
    stage1 = json.loads(stage1_seed_path.read_text(encoding="utf-8"))

    historical = {int(x) for x in history.get("recoverable_unique_seed_values", [])}
    p3 = phase3a["historical_seed_screen"]
    phase3a_values = sorted({
        *map(int, p3["formal_preflight_seeds"]),
        *map(int, p3["unit_test_fixture_seeds"]),
        *map(int, p3["pre_configuration_exploratory_seed_reuse"]["seeds_used"]),
    })
    stage1_values = sorted(map(int, stage1["streams"].values()))
    historical_collisions = sorted(candidate_seeds & historical)
    phase3a_collisions = sorted(candidate_seeds & set(phase3a_values))
    stage1_collisions = sorted(candidate_seeds & set(stage1_values))
    all_seeds = candidate_seeds
    result = {
        "status": "PASS" if not (historical_collisions or phase3a_collisions or stage1_collisions) else "FAIL",
        "historical_scan_source": {
            "path": history_path.relative_to(ROOT).as_posix(),
            "files_scanned_in_source_record": int(history["files_scanned"]),
            "recoverable_unique_seed_count": len(historical),
            "source_sha256": sha256_file(history_path),
        },
        "phase3a_seed_source": {
            "path": phase3a_path.relative_to(ROOT).as_posix(),
            "explicit_non_test_seed_values": phase3a_values,
            "source_sha256": sha256_file(phase3a_path),
        },
        "stage1_seed_source": {
            "path": stage1_seed_path.relative_to(ROOT).as_posix(),
            "diagnostic_seed_values": stage1_values,
            "source_sha256": sha256_file(stage1_seed_path),
        },
        "candidate_seed_count": len(all_seeds),
        "candidate_seeds_unique": len(all_seeds) == len({int(x) for x in all_seeds}),
        "candidate_seeds_within_stim_range": all(1 <= x <= MAX_STIM_SEED for x in all_seeds),
        "within_allocation_collisions": [],
        "historical_collisions": historical_collisions,
        "phase3a_collisions": phase3a_collisions,
        "stage1_diagnostic_collisions": stage1_collisions,
        "independent_test_files_or_seed_allocations_opened": False,
        "coverage_limit": "Only the archived recoverable-seed scan and explicit non-test Phase 3A/Stage 1 diagnostic metadata listed here were examined. Unrecorded historical RNG calls cannot be ruled out; no independent-test files or allocations were inspected.",
    }
    return result


def main() -> None:
    config_path = HERE / "stage2_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    shot_plan = config["shots_per_root_condition"]
    roots = int(config["roots"]["count"])
    conditions = int(config["conditions_per_root"])
    computed_by_split = {name: roots * conditions * int(count) for name, count in shot_plan.items()}
    computed_total = sum(computed_by_split.values())
    if computed_total != 260000 or computed_total != int(config["total_unique_shot_ceiling"]):
        raise RuntimeError(f"The frozen shot plan must equal its 260,000 ceiling, got {computed_total}")
    if computed_by_split != config.get("total_unique_shots_by_split"):
        raise RuntimeError(f"Per-split shot totals do not match the declared plan: {computed_by_split}")
    if config.get("independent_test", {}).get("access_permitted") is not False:
        raise RuntimeError("Independent-test access must remain prohibited")

    inventory = derive_inventory()
    inventory_path = HERE / "seed_inventory.json"
    write_or_verify(inventory_path, inventory)

    seeds = [int(item["seed"]) for item in inventory["streams"]]
    if len(seeds) != len(set(seeds)):
        raise RuntimeError("Stage 2 seed inventory contains duplicate seed values")
    audit = historical_seed_audit(set(seeds))
    write_or_verify(HERE / "seed_audit.json", audit)
    if audit["status"] != "PASS":
        raise RuntimeError(f"Seed collision audit failed: {audit}")

    source_paths = [
        "outputs/cnn_architecture_stage2_v1/CNN_STAGE2_FROZEN_PROTOCOL.md",
        "outputs/cnn_architecture_stage2_v1/CNN_STAGE2_READINESS_REPORT.md",
        "outputs/cnn_architecture_stage2_v1/stage2_config.json",
        "outputs/cnn_architecture_stage2_v1/seed_inventory.json",
        "outputs/cnn_architecture_stage2_v1/seed_audit.json",
        "outputs/cnn_architecture_stage2_v1/build_freeze.py",
        "outputs/cnn_architecture_stage1_v1/CNN_ARCHITECTURE_AUDIT.md",
        "outputs/cnn_architecture_stage1_v1/CNN_IMPROVEMENT_DESIGN.md",
        "outputs/cnn_architecture_stage1_v1/CNN_PREFLIGHT_RESULTS.md",
        "outputs/cnn_architecture_stage1_v1/CNN_EXPERIMENT_PROTOCOL.md",
        "outputs/cnn_architecture_stage1_v1/preflight_config.json",
        "outputs/cnn_architecture_stage1_v1/seed_inventory.json",
        "outputs/cnn_architecture_stage1_v1/PREFLIGHT_RESULTS.json",
        "outputs/cnn_architecture_stage1_v1/cnn_architectures.py",
        "outputs/cnn_architecture_stage1_v1/run_preflight.py",
        "outputs/cnn_architecture_stage1_v1/tests/test_cnn_architectures.py",
        "outputs/neural_decoder_diagnostic/autonomous_development/experiment.py",
        "dashboard/structured_decoder.py",
        "outputs/phase2b_pauli_bias/noise_model.py",
        "outputs/phase3a_correlated_noise_preflight/simulator.py",
        "outputs/phase3a_correlated_noise_preflight/PREFLIGHT_RESULTS.json",
        "outputs/headroom_feasibility/HISTORICAL_SEED_SCAN.json",
        "dashboard/seed_protocol.py",
    ]
    files = []
    for relative in source_paths:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"Required freeze input is missing: {relative}")
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256_file(path)})

    previous = json.loads((HERE / "FREEZE.json").read_text(encoding="utf-8")) if (HERE / "FREEZE.json").exists() else None
    created_utc = previous["created_utc"] if previous else datetime.now(timezone.utc).isoformat()
    freeze_core = {
        "protocol_version": "1.0-prospective-freeze",
        "status": "FROZEN_NOT_EXECUTED_NOT_READY_FOR_TRAINING",
        "created_utc": created_utc,
        "freeze_scope": "prospective development protocol only; no samples generated",
        "protocol_id_sha256": hashlib.sha256(canonical_bytes({"files": files, "inventory": inventory})).hexdigest(),
        "seed_count": len(seeds),
        "unique_seed_count": len(set(seeds)),
        "seed_collision_audit": audit["status"],
        "planned_unique_shot_ceiling": computed_total,
        "shots_generated": 0,
        "training_started": False,
        "final_development_data_accessed": False,
        "independent_test_seed_allocated": False,
        "independent_test_accessed": False,
        "source_and_protocol_files": files,
        "execution_blocker": "No Stage 2 runner, end-to-end split-isolation/resume tests, or throughput dry run exists yet.",
        "freeze_finalized": True,
    }
    freeze_path = HERE / "FREEZE.json"
    if previous is not None:
        chain = list(previous.get("superseded_freeze_sha256s", []))
        if previous.get("supersedes_pretest_freeze_sha256"):
            chain.append(previous["supersedes_pretest_freeze_sha256"])
        if chain:
            freeze_core["superseded_freeze_sha256s"] = list(dict.fromkeys(chain))
        if previous != freeze_core:
            if (previous.get("shots_generated", 0) != 0 or previous.get("training_started")
                    or previous.get("final_development_data_accessed")
                    or previous.get("independent_test_accessed")):
                raise RuntimeError("Existing finalized/used FREEZE.json differs from current inputs; refusing to overwrite it")
            chain.append(sha256_file(freeze_path))
            freeze_core["superseded_freeze_sha256s"] = list(dict.fromkeys(chain))
            freeze_path.write_text(json.dumps(freeze_core, indent=2) + "\n", encoding="utf-8", newline="\n")
    else:
        freeze_path.write_text(json.dumps(freeze_core, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "freeze": freeze_path.relative_to(ROOT).as_posix(),
        "status": freeze_core["status"],
        "seed_count": len(seeds),
        "seed_unique": len(set(seeds)) == len(seeds),
        "collision_audit": audit["status"],
        "files_hashed": len(files),
        "shots_generated": 0,
        "training_started": False,
        "independent_test_accessed": False,
        "protocol_id_sha256": freeze_core["protocol_id_sha256"],
    }, indent=2))


if __name__ == "__main__":
    main()
