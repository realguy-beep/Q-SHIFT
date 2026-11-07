"""Compare two elimination heuristics on the validated toy factor graphs."""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"outputs"/"categorical_decoder_feasibility"))
from categorical_reference import exact_posterior
from factor_graph import make_factor_graph, run_dense_ve
from toy_circuits import one_qubit_model, two_qubit_model


def main():
    rows=[]
    for name,model in (("one_qubit",one_qubit_model()),("two_qubit",two_qubit_model())):
        exact=exact_posterior(model); graph=make_factor_graph(model)
        results=[]
        for heuristic in ("min_fill","min_degree"):
            ve=run_dense_ve(model,heuristic)
            if ve["decisions"]!=exact.decisions or abs(ve["risk"]-exact.logical_error_probability)>1e-12:
                raise AssertionError(f"VE does not reproduce exact result: {name}/{heuristic}")
            results.append({"heuristic":heuristic,"induced_width":ve["induced_width"],
                            "max_combined_factor_states":ve["max_combined_factor_states"],
                            "max_intermediate_dense_cells":ve["max_intermediate_cells"],
                            "total_mass":ve["total_mass"],"MAP_risk":ve["risk"],
                            "decisions_match_exhaustive":True,"tie_syndromes":ve["tie_syndromes"]})
        rows.append({"model":name,"fault_variables":len(model.locations),
                     "outcome_domains":[len(x.outcomes) for x in model.locations],
                     "output_bits":model.detector_count+model.observable_count,
                     "factor_nodes":len(graph["factor_scopes"]),
                     "factor_incidences":sum(map(len,graph["factor_scopes"])),
                     "orders":results})
    out={"status":"PASS","methods":"Dense tensor variable elimination over categorical location variables with XOR parity factors. Output bits are retained; faults are eliminated.",
         "heuristic_definitions":{"min_fill":"eliminate fault variable minimizing missing edges among its current neighbors, tie-breaking by degree then ID",
                                  "min_degree":"eliminate fault variable minimizing current degree, tie-breaking by fill then ID"},
         "results":rows}
    (Path(__file__).resolve().parent/"TOY_VE_RESULTS.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2))

if __name__=="__main__": main()
