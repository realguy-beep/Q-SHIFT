"""Deterministic Chernoff-information audit for burst-step signatures.

Uses exact ten-detector probability laws for the categorical circuit and the
approximate DEM. No detector histories are generated. Chernoff information is
a symmetric simple-hypothesis separation exponent, not a sequential alarm
delay, false-alarm guarantee, or decoder-utility result.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import burst_step_information_audit as info
import categorical_circuit_parameter_grid_audit as grid
from categorical_circuit_feature_expectations import direct_xor
from dem_feature_expectations import build_dem, direct_xor_convolution

TRANSITIONS = info.TRANSITIONS
MEASUREMENT_PS = info.MEASUREMENT_PS


def coefficient(p: np.ndarray, q: np.ndarray, s: float) -> float:
    """Return sum_x p(x)^s q(x)^(1-s), with endpoint-safe support handling."""
    if abs(float(p.sum()) - 1.0) > 2e-12 or abs(float(q.sum()) - 1.0) > 2e-12:
        raise ValueError("input law is not normalized")
    terms = np.zeros_like(p, dtype=np.float64)
    mask = (p > 0) & (q > 0)
    terms[mask] = np.exp(s * np.log(p[mask]) + (1 - s) * np.log(q[mask]))
    if s == 0:
        terms[q > 0] = q[q > 0]
    elif s == 1:
        terms[p > 0] = p[p > 0]
    return float(terms.sum())


def chernoff(p_new: np.ndarray, p_old: np.ndarray) -> tuple[float, float]:
    """Maximize -log coefficient by golden-section search on [0,1]."""
    lo, hi = 0.0, 1.0
    phi = (math.sqrt(5.0) - 1.0) / 2.0
    x1 = hi - phi * (hi - lo)
    x2 = lo + phi * (hi - lo)
    f = lambda s: -math.log(max(coefficient(p_new, p_old, s), np.finfo(float).tiny))
    y1, y2 = f(x1), f(x2)
    for _ in range(120):
        if hi - lo <= 2e-14:
            break
        if y1 < y2:
            lo, x1, y1 = x1, x2, y2
            x2 = lo + phi * (hi - lo)
            y2 = f(x2)
        else:
            hi, x2, y2 = x2, x1, y1
            x1 = hi - phi * (hi - lo)
            y1 = f(x1)
    s_star = (lo + hi) / 2
    c_star = f(s_star)
    # Check endpoints and s=1/2 independently of the optimizer.
    candidates = [(f(0.0), 0.0), (f(0.5), 0.5), (f(1.0), 1.0), (c_star, s_star)]
    return max(candidates)


def laws() -> dict[str, dict[tuple[float, float], np.ndarray]]:
    base = grid.construct(0.010, 0.003)
    template, _ = grid.categorical_sites(base)
    ps = sorted({p for pair in TRANSITIONS for p in pair})
    result: dict[str, dict[tuple[float, float], np.ndarray]] = {
        "exact_categorical_circuit": {}, "approximate_dem": {}}
    for p in ps:
        for pm in MEASUREMENT_PS:
            sites = grid.reweight(template, grid.construct(p, pm))
            exact = direct_xor(sites, info.SELECTED)
            _, mechanisms = build_dem(p, pm)
            dem = direct_xor_convolution(mechanisms, info.SELECTED)
            for name, dist in (("exact_categorical_circuit", exact), ("approximate_dem", dem)):
                if abs(float(dist.sum()) - 1.0) > 2e-12 or np.any(dist < 0):
                    raise RuntimeError(f"invalid distribution: {name}, p={p}, pm={pm}")
                result[name][(p, pm)] = dist
    return result


def main() -> None:
    cache = laws()
    rows = []
    nuisance = []
    validation = {"normalization_error_max": 0.0, "chernoff_nonnegative": True,
                  "chernoff_below_bidirectional_kl": True,
                  "golden_section_vs_10001_grid_max_abs": 0.0,
                  "hellinger_coefficient_identity_max_abs": 0.0}
    for model, table in cache.items():
        for old_p, new_p in TRANSITIONS:
            for pm in MEASUREMENT_PS:
                p0, p1 = table[(old_p, pm)], table[(new_p, pm)]
                c, s_star = chernoff(p1, p0)
                d = info.distances(p0, p1)
                validation["normalization_error_max"] = max(validation["normalization_error_max"],
                    abs(float(p0.sum()) - 1), abs(float(p1.sum()) - 1))
                validation["chernoff_nonnegative"] &= c >= -1e-13
                validation["chernoff_below_bidirectional_kl"] &= c <= min(
                    d["KL_new_given_old_nats_per_shot"], d["KL_old_given_new_nats_per_shot"]) + 1e-11
                validation["hellinger_coefficient_identity_max_abs"] = max(
                    validation["hellinger_coefficient_identity_max_abs"],
                    abs(coefficient(p1, p0, .5) - float(np.sqrt(p1 * p0).sum())))
                # Independent dense grid sanity check; not the production optimizer.
                s_grid = np.linspace(0, 1, 10001)
                grid_best = max(-math.log(max(coefficient(p1, p0, s), np.finfo(float).tiny)) for s in s_grid)
                validation["golden_section_vs_10001_grid_max_abs"] = max(
                    validation["golden_section_vs_10001_grid_max_abs"], abs(grid_best - c))
                rows.append({"model": model, "old_burst_p": old_p, "new_burst_p": new_p,
                    "old_measurement_p": pm, "new_measurement_p": pm,
                    "chernoff_information_nats_per_shot": c, "optimizing_exponent_s": s_star,
                    "hellinger_squared_at_s_half": d["hellinger_squared_per_shot"]})
            candidates = []
            for pm_old in MEASUREMENT_PS:
                for pm_new in MEASUREMENT_PS:
                    c, s_star = chernoff(table[(new_p, pm_new)], table[(old_p, pm_old)])
                    candidates.append((c, pm_old, pm_new, s_star))
            worst = min(candidates)
            nuisance.append({"model": model, "old_burst_p": old_p, "new_burst_p": new_p,
                "minimum_chernoff_information_over_independent_measurement_grid_nats_per_shot": worst[0],
                "old_measurement_p_at_minimum": worst[1], "new_measurement_p_at_minimum": worst[2],
                "optimizing_exponent_s": worst[3], "measurement_grid": list(MEASUREMENT_PS)})
    if validation["golden_section_vs_10001_grid_max_abs"] > 2e-9:
        raise RuntimeError("optimizer disagrees with dense grid")
    if validation["hellinger_coefficient_identity_max_abs"] > 2e-12:
        raise RuntimeError("s=1/2 coefficient identity failed")
    result = {
        "classification": "DETERMINISTIC_SIMPLE_HYPOTHESIS_CHERNOFF_INFORMATION_NOT_ONLINE_DETECTOR_EVALUATION",
        "configuration": {"circuit": "Q-SHIFT d=3 five-round balanced Z memory",
            "selected_detectors": list(info.SELECTED), "state_count": 2**len(info.SELECTED),
            "gate_p": .003, "measurement_p_grid": list(MEASUREMENT_PS),
            "transitions": [list(x) for x in TRANSITIONS]},
        "method": "Exact 2^10 categorical-circuit and approximate-DEM detector laws; bounded golden-section maximization of -log sum_x P_new(x)^s P_old(x)^(1-s), with endpoints and s=1/2 checks; independent 10001-point grid validation.",
        "rows": rows, "independent_measurement_nuisance_grid_minima": nuisance,
        "validation": validation,
        "interpretation": [
            "Chernoff information is the asymptotic symmetric simple-hypothesis error exponent for IID observations under the two fully specified laws; it is not a realized test statistic, threshold, alarm delay, or finite-history error rate.",
            "The nuisance rows permit old and new measurement probabilities to differ on a coarse grid. They do not establish robustness to arbitrary drift, unknown nuisance estimation, dependent shots, or detector-model mismatch.",
            "Ten detectors are a subset of the 40 detector bits. Their Chernoff information cannot exceed that of the full observation, but the omitted bits could improve nuisance estimation.",
            "No alarm policy, decoder, logical outcome, sampling, or model selection was evaluated. Exact circuit and approximate DEM results remain separate."
        ], "sampling_calls": 0, "decoder_calls": 0}
    out = HERE / "BURST_STEP_CHERNOFF_AUDIT.json"
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": out.name, "rows": rows, "nuisance_minima": nuisance,
        "validation": validation}, indent=2))


if __name__ == "__main__":
    main()
