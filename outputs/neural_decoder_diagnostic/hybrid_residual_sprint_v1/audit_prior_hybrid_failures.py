"""Read-only audit of the completed 750K development run's residual CNN outputs.

This script computes only descriptive diagnostics at the historical frozen
threshold. It does not search thresholds, change model selection, or access the
independent test allocation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OLD = REPO / "outputs" / "neural_decoder_diagnostic" / "autonomous_development" / "run"
REGIMES = ("x_biased", "balanced", "z_biased")
ROOTS = range(5)
THRESHOLD = 0.5  # historical threshold only; not optimized here


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def wilson(k: int, n: int, z: float = 1.959963984540054) -> list[float] | None:
    if n == 0:
        return None
    p = k / n
    den = 1 + z * z / n
    mid = p + z * z / (2 * n)
    rad = z * np.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return [float((mid - rad) / den), float((mid + rad) / den)]


def auc_rank(y: np.ndarray, p: np.ndarray) -> float | None:
    y = np.asarray(y, dtype=np.uint8)
    p = np.asarray(p, dtype=np.float64)
    n1 = int(y.sum())
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return None
    order = np.argsort(p, kind="mergesort")
    sorted_p = p[order]
    ranks = np.empty(len(p), dtype=np.float64)
    i = 0
    while i < len(p):
        j = i + 1
        while j < len(p) and sorted_p[j] == sorted_p[i]:
            j += 1
        ranks[order[i:j]] = (i + 1 + j) / 2.0  # average 1-based ranks
        i = j
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def qstats(x: np.ndarray) -> dict:
    x = np.asarray(x, dtype=np.float64)
    if not x.size:
        return {"n": 0, "mean": None, "median": None, "q10": None, "q90": None,
                "min": None, "max": None}
    q = np.quantile(x, [0.1, 0.5, 0.9])
    return {"n": int(x.size), "mean": float(x.mean()), "median": float(q[1]),
            "q10": float(q[0]), "q90": float(q[2]), "min": float(x.min()),
            "max": float(x.max())}


def main() -> None:
    manifest = json.loads((OLD / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
    if int(manifest.get("independent_test_access", -1)) != 0:
        raise RuntimeError("Historical run manifest does not establish zero independent-test access.")
    hashes = manifest["file_sha256"]
    verified_input_files = [{"path": "outputs/neural_decoder_diagnostic/autonomous_development/run/RUN_MANIFEST.json",
                             "sha256": sha(OLD / "RUN_MANIFEST.json")}]
    all_y, all_pm, all_pred, all_prob, all_target, all_corr, all_det = [], [], [], [], [], [], []
    regime_arrays = {r: {k: [] for k in ("y", "pm", "pred", "prob", "target", "corr", "det")}
                     for r in REGIMES}
    per_root, per_regime = [], []
    event_patterns = {"helpful": {}, "harmful": {}}
    selection_records = []

    for root in ROOTS:
        pred_name = f"root{root:02d}_residual_position_cnn_10000.npz"
        pred_path = OLD / "predictions" / pred_name
        pred_key = f"predictions\\{pred_name}"
        if hashes.get(pred_key) != sha(pred_path):
            raise RuntimeError(f"Saved prediction hash differs from historical manifest: {pred_name}")
        verified_input_files.append({"path": f"outputs/neural_decoder_diagnostic/autonomous_development/run/predictions/{pred_name}",
                                     "sha256": sha(pred_path)})
        sample_name = f"final_root_{root:02d}.npz"
        sample_path = OLD / "data" / sample_name
        sample_key = f"data\\{sample_name}"
        if hashes.get(sample_key) != sha(sample_path):
            raise RuntimeError(f"Saved sample hash differs from historical manifest: {sample_name}")
        verified_input_files.append({"path": f"outputs/neural_decoder_diagnostic/autonomous_development/run/data/{sample_name}",
                                     "sha256": sha(sample_path)})
        meta_path = sample_path.with_suffix(".json")
        sample_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (int(sample_meta.get("independent_test_access", -1)) != 0 or
                int(sample_meta.get("root_id", -1)) != root or
                sample_meta.get("generated_after_selection") is not True):
            raise RuntimeError(f"Development sample provenance mismatch: root {root}")
        if hashes.get(f"data\\{meta_path.name}") != sha(meta_path):
            raise RuntimeError(f"Saved sample metadata hash differs from manifest: {meta_path.name}")
        verified_input_files.append({"path": f"outputs/neural_decoder_diagnostic/autonomous_development/run/data/{meta_path.name}",
                                     "sha256": sha(meta_path)})

        selection_path = OLD / "selections" / f"root{root:02d}_residual_position_cnn_10000.json"
        selection_key = f"selections\\{selection_path.name}"
        if hashes.get(selection_key) != sha(selection_path):
            raise RuntimeError(f"Selection record hash differs from manifest: root {root}")
        verified_input_files.append({"path": f"outputs/neural_decoder_diagnostic/autonomous_development/run/selections/{selection_path.name}",
                                     "sha256": sha(selection_path)})
        selection = json.loads(selection_path.read_text(encoding="utf-8"))
        threshold = float(selection.get("threshold", -1))
        if threshold != THRESHOLD:
            raise RuntimeError(f"Unexpected historical threshold at root {root}: {threshold}")
        selection_records.append({"root": root, "threshold": threshold,
                                  "temperature": selection.get("temperature"),
                                  "best_epoch": selection.get("best_epoch")})

        with np.load(pred_path, allow_pickle=False) as zpred, np.load(sample_path, allow_pickle=False) as zsample:
            root_counts = {"root": root, "shots": 0, "pymatching_errors": 0,
                           "hybrid_errors": 0, "helpful": 0, "harmful": 0,
                           "corrections": 0}
            for regime in REGIMES:
                y = zpred[f"observable__{regime}"].astype(np.uint8)
                pm = zpred[f"pymatching__{regime}"].astype(np.uint8)
                pred = zpred[f"prediction__{regime}"].astype(np.uint8)
                prob = zpred[f"probability__{regime}"].astype(np.float64)
                d = zsample[f"final__{regime}__detectors"].astype(np.uint8)
                y_source = zsample[f"final__{regime}__observable"].astype(np.uint8)
                pm_source = zsample[f"final__{regime}__pymatching"].astype(np.uint8)
                if (len(y) != 10000 or d.shape != (10000, 40) or
                        not np.array_equal(y, y_source) or not np.array_equal(pm, pm_source)):
                    raise RuntimeError(f"Prediction/data shot pairing failed for root {root}/{regime}")
                if any(np.any((a != 0) & (a != 1)) for a in (y, pm, pred, d)):
                    raise RuntimeError(f"Non-binary saved labels/predictions for root {root}/{regime}")
                if not np.isfinite(prob).all() or np.any((prob < 0) | (prob > 1)):
                    raise RuntimeError(f"Invalid residual probabilities for root {root}/{regime}")
                residual_truth = y ^ pm
                corrections = pred ^ pm
                if not np.array_equal(pred, pm ^ (prob >= threshold).astype(np.uint8)):
                    raise RuntimeError(f"Stored predictions do not match frozen threshold at root {root}/{regime}")
                pm_error = pm ^ y
                hybrid_error = pred ^ y
                helpful = corrections.astype(bool) & pm_error.astype(bool)
                harmful = corrections.astype(bool) & ~pm_error.astype(bool)
                if not np.array_equal(hybrid_error, pm_error ^ corrections):
                    raise RuntimeError(f"XOR correction convention failed at root {root}/{regime}")

                weights = d.sum(axis=1)
                for label, mask in (("helpful", helpful), ("harmful", harmful)):
                    for idx in np.flatnonzero(mask):
                        signature = np.packbits(d[idx], bitorder="little").tobytes().hex()
                        event_patterns[label][signature] = event_patterns[label].get(signature, 0) + 1
                n = len(y)
                row = {"root": root, "regime": regime, "shots": n,
                    "pymatching_errors": int(pm_error.sum()), "hybrid_errors": int(hybrid_error.sum()),
                    "corrections": int(corrections.sum()), "helpful": int(helpful.sum()),
                    "harmful": int(harmful.sum()), "candidate_only": int(harmful.sum()),
                    "pymatching_only": int(helpful.sum()),
                    "probability_brier_residual_target": float(np.mean((prob - residual_truth) ** 2)),
                    "residual_target_positives": int(residual_truth.sum()),
                    "residual_target_recall": float(helpful.sum() / residual_truth.sum()) if residual_truth.sum() else None,
                    "correction_precision": float(helpful.sum() / corrections.sum()) if corrections.sum() else None,
                    "helpful_probability": qstats(prob[helpful]), "harmful_probability": qstats(prob[harmful]),
                    "helpful_syndrome_weight": qstats(weights[helpful]),
                    "harmful_syndrome_weight": qstats(weights[harmful]),
                    "residual_auc_diagnostic": auc_rank(residual_truth, prob)}
                per_regime.append(row)
                for k in ("shots", "pymatching_errors", "hybrid_errors", "helpful", "harmful", "corrections"):
                    root_counts[k] += row[k]
                all_y.append(y); all_pm.append(pm); all_pred.append(pred); all_prob.append(prob)
                all_target.append(residual_truth); all_corr.append(corrections); all_det.append(d)
                for key, value in (("y", y), ("pm", pm), ("pred", pred), ("prob", prob),
                                   ("target", residual_truth), ("corr", corrections), ("det", d)):
                    regime_arrays[regime][key].append(value)
            root_counts["paired_delta_errors"] = root_counts["hybrid_errors"] - root_counts["pymatching_errors"]
            root_counts["paired_delta_ler"] = root_counts["paired_delta_errors"] / root_counts["shots"]
            per_root.append(root_counts)

    y = np.concatenate(all_y)
    pm = np.concatenate(all_pm)
    pred = np.concatenate(all_pred)
    prob = np.concatenate(all_prob)
    target = np.concatenate(all_target)
    corr = np.concatenate(all_corr).astype(bool)
    det = np.concatenate(all_det)
    pm_errors = pm ^ y
    hybrid_errors = pred ^ y
    helpful = corr & pm_errors.astype(bool)
    harmful = corr & ~pm_errors.astype(bool)
    if (len(y), int(pm_errors.sum()), int(hybrid_errors.sum()), int(helpful.sum()), int(harmful.sum())) != (150000, 653, 689, 13, 49):
        raise RuntimeError("Independent aggregate did not reproduce the known 150k-shot paired counts.")

    unique_help = len(event_patterns["helpful"])
    unique_harm = len(event_patterns["harmful"])
    pattern_overlap = len(set(event_patterns["helpful"]) & set(event_patterns["harmful"]))
    by_regime_summary = []
    for regime in REGIMES:
        ra = {k: np.concatenate(v) for k, v in regime_arrays[regime].items()}
        r_helpful = ra["corr"].astype(bool) & (ra["pm"] ^ ra["y"]).astype(bool)
        r_harmful = ra["corr"].astype(bool) & ~(ra["pm"] ^ ra["y"]).astype(bool)
        r_pm_errors = ra["pm"] ^ ra["y"]
        r_hybrid_errors = ra["pred"] ^ ra["y"]
        by_regime_summary.append({
            "regime": regime, "shots": int(len(ra["y"])),
            "pymatching_errors": int(r_pm_errors.sum()), "hybrid_errors": int(r_hybrid_errors.sum()),
            "pymatching_ler": float(r_pm_errors.mean()), "hybrid_ler": float(r_hybrid_errors.mean()),
            "paired_delta_ler": float(r_hybrid_errors.mean() - r_pm_errors.mean()),
            "corrections": int(ra["corr"].sum()), "helpful": int(r_helpful.sum()),
            "harmful": int(r_harmful.sum()),
            "correction_precision": float(r_helpful.sum() / ra["corr"].sum()) if ra["corr"].sum() else None,
            "residual_target_positives": int(ra["target"].sum()),
            "residual_recall": float(r_helpful.sum() / ra["target"].sum()) if ra["target"].sum() else None,
            "probability_auc_diagnostic": auc_rank(ra["target"], ra["prob"]),
            "probability_brier": float(np.mean((ra["prob"] - ra["target"]) ** 2)),
        })
    edges = np.linspace(0, 1, 11)
    bins = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (prob >= lo) & ((prob < hi) if hi < 1 else (prob <= hi))
        if mask.any():
            bins.append({"low": float(lo), "high": float(hi), "n": int(mask.sum()),
                         "mean_probability": float(prob[mask].mean()),
                         "observed_residual_rate": float(target[mask].mean())})
    summary = {
        "status": "verified descriptive audit of historical development predictions",
        "independent_test_access": 0,
        "historical_run_manifest_sha256": sha(OLD / "RUN_MANIFEST.json"),
        "historical_run_test_access": manifest["independent_test_access"],
        "verified_input_files": verified_input_files,
        "coverage": {"roots": len(per_root), "regimes": len(REGIMES), "shots": len(y),
                     "shots_per_root_regime": 10000, "paired_evaluation_samples": True},
        "frozen_threshold": THRESHOLD,
        "selected_models": selection_records,
        "aggregate": {"pymatching_errors": int(pm_errors.sum()), "hybrid_errors": int(hybrid_errors.sum()),
            "pymatching_ler": float(pm_errors.mean()), "hybrid_ler": float(hybrid_errors.mean()),
            "absolute_ler_difference": float(hybrid_errors.mean() - pm_errors.mean()),
            "residual_target_positives": int(target.sum()), "residual_target_prevalence": float(target.mean()),
            "corrections_proposed": int(corr.sum()), "helpful_corrections": int(helpful.sum()),
            "harmful_corrections": int(harmful.sum()), "correction_precision": float(helpful.sum() / corr.sum()),
            "correction_precision_wilson95": wilson(int(helpful.sum()), int(corr.sum())),
            "residual_recall": float(helpful.sum() / target.sum()),
            "residual_recall_wilson95": wilson(int(helpful.sum()), int(target.sum())),
            "unrecovered_pymatching_errors": int(target.sum() - helpful.sum()),
            "candidate_only_equals_harmful": True, "pymatching_only_equals_helpful": True,
            "residual_probability_auc_diagnostic": auc_rank(target, prob),
            "residual_probability_brier": float(np.mean((prob - target) ** 2)),
            "residual_probability_mean": float(prob.mean()),
            "p_h_given_helpful": qstats(prob[helpful]), "p_h_given_harmful": qstats(prob[harmful]),
            "syndrome_weight_helpful": qstats(det.sum(axis=1)[helpful]),
            "syndrome_weight_harmful": qstats(det.sum(axis=1)[harmful]),
            "distinct_syndromes_helpful": unique_help, "distinct_syndromes_harmful": unique_harm,
            "syndrome_patterns_shared_between_helpful_and_harmful": pattern_overlap,
            "fixed_width_reliability_bins": bins},
        "per_root": per_root, "per_regime": per_regime,
        "by_regime_summary": by_regime_summary,
        "interpretation_limit": "The final-development arrays are used only for a retrospective failure audit at the already frozen 0.5 threshold. These outcomes are not used to select the new sprint's methods, weights, thresholds, or policies. The 13 helpful corrections are too few for stable mechanism claims; syndrome associations are descriptive.",
    }
    out = HERE / "prior_hybrid_audit"
    out.mkdir(parents=True, exist_ok=True)
    output_path = out / "FAILURE_AUDIT.json"
    output_path.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    root_deltas = np.asarray([x["paired_delta_ler"] for x in per_root], dtype=np.float64)
    root_mean = float(root_deltas.mean())
    root_half = float(2.7764451051977987 * root_deltas.std(ddof=1) / np.sqrt(len(root_deltas)))
    observed_stat = abs(float(root_deltas.sum()))
    sign_stats = []
    for mask in range(1 << len(root_deltas)):
        signs = np.asarray([1.0 if (mask >> i) & 1 else -1.0 for i in range(len(root_deltas))])
        sign_stats.append(abs(float(np.sum(signs * root_deltas))))
    sign_p = float(np.mean(np.asarray(sign_stats) >= observed_stat - 1e-15))
    a = summary["aggregate"]
    lines = [
        "# Retrospective audit of the previous hybrid residual CNN", "",
        "**Scope:** read-only, descriptive audit of the already completed 750K development run. It verifies the frozen threshold and prediction pairing; no threshold is searched or changed. The independent test and its seed/sample files were not accessed.", "",
        f"Historical run manifest SHA-256: `{summary['historical_run_manifest_sha256']}`. Independent-test access in that manifest: `{summary['historical_run_test_access']}`.", "",
        "## Paired outcome", "",
        "| Measure | Verified value |", "|---|---:|",
        f"| Paired final-development shots | {len(y):,} |",
        f"| PyMatching logical errors / LER | {a['pymatching_errors']:,} / {100*a['pymatching_ler']:.5f}% |",
        f"| Hybrid logical errors / LER | {a['hybrid_errors']:,} / {100*a['hybrid_ler']:.5f}% |",
        f"| Difference (hybrid minus PyMatching) | {100*a['absolute_ler_difference']:+.5f} percentage points |",
        f"| Residual corrections proposed at frozen threshold 0.5 | {a['corrections_proposed']} |",
        f"| Helpful / harmful corrections | {a['helpful_corrections']} / {a['harmful_corrections']} |",
        f"| Correction precision (Wilson 95% interval) | {100*a['correction_precision']:.1f}% ([{100*a['correction_precision_wilson95'][0]:.1f}%, {100*a['correction_precision_wilson95'][1]:.1f}%]) |",
        f"| Residual recall | {100*a['residual_recall']:.2f}% ([{100*a['residual_recall_wilson95'][0]:.2f}%, {100*a['residual_recall_wilson95'][1]:.2f}%]) |",
        f"| Residual-target prevalence | {100*a['residual_target_prevalence']:.4f}% ({a['residual_target_positives']} / {len(y):,}) |",
        f"| Probability ranking AUC / Brier score | {a['residual_probability_auc_diagnostic']:.4f} / {a['residual_probability_brier']:.6f} |", "",
        "The hybrid worsened the paired total by 36 errors: 49 false residual corrections introduced errors, while 13 corrected PyMatching errors. It left 640 of 653 PyMatching residual-error labels uncorrected.", "",
        "## Regime and root distribution", "",
        "| Generating regime | Shots | PyMatching errors | Hybrid errors | Helpful | Harmful | Paired LER difference |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for rr in by_regime_summary:
        lines.append(f"| {rr['regime']} | {rr['shots']:,} | {rr['pymatching_errors']} | {rr['hybrid_errors']} | {rr['helpful']} | {rr['harmful']} | {100*rr['paired_delta_ler']:+.4f} pp |")
    lines += ["", "| Root | PM errors | Hybrid errors | Helpful | Harmful | Paired error difference |", "|---:|---:|---:|---:|---:|---:|"]
    for rr in per_root:
        lines.append(f"| {rr['root']} | {rr['pymatching_errors']} | {rr['hybrid_errors']} | {rr['helpful']} | {rr['harmful']} | {rr['paired_delta_errors']:+d} |")
    lines += ["", f"Across five roots, the mean paired difference was {100*root_mean:+.5f} percentage points (descriptive root-t 95% interval [{100*(root_mean-root_half):+.5f}, {100*(root_mean+root_half):+.5f}]); exact two-sided root sign-flip p={sign_p:.4f}. With five clusters, inferential resolution is coarse.", "",
        "## Confidence and syndrome diagnostics", "",
        f"The mean saved probability among helpful corrections was {a['p_h_given_helpful']['mean']:.3f}; among harmful corrections it was {a['p_h_given_harmful']['mean']:.3f}. Thus the 0.5 tail did not separate useful from harmful events. AUC of 0.941 describes broad ranking over all scores; it does not imply that the operating tail is safe.", "",
        f"Helpful corrections involved {a['distinct_syndromes_helpful']} distinct detector patterns among 13 events; harmful corrections involved {a['distinct_syndromes_harmful']} among 49. No pattern appeared in both groups in this finite sample. Median detector-event count was {a['syndrome_weight_helpful']['median']:.1f} for helpful and {a['syndrome_weight_harmful']['median']:.1f} for harmful events, with overlapping ranges. These sparse descriptive patterns do not establish a syndrome-level mechanism.", "",
        "| Frozen probability bin | N | Mean probability | Observed residual rate |", "|---|---:|---:|---:|"]
    for b in a["fixed_width_reliability_bins"]:
        if b["low"] >= 0.5:
            lines.append(f"| [{b['low']:.1f}, {b['high']:.1f}{']' if b['high'] == 1 else ')'} | {b['n']} | {b['mean_probability']:.3f} | {100*b['observed_residual_rate']:.1f}% |")
    lines += ["", "## Interpretation and use", "",
        "Confirmed diagnosis: the residual target is rare, score ranking contains signal, but the frozen decision tail is poorly selective; 79.0% of attempted residual corrections were harmful. The probabilities of harmful and helpful corrections overlap substantially. The small helpful count and five-root design do not support regime-specific thresholds or a causal syndrome explanation.", "",
        "This audit is retrospective and uses the previous final-development outcomes only to explain that prior run. Its findings were not used to alter the new sprint's frozen configuration, candidates, threshold grids, gates, seeds, or primary endpoint. The new sprint still requires execution in the user's PowerShell because the managed environment did not retain its detached child process.", "",
        f"Machine-readable results and per-root/per-regime tables: `prior_hybrid_audit/FAILURE_AUDIT.json`. Recompute: `python outputs/neural_decoder_diagnostic/hybrid_residual_sprint_v1/audit_prior_hybrid_failures.py`.", ""]
    (out / "FAILURE_ANALYSIS_SUPPLEMENT.md").write_text("\n".join(lines), encoding="utf-8")
    audit_manifest = {"status": "read-only historical development-data audit",
        "independent_test_access": 0,
        "historical_run_manifest_sha256": sha(OLD / "RUN_MANIFEST.json"),
        "files": [
            {"path": "../audit_prior_hybrid_failures.py", "sha256": sha(Path(__file__).resolve())},
            {"path": "FAILURE_AUDIT.json", "sha256": sha(output_path)},
            {"path": "FAILURE_ANALYSIS_SUPPLEMENT.md", "sha256": sha(out / "FAILURE_ANALYSIS_SUPPLEMENT.md")},
        ],
        "input_file_count": len(verified_input_files),
        "input_files": verified_input_files}
    (out / "MANIFEST.json").write_text(json.dumps(audit_manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output_path), "aggregate": summary["aggregate"],
                      "by_regime_summary": by_regime_summary, "per_root": per_root}, indent=2))


if __name__ == "__main__":
    main()
