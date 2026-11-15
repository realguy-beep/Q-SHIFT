"""Detector-only identifiability and PyMatching decision-sensitivity diagnostics.

No sampling API is used. Evaluation NPZ files are opened only for their
detectors member; observable members are never requested or scored.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Iterable

import numpy as np
import pymatching
import stim

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
PHASE3A = REPO / "outputs" / "phase3a_correlated_noise_preflight"
if str(PHASE3A) not in sys.path:
    sys.path.insert(0, str(PHASE3A))
from simulator import build_spatial_burst_circuit

P_VALUES = (0.0, 0.004, 0.008, 0.012, 0.016)
PAIR_MAP = ((8, 10), (16, 18), (24, 26), (32, 34), (36, 38))
ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0, 1000.0)
T95_DF9 = 2.2621571627409915


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha_array(array: np.ndarray) -> str:
    """Hash canonical array metadata and bytes, without reading archive members not selected."""
    x = np.ascontiguousarray(array)
    header = json.dumps({"dtype": x.dtype.str, "shape": list(x.shape)},
                        sort_keys=True, separators=(",", ":")).encode("ascii")
    h = hashlib.sha256()
    h.update(header + b"\0" + x.tobytes(order="C"))
    return h.hexdigest()


def feature_matrix(detectors: np.ndarray, pairs: tuple[tuple[int, int], ...] = PAIR_MAP) -> np.ndarray:
    x = np.asarray(detectors)
    if x.ndim != 2 or x.shape[1] != 40 or not np.isin(x, [0, 1]).all():
        raise ValueError("detectors must be binary [shots,40]")
    cofire = np.column_stack([x[:, a] & x[:, b] for a, b in pairs]).astype(np.uint8)
    return np.column_stack([x.astype(np.uint8, copy=False), cofire])


class StandardizedRidge:
    def __init__(self, alpha: float):
        self.alpha = float(alpha)

    def fit(self, x: np.ndarray, y: np.ndarray) -> "StandardizedRidge":
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        if x.ndim != 2 or len(x) != len(y) or len(x) == 0:
            raise ValueError("invalid ridge training arrays")
        self.mean = x.mean(axis=0)
        self.scale = x.std(axis=0)
        self.scale[self.scale < 1e-12] = 1.0
        z = (x - self.mean) / self.scale
        self.intercept = float(y.mean())
        self.coef = np.linalg.solve(z.T @ z + self.alpha * np.eye(x.shape[1]),
                                    z.T @ (y - self.intercept))
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=np.float64)
        z = (x - self.mean) / self.scale
        return np.clip(self.intercept + z @ self.coef, 0.0, 0.016)


def cv_alpha(x: np.ndarray, y: np.ndarray) -> tuple[float, dict[str, float]]:
    """Choose alpha by fixed within-condition 5-fold held-out training rows only."""
    y = np.asarray(y, dtype=np.float64)
    fold = np.zeros(len(y), dtype=bool)
    for p in P_VALUES:
        ids = np.flatnonzero(y == p)
        if len(ids) != 1000:
            raise ValueError(f"expected 1,000 training targets at p={p}, got {len(ids)}")
        fold[ids[::5]] = True
    scores = {}
    for alpha in ALPHAS:
        errors = []
        for k in range(5):
            valid = np.zeros(len(y), dtype=bool)
            for p in P_VALUES:
                ids = np.flatnonzero(y == p)
                valid[ids[k::5]] = True
            model = StandardizedRidge(alpha).fit(x[~valid], y[~valid])
            errors.append((model.predict(x[valid]) - y[valid]) ** 2)
        scores[str(alpha)] = float(np.sqrt(np.concatenate(errors).mean()))
    selected = min(ALPHAS, key=lambda a: (scores[str(a)], a))
    return float(selected), scores


def cv_alpha_by_calibration_batch(x: np.ndarray, y: np.ndarray) -> tuple[float, dict[str, float]]:
    """Tune for batch-mean p estimation using held-out training rows only."""
    y = np.asarray(y, dtype=np.float64)
    groups = {p: np.flatnonzero(y == p) for p in P_VALUES}
    if any(len(index) != 1000 for index in groups.values()):
        raise ValueError("batch-level CV requires the frozen 1,000 training shots per p")
    scores = {}
    for alpha in ALPHAS:
        squared = []
        for fold in range(5):
            valid = np.concatenate([groups[p][fold::5] for p in P_VALUES])
            train_mask = np.ones(len(y), dtype=bool)
            train_mask[valid] = False
            model = StandardizedRidge(alpha).fit(x[train_mask], y[train_mask])
            for p in P_VALUES:
                held = groups[p][fold::5]
                estimate = float(model.predict(x[held]).mean())
                squared.append((estimate - p) ** 2)
        scores[str(alpha)] = float(np.sqrt(np.mean(squared)))
    selected = min(ALPHAS, key=lambda a: (scores[str(a)], a))
    return float(selected), scores


def root_ci(values: Iterable[float]) -> list[float]:
    values = np.asarray(list(values), dtype=np.float64)
    if values.shape != (10,):
        raise ValueError("root-level interval requires ten independent calibration roots")
    margin = T95_DF9 * float(values.std(ddof=1)) / np.sqrt(len(values))
    return [float(values.mean() - margin), float(values.mean() + margin)]


def load_development_inputs(sample_root: Path):
    with np.load(sample_root / "training_detector_only.npz", allow_pickle=False) as z:
        train_x = np.asarray(z["detectors"], dtype=np.uint8)
        train_y = np.asarray(z["p_targets"], dtype=np.float64)
    if train_x.shape != (5000, 40) or train_y.shape != (5000,):
        raise RuntimeError("training archive shape mismatch")
    cal = {}
    calibration_hashes = {}
    for i, p in enumerate(P_VALUES):
        for root in range(10):
            path = sample_root / f"cal_p{i}_r{root:02d}.npz"
            with np.load(path, allow_pickle=False) as z:
                x = np.asarray(z["detectors"], dtype=np.uint8)
            if x.shape != (500, 40) or not np.isin(x, [0, 1]).all():
                raise RuntimeError(f"bad calibration detector array {path.name}")
            cal[(i, root)] = x
            calibration_hashes[f"p_index_{i}_root_{root:02d}"] = sha_array(x)
    input_hashes = {
        "training_detectors": sha_array(train_x),
        "training_p_targets": sha_array(train_y),
        "calibration_detectors": calibration_hashes,
        "hash_definition": "SHA256(canonical JSON {dtype,shape} + NUL + C-order array bytes)",
    }
    return train_x, train_y, cal, input_hashes


def model_diagnostics(train_x: np.ndarray, train_y: np.ndarray,
                      cal: dict[tuple[int, int], np.ndarray]) -> dict:
    train = {"marginals_40": train_x.astype(np.float64),
             "marginals_plus_cofires_45": feature_matrix(train_x).astype(np.float64)}
    cal_features = {key: {name: (x.astype(np.float64) if name == "marginals_40"
                                 else feature_matrix(x).astype(np.float64))
                          for name in train}
                    for key, x in cal.items()}
    models = {}
    for name, x in train.items():
        alpha_cv, cv_scores = cv_alpha(x, train_y)
        alpha_batch_cv, batch_cv_scores = cv_alpha_by_calibration_batch(x, train_y)
        models[name] = {
            "alpha_10": StandardizedRidge(10.0).fit(x, train_y),
            "alpha_cv": StandardizedRidge(alpha_cv).fit(x, train_y),
            "alpha_batch_cv": StandardizedRidge(alpha_batch_cv).fit(x, train_y),
            "alpha_cv_selected": alpha_cv,
            "alpha_batch_cv_selected": alpha_batch_cv,
            "training_cv_rmse_by_alpha": cv_scores,
            "training_batch_cv_rmse_by_alpha": batch_cv_scores,
        }

    estimation = {}
    for name in train:
        estimation[name] = {}
        for method in ("alpha_10", "alpha_cv", "alpha_batch_cv"):
            model = models[name][method]
            for n in (50, 100, 250, 500):
                estimates = []
                for (i, root), batch in cal.items():
                    index = np.linspace(0, 499, n, dtype=np.int64)
                    estimates.append({"p_index": i, "root": root,
                                      "p_true": P_VALUES[i],
                                      "p_hat": float(model.predict(cal_features[(i, root)][name][index]).mean())})
                errors = np.asarray([v["p_hat"] - v["p_true"] for v in estimates])
                per_condition = {}
                for i, p in enumerate(P_VALUES):
                    vals = np.asarray([v["p_hat"] for v in estimates if v["p_index"] == i])
                    err = vals - p
                    per_condition[str(p)] = {
                        "mean_estimate": float(vals.mean()), "bias": float(err.mean()),
                        "mae": float(np.abs(err).mean()), "rmse": float(np.sqrt(np.mean(err ** 2))),
                        "root_level_95_ci_for_bias": root_ci(err),
                        "root_level_95_ci_for_mae": root_ci(np.abs(err)),
                        "root_level_95_ci_for_mean_estimate": root_ci(vals),
                    }
                estimation[name][f"{method}_n{n}"] = {
                    "calibration_batches": len(estimates), "rows_per_batch": n,
                    "overall_bias": float(errors.mean()),
                    "overall_mae": float(np.abs(errors).mean()),
                    "overall_rmse": float(np.sqrt(np.mean(errors ** 2))),
                    "per_condition": per_condition,
                }
        estimation[name]["training_cv"] = {
            "selected_alpha": models[name]["alpha_cv_selected"],
            "rmse_by_alpha": models[name]["training_cv_rmse_by_alpha"],
        }
        estimation[name]["training_batch_cv"] = {
            "selected_alpha": models[name]["alpha_batch_cv_selected"],
            "rmse_by_alpha": models[name]["training_batch_cv_rmse_by_alpha"],
        }

    # Root-level condition means for every original marginal and the five fixed cofires.
    feature_rows = {}
    for (i, root), x in cal.items():
        feature_rows[(i, root)] = feature_matrix(x).mean(axis=0)
    condition_sep = {}
    for feature_index, feature_name in enumerate(
        [f"D{d}_marginal" for d in range(40)] + [f"cofire_D{a}_D{b}" for a, b in PAIR_MAP]
    ):
        condition_sep[feature_name] = {}
        condition_vectors = {}
        for i, p in enumerate(P_VALUES):
            root_values = np.asarray([feature_rows[(i, r)][feature_index] for r in range(10)])
            condition_vectors[i] = root_values
            condition_sep[feature_name][str(p)] = {
                "mean_across_roots": float(root_values.mean()),
                "root_sd": float(root_values.std(ddof=1)),
                "root_level_95_ci": root_ci(root_values),
            }
        contrasts = {}
        for i in range(1, len(P_VALUES)):
            a = condition_vectors[0]
            b = condition_vectors[i]
            delta = float(b.mean() - a.mean())
            se = float(np.sqrt(a.var(ddof=1) / 10 + b.var(ddof=1) / 10))
            # Conservative df=9 critical value for the independent-root difference.
            contrasts[str(P_VALUES[i])] = {"difference_vs_p0": delta,
                                            "conservative_95_ci": [delta - T95_DF9 * se,
                                                                    delta + T95_DF9 * se]}
        condition_sep[feature_name]["contrasts_vs_p0"] = contrasts

    return {"feature_estimation": estimation, "feature_separation": condition_sep,
            "p_hat_models": models, "cal_feature_rows": feature_rows}


def build_circuit(p: float) -> stim.Circuit:
    return build_spatial_burst_circuit(memory_basis="z", regime="balanced", distance=3,
                                       rounds=5, gate_p=0.003, measurement_p=0.003,
                                       bias_ratio=10.0, burst_probability=float(p),
                                       burst_pair=(8, 10))


def build_matcher(p: float):
    circuit = build_circuit(p)
    dem = circuit.detector_error_model(decompose_errors=True, approximate_disjoint_errors=True)
    if dem.num_detectors != 40 or dem.num_observables != 1:
        raise RuntimeError("diagnostic DEM circuit identity mismatch")
    matcher = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
    return circuit, dem, matcher


def load_evaluation_detectors_only(path: Path) -> np.ndarray:
    """Read exactly the detector member from an evaluation archive."""
    with np.load(path, allow_pickle=False) as archive:
        detectors = np.asarray(archive["detectors"], dtype=np.uint8)
    if detectors.shape != (2000, 40) or not np.isin(detectors, [0, 1]).all():
        raise RuntimeError(f"invalid evaluation detector array {path.name}")
    return detectors


def edge_map(matcher) -> dict:
    out = {}
    for u, v, data in matcher.edges():
        key = (int(u), None) if v is None else tuple(sorted((int(u), int(v))))
        if key in out:
            raise RuntimeError(f"parallel matching edge requires explicit multigraph handling: {key}")
        out[key] = {"weight": float(data["weight"]),
                    "error_probability": float(data["error_probability"])}
    return out


def detector_signature_pairs() -> tuple[tuple[int, int], ...]:
    # Deterministic DEM construction only; explicitly no Stim sampler is invoked.
    _, dem, _ = build_matcher(0.01)
    found = []
    for line in str(dem).splitlines():
        if line.startswith("error(0.01) "):
            ids = tuple(int(x) for x in re.findall(r"D(\d+)", line))
            if len(ids) == 2:
                found.append(ids)
    if tuple(found) != PAIR_MAP:
        raise RuntimeError(f"detector burst signature drift: {found}")
    return tuple(found)


def decoder_diagnostics(sample_root: Path, p_global: float, p_hat: dict) -> dict:
    _, _, fixed = build_matcher(p_global)
    fixed_edges = edge_map(fixed)
    edge_comparison = {}
    detector_decisions = {}
    pair_weights = {}
    for i, p in enumerate(P_VALUES):
        _, dem_true, oracle = build_matcher(p)
        oracle_edges = edge_map(oracle)
        common = set(fixed_edges) & set(oracle_edges)
        added = set(oracle_edges) - set(fixed_edges)
        removed = set(fixed_edges) - set(oracle_edges)
        diffs = [abs(fixed_edges[e]["weight"] - oracle_edges[e]["weight"]) for e in common]
        edge_comparison[str(p)] = {
            "fixed_p": p_global, "true_p": p,
            "fixed_edge_count": len(fixed_edges), "true_p_edge_count": len(oracle_edges),
            "common_edge_count": len(common), "added_under_true_p": len(added),
            "removed_under_true_p": len(removed),
            "common_edges_with_changed_weight_gt_1e_9": sum(d > 1e-9 for d in diffs),
            "common_edge_weight_abs_delta_mean": float(np.mean(diffs)) if diffs else None,
            "common_edge_weight_abs_delta_max": float(np.max(diffs)) if diffs else None,
            "dem_burst_error_lines": [line for line in str(dem_true).splitlines()
                                       if re.match(rf"error\({p:g}\) D", line)],
        }
        pair_weights[str(p)] = {
            f"D{a}-D{b}": {
                "pooled_fixed_weight": fixed_edges.get((a, b), {}).get("weight"),
                "true_p_weight": oracle_edges.get((a, b), {}).get("weight"),
                "pooled_fixed_error_probability": fixed_edges.get((a, b), {}).get("error_probability"),
                "true_p_error_probability": oracle_edges.get((a, b), {}).get("error_probability"),
            } for a, b in PAIR_MAP
        }
        stats = {"shots": 0, "fixed_vs_true_p_disagreements": 0,
                 "fixed_vs_profile_disagreements": 0, "roots": []}
        detector_hasher = hashlib.sha256()
        for root in range(10):
            path = sample_root / "recovery_v1_1" / f"eval_p{i}_r{root:02d}.npz"
            # Only the detector member is requested. Observable labels are never read.
            detectors = load_evaluation_detectors_only(path)
            detector_hasher.update(detectors.tobytes(order="C"))
            pred_fixed = np.asarray(fixed.decode_batch(detectors, enable_correlations=True), dtype=np.uint8).reshape(-1)
            pred_true = np.asarray(oracle.decode_batch(detectors, enable_correlations=True), dtype=np.uint8).reshape(-1)
            p_profile = p_hat[(i, root)]
            _, _, profile = build_matcher(p_profile)
            pred_profile = np.asarray(profile.decode_batch(detectors, enable_correlations=True), dtype=np.uint8).reshape(-1)
            d_oracle = int(np.count_nonzero(pred_fixed != pred_true))
            d_profile = int(np.count_nonzero(pred_fixed != pred_profile))
            stats["shots"] += len(detectors)
            stats["fixed_vs_true_p_disagreements"] += d_oracle
            stats["fixed_vs_profile_disagreements"] += d_profile
            stats["roots"].append({"root": root, "shots": len(detectors),
                                   "fixed_vs_true_p_disagreements": d_oracle,
                                   "fixed_vs_profile_disagreements": d_profile})
        stats["fixed_vs_true_p_fraction"] = stats["fixed_vs_true_p_disagreements"] / stats["shots"]
        stats["fixed_vs_profile_fraction"] = stats["fixed_vs_profile_disagreements"] / stats["shots"]
        stats["detector_rows_sha256"] = detector_hasher.hexdigest()
        detector_decisions[str(p)] = stats
    return {"pooled_p": p_global, "edge_weight_comparisons": edge_comparison,
            "burst_signature_edge_weights": pair_weights,
            "detector_only_prediction_disagreement": detector_decisions,
            "evaluation_observable_members_loaded": False}


def run(sample_root: Path) -> dict:
    train_x, train_y, cal, input_hashes = load_development_inputs(sample_root)
    feature = model_diagnostics(train_x, train_y, cal)
    model40 = feature["p_hat_models"]["marginals_40"]["alpha_10"]
    p_global = float(model40.predict(np.concatenate(list(cal.values()), axis=0)).mean())
    p_hat = {(i, r): float(model40.predict(cal[(i, r)]).mean())
             for i in range(5) for r in range(10)}
    if abs(p_global - 0.008004311733110277) > 1e-10:
        raise RuntimeError("reconstructed frozen pooled p differs from completed pilot")
    pairs = detector_signature_pairs()
    decoded = decoder_diagnostics(sample_root, p_global, p_hat)
    result = {
        "schema": "qshift-decoder-sensitivity-diagnostic-v1.4",
        "source_commit": "3a3f1dd2a14769dea645045c2be4acc8c1ecf739",
        "partition_policy": "saved training/calibration arrays for estimator; evaluation arrays accessed only through detectors member",
        "p_values": list(P_VALUES), "detector_count": 40, "observable_count": 1,
        "pair_features": [list(p) for p in pairs],
        "feature_estimation": feature["feature_estimation"],
        "feature_separation": feature["feature_separation"],
        "decoder_sensitivity": decoded,
        "training_and_calibration_detector_array_hashes": input_hashes,
        "sampling_api_calls": 0,
        "evaluation_observable_members_loaded": False,
        "input_data_description": "local ignored V1.1 saved-array directory; no path persisted",
    }
    with (ROOT / "diagnostic_results_v1_4.json").open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-root", required=True, type=Path,
                        help="path to saved samples directory from the completed V1.1 development run")
    args = parser.parse_args()
    if not args.sample_root.is_dir():
        raise SystemExit("sample root not found")
    result = run(args.sample_root.resolve())
    print(json.dumps({"output": str(ROOT / "diagnostic_results_v1_4.json"),
                      "p_global": result["decoder_sensitivity"]["pooled_p"],
                      "sampling_api_calls": 0,
                      "evaluation_observable_members_loaded": False}, indent=2))


if __name__ == "__main__":
    main()
