from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path

import numpy as np
from scipy.stats import t as student_t

from integrity import verify_freeze

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / "DESIGN_SIMULATION_CONFIG.json").read_text(encoding="utf-8"))
INVENTORY = json.loads((HERE / "DESIGN_SEED_INVENTORY.json").read_text(encoding="utf-8"))
SEED_MAP = {(x["stream"], x["cell"]): x["seed"] for x in INVENTORY["rng_streams"]}


def wilson(k: int, n: int, confidence: float = 0.95) -> list[float]:
    # Independent closed-form Wilson interval; z fixed to 1.959963984540054.
    z = 1.959963984540054 if confidence == 0.95 else 2.5758293035489004
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [max(0.0, center - half), min(1.0, center + half)]


def draw_root_values(rng, batch, n, means, sds, family):
    means = np.asarray(means, dtype=np.float64)
    sds = np.asarray(sds, dtype=np.float64)
    shape = (batch, len(means), n)
    loc = means[None, :, None]
    scale = sds[None, :, None]
    if family == "normal":
        return rng.normal(loc=loc, scale=scale, size=shape)
    if family.startswith("student_t"):
        df = int(family.removeprefix("student_t"))
        return loc + scale * rng.standard_t(df, size=shape) / math.sqrt(df / (df - 2))
    if family == "lognormal_sigma1":
        raw = rng.lognormal(mean=0.0, sigma=1.0, size=shape)
        log_mean = math.exp(0.5)
        log_sd = math.sqrt((math.e - 1) * math.e)
        return loc + scale * ((raw - log_mean) / log_sd)
    if family == "zero_inflated65_normal":
        q = 0.35
        cond_mean = means / q
        cond_var = (sds * sds + means * means) / q - cond_mean * cond_mean
        if np.any(cond_var <= 0):
            raise ValueError("zero-inflated requested moments are infeasible")
        draws = rng.normal(cond_mean[None, :, None], np.sqrt(cond_var)[None, :, None], size=shape)
        zeros = rng.random(size=shape) < 0.65
        return np.where(zeros, 0.0, draws)
    if family == "tied_asymmetric65":
        p0, p_low, p_high = 0.65, 0.28, 0.07
        q = p_low + p_high
        prob_low, prob_high = p_low / q, p_high / q
        cond_mean = means / q
        cond_var = (sds * sds + means * means) / q - cond_mean * cond_mean
        if np.any(cond_var <= 0):
            raise ValueError("tied requested moments are infeasible")
        low = cond_mean - np.sqrt(cond_var * prob_high / prob_low)
        high = cond_mean + np.sqrt(cond_var * prob_low / prob_high)
        u = rng.random(size=shape)
        return np.where(u < p0, 0.0, np.where(u < p0 + p_low, low[None, :, None], high[None, :, None]))
    raise ValueError(f"Unknown root-effect distribution {family}")


def studentized(x, null):
    # x: (replicates, strata, roots). Returns equal-weight mean, SE, t, Satterthwaite df.
    m = x.mean(axis=2)
    s2 = x.var(axis=2, ddof=1)
    k = x.shape[1]
    n = x.shape[2]
    var_contribution = s2 / (k * k * n)
    v = var_contribution.sum(axis=1)
    estimate = m.mean(axis=1)
    se = np.sqrt(v)
    tstat = np.divide(estimate - null, se, out=np.zeros_like(estimate), where=se > 0)
    tstat = np.where((se == 0) & (estimate < null), -np.inf, tstat)
    tstat = np.where((se == 0) & (estimate > null), np.inf, tstat)
    denom = (var_contribution * var_contribution / (n - 1)).sum(axis=1)
    df = np.divide(v * v, denom, out=np.full_like(v, np.inf), where=denom > 0)
    return estimate, se, tstat, df


def batches(reps, n, strata, seed, means, sds, family, batch_size):
    rng = np.random.Generator(np.random.PCG64(int(seed)))
    for start in range(0, reps, batch_size):
        b = min(batch_size, reps - start)
        yield draw_root_values(rng, b, n, means, sds, family)


def get_seed(stream, cell):
    return int(SEED_MAP[(stream, cell)])


def collect_t(reps, n, seed, means, sds, family, batch_size, null):
    all_t, all_df = [], []
    for x in batches(reps, n, len(means), seed, means, sds, family, batch_size):
        _, _, ts, dfs = studentized(x, null)
        all_t.append(ts)
        all_df.append(dfs)
    return np.concatenate(all_t), np.concatenate(all_df)


def criticals_for_n(n):
    reps = int(CONFIG["monte_carlo"]["calibration_replicates_per_null_cell"])
    bsz = int(CONFIG["monte_carlo"]["batch_size"])
    base_sd = np.asarray(CONFIG["condition_sd"], dtype=float)
    offsets_default = np.zeros(4)
    cal_rows = []
    lower_values, upper_values, central_lower, central_upper = [], [], [], []
    for scenario in CONFIG["null_scenarios"]:
        offsets = np.asarray(scenario.get("offsets", offsets_default), dtype=float)
        means = float(CONFIG["null_boundary"]) + offsets
        sds = base_sd * float(scenario["sd_multiplier"])
        cell = f"n{n}/{scenario['name']}"
        ts, dfs = collect_t(reps, n, get_seed("primary_null_calibration", cell), means, sds,
                            scenario["distribution"], bsz, CONFIG["null_boundary"])
        lower_values.append(-ts)
        upper_values.append(ts)
        cal_q = CONFIG["monte_carlo"]["critical_quantiles"]
        q1 = float(cal_q["one_sided_calibration"])
        q2lo = 1 - float(cal_q["central_lower_tail"])
        q2hi = float(cal_q["central_upper_tail"])
        q_one = float(np.quantile(-ts, q1, method="higher"))
        q_lo = float(np.quantile(-ts, 1 - q2lo, method="higher"))
        q_hi = float(np.quantile(ts, q2hi, method="higher"))
        # Preserve per-scenario calibration evidence, while the actual cutoff is the envelope maximum.
        cal_rows.append({"scenario": scenario["name"], "n": n, "seed": get_seed("primary_null_calibration", cell),
                         "replicates": reps, "q_one_sided": q_one, "q_central_lower": q_lo,
                         "q_central_upper": q_hi, "mean_t": float(np.mean(ts)),
                         "sd_t": float(np.std(ts, ddof=1)), "df_median": float(np.median(dfs))})
    c_one = max(x["q_one_sided"] for x in cal_rows)
    c_lo = max(x["q_central_lower"] for x in cal_rows)
    c_hi = max(x["q_central_upper"] for x in cal_rows)
    return {"n": n, "one_sided_critical": c_one, "central_lower_critical": c_lo,
            "central_upper_critical": c_hi, "calibration_cells": cal_rows}


def validate_primary(n, critical, out, progress):
    reps = int(CONFIG["monte_carlo"]["validation_replicates_per_null_cell"])
    bsz = int(CONFIG["monte_carlo"]["batch_size"])
    base_sd = np.asarray(CONFIG["condition_sd"], dtype=float)
    offset0 = np.zeros(4)
    c_one = critical["one_sided_critical"]
    c_lo, c_hi = critical["central_lower_critical"], critical["central_upper_critical"]
    for scenario in CONFIG["null_scenarios"]:
        offsets = np.asarray(scenario.get("offsets", offset0), dtype=float)
        means = float(CONFIG["null_boundary"]) + offsets
        sds = base_sd * float(scenario["sd_multiplier"])
        cell = f"n{n}/{scenario['name']}"
        seed = get_seed("primary_null_validation", cell)
        cand_rej = welch_rej = central_cover = 0
        done = 0
        rng = np.random.Generator(np.random.PCG64(seed))
        while done < reps:
            b = min(bsz, reps - done)
            x = draw_root_values(rng, b, n, means, sds, scenario["distribution"])
            estimate, se, ts, dfs = studentized(x, CONFIG["null_boundary"])
            crit_w = student_t.ppf(0.95, dfs)
            cand_rej += int(np.count_nonzero(ts < -c_one))
            welch_rej += int(np.count_nonzero(ts < -crit_w))
            central_cover += int(np.count_nonzero((ts >= -c_lo) & (ts <= c_hi)))
            done += b
        row = {
            "allocation_roots_per_stratum": n, "scenario": scenario["name"], "distribution": scenario["distribution"],
            "sd_multiplier": scenario["sd_multiplier"], "offsets": scenario.get("offsets", [0, 0, 0, 0]),
            "seed": seed, "replicates": reps,
            "candidate_rejections": cand_rej, "candidate_type1": cand_rej / reps,
            "candidate_type1_wilson95": wilson(cand_rej, reps),
            "candidate_upper_bound_coverage": 1 - cand_rej / reps,
            "candidate_upper_bound_coverage_wilson95": [1 - wilson(cand_rej, reps)[1], 1 - wilson(cand_rej, reps)[0]],
            "central_interval_coverage_count": central_cover,
            "central_interval_coverage": central_cover / reps,
            "central_interval_coverage_wilson95": wilson(central_cover, reps),
            "welch_rejections": welch_rej, "welch_type1": welch_rej / reps,
            "welch_type1_wilson95": wilson(welch_rej, reps),
            "one_sided_critical": c_one, "central_lower_critical": c_lo, "central_upper_critical": c_hi,
        }
        out.append(row)
        progress({"phase": "primary_null_validation", "n": n, "scenario": scenario["name"], "type1": row["candidate_type1"]})


def run_primary_power(n, critical, out, progress):
    reps = int(CONFIG["monte_carlo"]["power_replicates_per_cell"])
    bsz = int(CONFIG["monte_carlo"]["batch_size"])
    base_sd = np.asarray(CONFIG["condition_sd"], dtype=float)
    for scenario in CONFIG["power_scenarios"]:
        offsets = np.asarray(scenario.get("offsets", np.zeros(4)), dtype=float)
        sds = base_sd * float(scenario["sd_multiplier"])
        for effect in CONFIG["power_effects"]:
            means = float(effect) + offsets
            cell = f"n{n}/{scenario['name']}/delta{effect}"
            seed = get_seed("primary_power", cell)
            rng = np.random.Generator(np.random.PCG64(seed))
            cand = welch = 0
            done = 0
            while done < reps:
                b = min(bsz, reps - done)
                x = draw_root_values(rng, b, n, means, sds, scenario["distribution"])
                _, _, ts, dfs = studentized(x, CONFIG["null_boundary"])
                tw = student_t.ppf(0.95, dfs)
                cand += int(np.count_nonzero(ts < -critical["one_sided_critical"]))
                welch += int(np.count_nonzero(ts < -tw))
                done += b
            row = {"n": n, "scenario": scenario["name"], "distribution": scenario["distribution"],
                   "sd_multiplier": scenario["sd_multiplier"], "true_delta": effect, "seed": seed,
                   "replicates": reps, "candidate_power_count": cand, "candidate_power": cand / reps, "candidate_power_wilson95": wilson(cand, reps),
                   "welch_power_count": welch, "welch_power": welch / reps, "welch_power_wilson95": wilson(welch, reps),
                   "candidate_critical": critical["one_sided_critical"]}
            out.append(row)
            progress({"phase": "primary_power", "n": n, "scenario": scenario["name"], "effect": effect, "power": row["candidate_power"]})


def p0_stat(x, null):
    m = x.mean(axis=1)
    s2 = x.var(axis=1, ddof=1)
    se = np.sqrt(s2 / x.shape[1])
    ts = np.divide(m - null, se, out=np.zeros_like(m), where=se > 0)
    ts = np.where((se == 0) & (m < null), -np.inf, ts)
    ts = np.where((se == 0) & (m > null), np.inf, ts)
    df = np.full_like(se, x.shape[1] - 1, dtype=float)
    return m, se, ts, df


def draw_p0(rng, batch, n, mean, sd, family):
    return draw_root_values(rng, batch, n, [mean], [sd], family)[:, 0, :]


def run_p0(n, out_calibration, out_null, out_power, progress):
    reps = int(CONFIG["monte_carlo"]["validation_replicates_per_null_cell"])
    bsz = int(CONFIG["monte_carlo"]["batch_size"])
    p0 = CONFIG["p0_no_harm"]
    base_sd = float(p0["base_sd"])
    boundary = float(p0["boundary"])
    cal_reps = int(CONFIG["monte_carlo"]["calibration_replicates_per_null_cell"])
    calibrations = []
    for scenario in p0["scenarios"]:
        cell = f"n{n}/{scenario['name']}"
        rng = np.random.Generator(np.random.PCG64(get_seed("p0_null_calibration", cell)))
        ts_list = []
        done = 0
        while done < cal_reps:
            b = min(bsz, cal_reps - done)
            x = draw_p0(rng, b, n, boundary, base_sd * scenario["sd_multiplier"], scenario["distribution"])
            _, _, ts, _ = p0_stat(x, boundary)
            ts_list.append(-ts)
            done += b
        q = float(np.quantile(np.concatenate(ts_list), CONFIG["monte_carlo"]["critical_quantiles"]["one_sided_calibration"], method="higher"))
        calibrations.append({"scenario": scenario["name"], "critical": q,
                             "seed": get_seed("p0_null_calibration", cell), "replicates": cal_reps})
    critical = max(x["critical"] for x in calibrations)
    out_calibration.append({"n": n, "one_sided_critical": critical, "scenario_calibration": calibrations})
    for scenario in p0["scenarios"]:
        cell = f"n{n}/{scenario['name']}"
        seed = get_seed("p0_null_validation", cell)
        rng = np.random.Generator(np.random.PCG64(seed))
        rejects = 0
        done = 0
        while done < reps:
            b = min(bsz, reps - done)
            x = draw_p0(rng, b, n, boundary, base_sd * scenario["sd_multiplier"], scenario["distribution"])
            _, _, ts, _ = p0_stat(x, boundary)
            rejects += int(np.count_nonzero(ts < -critical))
            done += b
        out_null.append({"n": n, "scenario": scenario["name"], "seed": seed, "replicates": reps,
                         "critical": critical, "rejections": rejects, "type1": rejects / reps,
                         "type1_wilson95": wilson(rejects, reps),
                         "upper_bound_coverage": 1 - rejects / reps,
                         "upper_bound_coverage_wilson95": [1 - wilson(rejects, reps)[1], 1 - wilson(rejects, reps)[0]]})
        progress({"phase": "p0_null_validation", "n": n, "scenario": scenario["name"], "type1": rejects / reps})
        for effect in p0["power_true_effects"]:
            pcell = f"n{n}/{scenario['name']}/effect{effect}"
            prng = np.random.Generator(np.random.PCG64(get_seed("p0_safety_power", pcell)))
            pass_count = 0
            done = 0
            while done < reps:
                b = min(bsz, reps - done)
                x = draw_p0(prng, b, n, effect, base_sd * scenario["sd_multiplier"], scenario["distribution"])
                _, _, ts, _ = p0_stat(x, boundary)
                pass_count += int(np.count_nonzero(ts < -critical))
                done += b
            out_power.append({"n": n, "scenario": scenario["name"], "true_effect": effect,
                              "seed": get_seed("p0_safety_power", pcell), "replicates": reps,
                              "no_harm_pass_count": pass_count,
                              "no_harm_pass_probability": pass_count / reps,
                              "wilson95": wilson(pass_count, reps), "critical": critical})


def atomic_json(path: Path, data):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Run deterministic small-shape checks only; not design MC")
    args = ap.parse_args()
    freeze = verify_freeze()
    started = time.perf_counter()
    if args.dry_run:
        x = np.array([[[0., 1., 2., 3.], [1., 1., 2., 2.], [-2., -1., 0., 1.], [4., 2., 1., 3.]]])
        m, se, ts, df = studentized(x, 0.0)
        assert np.isfinite(m[0]) and np.isfinite(se[0]) and np.isfinite(ts[0]) and np.isfinite(df[0])
        for family in ["normal", "student_t5", "student_t3", "lognormal_sigma1", "zero_inflated65_normal", "tied_asymmetric65"]:
            arr = draw_root_values(np.random.default_rng(712345), 64, 20, np.zeros(4), np.array(CONFIG["condition_sd"]), family)
            assert arr.shape == (64, 4, 20) and np.all(np.isfinite(arr))
        print("PASS: freeze, deterministic fixture, all generator families, no Stim sampler invoked")
        return
    mc = CONFIG["monte_carlo"]
    if mc["calibration_replicates_per_null_cell"] < 100000 or mc["validation_replicates_per_null_cell"] < 100000:
        raise RuntimeError("The prespecified 100,000 replicate minimum is not met")
    criticals, null_results, power_results, p0_calibration, p0_null, p0_power = [], [], [], [], [], []
    def progress(msg):
        print(json.dumps(msg), flush=True)
    for n in CONFIG["allocations_roots_per_stratum"]:
        c = criticals_for_n(int(n))
        criticals.append(c)
        atomic_json(HERE / "DESIGN_SIMULATION_CHECKPOINT.json", {
            "status": "running", "stage5_evaluation_shots_generated": 0,
            "sealed_historical_test_accessed": False, "completed_n": int(n),
            "critical_values": criticals, "primary_null_validation": null_results,
            "primary_power": power_results, "p0_calibration": p0_calibration,
            "p0_null_validation": p0_null, "p0_safety_power": p0_power})
        validate_primary(int(n), c, null_results, progress)
        run_primary_power(int(n), c, power_results, progress)
        run_p0(int(n), p0_calibration, p0_null, p0_power, progress)
        atomic_json(HERE / "DESIGN_SIMULATION_CHECKPOINT.json", {
            "status": "running", "stage5_evaluation_shots_generated": 0,
            "sealed_historical_test_accessed": False, "completed_n": int(n),
            "critical_values": criticals, "primary_null_validation": null_results,
            "primary_power": power_results, "p0_calibration": p0_calibration,
            "p0_null_validation": p0_null, "p0_safety_power": p0_power})
    result = {
        "study": CONFIG["study"], "status": "complete", "simulation_type": "synthetic root-effect design only",
        "stage5_evaluation_shots_generated": 0, "sealed_historical_test_accessed": False,
        "replicates_per_primary_null_validation_cell": mc["validation_replicates_per_null_cell"],
        "replicates_per_power_cell": mc["power_replicates_per_cell"],
        "calibration_and_validation_are_seed_disjoint": True,
        "critical_values_by_allocation": criticals,
        "primary_null_validation": null_results, "primary_power": power_results,
        "p0_calibration": p0_calibration,
        "p0_null_validation": p0_null, "p0_safety_power": p0_power,
        "runtime_seconds": time.perf_counter() - started, "design_freeze_sha256": freeze["freeze_sha256"],
        "decision_rules": mc["acceptance"],
    }
    atomic_json(HERE / "DESIGN_SIMULATION_RESULTS.json", result)
    atomic_json(HERE / "DESIGN_SIMULATION_CHECKPOINT.json", {"status": "complete", "stage5_evaluation_shots_generated": 0,
                "sealed_historical_test_accessed": False, "result_sha256_pending": True})
    print(json.dumps({"status": "complete", "runtime_seconds": result["runtime_seconds"],
                      "null_cells": len(null_results), "power_cells": len(power_results),
                      "stage5_shots": 0}, indent=2))


if __name__ == "__main__":
    main()
