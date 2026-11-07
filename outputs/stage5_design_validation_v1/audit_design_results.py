"""Structural audit of the saved synthetic design-simulation outputs."""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
cfg = json.loads((HERE / "DESIGN_SIMULATION_CONFIG.json").read_text(encoding="utf-8"))
inv = json.loads((HERE / "VALIDATION_SEED_INVENTORY.json").read_text(encoding="utf-8"))
res = json.loads((HERE / "DESIGN_SIMULATION_RESULTS.json").read_text(encoding="utf-8"))
assert res["stage5_shots_generated"] == 0
assert res["sealed_test_accessed"] is False
rows = res["root_level_welch_results"]
assert len(rows) == len(cfg["scenarios"]) * len(cfg["primary"]["alternatives"]) == 28
assert all(r["replicates"] == cfg["welch_monte_carlo_replicates_per_scenario_effect"] for r in rows)
assert len(res["root_stratified_bootstrap_t_null_results"]) == 3
assert all(r["outer_replicates"] == cfg["bootstrap_t_outer_replicates_per_null_scenario"] and
           r["bootstrap_replicates"] == cfg["bootstrap_t_inner_replicates"]
           for r in res["root_stratified_bootstrap_t_null_results"])
assert inv["historical_seed_collision_count"] == 0
assert len(set(inv["analysis_rngs"]["welch_scenario_seeds"])) == 7
assert len(rows) == 28
for scenario_index, scenario in enumerate(cfg["scenarios"]):
    subset = [r for r in rows if r["scenario"] == scenario["name"]]
    assert len(subset) == 4
    actual_seed = cfg["rng"]["welch_seed_base"] + scenario_index * 100
    # Source initializes once per scenario and processes effects in fixed order.
    assert subset[0]["seed"] == actual_seed
    assert all(math.isclose(r["true_delta"], want, abs_tol=1e-12)
               for r, want in zip(subset, cfg["primary"]["alternatives"]))
for row in rows:
    stats = row["welch_primary"]
    low, high = stats["type_i_error_or_power_mc_95_wilson"]
    assert low <= stats["reject_rate_h0_delta_ge_minus_0_0002"] <= high
    low, high = stats["central_coverage_mc_95_wilson"]
    assert low <= stats["central_95_ci_coverage"] <= high
for row in res["root_stratified_bootstrap_t_null_results"]:
    stats = row["bootstrap_t"]
    low, high = stats["type_i_mc_95_wilson"]
    assert low <= stats["type_i_error"] <= high
    low, high = stats["central_coverage_mc_95_wilson"]
    assert low <= stats["central_95_ci_coverage"] <= high
print("PASS: 28 Welch cells and 3 bootstrap cells match frozen simulation allocation; Stage 5 shots=0")
