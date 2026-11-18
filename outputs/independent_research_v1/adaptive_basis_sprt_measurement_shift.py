"""Frozen sequential detector calibration under increased measurement noise."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from adaptive_basis_sprt import PROFILES, evaluate
from bias_identification import FEATURES, feature_masks, make_features
from basis_alignment_distance7 import build

HERE = Path(__file__).resolve().parent
FROZEN = json.loads((HERE / "adaptive_basis_sprt_results.json").read_text())
FROZEN_LDA = json.loads((HERE / "bias_identification_results.json").read_text())["training"]
PRE_SEEDS = (2026115901, 2026115902)
MAIN_SEEDS = (2026115911, 2026115912)
PRE_WINDOWS = 100
MAIN_WINDOWS = 1_000
SHOTS_PER_WINDOW = 500
GATE_P = 0.003
MEASUREMENT_P = 0.006


def score_stream(profile: str, count: int, seed: int) -> tuple[np.ndarray, float, dict]:
    circuit = build(
        "z", profile, 3, 5, bias_ratio=10.0, gate_p=GATE_P, measurement_p=MEASUREMENT_P
    )
    masks = feature_masks(circuit, 3, 5)
    started = time.perf_counter()
    detectors = circuit.compile_detector_sampler(seed=seed).sample(shots=count)
    elapsed = time.perf_counter() - started
    features = make_features(detectors, masks)
    weights = np.asarray(FROZEN_LDA["weights"], dtype=float)
    intercept = float(FROZEN_LDA["intercept"])
    scores = features @ weights + intercept
    if not np.isfinite(scores).all():
        raise RuntimeError(f"non-finite score under shifted composition for {profile}")
    return scores, elapsed, {"detectors": int(circuit.num_detectors), "feature_count": len(FEATURES), "bucket_sizes": [int(mask.sum()) for mask in masks]}


def run(preflight: bool) -> dict:
    from noise_model import build_circuit as source_build

    started = time.perf_counter()
    source_matches = {
        profile: str(build("z", profile, 3, 5, bias_ratio=10.0, gate_p=GATE_P, measurement_p=MEASUREMENT_P))
        == str(source_build("z", profile, distance=3, rounds=5, bias_ratio=10.0, gate_p=GATE_P, measurement_p=MEASUREMENT_P))
        for profile in PROFILES
    }
    if not all(source_matches.values()):
        raise RuntimeError(f"shifted calibration circuit differs from source: {source_matches}")
    windows = PRE_WINDOWS if preflight else MAIN_WINDOWS
    seeds = PRE_SEEDS if preflight else MAIN_SEEDS
    validation, rows = {}, []
    for i, profile in enumerate(PROFILES):
        scores, seconds, resources = score_stream(profile, windows * SHOTS_PER_WINDOW, seeds[i])
        validation[profile] = scores
        rows.append({"profile": profile, "seed": seeds[i], "windows": windows, "shots": windows * SHOTS_PER_WINDOW, "sampling_seconds": seconds, "score_mean": float(scores.mean()), "score_variance": float(scores.var(ddof=1)), "resources": resources})
    metrics = evaluate(None, validation, windows, frozen_parameters=FROZEN)
    elapsed = time.perf_counter() - started
    output = {
        **metrics,
        "status": "measurement_shift_preflight" if preflight else "measurement_shift_validation",
        "gate_p": GATE_P,
        "measurement_p": MEASUREMENT_P,
        "bias_ratio": 10,
        "source_builder_byte_identical": source_matches,
        "frozen_model_source": "nominal p=.003 adaptive_basis_sprt_results.json; no fit/recalibration",
        "sample_rows": rows,
        "elapsed_seconds": elapsed,
        "new_source_equivalent_samples": sum(row["shots"] for row in rows),
        "scope": "single measurement-noise composition stress; detector-only classifier, no LER result",
    }
    if preflight:
        output["projected_main_seconds"] = elapsed * MAIN_WINDOWS / PRE_WINDOWS
        output["runtime_cap_seconds"] = 300
        output["runtime_gate_passed"] = output["projected_main_seconds"] <= 300
        path = HERE / "adaptive_basis_sprt_measurement_shift_preflight.json"
    else:
        path = HERE / "adaptive_basis_sprt_measurement_shift_results.json"
    path.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "projected_main_seconds": output.get("projected_main_seconds"), "errors": [r["sprt_errors"] for r in output["per_profile"]], "mean_shots": [r["mean_shots_consumed"] for r in output["per_profile"]], "output": str(path)}, indent=2))
    return output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    result = run(args.preflight)
    if args.preflight and not result["runtime_gate_passed"]:
        raise SystemExit(1)
