"""Monte Carlo operating-characteristic study using synthetic root effects only.

This script does not invoke Stim, PyMatching, or any Stage 5 sampler. It writes
only DESIGN_SIMULATION_RESULTS.json in this candidate directory.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np
import scipy
from scipy.stats import t as student_t
from integrity import verify_preexecution_freeze

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "DESIGN_SIMULATION_CONFIG.json"
OUT = HERE / "DESIGN_SIMULATION_RESULTS.json"


def wilson(successes: int, n: int) -> list[float]:
    z = 1.959963984540054
    phat = successes / n
    den = 1 + z * z / n
    mid = (phat + z * z / (2 * n)) / den
    half = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / den
    return [max(0.0, mid - half), min(1.0, mid + half)]


def draw(rng: np.random.Generator, distribution: str, means: np.ndarray,
         sds: np.ndarray, n: int) -> np.ndarray:
    shape = (len(sds), n)
    mu = means[:, None]
    sig = sds[:, None]
    if distribution == "normal":
        return mu + sig * rng.standard_normal(shape)
    if distribution == "student_t5":
        return mu + sig * rng.standard_t(5, size=shape) / math.sqrt(5 / 3)
    if distribution == "lognormal_sigma1":
        sigma_logn = 1.0
        centered_unit = (np.exp(sigma_logn * rng.standard_normal(shape) - 0.5 * sigma_logn**2) - 1.0)
        centered_unit /= math.sqrt(math.exp(sigma_logn**2) - 1.0)
        return mu + sig * centered_unit
    if distribution == "zero_inflated_normal65":
        pi = 0.65
        active = rng.random(shape) >= pi
        conditional_mean = mu / (1 - pi)
        conditional_variance = (sig**2 - pi * mu**2 / (1 - pi)) / (1 - pi)
        if np.any(conditional_variance <= 0):
            raise ValueError("zero-inflated distribution cannot match requested moments")
        values = conditional_mean + np.sqrt(conditional_variance) * rng.standard_normal(shape)
        return np.where(active, values, 0.0)
    raise ValueError(f"unknown distribution {distribution}")


def draw_many(rng: np.random.Generator, distribution: str, means: np.ndarray,
              sds: np.ndarray, reps: int, n: int) -> np.ndarray:
    shape = (reps, len(sds), n)
    mu = means[None, :, None]
    sig = sds[None, :, None]
    if distribution == "normal":
        return mu + sig * rng.standard_normal(shape)
    if distribution == "student_t5":
        return mu + sig * rng.standard_t(5, size=shape) / math.sqrt(5 / 3)
    if distribution == "lognormal_sigma1":
        centered_unit = (np.exp(rng.standard_normal(shape) - 0.5) - 1.0) / math.sqrt(math.e - 1.0)
        return mu + sig * centered_unit
    if distribution == "zero_inflated_normal65":
        pi = 0.65
        active = rng.random(shape) >= pi
        conditional_mean = mu / (1 - pi)
        conditional_variance = (sig**2 - pi * mu**2 / (1 - pi)) / (1 - pi)
        if np.any(conditional_variance <= 0):
            raise ValueError("zero-inflated distribution cannot match requested moments")
        values = conditional_mean + np.sqrt(conditional_variance) * rng.standard_normal(shape)
        return np.where(active, values, 0.0)
    raise ValueError(f"unknown distribution {distribution}")


def welch(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    # x: simulations x four strata x independent roots
    n = x.shape[2]
    means = x.mean(axis=2)
    variances = x.var(axis=2, ddof=1)
    pieces = variances / (16.0 * n)
    v = pieces.sum(axis=1)
    se = np.sqrt(v)
    df = v**2 / (pieces**2 / (n - 1)).sum(axis=1)
    estimate = means.mean(axis=1)
    return estimate, se, df, means, variances


def run_welch_scenario(name: str, distribution: str, q: float, base_sds: np.ndarray,
                       reps: int, batch_size: int, seed: int,
                       offsets: np.ndarray | None = None) -> list[dict]:
    rng = np.random.Generator(np.random.PCG64(seed))
    sds = base_sds * q
    boundary = -0.0002
    effects = [boundary, -0.0003, -0.0004, -0.0005]
    result = []
    for effect_i, effect in enumerate(effects):
        stratum_offsets = np.zeros(4) if offsets is None else offsets
        true_means = effect + stratum_offsets
        true_delta = float(true_means.mean())
        rejected = covered_two = covered_upper = 0
        done = 0
        while done < reps:
            b = min(batch_size, reps - done)
            # Generate only synthetic root-level paired effect values.
            x = draw_many(rng, distribution, true_means, sds, reps=b, n=256)
            estimate, se, df, _, _ = welch(x)
            crit = student_t.ppf(0.95, df)
            upper = estimate + crit * se
            crit2 = student_t.ppf(0.975, df)
            lower2 = estimate - crit2 * se
            upper2 = estimate + crit2 * se
            rejected += int(np.count_nonzero(upper < boundary))
            covered_upper += int(np.count_nonzero(upper >= true_delta))
            covered_two += int(np.count_nonzero((lower2 <= true_delta) & (true_delta <= upper2)))
            done += b
        result.append({
            "scenario": name,
            "distribution": distribution,
            "sd_multiplier": q,
            "true_delta": true_delta,
            "roots_per_stratum": 256,
            "replicates": reps,
            "welch_primary": {
                "reject_rate_h0_delta_ge_minus_0_0002": rejected / reps,
                "type_i_error_or_power_mc_95_wilson": wilson(rejected, reps),
                "one_sided_upper_bound_coverage": covered_upper / reps,
                "one_sided_coverage_mc_95_wilson": wilson(covered_upper, reps),
                "central_95_ci_coverage": covered_two / reps,
                "central_coverage_mc_95_wilson": wilson(covered_two, reps),
            },
            "seed": seed + effect_i,
        })
    return result


def bootstrap_t_one_dataset(x: np.ndarray, rng: np.random.Generator, b: int) -> tuple[bool, bool]:
    # x: 4 x n; returns (one-sided boundary rejection, central 95% coverage)
    n = x.shape[1]
    xbatched = x[None, :, :]
    estimate, se, _, _, _ = welch(xbatched)
    estimate, se = float(estimate[0]), float(se[0])
    delta_star = np.zeros(b)
    variance_pieces = np.zeros((b, 4))
    for j in range(4):
        index = rng.integers(0, n, size=(b, n))
        draws = x[j][index]
        delta_star += draws.mean(axis=1) / 4.0
        variance_pieces[:, j] = draws.var(axis=1, ddof=1) / (16.0 * n)
    se_star = np.sqrt(variance_pieces.sum(axis=1))
    valid = se_star > 0
    tstar = (delta_star[valid] - estimate) / se_star[valid]
    if len(tstar) < max(20, b // 2):
        return False, False
    q05, q025, q975 = np.quantile(tstar, [0.05, 0.025, 0.975])
    upper = estimate - q05 * se
    lower2 = estimate - q975 * se
    upper2 = estimate - q025 * se
    true_delta = float(x.mean(axis=1).mean())
    # For null coverage, true_delta should be replaced by known population mean;
    # caller supplies that comparison after return in the next helper.
    return upper < -0.0002, lower2 <= true_delta <= upper2


def run_bootstrap_check(scenario: dict, base_sds: np.ndarray, reps: int, b: int,
                        batch_size: int, seed: int) -> dict:
    rng = np.random.Generator(np.random.PCG64(seed))
    pop_delta = -0.0002
    sds = base_sds * float(scenario["sd_multiplier"])
    offsets = np.asarray(scenario.get("mean_offsets", [0, 0, 0, 0]), dtype=float)
    means = pop_delta + offsets
    reject = cover_upper = cover_two = 0
    done = 0
    while done < reps:
        bsize = min(batch_size, reps - done)
        for _ in range(bsize):
            x = draw(rng, scenario["distribution"], means, sds, n=256)
            n = x.shape[1]
            est, se, _, _, _ = welch(x[None, :, :])
            est, se = float(est[0]), float(se[0])
            delta_star = np.zeros(b)
            vp = np.zeros((b, 4))
            for j in range(4):
                ix = rng.integers(0, n, size=(b, n))
                xb = x[j][ix]
                delta_star += xb.mean(axis=1) / 4.0
                vp[:, j] = xb.var(axis=1, ddof=1) / (16 * n)
            se_star = np.sqrt(vp.sum(axis=1))
            valid = se_star > 0
            tstar = (delta_star[valid] - est) / se_star[valid]
            if len(tstar) < max(20, b // 2):
                continue
            q05, q025, q975 = np.quantile(tstar, [0.05, 0.025, 0.975])
            upper = est - q05 * se
            lower2 = est - q975 * se
            upper2 = est - q025 * se
            reject += int(upper < -0.0002)
            cover_upper += int(upper >= pop_delta)
            cover_two += int(lower2 <= pop_delta <= upper2)
        done += bsize
    return {
        "scenario": scenario["name"], "distribution": scenario["distribution"],
        "sd_multiplier": scenario["sd_multiplier"], "true_delta": pop_delta,
        "outer_replicates": reps, "bootstrap_replicates": b, "seed": seed,
        "bootstrap_t": {
            "type_i_error": reject / reps, "type_i_mc_95_wilson": wilson(reject, reps),
            "one_sided_upper_coverage": cover_upper / reps,
            "one_sided_coverage_mc_95_wilson": wilson(cover_upper, reps),
            "central_95_ci_coverage": cover_two / reps,
            "central_coverage_mc_95_wilson": wilson(cover_two, reps),
        },
        "note": "At the B null boundary, rejection rate equals one-sided type-I error; finite bootstrap inner draws add Monte Carlo noise."
    }


def run_zero_burst(cfg: dict) -> list[dict]:
    spec = cfg["zero_burst_no_harm"]
    rng = np.random.Generator(np.random.PCG64(int(cfg["rng"]["p0_seed_base"])))
    results = []
    n = int(spec["roots"])
    reps = 10000
    boundary = float(spec["harm_margin"])
    for dist in spec["distribution_scenarios"]:
        for q in spec["sd_multipliers"]:
            sd = float(spec["sd"]) * float(q)
            for true_delta in spec["true_effects"]:
                reject = cover = 0
                if dist == "zero_inflated65" and true_delta != 0.0:
                    conditional_variance = (sd**2 - 0.65 * true_delta**2 / (1 - 0.65)) / (1 - 0.65)
                    if conditional_variance <= 0:
                        results.append({
                            "distribution": dist, "sd_multiplier": q, "true_effect": true_delta,
                            "roots": n, "replicates": 0, "status": "not_simulated_infeasible_moments",
                            "note": "A 65%-point-mass-at-zero mixture cannot attain this mean and SD; no alternative distribution substituted."
                        })
                        continue
                for start in range(0, reps, 250):
                    bsize = min(250, reps - start)
                    if dist == "zero_inflated65":
                        pi = 0.65
                        conditional_variance = (sd**2 - pi * true_delta**2 / (1 - pi)) / (1 - pi)
                        if conditional_variance <= 0:
                            raise ValueError("p=0 zero-inflated requested moments are infeasible")
                        active = rng.random((bsize, n)) >= pi
                        conditional_mean = true_delta / (1 - pi)
                        x = np.where(active, conditional_mean + math.sqrt(conditional_variance) * rng.standard_normal((bsize, n)), 0.0)
                    else:
                        x = true_delta + sd * rng.standard_normal((bsize, n))
                    means = x.mean(axis=1)
                    s = x.std(axis=1, ddof=1)
                    upper = means + student_t.ppf(0.95, n - 1) * s / math.sqrt(n)
                    reject += int(np.count_nonzero(upper < boundary))
                    cover += int(np.count_nonzero(upper >= float(true_delta)))
                results.append({
                    "distribution": dist, "sd_multiplier": q, "true_effect": true_delta,
                    "roots": n, "replicates": reps,
                    "pass_no_harm_rate_or_type_i": reject / reps,
                    "rate_mc_95_wilson": wilson(reject, reps),
                    "upper_bound_coverage": cover / reps,
                    "coverage_mc_95_wilson": wilson(cover, reps),
                    "seed": int(cfg["rng"]["p0_seed_base"]),
                })
    return results


def main() -> None:
    verify_preexecution_freeze()
    started = time.perf_counter()
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    base_sds = np.asarray(list(cfg["sd_by_nonzero_probability"].values()), dtype=float)
    reps = int(cfg["welch_monte_carlo_replicates_per_scenario_effect"])
    results = []
    for idx, scenario in enumerate(cfg["scenarios"]):
        results.extend(run_welch_scenario(
            scenario["name"], scenario["distribution"], float(scenario["sd_multiplier"]),
            base_sds, reps, int(cfg["welch_batch_size"]),
            int(cfg["rng"]["welch_seed_base"]) + idx * 100,
            np.asarray(scenario.get("mean_offsets"), dtype=float) if "mean_offsets" in scenario else None,
        ))
    boot_results = []
    by_name = {s["name"]: s for s in cfg["scenarios"]}
    for idx, name in enumerate(cfg["bootstrap_t_scenarios"]):
        boot_results.append(run_bootstrap_check(
            by_name[name], base_sds,
            int(cfg["bootstrap_t_outer_replicates_per_null_scenario"]),
            int(cfg["bootstrap_t_inner_replicates"]),
            int(cfg["bootstrap_t_batch_size"]),
            int(cfg["rng"]["bootstrap_seed_base"]) + idx * 100,
        ))
    output = {
        "status": "completed; synthetic root-effect design simulation only",
        "stage5_shots_generated": 0,
        "sealed_test_accessed": False,
        "configuration": str(CONFIG_PATH.name),
        "configuration_sha256_expected_in_freeze": "see DESIGN_VALIDATION_FREEZE.json",
        "software": {"numpy": np.__version__, "scipy": scipy.__version__},
        "root_level_welch_results": results,
        "root_stratified_bootstrap_t_null_results": boot_results,
        "zero_burst_no_harm_results": run_zero_burst(cfg),
        "wall_seconds": time.perf_counter() - started,
        "method_notes": [
            "All generated values are simulated root-level paired LER differences, not detector or observable samples.",
            "Welch simulations estimate test size, coverage, and power under the listed root-effect distributions.",
            "Bootstrap-t uses the same paired root differences and independently resamples roots within each nonzero stratum.",
            "Monte Carlo intervals quantify simulation error only, not uncertainty in the seven-root development SD inputs."
        ]
    }
    OUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}; Welch rows={len(results)}, bootstrap scenarios={len(boot_results)}, elapsed={output['wall_seconds']:.1f}s")


if __name__ == "__main__":
    main()
