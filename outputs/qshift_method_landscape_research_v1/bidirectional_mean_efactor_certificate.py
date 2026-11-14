"""Analytic up/down mean e-factor bounds from the exact rectangle certificate.

This derives population conditional-mean/log-increment bounds only. It does
not run an e-process, detector history, alarm, graph switch, or decoder.
"""
from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
CERT = HERE / "EXACT_BURST_MEASUREMENT_RECTANGLE_CERTIFICATE.json"
MARGIN = Fraction(1, 10**10)


def fraction(record: dict) -> Fraction:
    return Fraction(int(record["numerator"]), int(record["denominator"]))


def bound(mean_alt: Fraction, m: Fraction, lam: Fraction) -> dict:
    radius = max(Fraction(1), 1 / m - 1)
    excess = mean_alt / m - 1
    if lam * radius > Fraction(1, 2):
        raise RuntimeError("log lower-bound condition |lambda z|<=1/2 failed")
    lower = lam * excess - lam * lam * radius * radius
    if lower <= 0:
        raise RuntimeError("uniform log-growth lower bound is not positive")
    return {
        "lambda": float(lam),
        "null_mean_bound_with_margin": float(m),
        "alternative_mean_lower_bound": float(mean_alt),
        "normalized_mean_excess": float(excess),
        "absolute_normalized_increment_radius": float(radius),
        "lambda_times_radius": float(lam * radius),
        "inequality": "log(1+y) >= y-y^2 for |y|<=1/2",
        "uniform_expected_log_increment_lower_bound_nats_per_shot": float(lower),
        "exact_lower_bound_fraction": {"numerator": str(lower.numerator), "denominator": str(lower.denominator)},
    }


def main() -> None:
    cert = json.loads(CERT.read_text(encoding="utf-8"))
    bounds = cert["certified_continuous_bounds"]
    low_null_x = fraction(bounds["null_mean_maximum"]["exact_fraction"])
    high_min_x = fraction(bounds["alternative_mean_minimum"]["exact_fraction"])
    low_alt_gap = high_min_x - low_null_x

    up_m = low_null_x + MARGIN
    up = bound(high_min_x, up_m, Fraction(1, 100000))

    down_null_y = 1 - high_min_x
    down_alt_y = 1 - low_null_x
    down_m = down_null_y + MARGIN
    down = bound(down_alt_y, down_m, Fraction(3, 1000))

    result = {
        "classification": "BIDIRECTIONAL_EXACT_CIRCUIT_POPULATION_EFACTOR_BOUNDS_NOT_IMPLEMENTED_DETECTOR",
        "source_mean_certificate": CERT.name,
        "configuration": cert["configuration"],
        "common_mean_separation_gap_x": float(low_alt_gap),
        "upward_burst_detection": {
            "statistic": "X = mean of five pair-cofire indicators",
            "null": "p_b in [0,.002], p_m in [.001,.005], gate p=.003",
            "alternative": "p_b in [.010,.018], p_m in [.001,.005], gate p=.003",
            "null_mean_upper_bound": float(low_null_x),
            "alternative_mean_lower_bound": float(high_min_x),
            **up,
        },
        "downward_burst_detection": {
            "statistic": "Y = 1-X",
            "null": "p_b in [.010,.018], p_m in [.001,.005], gate p=.003",
            "alternative": "p_b in [0,.002], p_m in [.001,.005], gate p=.003",
            "null_mean_upper_bound": float(down_null_y),
            "alternative_mean_lower_bound": float(down_alt_y),
            **down,
        },
        "interpretation": "Separate one-sided e-factor alternatives support an analytic two-direction regime-monitor concept with an indifference band (.002,.010). Their alarms cannot be combined or reset without a prespecified alpha-spending/ARL and state-transition policy.",
        "limitations": [
            "The certificate assumes the exact categorical circuit, independent per-shot noise sites, fixed gate p=.003, and measurement p in [.001,.005].",
            "Burst probabilities between .002 and .010 are an indifference region; no uniform drift claim is made there.",
            "Positive expected log increments do not specify detection delay or false-alarm behavior.",
            "No sequential process, threshold, histories, graph switch, or decoder utility was evaluated.",
        ],
    }
    out = HERE / "BIDIRECTIONAL_MEAN_EFACTOR_CERTIFICATE.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("gap", result["common_mean_separation_gap_x"])
    print("up_log_lower", up["uniform_expected_log_increment_lower_bound_nats_per_shot"])
    print("down_log_lower", down["uniform_expected_log_increment_lower_bound_nats_per_shot"])
    print(f"wrote={out}")


if __name__ == "__main__":
    main()
