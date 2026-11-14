"""Rational continuous null envelopes for five-pair cofire-count categories.

This derives exact categorical-circuit population polynomials and bounds each
category over a continuous burst/measurement rectangle with tensor Bernstein
coefficients. It generates no histories and runs no detector or decoder.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
from fractions import Fraction
from pathlib import Path

import numpy as np

import burst_step_information_audit as joint
import categorical_circuit_parameter_grid_audit as grid
import categorical_circuit_feature_expectations as features


HERE = Path(__file__).resolve().parent
PAIRS = ((8, 10), (16, 18), (24, 26), (32, 34), (36, 38))
PB_INTERVAL = (Fraction(0), Fraction(2, 1000))
PM_INTERVAL = (Fraction(1, 1000), Fraction(5, 1000))
PB_ALT = (Fraction(10, 1000), Fraction(14, 1000), Fraction(18, 1000))
PM_GRID = tuple(Fraction(i, 1000) for i in range(1, 6))
REF = (Fraction(10, 1000), Fraction(3, 1000))
AUDIT_GRID = np.linspace(0.0, 0.002, 101)
PM_AUDIT_GRID = np.linspace(0.001, 0.005, 101)


def add(a: dict[tuple[int, int], Fraction], b: dict[tuple[int, int], Fraction], scale: Fraction = Fraction(1)) -> dict[tuple[int, int], Fraction]:
    out = dict(a)
    for key, value in b.items():
        out[key] = out.get(key, Fraction(0)) + scale * value
        if out[key] == 0:
            del out[key]
    return out


def all_character_polynomials(raw_sites: list, mapped_sites: list, names: list[str]) -> dict[int, tuple[Fraction, int, int]]:
    """Build all ten-bit parity characters using integer products over dyadic factors."""
    site_data = []
    for raw, (_identity_probability, mapped_alts) in zip(raw_sites, mapped_sites):
        instruction_index = raw[0]
        name = names[instruction_index]
        alts = []
        for probability, support, _obs, _paulis in mapped_alts:
            mask = sum(1 << k for j, pair in enumerate(PAIRS) for side, detector in enumerate(pair)
                       if detector in support for k in (2 * j + side,))
            alts.append((Fraction.from_float(float(probability)), mask))
        site_data.append((name, alts))
    result = {}
    for selected_mask in range(1 << (2 * len(PAIRS))):
        numerator, denominator_power = 1, 0
        pb_degree = pm_degree = 0
        for name, alts in site_data:
            odd_probability = sum((prob for prob, alt_mask in alts
                                   if (selected_mask & alt_mask).bit_count() % 2), Fraction(0))
            if name == "E":
                if odd_probability:
                    if odd_probability != Fraction.from_float(0.01):
                        raise RuntimeError("burst site probability or ordering did not match the circuit template")
                    pb_degree += 1
            elif name == "X_ERROR":
                if odd_probability:
                    pm_degree += 1
            else:
                factor = 1 - 2 * odd_probability
                d = factor.denominator
                if d & (d - 1):
                    raise RuntimeError("fixed channel factor was not dyadic")
                numerator *= factor.numerator
                denominator_power += d.bit_length() - 1
        result[selected_mask] = (Fraction(numerator, 1 << denominator_power), pb_degree, pm_degree)
    return result


def category_polynomials(circuit) -> tuple[list[dict[tuple[int, int], Fraction]], dict]:
    mapped_sites, meta = features.categorical_sites(circuit)
    raw_sites = features.extract_sites(circuit)
    if len(mapped_sites) != len(raw_sites):
        raise RuntimeError("raw and mapped categorical site counts differ")
    names = [inst.name for inst in circuit]
    chars = all_character_polynomials(raw_sites, mapped_sites, names)
    print("parity_characters_built", flush=True)

    moments: dict[int, dict[tuple[int, int], Fraction]] = {}
    for pair_mask in range(1 << len(PAIRS)):
        pair_indices = [j for j in range(len(PAIRS)) if pair_mask & (1 << j)]
        detector_indices = [i for j in pair_indices for i in (2 * j, 2 * j + 1)]
        moment: dict[tuple[int, int], Fraction] = {}
        for parity_mask in range(1 << len(detector_indices)):
            selected_detector_indices = [detector_indices[k] for k in range(len(detector_indices)) if parity_mask & (1 << k)]
            # Selected detector indices map to the canonical detector IDs in PAIRS.
            detector_mask = sum(1 << k for k in selected_detector_indices)
            coefficient, pb_degree, pm_degree = chars[detector_mask]
            term = {(pb_degree, pm_degree): coefficient / (1 << len(detector_indices))}
            moment = add(moment, term, Fraction(-1 if parity_mask.bit_count() % 2 else 1))
        moments[pair_mask] = moment

    joint_pattern: dict[int, dict[tuple[int, int], Fraction]] = {}
    for observed_mask in range(1 << len(PAIRS)):
        law: dict[tuple[int, int], Fraction] = {}
        for superset in range(1 << len(PAIRS)):
            if (superset & observed_mask) != observed_mask:
                continue
            sign = -1 if (superset.bit_count() - observed_mask.bit_count()) % 2 else 1
            law = add(law, moments[superset], Fraction(sign))
        joint_pattern[observed_mask] = law

    categories = [dict() for _ in range(len(PAIRS) + 1)]
    for mask, law in joint_pattern.items():
        k = mask.bit_count()
        categories[k] = add(categories[k], law)
    # Identically normalized law is a strong algebraic guard.
    total: dict[tuple[int, int], Fraction] = {}
    for law in categories:
        total = add(total, law)
    if total != {(0, 0): Fraction(1)}:
        raise RuntimeError(f"category law does not normalize identically: {total}")
    return categories, meta


def evaluate(poly: dict[tuple[int, int], Fraction], pb: Fraction, pm: Fraction) -> Fraction:
    v, u = 1 - 2 * pb, 1 - 2 * pm
    return sum((coef * v**j * u**k for (j, k), coef in poly.items()), Fraction(0))


def evaluate_grid(poly: dict[tuple[int, int], Fraction], pb: np.ndarray, pm: np.ndarray) -> np.ndarray:
    v, u = 1 - 2 * pb, 1 - 2 * pm
    out = np.zeros((len(pb), len(pm)))
    for (j, k), coefficient in poly.items():
        out += float(coefficient) * v[:, None]**j * u[None, :]**k
    return out


def bernstein_coefficients(poly: dict[tuple[int, int], Fraction], v0: Fraction, v1: Fraction, u0: Fraction, u1: Fraction, degree_v: int, degree_u: int) -> list[list[Fraction]]:
    h_v, h_u = v1 - v0, u1 - u0
    power = [[Fraction(0) for _ in range(degree_u + 1)] for _ in range(degree_v + 1)]
    for (j, k), coefficient in poly.items():
        for i in range(j + 1):
            a = coefficient * math.comb(j, i) * v0 ** (j - i) * h_v**i
            for ell in range(k + 1):
                power[i][ell] += a * math.comb(k, ell) * u0 ** (k - ell) * h_u**ell
    bern = [[Fraction(0) for _ in range(degree_u + 1)] for _ in range(degree_v + 1)]
    for r in range(degree_v + 1):
        for s in range(degree_u + 1):
            bern[r][s] = sum((power[i][ell] * Fraction(math.comb(r, i), math.comb(degree_v, i))
                              * Fraction(math.comb(s, ell), math.comb(degree_u, ell))
                              for i in range(r + 1) for ell in range(s + 1)), Fraction(0))
    return bern


def upper_bound(poly: dict[tuple[int, int], Fraction], degree_v: int, degree_u: int, splits: int = 4) -> tuple[Fraction, Fraction]:
    v_global = (1 - 2 * PB_INTERVAL[1], 1 - 2 * PB_INTERVAL[0])
    u_global = (1 - 2 * PM_INTERVAL[1], 1 - 2 * PM_INTERVAL[0])
    best = None
    min_lower = None
    for i in range(splits):
        va = v_global[0] + (v_global[1] - v_global[0]) * Fraction(i, splits)
        vb = v_global[0] + (v_global[1] - v_global[0]) * Fraction(i + 1, splits)
        for j in range(splits):
            ua = u_global[0] + (u_global[1] - u_global[0]) * Fraction(j, splits)
            ub = u_global[0] + (u_global[1] - u_global[0]) * Fraction(j + 1, splits)
            bern = bernstein_coefficients(poly, va, vb, ua, ub, degree_v, degree_u)
            cell_max = max(max(row) for row in bern)
            cell_min = min(min(row) for row in bern)
            best = cell_max if best is None else max(best, cell_max)
            min_lower = cell_min if min_lower is None else min(min_lower, cell_min)
    return best, min_lower


def log_rational_interval(x: Fraction, terms: int = 20) -> tuple[Fraction, Fraction]:
    """Rigorous ln(x) interval using the positive atanh series and a tail bound."""
    if x <= 0:
        raise ValueError("log interval requires positive rational")

    def atanh_log(z: Fraction) -> tuple[Fraction, Fraction]:
        partial = sum((2 * z ** (2 * n + 1) / (2 * n + 1) for n in range(terms)), Fraction(0))
        tail = 2 * z ** (2 * terms + 1) / ((2 * terms + 1) * (1 - z * z))
        return partial, partial + tail

    exponent = 0
    reduced = x
    while reduced >= 2:
        reduced /= 2
        exponent += 1
    while reduced < 1:
        reduced *= 2
        exponent -= 1
    z = (reduced - 1) / (reduced + 1)
    lo_y, hi_y = atanh_log(z)
    lo_2, hi_2 = atanh_log(Fraction(1, 3))
    if exponent >= 0:
        return lo_y + exponent * lo_2, hi_y + exponent * hi_2
    return lo_y + exponent * hi_2, hi_y + exponent * lo_2


def expected_log_bernstein_bounds(polys: list[dict[tuple[int, int], Fraction]], log_intervals: list[tuple[Fraction, Fraction]], degree_v: int, degree_u: int, splits: int = 1) -> tuple[Fraction, Fraction]:
    v_global = (1 - 2 * Fraction(18, 1000), 1 - 2 * Fraction(10, 1000))
    u_global = (1 - 2 * PM_INTERVAL[1], 1 - 2 * PM_INTERVAL[0])
    global_lo, global_hi = None, None
    for i in range(splits):
        va = v_global[0] + (v_global[1] - v_global[0]) * Fraction(i, splits)
        vb = v_global[0] + (v_global[1] - v_global[0]) * Fraction(i + 1, splits)
        for j in range(splits):
            ua = u_global[0] + (u_global[1] - u_global[0]) * Fraction(j, splits)
            ub = u_global[0] + (u_global[1] - u_global[0]) * Fraction(j + 1, splits)
            category_bern = [bernstein_coefficients(poly, va, vb, ua, ub, degree_v, degree_u) for poly in polys]
            for r in range(degree_v + 1):
                for s in range(degree_u + 1):
                    lo = Fraction(0)
                    hi = Fraction(0)
                    for c, (log_lo, log_hi) in enumerate(log_intervals):
                        coefficient = category_bern[c][r][s]
                        if coefficient >= 0:
                            lo += coefficient * log_lo
                            hi += coefficient * log_hi
                        else:
                            lo += coefficient * log_hi
                            hi += coefficient * log_lo
                    global_lo = lo if global_lo is None else min(global_lo, lo)
                    global_hi = hi if global_hi is None else max(global_hi, hi)
    return global_lo, global_hi


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--certify-alt-growth", action="store_true",
                        help="run the optional, expensive exact continuous expected-log Bernstein enclosure")
    args = parser.parse_args()
    template_circuit = grid.construct(float(REF[0]), float(REF[1]))
    exact_polys, meta = category_polynomials(template_circuit)
    print("category_polynomials_built", flush=True)
    degree_v = max((j for poly in exact_polys for j, _ in poly), default=0)
    degree_u = max((k for poly in exact_polys for _, k in poly), default=0)
    bounds = [upper_bound(poly, degree_v, degree_u) for poly in exact_polys]
    upper = [bound[0] for bound in bounds]
    null_category_grid = np.stack([evaluate_grid(poly, AUDIT_GRID, PM_AUDIT_GRID) for poly in exact_polys], axis=-1)
    if np.min(null_category_grid) < -2e-12 or np.max(np.abs(null_category_grid.sum(axis=-1) - 1)) > 2e-12:
        raise RuntimeError("dense polynomial null grid failed nonnegativity or normalization")
    sampled_category_max = null_category_grid.max(axis=(0, 1))
    if any(u <= 0 for u in upper):
        raise RuntimeError("nonpositive certified category upper envelope")

    q_reference = [evaluate(poly, *REF) for poly in exact_polys]
    if sum(q_reference, Fraction(0)) != 1:
        raise RuntimeError("reference proposal q does not normalize exactly")
    alt_points = [(pb, pm) for pb in PB_ALT for pm in PM_GRID]
    q_mixture = [sum((evaluate(poly, pb, pm) for pb, pm in alt_points), Fraction(0)) / len(alt_points) for poly in exact_polys]
    if sum(q_mixture, Fraction(0)) != 1:
        raise RuntimeError("mixture proposal q does not normalize exactly")

    proposals = {}
    continuous_growth_certificates = {}
    for label, q in (("reference_pb010_pm003", q_reference), ("uniform_grid_alt_mixture", q_mixture)):
        ef = [q[k] / upper[k] for k in range(6)]
        if args.certify_alt_growth:
            log_intervals = [log_rational_interval(value) for value in ef]
            growth_lo, growth_hi = expected_log_bernstein_bounds(exact_polys, log_intervals, degree_v, degree_u)
            continuous_growth_certificates[label] = {
                "partition": [1, 1],
                "log_bounds": "20-term exact rational atanh series with explicit positive tail bound; ln(2) range reduction for each positive rational q_c/U_c",
                "minimum_expected_log_lower_bound_nats_per_shot": float(growth_lo),
                "maximum_expected_log_upper_bound_nats_per_shot": float(growth_hi),
                "strictly_positive_lower_bound_certified": growth_lo > 0,
            }
        null_e_grid = np.einsum("ijk,k->ij", null_category_grid, np.array([float(x) for x in ef]))
        null_e_max = float(null_e_grid.max())
        alt_growth = []
        alt_values = []
        log_factor = np.log(np.array([float(x) for x in ef]))
        for pb in PB_ALT:
            laws = np.stack([evaluate_grid(poly, np.array([float(pb)]), PM_AUDIT_GRID)[0] for poly in exact_polys], axis=-1)
            growth = laws @ log_factor
            alt_values.extend(growth.tolist())
            alt_growth.extend({"pb": float(pb), "pm": float(pm), "expected_log_increment_nats_per_shot": float(val)}
                              for pm, val in zip(PM_AUDIT_GRID, growth))
        proposals[label] = {
            "proposal_q": [float(x) for x in q],
            "certified_e_factor_q_over_upper": [float(x) for x in ef],
            "exact_q_sums_to_one": sum(q, Fraction(0)) == 1,
            "max_null_expected_e_on_101x101_polynomial_grid": float(null_e_max),
            "min_alt_expected_log_increment_on_grid": float(min(alt_values)),
            "max_alt_expected_log_increment_on_grid": float(max(alt_values)),
            "alternative_growth_grid": alt_growth,
        }

    mean_certificate = json.loads((HERE / "EXACT_BURST_MEASUREMENT_RECTANGLE_CERTIFICATE.json").read_text(encoding="utf-8"))
    m0_data = mean_certificate["certified_continuous_bounds"]["null_mean_maximum"]["exact_fraction"]
    m0 = Fraction(int(m0_data["numerator"]), int(m0_data["denominator"]))
    scalar_m = float(m0) + 1e-10
    scalar_lambda = 0.036
    scalar_log_growth = []
    for pb in PB_ALT:
        for pm in PM_AUDIT_GRID:
            law = np.array([evaluate_grid(poly, np.array([float(pb)]), np.array([pm]))[0, 0] for poly in exact_polys])
            xvals = np.arange(6) / 5
            increments = 1 + scalar_lambda * (xvals / scalar_m - 1)
            scalar_log_growth.append(float(law @ np.log(increments)))

    # Independent direct-XOR cross-checks against the existing ten-bit law.
    mapped, _ = features.categorical_sites(template_circuit)
    validations = []
    for pb, pm in ((0.0005, 0.001), (0.001, 0.003), (0.002, 0.005), (0.01, 0.003), (0.018, 0.005)):
        direct = compress_direct(joint.exact_circuit_distribution(mapped, pb, pm))
        analytic = np.array([float(evaluate(poly, Fraction.from_float(pb), Fraction.from_float(pm))) for poly in exact_polys])
        err = float(np.max(np.abs(direct - analytic)))
        validations.append({"pb": pb, "pm": pm, "max_abs_category_error_vs_direct_xor": err})
        if err > 2e-12:
            raise RuntimeError(f"category-polynomial cross-check failed at {pb}/{pm}: {err}")

    result = {
        "classification": "EXACT_CATEGORICAL_CIRCUIT_CONTINUOUS_CATEGORY_ENVELOPES",
        "model": "d=3 five-round rotated Z-memory categorical circuit; gate p=.003; measurement p in [.001,.005]; burst p in [0,.002]",
        "statistic": "C in 0..5, count of five documented disjoint within-pair detector cofires",
        "polynomial_basis": "Exact rational coefficients in v=1-2*p_b and u=1-2*p_m, derived from categorical parity characters and Bernoulli subset inversion.",
        "degrees": {"burst_variable_v": degree_v, "measurement_variable_u": degree_u},
        "bernstein_partition": {"burst_axis_splits": 4, "measurement_axis_splits": 4, "method": "On each rectangle, every polynomial value is in the convex hull of its tensor-product Bernstein coefficients; category upper envelope is the maximum coefficient across all cells."},
        "population_grid": {"burst_null_grid": [0.0, 0.002, len(AUDIT_GRID)], "measurement_grid": [0.001, 0.005, len(PM_AUDIT_GRID)], "purpose": "Diagnostics for envelope slack and growth; continuous null validity follows from Bernstein bounds, not grid coverage."},
        "mapping_metadata": meta,
        "category_envelopes": [
            {"category": i, "upper_bound_exact_fraction": {"numerator": str(upper[i].numerator), "denominator": str(upper[i].denominator)}, "upper_bound": float(upper[i]), "minimum_bernstein_coefficient_over_partition": float(bounds[i][1]), "sampled_null_grid_max_101x101": float(sampled_category_max[i]), "nonnegative_slack_upper_minus_grid_max": max(0.0, float(upper[i]) - float(sampled_category_max[i])), "floating_grid_excess_over_upper": max(0.0, float(sampled_category_max[i]) - float(upper[i])), "reference_q": float(q_reference[i]), "mixture_q": float(q_mixture[i])}
            for i in range(6)
        ],
        "sum_category_upper_bounds": float(sum(upper, Fraction(0))),
        "proposals": proposals,
        "continuous_alternative_expected_log_certificates": continuous_growth_certificates or None,
        "continuous_alternative_growth_status": "only calculated when --certify-alt-growth is supplied; the recorded attempt was interrupted before completion and supplies no continuous lower bound",
        "scalar_mean_eincrement_comparison": {
            "source": "exact continuous pair-cofire mean certificate plus fixed lambda=.036",
            "m": scalar_m,
            "lambda": scalar_lambda,
            "minimum_expected_log_increment_on_same_alternative_grid": min(scalar_log_growth),
            "maximum_expected_log_increment_on_same_alternative_grid": max(scalar_log_growth),
            "interpretation": "Deterministic population comparison only. The scalar mean increment remains the simpler primary candidate; the category-wise proposal is a valid alternative construction under the same certified null but is not shown to improve drift or decoder utility.",
        },
        "direct_xor_cross_validation": validations,
        "conditional_validity_argument": "For any predictable exact-circuit null parameter in the declared rectangle, each category probability is at most its certified U_c. For any fixed proposal distribution q on the six categories, L(C)=q(C)/U_C is nonnegative and E[L|past]=sum_c P(C=c|past)q(c)/U_c <= sum_c q(c)=1. Thus it is a one-step e-factor under the exact stated conditional model; products (or predictable mixtures) form an e-process. This is a mathematical construction only, not an implemented or run detector.",
        "limitations": ["Fixed gate noise and exact categorical circuit only; no correlated-readout, gate drift, model error, or unknown circuit topology.", "The approximate DEM receives no continuous category-envelope certificate here.", "Expected log increments are population calculations; no finite-history delay, ARL, switching risk, logical error, or decoder utility was evaluated.", "Finite Bernstein subdivision yields rigorous upper bounds but may be conservative; a positive minimum log-growth is reported only on the specified alternative grid, not continuously over the alternative rectangle."],
    }
    out = HERE / "COFIRE_CATEGORY_CONTINUOUS_ENVELOPE_CERTIFICATE.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("degrees", degree_v, degree_u, "sum_upper", result["sum_category_upper_bounds"], "continuous_alt_growth_certified", bool(continuous_growth_certificates))
    for label, row in proposals.items():
        print(label, "min_alt_log", row["min_alt_expected_log_increment_on_grid"], "max_null_grid_e", row["max_null_expected_e_on_101x101_polynomial_grid"])
    print("validation_max", max(v["max_abs_category_error_vs_direct_xor"] for v in validations))
    print(f"wrote={out}")


def compress_direct(prob: np.ndarray) -> np.ndarray:
    states = np.arange(1 << len(joint.SELECTED), dtype=np.uint16)
    bits = (states[:, None] >> np.arange(len(joint.SELECTED))) & 1
    count = sum(bits[:, 2 * k] * bits[:, 2 * k + 1] for k in range(5))
    return np.bincount(count, weights=prob, minlength=6)


if __name__ == "__main__":
    main()
