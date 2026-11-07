"""Recompute Stage 5 endpoint power sensitivity from the saved review inputs.

Read-only with respect to historical artifacts. Writes only POWER_SENSITIVITY.json
in this versioned review directory. It generates no circuit or Stage 5 samples.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import NormalDist


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "outputs/stage5_preexecution_v1/POWER_RECOMPUTATION.json"
OUTPUT = Path(__file__).with_name("POWER_SENSITIVITY.json")
Z = NormalDist()
ALPHA_ONE_SIDED = 0.05
TARGET_POWERS = (0.80, 0.90)
GAPS = (0.0001, 0.0002, 0.0003)
HETEROGENEITY = (1.0, 1.25, 1.5, 2.0)
SHOTS_PER_ROOT_ALL_STRATA = 5 * (2_000 + 2_500)


def ceil(x: float) -> int:
    return math.ceil(x - 1e-12)


def main() -> None:
    frozen_review = json.loads(INPUT.read_text(encoding="utf-8"))
    sd = [float(row["used_sd"]) for row in frozen_review["per_condition"]]
    if len(sd) != 4 or any(not math.isfinite(x) or x <= 0 for x in sd):
        raise ValueError("Expected four positive, finite nonzero-condition SD inputs")

    # Equal weights across four nonzero strata; n independent roots per stratum.
    k = math.sqrt(sum(x * x for x in sd) / 16.0)

    def power(mean_effect: float, n: int, q: float, two_sided: bool = False) -> float:
        se = q * k / math.sqrt(n)
        if two_sided:
            critical = Z.inv_cdf(1.0 - ALPHA_ONE_SIDED / 2.0)
            return (1.0 - Z.cdf(critical - abs(mean_effect) / se)
                    + Z.cdf(-critical - abs(mean_effect) / se))
        critical = Z.inv_cdf(1.0 - ALPHA_ONE_SIDED)
        return 1.0 - Z.cdf(critical - abs(mean_effect) / se)

    def n_for_gap(gap: float, target_power: float, q: float) -> int:
        z_alpha = Z.inv_cdf(1.0 - ALPHA_ONE_SIDED)
        z_power = Z.inv_cdf(target_power)
        return ceil(((z_alpha + z_power) * q * k / gap) ** 2)

    n_current = 100
    se_current = k / math.sqrt(n_current)
    a = {
        "estimand": "equal-weight mean of four nonzero-stratum root-paired (adaptive - fixed) LER differences",
        "test": "one-sided alpha=0.05 test of H0: Delta >= 0 against Delta < 0",
        "true_effect": -0.0002,
        "roots_per_nonzero_stratum": n_current,
        "estimated_se": se_current,
        "power_one_sided": power(-0.0002, n_current, 1.0),
        "power_two_sided_alpha_0_05_sensitivity": power(-0.0002, n_current, 1.0, two_sided=True),
        "probability_point_estimate_at_or_below_minus_0_0002_when_true_effect_is_exactly_minus_0_0002": 0.5,
        "interpretation": "The practical threshold is not the null. Report the estimate and interval against -0.0002 separately; at the boundary the estimate falls on either side with probability about one half."
    }

    b_power = []
    b_heterogeneity_at_current_n = []
    b_sample = []
    for gap in GAPS:
        true_delta = -0.0002 - gap
        b_power.append({
            "true_delta": true_delta,
            "gap_beyond_margin": gap,
            "roots_per_stratum": n_current,
            "power_one_sided_alpha_0_05": power(gap, n_current, 1.0),
        })
        for q in HETEROGENEITY:
            b_heterogeneity_at_current_n.append({
                "gap_beyond_margin": gap,
                "true_delta": true_delta,
                "sd_inflation_factor": q,
                "roots_per_stratum": n_current,
                "power_one_sided_alpha_0_05": power(gap, n_current, q),
            })
            for target in TARGET_POWERS:
                n = n_for_gap(gap, target, q)
                b_sample.append({
                    "gap_beyond_margin": gap,
                    "true_delta": true_delta,
                    "sd_inflation_factor": q,
                    "target_power": target,
                    "roots_per_stratum": n,
                    "total_unique_shots_at_five_strata_and_4500_shots_per_root": n * SHOTS_PER_ROOT_ALL_STRATA,
                })

    max_roots_at_2_5m = 2_500_000 // SHOTS_PER_ROOT_ALL_STRATA
    result = {
        "status": "prospective design calculations only; no Stage 5 sampling",
        "source": str(INPUT.relative_to(ROOT)),
        "source_scope": "four nonzero-stratum root-level SDs from prior development summaries; n=7 roots per source cell",
        "sd_by_probability": {str(row["p"]): row["used_sd"] for row in frozen_review["per_condition"]},
        "equal_stratum_se_constant_k": k,
        "se_formula": "SE(Delta)=sqrt(sum_j sigma_j^2 / (16*n)) = K/sqrt(n), with four equally weighted nonzero strata and n independent roots per stratum",
        "shots_per_root_total_across_five_conditions": SHOTS_PER_ROOT_ALL_STRATA,
        "current_candidate_allocation": {
            "roots_per_stratum": 100,
            "total_shots": 100 * SHOTS_PER_ROOT_ALL_STRATA,
            "hard_cap": 2_500_000,
            "maximum_roots_per_stratum_under_cap": max_roots_at_2_5m,
            "max_allocation_shots": max_roots_at_2_5m * SHOTS_PER_ROOT_ALL_STRATA,
        },
        "endpoint_A": a,
        "endpoint_B": {
            "estimand": a["estimand"],
            "test": "one-sided alpha=0.05 test of H0: Delta >= -0.0002 against Delta < -0.0002",
            "power_at_current_100_roots": b_power,
            "heterogeneity_sensitivity_at_current_100_roots": b_heterogeneity_at_current_n,
            "roots_and_shots_for_planning_gaps": b_sample,
            "interpretation": "Power is defined at alternatives a prespecified distance beyond the margin; at the null boundary, type-I error is alpha, not a meaningful power target."
        },
        "assumptions_and_limits": [
            "Independent roots within each probability stratum; paired decoder predictions are reduced to one root-level LER difference.",
            "Normal-theory planning approximation for the stratified mean; variance inputs are sample SDs from only seven roots per cell.",
            "No guarantee that future root heterogeneity, skewness, ties, or calibration-induced dependence match development data.",
            "The 2.5-million-shot cap permits at most 111 roots per each of five strata, insufficient for 80% power at a 0.0001 gap beyond the practical margin even under the nominal SD inputs."
        ]
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    print(f"K={k:.12g}; SE at 100 roots/stratum={se_current:.12g}")
    print(f"Endpoint A one-sided power at Delta=-0.0002: {a['power_one_sided']:.6f}")
    print(f"Endpoint A two-sided sensitivity: {a['power_two_sided_alpha_0_05_sensitivity']:.6f}")
    print("Endpoint B power at 100 roots: " + ", ".join(f"gap {x['gap_beyond_margin']:.4g} -> {x['power_one_sided_alpha_0_05']:.6f}" for x in b_power))
    print(f"Current cap maximum: {max_roots_at_2_5m} roots/stratum, {max_roots_at_2_5m * SHOTS_PER_ROOT_ALL_STRATA:,} shots")


if __name__ == "__main__":
    main()
