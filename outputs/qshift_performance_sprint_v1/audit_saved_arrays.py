"""Independent saved-array audit; no Stim sampler calls."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
import pymatching

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO / "outputs" / "phase3a_correlated_noise_preflight"))
from simulator import build_spatial_burst_circuit

CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
P_VALUES = CFG["circuit"]["burst_probabilities"]
SAMPLES = ROOT / "samples"


def independently_fit_profile(x: np.ndarray, y: np.ndarray, alpha: float, lo: float, hi: float):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    mu = x.mean(axis=0)
    sigma = x.std(axis=0)
    sigma[sigma < 1e-12] = 1.0
    z = (x - mu) / sigma
    ym = float(y.mean())
    beta = np.linalg.solve(z.T @ z + alpha * np.eye(z.shape[1]), z.T @ (y - ym))
    def predict(a):
        return np.clip(ym + ((np.asarray(a, dtype=np.float64) - mu) / sigma) @ beta, lo, hi)
    return predict


def make_matching(p: float):
    c = CFG["circuit"]
    circuit = build_spatial_burst_circuit(
        memory_basis=c["memory_basis"], regime=c["pauli_regime"],
        distance=c["distance"], rounds=c["rounds"],
        gate_p=c["gate_probability"], measurement_p=c["measurement_probability"],
        bias_ratio=c["bias_ratio"], burst_probability=float(p),
        burst_pair=tuple(c["burst_pair"]),
    )
    dem = circuit.detector_error_model(
        decompose_errors=c["dem"]["decompose_errors"],
        approximate_disjoint_errors=c["dem"]["approximate_disjoint_errors"],
    )
    if dem.num_detectors != 40 or dem.num_observables != 1:
        raise AssertionError("independent audit DEM shape mismatch")
    return circuit, dem, pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def audit() -> dict:
    status = json.loads((SAMPLES / "status.json").read_text(encoding="utf-8"))
    if status.get("status") != "completed" or status.get("roots_complete") != 50:
        raise RuntimeError("refusing audit of incomplete run")
    with np.load(SAMPLES / "training_detector_only.npz", allow_pickle=False) as train:
        train_x = np.asarray(train["detectors"], dtype=np.uint8)
        train_y = np.asarray(train["p_targets"], dtype=np.float64)
    if train_x.shape != (5000, 40) or train_y.shape != (5000,):
        raise RuntimeError("training partition shape/count mismatch")
    estimator = independently_fit_profile(
        train_x, train_y, CFG["estimator"]["alpha"],
        *CFG["estimator"]["clip"],
    )
    calibration = {}
    p_hats = {}
    all_cal = []
    for i, p in enumerate(P_VALUES):
        for root in range(CFG["allocation"]["roots_per_probability"]):
            path = SAMPLES / f"cal_p{i}_r{root:02d}.npz"
            with np.load(path, allow_pickle=False) as d:
                x = np.asarray(d["detectors"], dtype=np.uint8)
            if x.shape != (500, 40) or not np.isin(x, [0, 1]).all():
                raise RuntimeError(f"calibration archive invalid p{i}/r{root}")
            p_hats[(i, root)] = float(np.mean(estimator(x)))
            all_cal.append(x)
    p_global = float(np.mean(estimator(np.concatenate(all_cal))))
    recorded = json.loads((ROOT / "calibration_estimates.json").read_text(encoding="utf-8"))
    estimate_error = max(abs(p_global - float(recorded["p_global"])),
                         max(abs(p_hats[(r["p_index"], r["root"])] - float(r["p_hat"]))
                             for r in recorded["estimates"]))
    if estimate_error > 1e-12:
        raise RuntimeError(f"independent calibration reconstruction mismatch {estimate_error}")

    static = make_matching(p_global)[2]
    no_burst = make_matching(0.0)[2]
    oracle = {i: make_matching(p)[2] for i, p in enumerate(P_VALUES)}
    roots_checked = 0
    total_shots = 0
    prediction_mismatches = []
    archive_hashes = {}
    for i, p in enumerate(P_VALUES):
        for root in range(CFG["allocation"]["roots_per_probability"]):
            stem = f"eval_p{i}_r{root:02d}"
            archive = SAMPLES / f"{stem}.npz"
            marker = json.loads((SAMPLES / f"{stem}.commit.json").read_text(encoding="utf-8"))
            if file_sha(archive) != marker.get("archive_sha256"):
                raise RuntimeError(f"archive hash mismatch {stem}")
            with np.load(archive, allow_pickle=False) as a:
                detectors = np.asarray(a["detectors"], dtype=np.uint8)
                labels = np.asarray(a["observables"], dtype=np.uint8)
                saved = {n: np.asarray(a[f"pred_{n}"], dtype=np.uint8) for n in (
                    "pooled_fixed", "profile_estimated", "oracle_true_p", "nominal_no_burst")}
            if detectors.shape != (2000, 40) or labels.shape != (2000, 1):
                raise RuntimeError(f"evaluation shape mismatch {stem}")
            constructed_profile = make_matching(p_hats[(i, root)])[2]
            fresh = {
                "pooled_fixed": np.asarray(static.decode_batch(detectors, enable_correlations=True), dtype=np.uint8).reshape(-1, 1),
                "profile_estimated": np.asarray(constructed_profile.decode_batch(detectors, enable_correlations=True), dtype=np.uint8).reshape(-1, 1),
                "oracle_true_p": np.asarray(oracle[i].decode_batch(detectors, enable_correlations=True), dtype=np.uint8).reshape(-1, 1),
                "nominal_no_burst": np.asarray(no_burst.decode_batch(detectors, enable_correlations=True), dtype=np.uint8).reshape(-1, 1),
            }
            for name in fresh:
                if not np.array_equal(fresh[name], saved[name]):
                    prediction_mismatches.append({"sample_id": stem, "arm": name})
            if marker.get("seed") <= 0 or marker.get("seed") > 2**31 - 1:
                raise RuntimeError(f"invalid seed identity {stem}")
            roots_checked += 1
            total_shots += len(detectors)
            archive_hashes[stem] = marker["archive_sha256"]
    if prediction_mismatches:
        raise RuntimeError(f"saved predictions differ on {len(prediction_mismatches)} root-arm pairs")
    report = {
        "schema": "qshift-performance-independent-saved-array-audit-v1",
        "status": "PASS",
        "sampler_calls": 0,
        "new_shots": 0,
        "roots_reconstructed": roots_checked,
        "evaluation_shots_reconstructed": total_shots,
        "training_rows": len(train_x),
        "calibration_rows": 5 * 10 * 500,
        "independent_estimator_max_abs_difference": estimate_error,
        "prediction_mismatches": 0,
        "archive_count": len(archive_hashes),
        "archive_sha256": archive_hashes,
        "limitation": "This is a saved-array/model reconstruction audit, not independent Stim re-sampling or confirmation of upstream source provenance.",
    }
    (ROOT / "independent_audit.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))