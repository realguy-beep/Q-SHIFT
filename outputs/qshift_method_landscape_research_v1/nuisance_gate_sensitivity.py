"""Deterministic local sensitivity to the fixed gate-noise probability."""
from __future__ import annotations
import json,sys
from pathlib import Path
import numpy as np
import stim
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from outputs.qshift_method_landscape_research_v1.categorical_circuit_feature_expectations import categorical_sites,extract_sites,means_from_characters,means_by_direct_xor
from outputs.qshift_method_landscape_research_v1.categorical_circuit_parameter_grid_audit import circuit_signature,exact_cov
from outputs.qshift_method_landscape_research_v1.dem_feature_expectations import feature_means, labels
from simulator import build_spatial_burst_circuit
B=.010; M=.003; G=.003; H=1e-5

def circuit(b,m,g): return build_spatial_burst_circuit(memory_basis='z',regime='balanced',distance=3,rounds=5,gate_p=float(g),measurement_p=float(m),bias_ratio=10.,burst_probability=float(b),burst_pair=(8,10))
def reweight(template,c):
 raw=extract_sites(c)
 if len(raw)!=len(template): raise RuntimeError('noise-site count changed')
 out=[]
 for (idx,qid,alts),(oq,old) in zip(raw,template):
  if len(alts)!=len(old): raise RuntimeError('alternative count changed')
  mapped=[]
  for (p,paulis),(op,support,obs,oldpaulis) in zip(alts,old):
   if paulis!=oldpaulis: raise RuntimeError('Pauli alternative topology changed')
   mapped.append((p,support,obs,paulis))
  out.append((qid,mapped))
 return out
def exact_mean(template,signature,b,m,g):
 c=circuit(b,m,g)
 if circuit_signature(c)!=signature: raise RuntimeError('non-noise circuit structure changed')
 return means_from_characters(reweight(template,c))
def dem_mean(b,m,g):
 c=circuit(b,m,g); dem=c.detector_error_model(decompose_errors=True,approximate_disjoint_errors=True); mechs=[]
 for ins in dem:
  if ins.type!='error': continue
  support=frozenset(t.val for t in ins.targets_copy() if t.is_relative_detector_id())
  mechs.append((float(ins.args_copy()[0]),support))
 return feature_means(mechs)
def summarize(J,scale):
 W=J/scale[:,None]; sv=np.linalg.svd(W,compute_uv=False); norms=np.linalg.norm(W,axis=0); cos=(W.T@W)/np.outer(norms,norms); A=W[:,:2]; g=W[:,2]; proj=A@np.linalg.pinv(A)@g
 return {'rank':int(np.linalg.matrix_rank(W)),'singular_values_nominal_variance_standardized':sv.tolist(),'condition_ratio':float(sv[0]/sv[-1]),'column_cosines_burst_measurement_gate':cos.tolist(),'gate_projection_fraction_onto_burst_measurement_span':float(np.linalg.norm(proj)/np.linalg.norm(g)),'gate_residual_fraction_after_projection':float(np.linalg.norm(g-proj)/np.linalg.norm(g)),'standardized_column_norms':norms.tolist()}
def main():
 c0=circuit(B,M,G); sig=circuit_signature(c0); template,stats=categorical_sites(c0)
 def exact(b,m,g): return exact_mean(template,sig,b,m,g)
 funcs={'exact_categorical_circuit':exact,'approximate_dem':dem_mean}; outputs={}; covariance=exact_cov(reweight(template,c0),exact(B,M,G)); scale=np.sqrt(np.maximum(np.diag(covariance),1e-12))
 for name,f in funcs.items():
  jb=(f(B+H,M,G)-f(B-H,M,G))/(2*H); jm=(f(B,M+H,G)-f(B,M-H,G))/(2*H); jg=(f(B,M,G+H)-f(B,M,G-H))/(2*H); J=np.column_stack((jb,jm,jg)); outputs[name]=summarize(J,scale); names=labels(); outputs[name]['top_absolute_feature_derivatives']={param:[{'feature':names[int(i)],'derivative':float(J[int(i),col])} for i in np.argsort(np.abs(J[:,col]))[-8:][::-1]] for col,param in enumerate(('burst_p','measurement_p','gate_p'))}
  if name=='exact_categorical_circuit':
   asym={}
   for k,params in ((2,['burst_p','measurement_p']),(3,['burst_p','measurement_p','gate_p'])):
    Jk=J[:,:k]; W=np.diag(1.0/np.diag(covariance)); bread=np.linalg.inv(Jk.T@W@Jk); vdiag=bread@(Jk.T@W@covariance@W@Jk)@bread; vopt=np.linalg.inv(Jk.T@np.linalg.solve(covariance,Jk)); asym[str(k)]={'parameters':params,'diagonal_standardized_profile_sandwich_covariance_per_iid_shot':vdiag.tolist(),'diagonal_standardized_profile_sd_per_sqrt_shots':[float(x) for x in np.sqrt(np.diag(vdiag))],'oracle_full_covariance_gmm_covariance_per_iid_shot':vopt.tolist(),'oracle_full_covariance_gmm_sd_per_sqrt_shots':[float(x) for x in np.sqrt(np.diag(vopt))]}
   outputs[name]['asymptotic_iid_shot_moment_covariance_sensitivity']=asym
   direct=means_by_direct_xor(reweight(template,c0)); outputs[name]['nominal_direct_xor_max_error']=float(np.max(np.abs(exact(B,M,G)-direct)))
   outputs[name]['largest_burst_sensitivity_pair_features']=[float(x) for x in jb[40:]]
   outputs[name]['largest_measurement_sensitivity_pair_features']=[float(x) for x in jm[40:]]
   outputs[name]['largest_gate_sensitivity_pair_features']=[float(x) for x in jg[40:]]
 result={'classification':'DETERMINISTIC_LOCAL_GATE_NUISANCE_SENSITIVITY','nominal_parameters':{'burst_p':B,'measurement_p':M,'gate_p':G,'finite_difference_step':H},'fault_map':stats,'results':outputs,'interpretation_limits':['Local derivatives do not establish global identifiability or finite-history estimation accuracy.','Gate p is a single scalar multiplying the existing fixed categorical gate-noise family; this does not introduce a new physical noise mechanism.','Correlated readout, drift in gate-channel composition, coherent errors, leakage and decoder utility are not tested.','Approximate DEM values use decompose_errors=True and approximate_disjoint_errors=True.'],'sampling_calls':0,'decoder_calls':0}
 p=HERE/'NUISANCE_GATE_SENSITIVITY.json'; p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); print(json.dumps({'output':p.relative_to(ROOT).as_posix(),'exact':outputs['exact_categorical_circuit'],'dem':outputs['approximate_dem']},indent=2))
if __name__=='__main__': main()
