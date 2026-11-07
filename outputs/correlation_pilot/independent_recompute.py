"""Independent, read-only recomputation of the correlation pilot checkpoints.

This script intentionally does not import the pilot runner or its reporting
functions. It rebuilds the six Phase 2B DEM pairs, checks saved predictions,
and recomputes paired errors/statistics directly from NPZ evidence.
"""
from __future__ import annotations

import csv
import csv
import hashlib
import importlib
import itertools
import json
import math
import sys
from decimal import Decimal
from pathlib import Path

import numpy as np
import pymatching

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
PHASE2B = (HERE / CFG["phase2b_source_dir"]).resolve()
sys.path.insert(0, str(PHASE2B))
noise_model = importlib.import_module("noise_model")
ARMS = CFG["decoder_arms"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def graph_signature(matcher):
    return sorted(((-1 if u is None else int(u)), (-1 if v is None else int(v)),
                   float(data["weight"]).hex(),
                   tuple(sorted(int(k) for k in data.get("fault_ids", set()))))
                  for u, v, data in matcher.edges())


def build_models():
    models = {}
    dem_hashes = {}
    for basis in CFG["memory_bases"]:
        for regime_index, regime in enumerate(CFG["regimes"]):
            circuit = noise_model.build_circuit(
                basis, regime, distance=CFG["distance"], rounds=CFG["rounds"],
                gate_p=CFG["gate_fault_probability_1q"],
                measurement_p=CFG["measurement_flip_probability"],
                bias_ratio=CFG["bias_ratio"])
            dem = circuit.detector_error_model(**CFG["dem_conversion"])
            if dem.num_detectors != 40 or dem.num_observables != 1:
                raise AssertionError(f"Unexpected DEM dimensions for {basis}/{regime}")
            dem_hashes[f"{basis}_{regime}"] = hashlib.sha256(str(dem).encode()).hexdigest()
            off = pymatching.Matching.from_detector_error_model(dem, enable_correlations=False)
            on = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
            if graph_signature(off) != graph_signature(on):
                raise AssertionError(f"Correlation toggle changed graph/weights for {basis}/{regime}")
            if off.num_detectors != 40 or on.num_detectors != 40:
                raise AssertionError(f"Detector count mismatch for {basis}/{regime}")
            models[(basis, regime_index, False)] = off
            models[(basis, regime_index, True)] = on
    return models, dem_hashes


def exact_mcnemar_p(a: int, b: int) -> float:
    n = a + b
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(a, b) + 1))
    return float(min(Decimal(1), Decimal(2 * tail) / (Decimal(2) ** n)))


def main():
    models, dem_hashes = build_models()
    strata = CFG["stratum_order"]
    roots = CFG["roots_per_stratum"]
    shots = CFG["shots_per_root"]
    per_root = []
    total_errors = np.zeros((4,), dtype=np.int64)
    total_observable = 0
    total_pair_wrong = np.zeros((4, 4), dtype=np.int64)
    total_pair_pred_disagree = np.zeros((4, 4), dtype=np.int64)
    mcnemar_primary = [0, 0]
    root_ler = np.zeros((4, 6, roots), dtype=np.float64)
    root_delta = np.zeros((6, roots), dtype=np.float64)
    checkpoint_hashes = {}
    prediction_bits_checked = 0
    expected_seed_base = CFG["seed_allocation"]["root_seed_base"]

    for si, label in enumerate(strata):
        basis, generating_regime = label.split("_", 1)
        generating_index = CFG["regimes"].index(generating_regime)
        fixed_index = int(CFG["pooled_fixed_model_index_by_basis"][basis])
        for ri in range(roots):
            rel = f"checkpoints/stratum_{si:02d}_root_{ri:02d}.npz"
            path = HERE / rel
            if not path.is_file():
                raise AssertionError(f"Missing checkpoint: {rel}")
            digest = sha256(path)
            checkpoint_hashes[rel] = digest
            expected_seed = int(expected_seed_base + 100 * si + ri)
            with np.load(path, allow_pickle=False) as z:
                required = {"schema_version", "detectors", "observable", "predictions",
                            "root_seed", "stratum_index", "root_index", "basis", "regime",
                            "fixed_decoder_index", "regime_decoder_index"}
                if not required.issubset(z.files):
                    raise AssertionError(f"Missing fields in {rel}: {sorted(required-set(z.files))}")
                if int(z["schema_version"]) != 1 or int(z["root_seed"]) != expected_seed:
                    raise AssertionError(f"Schema or seed mismatch in {rel}")
                if int(z["stratum_index"]) != si or int(z["root_index"]) != ri:
                    raise AssertionError(f"Filename/root mapping mismatch in {rel}")
                if str(z["basis"].item()) != basis or str(z["regime"].item()) != generating_regime:
                    raise AssertionError(f"Condition metadata mismatch in {rel}")
                if int(z["fixed_decoder_index"]) != fixed_index or int(z["regime_decoder_index"]) != generating_index:
                    raise AssertionError(f"Decoder selection metadata mismatch in {rel}")
                packed = z["detectors"]
                obs = z["observable"].copy()
                stored = z["predictions"].copy()
                if packed.shape != (shots, 5) or packed.dtype != np.uint8:
                    raise AssertionError(f"Packed detector schema mismatch in {rel}")
                detectors = np.unpackbits(packed, axis=1, count=40, bitorder="little")
                if detectors.shape != (shots, 40) or not np.isin(detectors, (0, 1)).all():
                    raise AssertionError(f"Detector unpack validation failed in {rel}")
                if obs.shape != (shots,) or not np.isin(obs, (0, 1)).all():
                    raise AssertionError(f"Observable schema/value mismatch in {rel}")
                if stored.shape != (4, shots) or not np.isin(stored, (0, 1)).all():
                    raise AssertionError(f"Prediction schema/value mismatch in {rel}")

            model_specs = [
                (basis, fixed_index, False),
                (basis, fixed_index, True),
                (basis, generating_index, False),
                (basis, generating_index, True),
            ]
            expected_predictions = []
            for key in model_specs:
                matcher = models[key]
                corr = key[2]
                pred = np.asarray(matcher.decode_batch(detectors, enable_correlations=corr), dtype=np.uint8)
                if pred.shape == (shots, 1):
                    pred = pred[:, 0]
                if pred.shape != (shots,) or not np.isin(pred, (0, 1)).all():
                    raise AssertionError(f"Decoder output invalid for {rel}, arm {key}")
                expected_predictions.append(pred)
            expected_predictions = np.stack(expected_predictions)
            mismatch = int(np.count_nonzero(expected_predictions != stored))
            if mismatch:
                raise AssertionError(f"Stored predictions mismatch in {rel}: {mismatch} bits")
            prediction_bits_checked += int(stored.size)

            residual = stored ^ obs[None, :]
            errors = residual.sum(axis=1).astype(np.int64)
            total_errors += errors
            total_observable += int(obs.sum())
            for a in range(4):
                for b in range(4):
                    total_pair_wrong[a, b] += int(np.count_nonzero((residual[a] == 1) & (residual[b] == 0)))
                    total_pair_pred_disagree[a, b] += int(np.count_nonzero(stored[a] != stored[b]))
            std_only = int(np.count_nonzero((residual[0] == 1) & (residual[1] == 0)))
            corr_only = int(np.count_nonzero((residual[1] == 1) & (residual[0] == 0)))
            mcnemar_primary[0] += std_only
            mcnemar_primary[1] += corr_only
            root_ler[:, si, ri] = errors / shots
            root_delta[si, ri] = (errors[1] - errors[0]) / shots
            per_root.append({"stratum_index": si, "stratum": label, "root_index": ri,
                             "seed": expected_seed, "shots": shots, "raw_observable_errors": int(obs.sum()),
                             "arm_errors": errors.tolist(), "standard_only_failures": std_only,
                             "correlation_only_failures": corr_only,
                             "primary_prediction_disagreements": int(np.count_nonzero(stored[0] != stored[1])),
                             "checkpoint_sha256": digest})

    # Cross-check the reporting CSV independently, root by root.
    with (HERE / "PER_ROOT_RESULTS.csv").open(newline="", encoding="utf-8") as f:
        saved_root_rows = list(csv.DictReader(f))
    if len(saved_root_rows) != len(per_root):
        raise AssertionError(f"PER_ROOT_RESULTS.csv has {len(saved_root_rows)} rows; expected {len(per_root)}")
    csv_arm_fields = [f"{arm}_errors" for arm in ARMS]
    for recomputed, saved in zip(per_root, saved_root_rows):
        if (int(saved["stratum_index"]) != recomputed["stratum_index"] or
                int(saved["root_index"]) != recomputed["root_index"] or
                int(saved["seed"]) != recomputed["seed"] or
                int(saved["shots"]) != shots or
                int(saved["raw_observable_errors"]) != recomputed["raw_observable_errors"] or
                saved["checkpoint_sha256"] != recomputed["checkpoint_sha256"] or
                [int(saved[k]) for k in csv_arm_fields] != recomputed["arm_errors"] or
                int(saved["primary_pooled_standard_only_failures"]) != recomputed["standard_only_failures"] or
                int(saved["primary_pooled_correlation_only_failures"]) != recomputed["correlation_only_failures"] or
                int(saved["primary_pooled_disagreements"]) != recomputed["primary_prediction_disagreements"]):
            raise AssertionError(f"PER_ROOT_RESULTS.csv mismatch at stratum/root {recomputed['stratum_index']}/{recomputed['root_index']}")

    # Recompute the frozen primary interval and Monte Carlo root-cluster test.
    rng = np.random.Generator(np.random.PCG64(int(CFG["seed_allocation"]["bootstrap_rng"])))
    bootstrap_n = int(CFG["statistics"]["bootstrap_resamples"])
    index = rng.integers(0, roots, size=(bootstrap_n, 6, roots), dtype=np.int16)
    boot_by_stratum = np.stack([
        (root_ler[1, s, :][index[:, s, :]].mean(axis=1) -
         root_ler[0, s, :][index[:, s, :]].mean(axis=1)) for s in range(6)
    ], axis=1)
    boot_primary = boot_by_stratum.mean(axis=1)
    primary_ci = np.quantile(boot_primary, [0.025, 0.975]).tolist()
    primary_delta = float(root_delta.mean())
    rng = np.random.Generator(np.random.PCG64(int(CFG["seed_allocation"]["primary_signflip_rng"])))
    assignments = int(CFG["statistics"]["primary_signflip_assignments"])
    signs = rng.integers(0, 2, size=(assignments, 6, roots), dtype=np.int8) * 2 - 1
    null = (signs * root_delta[None, :, :]).mean(axis=2).mean(axis=1)
    extremes = int(np.count_nonzero(np.abs(null) >= abs(primary_delta) - 1e-15))
    signflip_p = (1 + extremes) / (assignments + 1)

    observed = json.loads((HERE / "RESULTS.json").read_text(encoding="utf-8"))
    expected_primary = observed["primary"]
    expected_aggregate = observed["aggregate"]
    errors_by_stratum = np.zeros((6, 4), dtype=np.int64)
    shots_by_stratum = roots * shots
    raw_by_stratum = np.zeros(6, dtype=np.int64)
    for row in per_root:
        s = row["stratum_index"]
        errors_by_stratum[s] += np.asarray(row["arm_errors"], dtype=np.int64)
        raw_by_stratum[s] += row["raw_observable_errors"]

    assert sum(total_errors) == sum(expected_aggregate["arm_errors"])
    assert total_errors.tolist() == expected_aggregate["arm_errors"]
    assert total_observable == expected_aggregate["raw_observable_errors"]
    assert abs(primary_delta - float(expected_primary["delta_ler"])) < 1e-15
    assert np.allclose(primary_ci, expected_primary["root_stratified_bootstrap_95_ci"], atol=1e-15)
    assert signflip_p == expected_primary["two_sided_root_cluster_signflip_p"]
    assert extremes == expected_primary["signflip_extreme_assignments"]
    assert mcnemar_primary[0] == expected_primary["exact_shot_mcnemar_standard_only"]
    assert mcnemar_primary[1] == expected_primary["exact_shot_mcnemar_correlation_only"]

    per_stratum = []
    for s, label in enumerate(strata):
        stored_row = observed["per_stratum"][s]
        lers = (errors_by_stratum[s] / shots_by_stratum).tolist()
        delta = float(root_delta[s].mean())
        per_stratum.append({"stratum_index": s, "stratum": label, "shots": shots_by_stratum,
                            "raw_observable_errors": int(raw_by_stratum[s]),
                            "arm_errors": errors_by_stratum[s].tolist(), "arm_ler": lers,
                            "primary_correlated_minus_uncorrelated": delta,
                            "primary_standard_only": int(sum(x["standard_only_failures"] for x in per_root if x["stratum_index"] == s)),
                            "primary_correlation_only": int(sum(x["correlation_only_failures"] for x in per_root if x["stratum_index"] == s)),
                            "result_json_counts_match": errors_by_stratum[s].tolist() == [stored_row[f"{arm}_errors"] for arm in ARMS]})
        if errors_by_stratum[s].tolist() != [stored_row[f"{arm}_errors"] for arm in ARMS]:
            raise AssertionError(f"RESULTS.json per-stratum arm counts mismatch for {label}")

    summary = {
        "status": "PASS_INDEPENDENT_RECOMPUTATION",
        "method": "Rebuilt DEM/matcher predictions and recomputed residuals directly from saved NPZ; no analyzer/report functions imported",
        "coverage": {"strata": 6, "roots_per_stratum": roots, "roots": len(per_root),
                     "shots_per_root": shots, "paired_shots": len(per_root) * shots,
                     "checkpoint_count": len(checkpoint_hashes),
                     "prediction_bits_independently_checked": prediction_bits_checked,
                     "prediction_mismatches": 0},
        "dem_sha256": dem_hashes,
        "aggregate_arm_errors": total_errors.tolist(),
        "aggregate_arm_ler": (total_errors / (len(per_root) * shots)).tolist(),
        "raw_observable_errors": int(total_observable),
        "primary": {"estimand": "equal-stratum mean correlated pooled-fixed minus uncorrelated pooled-fixed LER",
                    "delta_ler": primary_delta, "bootstrap_95_ci": primary_ci,
                    "signflip_p_two_sided": signflip_p, "signflip_extremes": extremes,
                    "standard_only_failures": int(mcnemar_primary[0]),
                    "correlation_only_failures": int(mcnemar_primary[1]),
                    "prediction_disagreements": int(total_pair_pred_disagree[0, 1]),
                    "exact_mcnemar_p_descriptive": exact_mcnemar_p(*mcnemar_primary)},
        "pairwise_prediction_disagreement_matrix": total_pair_pred_disagree.tolist(),
        "pairwise_wrong_a_correct_b_matrix": total_pair_wrong.tolist(),
        "per_stratum": per_stratum,
        "comparisons_to_results_json": {"aggregate_counts_match": total_errors.tolist() == expected_aggregate["arm_errors"],
                                        "primary_delta_match": abs(primary_delta - expected_primary["delta_ler"]) < 1e-15,
                                        "primary_ci_match": bool(np.allclose(primary_ci, expected_primary["root_stratified_bootstrap_95_ci"], atol=1e-15)),
                                        "primary_p_match": signflip_p == expected_primary["two_sided_root_cluster_signflip_p"]},
        "per_root_csv_rows_verified": len(saved_root_rows),
        "per_root_csv_all_fields_match_recomputed_arrays": True,
        "checkpoint_sha256": checkpoint_hashes,
    }
    (HERE / "AGGREGATE_RECOMPUTATION.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    lines = ["# Independent raw-array recomputation", "",
             "Status: **PASS**. This checker does not import `analyze_correlation_pilot.py` or the runner reporting functions.", "",
             f"- Coverage: {len(per_root)} checkpoints; {len(per_root)*shots:,} paired shots.",
             f"- Decoder prediction bits independently checked: {prediction_bits_checked:,}; mismatches: 0.",
             f"- Per-root reporting CSV rows independently checked against arrays: {len(saved_root_rows)}; mismatches: 0.",
             f"- Arm residual errors in order {ARMS}: {total_errors.tolist()}.",
             f"- Raw observable errors: {total_observable:,}.",
             f"- Primary delta (correlated minus uncorrelated): {primary_delta:+.10f} LER.",
             f"- Root-stratified 95% bootstrap CI: [{primary_ci[0]:+.10f}, {primary_ci[1]:+.10f}].",
             f"- Root-cluster sign-flip p: {signflip_p:.10g} ({extremes:,}/{assignments:,} extreme assignments; add-one correction).",
             f"- Paired discordances: standard-only {mcnemar_primary[0]:,}; correlation-only {mcnemar_primary[1]:,}; total {sum(mcnemar_primary):,}.",
             f"- Exact shot-level McNemar p (descriptive): {exact_mcnemar_p(*mcnemar_primary):.10g}.", "",
             "The numerical values agree with `RESULTS.json`. This is an independent reconstruction from saved test arrays and decoder predictions; the run remains a development pilot, and the DEM's disjoint-error approximation remains a modeling limitation.", ""]
    (HERE / "AGGREGATE_RECOMPUTATION.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("status", "coverage", "aggregate_arm_errors", "primary")}, indent=2))


if __name__ == "__main__":
    main()
