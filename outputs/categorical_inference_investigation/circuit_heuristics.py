"""Symbolic direct-factor-graph width estimates for extracted reduced circuits."""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"outputs"/"categorical_decoder_feasibility"))
from categorical_reference import FaultOutcome,CategoricalLocation,CategoricalModel
from factor_graph import make_factor_graph,elimination_order


def load_model(rounds):
    evidence=json.loads((Path(__file__).resolve().parent/f"FRAGMENT_R{rounds}.json").read_text())
    report=evidence["report"]
    locations=[]
    for loc in evidence["categorical_locations_and_verified_masks"]:
        outcomes=tuple(FaultOutcome(o["label"],o["probability"],o["detector_mask"],o["observable_mask"]) for o in loc["outcomes"])
        locations.append(CategoricalLocation(loc["name"],outcomes,"I" if outcomes[0].label=="I" else "II"))
    return CategoricalModel(report["circuit_detectors"],report["circuit_observables"],tuple(locations))


def main():
    results=[]
    for rounds in (1,2,3):
        model=load_model(rounds); graph=make_factor_graph(model)
        results.append({"rounds":rounds,"fault_variables":len(model.locations),
                        "output_bits":model.detector_count+model.observable_count,
                        "graph_nodes":len(graph["graph"]),
                        "primal_graph_edges":sum(map(len,graph["graph"].values()))//2,
                        "factor_nodes":len(graph["factor_scopes"]),
                        "factor_incidences":sum(map(len,graph["factor_scopes"])),
                        "direct_parity_factor_scope_sizes":list(map(len,graph["parity_scopes"])),
                        "symbolic_direct_parity_heuristics":[elimination_order(graph,h) for h in ("min_fill","min_degree")],
                        "executed_solver_frontier_width_bits":model.detector_count+model.observable_count,
                        "executed_solver_frontier_states":1<<(model.detector_count+model.observable_count)})
    out={"status":"PASS_SYMBOLIC_HEURISTICS","warning":"Min-fill/min-degree outputs here are graph-width estimates only; they do not mean the corresponding dense direct parity tensors were materialized or inference completed. Executed inference used the categorical XOR/Walsh sum-product route.","results":results}
    (Path(__file__).resolve().parent/"CIRCUIT_HEURISTICS.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps([{ "rounds":r["rounds"],"edges":r["primal_graph_edges"],
                      "minfill_width":r["symbolic_direct_parity_heuristics"][0]["induced_width"],
                      "minfill_log2_states":r["symbolic_direct_parity_heuristics"][0]["max_combined_log2_states"],
                      "mindegree_width":r["symbolic_direct_parity_heuristics"][1]["induced_width"],
                      "mindegree_log2_states":r["symbolic_direct_parity_heuristics"][1]["max_combined_log2_states"]} for r in results],indent=2))

if __name__=="__main__":main()
