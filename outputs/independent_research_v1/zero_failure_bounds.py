"""Exact one-sided 95% zero-failure sample counts for a target Bernoulli rate."""
from math import ceil, log1p

RELATIVE_REDUCTION = 0.9999
CONFIDENCE = 0.95
BASELINE_RATES = (0.001, 0.005, 0.014333)


def zero_failure_trials(target_rate: float, confidence: float = CONFIDENCE) -> int:
    """Smallest N for which the exact one-sided binomial upper bound is <= p."""
    if not 0 < target_rate < 1:
        raise ValueError("target_rate must be between 0 and 1")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    return ceil(log1p(-confidence) / log1p(-target_rate))


if __name__ == "__main__":
    for baseline in BASELINE_RATES:
        candidate = baseline * (1 - RELATIVE_REDUCTION)
        n = zero_failure_trials(candidate)
        print(f"baseline={baseline:.6g} candidate_ceiling={candidate:.6g} zero_error_shots_95={n}")
