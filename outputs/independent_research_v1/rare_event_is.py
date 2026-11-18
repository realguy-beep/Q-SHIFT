"""Likelihood-ratio importance-sampling feasibility for approximate Phase 2B DEMs."""
from __future__ import annotations

import argparse
import json
import re
import resource
import time
from pathlib import Path
import sys

import numpy as np
import pymatching
import stim

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PHASE2B = REPO / "outputs" / "phase2b_pauli_bias"
sys.path.insert(0, str(PHASE2B))
from noise_model import MEMORY_BASES, REGIMES, build_circuit  # noqa: E402

THRESHOLD = 0.0018
ODDS_FACTOR = 5.0
PREFLIGHT_DIRECT = (202611211, 202611212, 202611213, 202611214, 202611215, 202611216)
PREFLIGHT_TILTED = (202611221, 202611222, 202611223, 202611224, 202611225, 202611226)
MAIN_DIRECT = (202611231, 202611232, 202611233, 202611234, 202611235, 202611236)
MAIN_TILTED = (202611241, 202611242, 202611243, 202611244, 202611245, 202611246)
CONDITIONS = tuple((basis, regime) for basis in MEMORY_BASES for regime in REGIMES)


def tilted_probability(p: float) -> float:
    return ODDS_FACTOR * p / (1 - p + ODDS_FACTOR * p)


def event_probabilities(dem: stim.DetectorErrorModel) -> np.ndarray:
    flat = dem.flattened()
    ps = [float(inst.args_copy()[0]) for inst in flat if inst.type == "error"]
    return np.asarray(ps, dtype=np.float64)


def tilt_dem(dem: stim.DetectorErrorModel) -> stim.DetectorErrorModel:
    flat_text = str(dem.flattened())
    pattern = re.compile(r"error\(([-+0-9.eE]+)\)")

    def replace(match: re.Match[str]) -> str:
        p = float(match.group(1))
        return f"error({tilted_probability(p):.17g})"

    return stim.DetectorErrorModel(pattern.sub(replace, flat_text))


def log_likelihood_ratio(errors: np.ndarray, p: np.ndarray, q: np.ndarray) -> np.ndarray:
    errors = np.asarray(errors, dtype=np.bool_)
    p = np.asarray(p, dtype=np.float64)
    q = np.asarray(q, dtype=np.float64)
    if errors.shape[1] != len(p) or p.shape != q.shape:
        raise ValueError("error-vector and probability dimensions differ")
    if np.any((p <= 0) | (p >= 1) | (q <= 0) | (q >= 1)):
        raise ValueError("importance sampling requires event probabilities strictly between 0 and 1")
    fired = errors @ np.log(p / q)
    not_fired = (~errors) @ np.log((1 - p) / (1 - q))
    return np.asarray(fired + not_fired, dtype=np.float64)


def exhaustive_weight_validation() -> dict:
    """Check normalization and a decoder-failure expectation on every toy pattern."""
    toy = stim.DetectorErrorModel(
        "error(0.1) D0 L0\nerror(0.2) D0\nerror(0.3) L0\n"
        "detector D0\nlogical_observable L0\n")
    p = event_probabilities(toy)
    q = np.asarray([tilted_probability(float(x)) for x in p])
    all_errors = np.asarray([[bool(mask & (1 << i)) for i in range(len(p))]
                             for mask in range(1 << len(p))], dtype=np.bool_)
    logw = log_likelihood_ratio(all_errors, p, q)
    q_prob = np.prod(np.where(all_errors, q, 1-q), axis=1)
    original_prob = np.prod(np.where(all_errors, p, 1-p), axis=1)
    failure = np.logical_xor(all_errors[:, 0], all_errors[:, 2]).astype(np.float64)
    # Failure means an always-zero logical decoder disagrees with L0.
    normalizer = float(np.sum(q_prob * np.exp(logw)))
    weighted_ler = float(np.sum(q_prob * np.exp(logw) * failure))
    exact_ler = float(np.sum(original_prob * failure))
    if not np.isclose(normalizer, 1.0, atol=1e-14) or not np.isclose(weighted_ler, exact_ler, atol=1e-14):
        raise RuntimeError("exhaustive likelihood-ratio validation failed")
    return {"patterns": len(all_errors), "weight_normalization": normalizer,
            "weighted_ler": weighted_ler, "exact_ler": exact_ler,
            "absolute_error": abs(weighted_ler-exact_ler)}


def decode_failures(matching: pymatching.Matching, detectors: np.ndarray,
                    observables: np.ndarray) -> np.ndarray:
    failed = np.empty(len(detectors), dtype=np.bool_)
    for i, syndrome in enumerate(detectors):
        predicted = np.asarray(matching.decode(syndrome), dtype=np.bool_).reshape(-1)
        failed[i] = not np.array_equal(predicted, observables[i])
    return failed


def relative_se(values: np.ndarray, estimate: float) -> float:
    if len(values) < 2 or estimate <= 0:
        return float("inf")
    se = float(np.std(values, ddof=1) / np.sqrt(len(values)))
    return se / estimate


def run_condition(basis: str, regime: str, shots: int,
                  direct_seed: int, tilted_seed: int) -> dict:
    circuit = build_circuit(basis, regime)
    dem = circuit.detector_error_model(
        decompose_errors=True, approximate_disjoint_errors=THRESHOLD).flattened()
    probs = event_probabilities(dem)
    tilted = tilt_dem(dem)
    q = event_probabilities(tilted)
    if not np.allclose(q, [tilted_probability(float(x)) for x in probs], rtol=1e-12, atol=1e-15):
        raise RuntimeError("tilted DEM event order/probabilities do not match base DEM")
    matching = pymatching.Matching.from_detector_error_model(dem, enable_correlations=True)
    direct_sampler = dem.compile_sampler(seed=direct_seed)
    tilted_sampler = tilted.compile_sampler(seed=tilted_seed)

    start = time.perf_counter()
    d_det, d_obs, _ = direct_sampler.sample(shots=shots, return_errors=False)
    direct_failed = decode_failures(matching, d_det, d_obs)
    direct_elapsed = time.perf_counter() - start
    start = time.perf_counter()
    t_det, t_obs, errors = tilted_sampler.sample(shots=shots, return_errors=True)
    tilted_failed = decode_failures(matching, t_det, t_obs)
    logw = log_likelihood_ratio(errors, probs, q)
    weights = np.exp(logw)
    weighted_terms = weights * tilted_failed
    tilted_elapsed = time.perf_counter() - start

    estimate = float(weighted_terms.mean())
    estimate_se = float(weighted_terms.std(ddof=1) / np.sqrt(shots)) if shots > 1 else float("inf")
    fail_weights = weights[tilted_failed]
    failure_ess = (float(fail_weights.sum()**2 / np.square(fail_weights).sum())
                   if len(fail_weights) and np.square(fail_weights).sum() else 0.0)
    direct_rate = float(direct_failed.mean())
    return {
        "memory_basis": basis,
        "regime": regime,
        "direct_seed": direct_seed,
        "tilted_seed": tilted_seed,
        "shots_per_arm": shots,
        "dem_events": int(len(probs)),
        "direct_failures": int(direct_failed.sum()),
        "direct_ler": direct_rate,
        "direct_relative_se": relative_se(direct_failed.astype(np.float64), direct_rate),
        "tilted_failures_unweighted": int(tilted_failed.sum()),
        "importance_weighted_ler": estimate,
        "importance_standard_error": estimate_se,
        "importance_relative_se": estimate_se / estimate if estimate > 0 else float("inf"),
        "failure_weight_effective_sample_size": failure_ess,
        "max_abs_log_weight": float(np.max(np.abs(logw))),
        "weight_min": float(weights.min()),
        "weight_max": float(weights.max()),
        "odds_factor": ODDS_FACTOR,
        "direct_seconds": direct_elapsed,
        "tilted_seconds": tilted_elapsed,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--shots", type=int, default=20000)
    parser.add_argument("--replicates", type=int, default=1,
                        help="independent replication count (use 8 for the predeclared stability check)")
    args = parser.parse_args()
    if args.shots <= 0:
        parser.error("--shots must be positive")
    if args.replicates <= 0 or (args.preflight and args.replicates != 1):
        parser.error("replicates must be positive; preflight and replicate modes cannot be combined")
    exact_check = exhaustive_weight_validation()
    preflight = args.preflight
    shots = 5000 if preflight else args.shots
    start = time.perf_counter()
    if args.replicates > 1:
        replicate_rows = []
        for rep in range(args.replicates):
            direct_seeds = tuple(202611301 + 6*rep + i for i in range(6))
            tilted_seeds = tuple(202611401 + 6*rep + i for i in range(6))
            replicate_rows.append([
                run_condition(b, r, shots, ds, ts)
                for (b, r), ds, ts in zip(CONDITIONS, direct_seeds, tilted_seeds, strict=True)
            ])
        summary_rows = []
        for i, (basis, regime) in enumerate(CONDITIONS):
            direct = np.asarray([block[i]["direct_ler"] for block in replicate_rows])
            tilted = np.asarray([block[i]["importance_weighted_ler"] for block in replicate_rows])
            direct_sd = float(direct.std(ddof=1))
            tilted_sd = float(tilted.std(ddof=1))
            differences = tilted-direct
            diff_se = float(differences.std(ddof=1)/np.sqrt(args.replicates))
            summary_rows.append({
                "memory_basis": basis, "regime": regime,
                "direct_mean": float(direct.mean()), "importance_mean": float(tilted.mean()),
                "direct_between_replicate_sd": direct_sd,
                "importance_between_replicate_sd": tilted_sd,
                "importance_to_direct_sd_ratio": tilted_sd/direct_sd if direct_sd else float("inf"),
                "mean_importance_minus_direct": float(differences.mean()),
                "difference_standard_error": diff_se,
            })
        replication_gain = sum(row["importance_to_direct_sd_ratio"] <= 0.75 for row in summary_rows)
        output = {
            "status": "independent_replication_check",
            "stim_version": stim.__version__, "pymatching_version": pymatching.__version__,
            "dem_threshold": THRESHOLD, "proposal": f"uniform odds factor {ODDS_FACTOR:g}",
            "exact_weight_validation": exact_check,
            "replicates": args.replicates, "shots_per_arm_per_condition_per_replicate": shots,
            "condition_summaries": summary_rows, "replicate_results": replicate_rows,
            "conditions_with_at_least_25pct_between_replicate_sd_reduction": replication_gain,
            "elapsed_seconds": time.perf_counter()-start,
            "stochastic_dem_samples": shots*len(CONDITIONS)*2*args.replicates,
            "scope": "independent variance/bias replication on the approximate DEM surrogate only",
        }
        target = HERE / "rare_event_replication_check.json"
        target.write_text(json.dumps(output, indent=2)+"\n", encoding="utf-8")
        print(f"Wrote {target}; elapsed={output['elapsed_seconds']:.3f}s; gain_conditions={replication_gain}/6")
        for row in summary_rows:
            print(row["memory_basis"], row["regime"],
                  f"SD={row['direct_between_replicate_sd']:.6g}->{row['importance_between_replicate_sd']:.6g}",
                  f"ratio={row['importance_to_direct_sd_ratio']:.3f}",
                  f"mean_diff={row['mean_importance_minus_direct']:.6g} +/- {row['difference_standard_error']:.3g}")
        return 0

    direct_seeds = PREFLIGHT_DIRECT if preflight else MAIN_DIRECT
    tilted_seeds = PREFLIGHT_TILTED if preflight else MAIN_TILTED
    rows = [run_condition(b, r, shots, ds, ts)
            for (b, r), ds, ts in zip(CONDITIONS, direct_seeds, tilted_seeds, strict=True)]
    elapsed = time.perf_counter() - start
    improved = [row["importance_relative_se"] <= 0.75 * row["direct_relative_se"]
                for row in rows]
    gate_pass = sum(improved) >= 4 and all(np.isfinite(row["importance_weighted_ler"])
                                           and np.isfinite(row["importance_standard_error"])
                                           for row in rows)
    output = {
        "status": "preflight" if preflight else "development_importance_sampling_screen",
        "stim_version": stim.__version__,
        "pymatching_version": pymatching.__version__,
        "dem_threshold": THRESHOLD,
        "proposal": f"uniform odds factor {ODDS_FACTOR:g}",
        "exact_weight_validation": exact_check,
        "shots_per_arm_per_condition": shots,
        "conditions": rows,
        "conditions_meeting_25pct_relative_se_gain": int(sum(improved)),
        "predeclared_advancement_gate_passed": bool(gate_pass),
        "elapsed_seconds": elapsed,
        "stochastic_dem_samples": shots * len(rows) * 2,
        "scope": "importance sampling targets the approximate DEM surrogate, not the original categorical circuit distribution",
    }
    target = HERE / ("rare_event_preflight.json" if preflight else "rare_event_results.json")
    target.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {target}; elapsed={elapsed:.3f}s; gain_conditions={sum(improved)}/6")
    for row in rows:
        print(row["memory_basis"], row["regime"],
              f"direct={row['direct_ler']:.6g}",
              f"IS={row['importance_weighted_ler']:.6g}",
              f"relative_SE={row['direct_relative_se']:.4g}->{row['importance_relative_se']:.4g}",
              f"failure_ESS={row['failure_weight_effective_sample_size']:.1f}")
    if preflight and not gate_pass:
        print("The predeclared variance-reduction gate failed; do not run the larger screen")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
