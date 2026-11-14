"""Exact/approximate-DEM local sensitivity to existing Pauli bias_ratio."""
from __future__ import annotations
import json,sys
from pathlib import Path
import numpy as np
import stim
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from outputs.qshift_method_landscape_research_v1.categorical_circuit_feature_expectations import categorical_sites,extract_sites,means_from_characters,means_by_direct_xor
from outputs.qshift_method_landscape_research_v1.categorical_circuit_parameter_grid_audit import circuit_signature,exact_cov
from outputs.qshift_method_landscape_research_v1.dem_feature_expectations import feature_means,labels
from simulator import build_spatial_burst_circuit
from noise_model import axis_weights
B=.010;M=.003;G=.003;R=10.;HB=1e-5;HM=1e-5;HG=1e-5;HR=.01

def circuit(b,m,g,r):return build_spatial_burst_circuit(memory_basis='z',regime='balanced',distance=3,rounds=5,gate_p=float(g),measurement_p=float(m),bias_ratio=float(r),burst_probability=float(b),burst_pair=(8,10))
def reweight(template,c):
 raw=extract_sites(c)
 if len(raw)!=len(template):raise RuntimeError('noise-site count changed')
 out=[]
 for (_,qid,alts),(_,oldq,old) in zip(raw,[(None,qid,alts) for qid,alts in template]):
  if len(alts)!=len(old):raise RuntimeError('alternative count changed')
  mapped=[]
  for (p,paulis),(op,support,obs,oldpaulis) in zip(alts,old):
   if paulis!=oldpaulis:raise RuntimeError('Pauli topology changed')
   mapped.append((p,support,obs,paulis))
  out.append((qid,mapped))
 return out
def exact_mean(template,sig,b,m,g,r):
 c=circuit(b,m,g,r)
 if circuit_signature(c)!=sig:raise RuntimeError('non-noise circuit changed')
 return means_from_characters(reweight(template,c))
def dem_mean(b,m,g,r):
 d=circuit(b,m,g,r).detector_error_model(decompose_errors=True,approximate_disjoint_errors=True);mechs=[]
 for i in d:
  if i.type=='error':mechs.append((float(i.args_copy()[0]),frozenset(t.val for t in i.targets_copy() if t.is_relative_detector_id())))
 return feature_means(mechs)
def summarize(J,scale,parameter_scale):
 W=J/scale[:,None];norm=np.linalg.norm(W,axis=0); denom=np.outer(norm,norm); cos=np.empty_like(denom,dtype=object)
 for i in range(len(norm)):
  for j in range(len(norm)): cos[i,j]=float((W[:,i]@W[:,j])/denom[i,j]) if denom[i,j]>1e-20 else None
 Jr=W*parameter_scale[None,:];sv=np.linalg.svd(Jr,compute_uv=False);N=Jr[:,:2];g=Jr[:,2];proj=N@np.linalg.pinv(N)@g
 return {'rank':int(np.linalg.matrix_rank(Jr)),'dimensionless_singular_values':sv.tolist(),'dimensionless_condition_ratio':float(sv[0]/sv[-1]) if sv[-1]>1e-14 else None,'column_cosines_burst_measurement_gate_bias_ratio':cos.tolist(),'gate_projection_fraction_onto_burst_measurement_span':float(np.linalg.norm(proj)/np.linalg.norm(g)) if np.linalg.norm(g)>1e-14 else None,'bias_ratio_projection_fraction_onto_burst_measurement_gate_span':None if norm[3]<=1e-14 else float(np.linalg.norm(N@np.linalg.pinv(N)@Jr[:,3])/np.linalg.norm(Jr[:,3])),'standardized_column_norms_raw_derivatives':norm.tolist(),'inactive_parameter_columns':[p for p,n in zip(('burst_p','measurement_p','gate_p','bias_ratio'),norm) if n<=1e-14]}

def main():
 c0=circuit(B,M,G,R);sig=circuit_signature(c0);template,stats=categorical_sites(c0);mean=exact_mean(template,sig,B,M,G,R);scale=np.sqrt(np.maximum(np.diag(exact_cov(reweight(template,c0),mean)),1e-12));balanced_bias_inactive=(axis_weights('balanced',5.0)==axis_weights('balanced',20.0))
 fns={'exact_categorical_circuit':lambda b,m,g,r:exact_mean(template,sig,b,m,g,r),'approximate_dem':dem_mean};results={}
 for name,f in fns.items():
  jb=(f(B+HB,M,G,R)-f(B-HB,M,G,R))/(2*HB);jm=(f(B,M+HM,G,R)-f(B,M-HM,G,R))/(2*HM);jg=(f(B,M,G+HG,R)-f(B,M,G-HG,R))/(2*HG);jr=(f(B,M,G,R+HR)-f(B,M,G,R-HR))/(2*HR);J=np.column_stack((jb,jm,jg,jr));results[name]=summarize(J,scale,np.array([B,M,G,1.]))
  if name=='exact_categorical_circuit':
   if not balanced_bias_inactive: raise RuntimeError('expected bias_ratio to be inactive in balanced regime')
   direct=means_by_direct_xor(reweight(template,c0));results[name]['nominal_direct_xor_max_error']=float(np.max(np.abs(mean-direct)));names=labels();results[name]['top_bias_ratio_feature_derivatives']=[{'feature':names[int(i)],'derivative_per_bias_ratio_unit':float(jr[int(i)])} for i in np.argsort(np.abs(jr))[-8:][::-1]]
 result={'classification':'DETERMINISTIC_LOCAL_EXISTING_GATE_COMPOSITION_SENSITIVITY','nominal_parameters':{'burst_p':B,'measurement_p':M,'gate_p':G,'bias_ratio':R,'finite_difference_steps':{'burst_p':HB,'measurement_p':HM,'gate_p':HG,'bias_ratio':HR}},'relative_parameter_scaling_for_conditioning':[B,M,G,1.0],'fault_map':stats,'results':results,'bias_ratio_is_active_in_balanced_regime':not balanced_bias_inactive,'interpretation_limits':['The source axis_weights function makes bias_ratio inactive when regime=balanced; the zero derivative does not indicate an unidentified active physical parameter.','bias_ratio is an existing categorical Pauli-channel composition parameter, not a newly introduced physical mechanism.','Finite differences are local; the result does not establish global identifiability or finite-history bias.','The Pauli composition change is a model sensitivity only; no owner-approved stress condition is implied.','No stochastic sampling, detector histories, decoder calls, logical outcome evaluation, or protected data.'],'sampling_calls':0,'decoder_calls':0}
 p=HERE/'NUISANCE_BIAS_RATIO_SENSITIVITY.json';p.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8');print(json.dumps({'output':p.relative_to(ROOT).as_posix(),'exact':results['exact_categorical_circuit'],'dem':results['approximate_dem']},indent=2))
if __name__=='__main__':main()
