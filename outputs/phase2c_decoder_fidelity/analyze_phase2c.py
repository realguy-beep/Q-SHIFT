from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
import time
from decimal import Decimal, localcontext
from pathlib import Path

import joblib
import numpy as np
import pymatching
import stim

HERE = Path(__file__).resolve().parent
P2B = HERE.parent / "phase2b_pauli_bias"
sys.path.insert(0, str(P2B))
from noise_model import MEMORY_BASES, REGIMES  # noqa: E402

DECODERS = ["pm_x", "pm_balanced", "pm_z", "ref_x", "ref_balanced", "ref_z"]
DISPLAY = {
    "pm_x": "Phase2B X-biased DEM",
    "pm_balanced": "Phase2B balanced DEM",
    "pm_z": "Phase2B Z-biased DEM",
    "ref_x": "Sampled posterior X-trained",
    "ref_balanced": "Sampled posterior balanced-trained",
    "ref_z": "Sampled posterior Z-trained",
}


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return [float("nan"), float("nan")]
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * np.sqrt((p * (1 - p) / n) + z * z / (4 * n * n)) / den
    return [float(max(0, center - half)), float(min(1, center + half))]


def exact_mcnemar(k, n):
    """Exact two-sided binomial p at 0.5, retaining decimal if float underflows."""
    if n == 0:
        return {"float": 1.0, "decimal": "1", "log10": 0.0}
    tail = min(int(k), int(n - k))
    numerator = min(2 * sum(math.comb(int(n), j) for j in range(tail + 1)), 1 << int(n))
    denominator = 1 << int(n)
    with localcontext() as ctx:
        ctx.prec = 50
        exact = Decimal(numerator) / Decimal(denominator)
        return {"float": float(exact), "decimal": format(exact, ".12E"), "log10": float(exact.log10())}


def paired(a, b, y):
    ea = np.asarray(a, dtype=np.uint8) ^ y
    eb = np.asarray(b, dtype=np.uint8) ^ y
    a_only = int(np.count_nonzero((ea == 1) & (eb == 0)))
    b_only = int(np.count_nonzero((ea == 0) & (eb == 1)))
    test = exact_mcnemar(a_only, a_only + b_only)
    return {"first_only_errors": a_only, "second_only_errors": b_only,
            "disagreements": a_only + b_only, "mcnemar_exact_two_sided_p": test["float"],
            "mcnemar_p_decimal": test["decimal"], "mcnemar_log10_p": test["log10"]}


def ece(prob, y, bins=10):
    p = np.asarray(prob, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    edges = np.linspace(0, 1, bins + 1)
    value = 0.0
    for i in range(bins):
        mask = (p >= edges[i]) & ((p <= edges[i + 1]) if i == bins - 1 else (p < edges[i + 1]))
        if np.any(mask):
            value += np.mean(mask) * abs(float(np.mean(p[mask]) - np.mean(y[mask])))
    return float(value)


def main():
    freeze = json.loads((HERE / "PILOT_FREEZE.json").read_text(encoding="utf-8"))
    for rel, expected in freeze["files_sha256"].items():
        path = HERE.parent.parent / Path(rel)
        if sha256(path) != expected:
            raise RuntimeError(f"frozen input hash mismatch during independent analysis: {rel}")
    selection = json.loads((HERE / "CALIBRATION_SELECTION.json").read_text(encoding="utf-8"))
    run = json.loads((HERE / "PILOT_RUN.json").read_text(encoding="utf-8"))
    if len(run["roots"]) != 24 or run["total_test_shots"] != 120000:
        raise RuntimeError("pilot root/shot coverage mismatch")

    matchers = {}
    forests = {}
    for basis in MEMORY_BASES:
        matchers[basis] = []
        for regime in REGIMES:
            dem = stim.DetectorErrorModel.from_file(str(HERE / "dems" / f"dem_{basis}_{regime}.dem"))
            matchers[basis].append(pymatching.Matching.from_detector_error_model(dem, enable_correlations=True))
            forests[(basis, regime)] = joblib.load(HERE / "models" / f"reference_{basis}_{regime}.joblib")

    per_root = []
    by_cell: dict[tuple[str, str], dict] = {}
    disagreement_rows = []
    posterior_acc = {name: {"p": [], "y": []} for name in DECODERS[3:]}
    candidate_error_counts = {name: 0 for name in DECODERS}
    candidate_shots = 0
    all_primary_root_diffs = []
    per_cell_diffs: dict[tuple[str, str], list[float]] = {}
    validation = {"expected_roots": 24, "verified_roots": 0,
                  "stored_prediction_redecodes_exact": True, "files": []}

    for basis in MEMORY_BASES:
        for regime in REGIMES:
            cell = (basis, regime)
            cell_idx = len(by_cell)
            idx = REGIMES.index(regime)
            global_ref = selection["global_fixed_reference_index_by_basis"][basis]
            regime_ref = selection["regime_informed_reference_index_by_cell"][f"{basis}/{regime}"]
            cell_rows = []
            for root_idx in range(4):
                path = HERE / "data" / "pilot" / f"pilot_{basis}_{regime}_root{root_idx:02}.npz"
                with np.load(path, allow_pickle=False) as z:
                    d = np.asarray(z["detectors"], dtype=np.uint8)
                    y = np.asarray(z["observable"], dtype=np.uint8)
                    pred = np.asarray(z["predictions"], dtype=np.uint8)
                    probs = np.asarray(z["reference_probabilities"], dtype=np.float64)
                    seed = int(z["seed"])
                    stored_basis = str(z["memory_basis"].item())
                    stored_regime = str(z["generating_regime"].item())
                    decoder_order = [str(x) for x in z["decoder_order"].tolist()]
                if stored_basis != basis or stored_regime != regime:
                    raise RuntimeError(f"filename-to-metadata mismatch in {path.name}")
                if d.shape != (5000, 40) or y.shape != (5000,) or pred.shape != (6, 5000) or probs.shape != (3, 5000):
                    raise RuntimeError(f"unexpected evidence shape in {path.name}: {d.shape}/{y.shape}/{pred.shape}/{probs.shape}")
                if decoder_order != DECODERS or not np.isin(pred, (0, 1)).all() or not np.isin(y, (0, 1)).all():
                    raise RuntimeError(f"binary/prediction order validation failed in {path.name}")
                recomputed = [np.asarray(m.decode_batch(d, enable_correlations=True), dtype=np.uint8)[:, 0]
                              for m in matchers[basis]]
                for candidate in REGIMES:
                    pp = forests[(basis, candidate)].predict(d)
                    recomputed.append(pp)
                recomputed = np.stack(recomputed)
                if not np.array_equal(recomputed, pred):
                    diff = np.count_nonzero(recomputed != pred, axis=1).tolist()
                    raise RuntimeError(f"saved predictions failed independent re-decode in {path.name}: {diff}")
                recomputed_probs = np.stack([forests[(basis, r)].predict_probability(d) for r in REGIMES])
                probability_redecode_max_abs = float(np.max(np.abs(probs - recomputed_probs)))
                # Parallel tree aggregation can differ by one floating-point
                # ulp on a second inference call. Binary predictions remain
                # checked exactly above; posterior values use a strict 1e-14
                # numerical tolerance.
                if not np.allclose(probs, recomputed_probs, atol=1e-14, rtol=1e-14):
                    raise RuntimeError(f"saved posterior probabilities failed independent recomputation in {path.name}")
                validation["verified_roots"] += 1
                validation["files"].append({"file": str(path.relative_to(HERE)), "sha256": sha256(path),
                                             "seed": seed, "shots": len(y), "prediction_redecode": "exact",
                                             "probability_redecode_max_abs_error": probability_redecode_max_abs,
                                             "probability_redecode_tolerance": 1e-14})

                phase2b_matched_idx = REGIMES.index(regime)
                comps = {
                    "phase2b_regime_matched": int(phase2b_matched_idx),
                    "phase2b_balanced_fixed": 1,
                    "reference_global_fixed": 3 + int(global_ref),
                    "reference_regime_informed": 3 + int(regime_ref),
                }
                errs = {name: int(np.count_nonzero(pred[i] ^ y)) for i, name in enumerate(DECODERS)}
                row = {"basis": basis, "generating_regime": regime, "root_index": root_idx,
                       "seed": seed, "shots": len(y), "raw_errors": int(y.sum()),
                       "phase2b_regime_matched_index": phase2b_matched_idx,
                       "reference_global_fixed_index": int(global_ref),
                       "reference_regime_informed_index": int(regime_ref)}
                for name, count in errs.items():
                    row[f"errors_{name}"] = count
                    row[f"ler_{name}"] = count / len(y)
                    candidate_error_counts[name] += count
                for name, dec_idx in comps.items():
                    row[f"errors_{name}"] = errs[DECODERS[dec_idx]]
                    row[f"ler_{name}"] = errs[DECODERS[dec_idx]] / len(y)
                row.update({
                    "primary_pair_regime_informed_wrong_fixed_correct": paired(pred[3 + regime_ref], pred[3 + global_ref], y)["first_only_errors"],
                    "primary_pair_fixed_wrong_regime_informed_correct": paired(pred[3 + regime_ref], pred[3 + global_ref], y)["second_only_errors"],
                })
                per_root.append(row)
                cell_rows.append((d, y, pred, probs, row))
                candidate_shots += len(y)
                for j, name in enumerate(DECODERS[3:]):
                    posterior_acc[name]["p"].append(probs[j])
                    posterior_acc[name]["y"].append(y)

                # Pairwise disagreement over the same shots for all six candidates.
                for i in range(len(DECODERS)):
                    for j in range(i + 1, len(DECODERS)):
                        disagreement_rows.append({"basis": basis, "generating_regime": regime,
                                                  "decoder_a": DECODERS[i], "decoder_b": DECODERS[j],
                                                  "shots": len(y),
                                                  "prediction_disagreements": int(np.count_nonzero(pred[i] != pred[j]))})

            by_cell[cell] = {"rows": cell_rows, "global_ref": int(global_ref), "regime_ref": int(regime_ref)}

    if validation["verified_roots"] != 24 or candidate_shots != 120000:
        raise RuntimeError("independent verification did not cover the complete pilot")
    validation["stored_prediction_redecodes_exact"] = True
    validation["total_test_shots"] = candidate_shots
    validation["status"] = "PASS: every stored detector, label, prediction, and posterior array independently checked"
    (HERE / "PILOT_EVIDENCE_AUDIT.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")

    result_rows = []
    cell_metrics = {}
    for (basis, regime), content in by_cell.items():
        ys = np.concatenate([x[1] for x in content["rows"]])
        preds = np.concatenate([x[2] for x in content["rows"]], axis=1)
        n = len(ys)
        for name, i in zip(DECODERS, range(6)):
            errors = int(np.count_nonzero(preds[i] ^ ys))
            result_rows.append({"basis": basis, "generating_regime": regime, "decoder": name,
                                "description": DISPLAY[name], "shots": n, "errors": errors,
                                "ler": errors / n, "wilson95_low": wilson(errors, n)[0],
                                "wilson95_high": wilson(errors, n)[1]})
        # Four named policies per cell.
        policies = {
            "phase2b_regime_matched": REGIMES.index(regime),
            "phase2b_balanced_fixed": 1,
            "reference_global_fixed": 3 + content["global_ref"],
            "reference_regime_informed": 3 + content["regime_ref"],
        }
        for policy, i in policies.items():
            errors = int(np.count_nonzero(preds[i] ^ ys))
            result_rows.append({"basis": basis, "generating_regime": regime, "decoder": policy,
                                "description": policy.replace("_", " "), "shots": n, "errors": errors,
                                "ler": errors / n, "wilson95_low": wilson(errors, n)[0],
                                "wilson95_high": wilson(errors, n)[1]})
        ref_i = 3 + content["regime_ref"]
        fixed_i = 3 + content["global_ref"]
        stat = paired(preds[ref_i], preds[fixed_i], ys)
        pm_i = REGIMES.index(regime)
        ref_vs_pm = paired(preds[ref_i], preds[pm_i], ys)
        matched_ref_i = 3 + REGIMES.index(regime)
        matched_ref_vs_pm = paired(preds[matched_ref_i], preds[pm_i], ys)
        root_rates = {policy: [float(x[4][f"ler_{policy}"]) for x in content["rows"]]
                      for policy in ["phase2b_regime_matched", "phase2b_balanced_fixed",
                                     "reference_global_fixed", "reference_regime_informed"]}
        cell_metrics[f"{basis}/{regime}"] = {
            "shots": n,
            "calibration_global_reference_index": content["global_ref"],
            "calibration_regime_reference_index": content["regime_ref"],
            "phase2b_regime_matched_errors": int(np.count_nonzero(preds[pm_i] ^ ys)),
            "phase2b_balanced_fixed_errors": int(np.count_nonzero(preds[1] ^ ys)),
            "reference_true_regime_candidate_errors": int(np.count_nonzero(preds[matched_ref_i] ^ ys)),
            "reference_global_fixed_errors": int(np.count_nonzero(preds[fixed_i] ^ ys)),
            "reference_regime_informed_errors": int(np.count_nonzero(preds[ref_i] ^ ys)),
            "reference_regime_minus_fixed_ler": float(np.mean((preds[ref_i] ^ ys).astype(float)) - np.mean((preds[fixed_i] ^ ys).astype(float))),
            "paired_regime_informed_vs_fixed": stat,
            "reference_regime_informed_vs_phase2b_matched": ref_vs_pm,
            "reference_true_regime_candidate_vs_phase2b_matched": matched_ref_vs_pm,
            "root_ler_mean_sd_min_max": {
                policy: {"mean": float(np.mean(values)), "sd_sample": float(np.std(values, ddof=1)),
                         "min": float(np.min(values)), "max": float(np.max(values))}
                for policy, values in root_rates.items()},
        }

    # Aggregate named estimands with equal weights across the six cells.
    aggregate = {}
    for policy in ["phase2b_regime_matched", "phase2b_balanced_fixed", "reference_global_fixed", "reference_regime_informed"]:
        rates = []
        errors = 0
        n_total = 0
        for (basis, regime), content in by_cell.items():
            ys = np.concatenate([x[1] for x in content["rows"]])
            preds = np.concatenate([x[2] for x in content["rows"]], axis=1)
            idx = {"phase2b_regime_matched": REGIMES.index(regime),
                   "phase2b_balanced_fixed": 1,
                   "reference_global_fixed": 3 + content["global_ref"],
                   "reference_regime_informed": 3 + content["regime_ref"]}[policy]
            e = int(np.count_nonzero(preds[idx] ^ ys))
            rates.append(e / len(ys))
            errors += e
            n_total += len(ys)
        aggregate[policy] = {"errors": errors, "shots": n_total,
                             "pooled_ler": errors / n_total,
                             "equal_cell_mean_ler": float(np.mean(rates))}

    comparison_specs = {
        "reference_global_fixed_vs_phase2b_balanced": ("reference_global_fixed", "phase2b_balanced_fixed"),
        "reference_regime_informed_vs_phase2b_regime_matched": ("reference_regime_informed", "phase2b_regime_matched"),
    }
    comparison_summary = {}
    for name, (first_policy, second_policy) in comparison_specs.items():
        first_errors = second_errors = first_only = second_only = 0
        for (basis, regime), content in by_cell.items():
            ys = np.concatenate([x[1] for x in content["rows"]])
            preds = np.concatenate([x[2] for x in content["rows"]], axis=1)
            idxs = {
                "reference_global_fixed": 3 + content["global_ref"],
                "reference_regime_informed": 3 + content["regime_ref"],
                "phase2b_balanced_fixed": 1,
                "phase2b_regime_matched": REGIMES.index(regime),
            }
            a = preds[idxs[first_policy]]
            b = preds[idxs[second_policy]]
            stat = paired(a, b, ys)
            first_errors += int(np.count_nonzero(a ^ ys))
            second_errors += int(np.count_nonzero(b ^ ys))
            first_only += stat["first_only_errors"]
            second_only += stat["second_only_errors"]
        disagreements = first_only + second_only
        comparison_summary[name] = {
            "first_policy": first_policy, "second_policy": second_policy,
            "first_errors": first_errors, "second_errors": second_errors,
            "first_minus_second_ler": (first_errors - second_errors) / candidate_shots,
            "first_only_errors": first_only, "second_only_errors": second_only,
            "disagreements": disagreements,
            "mcnemar_exact_two_sided_p": exact_mcnemar(first_only, disagreements)["float"],
            "mcnemar_p_decimal": exact_mcnemar(first_only, disagreements)["decimal"],
            "mcnemar_log10_p": exact_mcnemar(first_only, disagreements)["log10"],
        }

    # Root-cluster primary endpoint; preserve cell stratification in bootstrap.
    root_diffs: dict[tuple[str, str], np.ndarray] = {}
    for cell, content in by_cell.items():
        arr = []
        for _, y, pred, _, _ in content["rows"]:
            arr.append(float(np.mean(pred[3 + content["regime_ref"]] ^ y) -
                              np.mean(pred[3 + content["global_ref"]] ^ y)))
        root_diffs[cell] = np.asarray(arr, dtype=np.float64)
    observed = float(np.mean([x for arr in root_diffs.values() for x in arr]))
    rng_boot = np.random.default_rng(89300001)
    boot = np.empty(20000, dtype=np.float64)
    cells = list(root_diffs)
    for b in range(len(boot)):
        cell_effects = []
        for cell in cells:
            vals = root_diffs[cell]
            sample_ix = rng_boot.integers(0, len(vals), size=len(vals))
            cell_effects.append(float(np.mean(vals[sample_ix])))
        boot[b] = np.mean(cell_effects)
    ci = np.quantile(boot, [0.025, 0.975]).tolist()
    rng_sf = np.random.default_rng(89300002)
    diffs = np.concatenate([root_diffs[cell] for cell in cells])
    signs = rng_sf.choice(np.array([-1.0, 1.0]), size=(50000, len(diffs)))
    null = np.mean(signs * diffs[None, :], axis=1)
    sf_p = float((1 + np.count_nonzero(np.abs(null) >= abs(observed))) / (1 + len(null)))

    primary_shot_errors = []
    for cell, content in by_cell.items():
        for _, y, pred, _, _ in content["rows"]:
            primary_shot_errors.append(paired(pred[3 + content["regime_ref"]], pred[3 + content["global_ref"]], y))
    po = {k: sum(x[k] for x in primary_shot_errors) for k in ["first_only_errors", "second_only_errors", "disagreements"]}
    primary_mcnemar = exact_mcnemar(po["first_only_errors"], po["disagreements"])
    po["mcnemar_exact_two_sided_p"] = primary_mcnemar["float"]
    po["mcnemar_p_decimal"] = primary_mcnemar["decimal"]
    po["mcnemar_log10_p"] = primary_mcnemar["log10"]

    probability_metrics = {}
    for name, values in posterior_acc.items():
        p = np.concatenate(values["p"])
        y = np.concatenate(values["y"]).astype(np.float64)
        clipped = np.clip(p, 1e-12, 1 - 1e-12)
        prior = float(np.mean(y))
        prior_brier = prior * (1 - prior)
        prior_logloss = float(-(prior * np.log(prior) + (1 - prior) * np.log1p(-prior)))
        probability_metrics[name] = {
            "shots": len(y), "brier_score": float(np.mean((p - y) ** 2)),
            "log_loss_nats": float(np.mean(-(y * np.log(clipped) + (1 - y) * np.log1p(-clipped)))),
            "ece_10_equal_width": ece(p, y, 10),
            "mean_predicted_probability": float(np.mean(p)),
            "observed_logical_rate": float(np.mean(y)),
            "constant_prior_baseline_brier_score": prior_brier,
            "constant_prior_baseline_log_loss_nats": prior_logloss,
            "probability_threshold": 0.5,
        }

    # Pool pairwise disagreements within each cell for readable matrix CSV.
    disagreement_agg = {}
    for row in disagreement_rows:
        k = (row["basis"], row["generating_regime"], row["decoder_a"], row["decoder_b"])
        agg = disagreement_agg.setdefault(k, {"shots": 0, "prediction_disagreements": 0})
        agg["shots"] += row["shots"]
        agg["prediction_disagreements"] += row["prediction_disagreements"]
    with (HERE / "DECODER_DISAGREEMENT.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["basis", "generating_regime", "decoder_a", "decoder_b", "shots", "prediction_disagreements", "disagreement_rate"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for (basis, regime, a, b), v in disagreement_agg.items():
            w.writerow({"basis": basis, "generating_regime": regime, "decoder_a": a, "decoder_b": b,
                        **v, "disagreement_rate": v["prediction_disagreements"] / v["shots"]})

    def write_csv(name, rows):
        fields = list(dict.fromkeys(k for row in rows for k in row.keys()))
        with (HERE / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    write_csv("PILOT_RESULTS.csv", result_rows)
    write_csv("PER_ROOT_RESULTS.csv", per_root)
    primary = {"estimand": "equal-cell mean LER(reference regime-informed calibration selections) minus LER(reference global fixed calibration selection)",
               "difference": observed, "bootstrap_ci95_seed_cluster_stratified": ci,
               "bootstrap_replicates": 20000, "bootstrap_seed": 89300001,
               "paired_root_signflip_p_two_sided": sf_p, "signflip_replicates": 50000,
               "signflip_seed": 89300002,
               "paired_shot_discordances": po,
               "interpretation": "exploratory feasibility only; four roots per basis-regime cell"}
    results = {
        "phase": "Phase 2C decoder fidelity feasibility pilot",
        "status": "COMPLETE_EXPLORATORY_PILOT",
        "test_shots": candidate_shots,
        "root_count": validation["verified_roots"],
        "independent_raw_evidence_redecode": validation["status"],
        "calibration_selection": selection,
        "aggregate_policy_results": aggregate,
        "paired_policy_comparisons": comparison_summary,
        "per_cell": cell_metrics,
        "primary": primary,
        "posterior_probability_metrics_on_pilot": probability_metrics,
        "reference_model_file_sizes_bytes": {f"{b}/{r}": (HERE / "models" / f"reference_{b}_{r}.joblib").stat().st_size for b in MEMORY_BASES for r in REGIMES},
        "runtime": run["aggregate_runtime_seconds"],
        "pretest_frozen_hash": run["freeze_sha256"],
        "limitations": ["The full-circuit conditional posterior is not exactly enumerated.",
                        "Random-forest vote probabilities are finite-sample posterior surrogates; proper scores quantify predictive calibration, not a bound on posterior total-variation error.",
                        "Four independent test roots per cell are a small feasibility pilot.",
                        "The regime-informed policy is an oracle-like diagnostic that receives the known simulated regime; it is not online adaptation."]
    }
    (HERE / "PHASE2C_RESULTS.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"ANALYSIS COMPLETE: {candidate_shots} shots; primary={observed:.8f}, CI={ci}, signflip p={sf_p:.6g}; raw prediction audit PASS")


if __name__ == "__main__":
    main()

