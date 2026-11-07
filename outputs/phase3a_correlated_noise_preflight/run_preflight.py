"""Run a bounded, deterministic Phase 3A correlated-noise preflight.

Only metadata and development/diagnostic samples are read. No independent-test
sample, label, or seed allocation file is accessed by this runner.
"""
from __future__ import annotations

import csv
import hashlib
import json
import platform
import re
import sys
import time
from pathlib import Path

import numpy as np
import pymatching
import stim

from simulator import (DEFAULT_BURST_PAIR, build_isolated_burst_circuit,
                       build_matching, build_spatial_burst_circuit)
from noise_model import circuit_noise_record

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE
CONFIG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
SEEDS = [2503001001, 2503001002, 2503001003, 2503001004]
TEST_SEEDS = [2503002001, 2503002002, 2503002003, 2503002004]
EXPLORATORY_PRECONFIG_SEEDS = [2500000001]
REGIME = CONFIG["circuit"]["regime"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def seed_numbers(value, inherited=False):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from seed_numbers(child, inherited or "seed" in str(key).lower())
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from seed_numbers(child, inherited)
    elif inherited:
        if isinstance(value, int) and not isinstance(value, bool):
            yield int(value)
        elif isinstance(value, str):
            for token in re.findall(r"(?<!\d)\d{5,}(?!\d)", value):
                yield int(token)


def read_seed_inventory_files():
    files = []
    values = set()
    outputs = REPO / "outputs"
    for path in outputs.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".json", ".csv"}:
            continue
        if "seed" not in path.name.lower():
            continue
        if HERE in path.parents:
            continue
        rel_parts = [x.lower() for x in path.parts]
        # Do not enumerate or inspect anything located in sealed test folders.
        if any("independent_test" in x or "sealed_test" in x for x in rel_parts):
            continue
        per_file = set()
        try:
            if path.suffix.lower() == ".json":
                payload = json.loads(path.read_text(encoding="utf-8"))
                per_file.update(seed_numbers(payload))
            else:
                with path.open(newline="", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    seed_fields = [x for x in (reader.fieldnames or []) if "seed" in x.lower()]
                    for row in reader:
                        for field in seed_fields:
                            for token in re.findall(r"(?<!\d)\d{5,}(?!\d)", row.get(field, "")):
                                per_file.add(int(token))
        except Exception as exc:
            files.append({"path": path.relative_to(REPO).as_posix(), "status": "unreadable_seed_metadata",
                          "error": f"{type(exc).__name__}: {exc}", "values_extracted": 0})
            continue
        values.update(per_file)
        files.append({"path": path.relative_to(REPO).as_posix(), "status": "read_seed_metadata_only",
                      "values_extracted": len(per_file)})
    return files, values


def verify_historical_preservation():
    auto = REPO / "outputs/neural_decoder_diagnostic/autonomous_development"
    auto_run = auto / "run"
    auto_progress = json.loads((auto_run / "progress.json").read_text(encoding="utf-8"))
    auto_manifest = json.loads((auto_run / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
    auto_hash_errors = []
    for rel, expected in auto_manifest["file_sha256"].items():
        p = auto_run / Path(rel)
        if not p.is_file() or sha256(p) != expected:
            auto_hash_errors.append(rel)

    sprint = REPO / "outputs/neural_decoder_diagnostic/hybrid_residual_sprint_v1"
    sprint_run = sprint / "run"
    sprint_progress = json.loads((sprint_run / "PROGRESS.json").read_text(encoding="utf-8"))
    final_manifest_path = sprint / "post_run_audit/FINAL_EVIDENCE_MANIFEST.json"
    final_manifest = json.loads(final_manifest_path.read_text(encoding="utf-8"))
    sprint_hash_errors = []
    for entry in final_manifest["files"]:
        p = REPO / Path(entry["path"])
        if not p.is_file() or p.stat().st_size != entry["bytes"] or sha256(p) != entry["sha256"]:
            sprint_hash_errors.append(entry["path"])
    auto_post_manifest_logs = []
    auto_unexpected_hash_errors = []
    for mismatch in auto_hash_errors:
        if mismatch == "controller.stdout.log":
            p = auto_run / mismatch
            try:
                stdout_record = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                stdout_record = {}
            expected_empty_hash = hashlib.sha256(b"").hexdigest()
            expected_post_manifest = (auto_manifest["file_sha256"].get(mismatch) == expected_empty_hash
                                      and stdout_record.get("status") == "completed"
                                      and stdout_record.get("independent_test_access") == 0)
            if expected_post_manifest:
                auto_post_manifest_logs.append({"path": mismatch,
                    "classification": "post-manifest run-status stdout; empty when RUN_MANIFEST was written",
                    "current_sha256": sha256(p), "bytes": p.stat().st_size})
                continue
        auto_unexpected_hash_errors.append(mismatch)
    return {
        "autonomous_750k": {
            "progress_status": auto_progress["status"],
            "completed_jobs": len(auto_progress["completed_jobs"]),
            "independent_test_access": auto_progress.get("independent_test_access"),
            "run_manifest_entries_checked": len(auto_manifest["file_sha256"]),
            "run_manifest_hash_mismatches": auto_hash_errors,
            "explained_post_manifest_stdout_changes": auto_post_manifest_logs,
            "unexpected_run_manifest_hash_mismatches": auto_unexpected_hash_errors,
            "progress_sha256": sha256(auto_run / "progress.json"),
            "run_manifest_sha256": sha256(auto_run / "RUN_MANIFEST.json"),
        },
        "hybrid_residual_sprint": {
            "progress_status_preserved": sprint_progress["status"],
            "completed_jobs": len(sprint_progress["completed_jobs"]),
            "prior_readonly_audit_manifest_entries_checked": final_manifest["files_hashed"],
            "audit_manifest_hash_mismatches": sprint_hash_errors,
            "audit_manifest_sha256": sha256(final_manifest_path),
            "progress_sha256": sha256(sprint_run / "PROGRESS.json"),
        },
    }


def sample(circuit, shots, seed):
    return circuit.compile_detector_sampler(seed=seed).sample(
        shots=shots, separate_observables=True
    )


def text_sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def annotation_signature(circuit):
    return [str(inst) for inst in circuit if inst.name in {"DETECTOR", "OBSERVABLE_INCLUDE"}]


def main():
    start = time.perf_counter()
    preservation = verify_historical_preservation()
    if preservation["autonomous_750k"]["progress_status"] != "completed":
        raise RuntimeError("750K autonomous run is not recorded completed")
    if preservation["autonomous_750k"]["completed_jobs"] != 50:
        raise RuntimeError("750K autonomous run is missing jobs")
    if preservation["hybrid_residual_sprint"]["progress_status_preserved"] != "failed":
        raise RuntimeError("Historical hybrid sprint status unexpectedly changed")
    if preservation["autonomous_750k"]["unexpected_run_manifest_hash_mismatches"]:
        raise RuntimeError("750K historical run has unexplained manifest hash mismatches")
    if preservation["hybrid_residual_sprint"]["audit_manifest_hash_mismatches"]:
        raise RuntimeError("Hybrid historical audit manifest hash check failed")

    historical_files, historical_seeds = read_seed_inventory_files()
    all_new = SEEDS + TEST_SEEDS + EXPLORATORY_PRECONFIG_SEEDS
    final_allocated = SEEDS + TEST_SEEDS
    internal_collisions = sorted({s for s in final_allocated if final_allocated.count(s) > 1})
    historical_collisions = sorted(set(all_new) & historical_seeds)
    final_seed_collisions = sorted(set(final_allocated) & (historical_seeds | set(EXPLORATORY_PRECONFIG_SEEDS)))
    if internal_collisions or historical_collisions or final_seed_collisions:
        raise RuntimeError(f"Seed collision: internal={internal_collisions}, historical={historical_collisions}, final={final_seed_collisions}")

    c = CONFIG["circuit"]
    pair = tuple(c["burst_data_qubits"])
    zbase = build_spatial_burst_circuit(memory_basis="z", regime=REGIME,
        distance=c["distance"], rounds=c["rounds"], gate_p=0, measurement_p=0,
        bias_ratio=c["bias_ratio"], burst_probability=0, burst_pair=pair)
    zburst_only = build_spatial_burst_circuit(memory_basis="z", regime=REGIME,
        distance=c["distance"], rounds=c["rounds"], gate_p=0, measurement_p=0,
        bias_ratio=c["bias_ratio"], burst_probability=0.02, burst_pair=pair)
    if (zbase.num_detectors, zbase.num_observables) != (40, 1):
        raise RuntimeError("Unexpected detector/observable definition")

    zero_d, zero_l = sample(zbase, CONFIG["diagnostics"]["zero_noise_shots"], SEEDS[1])
    if np.any(zero_d) or np.any(zero_l):
        raise RuntimeError("Noiseless circuit produced a nonzero detector or logical observable")
    zero_corr = build_spatial_burst_circuit(memory_basis="z", regime=REGIME,
        distance=c["distance"], rounds=c["rounds"], gate_p=0, measurement_p=0,
        bias_ratio=c["bias_ratio"], burst_probability=0, burst_pair=pair)
    zc_d, zc_l = sample(zero_corr, 32, SEEDS[1])
    if not np.array_equal(zero_d, zc_d) or not np.array_equal(zero_l, zc_l):
        raise RuntimeError("Zero-correlation limit did not reproduce the zero-noise circuit")

    # Empirically expose a single common cause through direct Z measurements.
    toy_p = CONFIG["diagnostics"]["isolated_burst_probability"]
    toy_shots = CONFIG["diagnostics"]["isolated_burst_shots"]
    toy = build_isolated_burst_circuit(toy_p).compile_sampler(seed=SEEDS[0]).sample(toy_shots).astype(np.uint8)
    joint = float(np.mean((toy[:, 0] == 1) & (toy[:, 1] == 1)))
    discordant = int(np.count_nonzero(toy[:, 0] != toy[:, 1]))
    empirical_corr = float(np.corrcoef(toy.T)[0, 1])
    if discordant != 0 or joint <= 0 or joint >= 1 or empirical_corr < 0.99:
        raise RuntimeError("Isolated common-cause burst did not produce paired outcomes")

    burst_d, burst_l = sample(zburst_only, CONFIG["diagnostics"]["burst_only_surface_shots"], SEEDS[2])
    if not np.any(burst_d) and not np.any(burst_l):
        raise RuntimeError("Burst-only surface-code pilot showed no detector/logical response")

    full_blind = build_spatial_burst_circuit(memory_basis=c["memory_basis"], regime=REGIME,
        distance=c["distance"], rounds=c["rounds"], gate_p=c["gate_p"],
        measurement_p=c["measurement_p"], bias_ratio=c["bias_ratio"],
        burst_probability=0, burst_pair=pair)
    full_corr = build_spatial_burst_circuit(memory_basis=c["memory_basis"], regime=REGIME,
        distance=c["distance"], rounds=c["rounds"], gate_p=c["gate_p"],
        measurement_p=c["measurement_p"], bias_ratio=c["bias_ratio"],
        burst_probability=c["burst_probability_per_round"], burst_pair=pair)
    _, noise_record = circuit_noise_record(memory_basis=c["memory_basis"], regime=REGIME,
        distance=c["distance"], rounds=c["rounds"], gate_p=c["gate_p"],
        measurement_p=c["measurement_p"], bias_ratio=c["bias_ratio"])
    if abs(noise_record["1q_pauli_probability_sum"] - c["gate_p"]) > 1e-12:
        raise RuntimeError("1Q Pauli fault probabilities do not sum to the configured gate probability")
    if abs(noise_record["2q_pauli_probability_sum"] - c["gate_p"]) > 1e-12:
        raise RuntimeError("2Q Pauli-pair fault probabilities do not sum to the configured gate probability")
    if noise_record["measurement_flip_probability"] != c["measurement_p"]:
        raise RuntimeError("Measurement-fault probability differs from configuration")
    burst_instructions = [x for x in full_corr if x.name == "E"]
    burst_events_valid = (len(burst_instructions) == c["rounds"] and all(
        len(x.gate_args_copy()) == 1
        and abs(float(x.gate_args_copy()[0]) - c["burst_probability_per_round"]) <= 1e-15
        and [int(t.value) for t in x.targets_copy()] == list(pair)
        and all(t.is_x_target for t in x.targets_copy())
        for x in burst_instructions))
    if not burst_events_valid:
        raise RuntimeError("Burst instruction probability, count, or X targets do not match the frozen config")
    detector_defs_equal = annotation_signature(full_blind) == annotation_signature(full_corr)
    if not detector_defs_equal:
        raise RuntimeError("Adding burst events changed detector/observable annotation order")
    dem_blind, pm_blind = build_matching(full_blind, enable_correlations=False)
    dem_corr, pm_corr_off = build_matching(full_corr, enable_correlations=False)
    dem_corr_again, pm_corr_on = build_matching(full_corr, enable_correlations=True)
    if str(dem_corr) != str(dem_corr_again):
        raise RuntimeError("Correlation-enabled and disabled decoders did not use identical DEM text")
    if (dem_blind.num_detectors, dem_blind.num_observables) != (40, 1):
        raise RuntimeError("Blind DEM dimensions are invalid")
    if (dem_corr.num_detectors, dem_corr.num_observables) != (40, 1):
        raise RuntimeError("Burst-aware DEM dimensions are invalid")

    # Confirm the lossless DEM conversion is unavailable for the frozen
    # categorical two-qubit channels; never substitute a different channel.
    strict_dem_error = None
    try:
        full_corr.detector_error_model(decompose_errors=True, approximate_disjoint_errors=False)
    except Exception as exc:
        strict_dem_error = f"{type(exc).__name__}: {exc}"
    if strict_dem_error is None:
        raise RuntimeError("Expected unsupported strict DEM conversion to fail for PAULI_CHANNEL_2")

    d, obs = sample(full_corr, CONFIG["diagnostics"]["paired_decoder_shots"], SEEDS[3])
    # Same seed/circuit must reproduce the exact same sample; this is only a
    # deterministic check, not a second evaluation arm or a performance study.
    d_re, obs_re = sample(full_corr, CONFIG["diagnostics"]["paired_decoder_shots"], SEEDS[3])
    if not np.array_equal(d, d_re) or not np.array_equal(obs, obs_re):
        raise RuntimeError("Seeded Stim detector/observable samples are not reproducible")
    pred_blind = pm_blind.decode_batch(d).astype(np.uint8).reshape(-1, 1)
    pred_corr_off = pm_corr_off.decode_batch(d).astype(np.uint8).reshape(-1, 1)
    pred_corr_on = pm_corr_on.decode_batch(d).astype(np.uint8).reshape(-1, 1)
    if any(p.shape != obs.shape for p in (pred_blind, pred_corr_off, pred_corr_on)):
        raise RuntimeError("A matching arm produced the wrong prediction shape")

    np.savez_compressed(OUT / "preflight_paired_sample.npz",
        detectors=d.astype(np.uint8), observables=obs.astype(np.uint8),
        prediction_historical_blind=pred_blind,
        prediction_burst_model_correlations_off=pred_corr_off,
        prediction_burst_model_correlations_on=pred_corr_on)
    elapsed = time.perf_counter() - start

    source_files = [HERE / "config.json", HERE / "simulator.py", HERE / "run_preflight.py"]
    payload = {
        "status": "PASS_DETERMINISTIC_PREFLIGHT_ONLY",
        "completed_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "historical_preservation": preservation,
        "historical_seed_screen": {
            "sources_examined": historical_files,
            "unique_seed_values_extracted": len(historical_seeds),
            "formal_preflight_seeds": SEEDS,
            "unit_test_fixture_seeds": TEST_SEEDS,
            "pre_configuration_exploratory_seed_reuse": {
                "seeds_used": EXPLORATORY_PRECONFIG_SEEDS,
                "description": "A preliminary code/API smoke check used this seed before the formal diagnostic config; these samples are not part of any Phase 3B stream and were not saved.",
            },
            "internal_collision_count": len(internal_collisions),
            "historical_collision_count_including_exploratory": len(historical_collisions),
            "formal_preflight_collisions": len(final_seed_collisions),
            "independent_test_files_or_samples_accessed": 0,
        },
        "mechanism": {
            "spatial_burst_pair": list(pair),
            "pair_data_qubits_verified": True,
            "mr_boundaries": sum(x.name == "MR" for x in zbase),
            "burst_sites_in_full_circuit": sum(x.name == "E" for x in full_corr),
            "burst_probability_per_round": c["burst_probability_per_round"],
            "zero_noise_detector_nonzero_count": int(np.count_nonzero(zero_d)),
            "zero_noise_observable_nonzero_count": int(np.count_nonzero(zero_l)),
            "burst_only_surface_shots": int(len(burst_d)),
            "burst_only_nonzero_detector_shots": int(np.count_nonzero(np.any(burst_d, axis=1))),
            "burst_only_nonzero_observable_shots": int(np.count_nonzero(np.any(burst_l, axis=1))),
            "isolated_burst_empirical": {
                "shots": toy_shots, "probability": toy_p, "joint_error_rate": joint,
                "marginal_error_rates": [float(toy[:, i].mean()) for i in range(2)],
                "discordant_pair_count": discordant, "pearson_correlation": empirical_corr,
                "seed": SEEDS[0],
            },
        },
        "circuit_and_dem": {
            "detectors": full_corr.num_detectors, "observables": full_corr.num_observables,
            "detector_and_observable_annotations_identical": detector_defs_equal,
            "phase2b_noise_probabilities": noise_record,
            "burst_instruction_validation": {"passed": burst_events_valid,
                "count": len(burst_instructions), "probability_each": c["burst_probability_per_round"],
                "targets_each": list(pair), "pauli_each": "XX"},
            "noiseless_limit_pass": True, "zero_correlation_limit_pass": True,
            "dem_parameters": {"decompose_errors": True, "approximate_disjoint_errors": True},
            "blind_dem_errors": dem_blind.num_errors, "burst_dem_errors": dem_corr.num_errors,
            "burst_dem_separator_records": sum("^" in line for line in str(dem_corr).splitlines() if line.startswith("error(")),
            "dem_detector_counts_equal": dem_blind.num_detectors == dem_corr.num_detectors,
            "dem_observable_counts_equal": dem_blind.num_observables == dem_corr.num_observables,
            "burst_circuit_sha256": text_sha(str(full_corr)),
            "burst_dem_sha256": text_sha(str(dem_corr)),
            "blind_dem_sha256": text_sha(str(dem_blind)),
            "strict_approximate_disjoint_false_result": strict_dem_error,
        },
        "paired_decoder_smoke": {
            "shots": len(d), "seed": SEEDS[3], "shared_detector_array": True,
            "shared_observable_array": True, "same_seed_reproduced": True,
            "prediction_shape": list(pred_blind.shape),
            "baseline_vs_aware_off_disagreements": int(np.count_nonzero(pred_blind != pred_corr_off)),
            "baseline_vs_aware_on_disagreements": int(np.count_nonzero(pred_blind != pred_corr_on)),
            "aware_off_vs_on_disagreements": int(np.count_nonzero(pred_corr_off != pred_corr_on)),
            "historical_blind_errors": int(np.count_nonzero(pred_blind != obs)),
            "burst_model_correlations_off_errors": int(np.count_nonzero(pred_corr_off != obs)),
            "burst_model_correlations_on_errors": int(np.count_nonzero(pred_corr_on != obs)),
            "correlation_enabled_dem_is_identical": True,
            "graph_edges": {
                "historical_blind": len(pm_blind.edges()),
                "burst_model_off": len(pm_corr_off.edges()),
                "burst_model_on": len(pm_corr_on.edges()),
            },
        },
        "resource": {"diagnostic_wall_seconds": elapsed},
        "software": {"python": platform.python_version(), "stim": stim.__version__,
                     "pymatching": pymatching.__version__, "numpy": np.__version__},
        "integrity": {p.name: sha256(p) for p in source_files},
        "limitations": [
            "The spatial common-cause burst is a synthetic stochastic proxy, not a calibrated hardware crosstalk model.",
            "Only small diagnostic samples were generated; no LER comparison is confirmatory.",
            "The native categorical PAULI_CHANNEL_2 to DEM conversion uses approximate_disjoint_errors=True.",
            "A full multi-qubit correlated event may be hypergraph-like and can be unsupported by graph matching without a valid decomposition.",
        ],
    }
    (OUT / "PREFLIGHT_RESULTS.json").write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "shots": {
        "isolated_channel": toy_shots, "zero_noise": len(zero_d),
        "burst_surface": len(burst_d), "paired_decoding": len(d),
    }, "seed_collisions": final_seed_collisions,
        "detectors": full_corr.num_detectors, "dem_errors": dem_corr.num_errors,
        "correlation_disagreement": payload["paired_decoder_smoke"]["aware_off_vs_on_disagreements"],
        "seconds": elapsed}, indent=2))


if __name__ == "__main__":
    main()
