"""One-shot execution path for the bounded Q-SHIFT development pilot."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np
import psutil
import pymatching
import stim

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(REPO / "outputs" / "phase3a_correlated_noise_preflight") not in sys.path:
    sys.path.insert(0, str(REPO / "outputs" / "phase3a_correlated_noise_preflight"))

from estimator import RidgeProfile
from simulator import build_spatial_burst_circuit
from qshift_core_v1.contracts import DecoderPrediction
from qshift_core_v1.evaluation import evaluate_paired
from qshift_core_v1.pymatching_adapter import PyMatchingDecoder

CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
SEEDS = json.loads((ROOT / "seed_inventory.json").read_text(encoding="utf-8"))["seeds"]
SAMPLES = ROOT / "samples"
MAX_WALL = CFG["resource_limits"]["wall_seconds"]
MAX_RSS = CFG["resource_limits"]["peak_process_working_set_bytes"]
MAX_DISK = CFG["resource_limits"]["artifact_bytes"]
MIN_FREE = CFG["resource_limits"]["minimum_free_disk_bytes"]


class CapturingDecoder:
    def __init__(self, decoder):
        self._decoder = decoder
        self.metadata = decoder.metadata
        self.last_bits = None

    def decode(self, detectors: np.ndarray) -> DecoderPrediction:
        result = self._decoder.decode(detectors)
        self.last_bits = np.array(result.bits, dtype=np.uint8, copy=True)
        return result


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def circuit_for(p: float) -> stim.Circuit:
    c = CFG["circuit"]
    return build_spatial_burst_circuit(
        memory_basis=c["memory_basis"], regime=c["pauli_regime"],
        distance=c["distance"], rounds=c["rounds"],
        gate_p=c["gate_probability"], measurement_p=c["measurement_probability"],
        bias_ratio=c["bias_ratio"], burst_probability=float(p),
        burst_pair=tuple(c["burst_pair"]),
    )


def decoder_for(p: float, name: str) -> tuple[PyMatchingDecoder, float, str, str]:
    started = time.perf_counter()
    circuit = circuit_for(float(p))
    c = CFG["circuit"]
    dem = circuit.detector_error_model(
        decompose_errors=c["dem"]["decompose_errors"],
        approximate_disjoint_errors=c["dem"]["approximate_disjoint_errors"],
    )
    if dem.num_detectors != c["expected_detectors"] or dem.num_observables != c["expected_observables"]:
        raise RuntimeError("DEM detector/observable dimensions differ from frozen configuration")
    dem_text = str(dem)
    circuit_text = str(circuit)
    dem_sha = sha_bytes(dem_text.encode("utf-8"))
    circuit_sha = sha_bytes(circuit_text.encode("utf-8"))
    model_id = f"spatial-burst-dem:{dem_sha}"
    decoder = PyMatchingDecoder.from_detector_error_model(
        dem,
        correlation_mode=bool(c["dem"]["pymatching_enable_correlations"]),
        name=name,
        noise_model_id=model_id,
    )
    return decoder, time.perf_counter() - started, circuit_sha, dem_sha


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def atomic_npz(path: Path, **arrays) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            np.savez_compressed(f, **arrays)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def measured_peak_working_set() -> int:
    info = psutil.Process().memory_info()
    peak = getattr(info, "peak_wset", None)
    if peak is None or int(peak) <= 0:
        raise RuntimeError("peak process working-set metric is unavailable")
    return int(peak)


def artifact_bytes() -> int:
    return sum(p.stat().st_size for p in SAMPLES.rglob("*") if p.is_file())


def check_resources(started: float) -> None:
    if time.monotonic() - started > MAX_WALL:
        raise RuntimeError("600-second wall-clock limit exceeded")
    if measured_peak_working_set() > MAX_RSS:
        raise RuntimeError("1-GiB peak process working-set limit exceeded")
    if shutil.disk_usage(ROOT).free < MIN_FREE:
        raise RuntimeError("minimum free-disk limit violated")
    if SAMPLES.exists() and artifact_bytes() > MAX_DISK:
        raise RuntimeError("128-MiB artifact limit exceeded")


def verify_frozen_sources() -> dict:
    manifest_path = ROOT / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    freeze = json.loads((ROOT / "PRETEST_FREEZE.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != "qshift-performance-source-freeze-v1":
        raise RuntimeError("unexpected source-freeze schema")
    if freeze.get("source_manifest_sha256") != sha_file(manifest_path):
        raise RuntimeError("pretest freeze does not bind the source manifest")
    if freeze.get("source_files") != manifest.get("files"):
        raise RuntimeError("pretest freeze and source manifest file inventories differ")
    for rel, expected in manifest["files"].items():
        p = REPO / rel
        if not p.is_file() or sha_file(p) != expected:
            raise RuntimeError(f"frozen source hash mismatch: {rel}")
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    ).stdout.strip()
    if dirty:
        raise RuntimeError("worktree is not clean; frozen source cannot be executed")
    return manifest


def sample(circuit: stim.Circuit, shots: int, seed: int, *, keep_labels: bool) -> tuple[np.ndarray, np.ndarray | None, float]:
    if seed <= 0 or seed > 2**31 - 1:
        raise ValueError("seed outside the frozen 31-bit positive range")
    started = time.perf_counter()
    sampler = circuit.compile_detector_sampler(seed=int(seed))
    detector, labels = sampler.sample(shots=int(shots), separate_observables=True)
    elapsed = time.perf_counter() - started
    detector = np.asarray(detector, dtype=np.uint8)
    if detector.shape != (shots, CFG["circuit"]["expected_detectors"]):
        raise RuntimeError(f"unexpected detector sample shape {detector.shape}")
    if not np.isin(detector, [0, 1]).all():
        raise RuntimeError("nonbinary detector sample")
    if keep_labels:
        labels = np.asarray(labels, dtype=np.uint8)
        if labels.shape != (shots, CFG["circuit"]["expected_observables"]):
            raise RuntimeError(f"unexpected observable sample shape {labels.shape}")
        return detector, labels, elapsed
    del labels
    return detector, None, elapsed


def git_identity() -> dict:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, text=True,
                            capture_output=True, check=True).stdout.strip()
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=REPO, text=True,
                            capture_output=True, check=True).stdout.strip()
    return {"commit": commit, "branch": branch}


def preflight() -> dict:
    result = {"sampler_calls": 0, "shots": 0, "conditions": []}
    fixture = np.zeros((3, CFG["circuit"]["expected_detectors"]), dtype=np.uint8)
    fixture[1, 0] = 1
    fixture[2, -1] = 1
    for p in CFG["circuit"]["burst_probabilities"]:
        circuit = circuit_for(p)
        dem = circuit.detector_error_model(
            decompose_errors=True, approximate_disjoint_errors=True
        )
        decoder, construct_s, circuit_sha, dem_sha = decoder_for(p, f"preflight_p{p}")
        pred = decoder.decode(fixture).bits
        if circuit.num_detectors != 40 or circuit.num_observables != 1:
            raise RuntimeError(f"circuit shape failure at p={p}")
        if dem.num_detectors != 40 or dem.num_observables != 1:
            raise RuntimeError(f"DEM shape failure at p={p}")
        if pred.shape != (3, 1) or not np.isin(pred, [0, 1]).all():
            raise RuntimeError(f"deterministic decode fixture failed at p={p}: {pred.shape}")
        result["conditions"].append({
            "p": p, "circuit_sha256": circuit_sha,
            "dem_sha256": dem_sha, "construction_seconds": construct_s,
            "detectors": int(dem.num_detectors), "observables": int(dem.num_observables),
            "matching_edges": int(decoder._matching.num_edges),
            "correlation_mode": decoder.metadata.correlation_mode,
            "fixture_predictions": pred.reshape(-1).tolist(),
        })
    return result


def run() -> None:
    started = time.monotonic()
    verify_frozen_sources()
    if SAMPLES.exists() and any(SAMPLES.iterdir()):
        raise RuntimeError("sample output already exists; no automatic resume or overwrite")
    if shutil.disk_usage(ROOT).free < MIN_FREE:
        raise RuntimeError("less than 1 GiB free disk")
    SAMPLES.mkdir(parents=True, exist_ok=False)
    call_count = 0
    shot_count = 0
    status = {"status": "running", "sampler_calls_started": 0, "completed_calls": 0,
              "shots_started": 0, "verified_shots_committed": 0, "roots_complete": 0}
    atomic_json(SAMPLES / "status.json", status)
    atomic_json(SAMPLES / "run_start.json", {
        "git": git_identity(), "source_manifest_sha256": sha_file(ROOT / "source_manifest.json"),
        "config_sha256": sha_file(ROOT / "config.json"),
        "seed_inventory_sha256": sha_file(ROOT / "seed_inventory.json"),
        "python": sys.version, "stim": stim.__version__, "pymatching": pymatching.__version__,
        "numpy": np.__version__, "peak_metric": "psutil memory_info().peak_wset",
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "allocation": CFG["allocation"],
    })

    def perform(circuit, n, seed, keep_labels, sample_id):
        nonlocal call_count, shot_count
        check_resources(started)
        if call_count >= CFG["allocation"]["max_sampler_calls"]:
            raise RuntimeError("sampler-call ceiling exceeded")
        if shot_count + int(n) > CFG["allocation"]["max_unique_shots"]:
            raise RuntimeError("shot ceiling exceeded")
        call_count += 1
        shot_count += int(n)
        status.update({"sampler_calls_started": call_count, "shots_started": shot_count})
        atomic_json(SAMPLES / "status.json", status)
        d, y, seconds = sample(circuit, n, seed, keep_labels=keep_labels)
        check_resources(started)
        return d, y, seconds

    try:
        probabilities = CFG["circuit"]["burst_probabilities"]
        circuits = {i: circuit_for(p) for i, p in enumerate(probabilities)}
        # Training target is the declared simulation parameter, never an observable label.
        train_rows, train_targets = [], []
        train_times = {}
        for i, p in enumerate(probabilities):
            x, _, elapsed = perform(circuits[i], CFG["allocation"]["training_shots_per_probability"],
                                    SEEDS[f"train:p{i}"], False, f"train:p{i}")
            train_rows.append(x)
            train_targets.append(np.full(len(x), p, dtype=np.float64))
            train_times[str(p)] = elapsed
        train_x = np.concatenate(train_rows)
        train_y = np.concatenate(train_targets)
        model = RidgeProfile.fit(train_x, train_y, alpha=CFG["estimator"]["alpha"],
                                 clip=tuple(CFG["estimator"]["clip"]))
        model_json = json.dumps(model.to_dict(), sort_keys=True, separators=(",", ":"))
        atomic_json(SAMPLES / "trained_estimator.json", model.to_dict())
        atomic_npz(SAMPLES / "training_detector_only.npz", detectors=train_x, p_targets=train_y)
        del train_rows, train_targets, train_x, train_y
        status.update({"completed_calls": call_count, "verified_shots_committed": shot_count})
        atomic_json(SAMPLES / "status.json", status)

        cal: dict[int, list[np.ndarray]] = {i: [] for i in range(len(probabilities))}
        cal_times: dict[str, float] = {}
        estimates = []
        for i, p in enumerate(probabilities):
            for root in range(CFG["allocation"]["roots_per_probability"]):
                key = f"cal:p{i}:r{root:02d}"
                x, _, elapsed = perform(circuits[i], CFG["allocation"]["calibration_shots_per_root"],
                                        SEEDS[key], False, key)
                cal[i].append(x)
                atomic_npz(SAMPLES / f"cal_p{i}_r{root:02d}.npz", detectors=x)
                phat = model.predict_mean(x)
                estimates.append({"p_index": i, "root": root, "p_hat": phat,
                                  "simulation_p_for_diagnostic_only": p, "seed_label": key})
                cal_times[key] = elapsed
                status.update({"completed_calls": call_count, "verified_shots_committed": shot_count})
                atomic_json(SAMPLES / "status.json", status)
                check_resources(started)
        p_global = model.predict_mean(np.concatenate([x for group in cal.values() for x in group]))
        atomic_json(ROOT / "calibration_estimates.json", {
            "estimator": model.to_dict(), "p_global": p_global,
            "estimates": estimates, "training_sampling_seconds_by_p": train_times,
            "calibration_sampling_seconds_by_seed": cal_times,
            "diagnostic_truth_use": "true p appears only in post-fit calibration diagnostics; it is not passed to any decoder",
        })

        static, static_construct_s, static_c_sha, static_dem_sha = decoder_for(p_global, "pooled_fixed")
        no_burst, no_burst_construct_s, _, _ = decoder_for(0.0, "nominal_no_burst")
        oracle = {}
        oracle_construct = {}
        oracle_hashes = {}
        for i, p in enumerate(probabilities):
            oracle[i], oracle_construct[str(p)], _, oracle_hashes[str(p)] = decoder_for(p, "oracle_true_p")

        estimator_hash = sha_bytes(model_json.encode("utf-8"))
        eval_sampling_seconds = 0.0
        eval_decode_seconds = 0.0
        profile_construction_total = 0.0
        for i, p in enumerate(probabilities):
            for root in range(CFG["allocation"]["roots_per_probability"]):
                key = f"eval:p{i}:r{root:02d}"
                p_hat = estimates[i * CFG["allocation"]["roots_per_probability"] + root]["p_hat"]
                profile, profile_construct_s, profile_c_sha, profile_dem_sha = decoder_for(
                    p_hat, f"profile_p{i}_r{root:02d}"
                )
                profile_construction_total += profile_construct_s
                detectors, labels, sample_s = perform(
                    circuits[i], CFG["allocation"]["evaluation_shots_per_root"],
                    SEEDS[key], True, key
                )
                eval_sampling_seconds += sample_s
                decoders = {
                    "pooled_fixed": CapturingDecoder(static),
                    "profile_estimated": CapturingDecoder(profile),
                    "oracle_true_p": CapturingDecoder(oracle[i]),
                    "nominal_no_burst": CapturingDecoder(no_burst),
                }
                paired = evaluate_paired(
                    detectors, labels, decoders, baseline_name="pooled_fixed",
                    scope="heldout-development", sample_id=key,
                )
                eval_decode_seconds += sum(
                    float(row["elapsed_seconds"] or 0.0) for row in paired["records"].values()
                )
                if any(dec.last_bits is None for dec in decoders.values()):
                    raise RuntimeError("a paired decoder returned no captured prediction")
                arr_path = SAMPLES / f"eval_p{i}_r{root:02d}.npz"
                atomic_npz(
                    arr_path, detectors=detectors, observables=labels,
                    pred_pooled_fixed=decoders["pooled_fixed"].last_bits,
                    pred_profile_estimated=decoders["profile_estimated"].last_bits,
                    pred_oracle_true_p=decoders["oracle_true_p"].last_bits,
                    pred_nominal_no_burst=decoders["nominal_no_burst"].last_bits,
                )
                marker = {
                    "sample_id": key, "p_index": i, "root": root, "shots": len(detectors),
                    "seed": SEEDS[key], "archive_sha256": sha_file(arr_path),
                    "detector_sha256": sha_bytes(detectors.tobytes()),
                    "observable_sha256": sha_bytes(labels.tobytes()),
                    "estimator_sha256": estimator_hash, "p_hat": p_hat, "p_global": p_global,
                    "static_model": {"circuit_sha256": static_c_sha, "dem_sha256": static_dem_sha,
                                     "construction_seconds": static_construct_s},
                    "profile_model": {"circuit_sha256": profile_c_sha, "dem_sha256": profile_dem_sha,
                                      "assumed_p": p_hat, "construction_seconds": profile_construct_s},
                    "oracle_dem_sha256": oracle_hashes[str(p)],
                    "no_burst_construction_seconds": no_burst_construct_s,
                    "paired_records": paired["records"],
                    "sample_identity_sha256": paired["sample_identity"]["evidence_sha256"],
                    "evaluation_sampling_seconds": sample_s,
                }
                atomic_json(SAMPLES / f"eval_p{i}_r{root:02d}.commit.json", marker)
                status.update({"completed_calls": call_count, "verified_shots_committed": shot_count,
                               "roots_complete": status["roots_complete"] + 1})
                atomic_json(SAMPLES / "status.json", status)
                check_resources(started)
        if call_count != CFG["allocation"]["sampler_calls"] or shot_count != CFG["allocation"]["total_unique_shots"]:
            raise RuntimeError(f"allocation mismatch calls={call_count}, shots={shot_count}")
        final = {
            **status, "status": "completed", "sampler_calls_started": call_count,
            "completed_calls": call_count, "shots_started": shot_count,
            "verified_shots_committed": shot_count, "roots_complete": status["roots_complete"],
            "wall_seconds": time.monotonic() - started,
            "peak_working_set_bytes": measured_peak_working_set(),
            "artifact_bytes": artifact_bytes(),
            "construction_seconds": {
                "pooled_fixed": static_construct_s, "no_burst": no_burst_construct_s,
                "oracle_by_p": oracle_construct, "profile_total": profile_construction_total,
            },
            "evaluation_sampling_seconds_total": eval_sampling_seconds,
            "evaluation_decoder_seconds_total": eval_decode_seconds,
            "training_estimator": model.to_dict(),
        }
        check_resources(started)
        if final["roots_complete"] != 50 or final["artifact_bytes"] > MAX_DISK:
            raise RuntimeError("final completeness or artifact-size check failed")
        atomic_json(SAMPLES / "status.json", final)
    except BaseException as exc:
        status.update({
            "status": "incomplete", "error_type": type(exc).__name__,
            "error_message": str(exc), "sampler_calls_started": call_count,
            "completed_calls": call_count, "shots_started": shot_count,
            "verified_shots_committed": shot_count, "roots_complete": status["roots_complete"],
            "wall_seconds": time.monotonic() - started,
            "peak_working_set_bytes": measured_peak_working_set(),
        })
        atomic_json(SAMPLES / "status.json", status)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--verify-freeze", action="store_true")
    mode.add_argument("--execute-development-pilot", action="store_true")
    args = parser.parse_args()
    if args.preflight:
        print(json.dumps(preflight(), indent=2, sort_keys=True))
    elif args.verify_freeze:
        manifest = verify_frozen_sources()
        print(json.dumps({"verified_files": len(manifest["files"]), "git": git_identity(),
                          "sampler_calls": 0, "shots": 0}, indent=2, sort_keys=True))
    else:
        run()
        print(json.dumps(json.loads((SAMPLES / "status.json").read_text()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()