"""Run the small, deterministic architecture and correlated-noise preflight.

No model is trained. The script samples only the explicitly configured
diagnostic stream, checks both matching comparators on the same shots, and
checks candidate forward/gradient plumbing on actual Stim detector geometry.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pymatching
import stim
import torch

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "dashboard") not in sys.path:
    sys.path.insert(0, str(ROOT / "dashboard"))

from dashboard.seed_protocol import historical_seeds  # noqa: E402
from outputs.cnn_architecture_stage1_v1.cnn_architectures import (  # noqa: E402
    FactorizedSpatialTemporalResidualCNN,
    ResidualPositionCNNV2,
    parameter_count,
)
from outputs.phase3a_correlated_noise_preflight.simulator import (  # noqa: E402
    build_matching,
    build_spatial_burst_circuit,
)
from outputs.neural_decoder_diagnostic.autonomous_development.experiment import (  # noqa: E402
    ResidualPositionCNN as HistoricalResidualPositionCNN,
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def binary_array(name: str, value: np.ndarray) -> np.ndarray:
    result = np.asarray(value)
    if not np.isin(result, (0, 1)).all():
        raise ValueError(f"{name} contains non-binary values")
    return result.astype(np.uint8, copy=False)


def main() -> int:
    config = json.loads((OUT / "preflight_config.json").read_text(encoding="utf-8"))
    seed_inventory = json.loads((OUT / "seed_inventory.json").read_text(encoding="utf-8"))
    seeds = {name: int(value) for name, value in seed_inventory["streams"].items()}
    if len(seeds.values()) != len(set(seeds.values())):
        raise RuntimeError("Diagnostic RNG seeds are not unique")
    hist = historical_seeds()
    phase3a = json.loads((ROOT / "outputs/phase3a_correlated_noise_preflight/PREFLIGHT_RESULTS.json").read_text(encoding="utf-8"))
    prior = set(int(v) for v in phase3a["historical_seed_screen"]["formal_preflight_seeds"])
    prior.update(int(v) for v in phase3a["historical_seed_screen"]["unit_test_fixture_seeds"])
    prior.update(int(v) for v in phase3a["historical_seed_screen"]["pre_configuration_exploratory_seed_reuse"]["seeds_used"])
    collisions_historical = sorted(set(seeds.values()) & hist)
    collisions_phase3a = sorted(set(seeds.values()) & prior)
    if collisions_historical or collisions_phase3a:
        raise RuntimeError(f"Seed collision: archived={collisions_historical}; Phase3A={collisions_phase3a}")

    c = config["circuit"]
    base = build_spatial_burst_circuit(
        memory_basis=c["memory_basis"], regime=c["regime"], distance=c["distance"],
        rounds=c["rounds"], gate_p=c["gate_probability"],
        measurement_p=c["measurement_probability"], bias_ratio=c["bias_ratio"],
        burst_probability=0.0, burst_pair=tuple(c["burst_pair_data_qubits"]),
    )
    burst = build_spatial_burst_circuit(
        memory_basis=c["memory_basis"], regime=c["regime"], distance=c["distance"],
        rounds=c["rounds"], gate_p=c["gate_probability"],
        measurement_p=c["measurement_probability"], bias_ratio=c["bias_ratio"],
        burst_probability=c["burst_probability_per_round"],
        burst_pair=tuple(c["burst_pair_data_qubits"]),
    )
    if (base.num_detectors, base.num_observables) != (40, 1):
        raise RuntimeError("Base circuit detector/observable signature changed")
    if (burst.num_detectors, burst.num_observables) != (40, 1):
        raise RuntimeError("Burst circuit detector/observable signature changed")
    coords_base = base.get_detector_coordinates()
    coords_burst = burst.get_detector_coordinates()
    if coords_base != coords_burst or sorted(coords_base) != list(range(40)):
        raise RuntimeError("Base and burst circuits do not share the same detector mapping")

    start = time.perf_counter()
    dem_fixed, fixed = build_matching(base, enable_correlations=True)
    dem_burst, informed = build_matching(burst, enable_correlations=True)
    construction_seconds = time.perf_counter() - start
    if (dem_fixed.num_detectors, dem_fixed.num_observables) != (40, 1):
        raise RuntimeError("Fixed DEM dimensions do not match the expected circuit")
    if (dem_burst.num_detectors, dem_burst.num_observables) != (40, 1):
        raise RuntimeError("Burst-informed DEM dimensions do not match the expected circuit")
    if fixed.num_detectors != informed.num_detectors or fixed.num_detectors != 40:
        raise RuntimeError("Matching graph detector counts differ")

    noiseless = build_spatial_burst_circuit(
        memory_basis="z", regime="balanced", distance=3, rounds=5,
        gate_p=0.0, measurement_p=0.0, bias_ratio=c["bias_ratio"],
        burst_probability=0.0, burst_pair=tuple(c["burst_pair_data_qubits"]),
    )
    d0, o0 = noiseless.compile_detector_sampler(seed=seeds["stim_noiseless_structure_check"]).sample(
        config["diagnostics"]["stim_noiseless_shots"], separate_observables=True)
    d0, o0 = binary_array("noiseless detectors", d0), binary_array("noiseless observable", o0)
    if d0.shape != (16, 40) or o0.shape != (16, 1) or d0.any() or o0.any():
        raise RuntimeError("Noiseless circuit behavior did not match the expected all-zero result")

    shots = int(config["diagnostics"]["stim_correlated_shots"])
    det, obs = burst.compile_detector_sampler(seed=seeds["stim_correlated_diagnostic"]).sample(
        shots, separate_observables=True)
    det, obs = binary_array("correlated detectors", det), binary_array("correlated observable", obs)
    if det.shape != (shots, 40) or obs.shape != (shots, 1):
        raise RuntimeError(f"Invalid paired Stim shapes: {det.shape}, {obs.shape}")
    t_decode = time.perf_counter()
    pred_fixed = np.asarray(fixed.decode_batch(det), dtype=np.uint8)
    pred_burst = np.asarray(informed.decode_batch(det), dtype=np.uint8)
    decode_seconds = time.perf_counter() - t_decode
    if pred_fixed.shape != (shots, 1) or pred_burst.shape != (shots, 1):
        raise RuntimeError("PyMatching predictions have an unexpected shape")
    pred_fixed, pred_burst = binary_array("fixed predictions", pred_fixed), binary_array("burst predictions", pred_burst)

    x = torch.as_tensor(det[:config["diagnostics"]["model_batch_size"]], dtype=torch.float32)
    pm = torch.as_tensor(pred_fixed[:len(x), 0], dtype=torch.float32)
    torch.manual_seed(seeds["torch_candidate_initialization"])
    architecture_classes = (
        ("historical_residual_position_cnn", HistoricalResidualPositionCNN),
        ("residual_position_v2", ResidualPositionCNNV2),
        ("factorized_spatiotemporal_residual", FactorizedSpatialTemporalResidualCNN),
    )
    architecture_results = {}
    benchmark_batch = min(256, len(det))
    benchmark_x = torch.as_tensor(det[:benchmark_batch], dtype=torch.float32)
    benchmark_pm = torch.as_tensor(pred_fixed[:benchmark_batch, 0], dtype=torch.float32)
    torch.set_num_threads(1)
    for name, cls in architecture_classes:
        model = cls(coords_base, dropout=0.0).to("cpu")
        model.eval()
        with torch.inference_mode():
            logits = model(benchmark_x, benchmark_pm)
        if logits.shape != (benchmark_batch,) or not torch.isfinite(logits).all().item():
            raise RuntimeError(f"{name} failed finite forward-shape check")
        with torch.inference_mode():
            for _ in range(5):
                model(benchmark_x, benchmark_pm)
            times = []
            for _ in range(5):
                tic = time.perf_counter()
                for _ in range(25):
                    model(benchmark_x, benchmark_pm)
                times.append((time.perf_counter() - tic) / 25)
        architecture_results[name] = {
            "parameters": parameter_count(model),
            "float32_parameter_storage_bytes": parameter_count(model) * 4,
            "input_detector_shape": list(benchmark_x.shape),
            "input_matching_prediction_shape": list(benchmark_pm.shape),
            "output_logit_shape": list(logits.shape),
            "finite_forward": True,
            "cpu_batch_inference_median_seconds": float(np.median(times)),
            "cpu_per_shot_inference_median_microseconds": float(np.median(times) * 1e6 / benchmark_batch),
            "cpu_benchmark_trials": 5,
            "cpu_forwards_per_trial": 25,
            "trained": False,
            "scored_as_decoder": False,
        }
        if torch.cuda.is_available():
            device = torch.device("cuda:0")
            gpu_model = model.to(device)
            gpu_x, gpu_pm = benchmark_x.to(device), benchmark_pm.to(device)
            torch.cuda.synchronize(device)
            torch.cuda.reset_peak_memory_stats(device)
            with torch.inference_mode():
                for _ in range(10):
                    gpu_model(gpu_x, gpu_pm)
                torch.cuda.synchronize(device)
                gpu_times = []
                for _ in range(5):
                    start_event = torch.cuda.Event(enable_timing=True)
                    end_event = torch.cuda.Event(enable_timing=True)
                    start_event.record()
                    for _ in range(100):
                        gpu_model(gpu_x, gpu_pm)
                    end_event.record()
                    end_event.synchronize()
                    gpu_times.append(start_event.elapsed_time(end_event) / 100 / 1000)
            architecture_results[name]["cuda_batch_inference_median_seconds"] = float(np.median(gpu_times))
            architecture_results[name]["cuda_per_shot_inference_median_microseconds"] = float(
                np.median(gpu_times) * 1e6 / benchmark_batch)
            architecture_results[name]["cuda_benchmark_trials"] = 5
            architecture_results[name]["cuda_forwards_per_trial"] = 100
            architecture_results[name]["cuda_peak_allocated_bytes"] = int(
                torch.cuda.max_memory_allocated(device))
            model.to("cpu")

    observable = obs[:, 0]
    errors_fixed = pred_fixed[:, 0] ^ observable
    errors_burst = pred_burst[:, 0] ^ observable
    det_bytes = np.ascontiguousarray(det).tobytes()
    obs_bytes = np.ascontiguousarray(obs).tobytes()
    pred_bytes = np.ascontiguousarray(np.stack([pred_fixed[:, 0], pred_burst[:, 0]])).tobytes()
    evidence = {
        "status": "PASS_DIAGNOSTIC_ONLY_NO_TRAINING",
        "scope": "Small plumbing diagnostic only; not a training, model-selection, or performance study.",
        "independent_test_access": 0,
        "training_steps": 0,
        "final_evaluation_shots": 0,
        "runtime": {
            "matching_construction_seconds": construction_seconds,
            "paired_decode_seconds": decode_seconds,
            "wall_seconds": time.perf_counter() - start,
        },
        "software": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "stim": stim.__version__,
            "pymatching": pymatching.__version__,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        },
        "seeds": seeds,
        "seed_screen": {
            "archived_recoverable_values": len(hist),
            "additional_phase3a_values_checked": len(prior),
            "new_seed_count": len(seeds),
            "new_seed_values_unique": len(set(seeds.values())) == len(seeds),
            "historical_collisions": collisions_historical,
            "phase3a_collisions": collisions_phase3a,
        },
        "circuit": {
            "memory_basis": c["memory_basis"], "distance": c["distance"], "rounds": c["rounds"],
            "regime": c["regime"], "gate_probability": c["gate_probability"],
            "measurement_probability": c["measurement_probability"],
            "burst_pair": c["burst_pair_data_qubits"],
            "burst_probability_per_round": c["burst_probability_per_round"],
            "detectors": burst.num_detectors, "observables": burst.num_observables,
            "same_detector_coordinates_as_base": coords_base == coords_burst,
            "dem_conversion": {"decompose_errors": True, "approximate_disjoint_errors": True},
            "fixed_dem_error_records": sum(1 for line in str(dem_fixed).splitlines() if line.startswith("error(")),
            "burst_dem_error_records": sum(1 for line in str(dem_burst).splitlines() if line.startswith("error(")),
            "fixed_matching_edges": fixed.num_edges,
            "burst_matching_edges": informed.num_edges,
            "noiseless_check_shots": len(d0),
            "noiseless_detector_nonzero": int(d0.sum()),
            "noiseless_observable_nonzero": int(o0.sum()),
        },
        "paired_correlated_diagnostic": {
            "shots": shots,
            "detector_shape": list(det.shape), "observable_shape": list(obs.shape),
            "detector_sha256": sha256_bytes(det_bytes),
            "observable_sha256": sha256_bytes(obs_bytes),
            "paired_prediction_sha256": sha256_bytes(pred_bytes),
            "frozen_pymatching": {
                "errors": int(errors_fixed.sum()), "ler_diagnostic_only": float(errors_fixed.mean()),
            },
            "burst_informed_pymatching": {
                "errors": int(errors_burst.sum()), "ler_diagnostic_only": float(errors_burst.mean()),
            },
            "decoder_disagreements": int(np.sum(pred_fixed[:, 0] != pred_burst[:, 0])),
            "same_detector_and_label_arrays": True,
            "interpretation": "Counts on 256 diagnostic shots validate paired wiring only; do not interpret them as a decoder comparison or evidence of improvement.",
        },
        "candidate_forward_checks": architecture_results,
        "source_hashes": {},
    }
    source_paths = [
        OUT / "cnn_architectures.py", OUT / "run_preflight.py", OUT / "preflight_config.json",
        OUT / "seed_inventory.json", OUT / "tests" / "test_cnn_architectures.py",
        ROOT / "dashboard" / "structured_decoder.py",
        ROOT / "outputs" / "phase2b_pauli_bias" / "noise_model.py",
        ROOT / "outputs" / "phase3a_correlated_noise_preflight" / "simulator.py",
        ROOT / "outputs" / "neural_decoder_diagnostic" / "autonomous_development" / "experiment.py",
    ]
    evidence["source_hashes"] = {
        str(path.relative_to(ROOT)): sha256_file(path) for path in source_paths
    }
    result_path = OUT / "PREFLIGHT_RESULTS.json"
    result_path.write_bytes((json.dumps(evidence, indent=2, allow_nan=False) + "\n").encode("utf-8"))
    print(json.dumps({
        "status": evidence["status"], "shots": shots,
        "fixed_errors_diagnostic_only": int(errors_fixed.sum()),
        "burst_informed_errors_diagnostic_only": int(errors_burst.sum()),
        "disagreements": int(np.sum(pred_fixed[:, 0] != pred_burst[:, 0])),
        "architecture_parameters": {k: v["parameters"] for k, v in architecture_results.items()},
        "cpu_microbench_us_per_shot": {k: round(v["cpu_per_shot_inference_median_microseconds"], 3)
                                       for k, v in architecture_results.items()},
        "cuda_microbench_us_per_shot": {k: round(v["cuda_per_shot_inference_median_microseconds"], 3)
                                        for k, v in architecture_results.items()
                                        if "cuda_per_shot_inference_median_microseconds" in v},
        "seed_collisions": len(collisions_historical) + len(collisions_phase3a),
        "result": str(result_path.relative_to(ROOT)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
