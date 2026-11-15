"""One authorized, non-resumable V1.1 recovery of the failed V1 pilot."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time

import numpy as np
import psutil
import pymatching
import stim

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(REPO / "outputs" / "phase3a_correlated_noise_preflight") not in sys.path:
    sys.path.insert(0, str(REPO / "outputs" / "phase3a_correlated_noise_preflight"))

from qshift_core_v1.contracts import DecoderPrediction
from qshift_core_v1.evaluation import evaluate_paired
from qshift_core_v1.pymatching_adapter import PyMatchingDecoder
from recovery_support_v1_1 import (RECOVERY, SAMPLES, sha_file, git_identity,
                                   load_training_and_fit, reconstruct_calibration,
                                   verify_recovery_inputs)
from simulator import build_spatial_burst_circuit

CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
SEEDS = json.loads((ROOT / "seed_inventory.json").read_text(encoding="utf-8"))["seeds"]
P_VALUES = tuple(float(p) for p in CFG["circuit"]["burst_probabilities"])
MAX_WALL = int(CFG["resource_limits"]["wall_seconds"])
MAX_RSS = int(CFG["resource_limits"]["peak_process_working_set_bytes"])
MAX_ARTIFACTS = int(CFG["resource_limits"]["artifact_bytes"])
MIN_FREE = int(CFG["resource_limits"]["minimum_free_disk_bytes"])
PRIOR_WALL = None


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def atomic_npz(path: Path, **arrays) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            np.savez_compressed(f, **arrays)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def sha_bytes(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


def circuit_for(p: float) -> stim.Circuit:
    c = CFG["circuit"]
    return build_spatial_burst_circuit(
        memory_basis=c["memory_basis"], regime=c["pauli_regime"],
        distance=c["distance"], rounds=c["rounds"],
        gate_p=c["gate_probability"], measurement_p=c["measurement_probability"],
        bias_ratio=c["bias_ratio"], burst_probability=float(p),
        burst_pair=tuple(c["burst_pair"]),
    )


def decoder_for(p: float, name: str):
    started = time.perf_counter()
    circuit = circuit_for(p)
    c = CFG["circuit"]
    dem = circuit.detector_error_model(
        decompose_errors=c["dem"]["decompose_errors"],
        approximate_disjoint_errors=c["dem"]["approximate_disjoint_errors"],
    )
    if (dem.num_detectors != c["expected_detectors"]
            or dem.num_observables != c["expected_observables"]):
        raise RuntimeError("recovery DEM shape differs from frozen configuration")
    circuit_sha = sha_bytes(str(circuit).encode("utf-8"))
    dem_sha = sha_bytes(str(dem).encode("utf-8"))
    decoder = PyMatchingDecoder.from_detector_error_model(
        dem, correlation_mode=bool(c["dem"]["pymatching_enable_correlations"]),
        name=name, noise_model_id=f"spatial-burst-dem:{dem_sha}",
    )
    return decoder, time.perf_counter() - started, circuit_sha, dem_sha


class CapturingDecoder:
    def __init__(self, decoder):
        self._decoder = decoder
        self.metadata = decoder.metadata
        self.last_bits = None

    def decode(self, detectors: np.ndarray) -> DecoderPrediction:
        result = self._decoder.decode(detectors)
        self.last_bits = np.array(result.bits, dtype=np.uint8, copy=True)
        return result


def peak_working_set() -> int:
    info = psutil.Process().memory_info()
    value = getattr(info, "peak_wset", None)
    if value is None or int(value) <= 0:
        raise RuntimeError("peak process working-set metric unavailable")
    return int(value)


def artifact_bytes() -> int:
    return sum(p.stat().st_size for p in SAMPLES.rglob("*") if p.is_file())


def guard(started: float) -> None:
    if PRIOR_WALL + time.monotonic() - started > MAX_WALL:
        raise RuntimeError("combined elapsed wall-clock limit exceeded")
    if peak_working_set() > MAX_RSS:
        raise RuntimeError("1-GiB peak process working-set limit exceeded")
    if shutil.disk_usage(ROOT).free < MIN_FREE:
        raise RuntimeError("minimum free-disk limit violated")
    if artifact_bytes() > MAX_ARTIFACTS:
        raise RuntimeError("128-MiB artifact limit exceeded")


def sample(circuit: stim.Circuit, shots: int, seed: int):
    if seed <= 0 or seed > 2**31 - 1:
        raise ValueError("seed outside frozen positive 31-bit range")
    started = time.perf_counter()
    detector, labels = circuit.compile_detector_sampler(seed=int(seed)).sample(
        shots=int(shots), separate_observables=True
    )
    elapsed = time.perf_counter() - started
    detector = np.asarray(detector, dtype=np.uint8)
    labels = np.asarray(labels, dtype=np.uint8)
    if detector.shape != (shots, 40) or labels.shape != (shots, 1):
        raise RuntimeError("recovery sampler returned an unexpected shape")
    if not np.isin(detector, [0, 1]).all() or not np.isin(labels, [0, 1]).all():
        raise RuntimeError("recovery sampler returned nonbinary data")
    return detector, labels, elapsed


def run() -> dict:
    # Validate everything before creating the new evidence directory or sampling.
    global PRIOR_WALL
    inputs = verify_recovery_inputs(require_no_output=True)
    PRIOR_WALL = float(inputs["status"].get("wall_seconds", 0.0))
    git = git_identity()
    model = load_training_and_fit()
    calibration = reconstruct_calibration(model)
    if set(SEEDS) != set(json.loads((ROOT / "seed_inventory.json").read_text())["seeds"]):
        raise RuntimeError("seed inventory changed during recovery setup")
    if len(set(SEEDS.values())) != len(SEEDS):
        raise RuntimeError("duplicate frozen seed values")
    if len(calibration["estimates"]) != 50:
        raise RuntimeError("reconstructed calibration profile count mismatch")

    RECOVERY.mkdir(parents=False, exist_ok=False)
    started = time.monotonic()
    state = {
        "schema": "qshift-performance-recovery-status-v1.1", "status": "running",
        "recovery_sampler_calls_started": 0, "recovery_rows_returned": 0,
        "committed_roots": 0, "committed_evaluation_rows": 0,
        "verified_unique_total_rows": 30000, "prior_attempt_calls": 56,
        "prior_attempt_rows_started": 32000, "prior_attempt_durable_training_cal_rows": 30000,
        "recovery_seed_replay": "eval:p0:r00", "error_type": None,
    }
    atomic_json(RECOVERY / "status.json", state)
    atomic_json(RECOVERY / "run_start.json", {
        "git": git, "recovery_source_manifest_sha256": sha_file(ROOT / "RECOVERY_SOURCE_MANIFEST_V1_1.json"),
        "recovery_input_inventory_sha256": sha_file(ROOT / "RECOVERY_INPUT_INVENTORY_V1_1.json"),
        "v1_source_manifest_sha256": sha_file(ROOT / "source_manifest.json"),
        "config_sha256": sha_file(ROOT / "config.json"),
        "seed_inventory_sha256": sha_file(ROOT / "seed_inventory.json"),
        "python": sys.version, "stim": stim.__version__, "pymatching": pymatching.__version__,
        "numpy": np.__version__, "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "prior_failed_attempt_status_sha256": inputs["inventory"]["original_attempt_status_sha256"],
        "recovery_policy": "single replay/continuation; no resume or seed substitution",
    })

    calls = 0
    calls_completed = 0
    returned_rows = 0
    decode_seconds = 0.0
    sampling_seconds = 0.0
    construct_seconds = {"pooled_fixed": None, "nominal_no_burst": None,
                         "oracle_by_probability": {}, "profile_total": 0.0}
    try:
        circuits = {i: circuit_for(p) for i, p in enumerate(P_VALUES)}
        static, construct_seconds["pooled_fixed"], static_circuit_sha, static_dem_sha = decoder_for(
            calibration["p_global"], "pooled_fixed"
        )
        no_burst, construct_seconds["nominal_no_burst"], _, _ = decoder_for(0.0, "nominal_no_burst")
        oracle = {}
        oracle_dem_hashes = {}
        for i, p in enumerate(P_VALUES):
            (oracle[i], construct_seconds["oracle_by_probability"][str(p)],
             _, oracle_dem_hashes[str(p)]) = decoder_for(p, "oracle_true_p")
        estimator_hash = sha_bytes(json.dumps(model.to_dict(), sort_keys=True,
                                                separators=(",", ":")).encode("utf-8"))
        seen_ids = set()
        for i, p in enumerate(P_VALUES):
            for root in range(10):
                guard(started)
                sample_id = f"eval:p{i}:r{root:02d}"
                if sample_id in seen_ids:
                    raise RuntimeError("duplicate evaluation sample identity")
                seen_ids.add(sample_id)
                seed = int(SEEDS[sample_id])
                p_hat = calibration["estimates"][i * 10 + root]["p_hat"]
                profile, profile_s, profile_circuit_sha, profile_dem_sha = decoder_for(
                    p_hat, "profile_estimated"
                )
                construct_seconds["profile_total"] += profile_s
                # The name passed to the matcher must equal the fixed paired-evaluator key.
                if profile.metadata.name != "profile_estimated":
                    raise RuntimeError("profile decoder metadata name mismatch")
                calls += 1
                if calls > 50:
                    raise RuntimeError("V1.1 recovery call ceiling exceeded")
                state["recovery_sampler_calls_started"] = calls
                state["cumulative_sampler_calls_started"] = 56 + calls
                state["cumulative_sampler_rows_started"] = 32000 + returned_rows + 2000
                atomic_json(RECOVERY / "status.json", state)
                detectors, labels, sample_s = sample(
                    circuits[i], 2000, seed
                )
                calls_completed += 1
                returned_rows += len(detectors)
                sampling_seconds += sample_s
                state["recovery_rows_returned"] = returned_rows
                state["cumulative_sampler_rows_returned"] = 32000 + returned_rows
                decoders = {
                    "pooled_fixed": CapturingDecoder(static),
                    "profile_estimated": CapturingDecoder(profile),
                    "oracle_true_p": CapturingDecoder(oracle[i]),
                    "nominal_no_burst": CapturingDecoder(no_burst),
                }
                paired = evaluate_paired(
                    detectors, labels, decoders, baseline_name="pooled_fixed",
                    scope="heldout-development", sample_id=sample_id,
                )
                decode_seconds += sum(float(x["elapsed_seconds"] or 0.0)
                                      for x in paired["records"].values())
                if any(d.last_bits is None for d in decoders.values()):
                    raise RuntimeError("a paired decoder returned no prediction")
                stem = f"eval_p{i}_r{root:02d}"
                archive = RECOVERY / f"{stem}.npz"
                marker_path = RECOVERY / f"{stem}.commit.json"
                if archive.exists() or marker_path.exists():
                    raise RuntimeError("duplicate root output exists; no overwrite")
                atomic_npz(
                    archive, detectors=detectors, observables=labels,
                    pred_pooled_fixed=decoders["pooled_fixed"].last_bits,
                    pred_profile_estimated=decoders["profile_estimated"].last_bits,
                    pred_oracle_true_p=decoders["oracle_true_p"].last_bits,
                    pred_nominal_no_burst=decoders["nominal_no_burst"].last_bits,
                )
                marker = {
                    "sample_id": sample_id, "p_index": i, "p_burst": p, "root": root,
                    "seed": seed, "shots": len(detectors), "archive_sha256": sha_file(archive),
                    "detector_sha256": sha_bytes(detectors.tobytes()),
                    "observable_sha256": sha_bytes(labels.tobytes()),
                    "estimator_sha256": estimator_hash, "p_hat": p_hat,
                    "p_global": calibration["p_global"],
                    "static_model": {"circuit_sha256": static_circuit_sha,
                                     "dem_sha256": static_dem_sha},
                    "profile_model": {"circuit_sha256": profile_circuit_sha,
                                      "dem_sha256": profile_dem_sha, "assumed_p": p_hat},
                    "oracle_dem_sha256": oracle_dem_hashes[str(p)],
                    "sample_identity_sha256": paired["sample_identity"]["evidence_sha256"],
                    "paired_records": paired["records"], "evaluation_sampling_seconds": sample_s,
                }
                atomic_json(marker_path, marker)
                state.update({
                    "committed_roots": len(seen_ids),
                    "committed_evaluation_rows": 2000 * len(seen_ids),
                    "verified_unique_total_rows": 30000 + 2000 * len(seen_ids),
                    "cumulative_sampler_calls_completed": 56 + calls_completed,
                    "cumulative_sampler_rows_returned": 32000 + returned_rows,
                    "status": "running",
                })
                atomic_json(RECOVERY / "status.json", state)
                guard(started)
        if len(seen_ids) != 50 or calls != 50 or returned_rows != 100000:
            raise RuntimeError("V1.1 recovery allocation/completeness mismatch")
        final = {
            **state, "status": "completed", "committed_roots": 50,
            "committed_evaluation_rows": 100000, "verified_unique_total_rows": 130000,
            "cumulative_unique_partition_count": 105,
            "cumulative_sampler_calls_completed": 106,
            "cumulative_sampler_rows_returned": 132000,
            "combined_wall_seconds": PRIOR_WALL + time.monotonic() - started,
            "recovery_wall_seconds": time.monotonic() - started,
            "peak_working_set_bytes": peak_working_set(),
            "artifact_bytes": artifact_bytes(),
            "evaluation_sampling_seconds": sampling_seconds,
            "evaluation_decoder_seconds": decode_seconds,
            "construction_seconds": construct_seconds,
            "unique_sample_ids": sorted(seen_ids),
            "statistical_interpretation": "V1 frozen development protocol; oracle excluded from primary comparison",
            "replay_limitation": "The failed eval:p0:r00 output was not archived. The exact same frozen seed, circuit and Stim version were replayed; byte equality to the lost transient output cannot be directly checked.",
        }
        if final["combined_wall_seconds"] > MAX_WALL or final["peak_working_set_bytes"] > MAX_RSS:
            raise RuntimeError("final whole-run resource limit exceeded")
        if final["artifact_bytes"] > MAX_ARTIFACTS:
            raise RuntimeError("artifact limit exceeded")
        atomic_json(RECOVERY / "status.json", final)
        return final
    except BaseException as exc:
        state.update({
            "status": "incomplete", "error_type": type(exc).__name__,
            "error_message": str(exc), "recovery_sampler_calls_started": calls,
            "recovery_rows_returned": returned_rows,
            "committed_roots": len(list(RECOVERY.glob("eval_p*_r*.commit.json"))),
            "committed_evaluation_rows": 2000 * len(list(RECOVERY.glob("eval_p*_r*.commit.json"))),
            "verified_unique_total_rows": 30000 + 2000 * len(list(RECOVERY.glob("eval_p*_r*.commit.json"))),
            "cumulative_sampler_calls_completed": 56 + calls_completed,
            "cumulative_sampler_rows_returned": 32000 + returned_rows,
            "recovery_wall_seconds": time.monotonic() - started,
            "peak_working_set_bytes": peak_working_set(),
        })
        atomic_json(RECOVERY / "status.json", state)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute-single-recovery", action="store_true")
    args = parser.parse_args()
    if not args.execute_single_recovery:
        raise SystemExit("production sampling is disabled without --execute-single-recovery")
    print(json.dumps(run(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
