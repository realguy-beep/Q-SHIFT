"""Independent exact-rational correction of the checkpoint-133 threshold audit.

This module uses only saved rational certificate parameters and abstract
six-category factor sequences. It never imports Stim or invokes a sampler.
"""
from __future__ import annotations

import itertools
import json
from fractions import Fraction
from pathlib import Path
from typing import Iterable


Q_BITS = 96
SCALE = 1 << Q_BITS
ALPHA = Fraction(1, 20)
HERE = Path(__file__).resolve().parent
CERTIFICATE = HERE.parent / "qshift_method_landscape_research_v1" / "EXACT_THREE_PARAMETER_EFACTOR_ENVELOPE.json"


def fraction_from_record(record: dict) -> Fraction:
    return Fraction(int(record["numerator"]), int(record["denominator"]))


def alarm_exact(e_value: Fraction, alpha: Fraction = ALPHA) -> bool:
    """Test E >= 1/alpha exactly, with no floating-point threshold."""
    if alpha <= 0 or alpha > 1:
        raise ValueError("alpha must be in (0, 1]")
    return e_value >= 1 / alpha


def alarm_fixed(lower_integer: int, alpha: Fraction = ALPHA, scale: int = SCALE) -> bool:
    """Test (lower_integer/scale) >= 1/alpha by integer cross multiplication."""
    if lower_integer < 0 or scale <= 0 or alpha <= 0 or alpha > 1:
        raise ValueError("invalid nonnegative e-value, scale, or alpha")
    # lower/scale >= alpha.denominator/alpha.numerator
    return lower_integer * alpha.numerator >= scale * alpha.denominator


def factor_table(certificate: dict, direction: str) -> list[Fraction]:
    opt = certificate["robust_mean_e_factor_population_analysis"]["endpoint_chord_optimum"][direction]
    lam = fraction_from_record(opt["exact_optimal_lambda"])
    if direction == "upward":
        mean_null = fraction_from_record(
            certificate["robust_mean_e_factor_population_analysis"]["upward"]["exact_null_mean_upper"]
        )
        support_values = (Fraction(k, 5) for k in range(6))
    elif direction == "downward_on_complement":
        mean_null = fraction_from_record(
            certificate["robust_mean_e_factor_population_analysis"]["downward_on_complement_1_minus_X"]["exact_null_mean_upper"]
        )
        support_values = (Fraction(5 - k, 5) for k in range(6))
    else:
        raise ValueError(f"unsupported direction: {direction}")
    return [1 + lam * (value / mean_null - 1) for value in support_values]


def exact_mixture(factors: Iterable[Fraction]) -> Fraction:
    """Direct finite one-change mixture: prior starts s=1..t plus tail mass."""
    factors = tuple(factors)
    t = len(factors)
    if t == 0:
        return Fraction(1)
    total = Fraction(1, t + 1)
    for start in range(1, t + 1):
        product = Fraction(1)
        for value in factors[start - 1 :]:
            product *= value
        total += Fraction(1, start * (start + 1)) * product
    return total


def exact_mixture_recurrence(factors: Iterable[Fraction]) -> list[Fraction]:
    a = Fraction(0)
    out = []
    for t, factor in enumerate(factors, start=1):
        a = factor * (a + Fraction(1, t * (t + 1)))
        out.append(a + Fraction(1, t + 1))
    return out


def fixedpoint_lower(factors: Iterable[Fraction], scale: int = SCALE) -> list[int]:
    """Return scaled lower e-values, with each nonnegative input rounded down."""
    a = 0
    out = []
    for t, factor in enumerate(factors, start=1):
        l = factor.numerator * scale // factor.denominator
        w = scale // (t * (t + 1))
        remaining = scale // (t + 1)
        a = (l * (a + w)) // scale
        out.append(a + remaining)
    return out


def make_audit(certificate: dict, length: int = 4) -> dict:
    if length < 1:
        raise ValueError("length must be positive")
    directions = []
    for direction in ("upward", "downward_on_complement"):
        factors = factor_table(certificate, direction)
        checked = 0
        exact_crossings = 0
        lower_crossings = 0
        max_exact = Fraction(0)
        max_lower = Fraction(0)
        max_working_product_bits = 0
        distinct_prefixes = 0
        crossings_by_length = [0] * length
        # Enumerate every distinct category prefix of lengths 1..length.
        for t in range(1, length + 1):
            for categories in itertools.product(range(6), repeat=t):
                selected = [factors[k] for k in categories]
                exact_path = exact_mixture_recurrence(selected)
                direct = exact_mixture(selected)
                if exact_path[-1] != direct:
                    raise AssertionError("exact recurrence differs from direct mixture expansion")
                lower_path = fixedpoint_lower(selected)
                exact_value = direct
                lower_value = Fraction(lower_path[-1], SCALE)
                if lower_value > exact_value:
                    raise AssertionError("downward-rounded lower mixture exceeded exact mixture")
                if alarm_fixed(lower_path[-1]) and not alarm_exact(exact_value):
                    raise AssertionError("lower-bound alarm did not imply exact e-value alarm")
                exact_crossings += int(alarm_exact(exact_value))
                lower_crossings += int(alarm_fixed(lower_path[-1]))
                crossings_by_length[t - 1] += int(alarm_fixed(lower_path[-1]))
                max_exact = max(max_exact, exact_value)
                max_lower = max(max_lower, lower_value)
                l = factors[categories[-1]].numerator * SCALE // factors[categories[-1]].denominator
                w = SCALE // (t * (t + 1))
                a_before = 0 if t == 1 else lower_path[-2] - SCALE // t
                max_working_product_bits = max(max_working_product_bits, (l * (a_before + w)).bit_length())
                checked += 1
                distinct_prefixes += 1
        # Reproduce the old audit's full-length enumeration/prefix loop shape,
        # but count corrected-threshold hits (including repeated suffix copies).
        legacy_prefix_checks = 0
        legacy_prefix_crossings = 0
        full_sequences_with_any_crossing = 0
        for categories in itertools.product(range(6), repeat=length):
            path = fixedpoint_lower([factors[k] for k in categories])
            hit = False
            for t, e_int in enumerate(path, start=1):
                legacy_prefix_checks += 1
                if alarm_fixed(e_int):
                    legacy_prefix_crossings += 1
                    hit = True
            full_sequences_with_any_crossing += int(hit)
        directions.append({
            "direction": direction,
            "factor_rationals": [f"{x.numerator}/{x.denominator}" for x in factors],
            "sequence_length_max": length,
            "distinct_category_prefixes_checked": distinct_prefixes,
            "exact_recurrence_direct_sum_checks": checked,
            "lower_bound_dominance_checks": checked,
            "corrected_fixedpoint_crossings_by_prefix_length": crossings_by_length,
            "correct_alpha": f"{ALPHA.numerator}/{ALPHA.denominator}",
            "correct_alarm_threshold_1_over_alpha": f"{(1/ALPHA).numerator}/{(1/ALPHA).denominator}",
            "exact_mixture_crossing_prefixes": exact_crossings,
            "fixedpoint_lower_crossing_prefixes": lower_crossings,
            "legacy_loop_prefix_checks": legacy_prefix_checks,
            "legacy_loop_corrected_crossing_prefixes_with_suffix_multiplicity": legacy_prefix_crossings,
            "full_length_sequences_with_at_least_one_corrected_crossing": full_sequences_with_any_crossing,
            "maximum_exact_mixture_on_checked_prefixes_decimal": format(float(max_exact), ".17g"),
            "maximum_lower_mixture_on_checked_prefixes_decimal": format(float(max_lower), ".17g"),
            "max_intermediate_integer_product_bits_in_checked_prefixes": max_working_product_bits,
            "integer_semantics": "Python arbitrary-precision integers; no fixed-width overflow claim is made.",
        })
    return {
        "classification": "INDEPENDENT_DETERMINISTIC_EXACT_RATIONAL_THRESHOLD_AND_FIXEDPOINT_AUDIT",
        "source_correction": "The prior predicate compared E_lower with alpha (0.05), not with 1/alpha (20).",
        "correct_integer_predicate": "lower_integer * alpha.numerator >= scale * alpha.denominator",
        "incorrect_checkpoint_133_predicate": "lower_integer * alpha.denominator >= scale * alpha.numerator",
        "fixedpoint_scale": f"2^{Q_BITS}",
        "rounding": "Factor, start weight, and remaining prior tail are rounded downward; recurrence multiplication and division use floor.",
        "directions": directions,
        "boundary_cases": {
            "below": {"e_value": "19", "alarm": alarm_exact(Fraction(19))},
            "at": {"e_value": "20", "alarm": alarm_exact(Fraction(20))},
            "above": {"e_value": "21", "alarm": alarm_exact(Fraction(21))},
        },
        "limitations": [
            "These are exhaustive abstract six-category factor sequences up to the stated short horizon, not detector histories, trajectories, or performance experiments.",
            "Exact threshold correctness does not establish that the proposed factor is conditionally valid for the physical process.",
            "Python integer arithmetic does not validate fixed-width production implementations or an operational horizon.",
        ],
    }


def main() -> None:
    certificate = json.loads(CERTIFICATE.read_text(encoding="utf-8-sig"))
    result = make_audit(certificate)
    output = HERE / "EFACTOR_THRESHOLD_AUDIT_V1.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "output": output.name,
        "directions": [
            {k: v for k, v in row.items() if k in (
                "direction", "distinct_category_prefixes_checked",
                "exact_mixture_crossing_prefixes", "fixedpoint_lower_crossing_prefixes",
                "legacy_loop_corrected_crossing_prefixes_with_suffix_multiplicity",
                "full_length_sequences_with_at_least_one_corrected_crossing",
                "maximum_exact_mixture_on_checked_prefixes_decimal",
            )}
            for row in result["directions"]
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
