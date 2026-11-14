"""Deterministic Azuma delay bounds from existing exact-circuit e-factor certificates.
No histories, sampling, or decoder calls are performed.
"""
from __future__ import annotations
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "EXACT_THREE_PARAMETER_EFACTOR_ENVELOPE.json"
OUTPUT = ROOT / "EFACTOR_DELAY_CONCENTRATION_AUDIT.json"

# Decimal values are truncated downward from the exact rational/log-interval
# certificates in SOURCE, preserving a conservative expected-log lower bound.
ARMS = [
    {
        "name": "upward",
        "lambda": 0.006917395863312148,
        "mu_log_lower": 0.00493253787949116,
        "log_factor_min": -0.006941431954984323,
        "log_factor_max": 1.1920774589512741,
        "null": "burst p in [0,.002], measurement p in [.001,.005], gate p in [.002,.004]",
        "alternative": "burst p in [.010,.018], measurement p in [.001,.005], gate p in [.002,.004]",
    },
    {
        "name": "downward_on_complement",
        "lambda": 0.6964100870913746,
        "mu_log_lower": 0.00333661448705626,
        "log_factor_min": -1.1920774589512741,
        "log_factor_max": 0.006941431954984323,
        "null": "burst p in [.010,.018], measurement p in [.001,.005], gate p in [.002,.004]",
        "alternative": "burst p in [0,.002], measurement p in [.001,.005], gate p in [.002,.004]",
    },
]

# Slightly inflate the interval width to cover printed decimal rounding.
ROUNDING_SLACK = 1e-12
ALPHAS = (0.05, 0.01)
DELTAS = (0.10, 0.05)


def azuma_miss_bound(n: int, mu: float, log_threshold: float, width: float) -> float:
    """P(T>n) <= P(S_n < log threshold), bounded by Azuma-Hoeffding."""
    excess = n * mu - log_threshold
    if excess <= 0:
        return 1.0
    return math.exp(-2.0 * excess * excess / (n * width * width))


def first_sufficient_n(mu: float, log_threshold: float, width: float, delta: float) -> int:
    # Closed-form root in y=sqrt(n), followed by integer verification.
    c = width * math.sqrt(0.5 * math.log(1.0 / delta))
    y = (c + math.sqrt(c * c + 4.0 * mu * log_threshold)) / (2.0 * mu)
    n = max(1, math.ceil(y * y))
    while azuma_miss_bound(n, mu, log_threshold, width) > delta:
        n += 1
    while n > 1 and azuma_miss_bound(n - 1, mu, log_threshold, width) <= delta:
        n -= 1
    return n


def main() -> None:
    cert = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    assert cert["classification"] == "EXACT_CATEGORICAL_CIRCUIT_CONTINUOUS_THREE_PARAMETER_BERNSTEIN_ENVELOPES"
    assert cert["tensor_bernstein"]["separation_certified_by_global_coefficient_ranges"]
    analyses = []
    for arm in ARMS:
        growth = cert["robust_mean_e_factor_population_analysis"]["endpoint_chord_optimum"][arm["name"]]
        assert abs(growth["lambda"] - arm["lambda"]) < 1e-15
        assert growth["uniform_expected_log_lower_bound_nats_per_shot"] >= arm["mu_log_lower"]
        width = arm["log_factor_max"] - arm["log_factor_min"] + ROUNDING_SLACK
        rows = []
        for alpha in ALPHAS:
            threshold = math.log(1.0 / alpha)
            for delta in DELTAS:
                n = first_sufficient_n(arm["mu_log_lower"], threshold, width, delta)
                miss = azuma_miss_bound(n, arm["mu_log_lower"], threshold, width)
                prev = azuma_miss_bound(n - 1, arm["mu_log_lower"], threshold, width) if n > 1 else 1.0
                assert miss <= delta and prev > delta
                rows.append({
                    "one_sided_false_alarm_alpha": alpha,
                    "miss_probability_by_n_at_most_delta": delta,
                    "sufficient_n_shots": n,
                    "azuma_upper_bound_at_n": miss,
                    "previous_n_bound": prev,
                    "mean_drift_only_non_guarantee_n": math.ceil(threshold / arm["mu_log_lower"]),
                })
        analyses.append({**arm, "log_increment_range_width_with_rounding_slack": width, "rows": rows})
    result = {
        "classification": "ANALYTIC_DISTRIBUTION_FREE_SUFFICIENT_DELAY_BOUNDS_NOT_SIMULATED",
        "input_source": SOURCE.name,
        "assumptions": [
            "One fixed one-sided e-process with the certified exact-circuit null envelope and no repeated reset/state switching.",
            "Under the sustained alternative, conditional expected log increment given the full prior detector history is at least the certified mu on every shot.",
            "Each log increment lies in the stated deterministic interval; conditional laws may vary within the declared alternative rectangle.",
            "Azuma-Hoeffding applies to centered log increments; no independence beyond these conditional mean and bounded-increment assumptions is required.",
            "A crossing by n is implied by log e-process at n reaching log(1/alpha); the bound is therefore sufficient and conservative.",
        ],
        "method": "For A=log(1/alpha), width R, drift lower bound mu, use P(T>n) <= exp(-2*(n*mu-A)^2/(n*R^2)) when n*mu>A; solve for the first integer n with this bound <= delta.",
        "rounding_slack_added_to_log_range_width": ROUNDING_SLACK,
        "arms": analyses,
        "limitations": [
            "These are conservative analytic upper bounds on a fixed one-sided alarm crossing quantile, not estimated or expected delays.",
            "They do not cover bidirectional switching, resets, alpha spending across directions, the indifference band, gate distributions outside the certified rectangle, or decoder utility.",
            "They use ideal exact categorical detector-law certificates; they do not transfer the e-factor guarantee to an approximate DEM as a source law.",
            "No detector stream, synthetic history, alarm path, sampling, or decode was generated.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({a["name"]: a["rows"] for a in analyses}, indent=2))
    print(f"WROTE {OUTPUT.name}")


if __name__ == "__main__":
    main()
