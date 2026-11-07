"""Create the no-overwrite pre-test seed inventory and SHA-256 freeze."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def create_seed_inventory() -> dict:
    cfg = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    preflight = json.loads((HERE / "SMOKE_PREFLIGHT.json").read_text(encoding="utf-8"))
    audit = preflight["seed_audit"]
    if (preflight["status"] != "PASS" or not preflight["seed_collision_free"] or
            audit["candidate_seed_collisions"] or audit["read_errors"]):
        raise RuntimeError("Cannot freeze a failed seed/circuit preflight")
    seeds = cfg["seed_allocation"]
    roots = []
    for si, label in enumerate(cfg["stratum_order"]):
        for ri in range(cfg["roots_per_stratum"]):
            roots.append({"stratum_index": si, "stratum": label, "root_index": ri,
                          "seed": int(seeds["root_seed_base"] + 100 * si + ri)})
    auxiliary = {k: int(seeds[k]) for k in ("diagnostic", "bootstrap_rng", "primary_signflip_rng")}
    all_values = [x["seed"] for x in roots] + list(auxiliary.values())
    if len(roots) != 72 or len(all_values) != 75 or len(set(all_values)) != 75:
        raise RuntimeError("Root/auxiliary seed allocation is not 72+3 unique values")
    inventory = {
        "status": "VERIFIED_PROSPECTIVE_ALLOCATION",
        "seed_formula": seeds["root_formula"],
        "root_seeds": roots,
        "auxiliary_seeds": auxiliary,
        "counts": {"roots": len(roots), "all_derived_seeds": len(all_values),
                   "all_unique": True, "internal_collisions": []},
        "historical_scan": {
            "collision_free_over_recoverable_records": True,
            "candidate_collisions": audit["candidate_seed_collisions"],
            "read_errors": audit["read_errors"],
            "text_file_count": audit["text_file_count"],
            "text_files_examined": audit["text_files_examined"],
            "npz_file_count": audit["npz_file_count"],
            "npz_files_examined": audit["npz_files_examined"],
            "coverage_limit": audit["coverage_limit"],
        },
        "rejected_prior_candidates": [
            {"namespace": "93000000-series", "reason": "collision with prior Phase 5 adaptive-development block seeds", "audit": "SEED_COLLISION_PRECHECK.json"},
            {"namespace": "97000000-series", "reason": "collision with Phase 4C headroom template seeds", "audit": "SEED_COLLISION_970_AUDIT.json"},
            {"literal_review": "100000000 in a prior assertion is a threshold, not a seed; accepted diagnostic uses 100000999", "audit": "SEED_TEXT_MATCH_REVIEW.json"}
        ],
        "candidate_values_screened": all_values,
        "seed_screen_code_sha256": sha256(HERE / "preflight_correlation_pilot.py")
    }
    inventory_path = HERE / "SEED_INVENTORY.json"
    if inventory_path.exists():
        current = json.loads(inventory_path.read_text(encoding="utf-8"))
        if current != inventory:
            raise RuntimeError("SEED_INVENTORY.json exists with different contents; refusing to overwrite")
    else:
        write_json(inventory_path, inventory)
    return inventory


def create_freeze() -> dict:
    freeze_path = HERE / "PRETEST_FREEZE.json"
    if freeze_path.exists():
        raise RuntimeError("PRETEST_FREEZE.json already exists; refusing to overwrite")
    cfg = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    preflight = json.loads((HERE / "SMOKE_PREFLIGHT.json").read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or preflight["planned_total_shots"] != 720000:
        raise RuntimeError("Preflight not passing or wrong frozen sample size")
    if cfg["primary_comparison"]["minimum_practical_improvement_absolute_ler"] != 0.0002:
        raise RuntimeError("The frozen practical margin is not exactly 0.0002")
    if list((HERE / "checkpoints").glob("*.npz")) if (HERE / "checkpoints").exists() else []:
        raise RuntimeError("Checkpoint evidence exists before the pre-test freeze")

    own_files = [
        "outputs/research_direction_selection/PILOT_PROTOCOL.md",
        "outputs/correlation_pilot/PILOT_EXECUTION_PROTOCOL.md",
        "outputs/correlation_pilot/config.json",
        "outputs/correlation_pilot/SEED_INVENTORY.json",
        "outputs/correlation_pilot/SMOKE_PREFLIGHT.json",
        "outputs/correlation_pilot/SMOKE_TEST.json",
        "outputs/correlation_pilot/STATISTICAL_SELF_CHECK.json",
        "outputs/correlation_pilot/preflight_correlation_pilot.py",
        "outputs/correlation_pilot/run_correlation_pilot.py",
        "outputs/correlation_pilot/analyze_correlation_pilot.py",
        "outputs/correlation_pilot/freeze_pilot.py",
        "outputs/correlation_pilot/smoke_test_correlation_pilot.py",
        "outputs/correlation_pilot/REPRODUCE.md",
        "outputs/correlation_pilot/SEED_COLLISION_PRECHECK.json",
        "outputs/correlation_pilot/SEED_COLLISION_970_AUDIT.json",
        "outputs/correlation_pilot/SEED_TEXT_MATCH_REVIEW.json",
    ]
    p2b = [
        "outputs/phase2b_pauli_bias/noise_model.py",
        "outputs/phase2b_pauli_bias/decoder_bank.py",
        "outputs/phase2b_pauli_bias/PHASE2B_PROTOCOL.md",
        "outputs/phase2b_pauli_bias/NOISE_MODEL_SPECIFICATION.md",
        "outputs/phase2b_pauli_bias/CALIBRATION_SELECTION.json",
        "outputs/phase2b_pauli_bias/DECODER_BANK_AUDIT.json",
        "outputs/phase2b_pauli_bias/config.json",
    ]
    for basis in ("x", "z"):
        for regime in ("x_biased", "balanced", "z_biased"):
            p2b.append(f"outputs/phase2b_pauli_bias/dems/circuit_{basis}_{regime}.stim")
            p2b.append(f"outputs/phase2b_pauli_bias/dems/dem_{basis}_{regime}.dem")
    files = {}
    missing = []
    for rel in own_files + p2b:
        path = ROOT / Path(rel)
        if not path.is_file():
            missing.append(rel)
        else:
            files[rel] = sha256(path)
    if missing:
        raise RuntimeError(f"Freeze inputs missing: {missing}")

    decisions = {
        "full_sampling_preceded_by_freeze": True,
        "status": "development_feasibility_only",
        "strata": cfg["stratum_order"],
        "roots_per_stratum": cfg["roots_per_stratum"],
        "shots_per_root": cfg["shots_per_root"],
        "total_paired_shots": 720000,
        "arm_order": cfg["decoder_arms"],
        "pooled_fixed_model_index_by_basis": cfg["pooled_fixed_model_index_by_basis"],
        "DEM_conversion": cfg["dem_conversion"],
        "primary_comparison": cfg["primary_comparison"],
        "primary_statistics": cfg["statistics"],
        "seed_allocation": cfg["seed_allocation"],
        "primary_margin_absolute_ler": 0.0002,
        "secondary_family": cfg["statistics"]["secondary_family"],
        "test_label_handling": "Observable labels are generated and stored with each test detector bundle and are used only for post-decode scoring. No labels select or tune decoders. The pooled fixed index comes from Phase 2B calibration-only selection. The regime-informed index uses generating regime only as a labeled diagnostic comparator.",
        "preflight_runtime_estimate_seconds_with_2x_margin": preflight["estimated_total_compute_seconds_with_2x_margin"],
        "preflight_storage_estimate_bytes_with_50pct_margin": preflight["estimated_full_evidence_bytes_with_50pct_margin"],
        "preflight_free_storage_bytes": preflight["disk_free_bytes"],
        "no_full_pilot_samples_exist_at_freeze": True,
    }
    freeze = {
        "status": "FROZEN_BEFORE_FULL_SAMPLING",
        "freeze_created_utc": datetime.now(timezone.utc).isoformat(),
        "freeze_protocol": "PILOT_EXECUTION_PROTOCOL.md",
        "protocol_decisions": decisions,
        "sha256": files,
        "sha256_file_count": len(files),
        "historical_namespace_collisions_rejected": ["93000000-series", "97000000-series"],
    }
    write_json(freeze_path, freeze)
    return freeze


if __name__ == "__main__":
    inventory = create_seed_inventory()
    freeze = create_freeze()
    print(json.dumps({"seed_inventory": inventory["counts"],
                      "freeze_status": freeze["status"],
                      "hash_count": freeze["sha256_file_count"],
                      "margin": freeze["protocol_decisions"]["primary_margin_absolute_ler"]}, indent=2))
