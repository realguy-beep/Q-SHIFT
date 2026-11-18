"""Independent validation of a frozen sequential detector calibration rule."""
from __future__ import annotations

import json
import time
from pathlib import Path

from adaptive_basis_sprt import PROFILES, evaluate, sample_scores

HERE = Path(__file__).resolve().parent
PRE_SEEDS = (2026115391, 2026115392)
MAIN_SEEDS = (2026115401, 2026115402)
PRE_WINDOWS = 500
MAIN_WINDOWS = 2_500
MAX_SHOTS = 500


def run(preflight: bool) -> dict:
    started = time.perf_counter()
    frozen = json.loads((HERE / "adaptive_basis_sprt_results.json").read_text())
    windows = PRE_WINDOWS if preflight else MAIN_WINDOWS
    seeds = PRE_SEEDS if preflight else MAIN_SEEDS
    validation, rows = {}, []
    for i, profile in enumerate(PROFILES):
        scores, seconds, resources = sample_scores(profile, windows * MAX_SHOTS, seeds[i])
        validation[profile] = scores
        rows.append(
            {
                "profile": profile,
                "seed": seeds[i],
                "windows": windows,
                "shots": windows * MAX_SHOTS,
                "sampling_seconds": seconds,
                "resources": resources,
            }
        )
    metrics = evaluate(None, validation, windows, frozen_parameters=frozen)
    elapsed = time.perf_counter() - started
    output = {
        **metrics,
        "status": "sequential_calibration_replication_preflight" if preflight else "sequential_calibration_independent_replication",
        "frozen_training_source": "adaptive_basis_sprt_results.json; means, variances, LDA, and threshold unchanged",
        "sample_rows": rows,
        "elapsed_seconds": elapsed,
        "new_source_equivalent_samples": sum(row["shots"] for row in rows),
        "scope": "independent detector calibration validation only; no LER or hardware claim",
    }
    if preflight:
        output["projected_main_seconds"] = elapsed * MAIN_WINDOWS / PRE_WINDOWS
        output["runtime_cap_seconds"] = 300
        output["runtime_gate_passed"] = output["projected_main_seconds"] <= 300
        path = HERE / "adaptive_basis_sprt_replication_preflight.json"
    else:
        path = HERE / "adaptive_basis_sprt_replication_results.json"
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": output["status"],
                "projected_main_seconds": output.get("projected_main_seconds"),
                "sprt_errors": [row["sprt_errors"] for row in output["per_profile"]],
                "sprt_upper_bounds": [row["sprt_exact_95_ci"][1] for row in output["per_profile"]],
                "mean_shots": [row["mean_shots_consumed"] for row in output["per_profile"]],
                "output": str(path),
            },
            indent=2,
        )
    )
    return output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    result = run(args.preflight)
    if args.preflight and not result["runtime_gate_passed"]:
        raise SystemExit(1)
