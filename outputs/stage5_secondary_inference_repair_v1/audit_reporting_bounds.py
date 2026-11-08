"""Independently recompute every Monte Carlo Wilson interval in the reanalysis."""
from __future__ import annotations
import json, math
from pathlib import Path
from statistics import NormalDist

HERE = Path(__file__).resolve().parent


def wilson(k: int, n: int, cells: int = 1, *, one_sided: bool = True) -> list[float]:
    if n <= 0 or cells <= 0 or not 0 <= k <= n:
        raise ValueError("invalid binomial count")
    tail = 0.05 / cells if one_sided else 0.05 / (2.0 * cells)
    z = NormalDist().inv_cdf(1.0 - tail)
    p = k / n
    d = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / d
    rad = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / d
    return [max(0.0, center - rad), min(1.0, center + rad)]


def same(actual, expected, *, tol=2e-14):
    return len(actual) == 2 and all(math.isclose(float(a), float(b), rel_tol=0, abs_tol=tol)
                                    for a, b in zip(actual, expected))


def audit(path: Path | None = None) -> dict:
    path = path or HERE / "SIMULATION_RESULTS_REANALYZED_V2.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    n = int(data["replicates_per_family_scale_cell"])
    expected_counts = {
        "marginal": 192,
        "fwer": 516,
        "coverage": 12,
        "marginal_coverage": 48,
        "power_scenarios": 24,
        "power_rates": 144,
    }
    if (len(data["marginal_pvalue_checks"]) != expected_counts["marginal"] or
        len(data["complete_and_partial_null_fwer"]) != expected_counts["fwer"] or
        len(data["coverage"]) != expected_counts["coverage"] or
        len(data["secondary_power"]) != expected_counts["power_scenarios"]):
        raise AssertionError("reanalysis cell counts do not match the frozen design")

    marginal_pass = []
    for row in data["marginal_pvalue_checks"]:
        interval = wilson(row["count"], n, expected_counts["marginal"])
        if not same(row["simultaneous_one_sided_wilson95"], interval):
            raise AssertionError(f"marginal Wilson mismatch: {row}")
        passed = interval[1] <= float(row["alpha"]) + 0.002
        if passed != bool(row["pass"]): raise AssertionError("marginal gate flag mismatch")
        marginal_pass.append((interval[1], row["condition_index"], row["alpha"]))

    fwer_pass = []
    for row in data["complete_and_partial_null_fwer"]:
        interval = wilson(row["successes"], row["trials"], expected_counts["fwer"])
        if not same(row["pointwise_wilson95"], wilson(row["successes"], row["trials"], 1, one_sided=False)):
            raise AssertionError("pointwise FWER Wilson mismatch")
        if not same(row["simultaneous_one_sided_wilson95"], interval):
            raise AssertionError("simultaneous FWER Wilson mismatch")
        passed = interval[1] <= 0.052
        if passed != bool(row["pass"]): raise AssertionError("FWER gate flag mismatch")
        fwer_pass.append((interval[1], row["scenario"], row["configuration"], row["true_null_mask"]))

    coverage_pass = []
    marginal_coverage_count = 0
    for row in data["coverage"]:
        for stat in row["marginal_95_upper_coverage"]:
            marginal_coverage_count += 1
            point = wilson(stat["successes"], stat["trials"], 1, one_sided=False)
            simultaneous = wilson(stat["successes"], stat["trials"], expected_counts["marginal_coverage"])
            if not same(stat["pointwise_wilson95"], point) or not same(stat["simultaneous_one_sided_wilson95"], simultaneous):
                raise AssertionError("marginal-coverage Wilson mismatch")
        stat = row["four_condition_simultaneous_95_upper_coverage"]
        point = wilson(stat["successes"], stat["trials"], 1, one_sided=False)
        simultaneous = wilson(stat["successes"], stat["trials"], expected_counts["coverage"])
        if not same(stat["pointwise_wilson95"], point) or not same(stat["simultaneous_one_sided_wilson95"], simultaneous):
            raise AssertionError("simultaneous-coverage Wilson mismatch")
        passed = simultaneous[0] >= 0.94
        if passed != bool(row["pass"]): raise AssertionError("coverage gate flag mismatch")
        coverage_pass.append((simultaneous[0], row["scenario"]))
    if marginal_coverage_count != expected_counts["marginal_coverage"]:
        raise AssertionError("marginal coverage cells mismatch")

    power_pass = []
    power_rate_count = 0
    for row in data["secondary_power"]:
        rates = list(row["condition_holm_rejection"]) + [row["any_condition_rejected"], row["all_four_rejected"]]
        for stat in rates:
            power_rate_count += 1
            point = wilson(stat["successes"], stat["trials"], 1, one_sided=False)
            simultaneous = wilson(stat["successes"], stat["trials"], expected_counts["power_rates"])
            if not same(stat["pointwise_wilson95"], point) or not same(stat["simultaneous_one_sided_wilson95"], simultaneous):
                raise AssertionError("power Wilson mismatch")
            power_pass.append((stat["rate"], simultaneous[0], row["scenario"], row["effect"]))
    if power_rate_count != expected_counts["power_rates"]:
        raise AssertionError("power-rate cell count mismatch")

    gates = data["gate_summary"]
    aggregate = {
        "all_marginal_size_cells_pass": all(x[0] <= float(row["alpha"]) + 0.002
            for x, row in zip(marginal_pass, data["marginal_pvalue_checks"])),
        "all_complete_and_partial_fwer_cells_pass": all(x[0] <= 0.052 for x in fwer_pass),
        "all_simultaneous_coverage_cells_pass": all(x[0] >= 0.94 for x in coverage_pass),
    }
    aggregate["overall_secondary_method_pass"] = all(aggregate.values())
    for key, value in aggregate.items():
        if bool(gates[key]) != bool(value): raise AssertionError(f"saved aggregate gate differs: {key}")
    return {
        "status": "PASS",
        "source": path.name,
        "replicates_per_cell": n,
        "recomputed_interval_counts": expected_counts,
        "gate_summary": aggregate,
        "worst_marginal_upper": max(marginal_pass),
        "worst_fwer_upper": max(fwer_pass),
        "lowest_simultaneous_coverage_lower": min(coverage_pass),
        "lowest_secondary_power_rate": min(power_pass),
        "power_gate": "descriptive only; no minimum was prospectively specified",
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))
