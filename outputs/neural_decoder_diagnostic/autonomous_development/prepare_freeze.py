"""Build the full seed inventory and pre-sampling source/config freeze."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "dashboard"))

from seed_protocol import MAX_STIM_SEED, historical_seeds
from structured_protocol import build_inventory
from structured_training import inventory_seed_values


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(obj, path):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def make_inventory(cfg):
    regimes = cfg["regimes"]
    roots = int(cfg["independent_roots"])
    batch = 1024
    streams, all_seeds = [], []
    max_train = max(cfg["learning_curve_shots_per_regime"])
    val_counts = cfg["validation_shots_per_regime_per_root"]
    split_order = ["monitor", "calibration", "threshold_selection", "final_development_evaluation"]
    for root_i in range(roots):
        for ri, regime in enumerate(regimes):
            root = 1_900_000_001 + root_i * 150_000 + ri * 30_000
            seeds = list(range(root, root + math.ceil(max_train / batch)))
            streams.append({"root_id": root_i, "split": "train", "regime": regime,
                            "shots": max_train, "batch_size": batch, "root": root, "seeds": seeds})
            all_seeds.extend(seeds)
            for si, split in enumerate(split_order):
                amount = int(val_counts[split])
                val_root = 2_000_000_001 + root_i * 150_000 + ri * 30_000 + si * 5_000
                val_seeds = list(range(val_root, val_root + math.ceil(amount / batch)))
                streams.append({"root_id": root_i, "split": split, "regime": regime,
                                "shots": amount, "batch_size": batch, "root": val_root, "seeds": val_seeds})
                all_seeds.extend(val_seeds)
    model_streams = []
    index = 0
    for root_i in range(roots):
        for model in cfg["learning_curve_models"]:
            for size in cfg["learning_curve_shots_per_regime"]:
                seed = 2_100_000_001 + index * 10
                model_streams.append({"root_id": root_i, "model": model, "train_size_per_regime": size,
                                      "torch_seed": seed, "sampling_seed": seed + 1, "shuffle_seed": seed + 2})
                all_seeds.extend((seed, seed + 1, seed + 2)); index += 1
        seed = 2_100_000_001 + index * 10
        model_streams.append({"root_id": root_i, "model": "residual_position_cnn", "train_size_per_regime": 10_000,
                              "torch_seed": seed, "sampling_seed": seed + 1, "shuffle_seed": seed + 2})
        all_seeds.extend((seed, seed + 1, seed + 2)); index += 1
    # Dry run has separate actual Stim streams for every regime/split and its
    # own model RNG namespace. These are explicitly inventory entries; no
    # runtime-derived seed is left implicit.
    dry_streams = []
    dry_names = ("train", "monitor", "calibration", "threshold_selection", "final_development_evaluation")
    dry_counts = {"train": cfg["dry_run"]["train_shots"], "monitor": cfg["dry_run"]["monitor_shots"],
                  "calibration": cfg["dry_run"]["calibration_shots"],
                  "threshold_selection": cfg["dry_run"]["threshold_shots"],
                  "final_development_evaluation": cfg["dry_run"]["final_eval_shots"]}
    for i, split in enumerate(dry_names):
        for ri, regime in enumerate(regimes):
            seed = 1_820_000_001 + 100 * i + ri
            dry_streams.append({"split": split, "regime": regime, "shots": dry_counts[split], "seed": seed})
            all_seeds.append(seed)
    dry_model_seed = 2_120_000_001
    dry_rng_seeds = [dry_model_seed, dry_model_seed + 1, dry_model_seed + 2]
    diagnostic_seeds = [1_830_000_001, 1_830_000_002, 1_830_000_003]
    dry_diagnostic_seeds = [1_840_000_001, 1_840_000_002, 1_840_000_003]
    all_seeds.extend(dry_rng_seeds + diagnostic_seeds + dry_diagnostic_seeds)
    hist = historical_seeds()
    prepared = inventory_seed_values(build_inventory())
    from collections import Counter
    duplicates = Counter(all_seeds)
    collisions = {"duplicate_derived_seeds": sorted(s for s, n in duplicates.items() if n > 1),
                  "historical_seed_collisions": sorted(set(all_seeds) & hist),
                  "prepared_100k_namespace_collisions": sorted(set(all_seeds) & prepared),
                  "outside_stim_range": sorted(s for s in all_seeds if not 1 <= s <= MAX_STIM_SEED)}
    return {"status": "prospective inventory; full experiment not started", "streams": streams,
            "model_streams": model_streams, "dry_run_streams": dry_streams,
            "dry_run_model_rng_seeds": dry_rng_seeds, "circuit_diagnostic_seeds": diagnostic_seeds,
            "dry_run_circuit_diagnostic_seeds": dry_diagnostic_seeds,
            "unique_derived_seed_count": len(set(all_seeds)), "proposed_derived_seed_count": len(all_seeds),
            "recoverable_historical_values_checked": len(hist), "prepared_100k_values_checked": len(prepared),
            "collisions": collisions, "passed": not any(collisions.values()),
            "test_stream": "No test stream is present in this inventory; independent test data are not allocated or accessed."}


def main():
    freeze_path = OUT / "FREEZE_FINAL_V3.json"
    if freeze_path.exists():
        raise SystemExit("FREEZE_FINAL_V3.json already exists; refusing to replace the active pre-sampling freeze.")
    cfg_path = OUT / "config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    inv = make_inventory(cfg)
    inventory_path = OUT / "SEED_INVENTORY.json"
    if inventory_path.exists():
        if json.loads(inventory_path.read_text(encoding="utf-8")) != inv:
            raise SystemExit("Existing seed inventory differs; preserving it and refusing an implicit protocol change.")
    else:
        atomic_json(inv, inventory_path)
    if not inv["passed"]:
        print(json.dumps(inv["collisions"], indent=2))
        raise SystemExit("Seed preflight failed; do not sample.")
    sources = ["prepare_freeze.py", "controller.py", "experiment.py", "tests/test_controller.py",
               "config.json", "SEED_INVENTORY.json", "PROTOCOL.md", "ANALYSIS_PLAN.json"]
    external = ["dashboard/structured_decoder.py", "dashboard/structured_training.py", "dashboard/models.py",
                "dashboard/simulator.py", "dashboard/seed_protocol.py", "dashboard/structured_protocol.py",
                "outputs/phase2b_pauli_bias/noise_model.py", "outputs/phase2b_pauli_bias/decoder_bank.py",
                "outputs/phase2b_pauli_bias/PHASE2B_PROTOCOL.md", "outputs/phase2b_pauli_bias/CALIBRATION_SELECTION.json",
                "outputs/neural_decoder_diagnostic/root_cause_analysis/position_preserving_cnn/POSITIONAL_CNN_REPORT.md",
                "outputs/neural_decoder_diagnostic/root_cause_analysis/position_preserving_cnn/VERIFIED_RESULTS.json"]
    hashes = {rel: sha(OUT / rel) for rel in sources}
    hashes.update({rel: sha(ROOT / rel) for rel in external})
    freeze = {"status": "FROZEN BEFORE FULL EXPERIMENT; superseding freeze after dry-run schema validation correction",
              "supersedes": ["FREEZE.json", "FREEZE_FINAL.json", "FREEZE_FINAL_V2.json"],
              "prior_dry_run_evidence": "Preserved under dry_run/, dry_run_v2/, and dry_run_v3/ with versioned verification records; this freeze governs future full-run sampling.",
              "created_unix": time.time(), "config_sha256": sha(cfg_path),
              "seed_inventory_sha256": sha(OUT / "SEED_INVENTORY.json"),
              "source_sha256": hashes,
              "protocol_sha256": sha(OUT / "PROTOCOL.md"),
              "analysis_plan_sha256": sha(OUT / "ANALYSIS_PLAN.json"),
              "software": {"python": sys.version, "platform": sys.platform},
              "packages": {name: importlib.metadata.version(name) for name in
                           ("torch", "stim", "pymatching", "numpy", "psutil")},
              "python_executable": sys.executable,
              "cuda_available_at_freeze": bool(torch.cuda.is_available()),
              "cuda_device_name_at_freeze": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
              "partitions": {"train": "nested prefix of 30000 shots per regime/root",
                             "monitor": "4000 per regime/root", "calibration": "3000 per regime/root",
                             "threshold_selection": "3000 per regime/root",
                             "final_development_evaluation": "10000 per regime/root",
                             "independent_test": "not allocated and prohibited"},
              "full_experiment_authorized": False,
              "independent_test_access": "prohibited and not allocated",
              "protocol_summary": "5 roots; 3 learning-curve models x 3 nested train budgets; separate PM-assisted residual pilot; 4 independent validation roles; 6h wall/4h GPU hard limits."}
    atomic_json(freeze, freeze_path)
    print(json.dumps({"freeze": str(freeze_path), "status": freeze["status"],
                      "unique_seed_count": inv["unique_derived_seed_count"],
                      "collisions": inv["collisions"], "source_hashes": len(hashes)}, indent=2))


if __name__ == "__main__":
    main()
