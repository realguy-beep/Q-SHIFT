"""Rational Bernstein-sign certificate over the exact circuit p_b,p_m rectangle."""
from __future__ import annotations

import json
import math
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import categorical_circuit_parameter_grid_audit as grid
import categorical_circuit_feature_expectations as features
from measurement_nuisance_mean_certificate import (
    GATE_P, MEASUREMENT_TEMPLATE, PAIRS, PM_INTERVAL, character_coeff,
    derivative_bernstein, evaluate, polynomial_coefficients,
)


BURST_ENDPOINTS = (0.002, 0.010, 0.018)
PM_PROBES = (0.001, 0.003, 0.005)


def get_poly(burst_p: float) -> tuple[list[Fraction], dict]:
    circuit = grid.construct(burst_p, MEASUREMENT_TEMPLATE)
    mapped, meta = features.categorical_sites(circuit)
    raw = features.extract_sites(circuit)
    if len(mapped) != len(raw):
        raise RuntimeError("raw/mapped site count mismatch")
    expected = [list(pair) for pair in PAIRS]
    if meta["burst_detector_supports"] != expected:
        raise RuntimeError(f"burst support structure changed: {meta['burst_detector_supports']}")
    categories = [(r[0], m[1]) for r, m in zip(raw, mapped)]
    names = [inst.name for inst in circuit]
    supports = sorted({(a,) for pair in PAIRS for a in pair} | {tuple(pair) for pair in PAIRS})
    chars = {s: character_coeff(categories, names, s) for s in supports}
    return polynomial_coefficients(chars), mapped, meta


def bernstein_coefficients(poly: list[Fraction], a: Fraction, b: Fraction) -> list[Fraction]:
    """Convert a power-basis polynomial in u to Bernstein coefficients on [a,b]."""
    n = len(poly) - 1
    h = b - a
    power_t = []
    for k in range(n + 1):
        value = Fraction(0)
        for j in range(k, n + 1):
            value += poly[j] * math.comb(j, k) * (a ** (j - k)) * (h ** k)
        power_t.append(value)
    return [
        sum((power_t[j] * Fraction(math.comb(i, j), math.comb(n, j)) for j in range(i + 1)), Fraction(0))
        for i in range(n + 1)
    ]


def difference(left: list[Fraction], right: list[Fraction]) -> list[Fraction]:
    n = max(len(left), len(right))
    return [(left[i] if i < len(left) else Fraction(0)) - (right[i] if i < len(right) else Fraction(0)) for i in range(n)]


def main() -> None:
    u_lo, u_hi = 1 - 2 * PM_INTERVAL[1], 1 - 2 * PM_INTERVAL[0]
    polynomials = {}
    rows = []
    for pb in BURST_ENDPOINTS:
        poly, mapped_sites, meta = get_poly(pb)
        polynomials[pb] = poly
        deriv = [Fraction(i + 1) * poly[i + 1] for i in range(len(poly) - 1)]
        deriv_bern = bernstein_coefficients(deriv, u_lo, u_hi)
        all_neg = all(c < 0 for c in deriv_bern)
        all_pos = all(c > 0 for c in deriv_bern)
        if not (all_neg or all_pos):
            raise RuntimeError(f"measurement monotonicity not certified at burst p={pb}")
        discrepancies = []
        for pm in PM_PROBES:
            u = 1 - 2 * Fraction.from_float(pm)
            predicted = float(evaluate(poly, u))
            c = grid.construct(pb, pm)
            mean = features.means_from_characters(grid.reweight(mapped_sites, c))
            reference = float(np.mean(mean[40:45]))
            discrepancies.append({"measurement_p": pm, "polynomial_mean": predicted, "feature_mean": reference, "difference": predicted - reference})
            if abs(predicted - reference) > 2e-12:
                raise RuntimeError(f"polynomial validation mismatch at pb={pb},pm={pm}")
        rows.append({
            "burst_p": pb,
            "degree": len(poly) - 1,
            "measurement_derivative_bernstein_all_negative": all_neg,
            "measurement_derivative_bernstein_all_positive": all_pos,
            "measurement_derivative_bernstein_min_max": [float(min(deriv_bern)), float(max(deriv_bern))],
            "monotonicity": "increasing in pm" if all_neg else "decreasing in pm",
            "validation": discrepancies,
            "burst_mapping_metadata": meta,
        })

    gap_polys = {
        "alternative_010_minus_null_002": difference(polynomials[0.010], polynomials[0.002]),
        "alternative_018_minus_010": difference(polynomials[0.018], polynomials[0.010]),
    }
    gaps = {}
    for label, poly in gap_polys.items():
        bern = bernstein_coefficients(poly, u_lo, u_hi)
        if not all(c > 0 for c in bern):
            raise RuntimeError(f"burst rectangle mean gap not certified positive: {label}")
        gaps[label] = {"all_bernstein_coefficients_positive": True, "coefficient_min_max": [float(min(bern)), float(max(bern))]}

    null = polynomials[0.002]
    null_max_fraction = evaluate(null, 1 - 2 * PM_INTERVAL[1])
    alt_min_fraction = evaluate(polynomials[0.010], 1 - 2 * PM_INTERVAL[0])
    null_max = float(null_max_fraction)
    alt_min = float(alt_min_fraction)
    result = {
        "classification": "EXACT_CATEGORICAL_CIRCUIT_CONTINUOUS_RECTANGLE_CERTIFICATE",
        "configuration": {"gate_p": GATE_P, "burst_null_interval": [0.0, 0.002], "alternative_burst_interval": [0.010, 0.018], "measurement_interval": [float(PM_INTERVAL[0]), float(PM_INTERVAL[1])]},
        "derivation": "Each pair's five-round selected detector support intersects exactly one burst site, and that burst site flips both pair detectors; its simultaneous two-bit flip has even parity in that pair. The pair-cofire mean is therefore affine in the common burst probability. The certified positive gap g(.010,pm)-g(.002,pm) establishes positive slope, extending the null maximum at .002 to the whole interval [0,.002], including the analytic pb=0 limit even though the circuit builder omits a zero-probability instruction. Measurement-error X_ERROR sites contribute powers of u=1-2pm; the resulting degree-8 polynomial and Bernstein sign checks are computed with Fraction arithmetic.",
        "burst_endpoint_monotonicity_and_cross_validation": rows,
        "alternative_minus_null_gap_certificates": gaps,
        "certified_continuous_bounds": {
            "null_mean_maximum": {"burst_p_interval": [0.0, 0.002], "maximizer_burst_p": 0.002, "measurement_p": 0.005, "mean": null_max, "exact_fraction": {"numerator": str(null_max_fraction.numerator), "denominator": str(null_max_fraction.denominator)}},
            "alternative_mean_minimum": {"burst_p": 0.010, "measurement_p": 0.001, "mean": alt_min, "exact_fraction": {"numerator": str(alt_min_fraction.numerator), "denominator": str(alt_min_fraction.denominator)}},
            "gap": alt_min - null_max,
        },
        "scope_limits": [
            "Exact categorical circuit only; the approximate DEM has not received a continuous interval certificate.",
            "Gate p is fixed at .003; the burst null is covered only on [0,.002]; other physical or calibration uncertainty is outside this certificate.",
            "This certifies a population conditional-mean envelope and separation, not an implemented e-detector, its delay/ARL, finite-horizon false-switch risk, or decoder benefit.",
        ],
    }
    out = HERE / "EXACT_BURST_MEASUREMENT_RECTANGLE_CERTIFICATE.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"null_max={null_max:.15g} alt_min={alt_min:.15g} gap={alt_min-null_max:.15g}")
    print(f"wrote={out}")


if __name__ == "__main__":
    main()
