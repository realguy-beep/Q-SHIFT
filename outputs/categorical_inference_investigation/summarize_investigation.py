"""Recompute and cross-check headline findings from saved deterministic evidence."""
from __future__ import annotations
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def read(name): return json.loads((HERE/name).read_text(encoding="utf-8"))


def main():
    baseline=read("BASELINE_REPRODUCTION.json")
    dem=read("INDEPENDENT_DEM_RESULTS.json")
    sep=read("SEPARATOR_ABLATION.json")
    variants=read("CONTROLLED_VARIANTS_FIXED_MARGINALS.json")
    ve=read("TOY_VE_RESULTS.json")
    heuristic=read("CIRCUIT_HEURISTICS.json")
    fragments=[read(f"FRAGMENT_R{r}.json")["report"] for r in range(1,6)]
    assert baseline["status"]=="PASS" and baseline["stochastic_phase2b_shots_generated"]==0
    assert dem["mechanism_count"]==6 and dem["enumerated_independent_mechanism_configurations"]==64
    assert dem["syndrome_11_attribution"]["independent_DEM_exact_MAP"]==1
    assert dem["syndrome_11_attribution"]["PyMatching_standard"]==0
    assert sep["exact_independent_dem_posterior_unchanged"]
    assert sep["syndrome_11_result"]=={"DEM_MAP":1,"with_sep_standard":0,"with_sep_correlated":0,"without_sep_standard":1,"without_sep_correlated":1}
    assert len(variants["results"])==5
    for row in variants["results"]:
        assert row["decisions_exact"]=={"0":0,"1":0,"2":0,"3":1}
        assert row["decisions_pymatching"]["standard"]["3"]==0
        assert row["decisions_pymatching"]["correlation_enabled"]["3"]==0
    assert all(order["decisions_match_exhaustive"] for result in ve["results"] for order in result["orders"])
    for r,report in enumerate(fragments,1):
        assert report["stochastic_shots_generated"]==0
        assert report["complete_fault_configurations_enumerated"]==0
        assert report["rounds"]==r
        assert report["circuit_detectors"]==8*r
        assert report["circuit_observables"]==1
        if r<=3: assert report["inference"]["status"]=="COMPLETED"
        else: assert report["inference"]["status"]=="SKIPPED_RESOURCE_PREFLIGHT"
    outcome={
        "status":"PASS",
        "historical_manifest_checks":baseline["preserved_manifest_hashes_verified"],
        "software":baseline["software"],
        "baseline_risks":{
            name:baseline["results"][name]["logical_error_probability_under_exact_channel"]
            for name in ("one_qubit","two_qubit")},
        "independent_dem":{
            "mechanisms":dem["mechanism_count"],"enumerated_configurations":dem["enumerated_independent_mechanism_configurations"],
            "posterior_mass":dem["posterior_total_mass"],"joint_distribution_TV":dem["joint_distribution_total_variation_distance"],
            "risk_on_categorical_channel":dem["logical_error_risk_under_original_categorical_channel"],
            "risk_on_DEM_channel":dem["logical_error_risk_under_independent_DEM_distribution"]},
        "separator_ablation":sep["syndrome_11_result"],
        "fixed_marginal_variant_risks":[row["risks_under_variant_channel"] for row in variants["results"]],
        "toy_variable_elimination":ve["results"],
        "circuit_symbolic_heuristics":[{"rounds":r["rounds"],"min_fill_width":r["symbolic_direct_parity_heuristics"][0]["induced_width"],
                                        "min_degree_width":r["symbolic_direct_parity_heuristics"][1]["induced_width"]} for r in heuristic["results"]],
        "fragments":[{
            "rounds":r["rounds"],"detectors":r["circuit_detectors"],"observables":r["circuit_observables"],
            "fault_locations":r["fault_graph"]["fault_variables"],"configuration_log2":r["fault_graph"]["configuration_log2"],
            "frontier_width_bits":r["structured_elimination"]["frontier_width_bits"],
            "frontier_states":r["structured_elimination"]["max_intermediate_factor_states"],
            "posterior_bytes":r["structured_elimination"]["dense_float64_output_bytes"],
            "inference_status":r["inference"]["status"],"inference_seconds":r["inference"].get("runtime_seconds"),
            "logical_error_probability":r["inference"].get("logical_error_probability"),
            "peak_working_set_bytes":r["memory"]["peak_working_set_bytes"],
            "wall_seconds":r["total_runtime_seconds"],
            "forced_single_fault_checks":r["extraction"]["forced_nonidentity_checks"]} for r in fragments],
        "fragment_runner_wall_seconds_sum":sum(r["total_runtime_seconds"] for r in fragments),
        "forced_single_fault_checks_sum":sum(r["extraction"]["forced_nonidentity_checks"] for r in fragments),
        "stochastic_phase2b_evaluation_shots":0,
        "decision":"PARTIAL",
        "decision_reason":"Exact categorical inference was independently validated and a reduced-round distance-3 fragment completed through 3 rounds; the 4- and 5-round dense joint posterior exceeds the 2 GiB budget. A circuit-local exact tree-decomposition path to the full 5-round circuit has not been established."
    }
    (HERE/"INVESTIGATION_RESULTS.json").write_text(json.dumps(outcome,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","decision":"PARTIAL",
                      "syndrome11":outcome["separator_ablation"]["without_sep_standard"],
                      "r3_seconds":fragments[2]["inference"]["runtime_seconds"],
                      "r3_peak":fragments[2]["memory"]["peak_working_set_bytes"],
                      "total_fragment_wall_seconds":outcome["fragment_runner_wall_seconds_sum"]},indent=2))

if __name__=="__main__":main()
