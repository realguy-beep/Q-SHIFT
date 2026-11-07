"""A marginals-preserving categorical correlation sweep for supporting analysis."""
from __future__ import annotations

from itertools import product
import json
import math
from pathlib import Path
import sys

import numpy as np
import pymatching
import stim

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "outputs" / "categorical_decoder_feasibility"))
from categorical_reference import CategoricalLocation, CategoricalModel, FaultOutcome, decoder_risk, exact_posterior  # noqa: E402
from toy_circuits import PAULI_PAIRS, TWO_Q_NONIDENTITY_TOTAL, repetition_masks, two_qubit_probabilities  # noqa: E402

GRID = (0.0, 0.25, 0.5, 0.75, 1.0)


def categorical_pair_distribution(alpha: float) -> dict[str, float]:
    """Interpolate joint categorical channel toward product of its Pauli marginals."""
    original = {"II": 1.0 - TWO_Q_NONIDENTITY_TOTAL, **two_qubit_probabilities()}
    marginal_a = {p: sum(prob for pair, prob in original.items() if pair[0] == p) for p in "IXYZ"}
    marginal_b = {p: sum(prob for pair, prob in original.items() if pair[1] == p) for p in "IXYZ"}
    product_dist = {a+b: marginal_a[a] * marginal_b[b] for a in "IXYZ" for b in "IXYZ"}
    return {pair: (1-alpha)*original[pair] + alpha*product_dist[pair]
            for pair in ("II",) + PAULI_PAIRS}


def model_for_distribution(distribution):
    locations = []
    for index, (q0, q1) in enumerate(((0,1),(1,2))):
        outcomes = [FaultOutcome("II", distribution["II"], 0, 0)]
        for pair in PAULI_PAIRS:
            paulis=["I","I","I"]; paulis[q0],paulis[q1]=pair
            dmask,lmask=repetition_masks(tuple(paulis))
            outcomes.append(FaultOutcome(pair, distribution[pair], dmask, lmask))
        locations.append(CategoricalLocation(f"pair{index}",tuple(outcomes),"II"))
    return CategoricalModel(2,1,tuple(locations))


def circuit_for_distribution(distribution):
    c=stim.Circuit(); c.append("R",[0,1,2])
    args=[distribution[pair] for pair in PAULI_PAIRS]
    c.append("PAULI_CHANNEL_2",[0,1,1,2],args)
    c.append("MZZ",[0,1]); c.append("DETECTOR",[stim.target_rec(-1)])
    c.append("MZZ",[1,2]); c.append("DETECTOR",[stim.target_rec(-1)])
    c.append("M",[0,1,2]); c.append("OBSERVABLE_INCLUDE",[stim.target_rec(-1),stim.target_rec(-2),stim.target_rec(-3)],0)
    return c


def matching_predictions(circuit):
    dem=circuit.detector_error_model(decompose_errors=True,approximate_disjoint_errors=True)
    result={}
    for corr,name in ((False,"standard"),(True,"correlation_enabled")):
        m=pymatching.Matching.from_detector_error_model(dem,enable_correlations=corr)
        result[name]={}
        for s in range(4):
            bits=np.array([(s>>0)&1,(s>>1)&1],dtype=np.uint8)
            result[name][s]=int(np.asarray(m.decode(bits,enable_correlations=corr)).reshape(-1)[0])
    return result,str(dem)


def main():
    rows=[]
    for alpha in GRID:
        dist=categorical_pair_distribution(alpha)
        if not math.isclose(sum(dist.values()),1.0,abs_tol=1e-12): raise AssertionError("channel not normalized")
        model=model_for_distribution(dist); exact=exact_posterior(model)
        pm,dem_text=matching_predictions(circuit_for_distribution(dist))
        risks={"exact_categorical_MAP": exact.logical_error_probability}
        for name,pred in pm.items(): risks[f"pymatching_{name}"]=decoder_risk(exact.joint,pred)
        rows.append({"product_mix_alpha":alpha,"channel_distribution":dist,
                     "per_qubit_marginals":{
                        q:{p:sum(v for pair,v in dist.items() if pair[qidx]==p) for p in "IXYZ"}
                        for qidx,q in enumerate(("first","second"))},
                     "exact_MAP_decisions":exact.decisions,"PyMatching_decisions":pm,
                     "risks_under_this_categorical_channel":risks,
                     "standard_disagreements_vs_exact":sum(pm["standard"][s]!=exact.decisions[s] for s in range(4)),
                     "correlation_disagreements_vs_exact":sum(pm["correlation_enabled"][s]!=exact.decisions[s] for s in range(4)),
                     "DEM":dem_text})
    out={"purpose":"Supporting controlled distribution sweep; original toy definitions remain unchanged.",
         "variant_definition":"For each two-qubit location, linearly interpolate the original joint categorical Pauli-pair distribution with the product of its single-qubit Pauli marginals. Every draw remains one mutually exclusive 16-outcome categorical event including II. The sweep is descriptive, not a performance benchmark.",
         "alpha_grid":list(GRID),"results":rows}
    path=Path(__file__).resolve().parent/"CONTROLLED_VARIANTS.json"
    path.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps([{"alpha":r["product_mix_alpha"],"exact":r["risks_under_this_categorical_channel"]["exact_categorical_MAP"],
                       "std":r["risks_under_this_categorical_channel"]["pymatching_standard"],
                       "corr":r["risks_under_this_categorical_channel"]["pymatching_correlation_enabled"],
                       "disagree_std":r["standard_disagreements_vs_exact"],"disagree_corr":r["correlation_disagreements_vs_exact"]} for r in rows],indent=2))


if __name__=="__main__": main()
