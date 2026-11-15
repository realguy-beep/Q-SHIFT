"""Prepare prospective V2 streams and screen only recorded seed metadata.

This tool does not sample. It verifies the exact historical-source allowlist in
the preserved Stage 5 metadata inventory, then screens those metadata and
tracked seed inventories/manifests against the proposed V2 seed stream.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONFIG_PATH = HERE / "experiment_config_v2.json"
HISTORICAL_INVENTORY = ROOT / "outputs/stage5_secondary_inference_repair_v1/STAGE5_SAMPLE_SEED_INVENTORY.json"
OUT = HERE / "seed_inventory_v2_r2.json"
MIN_METADATA_INTEGER = 1_000_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def collect_large_ints(value: Any, target: set[int]) -> None:
    """Conservatively collect large numeric tokens from allowlisted metadata."""
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, int):
        if value >= MIN_METADATA_INTEGER:
            target.add(value)
    elif isinstance(value, str) and value.isdecimal() and len(value) >= 7:
        integer = int(value)
        if integer >= MIN_METADATA_INTEGER:
            target.add(integer)
    elif isinstance(value, dict):
        for key, item in value.items():
            collect_large_ints(key, target)
            collect_large_ints(item, target)
    elif isinstance(value, (list, tuple)):
        for item in value:
            collect_large_ints(item, target)


def parse_metadata(path: Path, target: set[int]) -> None:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            for row in csv.reader(stream):
                for cell in row:
                    collect_large_ints(cell.strip(), target)
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    collect_large_ints(payload, target)


def tracked_seed_metadata() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "outputs"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    )
    selected = []
    for raw in result.stdout.splitlines():
        path = Path(raw)
        if path.suffix.lower() not in {".json", ".csv"}:
            continue
        name = path.name.lower()
        if "seed" not in name:
            continue
        normalized = raw.replace("\\", "/")
        if normalized.startswith("outputs/strong_fixed_baselines_v2/seed_inventory_v2"):
            continue
        selected.append(raw.replace("\\", "/"))
    return sorted(set(selected))


def allocate(cfg: dict) -> list[dict]:
    p_values = [float(p) for p in cfg["circuit"]["probabilities"]]
    streams: list[dict] = []
    seed = int(cfg["seeds"]["namespace_start"])

    def add(role: str, split: str, *, probability=None, root=None, stream=None,
            shots=None, included=True) -> None:
        nonlocal seed
        streams.append({
            "role": role, "split": split, "probability": probability,
            "root": root, "stream": stream, "shots": shots,
            "included_in_allocation": included, "seed": seed,
        })
        seed += 1

    for p in cfg["decoders"]["profile_template_probabilities"]:
        add("profile_template", "templates", probability=float(p), stream="detector_only",
            shots=int(cfg["partitions"]["template_shots_per_probability"]))
    for split, roots_key in (("selection", "selection_roots_per_condition"),
                             ("validation", "validation_roots_per_condition")):
        for p in p_values:
            for root in range(int(cfg["partitions"][roots_key])):
                add("calibration", split, probability=p, root=root, stream="detector_only",
                    shots=int(cfg["decoders"]["calibration_shots_per_root"]))
                add("scoring", split, probability=p, root=root, stream="detector_observable",
                    shots=int(cfg["decoders"]["evaluation_shots_per_root"]))
    for p in p_values:
        for root in range(int(cfg["partitions"]["evaluation_roots_per_condition"])):
            add("calibration", "heldout_development", probability=p, root=root,
                stream="detector_only", shots=int(cfg["decoders"]["calibration_shots_per_root"]))
            add("evaluation", "heldout_development", probability=p, root=root,
                stream="detector_observable", shots=int(cfg["decoders"]["evaluation_shots_per_root"]))
    add("bootstrap_validation", "validation_analysis", stream="pcg64", included=False)
    add("bootstrap_results", "heldout_development_analysis", stream="pcg64", included=False)
    for p in cfg["decoders"]["profile_template_probabilities"]:
        add("benchmark_template", "benchmark_only", probability=float(p), stream="detector_only",
            shots=int(cfg["resources"]["benchmark_template_shots"]), included=False)
    add("benchmark_calibration", "benchmark_only", probability=float(cfg["resources"]["benchmark_probability"]),
        stream="detector_only", shots=int(cfg["resources"]["benchmark_calibration_shots"]), included=False)
    add("benchmark_evaluation", "benchmark_only", probability=float(cfg["resources"]["benchmark_probability"]),
        stream="detector_observable", shots=int(cfg["resources"]["benchmark_evaluation_shots"]), included=False)
    return streams


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--historical-root", type=Path, default=ROOT,
        help="checkout containing exact bytes listed in the historical metadata allowlist",
    )
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()

    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if cfg.get("execution", {}).get("sampling_authorized") is not False:
        raise RuntimeError("inventory preparation requires sampling_authorized=false")
    if not HISTORICAL_INVENTORY.is_file():
        raise FileNotFoundError("preserved Stage 5 seed metadata inventory is missing")
    historical_doc = json.loads(HISTORICAL_INVENTORY.read_text(encoding="utf-8"))
    allowlist = historical_doc.get("historical_sources_checked")
    if not isinstance(allowlist, list) or not allowlist:
        raise RuntimeError("historical seed metadata allowlist is absent")

    historical_values: set[int] = set()
    source_records: dict[str, dict[str, Any]] = {}
    allowlisted_paths: set[str] = set()
    for entry in allowlist:
        relative = str(entry["path"]).replace("\\", "/")
        source = args.historical_root / Path(relative)
        if not source.is_file():
            raise FileNotFoundError(f"allowlisted metadata missing: {relative}")
        observed_hash = sha256(source)
        if observed_hash != entry.get("sha256"):
            raise RuntimeError(f"historical metadata hash mismatch: {relative}")
        before = len(historical_values)
        parse_metadata(source, historical_values)
        source_records[relative] = {
            "sha256": observed_hash,
            "origin": "exact prior-audit allowlist; metadata only",
            "new_large_integer_tokens": len(historical_values) - before,
        }
        allowlisted_paths.add(relative)

    # Include every tracked, named seed inventory/manifest available in this
    # research clone, including records created after the Stage 5 allowlist.
    for relative in tracked_seed_metadata():
        if relative in allowlisted_paths:
            continue
        source = ROOT / Path(relative)
        before = len(historical_values)
        parse_metadata(source, historical_values)
        source_records[relative] = {
            "sha256": sha256(source),
            "origin": "tracked seed inventory/manifest in current research branch",
            "new_large_integer_tokens": len(historical_values) - before,
        }

    streams = allocate(cfg)
    seeds = [int(row["seed"]) for row in streams]
    collisions = sorted(set(seeds) & historical_values)
    if len(seeds) != len(set(seeds)):
        raise RuntimeError("proposed V2 stream seeds are not unique")
    if collisions:
        raise RuntimeError(f"proposed V2 seed namespace collides with historical metadata: {collisions[:10]}")

    planned = sum(int(row["shots"]) for row in streams if row["included_in_allocation"])
    expected = int(cfg["allocation"]["unique_shots"])
    if planned != expected:
        raise RuntimeError(f"shot allocation mismatch: inventory={planned}, config={expected}")
    if any(row["seed"] < 1_000_000 for row in streams):
        raise RuntimeError("candidate RNG seed is unexpectedly small")

    record = {
        "schema_version": 2,
        "study": cfg["study"],
        "configuration_path": str(CONFIG_PATH.relative_to(ROOT)).replace("\\", "/"),
        "configuration_sha256": sha256(CONFIG_PATH),
        "candidate_seed_generation": "sequential integers starting at config.seeds.namespace_start in canonical allocation order",
        "sampling_performed": False,
        "sealed_test_access": False,
        "historical_coverage_complete": False,
        "allowlisted_metadata_sources_verified": True,
        "allowlisted_metadata_sources_verified": True,
        "historical_coverage_status": "all_recoverable_allowlisted_and_tracked_seed_metadata_screened",
        "coverage_limitation": "Undocumented or unrecorded historical RNG use cannot be ruled out.",
        "historical_metadata_only": True,
        "historical_inventory_source": {
            "path": str(HISTORICAL_INVENTORY.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256(HISTORICAL_INVENTORY),
            "stage5_evaluation_shots_recorded_by_source_inventory_at_creation": historical_doc.get("stage5_evaluation_shots_generated"),
            "sealed_test_access_recorded_by_source_inventory_at_creation": historical_doc.get("sealed_historical_test_accessed"),
            "historical_sources_checked_count": len(allowlist),
        },
        "historical_sources_checked": source_records,
        "historical_large_integer_tokens_screened": len(historical_values),
        "candidate_seed_namespace_start": int(cfg["seeds"]["namespace_start"]),
        "candidate_seed_namespace_end": max(seeds),
        "candidate_stream_count": len(streams),
        "stream_count_including_analysis_rng": len(streams),
        "sampling_stream_count": sum(row["role"] in {"profile_template", "calibration", "scoring", "evaluation"} for row in streams),
        "analysis_stream_count": sum(row["stream"] == "pcg64" for row in streams),
        "benchmark_stream_count": sum(str(row["role"]).startswith("benchmark_") for row in streams),
        "candidate_unique_seed_count": len(set(seeds)),
        "candidate_internal_collisions": [],
        "historical_collisions": [],
        "collisions": [],
        "expected_unique_shots": expected,
        "streams": streams,
    }
    payload = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if args.output.exists():
        if args.output.read_text(encoding="utf-8") != payload:
            raise FileExistsError("candidate inventory already exists and differs; preserve it and use a new versioned path")
    else:
        args.output.write_text(payload, encoding="utf-8")
    print(json.dumps({
        "status": "INVENTORY_PREPARED_NO_SAMPLING",
        "allowlisted_historical_sources_verified": len(allowlist),
        "tracked_seed_metadata_sources_added": len(source_records) - len(allowlist),
        "large_integer_tokens_screened": len(historical_values),
        "candidate_streams": len(streams),
        "candidate_unique_seeds": len(set(seeds)),
        "historical_collisions": 0,
        "internal_collisions": 0,
        "unique_shot_allocation": planned,
        "inventory_sha256": sha256(args.output),
        "historical_coverage_complete": False,
    }, indent=2))


if __name__ == "__main__":
    main()
