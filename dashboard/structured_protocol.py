"""Frozen, independent seed allocation for the proposed 100K diagnostic."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

from seed_protocol import MAX_STIM_SEED, batches, historical_seeds

REGIMES = ("x_biased", "balanced", "z_biased")
TOTAL_SHOTS = {"train": 70_000, "validation": 15_000, "test": 15_000}
REGIME_SHOTS = {
    "train": {"x_biased": 23_334, "balanced": 23_333, "z_biased": 23_333},
    "validation": {regime: 5_000 for regime in REGIMES},
    "test": {regime: 5_000 for regime in REGIMES},
}
ROOTS = {
    "train": {"x_biased": 1_000_000_001, "balanced": 1_010_000_001, "z_biased": 1_020_000_001},
    "validation": {"x_biased": 1_030_000_001, "balanced": 1_040_000_001, "z_biased": 1_050_000_001},
    "test": {"x_biased": 1_060_000_001, "balanced": 1_070_000_001, "z_biased": 1_080_000_001},
}
MODEL_SEED = 1_090_000_001
BATCH_SIZE = 256


def build_inventory(prior_allocations: list[dict] | None = None) -> dict:
    streams = []
    for split in ("train", "validation", "test"):
        for regime in REGIMES:
            count = REGIME_SHOTS[split][regime]
            n_batches = batches(count, BATCH_SIZE)
            root = ROOTS[split][regime]
            streams.append({"split": split, "regime": regime, "root": root,
                            "shots": count, "batch_size": BATCH_SIZE,
                            "batch_count": n_batches,
                            "seed_range_inclusive": [root, root + n_batches - 1],
                            "seeds": list(range(root, root + n_batches))})
    all_seeds = [seed for stream in streams for seed in stream["seeds"]] + [MODEL_SEED]
    collisions = []
    if len(all_seeds) != len(set(all_seeds)):
        collisions.append({"type": "duplicate_proposed_seed", "values": sorted(
            seed for seed in set(all_seeds) if all_seeds.count(seed) > 1)})
    if any(seed < 1 or seed > MAX_STIM_SEED for seed in all_seeds):
        collisions.append({"type": "outside_stim_seed_range"})
    old_seeds = historical_seeds()
    old_hits = sorted(set(all_seeds) & old_seeds)
    if old_hits:
        collisions.append({"type": "historical_seed_overlap", "values": old_hits})
    for prior in prior_allocations or []:
        for stream in streams:
            lo, hi = stream["seed_range_inclusive"]
            for prior_name, (prior_lo, prior_hi) in prior.get("stream_ranges_inclusive", {}).items():
                if max(lo, prior_lo) <= min(hi, prior_hi):
                    collisions.append({"type": "prior_dashboard_run_overlap", "split": stream["split"],
                                       "regime": stream["regime"], "prior_stream": prior_name,
                                       "overlap": [max(lo, prior_lo), min(hi, prior_hi)]})
    if MODEL_SEED in old_seeds:
        collisions.append({"type": "model_seed_historical_overlap", "value": MODEL_SEED})
    for prior in prior_allocations or []:
        for prior_name, (prior_lo, prior_hi) in prior.get("stream_ranges_inclusive", {}).items():
            if prior_lo <= MODEL_SEED <= prior_hi:
                collisions.append({"type": "model_seed_prior_dashboard_overlap", "prior_stream": prior_name,
                                   "value": MODEL_SEED})
    return {"allocation_rule": "One deterministic Stim seed per batch; each split/regime has an independent root.",
            "model_seed": MODEL_SEED, "stream_count": len(streams), "derived_seed_count_including_model": len(all_seeds),
            "unique_seed_count": len(set(all_seeds)), "historical_seed_values_checked": len(old_seeds),
            "streams": streams, "collisions": collisions, "passed": not collisions,
            "historical_coverage_limit": "Historical screening is limited to recoverable seed values and existing dashboard run manifests."}


def experiment_protocol() -> dict:
    return {"status": "prospective; not executed", "total_shots": sum(TOTAL_SHOTS.values()),
            "split_totals": TOTAL_SHOTS, "regimes": list(REGIMES), "shots_by_split_and_regime": REGIME_SHOTS,
            "noise_parameters": {"gate_p": 0.003, "measurement_p": 0.003, "bias_ratio": 10.0,
                                 "distance": 3, "rounds": 5, "memory_basis": "z"},
            "model_inputs": ["40 syndrome detector bits"],
            "model_targets": {"direct": "Stim logical-observable flip bit", "residual": "PyMatching prediction XOR observable flip"},
            "candidates": ["frozen PyMatching", "DirectMLP", "StructuredConv3DDecoder", "ResidualMLP"],
            "validation_policy": "Use validation only for model, threshold, and checkpoint selection. Compute equal-regime mean LER and a 95% stratified paired-shot bootstrap interval for candidate-minus-pooled-fixed; select a neural candidate only when mean LER is lower and the entire interval is below zero. Otherwise retain pooled-fixed.",
            "validation_uncertainty_note": "The bootstrap is conditional on one seed stream per regime and is a development selection aid, not seed-cluster inference.",
            "test_policy": "Do not generate or read any test samples until architecture, threshold, and checkpoint selection are frozen. Then report all three regimes and paired outcomes.",
            "class_imbalance_policy": "Report positive-target prevalence. Compare unweighted BCE with a positive weight computed from training-label prevalence only; assess thresholds on validation. Never estimate class weights from validation/test labels.",
            "limits": "A 100K-shot diagnostic can reveal gross collapse and regime sensitivity but is not powered to establish a small LER improvement."}


def experiment_configuration(inventory: dict) -> dict:
    return {"experiment_id": "qshift_structured_neural_100k_diagnostic_v1",
            "status": "prospective; no data generated",
            "total_unique_shots": 100_000,
            "memory_basis": "z", "distance": 3, "rounds": 5,
            "gate_p": 0.003, "measurement_p": 0.003, "bias_ratio": 10.0,
            "batch_size": BATCH_SIZE,
            "regimes": list(REGIMES),
            "shot_allocation": REGIME_SHOTS,
            "decoder_bank": ["phase2b_frozen_pymatching_z_index_2", "DirectMLP",
                             "StructuredConv3DDecoder", "ResidualMLP"],
            "structured_decoder_grid": {"channels": [8, 16], "dropout": [0.05]},
            "fit_schedule": ["DirectMLP + unweighted BCE", "ResidualMLP + unweighted BCE",
                            "StructuredConv3DDecoder for each channel count × each loss variant (4 fits)"],
            "optimizer": {"name": "AdamW", "learning_rate": 0.001,
                          "weight_decay": 0.0001, "max_epochs": 2,
                          "early_stopping_patience": 1, "loss": "BCEWithLogitsLoss"},
            "loss_variants": ["unweighted BCEWithLogitsLoss", "BCEWithLogitsLoss with positive weight from training split only"],
            "output_thresholds": [0.25, 0.5, 0.75],
            "threshold_selection": "Validation only; choose by equal-regime paired LER, no test threshold sweep.",
            "primary_selection": "Validation equal-regime LER with 95% stratified paired-shot bootstrap; adopt neural only if lower and the entire candidate-minus-fixed interval is below zero; otherwise retain fixed.",
            "validation_uncertainty_note": "Single seed root per regime; shot-bootstrap intervals are not independent-root uncertainty estimates.",
            "test_access": "Test stream is reserved in the inventory and must remain unopened until architecture, checkpoint, objective, and threshold are frozen.",
            "seed_collision_audit_passed": inventory["passed"],
            "limitations": ["Single distance and basis.",
                            "Only 5,000 test shots per regime; descriptive diagnostic, not a powered superiority test.",
                            "No regime ID, gate probability, measurement probability, or labels are model inputs."]}


def write_outputs(directory: Path, prior_allocations: list[dict] | None = None) -> tuple[Path, Path, Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    inventory = build_inventory(prior_allocations)
    protocol = experiment_protocol()
    protocol["seed_inventory_passed"] = inventory["passed"]
    config = experiment_configuration(inventory)
    protocol_path = directory / "structured_diagnostic_protocol.json"
    inventory_path = directory / "structured_seed_inventory.json"
    config_path = directory / "structured_diagnostic_config.json"
    protocol_path.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
    inventory_path.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    sources = ("structured_decoder.py", "structured_protocol.py", "analyze_saved_run.py",
               "simulator.py", "models.py", "seed_protocol.py")
    base = Path(__file__).resolve().parent
    hashes = {name: hashlib.sha256((base / name).read_bytes()).hexdigest() for name in sources}
    freeze = {"status": "prospective protocol freeze; no final test samples generated",
              "sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in (protocol_path, inventory_path, config_path)},
              "source_sha256": hashes}
    freeze_path = directory / "structured_diagnostic_freeze.json"
    freeze_path.write_text(json.dumps(freeze, indent=2) + "\n", encoding="utf-8")
    return protocol_path, inventory_path, config_path, freeze_path
