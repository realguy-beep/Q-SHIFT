"""Finite-grid transfer screen of exact-circuit robust mean envelopes to DEMs."""
from __future__ import annotations

import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
import stim

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
for d in (ROOT,ROOT/"outputs"/"phase3a_correlated_noise_preflight",ROOT/"outputs"/"stage4_noise_adaptive_feasibility_v1"):
    if str(d) not in sys.path: sys.path.insert(0,str(d))

from three_parameter_dem_identifiability import build_mechanisms, all_one_moment, FEATURES

GATES=(.002,.0025,.003,.0035,.004)
MEASUREMENTS=(.001,.002,.003,.004,.005)
LOW_BURSTS=(0.0,.0005,.001,.0015,.002)
HIGH_BURSTS=(.010,.012,.014,.016,.018)


def x_mean(pb,pm,pg):
    mechanisms=build_mechanisms(np.array([pb,pm,pg]))
    return float(sum(all_one_moment(mechanisms,f) for f in FEATURES[40:45])/5),len(mechanisms)


def main():
    start=time.perf_counter()
    exact=json.loads((HERE/"EXACT_THREE_PARAMETER_EFACTOR_ENVELOPE.json").read_text(encoding="utf-8"))
    null_upper=exact["tensor_bernstein"]["null_box"]["mean_upper_bound"]
    high_lower=exact["tensor_bernstein"]["high_box"]["mean_lower_bound"]
    rows=[]
    for regime,bursts in (("low_null",LOW_BURSTS),("high_alternative",HIGH_BURSTS)):
        for pb,pm,pg in itertools.product(bursts,MEASUREMENTS,GATES):
            mean,count=x_mean(pb,pm,pg)
            rows.append({"regime":regime,"burst_p":pb,"measurement_p":pm,"gate_p":pg,"mean_X":mean,"dem_mechanisms":count})
    low=[r for r in rows if r["regime"]=="low_null"]
    high=[r for r in rows if r["regime"]=="high_alternative"]
    violations={
        "low_null_above_exact_upper": [r for r in low if r["mean_X"]>null_upper+5e-12],
        "high_alternative_below_exact_lower": [r for r in high if r["mean_X"]<high_lower-5e-12],
    }
    result={
        "classification":"FINITE_GRID_APPROXIMATE_DEM_TRANSFER_SCREEN_ONLY",
        "dem_conversion":{"decompose_errors":True,"approximate_disjoint_errors":True,"stim_version":stim.__version__},
        "grid":{"gate_p":GATES,"measurement_p":MEASUREMENTS,"low_burst_p":LOW_BURSTS,"high_burst_p":HIGH_BURSTS,"models":len(rows)},
        "exact_circuit_continuous_envelopes_used_for_screen":{"low_null_X_upper":null_upper,"high_alternative_X_lower":high_lower},
        "dem_grid_extrema":{"low_null_X_max":max(r["mean_X"] for r in low),"high_alternative_X_min":min(r["mean_X"] for r in high),"observed_gap":min(r["mean_X"] for r in high)-max(r["mean_X"] for r in low),"mechanism_count_min_max":[min(r["dem_mechanisms"] for r in rows),max(r["dem_mechanisms"] for r in rows)]},
        "finite_grid_violations":violations,
        "records":rows,
        "elapsed_wall_seconds":time.perf_counter()-start,
        "limitations":["This is a finite grid only and gives no continuous DEM envelope or sequential process-validity theorem.","The DEM is generated with Stim decomposition and approximate disjoint-error conversion; it is not the exact categorical circuit.","No detector histories, sampling, decoder calls, or protected data were used."]
    }
    out=HERE/"DEM_THREE_PARAMETER_ENVELOPE_TRANSFER.json"
    out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"output":str(out),"grid_models":len(rows),"low_max":result["dem_grid_extrema"]["low_null_X_max"],"high_min":result["dem_grid_extrema"]["high_alternative_X_min"],"gap":result["dem_grid_extrema"]["observed_gap"],"violations":{k:len(v) for k,v in violations.items()},"seconds":result["elapsed_wall_seconds"]},indent=2))


if __name__=="__main__": main()
