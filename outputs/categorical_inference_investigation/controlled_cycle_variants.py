"""Correlation perturbation preserving Pauli marginals and total gate-fault mass."""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"outputs"/"categorical_decoder_feasibility"))
from categorical_reference import decoder_risk, exact_posterior
from controlled_variants import (categorical_pair_distribution, circuit_for_distribution,
                                 matching_predictions, model_for_distribution)

ALPHAS=(-1.0,-0.5,0.0,0.5,1.0)
DELTA_MAX=0.004


def margins(dist):
    return ({p:sum(v for pair,v in dist.items() if pair[0]==p) for p in "IXYZ"},
            {p:sum(v for pair,v in dist.items() if pair[1]==p) for p in "IXYZ"})


def shifted_distribution(alpha):
    base=categorical_pair_distribution(0.0)
    delta=DELTA_MAX*alpha
    result=dict(base)
    result["XX"]+=delta; result["XY"]-=delta
    result["YX"]-=delta; result["YY"]+=delta
    if min(result.values()) < -1e-12 or not math.isclose(sum(result.values()),1.0,abs_tol=1e-12):
        raise ValueError("invalid cycle perturbation")
    return result


def main():
    base=shifted_distribution(0)
    base_margins=margins(base)
    rows=[]
    for alpha in ALPHAS:
        dist=shifted_distribution(alpha)
        if margins(dist)!=base_margins:
            # Floating addition can perturb the last bit; compare numerically.
            for actual,expected in zip(margins(dist),base_margins):
                for p in "IXYZ":
                    if not math.isclose(actual[p],expected[p],rel_tol=0,abs_tol=1e-15):
                        raise AssertionError((alpha,p,actual[p],expected[p]))
        model=model_for_distribution(dist); exact=exact_posterior(model)
        pm,dem=matching_predictions(circuit_for_distribution(dist))
        risks={"exact_categorical_MAP":exact.logical_error_probability}
        for name,pred in pm.items(): risks[f"pymatching_{name}"]=decoder_risk(exact.joint,pred)
        rows.append({"alpha":alpha,"delta":DELTA_MAX*alpha,"P_II":dist["II"],
                     "total_nonidentity_probability":1-dist["II"],
                     "marginals":margins(dist),"decisions_exact":exact.decisions,
                     "decisions_pymatching":pm,"risks_under_variant_channel":risks,
                     "standard_decision_disagreements":sum(pm["standard"][s]!=exact.decisions[s] for s in range(4)),
                     "correlation_decision_disagreements":sum(pm["correlation_enabled"][s]!=exact.decisions[s] for s in range(4)),
                     "dem":dem})
    out={"variant":"four-cell 2x2 contingency-table cycle on XX,XY,YX,YY",
         "definition":"P(XX)+=delta, P(XY)-=delta, P(YX)-=delta, P(YY)+=delta, delta=0.004*alpha. This preserves both single-qubit Pauli marginals, P(II), total nonidentity mass, categorical one-draw semantics, and all other event probabilities.",
         "alphas":list(ALPHAS),"results":rows,
         "interpretation_limit":"This is one prespecified local correlation direction in the toy distribution, not a physical fit or general mechanism claim."}
    path=Path(__file__).resolve().parent/"CONTROLLED_VARIANTS_FIXED_MARGINALS.json"
    path.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps([{ "alpha":r["alpha"],"exact":r["risks_under_variant_channel"]["exact_categorical_MAP"],
                       "standard":r["risks_under_variant_channel"]["pymatching_standard"],
                       "correlation":r["risks_under_variant_channel"]["pymatching_correlation_enabled"],
                       "std_disagreements":r["standard_decision_disagreements"],
                       "corr_disagreements":r["correlation_decision_disagreements"]} for r in rows],indent=2))


if __name__=="__main__": main()
