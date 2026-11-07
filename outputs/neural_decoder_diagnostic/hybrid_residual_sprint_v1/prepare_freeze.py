"""Build and freeze the development-only seed inventory before sampling."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import sys
import time
from pathlib import Path

import torch

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
MAX_STIM_SEED = 2_147_483_647
HISTORICAL_DEV = [
    "outputs/neural_decoder_diagnostic/autonomous_development/SEED_INVENTORY.json",
    "outputs/neural_decoder_diagnostic/root_cause_analysis/seed_inventory.json",
]
LOCAL_FILES = ["FAILURE_ANALYSIS.md", "EXPERIMENT_PROTOCOL.md", "config.json",
               "prepare_freeze.py", "run_sprint.py", "verify_results.py", "tests/test_sprint.py"]
EXTERNAL_FILES = [
    "outputs/neural_decoder_diagnostic/autonomous_development/experiment.py",
    "outputs/neural_decoder_diagnostic/autonomous_development/PROTOCOL.md",
    "outputs/neural_decoder_diagnostic/autonomous_development/config.json",
    "dashboard/simulator.py", "dashboard/structured_decoder.py", "dashboard/models.py",
    "outputs/phase2b_pauli_bias/noise_model.py", "outputs/phase2b_pauli_bias/decoder_bank.py",
    "outputs/phase2b_pauli_bias/PHASE2B_PROTOCOL.md",
    "outputs/phase2b_pauli_bias/CALIBRATION_SELECTION.json",
]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(obj, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, allow_nan=False, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _seed_numbers(value) -> set[int]:
    if isinstance(value, bool):
        return set()
    if isinstance(value, int):
        return {value}
    if isinstance(value, str) and value.lstrip("+-").isdigit():
        return {int(value)}
    if isinstance(value, list):
        return set().union(*(_seed_numbers(x) for x in value)) if value else set()
    if isinstance(value, dict):
        return set().union(*(_seed_numbers(x) for x in value.values())) if value else set()
    return set()


def extract_dev_seeds(value) -> set[int]:
    seeds: set[int] = set()
    def visit(obj):
        if isinstance(obj, dict):
            split = str(obj.get("split", obj.get("partition", ""))).lower()
            if split in {"test", "independent_test", "heldout_test", "held-out-test"}:
                raise RuntimeError("Selected seed inventory unexpectedly contains a test partition.")
            for key, item in obj.items():
                if "seed" in str(key).lower():
                    seeds.update(_seed_numbers(item))
                if isinstance(item, (dict, list)):
                    visit(item)
        elif isinstance(obj, list):
            for item in obj:
                visit(item)
    visit(value)
    return {x for x in seeds if 0 < x <= MAX_STIM_SEED}


def make_inventory(cfg: dict) -> dict:
    sampling = cfg["sampling"]
    regimes = cfg["circuit"]["regimes"]
    batch = int(sampling["batch_size"])
    sizes = {"train": max(int(x) for x in sampling["train_budgets_per_regime_root"]),
             "monitor": int(sampling["monitor_shots_per_regime_root"]),
             "calibration": int(sampling["calibration_shots_per_regime_root"]),
             "threshold_selection": int(sampling["threshold_selection_shots_per_regime_root"]),
             "final_development_evaluation": int(sampling["final_development_shots_per_regime_root"])}
    offsets = {"train": 0, "monitor": 100, "calibration": 200,
               "threshold_selection": 300, "final_development_evaluation": 400}
    streams, all_seeds = [], []
    for root in range(int(cfg["roots"])):
        for ri, regime in enumerate(regimes):
            block = 2_130_000_001 + (root * len(regimes) + ri) * 1000
            for split, shots in sizes.items():
                start = block + offsets[split]
                count = math.ceil(shots / batch)
                seeds = list(range(start, start + count))
                if seeds[-1] >= block + 1000:
                    raise ValueError("Per-root/regime seed block overflow.")
                streams.append({"root": root, "regime": regime, "split": split,
                                "shots": shots, "batch_size": batch,
                                "seed_start": start, "seeds": seeds})
                all_seeds.extend(seeds)
    model_streams, model_i = [], 0
    for root in range(int(cfg["roots"])):
        for strategy in cfg["models"]["strategies"]:
            for size in sampling["train_budgets_per_regime_root"]:
                seed = 2_140_000_001 + 10 * model_i
                row = {"root": root, "strategy": strategy, "train_size_per_regime": int(size),
                       "torch_seed": seed, "sampling_seed": seed + 1, "shuffle_seed": seed + 2}
                model_streams.append(row)
                all_seeds.extend((seed, seed + 1, seed + 2))
                model_i += 1
    diagnostic = [2_145_000_001, 2_145_000_002, 2_145_000_003]
    preflight_model_seed = 2_145_000_010
    analysis = {"sign_flip_seed": int(cfg["analysis"]["sign_flip_seed"]),
                "bootstrap_seed": int(cfg["analysis"]["bootstrap_seed"])}
    all_seeds.extend(diagnostic + [preflight_model_seed, *analysis.values()])
    duplicates = sorted(x for x in set(all_seeds) if all_seeds.count(x) > 1)
    out_of_range = sorted(x for x in all_seeds if not 1 <= x <= MAX_STIM_SEED)
    historical, provenance = set(), []
    gaps = []
    for rel in HISTORICAL_DEV:
        path = REPO / rel
        if not path.is_file():
            gaps.append(f"Missing source: {rel}")
            continue
        parsed = json.loads(path.read_text(encoding="utf-8"))
        serialized = json.dumps(parsed).lower()
        if "no test" not in serialized and "test_stream" not in serialized and "test_samples_generated_or_accessed\": 0" not in serialized:
            raise RuntimeError(f"Cannot verify test-free scope for historical inventory: {rel}")
        values = extract_dev_seeds(parsed)
        historical |= values
        provenance.append({"path": rel, "sha256": sha(path), "development_seed_values_extracted": len(values),
                           "test_free_metadata_verified": True})
    collisions = sorted(set(all_seeds) & historical)
    return {"status": "prospective development-only seed inventory", "streams": streams,
            "model_streams": model_streams, "diagnostic_seeds": diagnostic,
            "preflight_model_seed": preflight_model_seed, "analysis_seeds": analysis,
            "derived_seed_count": len(all_seeds), "unique_derived_seed_count": len(set(all_seeds)),
            "all_derived_seed_count": len(all_seeds), "unique_seed_count": len(set(all_seeds)),
            "all_derived_seeds": all_seeds, "duplicate_derived_seeds": duplicates,
            "outside_stim_range": out_of_range, "historical_collisions": collisions,
            "historical_seed_collisions": collisions, "seed_collision_audit_passed": not collisions and not duplicates and not out_of_range,
            "passed": not collisions and not duplicates and not out_of_range,
            "historical_sources": provenance, "historical_values_checked": len(historical),
            "coverage_gaps": gaps + ["Independent-test seed records were not read or enumerated by design.",
                "Coverage is limited to the two listed, explicitly development-only inventories."],
            "unique_production_shots": sum(sizes.values()) * int(cfg["roots"]) * len(regimes),
            "diagnostic_shots": int(sampling["diagnostic_shots_per_regime"]) * len(regimes),
            "independent_test": "No test seed was read, allocated, generated, or accessed."}


def main() -> None:
    freeze_path = HERE / "FREEZE.json"
    if freeze_path.exists():
        raise SystemExit("FREEZE.json already exists; preserving it and refusing to replace a pre-sampling freeze.")
    cfg_path = HERE / "config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    inventory = make_inventory(cfg)
    if not inventory["passed"]:
        atomic_json(inventory, HERE / "SEED_INVENTORY.json")
        raise SystemExit("Seed collisions or unsupported Stim seed were found; no samples generated.")
    inv_path = HERE / "SEED_INVENTORY.json"
    atomic_json(inventory, inv_path)
    audit = {"status": "PASS" if inventory["passed"] else "FAIL",
             "sources_examined": inventory["historical_sources"],
             "historical_development_values_checked": inventory["historical_values_checked"],
             "new_seed_count": inventory["derived_seed_count"],
             "new_unique_seed_count": inventory["unique_derived_seed_count"],
             "internal_collisions": inventory["duplicate_derived_seeds"],
             "historical_collisions": inventory["historical_collisions"],
             "outside_stim_range": inventory["outside_stim_range"],
             "coverage_gaps": inventory["coverage_gaps"],
             "independent_test_access": 0}
    audit_path = HERE / "HISTORICAL_SEED_AUDIT.json"
    atomic_json(audit, audit_path)
    source_paths = [HERE / rel for rel in LOCAL_FILES]
    external = [REPO / rel for rel in EXTERNAL_FILES]
    missing = [str(p) for p in source_paths + external if not p.is_file()]
    if missing:
        raise FileNotFoundError("Cannot freeze missing source(s): " + ", ".join(missing))
    hashes = {str(p.relative_to(REPO)): sha(p) for p in source_paths + external}
    hashes["outputs/neural_decoder_diagnostic/hybrid_residual_sprint_v1/SEED_INVENTORY.json"] = sha(inv_path)
    hashes["outputs/neural_decoder_diagnostic/hybrid_residual_sprint_v1/HISTORICAL_SEED_AUDIT.json"] = sha(audit_path)
    import stim, pymatching, numpy, psutil
    packages = {name: importlib.metadata.version(name) for name in ("torch", "stim", "pymatching", "numpy", "psutil")}
    device = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available; no sampling will start.")
    freeze = {"status": "FROZEN BEFORE ALL NEW SAMPLING", "created_unix": time.time(),
        "config_sha256": sha(cfg_path), "protocol_sha256": sha(HERE / "EXPERIMENT_PROTOCOL.md"),
        "failure_analysis_sha256": sha(HERE / "FAILURE_ANALYSIS.md"),
        "seed_inventory_sha256": sha(inv_path), "historical_seed_audit_sha256": sha(audit_path),
        "source_sha256": hashes, "python_executable": sys.executable, "python_version": sys.version,
        "packages": packages, "cuda_available": True, "cuda_device": device,
        "cuda_total_memory_bytes": int(torch.cuda.get_device_properties(0).total_memory),
        "seed_coverage": inventory["coverage_gaps"], "independent_test_access": 0}
    atomic_json(freeze, freeze_path)
    print(json.dumps({"status": freeze["status"], "freeze": str(freeze_path),
        "seed_count": inventory["derived_seed_count"], "historical_values_checked": inventory["historical_values_checked"],
        "collisions": inventory["historical_collisions"], "cuda_device": device}, indent=2))


if __name__ == "__main__":
    main()
