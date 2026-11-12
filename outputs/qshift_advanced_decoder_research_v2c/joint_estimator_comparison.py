"""Deterministic population comparison for Q-SHIFT Phase 2C.

No Stim sampler, RNG, decoder, labels, seed inventory, or logical outcome is used.
Exact categorical circuit masks are reused from deterministic p=1 fault analysis;
the approximate DEM is built and evaluated as a separate model.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import chi2

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit
from outputs.qshift_advanced_decoder_research_v2b import analyze_identifiability as b2

OUT = Path(__file__).resolve().parent / "comparison_results.json"
PB_NODES = np.linspace(0.0, 0.020, 21)
PM_NODES = np.linspace(0.0, 0.010, 11)
FIT_PB = np.linspace(0.0, 0.020, 201)
FIT_PM = np.linspace(0.0, 0.010, 101)
SCENARIOS = {
    "nominal": (0.008, 0.003),
    "measurement_mismatch": (0.008, 0.006),
    "low_burst_boundary": (0.0, 0.003),
    "high_burst_boundary": (0.020, 0.003),
    "low_measurement_boundary": (0.008, 0.0),
    "high_measurement_boundary": (0.008, 0.010),
    "corner_low": (0.0, 0.0),
    "corner_high": (0.020, 0.010),
}


def bilinear(table: np.ndarray, pb: float, pm: float) -> np.ndarray:
    i = min(max(int(np.searchsorted(PB_NODES, pb, side="right") - 1), 0), len(PB_NODES)-2)
    j = min(max(int(np.searchsorted(PM_NODES, pm, side="right") - 1), 0), len(PM_NODES)-2)
    u = (pb-PB_NODES[i])/(PB_NODES[i+1]-PB_NODES[i])
    v = (pm-PM_NODES[j])/(PM_NODES[j+1]-PM_NODES[j])
    return ((1-u)*(1-v)*table[i,j] + u*(1-v)*table[i+1,j]
            + (1-u)*v*table[i,j+1] + u*v*table[i+1,j+1])


def make_template_table(kind: str, physical_specs: list[dict]) -> np.ndarray:
    table = np.empty((len(PB_NODES), len(PM_NODES), len(b2.FEATURES)))
    for i, pb in enumerate(PB_NODES):
        for j, pm in enumerate(PM_NODES):
            if kind == "circuit":
                specs = b2.physical_specs_at(physical_specs, float(pb), float(pm))
            else:
                circuit = build_spatial_burst_circuit(gate_p=0.003, measurement_p=float(pm),
                                                       burst_probability=float(pb))
                specs = b2.dem_specs(circuit)
            table[i,j] = b2.feature_mean_from_characters(specs)
    return table


def profile_scales(table: np.ndarray) -> np.ndarray:
    # Existing estimator's pooled-template variance in the population limit;
    # equal weight over the five burst knots at fixed p_m=.003.
    knot_idx = [0, 5, 10, 15, 20]
    m = table[knot_idx, 3, :]
    pooled_mean = m.mean(axis=0)
    within = np.mean(m*(1-m), axis=0)
    between = np.mean((m-pooled_mean)**2, axis=0)
    return np.sqrt(np.maximum(within+between, 1e-6))


def gls_weight(table: np.ndarray, kind: str) -> tuple[np.ndarray, dict]:
    ref_pb, ref_pm = .010, .003
    if kind == "circuit":
        specs = b2.physical_specs_at(physical_specs_global, ref_pb, ref_pm)
    else:
        specs = b2.dem_specs(build_spatial_burst_circuit(gate_p=.003, measurement_p=ref_pm,
                                                         burst_probability=ref_pb))
    _, cov = b2.feature_moments(specs)
    eig, vec = np.linalg.eigh(cov)
    floor = float(eig.max()*1e-6)
    reg_eig = eig + floor
    weight = (vec / reg_eig) @ vec.T
    info = {"reference": [ref_pb, ref_pm], "covariance_eigenvalue_min": float(eig.min()),
            "covariance_eigenvalue_max": float(eig.max()),
            "covariance_condition": float(eig.max()/eig.min()),
            "ridge_floor": floor, "regularized_weight_condition": float(reg_eig.max()/reg_eig.min()),
            "covariance_rank": int(np.count_nonzero(eig > eig.max()*1e-10))}
    return weight, info


def fit_grid(data: np.ndarray, table: np.ndarray, scales: np.ndarray,
             weight: np.ndarray | None, fixed_pm: float | None = None) -> dict:
    # Coarse (0.0001) deterministic search after bilinear table interpolation.
    # Lexicographic arrays implement explicit lower-p_b, then lower-p_m tie-break.
    points = []
    means = []
    if fixed_pm is None:
        for pb in FIT_PB:
            for pm in FIT_PM:
                points.append((float(pb), float(pm)))
                means.append(bilinear(table, float(pb), float(pm)))
    else:
        for pb in FIT_PB:
            points.append((float(pb), float(fixed_pm)))
            means.append(bilinear(table, float(pb), float(fixed_pm)))
    means = np.asarray(means)
    residual = means-data
    if weight is None:
        scores = np.mean((residual/scales)**2, axis=1)
    else:
        scores = np.einsum('ni,ij,nj->n', residual, weight, residual)
    idx = int(np.argmin(scores))
    return {"estimate": list(points[idx]), "score": float(scores[idx]),
            "runner_up_gap": float(np.partition(scores, 1)[1]-scores[idx]),
            "grid_step": .0001, "grid_count": len(points)}


def scenario_comparison(truth: np.ndarray, circuit_table: np.ndarray,
                        dem_table: np.ndarray, scales_c: np.ndarray,
                        scales_d: np.ndarray, weight_c: np.ndarray,
                        weight_d: np.ndarray) -> dict:
    out = {}
    for name, (pb, pm) in SCENARIOS.items():
        data = b2.feature_mean_from_characters(b2.physical_specs_at(physical_specs_global, pb, pm))
        out[name] = {"truth": [pb, pm], "A_existing_profile_exact_templates":
                     fit_grid(data, circuit_table, scales_c, None, fixed_pm=.003),
                     "A_existing_profile_DEM_templates":
                     fit_grid(data, dem_table, scales_d, None, fixed_pm=.003),
                     "B_joint_standardized_exact_templates":
                     fit_grid(data, circuit_table, scales_c, None),
                     "B_joint_standardized_DEM_templates":
                     fit_grid(data, dem_table, scales_d, None),
                     "C_joint_GLS_exact_templates":
                     fit_grid(data, circuit_table, scales_c, weight_c),
                     "C_joint_GLS_DEM_templates":
                     fit_grid(data, dem_table, scales_d, weight_d)}
    return out


def finite_sample(theory_specs: list[dict], table: np.ndarray, scales: np.ndarray,
                  weight: np.ndarray) -> dict:
    pb, pm = .008, .003
    _, cov = b2.feature_moments(b2.physical_specs_at(theory_specs, pb, pm))
    j = b2.jacobian(lambda x,y: b2.feature_mean_from_characters(
        b2.physical_specs_at(theory_specs, x, y)), pb, pm)
    wdiag = np.diag(1/(scales**2))
    def sandwich(w: np.ndarray) -> np.ndarray:
        bread = np.linalg.inv(j.T @ w @ j)
        return bread @ (j.T @ w @ cov @ w @ j) @ bread
    j_b = j[:,0]
    var_a = float((j_b @ wdiag @ cov @ wdiag @ j_b)/(j_b @ wdiag @ j_b)**2)
    return {"point": [pb,pm], "delta_method_variance_n_times_var_pburst_A": var_a,
            "delta_method_covariance_n_times_cov_theta_B":
            sandwich(wdiag).tolist(), "delta_method_covariance_n_times_cov_theta_C":
            sandwich(weight).tolist(),
            "note": "Local asymptotic sandwich coefficients only; divide by N for covariance approximation. Not finite-sample accuracy or coverage."}


def main() -> None:
    global physical_specs_global
    circuit = build_spatial_burst_circuit(gate_p=.003, measurement_p=.003, burst_probability=.008)
    physical_specs_global, mapping = b2.extract_physical_signatures(circuit)
    circuit_table = make_template_table("circuit", physical_specs_global)
    dem_table = make_template_table("dem", physical_specs_global)
    scales_c, scales_d = profile_scales(circuit_table), profile_scales(dem_table)
    wc, wc_info = gls_weight(circuit_table, "circuit")
    wd, wd_info = gls_weight(dem_table, "dem")

    # Bilinear interpolation error on a deterministic half-cell lattice.
    interpolation = {"circuit": [], "dem": []}
    for kind, provider, table in (
        ("circuit", lambda p,m: b2.feature_mean_from_characters(
            b2.physical_specs_at(physical_specs_global,p,m)), circuit_table),
        ("dem", lambda p,m: b2.feature_mean_from_characters(b2.dem_specs(
            build_spatial_burst_circuit(gate_p=.003,measurement_p=m,burst_probability=p))), dem_table)):
        errs=[]
        for pb in np.arange(.0005,.020,.001):
            for pm in np.arange(.0005,.010,.001):
                err=provider(float(pb),float(pm))-bilinear(table,float(pb),float(pm))
                errs.append((float(np.max(np.abs(err))),float(np.sqrt(np.mean(err**2))),float(pb),float(pm)))
        interpolation[kind] = {"heldout_points":len(errs),"max_abs_error":max(e[0] for e in errs),
                               "max_feature_rms_error":max(e[1] for e in errs),
                               "worst_point":[max(errs)[2],max(errs)[3]]}

    # Exact categorical versus approximate DEM moment gap over the full nodes.
    gaps=np.abs(circuit_table-dem_table)
    model_gap={"node_count":int(len(PB_NODES)*len(PM_NODES)),
               "max_abs_feature_mean_gap":float(gaps.max()),
               "rms_over_all_node_features":float(np.sqrt(np.mean(gaps**2))),
               "worst_node": [float(PB_NODES[np.unravel_index(gaps.argmax(),gaps.shape)[0]]),
                              float(PM_NODES[np.unravel_index(gaps.argmax(),gaps.shape)[1]])],
               "nominal_and_mismatch":{}}
    for label,(pb,pm) in (("nominal",(.008,.003)),("mismatch",(.008,.006))):
        truth=b2.feature_mean_from_characters(b2.physical_specs_at(physical_specs_global,pb,pm))
        dem_specs=b2.dem_specs(build_spatial_burst_circuit(gate_p=.003,measurement_p=pm,burst_probability=pb))
        dem_mean=b2.feature_mean_from_characters(dem_specs)
        model_gap["nominal_and_mismatch"][label]={"max_abs":float(np.max(np.abs(truth-dem_mean))),
                                                   "rms":float(np.sqrt(np.mean((truth-dem_mean)**2)))}

    # Finite lattice local rank/conditioning sweep; this is not a continuum proof.
    identifiability={}
    for kind,table in (("circuit",circuit_table),("dem",dem_table)):
        rows=[]
        for pb in PB_NODES:
            for pm in PM_NODES:
                jac=b2.jacobian(lambda x,y:bilinear(table,x,y),float(pb),float(pm))
                sv=np.linalg.svd(jac,compute_uv=False)
                rows.append((float(sv[-1]),float(sv[0]/sv[-1]),float(pb),float(pm),int(np.count_nonzero(sv>sv[0]*1e-10))))
        identifiability[kind]={"lattice_points":len(rows),"minimum_small_singular_value":min(x[0] for x in rows),
                               "maximum_raw_condition":max(x[1] for x in rows),
                               "minimum_singular_value_point":[min(rows)[2],min(rows)[3]],
                               "maximum_condition_point":[max(rows,key=lambda x:x[1])[2],max(rows,key=lambda x:x[1])[3]],
                               "minimum_rank":min(x[4] for x in rows),
                               "warning":"finite lattice only; does not establish continuum/global identifiability"}

    comparison=scenario_comparison(physical_specs_global,circuit_table,dem_table,scales_c,scales_d,wc,wd)
    # The detector-only mismatch guard is an overidentification residual check:
    # after A, score the 45-vector residual using fixed reference covariance.
    # Its chi-square reference is asymptotic and approximate, not a guarantee.
    ref_specs=b2.physical_specs_at(physical_specs_global,.010,.003)
    _,ref_cov=b2.feature_moments(ref_specs)
    evals,evecs=np.linalg.eigh(ref_cov)
    inv_cov=(evecs/np.maximum(evals,evals.max()*1e-6)) @ evecs.T
    guard={}
    for n in (1000,10000):
        threshold=float(chi2.ppf(.99,44))
        guard[str(n)]={"approx_chi2_threshold_99pct_df44":threshold}
        for label,point in (("nominal",(.008,.003)),("mismatch",(.008,.006))):
            data=b2.feature_mean_from_characters(b2.physical_specs_at(physical_specs_global,*point))
            a=fit_grid(data,circuit_table,scales_c,None,fixed_pm=.003)
            null_gls=fit_grid(data,circuit_table,scales_c,wc,fixed_pm=.003)
            pred=bilinear(circuit_table,null_gls['estimate'][0],.003)
            rms=float(np.sqrt(np.mean(((data-pred)/scales_c)**2)))
            residual=data-pred
            statistic=float(n * residual @ inv_cov @ residual)
            guard[str(n)][label]={"A_profile_estimate":a['estimate'][0],
                                  "null_GLS_burst_estimate":null_gls['estimate'][0],
                                  "population_rms_residual_after_null_GLS_fit":rms,
                                  "population_noncentrality_approx":statistic,
                                  "would_flag_at_provisional_threshold":statistic>threshold,
                                  "fallback":"retain last accepted decoder setting; raise mismatch alarm"}

    # Deterministic finite-difference recovery and local covariance at nominal.
    fs=finite_sample(physical_specs_global,circuit_table,scales_c,wc)
    algebra_checks=[]
    for pb,pm in ((.008,.003),(.008,.006),(0.,.003),(.020,.010)):
        sp=b2.physical_specs_at(physical_specs_global,pb,pm)
        algebra_checks.append({"point":[pb,pm],"max_abs_character_vs_xor_convolution":float(np.max(np.abs(
            b2.feature_mean_from_characters(sp)-b2.feature_mean_from_convolution(sp))))})
    # Recompute a selected GLS objective by solving the regularized covariance
    # system directly, independently of the precomputed inverse-weight product.
    mismatch=b2.feature_mean_from_characters(b2.physical_specs_at(physical_specs_global,.008,.006))
    mismatch_fit=fit_grid(mismatch,dem_table,scales_d,wd)
    resid=mismatch-bilinear(dem_table,*mismatch_fit['estimate'])
    dem_ref_specs=b2.dem_specs(build_spatial_burst_circuit(gate_p=.003,measurement_p=.003,
                                                           burst_probability=.010))
    _,cov_ref=b2.feature_moments(dem_ref_specs)
    cov_reg=cov_ref+np.eye(45)*(np.linalg.eigvalsh(cov_ref).max()*1e-6)
    direct_gls=float(resid @ np.linalg.solve(cov_reg,resid))
    validation={"character_vs_independent_xor_convolution":algebra_checks,
                "mismatch_gls_fit_score_weight_product":mismatch_fit['score'],
                "mismatch_gls_fit_score_direct_solve":direct_gls,
                "gls_score_abs_difference":abs(direct_gls-mismatch_fit['score']),
                "interpolation_node_reproduction_max_abs":float(max(np.max(np.abs(
                    bilinear(circuit_table,float(pb),float(pm))-circuit_table[i,j]))
                    for i,pb in enumerate(PB_NODES) for j,pm in enumerate(PM_NODES)))}
    assert max(x['max_abs_character_vs_xor_convolution'] for x in algebra_checks) < 1e-12
    assert validation['gls_score_abs_difference'] < 1e-10
    assert validation['interpolation_node_reproduction_max_abs'] == 0.0
    assert min(x['minimum_rank'] for x in identifiability.values()) == 2
    results={"provenance":{"stim":"1.16.0","reviewed_checkpoint":"7597510a41be09b6b9c727e7ae6091627011424f",
                           "feature_dimension":45,"model_rectangle":{"p_burst":[0,.02],"p_measurement":[0,.01]},
                           "templates":{"p_burst_step":.001,"p_measurement_step":.001,"fit_step":.0001},
                           "gls":{"fixed_covariance_reference":[.01,.003],"eigenvalue_floor_relative":1e-6}},
             "mapping":mapping,"interpolation":interpolation,"exact_vs_dem_gap":model_gap,
             "lattice_identifiability":identifiability,"gls_regularization":{"circuit":wc_info,"dem":wd_info},
             "population_comparison_exact_circuit_truth":comparison,"finite_sample_local_theory":fs,
             "independent_validation":validation,
             "mismatch_guard_population_check":guard}
    OUT.write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({"out":str(OUT),"interpolation":interpolation,"gls":wc_info,
                      "scenario_estimates":{k:{m:v['estimate'] for m,v in row.items() if isinstance(v,dict) and 'estimate' in v}
                                            for k,row in comparison.items()},"guard":guard},indent=2))


if __name__=="__main__": main()
