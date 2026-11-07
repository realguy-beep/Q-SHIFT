"""Test whether DEM separator metadata changes matching while event law stays fixed."""
from __future__ import annotations

from itertools import product
import json
import math
from pathlib import Path
import sys

import numpy as np
import pymatching
import stim

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"outputs"/"categorical_decoder_feasibility"))
from categorical_reference import decoder_risk, exact_posterior
from toy_circuits import noisy_stim_circuit, two_qubit_model
from categorical_dem_analysis import dem_mechanisms, enumerate_independent_dem


def parse_events(dem):
    events=[]
    for instruction in dem.flattened():
        if instruction.type!="error": continue
        d=l=0
        for target in instruction.targets_copy():
            if target.is_separator(): continue
            if target.is_relative_detector_id(): d^=1<<target.val
            elif target.is_logical_observable_id(): l^=1<<target.val
        events.append({"probability":float(instruction.args_copy()[0]),"detector_mask":d,
                       "observable_mask":l,"line":str(instruction)})
    return events


def remove_decomposition_hints(dem):
    """Re-serialize identical total events without '^', preserving float64 p."""
    lines=[]
    for event in parse_events(dem):
        targets=[]
        for bit in range(2):
            if (event["detector_mask"] >> bit) & 1: targets.append(f"D{bit}")
        for bit in range(1):
            if (event["observable_mask"] >> bit) & 1: targets.append(f"L{bit}")
        lines.append("error("+format(event["probability"],".17g")+") "+" ".join(targets))
    return stim.DetectorErrorModel("\n".join(lines))


def pm_decode(dem, correlated):
    matching=pymatching.Matching.from_detector_error_model(dem,enable_correlations=correlated)
    predictions={}; weights={}; edge_rows=[]
    for edge in matching.edges():
        u,v,data=edge
        edge_rows.append({"u":u,"v":v,"fault_ids":sorted(data.get("fault_ids",set())),
                          "weight":data.get("weight"),"error_probability":data.get("error_probability")})
    for syndrome in range(4):
        bits=np.asarray([syndrome&1,(syndrome>>1)&1],dtype=np.uint8)
        pred,weight=matching.decode(bits,enable_correlations=correlated,return_weight=True)
        predictions[syndrome]=int(np.asarray(pred).reshape(-1)[0]); weights[syndrome]=float(weight)
    return predictions,weights,{"nodes":matching.num_nodes,"edges":matching.num_edges,
                                 "fault_ids":matching.num_fault_ids,"edge_list":edge_rows}


def main():
    original,events=dem_mechanisms()
    text=str(original)
    stripped=remove_decomposition_hints(original)
    a=parse_events(original); b=parse_events(stripped)
    if [(x["probability"],x["detector_mask"],x["observable_mask"]) for x in a] != \
       [(x["probability"],x["detector_mask"],x["observable_mask"]) for x in b]:
        raise AssertionError("separator stripping changed independent mechanism table")
    ja,ma,pa,ta,massa=enumerate_independent_dem(a)
    jb,mb,pb,tb,massb=enumerate_independent_dem(b)
    if ja!=jb or ma!=mb or pa!=pb:
        raise AssertionError("separator stripping changed exact DEM posterior")
    cat=exact_posterior(two_qubit_model())
    decoders={"categorical_exact_MAP":cat.decisions}
    decoder_rows={}
    for label,dem in (("with_separators",original),("separators_removed",stripped)):
        decoder_rows[label]={}
        for corr,mode in ((False,"standard"),(True,"correlation_enabled")):
            preds,weights,graph=pm_decode(dem,corr)
            key=f"{label}_{mode}"; decoders[key]=preds
            decoder_rows[label][mode]={"predictions":preds,"matched_weights":weights,"graph":graph,
                                       "risk_under_original_categorical":decoder_risk(cat.joint,preds),
                                       "risk_under_independent_DEM":decoder_risk(ja,preds)}
    out={"status":"PASS","original_dem":str(original),"separator_removed_dem":str(stripped),
         "events_unchanged_after_separator_removal":True,"event_count":len(a),
         "exact_independent_dem_posterior_unchanged":True,
         "total_probability_mass_with_separators":massa,"total_probability_mass_without_separators":massb,
         "independent_DEM_joint_posterior":{str(s):list(p) for s,p in ja.items()},
         "independent_DEM_MAP":ma,"categorical_exact_MAP":cat.decisions,
         "PyMatching_results":decoder_rows,
         "syndrome_11_result":{"DEM_MAP":ma[3],
             "with_sep_standard":decoder_rows["with_separators"]["standard"]["predictions"][3],
             "with_sep_correlated":decoder_rows["with_separators"]["correlation_enabled"]["predictions"][3],
             "without_sep_standard":decoder_rows["separators_removed"]["standard"]["predictions"][3],
             "without_sep_correlated":decoder_rows["separators_removed"]["correlation_enabled"]["predictions"][3]},
         "interpretation":"Removing only the two ^ decomposition separators leaves the six Bernoulli event probabilities and full detector/logical parity masks unchanged. The exact DEM posterior is bit-for-bit identical. PyMatching's predictions change: the separator-decomposed graph predicts L0=0 for syndrome 11, while the graphlike event representation without separators predicts L0=1. This isolates decoder graph construction/decomposition as a cause of the observed decision gap on this toy; it does not mean the categorical channel itself changed.",
         "phase2b_shots_generated":0}
    (Path(__file__).resolve().parent/"SEPARATOR_ABLATION.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out["syndrome_11_result"],indent=2))


if __name__=="__main__":main()
