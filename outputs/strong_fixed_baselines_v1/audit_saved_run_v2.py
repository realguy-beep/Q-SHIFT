"""Independent audit of saved v1 arrays; does not import runner/core/report code."""
from __future__ import annotations

import argparse
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


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def json_read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def binary(a: np.ndarray, shape: tuple[int, ...] | None = None) -> np.ndarray:
    a = np.asarray(a)
    if shape is not None and a.shape != shape:
        raise ValueError(f"shape mismatch: {a.shape} != {shape}")
    if a.dtype.kind not in "bui" or not np.isin(a, (0, 1)).all():
        raise ValueError("non-binary stored data")
    return a.astype(np.uint8, copy=False)


def feature_matrix(detectors: np.ndarray) -> np.ndarray:
    d = binary(detectors)
    if d.ndim != 2 or d.shape[1] != 40:
        raise ValueError("detectors must have shape (shots,40)")
    pairs = np.stack([d[:, a] & d[:, b] for a, b in ((8, 10), (16, 18), (24, 26), (32, 34), (36, 38))], axis=1)
    return np.concatenate([d, pairs], axis=1).astype(np.float64)


class IndependentProfileFit:
    """Independent local implementation of the frozen profile estimator formula."""
    def __init__(self, batches: list[tuple[float, np.ndarray]], grid_step: float):
        grouped: dict[float, list[np.ndarray]] = {}
        all_features = []
        for p, d in batches:
            f = feature_matrix(d)
            if f.shape[0] < 2:
                raise ValueError("profile batch too small")
            grouped.setdefault(float(p), []).append(f)
            all_features.append(f)
        self.ps = np.asarray(sorted(grouped), dtype=np.float64)
        self.means = np.asarray([np.concatenate(grouped[p], axis=0).mean(axis=0) for p in self.ps])
        pooled = np.concatenate(all_features, axis=0)
        self.scales = np.sqrt(np.maximum(pooled.var(axis=0), 1e-6))
        self.grid_step = float(grid_step)

    def estimate(self, detectors: np.ndarray) -> float:
        f = feature_matrix(detectors)
        if f.shape[0] < 2:
            raise ValueError("calibration batch too small")
        observed = f.mean(axis=0)
        lo, hi = float(self.ps[0]), float(self.ps[-1])
        count = int(round((hi - lo) / self.grid_step)) + 1
        grid = np.linspace(lo, hi, max(2, count), dtype=np.float64)
        expected = np.column_stack([np.interp(grid, self.ps, self.means[:, j]) for j in range(self.means.shape[1])])
        scores = np.mean(((expected - observed[None, :]) / self.scales[None, :]) ** 2, axis=1)
        return float(grid[int(np.argmin(scores))])


def matcher_for(p: float, cfg: dict):
    c = cfg["circuit"]
    circuit = build_spatial_burst_circuit(
        memory_basis=c["memory_basis"], regime=c["regime"], distance=int(c["distance"]),
        rounds=int(c["rounds"]), gate_p=float(c["gate_p"]), measurement_p=float(c["measurement_p"]),
        bias_ratio=float(c["bias_ratio"]), burst_probability=float(p), burst_pair=tuple(c["burst_pair"]),
    )
    dem = circuit.detector_error_model(**{k: v for k, v in c["dem"].items() if k != "enable_correlations"})
    if (circuit.num_detectors, circuit.num_observables, dem.num_detectors, dem.num_observables) != (40, 1, 40, 1):
        raise ValueError("circuit/DEM dimensions differ from v1 freeze")
    matcher = pymatching.Matching.from_detector_error_model(dem, enable_correlations=bool(c["dem"]["enable_correlations"]))
    return matcher


def committed(path: Path, expected: dict) -> tuple[dict, dict, str]:
    marker_path = path.with_suffix(path.suffix + ".commit.json")
    if not (path.is_file() and marker_path.is_file()):
        raise ValueError(f"archive/commit marker missing: {path}")
    digest = sha256(path)
    marker = json_read(marker_path)
    if marker.get("sha256") != digest:
        raise ValueError(f"archive hash mismatch: {path}")
    with np.load(path, allow_pickle=False) as z:
        arrays = {k: z[k] for k in z.files}
    meta = json.loads(str(arrays.pop("metadata_json").item()))
    if marker.get("metadata") != meta:
        raise ValueError(f"marker/archive metadata disagreement: {path}")
    for k, v in expected.items():
        if meta.get(k) != v:
            raise ValueError(f"{path}: {k}={meta.get(k)!r}, expected {v!r}")
    return arrays, meta, digest


def stream(inv: dict, role: str, split: str, p: float | None = None, root: int | None = None) -> dict:
    matches = [s for s in inv["streams"] if s["role"] == role and s["split"] == split
               and s["root"] == root and (s["probability"] is None if p is None else float(s["probability"]) == float(p))]
    if len(matches) != 1:
        raise ValueError(f"seed identity ambiguous: {role}/{split}/{p}/{root}")
    return matches[0]


def path_for(run: Path, partition: str, p: float, root: int | None = None) -> Path:
    if partition == "templates":
        return run / "templates" / f"p_{p:.3f}.npz"
    return run / partition / f"p_{p:.3f}" / f"root_{root:03d}.npz"


def decode(matcher, d: np.ndarray) -> np.ndarray:
    out = np.asarray(matcher.decode_batch(d)).reshape(-1)
    return binary(out, (d.shape[0],))


def bootstrap_upper(values: np.ndarray, seed: int, reps: int) -> float:
    x = np.asarray(values, dtype=np.float64)
    rng = np.random.Generator(np.random.PCG64(int(seed)))
    b = np.empty(reps)
    for start in range(0, reps, 2000):
        n = min(2000, reps - start)
        idx = rng.integers(0, x.size, size=(n, x.size))
        b[start:start+n] = x[idx].mean(axis=1)
    return float(np.quantile(b, 0.95, method="linear"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", type=Path, default=HERE / "run")
    args = ap.parse_args()
    run = args.run_dir.resolve()
    cfg = json_read(HERE / "experiment_config.json")
    inv = json_read(HERE / "seed_inventory.json")
    freeze_path = HERE / "PRETEST_FREEZE_V14.json"
    freeze = json_read(freeze_path)
    status = json_read(run / "status.json")
    if status.get("status") != "sampling_completed" or status.get("sampling_complete") is not True:
        raise ValueError("runner status is not sampling_completed")
    if freeze.get("sampling_performed_at_freeze") is not False:
        raise ValueError("pretest freeze does not attest pre-sampling state")
    for rel, expected_hash in freeze["sha256"].items():
        if sha256(ROOT / rel) != expected_hash:
            raise ValueError(f"frozen file hash mismatch: {rel}")
    seeds = [int(s["seed"]) for s in inv["streams"]]
    if len(seeds) != len(set(seeds)) or inv.get("collisions"):
        raise ValueError("seed inventory uniqueness/collision failure")

    probs = list(map(float, cfg["circuit"]["probabilities"]))
    grid = list(map(float, cfg["decoders"]["static_candidate_grid"]))
    n_sel = int(cfg["partitions"]["selection_roots_per_condition"])
    n_val = int(cfg["partitions"]["validation_roots_per_condition"])
    n_eval = int(cfg["partitions"]["evaluation_roots_per_condition"])
    cal_n = int(cfg["decoders"]["calibration_shots_per_root"])
    score_n = int(cfg["decoders"]["evaluation_shots_per_root"])
    files: dict[str, str] = {}
    sampled_shots = 0

    template_batches = []
    for p in map(float, cfg["decoders"]["profile_template_probabilities"]):
        s = stream(inv, "profile_template", "templates", p, None)
        path = path_for(run, "templates", p)
        arrays, meta, digest = committed(path, {"partition": "templates", "probability": p, "root": None, "seed": int(s["seed"]), "shots": int(cfg["partitions"]["template_shots_per_probability"])})
        d = binary(arrays["detectors"], (int(meta["shots"]), 40))
        template_batches.append((p, d))
        sampled_shots += len(d)
        files[str(path.relative_to(run))] = digest
    estimator = IndependentProfileFit(template_batches, float(cfg["decoders"]["profile_grid_step"]))

    matcher_cache = {p: matcher_for(p, cfg) for p in set(grid + probs + [0.0])}

    def get_matcher(p: float):
        p = float(p)
        if p not in matcher_cache:
            matcher_cache[p] = matcher_for(p, cfg)
        return matcher_cache[p]
    selection_roots_by_p: dict[float, list[np.ndarray]] = {p: [] for p in probs}
    validation_roots_by_p: dict[float, list[np.ndarray]] = {p: [] for p in probs}
    selection_root_lers: dict[float, list[np.ndarray]] = {p: [] for p in probs}
    validation_root_lers: dict[float, list[np.ndarray]] = {p: [] for p in probs}
    recomputed_score_records: dict[str, list[dict]] = {"selection": [], "validation": []}

    for partition, n_roots, collection, ler_collection in (
        ("selection", n_sel, selection_roots_by_p, selection_root_lers),
        ("validation", n_val, validation_roots_by_p, validation_root_lers),
    ):
        for p in probs:
            for root in range(n_roots):
                eval_seed = stream(inv, "scoring", partition, p, root)
                base_path = path_for(run, partition, p, root)
                a, meta, digest = committed(base_path, {"partition": partition, "probability": p, "root": root, "seed": int(eval_seed["seed"]), "shots": score_n})
                d, o = binary(a["detectors"], (score_n, 40)), binary(a["observable"], (score_n,))
                pred_seed = eval_seed
                pred_path = path_for(run, partition + "_predictions", p, root)
                pr, pmeta, pdigest = committed(pred_path, {"partition": partition + "_predictions", "probability": p, "root": root, "seed": int(pred_seed["seed"]), "shots": score_n})
                cp = binary(pr["candidate_predictions"], (len(grid), score_n))
                if not np.array_equal(d, pr["detectors"]) or not np.array_equal(o, pr["observable"]):
                    raise ValueError(f"paired candidate evidence mismatch: {pred_path}")
                independently_decoded = np.stack([decode(get_matcher(q), d) for q in grid])
                if not np.array_equal(cp, independently_decoded):
                    raise ValueError(f"candidate predictions do not reproduce: {pred_path}")
                lers = np.mean(cp ^ o[None, :], axis=1)
                collection[p].append(cp)
                ler_collection[p].append(lers)
                recomputed_score_records[partition].append({
                    "partition": partition, "probability": p, "root": root,
                    "shots": score_n, "errors_by_grid": (cp ^ o[None, :]).sum(axis=1).astype(int).tolist()
                })
                sampled_shots += len(d) + cal_n
                files[str(base_path.relative_to(run))] = digest
                files[str(pred_path.relative_to(run))] = pdigest
                cal_seed = stream(inv, "calibration", partition, p, root)
                cal_path = path_for(run, partition + "_calibration", p, root)
                ca, _, cdigest = committed(cal_path, {"partition": partition + "_calibration", "probability": p, "root": root, "seed": int(cal_seed["seed"]), "shots": cal_n})
                binary(ca["detectors"], (cal_n, 40))
                files[str(cal_path.relative_to(run))] = cdigest

    for partition in ("selection", "validation"):
        recorded = json_read(run / f"{partition}_scores.json")
        if recorded.get("per_root") != recomputed_score_records[partition]:
            raise ValueError(f"saved {partition} aggregate input differs from independent reconstruction")

    # Independently reproduce the candidate selection and validation accept/fallback gate.
    p0 = probs[0]
    zero_ref = np.asarray([x[0] for x in selection_root_lers[p0]])
    p0_candidate = {q: np.asarray([x[i] for x in selection_root_lers[p0]]) for i, q in enumerate(grid)}
    nonzero = {p: {q: np.asarray([x[i] for x in selection_root_lers[p]]) for i, q in enumerate(grid)} for p in probs[1:]}
    diagnostics = {}
    eligible = []
    for i, q in enumerate(grid):
        harm = float(np.mean(p0_candidate[q] - zero_ref))
        obj = float(np.mean([nonzero[p][q].mean() for p in probs[1:]]))
        diagnostics[q] = {"p0_harm": harm, "nonzero_objective": obj}
        if harm <= float(cfg["decoders"]["static_zero_burst_mean_harm_limit"]):
            eligible.append((obj, q))
    candidate = min(eligible, key=lambda z: (z[0], z[1]))[1] if eligible else 0.0
    j = grid.index(candidate)
    val_diffs = validation_root_lers[p0]
    val_diffs = np.asarray([x[j] - x[0] for x in val_diffs])
    boot_seed = int(stream(inv, "bootstrap_validation", "validation_analysis")["seed"])
    val_upper = bootstrap_upper(val_diffs, boot_seed, int(cfg["statistics"]["bootstrap_replicates"]))
    safe_p = candidate if (candidate == 0.0 or val_upper <= float(cfg["decoders"]["validation_upper_bound_harm_limit"])) else 0.0
    selection_freeze = json_read(run / "BASELINE_SELECTION_FREEZE.json")
    if float(selection_freeze["selection_candidate_before_validation"]) != float(candidate):
        raise ValueError("selection candidate differs from saved pre-evaluation freeze")
    if float(selection_freeze["chosen_probability"]) != float(safe_p):
        raise ValueError("safety-static fallback/acceptance differs from independent reconstruction")
    if not np.isclose(float(selection_freeze["validation_one_sided_95_upper"]), val_upper, rtol=0, atol=1e-12):
        raise ValueError("validation upper bound does not reproduce")

    final_cal_batches = []
    final_cal_by_root = {}
    cal_files = []
    for p in probs:
        for root in range(n_eval):
            s = stream(inv, "calibration", "heldout_development", p, root)
            path = path_for(run, "heldout_development_calibration", p, root)
            a, meta, digest = committed(path, {"partition": "heldout_development_calibration", "probability": p, "root": root, "seed": int(s["seed"]), "shots": cal_n})
            d = binary(a["detectors"], (cal_n, 40))
            final_cal_batches.append((p, d))
            final_cal_by_root[(p, root)] = d
            cal_files.append({"probability": p, "root": root, "seed": int(s["seed"]), "path": str(path.relative_to(run)), "sha256": digest})
            files[str(path.relative_to(run))] = digest
            sampled_shots += len(d)
    pooled_fit = IndependentProfileFit(template_batches, float(cfg["decoders"]["profile_grid_step"]))
    all_cal = np.concatenate([d for _, d in final_cal_batches], axis=0)
    p_pool = pooled_fit.estimate(all_cal)
    pool_record = json_read(run / "POOLED_CALIBRATION_FREEZE.json")
    if not np.isclose(float(pool_record["estimated_p"]), p_pool, rtol=0, atol=1e-12):
        raise ValueError("pooled detector-only calibration does not reproduce")
    if pool_record.get("calibration_archives") != cal_files:
        raise ValueError("pooled calibration archive provenance differs from independently verified archives")
    eval_freeze = json_read(run / "FINAL_EVAL_SELECTION_FREEZE.json")
    if not eval_freeze.get("created_before_final_evaluation_sampling") or not np.isclose(float(eval_freeze["pooled_detector_static_p"]), p_pool, rtol=0, atol=1e-12):
        raise ValueError("final selection freeze fails pooled calibration/pre-sampling check")
    if eval_freeze.get("experiment_config_sha256") != sha256(HERE / "experiment_config.json"):
        raise ValueError("final evaluation freeze config hash mismatch")
    if eval_freeze.get("decoder_arm_order") != ["nominal_fixed", "pooled_detector_static", "safety_constrained_static", "adaptive_profile", "privileged_true_p"]:
        raise ValueError("decoder arm order differs from frozen contract")
    if eval_freeze.get("all_eval_calibration_archive_hashes") != cal_files:
        raise ValueError("final evaluation freeze calibration archive mapping mismatch")

    # Rebuild every matcher independently and verify each saved paired final prediction.
    result_rows = []
    prediction_order = ["nominal_fixed", "pooled_detector_static", "safety_constrained_static", "adaptive_profile", "privileged_true_p"]
    model_values = set([0.0, p_pool, safe_p, *probs])
    for p in probs:
        for root in range(n_eval):
            seed = stream(inv, "evaluation", "heldout_development", p, root)
            path = path_for(run, "evaluation", p, root)
            arrays, meta, digest = committed(path, {"partition": "evaluation", "probability": p, "root": root, "seed": int(seed["seed"]), "shots": score_n})
            d, o = binary(arrays["detectors"], (score_n, 40)), binary(arrays["observable"], (score_n,))
            preds = binary(arrays["predictions"], (5, score_n))
            p_hat = estimator.estimate(final_cal_by_root[(p, root)])
            if not np.isclose(float(meta["p_hat"]), p_hat, rtol=0, atol=1e-12):
                raise ValueError(f"calibration estimate mismatch for {path}")
            model_values.add(p_hat)
            expected = np.stack([
                decode(get_matcher(0.0), d),
                decode(get_matcher(p_pool), d),
                decode(get_matcher(safe_p), d),
                decode(get_matcher(p_hat), d),
                decode(get_matcher(p), d),
            ])
            if not np.array_equal(preds, expected):
                raise ValueError(f"independent prediction mismatch for {path}")
            residuals = preds ^ o[None, :]
            names = prediction_order
            row = {"condition_p": p, "root": root, "seed": int(seed["seed"]), "shots": score_n,
                   "p_hat": float(p_hat), "prediction_disagreements_vs_nominal": int(np.sum(preds != preds[0:1]))}
            for i, name in enumerate(names):
                row[f"{name}_errors"] = int(residuals[i].sum())
                row[f"{name}_ler"] = float(residuals[i].mean())
            for i, name in ((1, "pooled_detector_static"), (2, "safety_constrained_static"), (3, "adaptive_profile"), (4, "privileged_true_p")):
                row[f"{name}_only_errors"] = int(np.sum((residuals[i] == 1) & (residuals[0] == 0)))
                row[f"nominal_only_vs_{name}"] = int(np.sum((residuals[i] == 0) & (residuals[0] == 1)))
                row[f"{name}_prediction_disagreements"] = int(np.sum(preds[i] != preds[0]))
            result_rows.append(row)
            sampled_shots += len(d)
            files[str(path.relative_to(run))] = digest

    expected_shots = int(cfg["allocation"]["unique_shots"])
    if sampled_shots != expected_shots:
        raise ValueError(f"sampled unique shot accounting {sampled_shots} != frozen {expected_shots}")
    expected_eval = len(probs) * n_eval * score_n
    if sum(r["shots"] for r in result_rows) != expected_eval:
        raise ValueError("final held-out development shot total mismatch")
    if len(result_rows) != len(probs) * n_eval:
        raise ValueError("missing final evaluation roots")

    npz_paths = sorted(run.rglob("*.npz"))
    for path in npz_paths:
        marker = path.with_suffix(path.suffix + ".commit.json")
        if not marker.is_file():
            raise ValueError(f"uncommitted archive present: {path}")
        files[str(path.relative_to(run))] = sha256(path)
        files[str(marker.relative_to(run))] = sha256(marker)
    if len(npz_paths) != 1803:
        raise ValueError(f"expected 1,803 study archives (including redundant candidate prediction records), found {len(npz_paths)}")
    if any(p.suffix == ".tmp" for p in run.rglob("*")):
        raise ValueError("temporary write artifact remains in run directory")

    result = {
        "audit_status": "PASS",
        "study_classification": "development_feasibility_not_confirmatory",
        "sealed_test_access": False,
        "historical_stage5_modified": False,
        "total_unique_shots_verified": sampled_shots,
        "final_paired_evaluation_shots": expected_eval,
        "final_evaluation_roots": len(result_rows),
        "selection_roots_per_condition": n_sel,
        "validation_roots_per_condition": n_val,
        "safe_static_selection": {"candidate": candidate, "frozen": safe_p,
                                  "validation_one_sided_upper": val_upper,
                                  "diagnostics": {str(k): v for k, v in diagnostics.items()}},
        "pooled_detector_static_p": p_pool,
        "prediction_order": prediction_order,
        "per_root": result_rows,
        "pretest_freeze_path": freeze_path.name,
        "pretest_freeze_sha256": sha256(freeze_path),
        "archive_count": len(files),
        "archive_sha256": files,
        "independent_method": "separate audit implementation; direct Stim circuit/DEM/PyMatching rebuild, local profile-formula reproduction, per-shot stored-prediction recomputation",
        "independent_auditor_sha256": sha256(Path(__file__)),
    }
    out = run / "INDEPENDENT_AUDIT.json"
    out.write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"audit_status": "PASS", "total_unique_shots_verified": sampled_shots,
                      "final_paired_evaluation_shots": expected_eval, "root_count": len(result_rows),
                      "safe_static_probability": safe_p, "pooled_probability": p_pool,
                      "archive_count": len(files), "audit_path": str(out)}, indent=2))


if __name__ == "__main__":
    main()
