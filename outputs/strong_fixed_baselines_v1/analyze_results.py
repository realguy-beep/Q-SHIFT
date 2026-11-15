"""Descriptive root-cluster analysis of independently audited development results."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from experiment_core import atomic_json, sha256


ARMS = ["nominal_fixed", "pooled_detector_static", "safety_constrained_static", "adaptive_profile", "privileged_true_p"]


def stratified_bootstrap(root_differences: dict[float, np.ndarray], seed: int, reps: int) -> np.ndarray:
    ps = sorted(root_differences)
    rng = np.random.Generator(np.random.PCG64(int(seed)))
    result = np.empty(reps, dtype=np.float64)
    for start in range(0, reps, 2000):
        n = min(2000, reps - start)
        condition_means = []
        for p in ps:
            x = np.asarray(root_differences[p], dtype=np.float64)
            idx = rng.integers(0, x.size, size=(n, x.size))
            condition_means.append(x[idx].mean(axis=1))
        result[start:start+n] = np.mean(condition_means, axis=0)
    return result


def summarize_contrast(rows: list[dict], left: str, right: str, probs: list[float], seed: int, reps: int) -> dict:
    diffs = {}
    for p in probs:
        local = [r for r in rows if float(r["condition_p"]) == float(p)]
        diffs[float(p)] = np.asarray([r[f"{left}_ler"] - r[f"{right}_ler"] for r in local], dtype=np.float64)
        if diffs[float(p)].size < 2:
            raise ValueError(f"not enough roots for condition p={p}")
    weights = np.full(len(diffs), 1.0 / len(diffs))
    est = float(sum(weights[i] * diffs[p].mean() for i, p in enumerate(diffs)))
    boot = stratified_bootstrap(diffs, seed, reps)
    return {
        "left_minus_right": f"{left} - {right}",
        "condition_values": {str(p): {"mean": float(x.mean()), "root_sd": float(x.std(ddof=1)),
                                       "root_se": float(x.std(ddof=1) / np.sqrt(len(x))), "roots": int(len(x))}
                              for p, x in diffs.items()},
        "equal_condition_mean": est,
        "percentile_95_ci": [float(np.quantile(boot, .025)), float(np.quantile(boot, .975))],
        "bootstrap_replicates": int(reps),
        "interpretation": "descriptive development uncertainty; not confirmatory evidence",
    }


def main() -> None:
    run = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE / "run"
    audit_path = run / "INDEPENDENT_AUDIT.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("audit_status") != "PASS":
        raise RuntimeError("independent saved-array audit has not passed")
    cfg = json.loads((HERE / "experiment_config.json").read_text(encoding="utf-8"))
    inv = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
    seed = next(int(x["seed"]) for x in inv["streams"] if x["role"] == "bootstrap_results")
    reps = int(cfg["statistics"]["bootstrap_replicates"])
    rows = audit["per_root"]
    probs = list(map(float, cfg["circuit"]["probabilities"]))
    nonzero = probs[1:]
    contrasts = {
        "adaptive_minus_safety_static": summarize_contrast(rows, "adaptive_profile", "safety_constrained_static", nonzero, seed, reps),
        "adaptive_minus_pooled_static": summarize_contrast(rows, "adaptive_profile", "pooled_detector_static", nonzero, seed, reps),
        "adaptive_minus_nominal": summarize_contrast(rows, "adaptive_profile", "nominal_fixed", nonzero, seed, reps),
        "safety_static_minus_nominal": summarize_contrast(rows, "safety_constrained_static", "nominal_fixed", nonzero, seed, reps),
        "pooled_static_minus_nominal": summarize_contrast(rows, "pooled_detector_static", "nominal_fixed", nonzero, seed, reps),
        "adaptive_minus_privileged_reference": summarize_contrast(rows, "adaptive_profile", "privileged_true_p", nonzero, seed, reps),
    }
    p0_rows = [r for r in rows if float(r["condition_p"]) == 0.0]
    zero_safety = {}
    for arm in ("safety_constrained_static", "adaptive_profile", "pooled_detector_static", "privileged_true_p"):
        x = np.asarray([r[f"{arm}_ler"] - r["nominal_fixed_ler"] for r in p0_rows], dtype=np.float64)
        rng = np.random.Generator(np.random.PCG64(seed + len(zero_safety)))
        boots = np.empty(reps, dtype=np.float64)
        for start in range(0, reps, 2000):
            n = min(2000, reps - start)
            idx = rng.integers(0, len(x), size=(n, len(x)))
            boots[start:start+n] = x[idx].mean(axis=1)
        zero_safety[arm] = {"mean_excess_vs_nominal": float(x.mean()), "root_sd": float(x.std(ddof=1)),
                            "one_sided_95_upper": float(np.quantile(boots, .95)),
                            "harm_benchmark": float(cfg["statistics"]["zero_burst_harm_benchmark"]),
                            "descriptive_only": True}
    per_condition = []
    for p in probs:
        local = [r for r in rows if float(r["condition_p"]) == p]
        entry = {"condition_p": p, "roots": len(local), "shots": int(sum(r["shots"] for r in local))}
        for arm in ARMS:
            errors = sum(int(r[f"{arm}_errors"]) for r in local)
            shots = entry["shots"]
            entry[f"{arm}_errors"] = errors
            entry[f"{arm}_ler"] = errors / shots
            diffs = np.asarray([r[f"{arm}_ler"] - r["nominal_fixed_ler"] for r in local])
            entry[f"{arm}_minus_nominal_root_sd"] = float(diffs.std(ddof=1)) if len(diffs) > 1 else 0.0
        for arm in ARMS[1:]:
            entry[f"{arm}_candidate_only_vs_nominal"] = int(sum(r[f"{arm}_only_errors"] for r in local))
            entry[f"{arm}_nominal_only"] = int(sum(r[f"nominal_only_vs_{arm}"] for r in local))
            entry[f"{arm}_prediction_disagreements"] = int(sum(r[f"{arm}_prediction_disagreements"] for r in local))
        entry["adaptive_p_hat_mean"] = float(np.mean([r["p_hat"] for r in local]))
        entry["adaptive_p_hat_sd"] = float(np.std([r["p_hat"] for r in local], ddof=1)) if len(local) > 1 else 0.0
        per_condition.append(entry)

    report = {
        "status": "ANALYZED_AFTER_INDEPENDENT_AUDIT_PASS",
        "classification": "development_feasibility_not_confirmatory",
        "sealed_test_access": False,
        "total_unique_shots": audit["total_unique_shots_verified"],
        "final_paired_evaluation_shots": audit["final_paired_evaluation_shots"],
        "prediction_order": ARMS,
        "primary_descriptive_contrast": contrasts["adaptive_minus_safety_static"],
        "secondary_descriptive_contrasts": contrasts,
        "zero_burst_safety": zero_safety,
        "per_condition": per_condition,
        "per_root": rows,
        "safe_static_selection": audit["safe_static_selection"],
        "pooled_detector_static_p": audit["pooled_detector_static_p"],
        "uncertainty": "root-cluster stratified percentile bootstrap; 100,000 resamples; roots sampled within each generating condition; all effects descriptive and conditional on selected/calibrated models",
        "no_confirmatory_significance_claim": True,
    }
    outdir = HERE / "report"
    outdir.mkdir(parents=True, exist_ok=True)
    atomic_json(outdir / "RESULTS.json", report)
    with (outdir / "PER_ROOT.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    with (outdir / "PER_CONDITION.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(per_condition[0].keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(per_condition)
    md = ["# Strong fixed-baseline development v1 — results", "",
          "**Status:** independently audited development feasibility study; not confirmatory.", "",
          f"- Unique study shots verified: {audit['total_unique_shots_verified']:,}",
          f"- Paired final development shots: {audit['final_paired_evaluation_shots']:,}",
          f"- Final roots: {audit['final_evaluation_roots']}",
          f"- Pooled detector-static estimated burst p: {audit['pooled_detector_static_p']:.5f}",
          f"- Safety-constrained static p: {audit['safe_static_selection']['frozen']:.3f}", "",
          "## Paired final-development LER by condition", "",
          "| Burst probability | Shots | Nominal | Pooled static | Safety static | Adaptive | Privileged reference |", "|---:|---:|---:|---:|---:|---:|---:|"]
    for row in per_condition:
        md.append(f"| {row['condition_p']:.3f} | {row['shots']:,} | {row['nominal_fixed_ler']:.6%} | {row['pooled_detector_static_ler']:.6%} | {row['safety_constrained_static_ler']:.6%} | {row['adaptive_profile_ler']:.6%} | {row['privileged_true_p_ler']:.6%} |")
    ci = contrasts["adaptive_minus_safety_static"]
    md += ["", "## Primary descriptive comparison", "",
           f"Equal-condition adaptive − safety-static difference: **{ci['equal_condition_mean']:+.7%}**, root-bootstrap 95% interval [{ci['percentile_95_ci'][0]:+.7%}, {ci['percentile_95_ci'][1]:+.7%}].",
           "", "No confirmatory p-values are reported. The interval reflects root resampling within these five simulated conditions and is not a hardware or external-generalization claim.", "",
           "## Interpretation limits", "",
           "The safety-static baseline is selected using separate development labels and validated on a distinct p=0 subset; the pooled static baseline uses detector-only calibration. Adaptive uses per-root detector-only calibration. The privileged reference receives the true simulated p and is not deployable. All decoders score identical per-root final detector/observable arrays. Stage 5 evaluation material was not accessed.", "",
           f"Independent audit input SHA-256: `{sha256(audit_path)}`.", ""]
    (outdir / "RESULTS.md").write_text("\n".join(md), encoding="utf-8")
    hashes = {p.name: sha256(p) for p in outdir.iterdir() if p.is_file()}
    atomic_json(outdir / "REPORT_MANIFEST.json", {"files": hashes, "independent_audit_sha256": sha256(audit_path), "sealed_test_access": False})
    print(json.dumps({"status": report["status"], "primary": ci,
                      "results": str(outdir / "RESULTS.md")}, indent=2))


if __name__ == "__main__":
    main()
