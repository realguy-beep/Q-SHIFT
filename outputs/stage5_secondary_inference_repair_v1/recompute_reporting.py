"""Correct Wilson multiplicity metadata without altering simulated rejection/coverage counts."""
from __future__ import annotations
import hashlib, json, math, os
from pathlib import Path
from scipy.stats import norm

HERE = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def wilson(k: int, n: int, cells: int = 1, *, one_sided: bool = True) -> list[float]:
    if n <= 0 or not 0 <= k <= n:
        raise ValueError("invalid count")
    z = float(norm.ppf(1.0 - 0.05 / cells if one_sided else 1.0 - 0.05 / (2.0 * cells)))
    p = k / n
    d = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / d
    rad = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / d
    return [max(0.0, center - rad), min(1.0, center + rad)]


def recalc(row: dict, cells: int) -> dict:
    row["pointwise_wilson95"] = wilson(row["successes"], row["trials"], 1, one_sided=False)
    row["simultaneous_one_sided_wilson95"] = wilson(row["successes"], row["trials"], cells, one_sided=True)
    return row


def main() -> None:
    source = HERE / "SIMULATION_RESULTS.json"
    target = HERE / "SIMULATION_RESULTS_REANALYZED_V2.json"
    if target.exists():
        raise RuntimeError("refusing to overwrite reanalysis output")
    d = json.loads(source.read_text(encoding="utf-8"))
    marginal_cells = 12 * 4 * 4
    fwer_cells = 12 * (1 + 14 * 3)
    coverage_cells = 12
    marginal_coverage_cells = 12 * 4
    power_cells = 12 * 2 * 6
    if (len(d["marginal_pvalue_checks"]) != marginal_cells or
        len(d["complete_and_partial_null_fwer"]) != fwer_cells or
        len(d["coverage"]) != coverage_cells or len(d["secondary_power"]) != 24):
        raise AssertionError("saved result cell coverage does not match the frozen 12-family-by-scale design")
    for row in d["marginal_pvalue_checks"]:
        row["simultaneous_one_sided_wilson95"] = wilson(row["count"], d["replicates_per_family_scale_cell"], marginal_cells)
        row["pass"] = row["simultaneous_one_sided_wilson95"][1] <= row["alpha"] + 0.002
    for row in d["complete_and_partial_null_fwer"]:
        recalc(row, fwer_cells)
        row["pass"] = row["simultaneous_one_sided_wilson95"][1] <= 0.052
    for row in d["coverage"]:
        for m in row["marginal_95_upper_coverage"]:
            recalc(m, marginal_coverage_cells)
        recalc(row["four_condition_simultaneous_95_upper_coverage"], coverage_cells)
        row["pass"] = row["four_condition_simultaneous_95_upper_coverage"]["simultaneous_one_sided_wilson95"][0] >= 0.94
    for row in d["secondary_power"]:
        all_rates = list(row["condition_holm_rejection"]) + [row["any_condition_rejected"], row["all_four_rejected"]]
        for stat in all_rates:
            recalc(stat, power_cells)
    d["reporting_repair"] = {
        "source_result_sha256": sha(source),
        "reason": "The frozen configuration expanded the validation to twelve family-by-scale cells, but the first report serializer retained coverage cell counts from a ten-cell draft and power count from a twenty-cell draft.",
        "scope": "Recomputed confidence bounds and gate flags only; all simulated successes/trials, p-values, reference CDFs, seeds and test statistics are unchanged.",
        "correct_cell_counts": {"marginal_pvalue": marginal_cells, "fwer": fwer_cells,
                                "simultaneous_coverage": coverage_cells, "marginal_coverage": marginal_coverage_cells,
                                "power_rates": power_cells}
    }
    d["gate_summary"]["all_marginal_size_cells_pass"] = all(r["pass"] for r in d["marginal_pvalue_checks"])
    d["gate_summary"]["all_complete_and_partial_fwer_cells_pass"] = all(r["pass"] for r in d["complete_and_partial_null_fwer"])
    d["gate_summary"]["all_simultaneous_coverage_cells_pass"] = all(r["pass"] for r in d["coverage"])
    d["gate_summary"]["overall_secondary_method_pass"] = (d["gate_summary"]["all_marginal_size_cells_pass"] and
        d["gate_summary"]["all_complete_and_partial_fwer_cells_pass"] and d["gate_summary"]["all_simultaneous_coverage_cells_pass"])
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, target)
    print(json.dumps({"status": "REPORTING_REANALYSIS_COMPLETE", "counts_unchanged": True,
                      "gate_summary": d["gate_summary"], "sha256": sha(target)}, indent=2))


if __name__ == "__main__":
    main()
