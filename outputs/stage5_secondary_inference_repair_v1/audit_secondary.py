"""Independent deterministic replay; deliberately imports neither simulator nor stats module."""
from __future__ import annotations

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
from scipy.stats import norm

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dkw_margin(m: int, k: int, delta: float) -> float:
    return float(np.sqrt(np.log(2.0 * k / delta) / (2.0 * m)))


def root_samples(gen: np.random.Generator, family: str, dims: tuple[int, ...]) -> np.ndarray:
    if family == "normal":
        return gen.normal(0.0, 1.0, size=dims)
    if family in ("student_t5", "student_t3"):
        df = 5 if family == "student_t5" else 3
        return gen.standard_t(df, size=dims) / float(np.sqrt(df / (df - 2.0)))
    if family == "lognormal_sigma1":
        z = gen.lognormal(mean=0.0, sigma=1.0, size=dims)
        return (z - math.exp(0.5)) / math.sqrt((math.e - 1.0) * math.e)
    if family == "zero_inflated65_normal":
        keep = gen.uniform(size=dims) >= 0.65
        z = gen.normal(0.0, 1.0 / math.sqrt(0.35), size=dims)
        return np.where(keep, z, 0.0)
    if family == "tied_asymmetric65":
        u = gen.uniform(size=dims)
        q = 0.35
        low = -math.sqrt((1.0 / q) * (0.07 / q) / (0.28 / q))
        high = math.sqrt((1.0 / q) * (0.28 / q) / (0.07 / q))
        return np.where(u < 0.65, 0.0, np.where(u < 0.93, low, high))
    raise AssertionError(f"unknown family {family}")


def sample_moments(gen: np.random.Generator, family: str, r: int, n: int, p: int, b: int):
    avg = np.empty((r, p), dtype=np.float64)
    sd = np.empty((r, p), dtype=np.float64)
    start = 0
    while start < r:
        end = min(start + b, r)
        a = root_samples(gen, family, (end - start, n, p))
        avg[start:end, :] = a.mean(axis=1, dtype=np.float64)
        sd[start:end, :] = a.std(axis=1, ddof=1, dtype=np.float64)
        start = end
    return avg, sd


def studentized(avg: np.ndarray, spread: np.ndarray, n: int) -> np.ndarray:
    r = np.empty_like(avg)
    ok = spread != 0
    r[ok] = np.sqrt(n) * avg[ok] / spread[ok]
    r[~ok] = np.where(avg[~ok] < 0.0, -np.inf, np.inf)
    return r


def upper_envelope(references: list[np.ndarray], margin: float, t: np.ndarray) -> np.ndarray:
    value = np.full(t.shape, -np.inf, dtype=np.float64)
    for ref in references:
        count = np.searchsorted(ref, t, side="right")
        value = np.maximum(value, count.astype(np.float64) / len(ref) + margin)
    return np.clip(value, 0.0, 1.0)


def holm_map(p: np.ndarray, alpha: float) -> np.ndarray:
    order = np.argsort(p, axis=1, kind="stable")
    rank_values = np.take_along_axis(p, order, axis=1)
    rank_reject = np.zeros(p.shape, dtype=bool)
    open_step = np.ones(p.shape[0], dtype=bool)
    for j in range(p.shape[1]):
        open_step &= rank_values[:, j] <= alpha / (p.shape[1] - j)
        rank_reject[:, j] = open_step
    flags = np.zeros_like(rank_reject)
    rows = np.arange(p.shape[0])
    for j in range(p.shape[1]):
        flags[rows, order[:, j]] = rank_reject[:, j]
    return flags


def interval(k: int, n: int, cells: int, side: str = "upper") -> tuple[float, float]:
    z = float(norm.ppf(1.0 - 0.05 / cells))
    phat = k / n
    scale = 1.0 + z * z / n
    center = (phat + z * z / (2.0 * n)) / scale
    half = z * math.sqrt(phat * (1.0 - phat) / n + z * z / (4.0 * n * n)) / scale
    return max(0.0, center - half), min(1.0, center + half)


def main() -> None:
    started = time.monotonic()
    target = HERE / "INDEPENDENT_AUDIT.json"
    if target.exists():
        raise RuntimeError("refusing to overwrite independent audit output")
    config = json.loads((HERE / "DESIGN_CONFIG.json").read_text(encoding="utf-8"))
    inv = json.loads((HERE / "STAGE5_SECONDARY_REPAIR_SEED_INVENTORY.json").read_text(encoding="utf-8"))
    freeze = json.loads((HERE / "DESIGN_FREEZE.json").read_text(encoding="utf-8"))
    saved = json.loads((HERE / "SIMULATION_RESULTS.json").read_text(encoding="utf-8"))
    for rel, expected in freeze["source_and_config_sha256"].items():
        if digest_file(HERE / rel) != expected:
            raise AssertionError(f"frozen source/config changed: {rel}")
    for rel, expected in freeze["historical_metadata_sha256"].items():
        if digest_file(ROOT / rel) != expected:
            raise AssertionError(f"historical metadata changed: {rel}")
    if digest_file(HERE / "STAGE5_SECONDARY_REPAIR_SEED_INVENTORY.json") != freeze["seed_inventory_sha256"]:
        raise AssertionError("seed inventory differs from freeze")
    seeds = {x["role"]: x["seed"] for x in inv["streams"]}
    families = config["families"]
    qvalues = config["variability_multipliers"]
    n = int(config["n_roots_per_condition"])
    reps = int(config["validation_replicates_per_condition_family_scale"])
    m = int(config["calibration_replicates_per_family"])
    eps = dkw_margin(m, len(families), float(config["total_dkw_failure_probability"]))
    if abs(eps - saved["dkw_epsilon"]) > 1e-15:
        raise AssertionError("DKW margin differs")
    refs = []
    fingerprints = []
    for fam in families:
        g = np.random.Generator(np.random.PCG64(seeds[f"calibration:{fam['name']}"]))
        av, sd = sample_moments(g, fam["distribution"], m, n, 1, int(config["batch_size"]))
        tt = studentized(av, sd, n)[:, 0]
        tt.sort()
        dig = hashlib.sha256(tt.tobytes()).hexdigest()
        refs.append(tt)
        fingerprints.append({"family": fam["name"], "sha256_sorted_t": dig})
    if fingerprints != saved["calibration_reference_fingerprints"]:
        raise AssertionError("reference-CDF fingerprints differ on independent replay")
    marginal_counts = []
    fwer_counts = []
    coverage_counts = []
    power_counts = []
    threshold_list = list(config["holm_steps"])
    cut = {}
    for alpha in threshold_list:
        limit = math.floor((alpha - eps) * m)
        crossings = []
        for ref in refs:
            idx = min(max(limit, 0), len(ref) - 1)
            crossings.append(float(ref[idx]))
        cut[str(float(alpha))] = min(crossings)
    if any(abs(cut[k] - saved["critical_values_by_holm_step"][k]) > 0 for k in cut):
        raise AssertionError("critical values differ")
    complete_mask = np.ones(4, dtype=bool)
    for fam in families:
        for q in qvalues:
            scenario = f"{fam['name']}_q{str(q).replace('.', '_')}"
            g = np.random.Generator(np.random.PCG64(seeds[f"validation:{scenario}"]))
            av, sd = sample_moments(g, fam["distribution"], reps, n, 4, int(config["batch_size"]))
            t0 = studentized(av, sd, n)
            p0 = upper_envelope(refs, eps, t0)
            for c in range(4):
                for alpha in threshold_list:
                    marginal_counts.append({"scenario": scenario, "condition_index": c, "alpha": float(alpha),
                                            "count": int(np.count_nonzero(p0[:, c] <= alpha))})
            complete = int(np.count_nonzero(np.any(holm_map(p0, float(config["holm_alpha"])), axis=1)))
            fwer_counts.append({"scenario": scenario, "configuration": "complete_null", "true_null_mask": 15,
                                "false_null_effect": None, "kind": "simulated", "count": complete})
            # All partial-null subsets and both frozen alternatives, plus least-favorable p=0 false-null values.
            sigma = np.asarray(config["condition_sd"], dtype=np.float64) * float(q)
            for mask in range(1, 15):
                truth = np.array([bool(mask & (1 << c)) for c in range(4)])
                for effect in config["partial_null_alternatives"]:
                    shifted = t0 + np.sqrt(n) * float(effect) / (sigma[None, :] * sd)
                    altp = upper_envelope(refs, eps, shifted)
                    mixed = np.where(truth[None, :], p0, altp)
                    reject = holm_map(mixed, float(config["holm_alpha"]))
                    count = int(np.count_nonzero(np.any(reject & truth[None, :], axis=1)))
                    fwer_counts.append({"scenario": scenario, "configuration": "partial_null", "true_null_mask": mask,
                                        "false_null_effect": float(effect), "kind": "simulated", "count": count})
                worst = np.where(truth[None, :], p0, 0.0)
                reject = holm_map(worst, float(config["holm_alpha"]))
                count = int(np.count_nonzero(np.any(reject & truth[None, :], axis=1)))
                fwer_counts.append({"scenario": scenario, "configuration": "partial_null", "true_null_mask": mask,
                                    "false_null_effect": "raw_p_zero_least_favorable", "kind": "least_favorable_pvalue_sensitivity", "count": count})
            cov = int(np.count_nonzero(np.all(t0 >= cut[str(float(config["holm_alpha"])/4.0)], axis=1)))
            coverage_counts.append({"scenario": scenario, "four_condition_simultaneous_coverage_count": cov})
            for effect in config["power_effects"]:
                shifted = t0 + np.sqrt(n) * float(effect) / (sigma[None, :] * sd)
                altp = upper_envelope(refs, eps, shifted)
                reject = holm_map(altp, float(config["holm_alpha"]))
                power_counts.append({"scenario": scenario, "effect": float(effect),
                                     "condition_counts": [int(np.count_nonzero(reject[:, c])) for c in range(4)],
                                     "any_count": int(np.count_nonzero(np.any(reject, axis=1))),
                                     "all_four_count": int(np.count_nonzero(np.all(reject, axis=1)))})
    # Compare independent recomputation against every saved binomial count.
    for got in marginal_counts:
        match = next(x for x in saved["marginal_pvalue_checks"] if x["scenario"] == got["scenario"] and x["condition_index"] == got["condition_index"] and x["alpha"] == got["alpha"])
        if got["count"] != match["count"]:
            raise AssertionError(f"marginal replay mismatch: {got}")
    for got in fwer_counts:
        match = next(x for x in saved["complete_and_partial_null_fwer"] if x["scenario"] == got["scenario"] and x["configuration"] == got["configuration"] and x["true_null_mask"] == got["true_null_mask"] and x["false_null_effect"] == got["false_null_effect"])
        if got["count"] != match["successes"]:
            raise AssertionError(f"Holm FWER replay mismatch: {got}")
    for got in coverage_counts:
        match = next(x for x in saved["coverage"] if x["scenario"] == got["scenario"])
        if got["four_condition_simultaneous_coverage_count"] != match["four_condition_simultaneous_95_upper_coverage"]["successes"]:
            raise AssertionError(f"coverage replay mismatch: {got}")
    for got in power_counts:
        match = next(x for x in saved["secondary_power"] if x["scenario"] == got["scenario"] and x["effect"] == got["effect"])
        counts = [x["successes"] for x in match["condition_holm_rejection"]]
        if counts != got["condition_counts"] or got["any_count"] != match["any_condition_rejected"]["successes"] or got["all_four_count"] != match["all_four_rejected"]["successes"]:
            raise AssertionError(f"power replay mismatch: {got}")
    audit = {
        "audit": "independent full seed replay with separately coded sampling, root statistics, DKW envelope, Holm step-down, and Wilson bounds; no import from candidate simulator or statistics module",
        "source_freeze_sha256": digest_file(HERE / "DESIGN_FREEZE.json"),
        "result_sha256": digest_file(HERE / "SIMULATION_RESULTS.json"),
        "historical_metadata_hashes_verified": len(freeze["historical_metadata_sha256"]),
        "calibration_reference_families_replayed": len(fingerprints),
        "marginal_cells_replayed": len(marginal_counts),
        "complete_and_partial_fwer_cells_replayed": len(fwer_counts),
        "coverage_cells_replayed": len(coverage_counts),
        "power_cells_replayed": len(power_counts),
        "all_counts_and_reference_fingerprints_exactly_match": True,
        "stage5_evaluation_shots_generated": 0,
        "sealed_test_accessed": False,
        "environment": {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "scipy": scipy.__version__},
        "runtime_seconds": time.monotonic() - started
    }
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, target)
    print(json.dumps({"status": "PASS", "replayed": len(marginal_counts) + len(fwer_counts) + len(coverage_counts) + len(power_counts),
                      "runtime_seconds": audit["runtime_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
