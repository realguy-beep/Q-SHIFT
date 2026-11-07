"""Independent read-only audit of Stage 5 candidate plan, seeds, and provenance.

Reads only explicitly named protocol/config/seed metadata and the compact
Stage 4C development profile model. It never lists or opens a sealed-test path
or any Stage 5 sample archive; no Stage 5 runner exists.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT_JSON = HERE / "STAGE5_PRETEST_AUDIT.json"
OUTPUT_MD = HERE / "STAGE5_PRETEST_AUDIT.md"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def collect_json_seeds(value, in_seed_field=False):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            seed_key = "seed" in str(key).lower() or "rng" in str(key).lower()
            found.extend(collect_json_seeds(child, in_seed_field or seed_key))
    elif isinstance(value, list):
        for child in value:
            found.extend(collect_json_seeds(child, in_seed_field))
    elif in_seed_field and isinstance(value, (int, float)) and not isinstance(value, bool):
        integer = int(value)
        if integer == value and 0 <= integer < 2**32:
            found.append(integer)
    return found


def read_seed_metadata(path: Path):
    if path.suffix.lower() == ".csv":
        found = []
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            cols = [c for c in (reader.fieldnames or [])
                    if "seed" in c.lower() or "rng" in c.lower()]
            for row in reader:
                for col in cols:
                    try:
                        value = int(row[col])
                    except (TypeError, ValueError):
                        continue
                    if 0 <= value < 2**32:
                        found.append(value)
        return found
    return collect_json_seeds(json.loads(path.read_text(encoding="utf-8")))


def main():
    checks = []
    freeze = json.loads((HERE / "STAGE5_CANDIDATE_FREEZE.json").read_text(encoding="utf-8"))
    changed = []
    for rel, expected in freeze["files_sha256"].items():
        path = ROOT / rel
        if not path.is_file() or digest(path) != expected:
            changed.append(rel)
    checks.append({"check": "candidate_freeze_hashes", "status": "PASS" if not changed else "FAIL",
                   "file_count": len(freeze["files_sha256"]), "mismatches": changed})

    audit = json.loads((HERE / "seed_audit.json").read_text(encoding="utf-8"))
    historical = set()
    metadata_mismatches = []
    for record in audit["historical_files_examined"]:
        path = ROOT / record["path"]
        if not path.is_file() or digest(path) != record["sha256"]:
            metadata_mismatches.append(record["path"])
            continue
        extracted = sorted(set(read_seed_metadata(path)))
        if extracted != record["extracted_values"]:
            metadata_mismatches.append(record["path"] + " (seed extraction differs)")
        historical.update(extracted)
    expansion_mismatches = []
    for record in audit.get("derived_phase4a_phase4b_seed_expansions", []):
        path = ROOT / record["config_path"]
        if not path.is_file() or digest(path) != record["config_sha256"]:
            expansion_mismatches.append(record["config_path"] + " (config hash mismatch)")
            continue
        cfg = json.loads(path.read_text(encoding="utf-8"))
        root_cfg = cfg["seed_roots"]
        roots = [int(root_cfg["start"]) + i * int(root_cfg["step"])
                 for i in range(int(root_cfg["count"]))]
        offsets = [int(v) for v in cfg["seed_offsets"].values()]
        expanded = set(roots)
        expanded.update(root + offset + condition
                        for root in roots for offset in offsets for condition in range(3))
        expanded.update(int(cfg["template_seed_start"]) + i for i in range(9))
        expanded.update((int(cfg["noiseless_seed"]), int(cfg["bootstrap_seed"])))
        if sorted(expanded) != record["expanded_seed_values"] or len(expanded) != record["unique_count"]:
            expansion_mismatches.append(record["config_path"] + " (derived seed expansion differs)")
        historical.update(expanded)
    if len(audit.get("derived_phase4a_phase4b_seed_expansions", [])) != 2:
        expansion_mismatches.append("Phase 4A/4B seed expansion records missing")
    checks.append({"check": "historical_seed_metadata_reextraction", "status": "PASS" if not metadata_mismatches else "FAIL",
                   "files_examined": len(audit["historical_files_examined"]),
                   "distinct_values": len(historical), "mismatches": metadata_mismatches})
    checks.append({"check": "phase4a_phase4b_derived_seed_expansion", "status": "PASS" if not expansion_mismatches else "FAIL",
                   "configs_checked": len(audit.get("derived_phase4a_phase4b_seed_expansions", [])),
                   "mismatches": expansion_mismatches})

    inventory = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
    config = json.loads((HERE / "STAGE5_CONFIG.json").read_text(encoding="utf-8"))
    expected_p = [0.0, 0.004, 0.008, 0.012, 0.016]
    expected_streams = []
    next_seed = 4_240_000_001
    for kind, shots in (("calibration_detector_only", 2000),
                        ("paired_evaluation_detector_observable", 2500)):
        for p in expected_p:
            for root in range(100):
                expected_streams.append({"kind": kind, "probability": p,
                                         "root": root, "shots": shots, "seed": next_seed})
                next_seed += 1
    expected_rngs = {"bootstrap": next_seed, "primary_signflip": next_seed + 1}
    proposed = [r["seed"] for r in inventory["streams"]] + list(inventory["analysis_rngs"].values())
    allocation_ok = (inventory["streams"] == expected_streams and
                     inventory["analysis_rngs"] == expected_rngs and
                     len(proposed) == len(set(proposed)) == 1002 and
                     len(proposed) == len(set(proposed).union(historical)) - len(historical))
    config_ok = (config["evaluation"]["probabilities"] == expected_p and
                 config["evaluation"]["roots_per_condition"] == 100 and
                 config["evaluation"]["calibration_shots_per_root"] == 2000 and
                 config["evaluation"]["paired_evaluation_shots_per_root"] == 2500 and
                 config["evaluation"]["total_unique_shots"] == 2_250_000 and
                 config["success_gate"]["primary_delta_max"] == -0.0002 and
                 config["statistical_plan"]["bootstrap"]["resamples"] == 20_000 and
                 config["statistical_plan"]["bootstrap"]["seed"] == expected_rngs["bootstrap"] and
                 config["statistical_plan"]["primary_signflip"]["assignments"] == 100_000 and
                 config["statistical_plan"]["primary_signflip"]["seed"] == expected_rngs["primary_signflip"] and
                 config["success_gate"]["primary_ci_upper_max"] == 0.0 and
                 config["success_gate"]["primary_p_max"] == 0.05 and
                 config["resources"]["max_unique_shots"] >= inventory["shot_count"] and
                 inventory["shot_count"] == config["evaluation"]["total_unique_shots"])
    collision_list = sorted(set(proposed) & historical)
    checks.append({"check": "seed_allocation_and_collision_screen", "status": "PASS" if allocation_ok and config_ok and not collision_list else "FAIL",
                   "proposed_seed_count": len(proposed), "historical_distinct_seed_values": len(historical),
                   "collisions": collision_list, "allocation_matches_protocol": allocation_ok,
                   "config_matches_protocol": config_ok})

    provenance = json.loads((HERE / "PROFILE_PROVENANCE.json").read_text(encoding="utf-8"))
    source_path = ROOT / provenance["source_path"]
    copied_path = HERE / "FROZEN_PROFILE_ESTIMATOR.json"
    training_path = ROOT / "outputs/stage4c_cnn_noise_estimation_v1/run/training_batches.npz"
    provenance_ok = (source_path.is_file() and copied_path.is_file() and training_path.is_file() and
                     digest(source_path) == provenance["source_sha256"] == digest(copied_path) == provenance["copied_sha256"] and
                     digest(training_path) == provenance["stage4c_training_archive_sha256"] and
                     provenance["stage4c_independent_audit_status"] == "PASS")
    checks.append({"check": "selected_profile_provenance", "status": "PASS" if provenance_ok else "FAIL",
                   "stage4c_training_partition_hash_matches": provenance_ok,
                   "profile_model_copy_hash_matches": provenance_ok})

    no_run = not (HERE / "run").exists()
    checks.append({"check": "no_stage5_sampling", "status": "PASS" if no_run and freeze.get("sampling_started") is False else "FAIL",
                   "stage5_run_directory_exists": not no_run, "sampling_started_record": freeze.get("sampling_started")})
    overall = "PASS_CANDIDATE_READY_FOR_INDEPENDENT_REVIEW_NOT_SAMPLING" if all(c["status"] == "PASS" for c in checks) else "FAIL"
    result = {
        "status": overall,
        "independent_test_accessed": False,
        "stage5_samples_generated": False,
        "checks": checks,
        "limitations": [
            "Seed checks cover 3,811 distinct values in explicit, recoverable development metadata; undocumented historical RNG use cannot be ruled out.",
            "Stage 4B calibration detector arrays were not retained, so its original calibration fit cannot be reproduced; Stage 5 instead freezes the audited Stage 4C refitted profile and its Stage 4C training archive provenance.",
            "Planning power inputs are estimated from small development root samples and must be independently reviewed before any Stage 5 runner is frozen.",
            "No runner or complete executable independent-audit pipeline exists yet; this audit validates only the no-sampling candidate package.",
            "No sealed independent-test path or sample array was enumerated or opened."
        ]
    }
    OUTPUT_JSON.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = ["# Stage 5 Candidate Pre-test Audit", "", f"**Status: {overall}.** No Stage 5 samples generated; current sealed independent test untouched.", "",
             "| Check | Status | Evidence |", "|---|---|---|"]
    for c in checks:
        detail = json.dumps({k: v for k, v in c.items() if k not in ("check", "status")}, sort_keys=True)
        lines.append(f"| {c['check']} | {c['status']} | `{detail}` |")
    lines.extend(["", "## Review boundary", "",
                  "This is an independently implemented read-only cross-check of the candidate freeze, seed streams, historical metadata extraction, configuration, and frozen profile provenance. It does not independently validate performance, a Stage 5 runner, or the power assumptions. The candidate is ready for a separate protocol review, not for sampling.", "",
                  "## Limitations", ""])
    lines.extend(f"- {x}" for x in result["limitations"])
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": overall, "checks": [{"check": c["check"], "status": c["status"]} for c in checks],
                      "historical_seeds": len(historical), "proposed_seeds": len(proposed),
                      "stage5_shots_generated": 0}, indent=2))
    if overall == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
