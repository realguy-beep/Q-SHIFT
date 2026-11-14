"""Conservative continuous alternative log-growth bounds via category envelopes.

Uses exact rational category probability bounds and exact rational log intervals,
then interval-products each of six terms. Population analysis only; no streams.
"""
from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import categorical_circuit_parameter_grid_audit as grid
import cofire_category_continuous_envelope as polytools


HERE = Path(__file__).resolve().parent
MEAN_CERT = HERE / "EXACT_BURST_MEASUREMENT_RECTANGLE_CERTIFICATE.json"
PB_UP_ALT = (Fraction(10, 1000), Fraction(18, 1000))
PB_DOWN_ALT = (Fraction(0), Fraction(2, 1000))
PM_INTERVAL = (Fraction(1, 1000), Fraction(5, 1000))
SPLITS = 4


def rectangle_probability_bounds(poly, pb_interval, pm_interval, degree_v, degree_u):
    v_global = (1 - 2 * pb_interval[1], 1 - 2 * pb_interval[0])
    u_global = (1 - 2 * pm_interval[1], 1 - 2 * pm_interval[0])
    minimum, maximum = None, None
    for i in range(SPLITS):
        va = v_global[0] + (v_global[1] - v_global[0]) * Fraction(i, SPLITS)
        vb = v_global[0] + (v_global[1] - v_global[0]) * Fraction(i + 1, SPLITS)
        for j in range(SPLITS):
            ua = u_global[0] + (u_global[1] - u_global[0]) * Fraction(j, SPLITS)
            ub = u_global[0] + (u_global[1] - u_global[0]) * Fraction(j + 1, SPLITS)
            coeffs = polytools.bernstein_coefficients(poly, va, vb, ua, ub, degree_v, degree_u)
            cell_min, cell_max = min(map(min, coeffs)), max(map(max, coeffs))
            minimum = cell_min if minimum is None else min(minimum, cell_min)
            maximum = cell_max if maximum is None else max(maximum, cell_max)
    return max(Fraction(0), minimum), maximum


def expected_log_lower(prob_bounds, log_bounds):
    total = Fraction(0)
    rows = []
    for c, ((p_lo, p_hi), (l_lo, l_hi)) in enumerate(zip(prob_bounds, log_bounds)):
        products = (p_lo * l_lo, p_lo * l_hi, p_hi * l_lo, p_hi * l_hi)
        term_lower = min(products)
        total += term_lower
        rows.append({"category": c, "p_lower": float(p_lo), "p_upper": float(p_hi), "log_lower": float(l_lo), "log_upper": float(l_hi), "term_lower": float(term_lower)})
    return total, rows


def bounded_log_factors(m: Fraction, lam: Fraction, complement: bool = False):
    logs = []
    for c in range(6):
        x = Fraction(c, 5)
        if complement:
            x = 1 - x
        factor = 1 + lam * (x / m - 1)
        if factor <= 0:
            raise RuntimeError("nonpositive e-factor increment")
        logs.append(polytools.log_rational_interval(factor))
    return logs


def main() -> None:
    mean = json.loads(MEAN_CERT.read_text(encoding="utf-8"))["certified_continuous_bounds"]
    low_null_x = Fraction(int(mean["null_mean_maximum"]["exact_fraction"]["numerator"]), int(mean["null_mean_maximum"]["exact_fraction"]["denominator"]))
    high_min_x = Fraction(int(mean["alternative_mean_minimum"]["exact_fraction"]["numerator"]), int(mean["alternative_mean_minimum"]["exact_fraction"]["denominator"]))
    margin = Fraction(1, 10**10)
    m_up = low_null_x + margin
    m_down = 1 - high_min_x + margin

    template_circuit = grid.construct(0.010, 0.003)
    polys, _meta = polytools.category_polynomials(template_circuit)
    degree_v = max(j for p in polys for j, _ in p)
    degree_u = max(k for p in polys for _, k in p)

    up_prob = [rectangle_probability_bounds(p, PB_UP_ALT, PM_INTERVAL, degree_v, degree_u) for p in polys]
    down_prob = [rectangle_probability_bounds(p, PB_DOWN_ALT, PM_INTERVAL, degree_v, degree_u) for p in polys]

    candidates = []
    for lam in (Fraction(1, 1000), Fraction(3, 1000), Fraction(5, 1000)):
        up_lower, up_terms = expected_log_lower(up_prob, bounded_log_factors(m_up, lam))
        down_lower, down_terms = expected_log_lower(down_prob, bounded_log_factors(m_down, lam, complement=True))
        candidates.append({
            "lambda": float(lam),
            "upward_uniform_expected_log_lower_bound": float(up_lower),
            "upward_strictly_positive": up_lower > 0,
            "upward_category_term_bounds": up_terms,
            "downward_uniform_expected_log_lower_bound": float(down_lower),
            "downward_strictly_positive": down_lower > 0,
            "downward_category_term_bounds": down_terms,
        })

    result = {
        "classification": "RATIONAL_BERNSTEIN_CATEGORY_INTERVAL_LOG_GROWTH_CERTIFICATES",
        "parameter_regions": {"upward_alternative": [float(x) for x in PB_UP_ALT], "downward_alternative": [float(x) for x in PB_DOWN_ALT], "measurement_interval": [float(x) for x in PM_INTERVAL]},
        "bernstein_partition": [SPLITS, SPLITS],
        "polynomial_degrees": [degree_v, degree_u],
        "mean_null_bounds_plus_margin": {"upward_x": float(m_up), "downward_complement_y": float(m_down)},
        "log_interval_method": "20-term exact rational atanh series with explicit tail bound; six log factors",
        "expected_log_lower_method": "For each category, exact Bernstein lower/upper probability bounds times the rational log interval; sum the least endpoint product across the six terms.",
        "lambda_candidates": candidates,
        "limitations": [
            "Exact categorical circuit only; fixed gate p=.003, measurement p in [.001,.005], independent per-shot mechanisms.",
            "Bernstein category intervals are conservative and may be loose; these bounds do not measure finite-sample delay.",
            "No e-process, threshold, alarm, graph switch, decoder outcome, or logical error was evaluated.",
        ],
    }
    out = HERE / "MEAN_EFACTOR_CONTINUOUS_LOG_GROWTH_AUDIT.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for row in candidates:
        print("lambda", row["lambda"], "up", row["upward_uniform_expected_log_lower_bound"], "down", row["downward_uniform_expected_log_lower_bound"])
    print(f"wrote={out}")


if __name__ == "__main__":
    main()
