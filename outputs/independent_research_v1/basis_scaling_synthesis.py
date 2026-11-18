"""Descriptive synthesis of saved known-profile X-bias basis-alignment screens."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.stats import beta

HERE=Path(__file__).resolve().parent
# Counts are taken from the committed distance-specific RESULTS.json records.
# Every cell is X-biased ratio 10:1, p_gate=p_measurement=.003, rounds=2d-1.
ROWS=[
    {"distance":3,"shots":40000,"aligned_failures":51,"mismatched_failures":263,"source":"known_profile_memory_basis_alignment"},
    {"distance":5,"shots":50000,"aligned_failures":6,"mismatched_failures":217,"source":"known_profile_memory_basis_distance5"},
    {"distance":7,"shots":500000,"aligned_failures":5,"mismatched_failures":1009,"source":"known_profile_memory_basis_distance7"},
    {"distance":9,"shots":500000,"aligned_failures":1,"mismatched_failures":408,"source":"basis_alignment_d9"},
]


def exact_rate_ratio(x:int,y:int,nx:int,ny:int,alpha:float=.05):
    total=x+y
    lo=0.0 if x==0 else beta.ppf(alpha/2,x,y+1)
    hi=1.0 if y==0 else beta.ppf(1-alpha/2,x+1,y)
    return {"point":(x/nx)/(y/ny),
            "conditional_exact_95_ci":[float(lo/(1-lo)*ny/nx),float(hi/(1-hi)*ny/nx)],
            "conditional_failures":total}


def poisson_line(counts,exposure,distances):
    x=np.column_stack([np.ones(len(distances)),np.asarray(distances,dtype=float)])
    y=np.asarray(counts,dtype=float);off=np.log(np.asarray(exposure,dtype=float))
    def objective(b):
        eta=off+x@b
        return float(np.sum(np.exp(eta)-y*eta))
    fit=minimize(objective,np.array([-4.0,-.5]),method='BFGS',tol=1e-12)
    if not fit.success and not np.isfinite(fit.fun):raise RuntimeError(fit.message)
    mu=np.exp(off+x@fit.x);cov=np.linalg.inv(x.T@(mu[:,None]*x))
    slope=float(fit.x[1]);se=float(np.sqrt(cov[1,1]))
    return {"log_rate_intercept":float(fit.x[0]),"log_rate_slope_per_distance":slope,
            "slope_wald_95_ci":[slope-1.96*se,slope+1.96*se],
            "rate_multiplier_per_plus_2_distance":float(np.exp(2*slope)),
            "model":"independent Poisson counts with log(shots) offset; descriptive log-linear fit"}


def main():
    ds=[r['distance'] for r in ROWS];ns=[r['shots'] for r in ROWS]
    aligned=[r['aligned_failures'] for r in ROWS];mismatched=[r['mismatched_failures'] for r in ROWS]
    points=[]
    for r in ROWS:
        a=r['aligned_failures'];m=r['mismatched_failures'];n=r['shots']
        points.append({**r,"aligned_ler":a/n,"mismatched_ler":m/n,
                       "aligned_over_mismatched":exact_rate_ratio(a,m,n,n)})
    af=poisson_line(aligned,ns,ds);mf=poisson_line(mismatched,ns,ds)
    ratio_slope=af['log_rate_slope_per_distance']-mf['log_rate_slope_per_distance']
    out={"status":"secondary_descriptive_development_synthesis",
         "question":"Do saved matched-resource known-profile screens establish distance scaling of basis alignment?",
         "conditions":"X-biased ratio 10:1, gate and measurement probabilities .003, distance d, rounds 2d-1; compare X-memory aligned vs Z-memory mismatched.",
         "data_sources":"Four saved independent distance screens in RESULTS.json; no samples generated.",
         "distance_points":points,"aligned_poisson_log_linear_fit":af,"mismatched_poisson_log_linear_fit":mf,
         "ratio_log_slope_point_difference_per_distance":ratio_slope,
         "ratio_multiplier_per_plus_2_distance_point":float(np.exp(2*ratio_slope)),
         "endpoint_aligned_rate_reduction_d3_to_d9":float((aligned[0]/ns[0])/(aligned[-1]/ns[-1])),
         "endpoint_mismatched_rate_reduction_d3_to_d9":float((mismatched[0]/ns[0])/(mismatched[-1]/ns[-1])),
         "d9_relative_target_ratio":0.0001,
         "d9_observed_ratio_over_target":points[-1]['aligned_over_mismatched']['point']/0.0001,
         "limitations":["Only four finite distances and independent streams; not a threshold estimate.",
          "Aligned counts are sparse (51, 6, 5, 1); Poisson slope intervals are model-based and do not capture circuit-model uncertainty.",
          "Distance, qubit count, and round count change together.",
          "All results use the simulator's stipulated noise model; no hardware calibration or arbitrary logical-state result.",
          "No 99.99% relative LER reduction is demonstrated; the d9 point ratio is 24.5 times the 1e-4 target."]}
    (HERE/'basis_scaling_synthesis_results.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({"status":out['status'],"points":[[p['distance'],p['aligned_failures'],p['mismatched_failures'],p['aligned_over_mismatched']['point']] for p in points],
      "aligned_multiplier_per_2":af['rate_multiplier_per_plus_2_distance'],
      "mismatched_multiplier_per_2":mf['rate_multiplier_per_plus_2_distance'],
      "d9_ratio_over_target":out['d9_observed_ratio_over_target']},indent=2))

if __name__=='__main__':main()
