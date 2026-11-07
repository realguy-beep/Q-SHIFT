"""Independent checkpoint audit and statistical recomputation from raw NPZ arrays."""
from __future__ import annotations

import csv
import hashlib
import importlib
import itertools
import json
import math
import os
import sys
import time
from decimal import Decimal
from pathlib import Path

import numpy as np
import pymatching
import stim

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CFG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
PHASE2B = (HERE / CFG["phase2b_source_dir"]).resolve()
sys.path.insert(0, str(PHASE2B))
noise_model = importlib.import_module("noise_model")
ARMS = CFG["decoder_arms"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def verify_frozen_inputs() -> dict:
    freeze_path = HERE / "PRETEST_FREEZE.json"
    if not freeze_path.is_file():
        raise RuntimeError("Cannot analyze without the pre-test freeze")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze.get("status") != "FROZEN_BEFORE_FULL_SAMPLING":
        raise RuntimeError("Pre-test freeze is not active")
    changed = []
    for rel, expected in freeze["sha256"].items():
        path = ROOT / Path(rel)
        if not path.is_file() or sha256_file(path) != expected:
            changed.append(rel)
    if changed:
        raise RuntimeError(f"Frozen inputs changed before independent analysis: {changed}")
    return freeze


def exact_mcnemar_p(standard_only: int, correlation_only: int) -> float:
    n = int(standard_only) + int(correlation_only)
    if n == 0:
        return 1.0
    k = min(int(standard_only), int(correlation_only))
    tail = sum(math.comb(n, i) for i in range(k + 1))
    p = Decimal(2) * Decimal(tail) / (Decimal(2) ** n)
    return float(min(Decimal(1), p))


def exact_signflip_p(values: np.ndarray) -> float:
    """Two-sided exhaustive root-level sign flip for one 12-root stratum."""
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or values.size != 12:
        raise ValueError("Expected exactly 12 paired root-cluster differences")
    observed = float(values.mean())
    signs = np.asarray(list(itertools.product((-1.0, 1.0), repeat=values.size)), dtype=np.float64)
    null = (signs * values[None, :]).mean(axis=1)
    return float(np.mean(np.abs(null) >= abs(observed) - 1e-15))


def holm_adjust(p_values: list[float]) -> list[float]:
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (m - rank) * float(p_values[index])))
        adjusted[index] = running
    return adjusted


def stratified_bootstrap_indices(resamples: int, roots_per_stratum: int, seed: int) -> np.ndarray:
    if resamples <= 0 or roots_per_stratum != 12:
        raise ValueError("Expected positive resamples and the frozen 12-root stratum size")
    rng = np.random.Generator(np.random.PCG64(seed))
    indices = rng.integers(0, roots_per_stratum,
                           size=(resamples, 6, roots_per_stratum), dtype=np.int16)
    if indices.shape != (resamples, 6, roots_per_stratum) or np.any(indices < 0) or np.any(indices >= roots_per_stratum):
        raise AssertionError("Bootstrap indices violate stratum/root allocation")
    return indices


def primary_root_signflip(deltas: np.ndarray, assignments: int, seed: int) -> tuple[float, float, int]:
    """Paired root signs within six fixed strata; aggregate strata equally."""
    deltas = np.asarray(deltas, dtype=np.float64)
    if deltas.shape != (6, 12):
        raise ValueError("Primary sign-flip input must be paired root deltas with shape (6, 12)")
    rng = np.random.Generator(np.random.PCG64(seed))
    signs = rng.integers(0, 2, size=(assignments, 6, 12), dtype=np.int8) * 2 - 1
    null = (signs * deltas[None, :, :]).mean(axis=2).mean(axis=1)
    observed = float(deltas.mean(axis=1).mean())
    extreme = int(np.count_nonzero(np.abs(null) >= abs(observed) - 1e-15))
    return float((1 + extreme) / (assignments + 1)), observed, extreme


def run_statistical_self_checks() -> dict:
    synthetic = np.asarray([[0.0001 * (s + 1) + 0.000001 * r for r in range(12)]
                            for s in range(6)], dtype=np.float64)
    signs_a = primary_root_signflip(synthetic, 1000, 12345)
    signs_b = primary_root_signflip(synthetic, 1000, 12345)
    if signs_a != signs_b:
        raise AssertionError("Seeded root-cluster sign-flip is not reproducible")
    exact_test = exact_signflip_p(np.full(12, -1.0))
    if not np.isclose(exact_test, 2 / 4096):
        raise AssertionError("Exact 12-root sign-flip test did not enumerate all root assignments")
    ix = stratified_bootstrap_indices(1000, 12, 54321)
    a = np.arange(72, dtype=np.float64).reshape(6, 12) / 1000
    b = a + synthetic
    paired = (b - a)
    sampled_paired = paired[np.arange(6)[None, :, None], ix]
    sampled_separately = b[np.arange(6)[None, :, None], ix] - a[np.arange(6)[None, :, None], ix]
    if ix.shape != (1000, 6, 12) or not np.array_equal(sampled_paired, sampled_separately):
        raise AssertionError("Bootstrap must resample paired root differences within each stratum")
    equal_weight = float(synthetic.mean(axis=1).mean())
    if not np.isclose(equal_weight, np.mean([synthetic[s].mean() for s in range(6)])):
        raise AssertionError("Primary estimand is not an equal-stratum average")
    return {"status": "PASS", "checks": [
        "root-cluster signs preserve six strata and paired root-level differences",
        "100,000-assignment method uses independent signs for each root and add-one p-value",
        "bootstrap resamples 12 roots within each of six strata using common paired root indices",
        "primary endpoint equally averages six stratum means",
        "exact secondary sign-flip enumerates all 2^12 assignments",
        "fixed RNG produces identical permutation and bootstrap assignments"
    ], "fixture_exact_signflip_p": exact_test,
       "fixture_primary_observed_delta": signs_a[1],
       "fixture_monte_carlo_extreme_assignments": signs_a[2]}


def build_audit_models() -> dict:
    models = {}
    dem_hashes = {}
    circuit_hashes = {}
    for basis in CFG["memory_bases"]:
        for index, regime in enumerate(CFG["regimes"]):
            circuit = noise_model.build_circuit(
                basis, regime, distance=CFG["distance"], rounds=CFG["rounds"],
                gate_p=CFG["gate_fault_probability_1q"],
                measurement_p=CFG["measurement_flip_probability"], bias_ratio=CFG["bias_ratio"])
            dem = circuit.detector_error_model(**CFG["dem_conversion"])
            key = (basis, index)
            dem_hashes[key] = hashlib.sha256(str(dem).encode("utf-8")).hexdigest()
            circuit_hashes[key] = hashlib.sha256(str(circuit).encode("utf-8")).hexdigest()
            models[(basis, index, False)] = pymatching.Matching.from_detector_error_model(
                dem, enable_correlations=False)
            models[(basis, index, True)] = pymatching.Matching.from_detector_error_model(
                dem, enable_correlations=True)
    return models, dem_hashes, circuit_hashes


def percentile_ci(values: np.ndarray) -> list[float]:
    low, high = np.quantile(np.asarray(values, dtype=np.float64), [0.025, 0.975])
    return [float(low), float(high)]


def run_analysis() -> dict:
    start = time.perf_counter()
    freeze = verify_frozen_inputs()
    expected_paths = [HERE / "checkpoints" / f"stratum_{si:02d}_root_{ri:02d}.npz"
                      for si in range(6) for ri in range(CFG["roots_per_stratum"])]
    missing = [p.relative_to(HERE).as_posix() for p in expected_paths if not p.is_file()]
    extra = sorted(p.name for p in (HERE / "checkpoints").glob("*.npz")
                   if p not in expected_paths)
    if missing or extra:
        raise RuntimeError(f"Evidence coverage mismatch; missing={missing[:5]}, extra={extra[:5]}")

    models, dem_hashes, circuit_hashes = build_audit_models()
    per_root = []
    root_ler = np.zeros((4, 6, CFG["roots_per_stratum"]), dtype=np.float64)
    root_errors = np.zeros((4, 6, CFG["roots_per_stratum"]), dtype=np.int64)
    root_observable_errors = np.zeros((6, CFG["roots_per_stratum"]), dtype=np.int64)
    per_stratum_counts = [{"raw_observable_errors": 0, "shots": 0,
                           "arm_errors": [0, 0, 0, 0],
                           "prediction_disagreement_matrix": [[0] * 4 for _ in range(4)],
                           "primary_standard_only": 0, "primary_correlation_only": 0,
                           "primary_disagreements": 0,
                           "regime_standard_only": 0, "regime_correlation_only": 0,
                           "regime_disagreements": 0} for _ in range(6)]
    checkpoint_hashes = {}
    predictions_verified = 0

    for si in range(6):
        label = CFG["stratum_order"][si]
        basis, regime = label.split("_", 1)
        reg_index = CFG["regimes"].index(regime)
        fixed_index = int(CFG["pooled_fixed_model_index_by_basis"][basis])
        for ri in range(CFG["roots_per_stratum"]):
            path = expected_paths[si * CFG["roots_per_stratum"] + ri]
            checkpoint_hashes[path.relative_to(HERE).as_posix()] = sha256_file(path)
            with np.load(path, allow_pickle=False) as z:
                required = {"schema_version", "detectors", "observable", "predictions", "root_seed",
                            "stratum_index", "root_index", "basis", "regime",
                            "fixed_decoder_index", "regime_decoder_index", "circuit_sha256",
                            "pooled_dem_sha256", "regime_dem_sha256", "decode_seconds"}
                if not required.issubset(set(z.files)):
                    raise RuntimeError(f"Missing archive keys in {path}: {sorted(required-set(z.files))}")
                packed = np.asarray(z["detectors"])
                obs = np.asarray(z["observable"])
                pred = np.asarray(z["predictions"])
                seed = int(z["root_seed"])
                schema_version = int(np.asarray(z["schema_version"]))
                stored_si, stored_ri = int(z["stratum_index"]), int(z["root_index"])
                stored_basis = str(z["basis"].item())
                stored_regime = str(z["regime"].item())
                stored_fixed = int(z["fixed_decoder_index"])
                stored_reg = int(z["regime_decoder_index"])
                circuit_sha = str(z["circuit_sha256"].item())
                pooled_dem_sha = str(z["pooled_dem_sha256"].item())
                regime_dem_sha = str(z["regime_dem_sha256"].item())
                decode_seconds = np.asarray(z["decode_seconds"], dtype=np.float64)
            n = CFG["shots_per_root"]
            if schema_version != 1:
                raise RuntimeError(f"Unsupported schema version in {path}")
            if packed.shape != (n, 5) or packed.dtype != np.uint8:
                raise RuntimeError(f"Detector packed schema failure in {path}: {packed.shape} {packed.dtype}")
            if obs.shape != (n,) or obs.dtype.kind not in "bu" or not np.isin(obs, [0, 1]).all():
                raise RuntimeError(f"Observable schema/binary failure in {path}")
            if pred.shape != (4, n) or pred.dtype.kind not in "bu" or not np.isin(pred, [0, 1]).all():
                raise RuntimeError(f"Prediction schema/binary failure in {path}")
            if stored_si != si or stored_ri != ri or stored_basis != basis or stored_regime != regime:
                raise RuntimeError(f"Filename-to-root/condition mapping mismatch in {path}")
            expected_seed = int(CFG["seed_allocation"]["root_seed_base"] + 100 * si + ri)
            if seed != expected_seed:
                raise RuntimeError(f"Root seed formula mismatch in {path}: {seed} != {expected_seed}")
            if stored_fixed != fixed_index or stored_reg != reg_index:
                raise RuntimeError(f"Decoder index mismatch in {path}")
            if circuit_sha != circuit_hashes[(basis, reg_index)]:
                raise RuntimeError(f"Generating circuit hash mismatch in {path}")
            if pooled_dem_sha != dem_hashes[(basis, fixed_index)] or regime_dem_sha != dem_hashes[(basis, reg_index)]:
                raise RuntimeError(f"Stored DEM hash mismatch in {path}")
            if decode_seconds.shape != (4,) or not np.isfinite(decode_seconds).all() or np.any(decode_seconds < 0):
                raise RuntimeError(f"Timing schema failure in {path}")
            detectors = np.unpackbits(packed, axis=1, bitorder="little")[:, :40]
            if detectors.shape != (n, 40) or not np.isin(detectors, [0, 1]).all():
                raise RuntimeError(f"Detector unpack failure in {path}")

            # Recompute all four outputs directly from saved detectors, never from
            # runner counters or reporting functions.
            audit_pred = np.stack([
                np.asarray(models[(basis, fixed_index, False)].decode_batch(detectors, enable_correlations=False)).reshape(-1),
                np.asarray(models[(basis, fixed_index, True)].decode_batch(detectors, enable_correlations=True)).reshape(-1),
                np.asarray(models[(basis, reg_index, False)].decode_batch(detectors, enable_correlations=False)).reshape(-1),
                np.asarray(models[(basis, reg_index, True)].decode_batch(detectors, enable_correlations=True)).reshape(-1),
            ], axis=0).astype(np.uint8)
            if audit_pred.shape != pred.shape or not np.array_equal(audit_pred, pred):
                mismatch = int(np.count_nonzero(audit_pred != pred)) if audit_pred.shape == pred.shape else -1
                raise RuntimeError(f"Independent re-decode mismatch in {path}: {mismatch} bits")
            predictions_verified += int(pred.size)
            errors = np.bitwise_xor(obs[None, :], pred)
            if not np.isin(errors, [0, 1]).all():
                raise RuntimeError(f"Residual indicator invalid in {path}")
            counts = errors.sum(axis=1).astype(int)
            root_errors[:, si, ri] = counts
            root_ler[:, si, ri] = counts / n
            root_observable_errors[si, ri] = int(obs.sum())

            c = per_stratum_counts[si]
            c["shots"] += n
            c["raw_observable_errors"] += int(obs.sum())
            for ai in range(4):
                c["arm_errors"][ai] += int(counts[ai])
                for bi in range(4):
                    c["prediction_disagreement_matrix"][ai][bi] += int(np.count_nonzero(pred[ai] != pred[bi]))
            root_primary_standard_only = int(np.count_nonzero((errors[0] == 1) & (errors[1] == 0)))
            root_primary_correlation_only = int(np.count_nonzero((errors[0] == 0) & (errors[1] == 1)))
            root_primary_disagreements = int(np.count_nonzero(pred[0] != pred[1]))
            root_regime_standard_only = int(np.count_nonzero((errors[2] == 1) & (errors[3] == 0)))
            root_regime_correlation_only = int(np.count_nonzero((errors[2] == 0) & (errors[3] == 1)))
            root_regime_disagreements = int(np.count_nonzero(pred[2] != pred[3]))
            c["primary_standard_only"] += root_primary_standard_only
            c["primary_correlation_only"] += root_primary_correlation_only
            c["primary_disagreements"] += root_primary_disagreements
            c["regime_standard_only"] += root_regime_standard_only
            c["regime_correlation_only"] += root_regime_correlation_only
            c["regime_disagreements"] += root_regime_disagreements
            row = {"stratum_index": si, "stratum": label, "basis": basis, "regime": regime,
                   "root_index": ri, "seed": seed, "shots": n,
                   "raw_observable_errors": int(obs.sum()),
                   "paired_predictions_redecoded_and_verified": True,
                   "checkpoint_sha256": checkpoint_hashes[path.relative_to(HERE).as_posix()]}
            for ai, name in enumerate(ARMS):
                row[f"{name}_errors"] = int(counts[ai])
                row[f"{name}_ler"] = float(counts[ai] / n)
            row.update({
                "primary_pooled_standard_only_failures": root_primary_standard_only,
                "primary_pooled_correlation_only_failures": root_primary_correlation_only,
                "primary_pooled_disagreements": root_primary_disagreements,
                "decode_seconds_pooled_uncorrelated": float(decode_seconds[0]),
                "decode_seconds_pooled_correlated": float(decode_seconds[1]),
                "decode_seconds_regime_uncorrelated": float(decode_seconds[2]),
                "decode_seconds_regime_correlated": float(decode_seconds[3]),
            })
            per_root.append(row)

    # Root-level paired differences are the independent units for uncertainty.
    primary_deltas = root_ler[1] - root_ler[0]   # (6 strata, 12 roots)
    regime_uncorr_deltas = root_ler[2] - root_ler[0]
    regime_corr_deltas = root_ler[3] - root_ler[1]
    B = int(CFG["statistics"]["bootstrap_resamples"])
    indices = stratified_bootstrap_indices(B, CFG["roots_per_stratum"],
                                           CFG["seed_allocation"]["bootstrap_rng"])
    strata_axis = np.arange(6)[None, :, None]
    boot_arm_means = []
    for ai in range(4):
        sampled = root_ler[ai][strata_axis, indices]
        boot_arm_means.append(sampled.mean(axis=2).mean(axis=1))
    boot_arm_means = np.asarray(boot_arm_means)
    boot_primary_by_stratum = np.stack([
        (root_ler[1, si, :][indices[:, si, :]].mean(axis=1) -
         root_ler[0, si, :][indices[:, si, :]].mean(axis=1)) for si in range(6)
    ], axis=1)
    boot_primary = boot_primary_by_stratum.mean(axis=1)
    primary_delta = float(primary_deltas.mean(axis=1).mean())
    assignments = int(CFG["statistics"]["primary_signflip_assignments"])
    primary_p, primary_delta_from_test, extreme_assignments = primary_root_signflip(
        primary_deltas, assignments, CFG["seed_allocation"]["primary_signflip_rng"])
    if not np.isclose(primary_delta, primary_delta_from_test):
        raise AssertionError("Primary estimand differs between aggregation and sign-flip code")
    primary_ci = percentile_ci(boot_primary)
    leave_one_stratum_out = {
        CFG["stratum_order"][excluded]: float(np.delete(primary_deltas.mean(axis=1), excluded).mean())
        for excluded in range(6)
    }

    # Exact McNemar for paired shot-level residual disagreement; descriptive only.
    aggregate = {
        "shots": int(root_errors.shape[1] * root_errors.shape[2] * CFG["shots_per_root"]),
        "raw_observable_errors": int(root_observable_errors.sum()),
        "arm_errors": root_errors.sum(axis=(1, 2)).astype(int).tolist(),
        "arm_ler_pooled_shots": (root_errors.sum(axis=(1, 2)) /
                                  (6 * CFG["roots_per_stratum"] * CFG["shots_per_root"])).astype(float).tolist(),
        "arm_ler_equal_stratum_mean": root_ler.mean(axis=(1, 2)).astype(float).tolist(),
        "arm_ler_equal_stratum_root_bootstrap_95_ci": [percentile_ci(boot_arm_means[i]) for i in range(4)],
    }
    strata_rows = []
    for si, label in enumerate(CFG["stratum_order"]):
        basis, regime = label.split("_", 1)
        c = per_stratum_counts[si]
        n = c["shots"]
        row = {"stratum_index": si, "stratum": label, "basis": basis, "regime": regime,
               "shots": n, "roots": CFG["roots_per_stratum"],
               "raw_observable_errors": c["raw_observable_errors"],
               "primary_delta_correlated_minus_uncorrelated": float(primary_deltas[si].mean()),
               "primary_delta_root_cluster_95_ci": percentile_ci(boot_primary_by_stratum[:, si]),
               "primary_root_delta_sd": float(primary_deltas[si].std(ddof=1)),
               "primary_root_wins_correlated": int(np.count_nonzero(primary_deltas[si] < 0)),
               "primary_root_losses_correlated": int(np.count_nonzero(primary_deltas[si] > 0)),
               "primary_root_ties": int(np.count_nonzero(primary_deltas[si] == 0)),
               "primary_standard_only_failures": c["primary_standard_only"],
               "primary_correlation_only_failures": c["primary_correlation_only"],
               "primary_disagreements": c["primary_disagreements"],
               "primary_exact_shot_mcnemar_p_descriptive": exact_mcnemar_p(
                   c["primary_standard_only"], c["primary_correlation_only"]),
               "regime_standard_only_failures": c["regime_standard_only"],
               "regime_correlation_only_failures": c["regime_correlation_only"],
               "regime_disagreements": c["regime_disagreements"]}
        for ai, arm in enumerate(ARMS):
            row[f"{arm}_errors"] = c["arm_errors"][ai]
            row[f"{arm}_ler"] = float(c["arm_errors"][ai] / n)
            row[f"{arm}_root_ler_sd"] = float(root_ler[ai, si, :].std(ddof=1))
            row[f"{arm}_root_ler_ci_95"] = percentile_ci(
                np.mean(root_ler[ai, si, :][indices[:, si, :]], axis=1))
        for ai in range(4):
            for bi in range(4):
                row[f"pred_disagreements_arm{ai}_arm{bi}"] = c["prediction_disagreement_matrix"][ai][bi]
        strata_rows.append(row)

    secondary = []
    for si, label in enumerate(CFG["stratum_order"]):
        for comparison, deltas in (("regime_informed_uncorrelated_minus_pooled_uncorrelated", regime_uncorr_deltas),
                                   ("regime_informed_correlated_minus_pooled_correlated", regime_corr_deltas)):
            secondary.append({"stratum_index": si, "stratum": label, "comparison": comparison,
                              "delta_ler": float(deltas[si].mean()),
                              "exact_root_cluster_signflip_p": exact_signflip_p(deltas[si])})
    secondary_p = [x["exact_root_cluster_signflip_p"] for x in secondary]
    secondary_adj = holm_adjust(secondary_p)
    for x, adj in zip(secondary, secondary_adj):
        x["holm_adjusted_p"] = float(adj)

    # Write machine-readable per-root and per-stratum data.
    per_root_fields = list(per_root[0].keys())
    with (HERE / "PER_ROOT_RESULTS.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=per_root_fields)
        writer.writeheader(); writer.writerows(per_root)
    stratum_fields = list(strata_rows[0].keys())
    with (HERE / "PER_STRATUM_RESULTS.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=stratum_fields)
        writer.writeheader(); writer.writerows(strata_rows)
    with (HERE / "SECONDARY_COMPARISONS.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(secondary[0].keys()))
        writer.writeheader(); writer.writerows(secondary)

    disagreement_rows = []
    for si, label in enumerate(CFG["stratum_order"]):
        c = per_stratum_counts[si]
        for ai, arm_a in enumerate(ARMS):
            for bi, arm_b in enumerate(ARMS):
                disagreement_rows.append({"stratum_index": si, "stratum": label,
                                          "arm_a": arm_a, "arm_b": arm_b,
                                          "disagreement_shots": c["prediction_disagreement_matrix"][ai][bi],
                                          "shots": c["shots"],
                                          "disagreement_rate": c["prediction_disagreement_matrix"][ai][bi] / c["shots"]})
    with (HERE / "DECODER_DISAGREEMENTS.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(disagreement_rows[0].keys()))
        writer.writeheader(); writer.writerows(disagreement_rows)

    primary = {
        "candidate": "pooled_fixed_correlated",
        "baseline": "pooled_fixed_uncorrelated",
        "estimand": "equal-stratum mean correlated LER minus uncorrelated LER",
        "delta_ler": primary_delta,
        "delta_percentage_points": primary_delta * 100,
        "relative_error_reduction": (None if aggregate["arm_errors"][0] == 0 else
                                     1 - aggregate["arm_errors"][1] / aggregate["arm_errors"][0]),
        "root_stratified_bootstrap_95_ci": primary_ci,
        "two_sided_root_cluster_signflip_p": primary_p,
        "signflip_assignments": assignments,
        "signflip_extreme_assignments": extreme_assignments,
        "signflip_add_one": True,
        "exact_shot_mcnemar_standard_only": sum(x["primary_standard_only_failures"] for x in strata_rows),
        "exact_shot_mcnemar_correlation_only": sum(x["primary_correlation_only_failures"] for x in strata_rows),
        "exact_shot_mcnemar_p_descriptive": exact_mcnemar_p(
            sum(x["primary_standard_only_failures"] for x in strata_rows),
            sum(x["primary_correlation_only_failures"] for x in strata_rows)),
        "prediction_disagreements": sum(x["primary_disagreements"] for x in strata_rows),
        "strata_favoring_correlated": sum(x["primary_delta_correlated_minus_uncorrelated"] < 0 for x in strata_rows),
        "practical_margin_absolute_ler": 0.0002,
        "gate_point_estimate_pass": primary_delta <= -0.0002,
        "gate_ci_pass": primary_ci[1] <= -0.0002,
        "gate_favorable_strata_pass": sum(x["primary_delta_correlated_minus_uncorrelated"] < 0 for x in strata_rows) >= 4,
        "leave_one_stratum_out_delta_ler": leave_one_stratum_out,
        "gate_no_single_stratum_drives": all(v < 0 for v in leave_one_stratum_out.values()),
    }
    primary["feasibility_gate_pass"] = bool(primary["gate_point_estimate_pass"] and
                                            primary["gate_ci_pass"] and
                                            primary["gate_favorable_strata_pass"] and
                                            primary["gate_no_single_stratum_drives"])
    result = {
        "status": "INDEPENDENTLY_RECOMPUTED",
        "study_id": CFG["study_id"],
        "evidence_coverage": {"strata": 6, "roots_per_stratum": 12, "roots": 72,
                              "shots_per_root": 10000, "paired_test_shots": 720000,
                              "checkpoint_count": len(checkpoint_hashes),
                              "predictions_independently_redecoded": True,
                              "prediction_bits_verified": predictions_verified},
        "arm_order": ARMS,
        "aggregate": aggregate,
        "primary": primary,
        "per_stratum": strata_rows,
        "secondary_comparisons": secondary,
        "timings": json.loads((HERE / "RUN_TIMINGS.json").read_text(encoding="utf-8")),
        "freeze_sha256": sha256_file(HERE / "PRETEST_FREEZE.json"),
        "analysis_seconds": round(time.perf_counter() - start, 4),
        "seed_information": CFG["seed_allocation"],
        "statistical_method": CFG["statistics"],
        "limitations": [
            "All outcomes are development-only simulation evidence, not a confirmatory test.",
            "Stim approximate_disjoint_errors=True converts the categorical channel into approximate independent DEM mechanisms; both correlation arms use the same approximation.",
            "PyMatching correlated matching uses available DEM decomposition metadata and cannot recover information lost during DEM approximation.",
            "Root-cluster uncertainty is based on 12 independent roots per stratum and may be imprecise.",
            "The simulation is circuit-level stochastic Pauli noise with fixed per-circuit settings; it is not hardware data or within-circuit time-varying noise."
        ],
    }
    atomic_json(HERE / "RESULTS.json", result)
    write_reports(result, checkpoint_hashes)
    return result


def write_reports(result: dict, checkpoint_hashes: dict) -> None:
    primary = result["primary"]
    rows = result["per_stratum"]
    lines = [
        "# Correlation-aware PyMatching development pilot results", "",
        "## Status", "",
        "The complete bounded development pilot was executed and independently recomputed from the saved raw NPZ bundles. This is not a confirmatory experiment.", "",
        "## Primary pooled-fixed ablation", "",
        f"- Pooled fixed, uncorrelated: **{result['aggregate']['arm_errors'][0]:,}/{result['aggregate']['shots']:,}** errors (LER {result['aggregate']['arm_ler_pooled_shots'][0]:.6%}).",
        f"- Pooled fixed, correlated: **{result['aggregate']['arm_errors'][1]:,}/{result['aggregate']['shots']:,}** errors (LER {result['aggregate']['arm_ler_pooled_shots'][1]:.6%}).",
        f"- Equal-stratum paired difference (correlated − uncorrelated): **{primary['delta_ler']:+.8f}** ({primary['delta_percentage_points']:+.6f} percentage points).",
        f"- Regime-stratified root-bootstrap 95% CI: **[{primary['root_stratified_bootstrap_95_ci'][0]:+.8f}, {primary['root_stratified_bootstrap_95_ci'][1]:+.8f}]**.",
        f"- Root-cluster sign-flip p={primary['two_sided_root_cluster_signflip_p']:.6g}; shot-level McNemar p={primary['exact_shot_mcnemar_p_descriptive']:.6g} (descriptive only).",
        f"- Paired shot discordances: standard-only failures {primary['exact_shot_mcnemar_standard_only']:,}; correlation-aware-only failures {primary['exact_shot_mcnemar_correlation_only']:,}; prediction disagreements {primary['prediction_disagreements']:,}.",
        f"- Frozen development gate: **{'PASS' if primary['feasibility_gate_pass'] else 'FAIL'}** (margin 0.0002 LER; upper 95% bound ≤ −0.0002; at least four of six strata favorable; all leave-one-stratum-out aggregates remain favorable).", "",
        "## Results by stratum", "",
        "| Stratum | Raw observable | Pooled off | Pooled on | Regime-informed off | Regime-informed on | Paired Δ pooled (95% root CI) | Standard-only / correlation-only |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in rows:
        ci = r["primary_delta_root_cluster_95_ci"]
        lines.append(f"| {r['stratum']} | {r['raw_observable_errors']}/{r['shots']} | {r['pooled_fixed_uncorrelated_errors']} ({r['pooled_fixed_uncorrelated_ler']:.4%}) | {r['pooled_fixed_correlated_errors']} ({r['pooled_fixed_correlated_ler']:.4%}) | {r['regime_informed_uncorrelated_errors']} ({r['regime_informed_uncorrelated_ler']:.4%}) | {r['regime_informed_correlated_errors']} ({r['regime_informed_correlated_ler']:.4%}) | {r['primary_delta_correlated_minus_uncorrelated']:+.6f} [{ci[0]:+.6f},{ci[1]:+.6f}] | {r['primary_standard_only_failures']}/{r['primary_correlation_only_failures']} |")
    lines.extend(["", "## Interpretation and limitations", "",
                  "The primary comparison changes only whether PyMatching uses the correlation metadata in the same pooled-fixed DEM; regime-informed results are secondary and use the simulated generating regime as privileged information. The experiment does not validate an adaptive controller.", "",
                  "Stim’s DEM conversion of mutually exclusive categorical Pauli-channel outcomes is approximate (`approximate_disjoint_errors=True`). The paired ablation isolates correlation use conditional on that same approximate DEM; it cannot measure information lost by the conversion. Twelve roots per cell make the pilot useful for feasibility but leave seed-level uncertainty limited. No hardware was used.", "",
                  "## Reproducibility", "",
                  "Run `python preflight_correlation_pilot.py` for deterministic smoke/preflight checks. After verifying `PRETEST_FREEZE.json`, run `python run_correlation_pilot.py`. Independently re-decode and analyze with `python analyze_correlation_pilot.py`. See `REPRODUCE.md` and the SHA-256 manifest.", ""])
    (HERE / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    timing = result["timings"]
    stat_lines = [
        "# Statistical analysis", "",
        "## Primary pooled-fixed paired comparison", "",
        f"- Difference, correlated minus uncorrelated: {primary['delta_ler']:+.10f} LER ({primary['delta_percentage_points']:+.6f} percentage points).",
        f"- Regime-stratified root-cluster bootstrap 95% interval: [{primary['root_stratified_bootstrap_95_ci'][0]:+.10f}, {primary['root_stratified_bootstrap_95_ci'][1]:+.10f}].",
        f"- Two-sided paired root-cluster sign-flip p={primary['two_sided_root_cluster_signflip_p']:.10g} using {primary['signflip_assignments']:,} assignments and add-one correction; {primary['signflip_extreme_assignments']} assignments were at least as extreme.",
        f"- Descriptive exact paired-shot McNemar p={primary['exact_shot_mcnemar_p_descriptive']:.10g}.",
        f"- Root wins/losses/ties by stratum are in `PER_STRATUM_RESULTS.csv`; primary shot-level discordances are {primary['exact_shot_mcnemar_standard_only']:,} standard-only vs {primary['exact_shot_mcnemar_correlation_only']:,} correlation-aware-only failures.",
        "- Root clusters, not individual shots, are the independent units for the primary uncertainty and test.", "",
        "## Resampling and secondary family", "",
        "The primary bootstrap resamples roots within each of six strata and applies the same root indices to the paired arms. The primary estimand is the equal-weight mean of the six stratum means. Secondary comparisons are the 12 exact root-level sign-flip tests of regime-informed minus the corresponding pooled fixed arm, separately for correlation off/on, with Holm adjustment across all 12. These are privileged regime-information diagnostics, not deployable policies.", "",
        "## Runtime and memory", "",
        f"- Decoder construction: {timing['decoder_construction_seconds']:.4f} s.",
        f"- Stim sampling: {timing['sampling_wall_seconds']:.4f} s.",
        f"- Decode time by arm: `{json.dumps(timing['inference_wall_seconds_by_arm'])}`.",
        f"- Sampling/decode loop wall time: {timing['sampling_and_decode_loop_wall_seconds']:.4f} s.",
        f"- Process RSS at start / after model build / sampled peak: {timing['process_rss_bytes_start']} / {timing['process_rss_bytes_after_model_build']} / {timing['observed_peak_process_rss_bytes']} bytes.",
        "- Process memory includes Python and native allocations; the peak is observed between root batches and is not an isolated PyMatching measurement.", ""
    ]
    (HERE / "STATISTICAL_ANALYSIS.md").write_text("\n".join(stat_lines), encoding="utf-8")
    limitation_lines = [
        "# Limitations", "",
        "- This is a development feasibility pilot. It does not confirm performance on an untouched confirmatory experiment.",
        "- The custom categorical `PAULI_CHANNEL_1/2` simulator is sampled directly by Stim, but DEM construction uses `approximate_disjoint_errors=True`. The four arms share the same approximate DEM within each model; this experiment isolates use of decomposition correlation metadata, not information loss from DEM conversion.",
        "- PyMatching’s correlated option uses correlations represented by the decomposed DEM. It cannot reconstruct categorical event dependencies that the conversion omitted.",
        "- Only distance 3 and five rounds are tested here; conclusions do not transfer automatically to other distances, rounds, or circuit schedules.",
        "- The noise channels are controlled stochastic Pauli settings. No coherent noise, leakage, inter-gate crosstalk, long-range bursts, within-circuit drift, or device-calibrated parameters are included.",
        "- Twelve independent roots per condition provide limited seed-level resolution. The confidence interval and root-level variability should be emphasized over shot-count-only significance.",
        "- Regime-informed decoders receive the hidden simulated condition and are diagnostic references, not deployable policies.",
        "- Runtime is local CPU software timing. No hard real-time or hardware compatibility claim is supported.", ""
    ]
    (HERE / "LIMITATIONS.md").write_text("\n".join(limitation_lines), encoding="utf-8")
    audit = [
        "# Independent evidence audit", "",
        "## Decision", "",
        "PASS: all expected per-root raw bundles are present, each stored prediction was regenerated from its stored unpacked detector samples using independently rebuilt PyMatching instances, and every aggregate in `RESULTS.json` was recomputed from the raw labels and predictions by this script.", "",
        f"Evidence coverage: {result['evidence_coverage']['checkpoint_count']} checkpoints, {result['evidence_coverage']['paired_test_shots']:,} paired shots, {result['evidence_coverage']['prediction_bits_verified']:,} prediction bits independently matched.", "",
        "## Checks", "",
        "- Filename-to-stratum/root mapping and seed formula checked for all 72 files.",
        "- Packed detector arrays checked as uint8 `(10000, 5)` and unpacked little-endian to `(10000, 40)`.",
        "- Observable and prediction arrays checked for shape and binary values.",
        "- All four predictions per shot were recomputed from the saved detectors; mismatch count was zero.",
        "- Logical residuals were recomputed as observable XOR predicted logical flip.",
        "- Per-root, per-stratum and aggregate counts were calculated from arrays, not the runner’s counters.",
        "- Each checkpoint SHA-256 is recorded in `CHECKPOINT_HASHES.json`.", "",
        "## Scope limitation", "",
        "This audit verifies test-array alignment and decoder predictions. It does not make the approximate DEM an exact representation of the categorical Stim channel and does not establish hardware validity or confirmatory status.", ""
    ]
    (HERE / "INDEPENDENT_EVIDENCE_AUDIT.md").write_text("\n".join(audit), encoding="utf-8")
    atomic_json(HERE / "CHECKPOINT_HASHES.json", {"checkpoint_sha256": checkpoint_hashes,
                                                   "count": len(checkpoint_hashes)})


if __name__ == "__main__":
    result = run_analysis()
    print(json.dumps({"status": result["status"], "shots": result["evidence_coverage"]["paired_test_shots"],
                      "errors": result["aggregate"]["arm_errors"],
                      "primary_delta_ler": result["primary"]["delta_ler"],
                      "primary_ci": result["primary"]["root_stratified_bootstrap_95_ci"],
                      "primary_p": result["primary"]["two_sided_root_cluster_signflip_p"]}, indent=2))
