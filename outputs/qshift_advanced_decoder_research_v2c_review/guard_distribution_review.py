"""Deterministic covariance and asymptotic-reference audit for Candidate D.

No sampler, RNG, decoder, training, logical outcome, or evaluation data.
The script reuses deterministic Phase 2B fault signatures and Phase 2C
population template code, then examines covariance geometry and chi-square
assumption failures. It does not estimate an empirical alarm rate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import chi2, ncx2

ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit
from outputs.qshift_advanced_decoder_research_v2b import analyze_identifiability as b2
from outputs.qshift_advanced_decoder_research_v2c import joint_estimator_comparison as c2

OUT=Path(__file__).resolve().parent/'guard_distribution_results.json'


def specs_at(kind:str,physical:list[dict],pb:float,pm:float)->list[dict]:
    if kind=='exact_categorical': return b2.physical_specs_at(physical,pb,pm)
    return b2.dem_specs(build_spatial_burst_circuit(gate_p=.003,measurement_p=pm,
                                                      burst_probability=pb))


def covariance_stats(cov:np.ndarray)->dict:
    eig=np.linalg.eigvalsh((cov+cov.T)/2)
    return {'min_eigenvalue':float(eig.min()),'max_eigenvalue':float(eig.max()),
            'mean_eigenvalue':float(eig.mean()),'condition':float(eig.max()/eig.min()),
            'rank':int(np.count_nonzero(eig>eig.max()*1e-10))}


def physical_specs_with_gate(specs:list[dict],pb:float,pm:float,gate_p:float)->list[dict]:
    """Rescale existing balanced categorical gate channels; add no mechanism."""
    out=[]
    for spec in specs:
        item=dict(spec)
        if spec['kind'] in ('categorical_1q','categorical_2q'):
            alts=[(p*gate_p/.003,mask) for p,mask in spec['alts']]
            item['alts']=alts; item['identity']=1-sum(p for p,_ in alts)
        elif spec['kind']=='bernoulli_burst':
            mask=spec['alts'][0][1]; item['identity']=1-pb; item['alts']=[(pb,mask)] if pb else []
        elif spec['kind']=='bernoulli_measurement':
            mask=spec['alts'][0][1]; item['identity']=1-pm; item['alts']=[(pm,mask)] if pm else []
        out.append(item)
    return out


def existing_a_population_limit(data:np.ndarray,table:np.ndarray)->dict:
    """Exact population-limit counterpart of DetectorProfileEstimator.estimate."""
    knot_idx=[0,5,10,15,20]
    knots=np.asarray([0,.005,.010,.015,.020],dtype=float)
    templates=table[knot_idx,3,:]  # p_m=.003, p_b knots as original estimator
    scales=c2.profile_scales(table)
    grid=np.linspace(0,.020,2001)   # source GRID_STEP=1e-5, inclusive endpoints
    expected=np.column_stack([np.interp(grid,knots,templates[:,j]) for j in range(45)])
    scores=np.mean(((expected-data)/scales)**2,axis=1)
    i=int(np.argmin(scores))
    return {'estimate_pburst':float(grid[i]),'assumed_pmeasurement':.003,
            'grid_step':.00001,'grid_count':len(grid),'score':float(scores[i]),
            'feature_scales':'population-limit pooled variance over five burst template batches'}


def main()->None:
    circuit=build_spatial_burst_circuit(gate_p=.003,measurement_p=.003,burst_probability=.008)
    physical,mapping=b2.extract_physical_signatures(circuit)
    exact_table=c2.make_template_table('circuit',physical)
    dem_table=c2.make_template_table('dem',physical)
    model_tables={'exact_categorical':exact_table,'approximate_dem':dem_table}
    results={'provenance':{'reviewed_phase2c_checkpoint':'a5e6a86b24affc355169dbbf188e3ee1e247b1e7',
                           'stim':'1.16.0','parameter_rectangle':{'burst':[0,.02],'measurement':[0,.01]},
                           'test_grid_step':.0001,'reference_covariance_point':[.010,.003],
                           'test':'fixed-reference covariance score after constrained fixed-measurement profile fit',
                           'no_sampling':True},'burst_mapping':mapping,'candidate_cases':{}}
    for template_kind,table in model_tables.items():
        scales=c2.profile_scales(table)
        ref_specs=specs_at(template_kind,physical,.010,.003)
        _,ref_cov=b2.feature_moments(ref_specs)
        eig,vec=np.linalg.eigh((ref_cov+ref_cov.T)/2)
        ridge=float(eig.max()*1e-6)
        regularized=eig+ridge
        whitening=(vec/np.sqrt(regularized))@vec.T
        weight=(vec/regularized)@vec.T
        ref_info=covariance_stats(ref_cov)
        case_results={'reference_covariance':ref_info,'ridge':ridge,'cases':{}}
        for data_kind in ('exact_categorical','approximate_dem'):
            for label,(pb,pm) in {'nominal_null':(.008,.003),'measurement_mismatch':(.008,.006)}.items():
                data_specs=specs_at(data_kind,physical,pb,pm)
                mu,cov_data=b2.feature_moments(data_specs)
                fit=c2.fit_grid(mu,table,scales,weight,fixed_pm=.003)
                pb_fit=float(fit['estimate'][0])
                null_mean=c2.bilinear(table,pb_fit,.003)
                residual=mu-null_mean
                raw_energy_per_shot=float(residual@weight@residual)
                # The discrete grid fit is the actual estimator. This optional
                # projection is a separate continuous-nuisance asymptotic aid.
                j=b2.jacobian(lambda x,y:c2.bilinear(table,x,y),pb_fit,.003)[:,0]
                x=whitening@j
                proj=np.eye(len(mu))-np.outer(x,x)/(x@x)
                projected_mean=proj@(whitening@residual)
                projected_energy=float(projected_mean@projected_mean)
                cov_whitened=whitening@cov_data@whitening
                cov_whitened=(cov_whitened+cov_whitened.T)/2
                vals=np.linalg.eigvalsh(cov_whitened)
                projected_cov=proj@cov_whitened@proj
                pvals=np.linalg.eigvalsh((projected_cov+projected_cov.T)/2)
                pvals=pvals[pvals>max(float(pvals.max()),1e-14)*1e-9]
                # Sensitivity-only nc-chi-square probabilities require the
                # stronger false assumption that projected truth covariance
                # equals identity and the fitted nuisance is continuous.
                nc_lambdas={str(n):float(n*projected_energy) for n in (1000,10000)}
                idealized={}
                for n,lam in ((int(k),v) for k,v in nc_lambdas.items()):
                    cutoff=float(chi2.ppf(.99,44))
                    idealized[str(n)]={'lambda_continuous_projection':lam,
                                       'central_chi2_df44_99pct_cutoff':cutoff,
                                       'ncx2_tail_if_identity_covariance_df44':float(ncx2.sf(cutoff,44,lam)),
                                       'status':'counterfactual sensitivity only; not an alarm operating characteristic'}
                case_results['cases'][f'{data_kind}:{label}']={
                    'data_point':[pb,pm],'template_kind':template_kind,'null_grid_fit_pburst':pb_fit,
                    'grid_runner_up_gap':fit['runner_up_gap'],
                    'population_residual_energy_per_shot_discrete_grid':raw_energy_per_shot,
                    'lambda_population_energy_N1000_N10000':{str(n):float(n*raw_energy_per_shot) for n in (1000,10000)},
                    'continuous_tangent_projected_energy_per_shot':projected_energy,
                    'whitened_truth_covariance_eigenvalue_summary':{'min':float(vals.min()),'max':float(vals.max()),
                        'mean':float(vals.mean()),'sd':float(vals.std()),'rank':int(np.count_nonzero(vals>1e-9))},
                    'continuous_projection_covariance_positive_eigenvalues':{'count':int(len(pvals)),
                        'min':float(pvals.min()),'max':float(pvals.max()),'mean':float(pvals.mean()),
                        'range_note':'should be near one for a central/noncentral chi-square reference; not assumed'},
                    'counterfactual_idealized_probabilities':idealized,
                    'fit_grid_fixed_step':.0001}
        case_results['central_cutoffs']={'chi2_44_99pct':float(chi2.ppf(.99,44)),
                                         'chi2_45_99pct':float(chi2.ppf(.99,45))}
        results['candidate_cases'][template_kind]=case_results
    profile_case={}
    for label,(pb,pm) in {'nominal':(.008,.003),'mismatch':(.008,.006),
                          'measurement_low':(.008,0.),'measurement_high':(.008,.010)}.items():
        truth=b2.feature_mean_from_characters(b2.physical_specs_at(physical,pb,pm))
        exact_a=existing_a_population_limit(truth,exact_table)
        dem_a=existing_a_population_limit(truth,dem_table)
        coarse_a=c2.fit_grid(truth,exact_table,c2.profile_scales(exact_table),None,fixed_pm=.003)
        profile_case[label]={'truth':[pb,pm],
            'A_exact_population_limit':exact_a,'A_DEM_template_population_limit':dem_a,
            'phase2c_comparison_grid_implementation':{'estimate_pburst':coarse_a['estimate'][0],
                'grid_step':.0001,'template_interpolation':'bilinear .001 joint lattice row, not original five-knot line'},
            'absolute_estimate_difference_exactA_vs_phase2c_grid':abs(exact_a['estimate_pburst']-coarse_a['estimate'][0])}
    results['candidate_A_population_limit_verification']=profile_case
    # Deterministic sensitivity to the existing balanced gate-rate parameter.
    # Channel alternatives and all detector signatures remain unchanged.
    derivs=[]
    for ix in range(3):
        h=1e-6; lo=[.008,.003,.003]; hi=lo.copy(); lo[ix]-=h; hi[ix]+=h
        a=b2.feature_mean_from_characters(physical_specs_with_gate(physical,*lo))
        z=b2.feature_mean_from_characters(physical_specs_with_gate(physical,*hi))
        derivs.append((z-a)/(2*h))
    j3=np.column_stack(derivs); norms=np.linalg.norm(j3,axis=0)
    cos=j3.T@j3/np.outer(norms,norms); sv=np.linalg.svd(j3,compute_uv=False)
    gate_rows={}
    for gp in (.002,.003,.004):
        exact_mu=b2.feature_mean_from_characters(physical_specs_with_gate(physical,.008,.003,gp))
        dem_mu=b2.feature_mean_from_characters(b2.dem_specs(build_spatial_burst_circuit(
            gate_p=gp,measurement_p=.003,burst_probability=.008)))
        fit_exact=c2.fit_grid(exact_mu,exact_table,c2.profile_scales(exact_table),None)
        fit_dem=c2.fit_grid(exact_mu,dem_table,c2.profile_scales(dem_table),None)
        dem_truth_fit=c2.fit_grid(dem_mu,dem_table,c2.profile_scales(dem_table),None)
        gate_rows[str(gp)]={'exact_truth_fit_exact_templates':fit_exact['estimate'],
                            'exact_truth_fit_DEM_templates':fit_dem['estimate'],
                            'DEM_truth_fit_DEM_templates':dem_truth_fit['estimate'],
                            'exact_vs_DEM_truth_mean_max_abs':float(np.max(np.abs(exact_mu-dem_mu))),
                            'exact_vs_DEM_truth_mean_rms':float(np.sqrt(np.mean((exact_mu-dem_mu)**2)))}
    results['fixed_gate_noise_sensitivity']={'gate_values':[.002,.003,.004],
        'local_45x3_jacobian_singular_values':sv.tolist(),'local_condition':float(sv[0]/sv[-1]),
        'derivative_column_cosines_burst_measurement_gate':cos.tolist(),
        'population_fits_with_templates_fixed_at_gate_p_003':gate_rows,
        'note':'Only the existing balanced categorical gate-channel rate is varied; no new mechanism or sampling.'}
    OUT.write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'out':str(OUT),'cutoffs':{k:v['central_cutoffs'] for k,v in results['candidate_cases'].items()},
                      'cases':{k:{c:{'fit':v['null_grid_fit_pburst'],'energy':v['population_residual_energy_per_shot_discrete_grid'],
                                      'cov_eigs':v['whitened_truth_covariance_eigenvalue_summary'],
                                      'projected_eigs':v['continuous_projection_covariance_positive_eigenvalues']}
                                 for c,v in x['cases'].items()} for k,x in results['candidate_cases'].items()}},indent=2))


if __name__=='__main__': main()
