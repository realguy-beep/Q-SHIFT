"""Population-limit mismatch screen for the one-parameter burst profile.
No sampled histories or decoder outcomes. Equal-knot pooled scales match the
population-limit pooling implied by equal-size historical template batches;
they are not the finite-sample scales realized by those batches.
"""
from __future__ import annotations
import json,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from outputs.qshift_method_landscape_research_v1.categorical_circuit_feature_expectations import categorical_sites,extract_sites,means_from_characters
from outputs.qshift_method_landscape_research_v1.categorical_circuit_parameter_grid_audit import circuit_signature,exact_cov
from outputs.qshift_method_landscape_research_v1.dem_feature_expectations import build_dem,feature_means,direct_feature_covariance
from simulator import build_spatial_burst_circuit
KNOTS=np.array([.002,.010,.018]); PGRID=np.linspace(.002,.018,1601); TRUE_B=np.array([.004,.010,.016]); TRUE_M=np.array([.001,.003,.005]); TRUE_G=np.array([.002,.003,.004]); G=.003

def circuit(b,m,g=G): return build_spatial_burst_circuit(memory_basis='z',regime='balanced',distance=3,rounds=5,gate_p=float(g),measurement_p=float(m),bias_ratio=10.,burst_probability=float(b),burst_pair=(8,10))
def reweight(template,c):
 raw=extract_sites(c)
 if len(raw)!=len(template): raise RuntimeError('noise-site count changed')
 out=[]
 for (ix,qid,alts),(oq,old) in zip(raw,template):
  if len(alts)!=len(old): raise RuntimeError('alternative count changed')
  mapped=[]
  for (p,paulis),(op,support,obs,oldpaulis) in zip(alts,old):
   if paulis!=oldpaulis: raise RuntimeError('noise alternative topology changed')
   mapped.append((p,support,obs,paulis))
  out.append((qid,mapped))
 return out
def exact_mean(template,sig,b,m,g=G):
 c=circuit(b,m,g)
 if circuit_signature(c)!=sig: raise RuntimeError('non-noise circuit structure changed')
 return means_from_characters(reweight(template,c))
def fit(observed,templates,scale):
 profile=np.column_stack([np.interp(PGRID,KNOTS,templates[:,j]) for j in range(45)])
 scores=np.mean(((profile-observed[None,:])/scale[None,:])**2,axis=1)
 i=int(np.argmin(scores)); return float(PGRID[i]),float(scores[i])
def dem_profile(b,m,g=G):
 c=circuit(b,m,g); dem=c.detector_error_model(decompose_errors=True,approximate_disjoint_errors=True); mechs=[]
 for ins in dem:
  if ins.type!='error': continue
  support=frozenset(t.val for t in ins.targets_copy() if t.is_relative_detector_id())
  mechs.append((float(ins.args_copy()[0]),support))
 return feature_means(mechs)
def main():
 c0=circuit(.010,.003); sig=circuit_signature(c0); template,_=categorical_sites(c0)
 exact_knots=np.vstack([exact_mean(template,sig,b,.003) for b in KNOTS]); dem_knots=np.vstack([dem_profile(b,.003) for b in KNOTS])
 nominal=exact_mean(template,sig,.010,.003); nominal_cov=exact_cov(reweight(template,c0),nominal)
 scales={'exact_nominal_single_shot_sd':np.sqrt(np.maximum(np.diag(nominal_cov),1e-12)),'unit_weights':np.ones(45)}
 knot_covs=[]
 for b,mu in zip(KNOTS,exact_knots): knot_covs.append(exact_cov(reweight(template,circuit(b,.003)),mu))
 pooled_mean=exact_knots.mean(axis=0); pooled_var=np.mean([np.diag(cov)+(mu-pooled_mean)**2 for cov,mu in zip(knot_covs,exact_knots)],axis=0)
 scales['equal_weight_pooled_template_sd']=np.sqrt(np.maximum(pooled_var,1e-12))
 cases=[]
 for b in TRUE_B:
  for m in TRUE_M: cases.append((float(b),float(m),G,'measurement_mismatch' if m!=.003 else 'nominal'))
 for b in TRUE_B:
  for g in TRUE_G:
   if g!=G: cases.append((float(b),.003,float(g),'gate_mismatch'))
 results=[]
 for b,m,g,condition in cases:
  observations=[('exact_categorical_circuit',exact_mean(template,sig,b,m,g)),('approximate_dem',dem_profile(b,m,g))]
  for weighting,scale in scales.items():
   for model,obs in observations:
    knots=exact_knots if model=='exact_categorical_circuit' else dem_knots
    estimate,score=fit(obs,knots,scale)
    results.append({'model':model,'weighting':weighting,'condition':condition,'true_burst_p':b,'true_measurement_p':m,'true_gate_p':g,'estimated_burst_p_population_profile':estimate,'burst_estimate_bias':estimate-b,'minimum_standardized_mean_square_residual':score})
 summaries={}
 for weighting in scales:
  subset=[x for x in results if x['weighting']==weighting]
  summaries[weighting]={}
  for condition in ('nominal','measurement_mismatch','gate_mismatch'):
   vals=[abs(x['burst_estimate_bias']) for x in subset if x['condition']==condition]
   summaries[weighting][condition+'_max_abs_burst_bias']=max(vals) if vals else None
 result={'classification':'DETERMINISTIC_POPULATION_LIMIT_BURST_ONLY_MISMATCH_SCREEN','parameter_grid':{'true_burst_p':TRUE_B.tolist(),'true_measurement_p':TRUE_M.tolist(),'true_gate_p':TRUE_G.tolist(),'fixed_template_measurement_p':.003,'fixed_template_gate_p':G,'burst_template_knots':KNOTS.tolist(),'burst_estimate_grid':{'min':float(PGRID[0]),'max':float(PGRID[-1]),'step':float(PGRID[1]-PGRID[0]),'count':len(PGRID)}},'objective':'Mean of 45 squared feature-mean residuals divided by fixed feature scales; each feature mean is linearly interpolated across the three burst knots and scored on the same 1,601-point p grid.','weighting_scenarios':{'exact_nominal_single_shot_sd':'Exact categorical-circuit marginal SD at burst p=.010, measurement p=.003, gate p=.003.','equal_weight_pooled_template_sd':'Population SD of an equal-weight mixture of the three exact categorical burst-template populations; this matches the population-limit source pooling weights because source uses two equal 2,000-shot batches at each knot. It is not the historical finite-sample scale vector.','unit_weights':'No feature scaling; sensitivity check only.'},'results':results,'bias_summaries':summaries,'interpretation_limits':['This is a population-limit profile analogue, not the sampled DetectorProfileEstimator.','Source inspection confirms two 2,000-shot batches at each of three template knots; equal-weight pooling therefore matches source pooling weights in the population limit, but not the random finite-sample scale vector.','No finite-history noise, calibration uncertainty, temporal drift, logical labels or decoder costs are included.','Approximate-DEM and exact categorical-circuit population maps are separately labeled.','Measurement and scalar gate settings are exploratory sensitivity points, not frozen or owner-approved stress conditions.'],'sampling_calls':0,'decoder_calls':0}
 p=HERE/'POPULATION_BURST_ONLY_MISMATCH_AUDIT.json';p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({'output':p.relative_to(ROOT).as_posix(),'bias_summaries':summaries,'rows':len(results)},indent=2))
if __name__=='__main__':main()
