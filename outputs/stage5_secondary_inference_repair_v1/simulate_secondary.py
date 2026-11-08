"""Prospective design-only validation of finite-envelope secondary p-values."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
import time
from pathlib import Path

import numpy as np
import scipy

from stage5_secondary_stats import (conservative_cutoff, dkw_epsilon, envelope_p, holm_reject,
                                    wilson, wilson_one_sided_simultaneous)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CFG = json.loads((HERE / "DESIGN_CONFIG.json").read_text(encoding="utf-8"))
INV = json.loads((HERE / "STAGE5_SECONDARY_REPAIR_SEED_INVENTORY.json").read_text(encoding="utf-8"))
FAMILIES = CFG["families"]
SCENARIOS = [(f, q) for f in FAMILIES for q in CFG["variability_multipliers"]]
SEEDS = {x["role"]: x["seed"] for x in INV["streams"]}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def draw_standardized(rng: np.random.Generator, name: str, shape: tuple[int, ...]) -> np.ndarray:
    if name == "normal":
        return rng.standard_normal(shape)
    if name == "student_t5":
        return rng.standard_t(5, size=shape) / math.sqrt(5.0 / 3.0)
    if name == "student_t3":
        return rng.standard_t(3, size=shape) / math.sqrt(3.0)
    if name == "lognormal_sigma1":
        raw = rng.lognormal(0.0, 1.0, size=shape)
        return (raw - math.exp(0.5)) / math.sqrt((math.e - 1.0) * math.e)
    if name == "zero_inflated65_normal":
        zeros = rng.random(size=shape) < 0.65
        normal = rng.standard_normal(shape) / math.sqrt(0.35)
        return np.where(zeros, 0.0, normal)
    if name == "tied_asymmetric65":
        u = rng.random(size=shape)
        q, pl, ph = 0.35, 0.28, 0.07
        cv = 1.0 / q - 0.0
        low = -math.sqrt(cv * (ph / q) / (pl / q))
        high = math.sqrt(cv * (pl / q) / (ph / q))
        return np.where(u < 0.65, 0.0, np.where(u < 0.93, low, high))
    raise ValueError(f"unknown root-effect family: {name}")


def draw_mean_sd(rng: np.random.Generator, name: str, replicates: int, n: int, columns: int, batch_size: int) -> tuple[np.ndarray, np.ndarray]:
    means = np.empty((replicates, columns), dtype=np.float64)
    sds = np.empty_like(means)
    for start in range(0, replicates, batch_size):
        stop = min(start + batch_size, replicates)
        sample = draw_standardized(rng, name, (stop - start, n, columns))
        means[start:stop] = np.mean(sample, axis=1, dtype=np.float64)
        sds[start:stop] = np.std(sample, axis=1, ddof=1, dtype=np.float64)
    return means, sds


def centered_t(mean: np.ndarray, sd: np.ndarray, n: int) -> np.ndarray:
    out = np.empty_like(mean)
    good = sd > 0
    out[good] = math.sqrt(n) * mean[good] / sd[good]
    out[~good] = np.where(mean[~good] < 0, -np.inf, np.inf)
    return out


def upper_from_t(mean: np.ndarray, sd: np.ndarray, n: int, cutoff: float) -> np.ndarray:
    # U = sample_mean - cutoff * sample_SD/sqrt(n); coverage iff T >= cutoff.
    return mean - cutoff * sd / math.sqrt(n)


def holm_family_false_discoveries(p: np.ndarray, true_null_mask: np.ndarray) -> np.ndarray:
    rejected = holm_reject(p, float(CFG["holm_alpha"]))
    return np.any(rejected & true_null_mask[None, :], axis=1)


def binomial_summary(k: int, n: int, cells: int) -> dict:
    lo, hi = wilson_one_sided_simultaneous(k, n, cells, CFG["mc_confidence"])
    point_lo, point_hi = wilson(k, n, CFG["mc_confidence"])
    return {"successes": int(k), "trials": int(n), "rate": k / n,
            "pointwise_wilson95": [point_lo, point_hi],
            "simultaneous_one_sided_wilson95": [lo, hi]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true", help="deterministic 1,000-replicate smoke test only")
    parser.add_argument("--full", action="store_true", help="run the frozen design validation")
    args = parser.parse_args()
    if args.preflight == args.full:
        parser.error("choose exactly one of --preflight or --full")
    n = int(CFG["n_roots_per_condition"])
    reps = 1000 if args.preflight else int(CFG["validation_replicates_per_condition_family_scale"])
    cal_n = 10000 if args.preflight else int(CFG["calibration_replicates_per_family"])
    eps = dkw_epsilon(cal_n, len(FAMILIES), float(CFG["total_dkw_failure_probability"]))
    calrefs = []
    calmeta = []
    start = time.time()
    for family in FAMILIES:
        rng = np.random.Generator(np.random.PCG64(SEEDS[f"calibration:{family['name']}"]))
        m, s = draw_mean_sd(rng, family["distribution"], cal_n, n, 1, int(CFG["batch_size"]))
        t = centered_t(m, s, n)[:, 0]
        t.sort()
        calrefs.append(t)
        calmeta.append({"family": family["name"], "n": cal_n, "sha256_sorted_t": sha256_bytes(t.tobytes())})
    alphas = list(CFG["holm_steps"])
    cutoffs = {str(a): conservative_cutoff(calrefs, eps, float(a)) for a in alphas}
    sim_cutoff = cutoffs[str(float(CFG["holm_alpha"]) / 4.0)]
    marginal_z = []
    family_results = []
    coverage_results = []
    power_results = []
    progress_path = HERE / ("PREFLIGHT_PROGRESS.jsonl" if args.preflight else "SIMULATION_PROGRESS.jsonl")
    if not args.preflight and (HERE / "SIMULATION_RESULTS.json").exists():
        raise RuntimeError("SIMULATION_RESULTS.json already exists; refusing to overwrite frozen evidence")
    with progress_path.open("w", encoding="utf-8") as progress:
        for scenario_index, (family, q) in enumerate(SCENARIOS):
            scenario = f"{family['name']}_q{str(q).replace('.', '_')}"
            rng = np.random.Generator(np.random.PCG64(SEEDS[f"validation:{scenario}"]))
            zmean, zsd = draw_mean_sd(rng, family["distribution"], reps, n, 4, int(CFG["batch_size"]))
            t0 = centered_t(zmean, zsd, n)
            p0 = envelope_p(calrefs, eps, t0)
            marginal = []
            for c in range(4):
                for alpha in alphas:
                    k = int(np.count_nonzero(p0[:, c] <= alpha))
                    marginal.append({"condition_index": c, "alpha": float(alpha), "count": k, "rate": k / reps})
            marginal_z.extend(marginal)
            cut_family = sim_cutoff
            marginal_cover = []
            for c in range(4):
                k = int(np.count_nonzero(t0[:, c] >= cutoffs[str(0.05)]))
                marginal_cover.append({"condition_index": c, **binomial_summary(k, reps, 40)})
            simultaneous_cover_count = int(np.count_nonzero(np.all(t0 >= cut_family, axis=1)))
            coverage_results.append({"scenario": scenario, "marginal_95_upper_coverage": marginal_cover,
                                     "four_condition_simultaneous_95_upper_coverage": binomial_summary(simultaneous_cover_count, reps, 10)})
            # Complete null.
            null_p = p0
            complete_count = int(np.count_nonzero(np.any(holm_reject(null_p, float(CFG["holm_alpha"])), axis=1)))
            family_results.append({"scenario": scenario, "configuration": "complete_null", "true_null_mask": 15,
                                   "false_null_effect": None, "kind": "simulated", **binomial_summary(complete_count, reps, int(CFG["acceptance"]["fwer_cells"]))})
            # Every nonempty proper subset of true nulls. Non-null effects include the planning alternative and a strong-effect least-favorable diagnostic.
            for mask in range(1, 15):
                true_mask = np.array([bool(mask & (1 << c)) for c in range(4)], dtype=bool)
                for effect in CFG["partial_null_alternatives"]:
                    sigma = np.asarray(CFG["condition_sd"], dtype=np.float64) * float(q)
                    shift = math.sqrt(n) * float(effect) / (sigma[None, :] * zsd)
                    t_alt = t0 + shift
                    p_alt = envelope_p(calrefs, eps, t_alt)
                    p_mix = np.where(true_mask[None, :], p0, p_alt)
                    count = int(np.count_nonzero(holm_family_false_discoveries(p_mix, true_mask)))
                    family_results.append({"scenario": scenario, "configuration": "partial_null", "true_null_mask": mask,
                                           "true_null_count": int(mask.bit_count()), "false_null_effect": float(effect),
                                           "kind": "simulated", **binomial_summary(count, reps, int(CFG["acceptance"]["fwer_cells"]))})
                p_lf = np.where(true_mask[None, :], p0, 0.0)
                count_lf = int(np.count_nonzero(holm_family_false_discoveries(p_lf, true_mask)))
                family_results.append({"scenario": scenario, "configuration": "partial_null", "true_null_mask": mask,
                                       "true_null_count": int(mask.bit_count()), "false_null_effect": "raw_p_zero_least_favorable",
                                       "kind": "least_favorable_pvalue_sensitivity", **binomial_summary(count_lf, reps, int(CFG["acceptance"]["fwer_cells"]))})
            # Secondary power; the historical protocol supplies no pass threshold for this family.
            sigma = np.asarray(CFG["condition_sd"], dtype=np.float64) * float(q)
            for effect in CFG["power_effects"]:
                t_alt = t0 + math.sqrt(n) * float(effect) / (sigma[None, :] * zsd)
                p_alt = envelope_p(calrefs, eps, t_alt)
                rej = holm_reject(p_alt, float(CFG["holm_alpha"]))
                by_condition = [binomial_summary(int(np.count_nonzero(rej[:, c])), reps, 20) for c in range(4)]
                power_results.append({"scenario": scenario, "effect": float(effect), "condition_holm_rejection": by_condition,
                                      "any_condition_rejected": binomial_summary(int(np.count_nonzero(np.any(rej, axis=1))), reps, 20),
                                      "all_four_rejected": binomial_summary(int(np.count_nonzero(np.all(rej, axis=1))), reps, 20)})
            progress.write(json.dumps({"scenario": scenario, "completed_replicates": reps, "elapsed_seconds": time.time() - start}) + "\n")
            progress.flush()
    # Familywise Wilson bounds for the marginal-size cells.
    for row in marginal_z:
        lower, upper = wilson_one_sided_simultaneous(row["count"], reps, int(CFG["acceptance"]["marginal_cells"]), CFG["mc_confidence"])
        row["simultaneous_one_sided_wilson95"] = [lower, upper]
        row["pass"] = upper <= row["alpha"] + float(CFG["acceptance"]["marginal_simultaneous_wilson_upper_le_step_alpha_plus"])
    for row in family_results:
        row["pass"] = row["simultaneous_one_sided_wilson95"][1] <= float(CFG["acceptance"]["simultaneous_wilson_upper_fwer_max"])
    for row in coverage_results:
        row["pass"] = row["four_condition_simultaneous_95_upper_coverage"]["simultaneous_one_sided_wilson95"][0] >= float(CFG["acceptance"]["simultaneous_wilson_lower_coverage_min"])
    results = {
        "status": "completed_design_simulation" if args.full else "preflight_only",
        "sampling_authorized": False,
        "stage5_evaluation_shots_generated": 0,
        "sealed_test_accessed": False,
        "n_roots_per_condition": n,
        "replicates_per_family_scale_cell": reps,
        "calibration_replicates_per_reference_family": cal_n,
        "dkw_epsilon": eps,
        "dkw_delta_total": float(CFG["total_dkw_failure_probability"]),
        "calibration_reference_fingerprints": calmeta,
        "critical_values_by_holm_step": {k: (None if not math.isfinite(v) else v) for k, v in cutoffs.items()},
        "marginal_pvalue_checks": marginal_z,
        "complete_and_partial_null_fwer": family_results,
        "coverage": coverage_results,
        "secondary_power": power_results,
        "gate_summary": {
            "all_marginal_size_cells_pass": all(r["pass"] for r in marginal_z),
            "all_complete_and_partial_fwer_cells_pass": all(r["pass"] for r in family_results),
            "all_simultaneous_coverage_cells_pass": all(r["pass"] for r in coverage_results),
            "secondary_power_gate": "not prespecified; descriptive only",
            "overall_secondary_method_pass": all(r["pass"] for r in marginal_z) and all(r["pass"] for r in family_results) and all(r["pass"] for r in coverage_results)
        },
        "environment": {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "scipy": scipy.__version__},
        "runtime_seconds": time.time() - start,
        "resource_limit_note": "Design-only synthetic root-effect simulations; no Stim shots or Stage 5 evaluation samples."
    }
    target = HERE / ("PREFLIGHT_RESULTS.json" if args.preflight else "SIMULATION_RESULTS.json")
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(results, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, target)
    print(json.dumps({"status": results["status"], "reps": reps, "family_cells": len(family_results),
                      "marginal_cells": len(marginal_z), "overall_secondary_method_pass": results["gate_summary"]["overall_secondary_method_pass"],
                      "runtime_seconds": results["runtime_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
