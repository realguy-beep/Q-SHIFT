"""Independent raw-array scoring and prespecified Phase 2B statistics."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import binomtest

from decoder_bank import build_bank, decode_bank
from noise_model import MEMORY_BASES, REGIMES, build_circuit

P = Path(__file__).resolve().parent
ROOT = P.parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows):
    if not rows:
        raise ValueError(f"cannot write empty csv: {path}")
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def wilson(k: int, n: int, z: float = 1.959963984540054):
    if not n:
        return [None, None]
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, float(mid - half)), min(1.0, float(mid + half))]


def exact_mcnemar(candidate_only: int, baseline_only: int):
    n = int(candidate_only + baseline_only)
    if n == 0:
        return 1.0
    return float(binomtest(min(candidate_only, baseline_only), n, 0.5, alternative="two-sided").pvalue)


def holm(pvalues):
    p = np.asarray(pvalues, dtype=float)
    order = np.argsort(p)
    adjusted = np.empty_like(p)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, (len(p) - rank) * p[idx])
        adjusted[idx] = min(1.0, running)
    return adjusted.tolist()


def bootstrap_equal_strata(diffs_by_cell, rng, draws=100000, batch=10000):
    out = np.empty(draws, dtype=np.float64)
    for start in range(0, draws, batch):
        size = min(batch, draws - start)
        means = []
        for diffs in diffs_by_cell:
            ix = rng.integers(0, len(diffs), size=(size, len(diffs)))
            means.append(diffs[ix].mean(axis=1))
        out[start:start + size] = np.mean(means, axis=0)
    return [float(x) for x in np.quantile(out, [0.025, 0.975])]


def signflip_equal_strata(diffs_by_cell, rng, draws=100000, batch=10000):
    observed = float(np.mean([np.mean(x) for x in diffs_by_cell]))
    if all(np.all(np.asarray(x) == 0) for x in diffs_by_cell):
        return observed, 1.0
    extreme = 0
    completed = 0
    for start in range(0, draws, batch):
        size = min(batch, draws - start)
        cell_means = []
        for diffs in diffs_by_cell:
            signs = rng.integers(0, 2, size=(size, len(diffs)), dtype=np.int8) * 2 - 1
            cell_means.append((signs * np.asarray(diffs, dtype=np.float64)[None, :]).mean(axis=1))
        randomized = np.mean(cell_means, axis=0)
        extreme += int(np.count_nonzero(np.abs(randomized) >= abs(observed)))
        completed += size
    return observed, float((extreme + 1) / (completed + 1))


def load_and_verify():
    freeze = json.loads((P / "PRETEST_FREEZE.json").read_text(encoding="utf-8"))
    for rel, expected in freeze["files_sha256"].items():
        path = ROOT / rel
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"frozen pretest file hash mismatch: {rel}")
    selection = freeze["selected_models"]
    bank_by_basis = {b: build_bank(b, distance=3, rounds=5)[0] for b in MEMORY_BASES}
    records = []
    grouped = {(b, r): [] for b in MEMORY_BASES for r in REGIMES}
    for basis in MEMORY_BASES:
        for regime in REGIMES:
            for root in range(20):
                path = P / "data" / "heldout" / f"test_{basis}_{regime}_root{root:02d}.npz"
                with np.load(path, allow_pickle=False) as z:
                    d, y, pred = z["detectors"], z["observable"], z["predictions"]
                    seed = int(z["seed"])
                    if d.shape != (10000, 40) or d.dtype != np.uint8:
                        raise RuntimeError(f"bad detector data schema: {path.name} {d.shape}/{d.dtype}")
                    if y.shape != (10000,) or pred.shape != (3, 10000):
                        raise RuntimeError(f"bad labels/predictions schema: {path.name}")
                    if not set(np.unique(d)).issubset({0, 1}) or not set(np.unique(y)).issubset({0, 1}) or not set(np.unique(pred)).issubset({0, 1}):
                        raise RuntimeError(f"nonbinary values in {path.name}")
                    if int(z["basis_id"]) != MEMORY_BASES.index(basis) or int(z["regime_id"]) != REGIMES.index(regime):
                        raise RuntimeError(f"filename and metadata cell mismatch: {path.name}")
                    if int(z["root_index"]) != root:
                        raise RuntimeError(f"filename and metadata root mismatch: {path.name}")
                    expected_seed = int(freeze["seed_inventory"]["heldout"][MEMORY_BASES.index(basis) * 60 + REGIMES.index(regime) * 20 + root])
                    if seed != expected_seed:
                        raise RuntimeError(f"filename/seed manifest mismatch: {path.name}")
                    rebuilt = decode_bank(bank_by_basis[basis], d)
                    if not np.array_equal(pred, rebuilt):
                        raise RuntimeError(f"independent prediction re-decode mismatch: {path.name}")
                    err = pred ^ y[None, :]
                    a = int(selection[basis]["global_index"])
                    b = int(selection[basis]["per_regime_indices"][regime])
                    c = 1
                    # A/B/C are scored on the same detector and observable vectors.
                    a_err = err[a]
                    b_err = err[b]
                    c_err = err[c]
                    b_co = int(np.count_nonzero(b_err & ~a_err))
                    b_bo = int(np.count_nonzero(~b_err & a_err))
                    rootrec = {
                        "basis": basis, "regime": regime, "regime_index": REGIMES.index(regime),
                        "root_index": root, "seed": seed, "shots": len(y),
                        "global_decoder_index": a, "regime_decoder_index": b,
                        "global_fixed_errors": int(a_err.sum()), "regime_informed_errors": int(b_err.sum()),
                        "balanced_decoder_errors": int(c_err.sum()),
                        "B_minus_A_errors": int(b_err.sum() - a_err.sum()),
                        "B_minus_A_LER": float(np.mean(b_err) - np.mean(a_err)),
                        "B_candidate_only": b_co, "A_only": b_bo,
                        "B_prediction_disagreements_vs_A": int(np.count_nonzero(pred[b] != pred[a])),
                        "decoder_errors": [int(row.sum()) for row in err],
                        "sha256": sha256(path),
                    }
                    rootrec.update({f"decoder_{i}_errors": int(err[i].sum()) for i in range(3)})
                    rootrec.update({f"decoder_{i}_ler": float(np.mean(err[i])) for i in range(3)})
                    records.append(rootrec)
                    grouped[(basis, regime)].append({"record": rootrec, "detectors": d.copy(),
                                                     "observable": y.copy(), "predictions": pred.copy(),
                                                     "errors": err.copy()})
    if len(records) != 120 or sum(r["shots"] for r in records) != 1_200_000:
        raise RuntimeError(f"heldout coverage failure: roots={len(records)}, shots={sum(r['shots'] for r in records)}")
    return freeze, selection, records, grouped


def main():
    config = json.loads((P / "config.json").read_text(encoding="utf-8"))
    plan = json.loads((P / "STATISTICAL_PLAN.json").read_text(encoding="utf-8"))
    freeze, selection, root_records, grouped = load_and_verify()
    write_csv(P / "PER_ROOT_RESULTS.csv", root_records)

    per_cell = []
    diffs_BA = {}
    paired_comparisons = []
    disagreement_rows = []
    oracle_cells = []
    overall_errors = {"A_global_fixed": 0, "B_calibration_regime_informed": 0, "C_balanced": 0,
                      "retrospective_regime_oracle": 0, "retrospective_per_shot_oracle": 0}
    for basis in MEMORY_BASES:
        for regime in REGIMES:
            shots = 0
            model_errors = np.zeros(3, dtype=np.int64)
            a_co = np.zeros(3, dtype=np.int64)
            a_bo = np.zeros(3, dtype=np.int64)
            disagreement = np.zeros((3, 3), dtype=np.int64)
            pair_i_only = np.zeros((3, 3), dtype=np.int64)
            pair_j_only = np.zeros((3, 3), dtype=np.int64)
            oracle_per_shot = 0
            for item in grouped[(basis, regime)]:
                r, err, pred, y = item["record"], item["errors"], item["predictions"], item["observable"]
                shots += len(y)
                model_errors += err.sum(axis=1)
                oracle_per_shot += int(err.min(axis=0).sum())
                for i in range(3):
                    for j in range(3):
                        disagreement[i, j] += int(np.count_nonzero(pred[i] != pred[j]))
                        pair_i_only[i, j] += int(np.count_nonzero(err[i] & ~err[j]))
                        pair_j_only[i, j] += int(np.count_nonzero(err[j] & ~err[i]))
                aidx = int(selection[basis]["global_index"])
                for candidate in range(3):
                    a_co[candidate] += int(np.count_nonzero(err[candidate] & ~err[aidx]))
                    a_bo[candidate] += int(np.count_nonzero(~err[candidate] & err[aidx]))
            if shots != 200000:
                raise RuntimeError(f"wrong heldout shot count in {basis}/{regime}: {shots}")
            aidx = int(selection[basis]["global_index"])
            bidx = int(selection[basis]["per_regime_indices"][regime])
            hidx = int(np.argmin(model_errors))
            diff = np.asarray([r["B_minus_A_LER"] for r in root_records if r["basis"] == basis and r["regime"] == regime])
            diffs_BA[(basis, regime)] = diff
            rows = [r for r in root_records if r["basis"] == basis and r["regime"] == regime]
            a_errors = int(model_errors[aidx]); b_errors = int(model_errors[bidx]); c_errors = int(model_errors[1])
            b_cand_only = int(a_co[bidx]); b_a_only = int(a_bo[bidx])
            cell = {
                "basis": basis, "regime": regime, "shots": shots,
                "global_decoder_index": aidx, "regime_selected_decoder_index": bidx,
                "A_global_fixed_errors": a_errors, "A_global_fixed_ler": a_errors / shots,
                "B_regime_informed_errors": b_errors, "B_regime_informed_ler": b_errors / shots,
                "C_balanced_errors": c_errors, "C_balanced_ler": c_errors / shots,
                "B_minus_A_errors": b_errors - a_errors, "B_minus_A_ler": (b_errors - a_errors) / shots,
                "B_minus_A_root_mean": float(diff.mean()), "B_minus_A_root_sd": float(diff.std(ddof=1)),
                "B_minus_A_candidate_only": b_cand_only, "B_minus_A_A_only": b_a_only,
                "B_minus_A_exact_mcnemar_p_descriptive": exact_mcnemar(b_cand_only, b_a_only),
                "B_minus_A_paired_root_bootstrap95": None,
                "test_label_hindsight_regime_index": hidx,
                "test_label_hindsight_regime_errors": int(model_errors[hidx]),
                "test_label_per_shot_oracle_errors": int(oracle_per_shot),
                "decoder_errors": model_errors.tolist(),
                "decoder_ler": [float(x / shots) for x in model_errors],
                "decoder_wilson95": [wilson(int(x), shots) for x in model_errors],
                "prediction_disagreement_counts": disagreement.tolist(),
            }
            per_cell.append(cell)
            overall_errors["A_global_fixed"] += a_errors
            overall_errors["B_calibration_regime_informed"] += b_errors
            overall_errors["C_balanced"] += c_errors
            overall_errors["retrospective_regime_oracle"] += int(model_errors[hidx])
            overall_errors["retrospective_per_shot_oracle"] += int(oracle_per_shot)
            oracle_cells.append({"basis": basis, "regime": regime, "shots": shots,
                                 "hindsight_decoder_index": hidx, "hindsight_errors": int(model_errors[hidx]),
                                 "per_shot_oracle_errors": int(oracle_per_shot)})
            for i in range(3):
                for j in range(i + 1, 3):
                    disagreement_rows.append({"basis": basis, "regime": regime, "decoder_i": i,
                        "decoder_j": j, "shots": shots,
                        "prediction_disagreements": int(disagreement[i, j]),
                        "disagreement_rate": float(disagreement[i, j] / shots),
                        "i_only_errors_vs_j": int(pair_i_only[i, j]),
                        "j_only_errors_vs_i": int(pair_j_only[i, j])})
            # All 3 assumed decoders vs A; only the two non-identical policy indices
            # enter root-cluster multiple-comparison inference below.
            for candidate in range(3):
                co, bo = int(a_co[candidate]), int(a_bo[candidate])
                paired_comparisons.append({"basis": basis, "regime": regime, "candidate_decoder_index": candidate,
                    "baseline_global_index": aidx, "shots": shots,
                    "candidate_errors": int(model_errors[candidate]), "baseline_errors": a_errors,
                    "candidate_only": co, "baseline_only": bo,
                    "exact_mcnemar_p_shot_descriptive": exact_mcnemar(co, bo),
                    "prediction_disagreements_vs_baseline": int(disagreement[candidate, aidx]),
                    "root_cluster_p": None, "holm_p_family12": None})

    # Primary inferential calculations: resample/sign-flip independent roots inside cells.
    seed_inventory = freeze["seed_inventory"]
    bootstrap_rng = np.random.default_rng(int(seed_inventory["bootstrap"][0]))
    sign_rng = np.random.default_rng(int(seed_inventory["signflip"][0]))
    cell_diff_arrays = [diffs_BA[(b, r)] for b in MEMORY_BASES for r in REGIMES]
    primary_effect, primary_p = signflip_equal_strata(cell_diff_arrays, sign_rng, draws=100000)
    primary_ci = bootstrap_equal_strata(cell_diff_arrays, bootstrap_rng, draws=100000)
    per_basis_stats = []
    for basis in MEMORY_BASES:
        arrs = [diffs_BA[(basis, r)] for r in REGIMES]
        effect, p = signflip_equal_strata(arrs, sign_rng, draws=100000)
        ci = bootstrap_equal_strata(arrs, bootstrap_rng, draws=50000)
        per_basis_stats.append({"basis": basis, "effect_B_minus_A": effect, "p_raw": p, "ci95": ci})
    basis_holm = holm([x["p_raw"] for x in per_basis_stats])
    for row, adj in zip(per_basis_stats, basis_holm):
        row["holm_p_family2"] = adj

    cell_stats = []
    for cell in per_cell:
        arr = diffs_BA[(cell["basis"], cell["regime"])]
        effect, p = signflip_equal_strata([arr], sign_rng, draws=100000)
        ci = bootstrap_equal_strata([arr], bootstrap_rng, draws=50000)
        cell["B_minus_A_paired_root_signflip_p"] = p
        cell["B_minus_A_paired_root_bootstrap95"] = ci
        cell_stats.append({"basis": cell["basis"], "regime": cell["regime"],
                           "effect_B_minus_A": effect, "p_raw": p, "ci95": ci})
    cell_adj = holm([x["p_raw"] for x in cell_stats])
    for row, adj in zip(cell_stats, cell_adj):
        row["holm_p_family6"] = adj

    alternative_tests = []
    for item in paired_comparisons:
        if item["candidate_decoder_index"] == item["baseline_global_index"]:
            continue
        basis, regime, candidate, baseline = item["basis"], item["regime"], item["candidate_decoder_index"], item["baseline_global_index"]
        root_diffs = []
        for root in range(20):
            rec = next(r for r in root_records if r["basis"] == basis and r["regime"] == regime and r["root_index"] == root)
            root_diffs.append((rec["decoder_errors"][candidate] - rec["decoder_errors"][baseline]) / rec["shots"])
        effect, p = signflip_equal_strata([np.asarray(root_diffs)], sign_rng, draws=100000)
        item["root_cluster_effect"] = effect
        item["root_cluster_p"] = p
        alternative_tests.append(item)
    if len(alternative_tests) != 12:
        raise RuntimeError(f"expected 12 alternative model comparisons; got {len(alternative_tests)}")
    alternative_adj = holm([x["root_cluster_p"] for x in alternative_tests])
    for item, adj in zip(alternative_tests, alternative_adj):
        item["holm_p_family12"] = adj

    write_csv(P / "PER_REGIME_RESULTS.csv", per_cell)
    write_csv(P / "DECODER_DISAGREEMENT.csv", disagreement_rows)
    write_csv(P / "PAIRED_COMPARISONS.csv", paired_comparisons)
    stats = {
        "primary": {"effect_B_minus_A_equal_six_cell_mean": primary_effect,
                    "bootstrap95_ci": primary_ci, "two_sided_root_cluster_signflip_p": primary_p,
                    "bootstrap_draws": 100000, "signflip_draws": 100000,
                    "shots": 1200000, "roots": 120, "method": plan["primary_test"]},
        "per_memory_basis_secondary_family2": per_basis_stats,
        "per_cell_secondary_family6": cell_stats,
        "alternative_model_vs_global_fixed_family12": alternative_tests,
        "holm_method": "step-down Holm adjusted p-values; adjustment family sizes as predeclared",
        "exact_mcnemar_role": "shot-level descriptive only; root is the inferential unit",
    }
    write_json(P / "STATISTICAL_RESULTS.json", stats)
    oracle = {
        "status": "verified_from_saved_test_arrays",
        "overall_shots": 1200000,
        "calibration_selected_global_fixed_errors": overall_errors["A_global_fixed"],
        "calibration_selected_regime_informed_errors": overall_errors["B_calibration_regime_informed"],
        "balanced_fixed_errors": overall_errors["C_balanced"],
        "retrospective_hindsight_per_regime_errors": overall_errors["retrospective_regime_oracle"],
        "retrospective_per_shot_oracle_errors": overall_errors["retrospective_per_shot_oracle"],
        "hindsight_oracle_is_unattainable": True,
        "by_basis_regime": oracle_cells,
        "primary_B_minus_A": stats["primary"],
        "test_labels_used_for_selection": False,
    }
    for key in ("calibration_selected_global_fixed", "calibration_selected_regime_informed", "balanced_fixed",
                "retrospective_hindsight_per_regime", "retrospective_per_shot_oracle"):
        err = oracle[key + "_errors"]
        oracle[key + "_ler"] = err / 1_200_000
    oracle["B_minus_A_error_count"] = overall_errors["B_calibration_regime_informed"] - overall_errors["A_global_fixed"]
    oracle["B_minus_A_absolute_ler_difference"] = oracle["B_minus_A_error_count"] / 1_200_000
    write_json(P / "ORACLE_HEADROOM.json", oracle)

    findings = []
    findings += ["# Phase 2B Findings", "",
        "## Scope and design", "",
        "Phase 2B compared three equal-total gate-fault Pauli compositions in distance-3, five-round rotated surface-code Z- and X-memory circuits. For every basis/regime cell, 20 independent held-out roots of 10,000 paired shots were decoded by all three matching models (1,200,000 shots total). Decoder selection used separate calibration data; held-out regime labels and logical labels were not available to the selection rule.", "",
        "## Main result", "",
        f"The calibration-selected regime-informed comparator minus calibration-selected global fixed decoder was {primary_effect:+.6%} LER (95% root-stratified bootstrap CI [{primary_ci[0]:+.6%}, {primary_ci[1]:+.6%}], two-sided root-cluster sign-flip p={primary_p:.5g}). The corresponding total errors were {overall_errors['B_calibration_regime_informed']:,} for B and {overall_errors['A_global_fixed']:,} for A across {1_200_000:,} paired shots. B uses the known simulated regime identity and is a diagnostic, not a deployable adaptive decoder.", "",
        "The per-basis and six basis-regime estimates, root-level uncertainty, Holm-adjusted secondary tests, candidate-only failures, and exact descriptive McNemar tests are in `STATISTICAL_ANALYSIS.md`, `STATISTICAL_RESULTS.json`, and `PER_REGIME_RESULTS.csv`.", "",
        "## Decoder behavior and headroom", "",
        f"Calibration-selected global indices by memory basis: {json.dumps({b: selection[b]['global_index'] for b in MEMORY_BASES})}. Calibration-selected regime indices: {json.dumps({b: selection[b]['per_regime_indices'] for b in MEMORY_BASES}, sort_keys=True)}. The balanced fixed decoder made {overall_errors['C_balanced']:,} errors. The retrospective test-label per-regime oracle made {overall_errors['retrospective_regime_oracle']:,}, and the per-shot oracle made {overall_errors['retrospective_per_shot_oracle']:,}; both are optimistic, unattainable diagnostics and are not evidence of a practical policy.", "",
        "Paired decoder disagreement counts/rates by basis and regime are in `DECODER_DISAGREEMENT.csv`. The graph audit gives topology, weights, fault-ID mappings, and the documented channel-to-DEM approximation.", "",
        "## Interpretation and limitations", "",
        "The calibration and held-out data are independent RNG streams, and test predictions were independently regenerated from their saved detector arrays. The simulator samples categorical Pauli channels, while Stim's DEM conversion uses the documented `approximate_disjoint_errors=True` approximation required for arbitrary custom Pauli channels. PyMatching correlated decoding uses available DEM decompositions but cannot remove this approximation. The 10:1:1 bias is a controlled sensitivity assumption rather than a hardware estimate. No coherent errors, leakage, crosstalk across gates, non-Markovian drift, or within-circuit regime changes were tested. Results are specific to this circuit, probability, channel, and decoder family; they do not establish hardware performance or the value of a causal adaptive controller.", "",
        "The exploratory conclusion is determined by the reported estimates and uncertainty, not by the positive-or-negative sign alone. Any noise-model or decoder change after held-out analysis requires a new frozen evaluation."]
    (P / "PHASE2B_FINDINGS.md").write_text("\n".join(findings) + "\n", encoding="utf-8")

    stat_md = ["# Phase 2B Statistical Analysis", "",
        "## Frozen inference procedure", "",
        f"Primary estimand: equal-weight average of B−A across six basis-regime cells. The root is the independent unit (20 per cell). Two-sided paired sign-flip Monte Carlo used 100,000 assignments; the stratified percentile bootstrap used 100,000 resamples and a 95% interval. Secondary families were Holm-adjusted at sizes 2, 6, and 12. Exact shot-level McNemar tests are descriptive only.", "",
        "## Primary", "",
        f"B−A = {primary_effect:+.6%}; 95% CI [{primary_ci[0]:+.6%}, {primary_ci[1]:+.6%}]; p={primary_p:.6g}. B errors={overall_errors['B_calibration_regime_informed']:,}; A errors={overall_errors['A_global_fixed']:,}; paired shots=1,200,000.", "",
        "## By memory basis", "", "| Basis | B−A LER | Root-bootstrap 95% CI | Raw p | Holm p (2) |", "|---|---:|---:|---:|---:|"]
    for x in per_basis_stats:
        stat_md.append(f"| {x['basis']} | {x['effect_B_minus_A']:+.6%} | [{x['ci95'][0]:+.6%}, {x['ci95'][1]:+.6%}] | {x['p_raw']:.6g} | {x['holm_p_family2']:.6g} |")
    stat_md += ["", "## By basis and regime", "", "| Basis | Regime | B−A LER | 95% CI | Raw p | Holm p (6) |", "|---|---|---:|---:|---:|---:|"]
    for x in cell_stats:
        stat_md.append(f"| {x['basis']} | {x['regime']} | {x['effect_B_minus_A']:+.6%} | [{x['ci95'][0]:+.6%}, {x['ci95'][1]:+.6%}] | {x['p_raw']:.6g} | {x['holm_p_family6']:.6g} |")
    stat_md += ["", "## Alternative bank candidates versus calibration-selected global fixed", "", "| Basis | Regime | Candidate index | Effect LER | Root p | Holm p (12) | Candidate-only / baseline-only shots | McNemar p (descriptive) |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for x in alternative_tests:
        stat_md.append(f"| {x['basis']} | {x['regime']} | {x['candidate_decoder_index']} | {x['root_cluster_effect']:+.6%} | {x['root_cluster_p']:.6g} | {x['holm_p_family12']:.6g} | {x['candidate_only']} / {x['baseline_only']} | {x['exact_mcnemar_p_shot_descriptive']:.6g} |")
    stat_md += ["", "Shotwise intervals and McNemar p-values do not treat 1.2 million shots as independent experimental replicates; primary uncertainty is clustered by independent Stim root."]
    (P / "STATISTICAL_ANALYSIS.md").write_text("\n".join(stat_md) + "\n", encoding="utf-8")

    write_json(P / "PHASE2B_ANALYSIS_AUDIT.json", {
        "status": "PASS", "roots": len(root_records), "shots": sum(r["shots"] for r in root_records),
        "all_predictions_independently_redecoded": True, "frozen_source_and_protocol_hashes_pass": True,
        "per_root_and_cell_results_recomputed_from_raw_npz": True,
        "seed_metadata_checked": True, "heldout_labels_used_for_selection": False,
        "raw_heldout_hashes": {f"{r['basis']}_{r['regime']}_root{r['root_index']:02d}": r["sha256"] for r in root_records},
        "primary": stats["primary"],
    })
    print(f"ANALYSIS PASS: 120 roots, 1,200,000 shots; A={overall_errors['A_global_fixed']}; B={overall_errors['B_calibration_regime_informed']}; B-A={primary_effect:+.6%}; CI={primary_ci}; p={primary_p:.6g}")


if __name__ == "__main__":
    main()
