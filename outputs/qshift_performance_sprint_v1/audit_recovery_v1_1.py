"""Independent saved-array reconstruction of the V1.1 development pilot."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pymatching

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
RECOVERY = ROOT / "samples" / "recovery_v1_1"
if str(REPO / "outputs" / "phase3a_correlated_noise_preflight") not in sys.path:
    sys.path.insert(0, str(REPO / "outputs" / "phase3a_correlated_noise_preflight"))
from simulator import build_spatial_burst_circuit

P_VALUES = (0.0, 0.004, 0.008, 0.012, 0.016)
ARMS = ("pooled_fixed", "profile_estimated", "oracle_true_p", "nominal_no_burst")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def independent_profile(train_x: np.ndarray, train_y: np.ndarray):
    x = np.asarray(train_x, dtype=np.float64)
    y = np.asarray(train_y, dtype=np.float64).reshape(-1)
    mean = x.mean(axis=0)
    scale = x.std(axis=0)
    scale[scale < 1e-12] = 1.0
    standardized = (x - mean) / scale
    target_mean = float(y.mean())
    weights = np.linalg.solve(standardized.T @ standardized + 10.0 * np.eye(x.shape[1]),
                              standardized.T @ (y - target_mean))
    def predict(rows):
        values = (np.asarray(rows, dtype=np.float64) - mean) / scale
        return np.clip(target_mean + values @ weights, 0.0, 0.016)
    return predict


def make_model(p: float):
    circuit = build_spatial_burst_circuit(
        memory_basis="z", regime="balanced", distance=3, rounds=5,
        gate_p=0.003, measurement_p=0.003, bias_ratio=10.0,
        burst_probability=float(p), burst_pair=(8, 10),
    )
    dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
    if dem.num_detectors != 40 or dem.num_observables != 1:
        raise AssertionError("reconstructed DEM has wrong detector/observable shape")
    return circuit, dem, pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)


def audit() -> dict:
    status = json.loads((RECOVERY / "status.json").read_text(encoding="utf-8"))
    if status.get("status") != "completed" or status.get("committed_roots") != 50:
        raise RuntimeError("cannot independently audit an incomplete recovery")
    seed_map = json.loads((ROOT / "seed_inventory.json").read_text(encoding="utf-8"))["seeds"]
    if len(set(seed_map.values())) != len(seed_map):
        raise RuntimeError("frozen seed inventory contains a collision")
    with np.load(ROOT / "samples" / "training_detector_only.npz", allow_pickle=False) as data:
        train_x = np.asarray(data["detectors"], dtype=np.uint8)
        train_y = np.asarray(data["p_targets"], dtype=np.float64)
    if train_x.shape != (5000, 40) or train_y.shape != (5000,):
        raise RuntimeError("training evidence shape mismatch")
    profile_estimator = independent_profile(train_x, train_y)
    p_hat = {}
    calibration_rows = []
    for i, p in enumerate(P_VALUES):
        for root in range(10):
            with np.load(ROOT / "samples" / f"cal_p{i}_r{root:02d}.npz", allow_pickle=False) as data:
                x = np.asarray(data["detectors"], dtype=np.uint8)
            if x.shape != (500, 40) or not np.isin(x, [0, 1]).all():
                raise RuntimeError("calibration evidence invalid")
            p_hat[(i, root)] = float(np.mean(profile_estimator(x)))
            calibration_rows.append(x)
    p_global = float(np.mean(profile_estimator(np.concatenate(calibration_rows, axis=0))))
    record = json.loads((ROOT / "calibration_estimates.json").read_text(encoding="utf-8"))
    calibration_delta = max(abs(p_global - float(record["p_global"])),
                            max(abs(p_hat[(r["p_index"], r["root"])] - float(r["p_hat"]))
                                for r in record["estimates"]))
    if calibration_delta > 1e-12:
        raise RuntimeError("independent estimator reconstruction does not match calibration record")

    _, _, fixed = make_model(p_global)
    _, _, nominal = make_model(0.0)
    oracle = {i: make_model(p)[2] for i, p in enumerate(P_VALUES)}
    roots = []
    archive_hashes = {}
    prediction_checks = 0
    exact_files = {p.name for p in RECOVERY.iterdir() if p.is_file()}
    expected_files = {"status.json", "run_start.json"}
    for i in range(5):
        for root in range(10):
            stem = f"eval_p{i}_r{root:02d}"
            sample_id = f"eval:p{i}:r{root:02d}"
            archive = RECOVERY / f"{stem}.npz"
            marker_path = RECOVERY / f"{stem}.commit.json"
            expected_files.update({archive.name, marker_path.name})
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
            if sha_file(archive) != marker.get("archive_sha256"):
                raise RuntimeError(f"archive hash mismatch: {stem}")
            if (marker.get("sample_id") != sample_id or marker.get("seed") != seed_map[sample_id]
                    or marker.get("p_index") != i or marker.get("root") != root
                    or marker.get("shots") != 2000):
                raise RuntimeError(f"root/sample identity mismatch: {stem}")
            with np.load(archive, allow_pickle=False) as data:
                detectors = np.asarray(data["detectors"], dtype=np.uint8)
                labels = np.asarray(data["observables"], dtype=np.uint8)
                saved = {arm: np.asarray(data[f"pred_{arm}"], dtype=np.uint8) for arm in ARMS}
            if detectors.shape != (2000, 40) or labels.shape != (2000, 1):
                raise RuntimeError(f"evaluation array shape mismatch: {stem}")
            if (not np.isin(detectors, [0, 1]).all() or not np.isin(labels, [0, 1]).all()
                    or any(a.shape != labels.shape or not np.isin(a, [0, 1]).all() for a in saved.values())):
                raise RuntimeError(f"nonbinary or misshaped array: {stem}")
            if sha(detectors.tobytes()) != marker.get("detector_sha256"):
                raise RuntimeError(f"detector bytes mismatch: {stem}")
            if sha(labels.tobytes()) != marker.get("observable_sha256"):
                raise RuntimeError(f"observable bytes mismatch: {stem}")
            profile_model = make_model(p_hat[(i, root)])[2]
            reconstructed = {
                "pooled_fixed": np.asarray(fixed.decode_batch(detectors, enable_correlations=True), dtype=np.uint8).reshape(-1, 1),
                "profile_estimated": np.asarray(profile_model.decode_batch(detectors, enable_correlations=True), dtype=np.uint8).reshape(-1, 1),
                "oracle_true_p": np.asarray(oracle[i].decode_batch(detectors, enable_correlations=True), dtype=np.uint8).reshape(-1, 1),
                "nominal_no_burst": np.asarray(nominal.decode_batch(detectors, enable_correlations=True), dtype=np.uint8).reshape(-1, 1),
            }
            for arm in ARMS:
                if not np.array_equal(reconstructed[arm], saved[arm]):
                    raise RuntimeError(f"saved prediction differs from independent reconstruction: {stem}/{arm}")
                prediction_checks += 1
            errors = {arm: int(np.count_nonzero(saved[arm] != labels)) for arm in ARMS}
            disagreements = int(np.count_nonzero(saved["profile_estimated"] != saved["pooled_fixed"]))
            roots.append({"p": P_VALUES[i], "root": root, "errors": errors,
                          "disagreements": disagreements,
                          "profile_only": int(np.count_nonzero((saved["profile_estimated"] != labels) & (saved["pooled_fixed"] == labels))),
                          "fixed_only": int(np.count_nonzero((saved["pooled_fixed"] != labels) & (saved["profile_estimated"] == labels)))})
            archive_hashes[stem] = marker["archive_sha256"]
    if exact_files != expected_files:
        raise RuntimeError(f"unexpected or missing recovery output files: {sorted(exact_files ^ expected_files)}")

    differences = []
    condition_results = {}
    for p in P_VALUES:
        rs = [r for r in roots if r["p"] == p]
        fixed_errors = sum(r["errors"]["pooled_fixed"] for r in rs)
        profile_errors = sum(r["errors"]["profile_estimated"] for r in rs)
        condition_results[str(p)] = {
            "fixed_errors": fixed_errors, "profile_errors": profile_errors,
            "fixed_ler": fixed_errors / 20000, "profile_ler": profile_errors / 20000,
            "paired_disagreements": sum(r["disagreements"] for r in rs),
            "profile_only_errors": sum(r["profile_only"] for r in rs),
            "fixed_only_errors": sum(r["fixed_only"] for r in rs),
            "root_differences": [(r["errors"]["profile_estimated"] - r["errors"]["pooled_fixed"]) / 2000 for r in rs],
        }
    for p in P_VALUES[1:]:
        differences.append(condition_results[str(p)]["root_differences"])
    difference_matrix = np.asarray(differences, dtype=np.float64)
    point = float(difference_matrix.mean())
    fixed_rate = float(np.mean([condition_results[str(p)]["fixed_ler"] for p in P_VALUES[1:]]))
    profile_rate = float(np.mean([condition_results[str(p)]["profile_ler"] for p in P_VALUES[1:]]))
    relative = None if fixed_rate == 0 else (fixed_rate - profile_rate) / fixed_rate

    # Independent implementation of the prespecified root-stratified percentile bootstrap.
    seeds = seed_map
    rng = np.random.default_rng(seeds["statistics:primary-bootstrap"])
    boot_conditions = []
    for condition in difference_matrix:
        index = rng.integers(0, len(condition), size=(100000, len(condition)))
        boot_conditions.append(condition[index].mean(axis=1))
    boot = np.mean(np.stack(boot_conditions), axis=0)
    ci = [float(np.quantile(boot, .025, method="linear")), float(np.quantile(boot, .975, method="linear"))]
    zero_rng = np.random.default_rng(seeds["statistics:zero-gate"])
    z = np.asarray([condition_results["0.0"]["root_differences"]])
    zi = zero_rng.integers(0, z.shape[1], size=(100000, z.shape[1]))
    zero_boot = z[0][zi].mean(axis=1)
    zero_bounds = [float(np.quantile(zero_boot, .05, method="linear")),
                   float(np.quantile(zero_boot, .95, method="linear"))]
    analysis = json.loads((ROOT / "analysis_v1_1.json").read_text(encoding="utf-8"))
    if (abs(point - analysis["primary"]["difference"]) > 1e-15
            or abs(ci[0] - analysis["primary"]["percentile_95_ci"][0]) > 1e-15
            or abs(ci[1] - analysis["primary"]["percentile_95_ci"][1]) > 1e-15
            or abs(zero_bounds[1] - analysis["zero_burst_no_harm"]["bootstrap_lower_upper_5_95"][1]) > 1e-15):
        raise RuntimeError("independent summary recomputation disagrees with primary analysis")
    report = {
        "schema": "qshift-performance-independent-recovery-audit-v1.1",
        "audit_status": "PASS", "sampler_calls": 0, "new_shots": 0,
        "reconstructed_roots": len(roots), "unique_evaluation_rows": 2000 * len(roots),
        "unique_total_rows": 130000, "prediction_reconstructions": prediction_checks,
        "calibration_max_abs_difference": calibration_delta,
        "primary_difference": point, "primary_percentile_95_ci": ci,
        "zero_gate_5_95": zero_bounds, "independent_condition_counts": condition_results,
        "archive_hashes": archive_hashes,
        "limitations": [
            "Saved-array/model reconstruction only; no independent Stim resampling was performed.",
            "The first failed eval:p0:r00 sampler return was not persisted. Recovery replayed its identical frozen seed/circuit/version; byte comparison to the lost transient array is impossible.",
            "The synthetic DEM uses the frozen decomposition and approximate-disjoint settings; this is not hardware validation.",
        ],
    }
    (ROOT / "independent_audit_v1_1.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))
