"""Build and verify Stage 3's prospective seed inventory and source freeze."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE_SEED = 3_100_000_001
STAGE2 = ROOT / "outputs/cnn_architecture_stage2_v1"
FREEZE_PATH = HERE / "FREEZE.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def collect_seed_values(value: Any, key_path: str = "") -> set[int]:
    found: set[int] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            new_key = f"{key_path}.{key}" if key_path else str(key)
            if "seed" in str(key).lower():
                found |= collect_numbers(child)
            else:
                found |= collect_seed_values(child, new_key)
    elif isinstance(value, list):
        for child in value:
            found |= collect_seed_values(child, key_path)
    return found


def collect_numbers(value: Any) -> set[int]:
    if isinstance(value, bool):
        return set()
    if isinstance(value, int):
        return {value}
    if isinstance(value, str) and value.isdecimal():
        return {int(value)}
    if isinstance(value, list):
        return set().union(*(collect_numbers(x) for x in value)) if value else set()
    if isinstance(value, dict):
        return set().union(*(collect_numbers(x) for x in value.values())) if value else set()
    return set()


def historical_sources() -> list[Path]:
    # The existing broad scan covers earlier phases; these explicit later
    # inventories/results extend it. No independent-test directories or files
    # are enumerated, opened, or searched.
    return [
        ROOT / "outputs/headroom_feasibility/HISTORICAL_SEED_SCAN.json",
        ROOT / "outputs/cnn_architecture_stage1_v1/seed_inventory.json",
        ROOT / "outputs/cnn_architecture_stage1_v1/PREFLIGHT_RESULTS.json",
        ROOT / "outputs/cnn_architecture_stage2_v1/seed_inventory.json",
        ROOT / "outputs/cnn_architecture_stage2_v1/seed_audit.json",
        ROOT / "outputs/phase3a_correlated_noise_preflight/PREFLIGHT_RESULTS.json",
        ROOT / "outputs/phase3a_correlated_noise_preflight/config.json",
        ROOT / "outputs/phase3a_correlated_noise_preflight/test_correlated_noise.py",
    ]


def build_inventory() -> tuple[dict, dict]:
    cfg = json.loads((HERE / "stage3_config.json").read_text(encoding="utf-8"))
    rows: list[dict] = []
    next_seed = BASE_SEED
    for root_i, root_id in enumerate(cfg["roots"]["ids"]):
        for split, condition in (
            ("training", "synthetic_spatial_burst"),
            ("monitor", "synthetic_spatial_burst"),
            ("probability_calibration", "synthetic_spatial_burst"),
            ("threshold_selection", "synthetic_spatial_burst"),
            ("final_development_evaluation", "synthetic_spatial_burst"),
            ("final_development_evaluation", "nominal"),
        ):
            rows.append({"root_id": root_id, "kind": "stim_sample_stream",
                         "split": split, "condition": condition, "seed": next_seed})
            next_seed += 1
        for purpose in ("torch_initialization", "balanced_sampling", "batch_order"):
            rows.append({"root_id": root_id, "kind": "training_rng", "purpose": purpose,
                         "seed": next_seed})
            next_seed += 1
    rows.append({"root_id": "all", "kind": "analysis_rng", "purpose": "root_bootstrap",
                 "seed": next_seed})
    proposed = [int(row["seed"]) for row in rows]
    if len(proposed) != 46 or len(set(proposed)) != len(proposed):
        raise RuntimeError(f"Unexpected proposed seed inventory: {len(proposed)} rows")

    sources = historical_sources()
    missing = [str(p.relative_to(ROOT)) for p in sources if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"Historical seed sources missing: {missing}")
    historic_values: set[int] = set()
    source_records = []
    for path in sources:
        raw = path.read_bytes()
        rec = {"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(raw).hexdigest(),
               "bytes": len(raw)}
        if path.suffix.lower() == ".json":
            historic_values |= collect_seed_values(json.loads(raw.decode("utf-8")))
        else:
            text = raw.decode("utf-8", errors="replace")
            historic_values |= {int(x) for x in re.findall(r"\bseed\s*=\s*(\d+)\b", text)}
        source_records.append(rec)
    scan = json.loads((sources[0]).read_text(encoding="utf-8"))
    # Stage 2 inventories list every reserved split and model RNG stream; the
    # historical scan includes every value in its recoverable-value array.
    collisions = sorted(set(proposed) & historic_values)
    stim_max = max(int(x) for x in proposed if any(r.get("kind") == "stim_sample_stream" and r["seed"] == x for r in rows))
    if collisions:
        raise RuntimeError(f"Historical seed collisions: {collisions}")

    inventory = {
        "protocol_version": cfg["protocol_version"],
        "status": "reserved_for_stage3",
        "allocation_rule": f"Sequential unique streams starting at {BASE_SEED}; fixed row order in this file; no modulo or random-derived offsets.",
        "root_ids": cfg["roots"]["ids"],
        "stream_count": len(rows), "unique_seed_count": len(set(proposed)),
        "maximum_stim_seed": stim_max,
        "independent_test_seed_allocated": False,
        "streams": rows,
    }
    audit = {
        "status": "PASS",
        "candidate_seed_count": len(proposed),
        "candidate_seeds_unique": len(set(proposed)) == len(proposed),
        "candidate_stim_seed_max": stim_max,
        "candidate_stim_seeds_within_uint32": stim_max < 2**32,
        "within_allocation_collisions": [],
        "historical_collisions": collisions,
        "historical_seed_values": sorted(historic_values),
        "historical_unique_values_extracted_from_sources": len(historic_values),
        "historical_scan_recorded_file_count": scan.get("files_scanned"),
        "historical_scan_recorded_seed_count": len(scan.get("recoverable_unique_seed_values", [])),
        "historical_source_files_examined": source_records,
        "coverage_limit": "The saved broad historical scan plus the explicitly listed Stage 1, Stage 2, and Phase 3A seed records were checked. Unrecorded RNG uses cannot be ruled out. No independent-test path or artifact was inspected.",
    }
    return inventory, audit


def frozen_inputs() -> list[Path]:
    paths = [
        HERE / name for name in (
            "CNN_STAGE3_PROTOCOL.md", "CNN_STAGE3_DIAGNOSTIC_REVIEW.md", "CNN_STAGE3_REPRODUCE.md",
            "CNN_STAGE3_PROTOCOL_AMENDMENT_PRE_SAMPLING.md",
            "stage3_config.json", "seed_inventory.json", "seed_audit.json",
            "diagnose_stage2.py", "STAGE2_RETROSPECTIVE_DIAGNOSTICS.json",
            "run_stage3.py", "audit_stage3.py", "tests/test_stage3.py",
            "freeze_stage3.py",
        )
    ]
    paths += [ROOT / p for p in (
        "AGENTS.md", "RESEARCH_STATUS.md",
        "dashboard/structured_decoder.py",
        "outputs/cnn_architecture_stage1_v1/cnn_architectures.py",
        "outputs/neural_decoder_diagnostic/autonomous_development/experiment.py",
        "outputs/phase2b_pauli_bias/noise_model.py",
        "outputs/phase3a_correlated_noise_preflight/simulator.py",
        "outputs/phase3a_correlated_noise_preflight/test_correlated_noise.py",
        "outputs/cnn_architecture_stage2_v1/CNN_STAGE2_FROZEN_PROTOCOL.md",
        "outputs/cnn_architecture_stage2_v1/CNN_STAGE2_RESULTS.md",
        "outputs/cnn_architecture_stage2_v1/CNN_STAGE2_EXECUTION_REPORT.md",
        "outputs/cnn_architecture_stage2_v1/CNN_STAGE2_INDEPENDENT_AUDIT.md",
        "outputs/cnn_architecture_stage2_v1/CNN_STAGE2_PER_ROOT.csv",
        "outputs/cnn_architecture_stage2_v1/CNN_STAGE2_TRAINING_DIAGNOSTICS.csv",
        "outputs/cnn_architecture_stage2_v1/stage2_config.json",
        "outputs/cnn_architecture_stage2_v1/seed_inventory.json",
        "outputs/cnn_architecture_stage2_v1/FREEZE.json",
        "outputs/cnn_architecture_stage2_v1/FREEZE_IMPLEMENTATION_V4.json",
        "outputs/cnn_architecture_stage2_v1/run_stage2.py",
        "outputs/cnn_architecture_stage2_v1/audit_stage2_recovery.py",
    )]
    for root_id in (f"dev-root-{i:02d}" for i in range(5)):
        paths.append(STAGE2 / "run_v1/checkpoints" / root_id / "historical_residual_position_cnn_selected.pt")
        paths.append(STAGE2 / "run_v1/raw" / root_id / "selections/historical_residual_position_cnn.json")
    return paths


def freeze(*, supersede: bool = False) -> None:
    supersedes_record = None
    if FREEZE_PATH.exists():
        if not supersede:
            raise FileExistsError("FREEZE.json already exists; use --supersede-freeze only before sampling and after recording an amendment")
        raw_old = FREEZE_PATH.read_bytes()
        backup = HERE / "FREEZE_SUPERSEDED_001.json"
        if backup.exists():
            raise FileExistsError(f"Superseded freeze backup already exists: {backup}")
        with backup.open("xb") as stream:
            stream.write(raw_old)
            stream.flush()
        supersedes_record = {"path": backup.name, "sha256": hashlib.sha256(raw_old).hexdigest(),
                             "sampled_shots_at_supersession": 0,
                             "reason": "Implementation and resume/resource guard fixes were made before any Stage 3 sample generation."}
    inputs = frozen_inputs()
    missing = [str(p.relative_to(ROOT)) for p in inputs if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"Freeze inputs missing: {missing}")
    records = []
    for path in inputs:
        records.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size,
                        "sha256": sha256(path)})
    inventory = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
    audit = json.loads((HERE / "seed_audit.json").read_text(encoding="utf-8"))
    if audit.get("status") != "PASS" or inventory.get("unique_seed_count") != 46:
        raise RuntimeError("Seed preflight is not PASS or inventory is incomplete")
    payload = {
        "status": "FROZEN_BEFORE_SAMPLING",
        "protocol_version": "qshift-stage3-correlated-specialist-v1",
        "frozen_utc": "2026-11-07T00:00:00Z",
        "frozen_timestamp_note": "Prospective freeze file generated at execution; timestamp is recorded by the builder at run time.",
        "planned_unique_shots": 200000,
        "seed_count": inventory["unique_seed_count"],
        "seed_audit_status": audit["status"],
        "independent_test_accessed": False,
        "inputs": records,
    }
    if supersedes_record is not None:
        payload["supersedes_freeze"] = supersedes_record
    import time
    payload["frozen_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["protocol_id_sha256"] = hashlib.sha256(canonical).hexdigest()
    atomic_json(FREEZE_PATH, payload)
    print(json.dumps({"status": payload["status"], "protocol_id_sha256": payload["protocol_id_sha256"],
                      "hash_inputs": len(records), "unique_seeds": inventory["unique_seed_count"],
                      "planned_shots": payload["planned_unique_shots"]}, indent=2))


def verify() -> None:
    freeze_path = FREEZE_PATH
    if not freeze_path.is_file():
        raise FileNotFoundError(freeze_path)
    payload = json.loads(freeze_path.read_text(encoding="utf-8"))
    bad = []
    for row in payload["inputs"]:
        path = ROOT / row["path"]
        if not path.is_file() or path.stat().st_size != row["bytes"] or sha256(path) != row["sha256"]:
            bad.append(row["path"])
    inv = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
    audit = json.loads((HERE / "seed_audit.json").read_text(encoding="utf-8"))
    expected_inventory, expected_audit = build_inventory()
    canonical = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"))
    if canonical(inv) != canonical(expected_inventory) or canonical(audit) != canonical(expected_audit):
        bad.append("seed_inventory.json or seed_audit.json does not reproduce from frozen allocation and recorded historical sources")
    id_payload = {k: v for k, v in payload.items() if k != "protocol_id_sha256"}
    expected_id = hashlib.sha256(json.dumps(id_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if payload.get("protocol_id_sha256") != expected_id:
        bad.append("FREEZE.json protocol identifier hash")
    supersedes = payload.get("supersedes_freeze")
    if supersedes is not None:
        old_path = HERE / supersedes.get("path", "")
        if (not old_path.is_file() or sha256(old_path) != supersedes.get("sha256") or
                supersedes.get("sampled_shots_at_supersession") != 0):
            bad.append("superseded pre-sampling freeze record")
    if bad or payload.get("status") != "FROZEN_BEFORE_SAMPLING" or audit.get("status") != "PASS":
        raise RuntimeError(f"Stage 3 freeze verification failed; changed inputs={bad}")
    if inv.get("unique_seed_count") != payload.get("seed_count") or inv.get("independent_test_seed_allocated") is not False:
        raise RuntimeError("Seed inventory/freeze mismatch")
    print(json.dumps({"status": "PASS", "protocol_id_sha256": payload["protocol_id_sha256"],
                      "verified_inputs": len(payload["inputs"]), "unique_seeds": inv["unique_seed_count"],
                      "shots": payload["planned_unique_shots"]}))


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare-seeds", action="store_true")
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--supersede-freeze", action="store_true")
    group.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.prepare_seeds:
        if FREEZE_PATH.exists():
            raise FileExistsError("FREEZE.json already exists; refusing to alter the frozen seed inventory")
        inventory, audit = build_inventory()
        atomic_json(HERE / "seed_inventory.json", inventory)
        atomic_json(HERE / "seed_audit.json", audit)
        print(json.dumps({"status": audit["status"], "streams": inventory["stream_count"],
                          "historical_values": audit["historical_unique_values_extracted_from_sources"],
                          "collisions": audit["historical_collisions"]}))
    elif args.freeze:
        freeze()
    elif args.supersede_freeze:
        if not (HERE / "CNN_STAGE3_PROTOCOL_AMENDMENT_PRE_SAMPLING.md").is_file():
            raise FileNotFoundError("A pre-sampling amendment is required before superseding FREEZE.json")
        if any((HERE / "run_v1").rglob("*.npz")):
            raise RuntimeError("Cannot supersede the freeze after Stage 3 samples have been generated")
        freeze(supersede=True)
    else:
        verify()


if __name__ == "__main__":
    main()
