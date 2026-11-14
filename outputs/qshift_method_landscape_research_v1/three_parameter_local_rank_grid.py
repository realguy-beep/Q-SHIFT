"""Exact-circuit local mean-feature rank/conditioning across parameter grid."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
for d in (ROOT,ROOT/"outputs"/"phase3a_correlated_noise_preflight",ROOT/"outputs"/"stage4_noise_adaptive_feasibility_v1"):
    if str(d) not in sys.path: sys.path.insert(0,str(d))

import categorical_circuit_feature_expectations as features
from categorical_circuit_parameter_grid_audit import exact_cov
from three_parameter_detector_identifiability import build,mean_at,NOMINAL,SCALES

PB=np.linspace(.002,.018,5); PM=np.linspace(.001,.005,5); PG=np.linspace(.002,.004,3)
STEPS=(1e-4,5e-5)


def main():
    start=time.perf_counter()
    c0=build(NOMINAL); mapped,_=features.categorical_sites(c0); names=[inst.name for inst in c0]
    mean0=features.means_from_characters(mapped); cov0=exact_cov(mapped,mean0)
    eig,vec=np.linalg.eigh(cov0)
    if eig[0]<=0: raise RuntimeError("nominal feature covariance not positive definite")
    invsqrt=(vec/np.sqrt(eig))@vec.T
    rows=[]
    for pb in PB:
        for pm in PM:
            for pg in PG:
                point=np.array([pb,pm,pg],dtype=float)
                column_rows=[]; step_rows=[]
                for k,param in enumerate(("burst_p","measurement_p","gate_p")):
                    derivs=[]
                    for h in STEPS:
                        plus,minus=point.copy(),point.copy(); plus[k]+=h; minus[k]-=h
                        derivs.append((mean_at(plus,mapped,names)-mean_at(minus,mapped,names))/(2*h))
                    column_rows.append(derivs[0])
                    step_rows.append(float(np.linalg.norm(derivs[0]-derivs[1])/np.linalg.norm(derivs[1])))
                jac=np.column_stack(column_rows)
                singular=np.linalg.svd(invsqrt@(jac*SCALES[None,:]),compute_uv=False)
                rank=int(np.sum(singular>singular[0]*1e-8))
                rows.append({"burst_p":float(pb),"measurement_p":float(pm),"gate_p":float(pg),"singular_values_nominal_covariance_whitened_scaled":singular.tolist(),"relative_step_change_by_parameter":step_rows,"numerical_rank_relative_1e-8":rank,"condition_ratio":float(singular[0]/singular[-1])})
    worst=max(rows,key=lambda r:r["condition_ratio"]); best=min(rows,key=lambda r:r["condition_ratio"])
    result={
        "classification":"EXACT_CATEGORICAL_CIRCUIT_LOCAL_JACOBIAN_GRID_SCREEN",
        "nominal_covariance_reference":NOMINAL.tolist(),"parameter_scales":SCALES.tolist(),
        "grid":{"shape":[len(PB),len(PM),len(PG)],"burst_p":PB.tolist(),"measurement_p":PM.tolist(),"gate_p":PG.tolist(),"profiles":len(rows)},
        "derivative_steps":STEPS,"whitening":"fixed exact single-shot covariance at nominal (.010,.003,.003), reused over the grid for comparability",
        "rank_counts":{str(r):sum(x["numerical_rank_relative_1e-8"]==r for x in rows) for r in sorted(set(x["numerical_rank_relative_1e-8"] for x in rows))},
        "condition_ratio_min_max":[best["condition_ratio"],worst["condition_ratio"]],
        "best_condition_profile":best,"worst_condition_profile":worst,
        "max_relative_step_change_over_grid":max(max(x["relative_step_change_by_parameter"]) for x in rows),
        "profiles":rows,
        "limitations":["Finite-difference, finite-grid local mean-feature analysis only.","Whitening covariance is frozen at the nominal point; this is a comparability scale, not local Fisher information at each profile.","Full rank at grid nodes does not establish global injectivity or finite-history recovery.","Exact categorical circuit only; approximate DEM rank grid is not included here.","No histories, sampling, decoder inference, or protected data were used."],
    }
    out=HERE/"THREE_PARAMETER_LOCAL_RANK_GRID.json"; out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"output":str(out),"profiles":len(rows),"rank_counts":result["rank_counts"],"condition_min_max":result["condition_ratio_min_max"],"worst":worst,"max_step_change":result["max_relative_step_change_over_grid"],"seconds":time.perf_counter()-start},indent=2))


if __name__=="__main__": main()
