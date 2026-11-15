"""Independent verification of corrected predictions, aggregates, and pairing."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pymatching

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def independent_features(d: np.ndarray) -> np.ndarray:
    d = np.asarray(d)
    if d.ndim != 2 or d.shape[1] != 40 or not np.isin(d, (0, 1)).all():
        raise ValueError("invalid detector matrix")
    pair_bits = np.column_stack([d[:, a] & d[:, b] for a, b in ((8, 10), (16, 18), (24, 26), (32, 34), (36, 38))])
    return np.column_stack([d, pair_bits]).astype(np.float64)


def estimate_p_pool(run: Path, cfg: dict) -> float:
    profile_ps = list(map(float, cfg["decoders"]["profile_template_probabilities"]))
    grouped = []
    template_features = []
    for p in profile_ps:
        path = run / "templates" / f"p_{p:.3f}.npz"
        with np.load(path, allow_pickle=False) as z:
            d = z["detectors"]
        if d.shape != (20_000, 40):
            raise ValueError(f"template shape mismatch: {path}")
        f = independent_features(d)
        grouped.append(f)
        template_features.append((p, f))
    means = np.asarray([x.mean(axis=0) for x in grouped])
    scales = np.sqrt(np.maximum(np.concatenate(grouped, axis=0).var(axis=0), 1e-6))
    cal_parts = []
    for p in map(float, cfg["circuit"]["probabilities"]):
        for root in range(int(cfg["partitions"]["evaluation_roots_per_condition"])):
            path = run / "heldout_development_calibration" / f"p_{p:.3f}" / f"root_{root:03d}.npz"
            with np.load(path, allow_pickle=False) as z:
                d = z["detectors"]
            if d.shape != (2_000, 40):
                raise ValueError(f"calibration shape mismatch: {path}")
            cal_parts.append(d)
    calibration = np.concatenate(cal_parts, axis=0)
    observed = independent_features(calibration).mean(axis=0)
    lo, hi = profile_ps[0], profile_ps[-1]
    step = float(cfg["decoders"]["profile_grid_step"])
    grid = np.linspace(lo, hi, int(round((hi - lo) / step)) + 1, dtype=np.float64)
    expected = np.column_stack([np.interp(grid, profile_ps, means[:, j]) for j in range(means.shape[1])])
    scores = np.mean(((expected - observed[None, :]) / scales[None, :]) ** 2, axis=1)
    return float(grid[int(np.argmin(scores))])


def build_matcher(p: float, cfg: dict):
    c = cfg["circuit"]
    circuit = build_spatial_burst_circuit(
        memory_basis=c["memory_basis"], regime=c["regime"], distance=int(c["distance"]), rounds=int(c["rounds"]),
        gate_p=float(c["gate_p"]), measurement_p=float(c["measurement_p"]), bias_ratio=float(c["bias_ratio"]),
        burst_probability=float(p), burst_pair=tuple(c["burst_pair"]),
    )
    dem = circuit.detector_error_model(decompose_errors=c["dem"]["decompose_errors"],
                                      approximate_disjoint_errors=c["dem"]["approximate_disjoint_errors"])
    if (circuit.num_detectors, circuit.num_observables, dem.num_detectors, dem.num_observables) != (40, 1, 40, 1):
        raise ValueError("reconstructed circuit/DEM shape mismatch")
    return pymatching.Matching.from_detector_error_model(dem, enable_correlations=c["dem"]["enable_correlations"])


def bootstrap(diffs: dict[float, np.ndarray], seed: int, reps: int) -> np.ndarray:
    rng = np.random.Generator(np.random.PCG64(int(seed)))
    ps = sorted(diffs)
    out = np.empty(reps, dtype=np.float64)
    for start in range(0, reps, 2_000):
        n = min(2_000, reps - start)
        means = []
        for p in ps:
            x = np.asarray(diffs[p], dtype=np.float64)
            idx = rng.integers(0, len(x), size=(n, len(x)))
            means.append(x[idx].mean(axis=1))
        out[start:start+n] = np.mean(means, axis=0)
    return out


def main() -> None:
    run = HERE / "run_recovery_v5"
    freeze = json.loads((HERE / "POSTRUN_RECONSTRUCTION_FREEZE_V1.json").read_text(encoding="utf-8"))
    cfg = json.loads((HERE / "experiment_config.json").read_text(encoding="utf-8"))
    inv = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
    audit = json.loads((run / "INDEPENDENT_AUDIT.json").read_text(encoding="utf-8"))
    results = json.loads((HERE / "report_reconstruction_v1" / "RESULTS.json").read_text(encoding="utf-8"))
    if audit["audit_status"] != "PASS_WITH_PROTOCOL_DEVIATION_RECONSTRUCTION":
        raise ValueError("unexpected audit disposition")
    # Check the post-run reconstruction source hashes before trusting its result.
    for rel, expected in freeze["source_sha256"].items():
        if sha(HERE / rel) != expected:
            raise ValueError(f"postrun reconstruction source drift: {rel}")
    corrected_p = estimate_p_pool(run, cfg)
    if not np.isclose(corrected_p, float(audit["pooled_detector_static_p"]), rtol=0, atol=1e-12):
        raise ValueError("independent detector-only pooled-p estimate differs from audit")
    matcher = build_matcher(corrected_p, cfg)
    rows_by_key = {(float(r["condition_p"]), int(r["root"])): r for r in audit["per_root"]}
    if len(rows_by_key) != 600:
        raise ValueError("audit per-root coverage differs from 600")
    pair_names = {
        "adaptive_minus_pooled_static": ("adaptive_profile", "pooled_detector_static"),
        "adaptive_minus_nominal": ("adaptive_profile", "nominal_fixed"),
        "pooled_static_minus_nominal": ("pooled_detector_static", "nominal_fixed"),
    }
    by_condition = {}
    corrected_file_hashes = []
    pooled_disagreement_total = 0
    total_eval_shots = 0
    per_root_discordances = []
    for p in map(float, cfg["circuit"]["probabilities"]):
        pair_totals = {name: {"left_only_errors": 0, "right_only_errors": 0, "prediction_disagreements": 0}
                       for name in pair_names}
        for root in range(int(cfg["partitions"]["evaluation_roots_per_condition"])):
            eval_path = run / "evaluation" / f"p_{p:.3f}" / f"root_{root:03d}.npz"
            corrected_path = HERE / "postrun_reconstruction_v1" / "corrected_pooled_predictions" / f"p_{p:.3f}" / f"root_{root:03d}.npz"
            with np.load(eval_path, allow_pickle=False) as z:
                d, o, saved = z["detectors"], z["observable"], z["predictions"]
            with np.load(corrected_path, allow_pickle=False) as z:
                pooled = z["prediction"]
                meta = json.loads(str(z["metadata_json"].item()))
            if d.shape != (2_500, 40) or o.shape != (2_500,) or saved.shape != (5, 2_500) or pooled.shape != (2_500,):
                raise ValueError(f"evaluation dimensions mismatch at p={p} root={root}")
            eval_hash = sha(eval_path)
            if meta.get("evaluation_archive_sha256") != eval_hash or float(meta.get("reconstructed_pooled_p")) != corrected_p:
                raise ValueError(f"corrected prediction provenance mismatch at p={p} root={root}")
            expected = np.asarray(matcher.decode_batch(d)).reshape(-1).astype(np.uint8)
            if not np.array_equal(pooled, expected):
                raise ValueError(f"corrected pooled prediction mismatch at p={p} root={root}")
            corrected_file_hashes.append({"path": str(corrected_path.relative_to(HERE)), "sha256": sha(corrected_path)})
            pooled_disagreement_total += int(np.sum(saved[1] != pooled))
            row = rows_by_key[(p, root)]
            shot_arm = {
                "adaptive_profile": saved[3].astype(bool),
                "pooled_detector_static": pooled.astype(bool),
                "nominal_fixed": saved[0].astype(bool),
            }
            shot_err = {k: np.logical_xor(v, o.astype(bool)) for k, v in shot_arm.items()}
            root_entry = {"condition_p": p, "root": root, "paired_shots": int(len(o))}
            for name, (left, right) in pair_names.items():
                le, re = shot_err[left], shot_err[right]
                lo = int(np.sum(le & ~re))
                ro = int(np.sum(re & ~le))
                pd = int(np.sum(shot_arm[left] != shot_arm[right]))
                pair_totals[name]["left_only_errors"] += lo
                pair_totals[name]["right_only_errors"] += ro
                pair_totals[name]["prediction_disagreements"] += pd
                root_entry[name] = {"left_only_errors": lo, "right_only_errors": ro,
                                    "prediction_disagreements": pd,
                                    "net_left_minus_right_errors": lo - ro}
            per_root_discordances.append(root_entry)
            total_eval_shots += len(o)
            # Check stored aggregate errors against direct shot-level recomputation.
            for arm, pred in shot_arm.items():
                if int(shot_err[arm].sum()) != int(row[f"{arm}_errors"]):
                    raise ValueError(f"per-root LER audit mismatch: p={p}, root={root}, arm={arm}")
        by_condition[str(p)] = pair_totals
    if total_eval_shots != 1_500_000 or len(corrected_file_hashes) != 600:
        raise ValueError("corrected prediction/evaluation coverage mismatch")

    # Independently verify saved aggregate counts, primary root bootstrap and p=0 bound.
    per_condition = {float(x["condition_p"]): x for x in results["per_condition"]}
    aggregate_counts = {}
    for p, row in per_condition.items():
        local = [x for x in audit["per_root"] if float(x["condition_p"]) == p]
        for arm in ("nominal_fixed", "pooled_detector_static", "safety_constrained_static", "adaptive_profile", "privileged_true_p"):
            errors = sum(int(x[f"{arm}_errors"]) for x in local)
            if errors != int(row[f"{arm}_errors"]):
                raise ValueError(f"aggregate count mismatch for {arm}, p={p}")
        aggregate_counts[str(p)] = {arm: int(row[f"{arm}_errors"]) for arm in
            ("nominal_fixed", "pooled_detector_static", "safety_constrained_static", "adaptive_profile", "privileged_true_p")}
    nonzero = list(map(float, cfg["circuit"]["probabilities"]))[1:]
    diff = {p: np.asarray([r["adaptive_profile_ler"] - r["safety_constrained_static_ler"]
                           for r in audit["per_root"] if float(r["condition_p"]) == p]) for p in nonzero}
    analysis_seed = next(int(x["seed"]) for x in inv["streams"] if x["role"] == "bootstrap_results")
    reps = int(cfg["statistics"]["bootstrap_replicates"])
    boots = bootstrap(diff, analysis_seed, reps)
    primary = results["primary_descriptive_contrast"]
    primary_est = float(np.mean([diff[p].mean() for p in sorted(diff)]))
    ci = [float(np.quantile(boots, .025)), float(np.quantile(boots, .975))]
    if not np.isclose(primary_est, primary["equal_condition_mean"], rtol=0, atol=1e-15) or not np.allclose(ci, primary["percentile_95_ci"], rtol=0, atol=1e-15):
        raise ValueError("independent primary bootstrap does not reproduce saved result")
    p0 = [r for r in audit["per_root"] if float(r["condition_p"]) == 0.0]
    # In the frozen analyzer's insertion order, the adaptive arm uses the
    # second zero-harm bootstrap seed (base + 1) after safety-static.
    zero_seed = analysis_seed + 1
    rng = np.random.Generator(np.random.PCG64(zero_seed))
    x = np.asarray([r["adaptive_profile_ler"] - r["nominal_fixed_ler"] for r in p0], dtype=np.float64)
    zero_boot = np.empty(reps)
    for start in range(0, reps, 2_000):
        n = min(2_000, reps - start)
        idx = rng.integers(0, len(x), size=(n, len(x)))
        zero_boot[start:start+n] = x[idx].mean(axis=1)
    zero_upper = float(np.quantile(zero_boot, .95))
    saved_zero_upper = results["zero_burst_safety"]["adaptive_profile"]["one_sided_95_upper"]
    if not np.isclose(zero_upper, saved_zero_upper, rtol=0, atol=1e-15):
        raise ValueError("independent zero-burst bootstrap does not reproduce")

    out = {
        "audit_status": "PASS",
        "classification": "independent read-only numerical verification of postrun reconstruction; not confirmatory",
        "postrun_freeze_sha256": sha(HERE / "POSTRUN_RECONSTRUCTION_FREEZE_V1.json"),
        "audit_input_sha256": sha(run / "INDEPENDENT_AUDIT.json"),
        "results_input_sha256": sha(HERE / "report_reconstruction_v1" / "RESULTS.json"),
        "corrected_prediction_count": len(corrected_file_hashes),
        "corrected_prediction_values_verified": 1_500_000,
        "corrected_prediction_file_hashes": corrected_file_hashes,
        "corrected_pooled_p_independently_recomputed": corrected_p,
        "legacy_pooled_vs_corrected_prediction_disagreements": pooled_disagreement_total,
        "final_paired_evaluation_shots": total_eval_shots,
        "per_condition_aggregate_error_counts": aggregate_counts,
        "shot_level_paired_discordance_by_condition": by_condition,
        "per_root_paired_discordance": per_root_discordances,
        "primary_adaptive_minus_safe_static": {"estimate": primary_est, "percentile_95_ci": ci, "resamples": reps},
        "adaptive_zero_burst_one_sided_95_upper": zero_upper,
        "sealed_test_access": False,
        "stage5_files_accessed": False,
        "independent_verifier_sha256": sha(Path(__file__)),
    }
    out_path = HERE / "POSTRUN_RECONSTRUCTION_VERIFICATION_V1.json"
    out_path.write_text(json.dumps(out, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": out["audit_status"], "corrected_predictions": len(corrected_file_hashes),
                      "paired_shots": total_eval_shots, "primary": out["primary_adaptive_minus_safe_static"],
                      "p0_adaptive_upper": zero_upper, "legacy_pool_disagreements": pooled_disagreement_total,
                      "output": str(out_path)}, indent=2))


if __name__ == "__main__":
    main()
