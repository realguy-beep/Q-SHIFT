"""Exact-circuit derivative sign certificate for the bounded pair mean.

Uses categorical parity-character products and exact rational arithmetic on
the fixed non-measurement site probabilities. No histories are generated.
"""
from __future__ import annotations

import json
import math
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for path in (ROOT, ROOT / "outputs" / "phase3a_correlated_noise_preflight"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import categorical_circuit_parameter_grid_audit as grid
import categorical_circuit_feature_expectations as exact_features


PB = 0.002
GATE_P = 0.003
MEASUREMENT_TEMPLATE = 0.003
PM_INTERVAL = (Fraction(1, 1000), Fraction(5, 1000))
PAIRS = ((8, 10), (16, 18), (24, 26), (32, 34), (36, 38))


def character_coeff(site_categories, instruction_names, support: tuple[int, ...]) -> tuple[Fraction, int]:
    selected = set(support)
    constant = Fraction(1)
    exponent = 0
    for instruction_index, alternatives in site_categories:
        name = instruction_names[instruction_index]
        odd_probability = sum(
            (Fraction.from_float(float(probability))
             for probability, detector_support, _, _ in alternatives
             if len(selected.intersection(detector_support)) % 2),
            Fraction(0),
        )
        if name == "X_ERROR":
            if odd_probability not in (Fraction(0), Fraction.from_float(MEASUREMENT_TEMPLATE)):
                raise RuntimeError(f"unexpected measurement-site probability {odd_probability}")
            if odd_probability:
                exponent += 1
        else:
            constant *= 1 - 2 * odd_probability
    return constant, exponent


def polynomial_coefficients(chars: dict[tuple[int, ...], tuple[Fraction, int]]) -> list[Fraction]:
    # g(u) = E[X] = (1/20) sum_pairs [1 - chi_a(u) - chi_b(u) + chi_ab(u)].
    coeffs: list[Fraction] = [Fraction(0)]
    coeffs[0] = Fraction(len(PAIRS), 20)
    for a, b in PAIRS:
        for support, sign in (((a,), -1), ((b,), -1), ((a, b), 1)):
            c, k = chars[support]
            while len(coeffs) <= k:
                coeffs.append(Fraction(0))
            coeffs[k] += Fraction(sign, 20) * c
    while len(coeffs) > 1 and coeffs[-1] == 0:
        coeffs.pop()
    return coeffs


def derivative_bernstein(coeffs: list[Fraction], a: Fraction, b: Fraction) -> list[Fraction]:
    # Convert q(u)=g'(u), u=a+(b-a)t, to degree-n Bernstein coefficients.
    deriv = [Fraction(i + 1) * coeffs[i + 1] for i in range(len(coeffs) - 1)]
    n = len(deriv) - 1
    h = b - a
    power_t = []
    for k in range(n + 1):
        value = Fraction(0)
        for j in range(k, n + 1):
            value += deriv[j] * math.comb(j, k) * (a ** (j - k)) * (h ** k)
        power_t.append(value)
    bernstein = []
    for i in range(n + 1):
        value = Fraction(0)
        for j in range(i + 1):
            value += power_t[j] * Fraction(math.comb(i, j), math.comb(n, j))
        bernstein.append(value)
    return bernstein


def evaluate(coeffs: list[Fraction], u: Fraction) -> Fraction:
    value = Fraction(0)
    for c in reversed(coeffs):
        value = value * u + c
    return value


def main() -> None:
    circuit = grid.construct(PB, MEASUREMENT_TEMPLATE)
    mapped_sites, mapping_meta = exact_features.categorical_sites(circuit)
    raw_sites = exact_features.extract_sites(circuit)
    if len(mapped_sites) != len(raw_sites):
        raise RuntimeError("raw and detector-mapped categorical site counts differ")
    site_categories = [(raw[0], mapped[1]) for raw, mapped in zip(raw_sites, mapped_sites)]
    instruction_names = [inst.name for inst in circuit]
    supports = sorted({(a,) for pair in PAIRS for a in pair} | {tuple(pair) for pair in PAIRS})
    chars = {s: character_coeff(site_categories, instruction_names, s) for s in supports}
    poly = polynomial_coefficients(chars)
    u_lo, u_hi = 1 - 2 * PM_INTERVAL[1], 1 - 2 * PM_INTERVAL[0]
    bernstein = derivative_bernstein(poly, u_lo, u_hi)
    all_negative = all(c < 0 for c in bernstein)
    all_positive = all(c > 0 for c in bernstein)
    if not (all_negative or all_positive):
        monotonicity = "not_certified_by_single_interval_bernstein_coefficients"
        endpoint_max = None
    else:
        monotonicity = "strictly_decreasing_in_u_and_increasing_in_pm" if all_negative else "strictly_increasing_in_u_and_decreasing_in_pm"
        endpoint_pm = PM_INTERVAL[1] if all_negative else PM_INTERVAL[0]
        endpoint_u = 1 - 2 * endpoint_pm
        endpoint_max = float(evaluate(poly, endpoint_u))

    # Independent deterministic comparison against the original feature routine.
    probes = (0.001, 0.003, 0.005)
    validation = []
    for pm in probes:
        u = 1 - 2 * Fraction.from_float(pm)
        predicted = float(evaluate(poly, u))
        probe_circuit = grid.construct(PB, pm)
        means = exact_features.means_from_characters(grid.reweight(site_categories, probe_circuit))
        reference = float(np.mean(means[40:45]))
        err = predicted - reference
        validation.append({"measurement_p": pm, "polynomial_mean": predicted, "independent_feature_mean": reference, "difference": err})
        if abs(err) > 2e-12:
            raise RuntimeError(f"polynomial/reference mismatch at pm={pm}: {err}")

    result = {
        "classification": "EXACT_CATEGORICAL_CIRCUIT_DERIVATIVE_CERTIFICATE",
        "configuration": {"burst_p": PB, "gate_p": GATE_P, "measurement_p_interval": [float(PM_INTERVAL[0]), float(PM_INTERVAL[1])], "pair_supports": [list(x) for x in PAIRS]},
        "formula": "g(u)=E[X]=(1/20) sum_pairs [1-chi_a(u)-chi_b(u)+chi_ab(u)], u=1-2pm; each chi_S=C_S*u^k_S, where C and k are derived from exact categorical sites and odd-support parity.",
        "polynomial_degree": len(poly) - 1,
        "derivative_bernstein_degree": len(bernstein) - 1,
        "derivative_bernstein_signs": {"all_negative": all_negative, "all_positive": all_positive},
        "derivative_bernstein_min_max": [float(min(bernstein)), float(max(bernstein))],
        "monotonicity_certificate": monotonicity,
        "certified_interval_maximum": None if endpoint_max is None else {"measurement_p": float(PM_INTERVAL[1] if all_negative else PM_INTERVAL[0]), "mean": endpoint_max},
        "polynomial_vs_independent_feature_expectation": validation,
        "mapping_metadata": mapping_meta,
        "limitations": [
            "Certificate covers the exact categorical circuit at fixed gate p=.003 and fixed burst p=.002 only.",
            "It does not cover the approximate DEM; DEM probabilities require a separate analysis.",
            "It certifies a conditional mean envelope only under the stated fixed physical model and measurement interval; calibration uncertainty and other nuisance mechanisms are excluded.",
            "It does not itself construct or validate a sequential e-detector, ARL, finite-horizon false-alarm probability, delay, or decoder-switch policy.",
        ],
    }
    output = HERE / "MEASUREMENT_NUISANCE_MEAN_CERTIFICATE.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"degree={result['polynomial_degree']} monotonicity={monotonicity} max={result['certified_interval_maximum']}")
    print(f"validation_max_abs={max(abs(r['difference']) for r in validation):.3g}")
    print(f"wrote={output}")


if __name__ == "__main__":
    main()
