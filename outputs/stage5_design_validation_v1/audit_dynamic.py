"""Independent, root-count-configurable audit for normalized Stage 5 archives.

This does not import the Stage 5 runner or its reporting functions. It is
validated against the disposable 10-root benchmark and 256-root cardinality
fixtures; no Stage 5 run directory is read.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pymatching

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit
from integrity import verify_preexecution_freeze

STAGE5_PROFILE = ROOT / "outputs/stage5_preexecution_v1/FROZEN_PROFILE_ESTIMATOR.json"
PAIR_FEATURES = ((8, 10), (16, 18), (24, 26), (32, 34), (36, 38))


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def expected_root_keys(probabilities, roots_per_probability):
    return [(float(p), r) for p in probabilities for r in range(int(roots_per_probability))]


def expected_totals(config):
    roots = len(config["probabilities"]) * int(config["roots_per_probability"])
    cal = roots * int(config["calibration_shots_per_root"])
    ev = roots * int(config["paired_evaluation_shots_per_root"])
    return {"roots": roots, "calibration_shots": cal, "evaluation_shots": ev,
            "unique_shots": cal + ev}


def feature_matrix(detectors: np.ndarray) -> np.ndarray:
    d = np.asarray(detectors)
    if d.ndim != 2 or d.shape[1] != 40 or not np.isin(d, (0, 1)).all():
        raise ValueError("invalid 40-detector array")
    pairs = np.column_stack([d[:, a] & d[:, b] for a, b in PAIR_FEATURES])
    return np.column_stack([d, pairs]).astype(float)


def estimate_probability(detectors: np.ndarray, profile: dict) -> float:
    # Independent duplicate of the specified detector-only profile estimator.
    observed = feature_matrix(detectors).mean(axis=0)
    knots = np.asarray(profile["probabilities"], float)
    means = np.asarray(profile["means"], float)
    scales = np.asarray(profile["scales"], float)
    step = float(profile.get("grid_step", .00001))
    count = round((knots[-1] - knots[0]) / step) + 1
    grid = np.linspace(knots[0], knots[-1], max(2, int(count)))
    interp = np.column_stack([np.interp(grid, knots, means[:, j]) for j in range(45)])
    scores = np.square((interp - observed) / scales).mean(axis=1)
    return float(grid[np.argmin(scores)])


def matcher(probability: float, config: dict):
    circuit_cfg = config["circuit"]
    circuit = build_spatial_burst_circuit(
        memory_basis=circuit_cfg.get("memory_basis", "z"),
        regime="balanced", distance=int(circuit_cfg["distance"]), rounds=int(circuit_cfg["rounds"]),
        gate_p=float(circuit_cfg["gate_p"]), measurement_p=float(circuit_cfg["measurement_p"]),
        bias_ratio=float(circuit_cfg["bias_ratio"]), burst_probability=float(probability),
        burst_pair=tuple(circuit_cfg["burst_pair"]),
    )
    if (circuit.num_detectors, circuit.num_observables) != (40, 1):
        raise ValueError("reconstructed circuit dimensions mismatch")
    dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
    if (dem.num_detectors, dem.num_observables) != (40, 1):
        raise ValueError("reconstructed DEM dimensions mismatch")
    return pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)


def decode(matcher_obj, det):
    out = np.asarray(matcher_obj.decode_batch(np.asarray(det, dtype=np.uint8)), dtype=np.uint8).reshape(-1)
    if out.shape != (len(det),) or not np.isin(out, (0, 1)).all():
        raise ValueError("reconstructed prediction invalid")
    return out


def audit(run_dir: Path, config_path: Path, inventory_path: Path) -> dict:
    verify_preexecution_freeze()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    probs = [float(p) for p in config["probabilities"]]
    roots = int(config["roots_per_probability"])
    expected = expected_root_keys(probs, roots)
    total = expected_totals(config)
    seed_map = {}
    for row in inventory["benchmark_streams"]:
        key = (row["kind"], float(row["probability"]), int(row["root"]))
        if key in seed_map:
            raise ValueError(f"duplicate seed stream key: {key}")
        seed_map[key] = int(row["seed"])
    expected_streams = {(k, p, r) for k in ("calibration_detector_only", "paired_evaluation_detector_observable")
                        for p, r in expected}
    if set(seed_map) != expected_streams or len(set(seed_map.values())) != len(seed_map):
        raise ValueError("seed inventory does not exactly match dynamic root allocation")
    profile = json.loads(STAGE5_PROFILE.read_text(encoding="utf-8"))
    fixed = matcher(0.0, config)
    oracle = {p: matcher(p, config) for p in probs}
    root_dir = Path(run_dir) / "roots"
    files = sorted(root_dir.glob("root_p*.npz"))
    expected_names = {f"root_p{p:.3f}_r{r:03d}.npz" for p, r in expected}
    if {f.name for f in files} != expected_names:
        missing = sorted(expected_names - {f.name for f in files})
        extra = sorted({f.name for f in files} - expected_names)
        raise ValueError(f"root archive coverage mismatch; missing={len(missing)}, extra={len(extra)}")
    ncal = int(config["calibration_shots_per_root"])
    nev = int(config["paired_evaluation_shots_per_root"])
    root_rows, hashes = [], {}
    for p, r in expected:
        path = root_dir / f"root_p{p:.3f}_r{r:03d}.npz"
        hashes[path.name] = sha(path)
        with np.load(path, allow_pickle=False) as z:
            required = {"phase", "calibration_detectors", "evaluation_detectors", "observables", "predictions",
                        "p_hat", "probability", "root", "seed_calibration", "seed_evaluation"}
            if set(z.files) != required or str(np.asarray(z["phase"]).item()) != "complete":
                raise ValueError(f"schema/phase mismatch: {path.name}")
            cal = np.asarray(z["calibration_detectors"])
            det = np.asarray(z["evaluation_detectors"])
            obs = np.asarray(z["observables"])
            pred = np.asarray(z["predictions"])
            if cal.shape != (ncal, 40) or det.shape != (nev, 40) or obs.shape != (nev,) or pred.shape != (3, nev):
                raise ValueError(f"shape mismatch: {path.name}")
            if any(not np.isin(x, (0, 1)).all() for x in (cal, det, obs, pred)):
                raise ValueError(f"nonbinary data: {path.name}")
            if float(np.asarray(z["probability"]).item()) != p or int(np.asarray(z["root"]).item()) != r:
                raise ValueError(f"root/probability identity mismatch: {path.name}")
            if int(np.asarray(z["seed_calibration"]).item()) != seed_map[("calibration_detector_only", p, r)]:
                raise ValueError(f"calibration seed mismatch: {path.name}")
            if int(np.asarray(z["seed_evaluation"]).item()) != seed_map[("paired_evaluation_detector_observable", p, r)]:
                raise ValueError(f"evaluation seed mismatch: {path.name}")
            p_hat = estimate_probability(cal, profile)
            if not math.isclose(p_hat, float(np.asarray(z["p_hat"]).item()), rel_tol=0, abs_tol=1e-12):
                raise ValueError(f"detector-only estimate mismatch: {path.name}")
            adaptive = matcher(p_hat, config)
            regenerated = np.stack([decode(fixed, det), decode(adaptive, det), decode(oracle[p], det)])
            if not np.array_equal(regenerated, pred):
                raise ValueError(f"independent decoder re-score mismatch: {path.name}")
            errors = np.count_nonzero(regenerated ^ obs[None, :], axis=1).astype(int)
            root_rows.append({"probability": p, "root": r, "shots": nev,
                "fixed_errors": int(errors[0]), "adaptive_errors": int(errors[1]),
                "oracle_errors": int(errors[2]),
                "adaptive_only_wrong": int(np.count_nonzero((regenerated[1] != obs) & (regenerated[0] == obs))),
                "fixed_only_wrong": int(np.count_nonzero((regenerated[1] == obs) & (regenerated[0] != obs))),
                "prediction_disagreements": int(np.count_nonzero(regenerated[1] != regenerated[0]))})
    manifest = json.loads((Path(run_dir) / "ROOT_ARCHIVE_MANIFEST.json").read_text(encoding="utf-8"))
    if manifest.get("root_count") != total["roots"] or manifest.get("sha256") != hashes:
        raise ValueError("root archive manifest does not match independent hashes")
    status = json.loads((Path(run_dir) / "BENCHMARK_STATUS.json").read_text(encoding="utf-8"))
    if status.get("status") not in {"benchmark_completed", "completed"} or status.get("completed_roots") != total["roots"] or status.get("unique_shots_generated") != total["unique_shots"]:
        raise ValueError("persisted totals do not match dynamic allocation")
    return {"audit": "PASS", "roots_verified": total["roots"], "calibration_shots": total["calibration_shots"],
            "evaluation_shots": total["evaluation_shots"], "unique_shots": total["unique_shots"],
            "independent_test_access": 0, "stage5_sampling": False,
            "root_rows": root_rows, "archive_sha256": hashes,
            "audit_note": "Independent re-decoding implemented from normalized config; not imported from benchmark runner or Stage 5 runner."}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--config", type=Path, default=HERE / "BENCHMARK_CONFIG.json")
    parser.add_argument("--inventory", type=Path, default=HERE / "VALIDATION_SEED_INVENTORY.json")
    parser.add_argument("--output", type=Path, default=HERE / "benchmark_run/BENCHMARK_AUDIT.json")
    args = parser.parse_args()
    result = audit(args.run_dir, args.config, args.inventory)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: independently re-decoded {result['roots_verified']} roots / {result['unique_shots']} shots")
