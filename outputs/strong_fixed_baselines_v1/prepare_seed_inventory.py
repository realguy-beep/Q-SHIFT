"""Create a collision-screened, new seed inventory without generating shots."""
from __future__ import annotations

import hashlib
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONFIG_PATH = HERE / "experiment_config.json"
HISTORICAL = ROOT / "outputs/stage5_secondary_inference_repair_v1/STAGE5_SAMPLE_SEED_INVENTORY.json"
OUT = HERE / "seed_inventory.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def collect_large_ints(value, out: set[int]) -> None:
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, int):
        if value >= 1_000_000:
            out.add(value)
    elif isinstance(value, str) and value.isdecimal():
        if len(value) >= 7:
            n = int(value)
            if n >= 1_000_000:
                out.add(n)
    elif isinstance(value, dict):
        for k, v in value.items():
            collect_large_ints(k, out)
            collect_large_ints(v, out)
    elif isinstance(value, (tuple, list)):
        for item in value:
            collect_large_ints(item, out)


def allocate() -> list[dict]:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    p_values = [float(p) for p in cfg["circuit"]["probabilities"]]
    out: list[dict] = []

    def add(role: str, split: str, *, probability=None, root=None, stream=None,
            shots=None, included_in_allocation=True) -> None:
        out.append({
            "role": role,
            "split": split,
            "probability": probability,
            "root": root,
            "stream": stream,
            "shots": shots,
            "included_in_allocation": included_in_allocation,
            "seed": int(cfg["seeds"]["namespace_start"]) + len(out),
        })

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
    add("bootstrap_validation", "validation_analysis", stream="pcg64", included_in_allocation=False)
    add("bootstrap_results", "heldout_development_analysis", stream="pcg64", included_in_allocation=False)
    for p in cfg["decoders"]["profile_template_probabilities"]:
        add("benchmark_template", "benchmark_only", probability=float(p), stream="detector_only",
            shots=int(cfg["resources"]["benchmark_template_shots"]), included_in_allocation=False)
    add("benchmark_calibration", "benchmark_only", probability=float(cfg["resources"]["benchmark_probability"]),
        stream="detector_only", shots=int(cfg["resources"]["benchmark_calibration_shots"]), included_in_allocation=False)
    add("benchmark_evaluation", "benchmark_only", probability=float(cfg["resources"]["benchmark_probability"]),
        stream="detector_observable", shots=int(cfg["resources"]["benchmark_evaluation_shots"]), included_in_allocation=False)
    for p in cfg["decoders"]["profile_template_probabilities"]:
        add("benchmark_v2_template", "benchmark_only_v2", probability=float(p), stream="detector_only",
            shots=int(cfg["resources"]["benchmark_template_shots"]), included_in_allocation=False)
    add("benchmark_v2_calibration", "benchmark_only_v2", probability=float(cfg["resources"]["benchmark_probability"]),
        stream="detector_only", shots=int(cfg["resources"]["benchmark_calibration_shots"]), included_in_allocation=False)
    add("benchmark_v2_evaluation", "benchmark_only_v2", probability=float(cfg["resources"]["benchmark_probability"]),
        stream="detector_observable", shots=int(cfg["resources"]["benchmark_evaluation_shots"]), included_in_allocation=False)
    for p in cfg["decoders"]["profile_template_probabilities"]:
        add("benchmark_v3_template", "benchmark_only_v3", probability=float(p), stream="detector_only",
            shots=int(cfg["resources"]["benchmark_template_shots"]), included_in_allocation=False)
    add("benchmark_v3_calibration", "benchmark_only_v3", probability=float(cfg["resources"]["benchmark_probability"]),
        stream="detector_only", shots=int(cfg["resources"]["benchmark_calibration_shots"]), included_in_allocation=False)
    add("benchmark_v3_evaluation", "benchmark_only_v3", probability=float(cfg["resources"]["benchmark_probability"]),
        stream="detector_observable", shots=int(cfg["resources"]["benchmark_evaluation_shots"]), included_in_allocation=False)
    for p in cfg["decoders"]["profile_template_probabilities"]:
        add("benchmark_v4_template", "benchmark_only_v4", probability=float(p), stream="detector_only",
            shots=int(cfg["resources"]["benchmark_template_shots"]), included_in_allocation=False)
    add("benchmark_v4_calibration", "benchmark_only_v4", probability=float(cfg["resources"]["benchmark_probability"]),
        stream="detector_only", shots=int(cfg["resources"]["benchmark_calibration_shots"]), included_in_allocation=False)
    add("benchmark_v4_evaluation", "benchmark_only_v4", probability=float(cfg["resources"]["benchmark_probability"]),
        stream="detector_observable", shots=int(cfg["resources"]["benchmark_evaluation_shots"]), included_in_allocation=False)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--historical-root",
        type=Path,
        default=ROOT,
        help="Checkout containing the exact bytes named by the prior historical seed audit",
    )
    args = parser.parse_args()
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    historical = json.loads(HISTORICAL.read_text(encoding="utf-8"))
    sources = historical.get("historical_sources_checked")
    if not isinstance(sources, list) or not sources:
        raise RuntimeError("Historical audited source allowlist is absent")

    historical_values: set[int] = set()
    verified_sources = []
    for entry in sources:
        path = args.historical_root / entry["path"]
        if not path.is_file():
            raise FileNotFoundError(f"Historical seed metadata missing: {entry['path']}")
        actual = sha256(path)
        if actual != entry["sha256"]:
            raise RuntimeError(f"Historical seed metadata hash mismatch: {entry['path']}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Allowlisted metadata is not readable JSON: {entry['path']}") from e
        before = len(historical_values)
        collect_large_ints(payload, historical_values)
        verified_sources.append({
            "path": entry["path"],
            "sha256": actual,
            "distinct_values_added": len(historical_values) - before,
        })

    streams = allocate()
    seeds = [row["seed"] for row in streams]
    collisions = sorted(set(seeds) & historical_values)
    if collisions:
        raise RuntimeError(f"New seed namespace collides with history: {collisions[:10]}")
    if len(seeds) != len(set(seeds)):
        raise RuntimeError("New stream seeds are not unique")
    expected_unique_shots = int(cfg["allocation"]["unique_shots"])
    allocated_shots = sum(int(row["shots"]) for row in streams if row["included_in_allocation"])
    if allocated_shots != expected_unique_shots:
        raise RuntimeError(f"inventory shot allocation mismatch: {allocated_shots} != {expected_unique_shots}")
    record = {
        "schema_version": 1,
        "study": cfg["study"],
        "sampling_performed": False,
        "sealed_test_access": False,
        "namespace_start": int(cfg["seeds"]["namespace_start"]),
        "stream_count_including_analysis_rng": len(streams),
        "sampling_stream_count": sum(row["role"] in {
            "profile_template", "calibration", "scoring", "evaluation"
        } for row in streams),
        "analysis_stream_count": sum(row["stream"] == "pcg64" for row in streams),
        "benchmark_stream_count": sum(str(row["role"]).startswith("benchmark_") for row in streams),
        "unique_seed_count": len(set(seeds)),
        "historical_values_screened": len(historical_values),
        "historical_inventory_source": {
            "path": str(HISTORICAL.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256(HISTORICAL),
            "recorded_historical_source_count": len(sources),
            "verification_locator": "exact historical source checkout supplied by --historical-root",
            "clone_line_ending_note": "the fresh clone normalizes some allowlisted JSON from CRLF to LF; JSON semantics match, while the prior audit records byte-level CRLF hashes",
        },
        "historical_sources_checked": verified_sources,
        "collisions": collisions,
        "expected_unique_shots": expected_unique_shots,
        "streams": streams,
        "previous_independent_audit_provenance": {
            "status": "available_in_previous_workspace; not tracked in this clone",
            "report_sha256": "e1a963987caf2ea3599e2d005c79b149b7c9181abf03783f60cd5e54c095be15",
            "audit_manifest_sha256": "785ab018ecc38e2567f262d8ab41d75708995b75b83926e0cf0ca058104b41dd",
            "static_reanalysis_sha256": "376e55f5113e2c8c97d14e4d163fec4ffe20cb6b697eb37531ef25a6c29a6667",
            "raw_arrays_in_current_clone": False,
        },
    }
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "SEED_INVENTORY_CREATED_NO_SAMPLING",
        "historical_source_count": len(verified_sources),
        "historical_integer_values_screened": len(historical_values),
        "stream_count": len(streams),
        "collisions": collisions,
        "shot_allocation": expected_unique_shots,
        "inventory_sha256": sha256(OUT),
    }, indent=2))


if __name__ == "__main__":
    main()
