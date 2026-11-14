"""Compare exact categorical-circuit and approximate-DEM feature profiles.

A deterministic single-fault support map is constructed once. Since all scanned
settings share the same Clifford circuit and categorical-site topology, channel
probabilities are reweighted over a bounded 9x9 grid without new fault-map runs.
No stochastic sampling, decoding, or logical outcome evaluation is performed.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import stim
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from outputs.qshift_method_landscape_research_v1.categorical_circuit_feature_expectations import categorical_sites, extract_sites, means_from_characters, means_by_direct_xor, feature_supports
from outputs.qshift_method_landscape_research_v1.dem_feature_expectations import build_dem, feature_means
from simulator import build_spatial_burst_circuit
BG=np.linspace(.002,.018,9); MG=np.linspace(.001,.005,9); H=1e-4

def reweight(template, circuit):
 raw=extract_sites(circuit)
 if len(raw)!=len(template): raise RuntimeError('noise-site count changed across grid')
 out=[]
 for (idx,qid,alts),(old_qid,old_alts) in zip(raw,template):
  if len(alts)!=len(old_alts): raise RuntimeError('alternative count changed')
  mapped=[]
  for (p,paulis),(old_p,support,obs,old_paulis) in zip(alts,old_alts):
   if paulis!=old_paulis: raise RuntimeError('categorical alternative ordering changed')
   mapped.append((p,support,obs,paulis))
  out.append((qid,mapped))
 return out

def parity_char(sites, selected):
 v=1.0
 for qid,alts in sites:
  factor=1.0
  for p,support,_,_ in alts:
   if len(set(selected).intersection(support))%2: factor-=2*p
  v*=factor
 return v

def exact_cov(sites, means):
 fs=feature_supports()
 def all_one(ds):
  ds=tuple(sorted(set(ds))); k=len(ds); total=0.
  for mask in range(1<<k):
   subset=tuple(ds[j] for j in range(k) if (mask>>j)&1)
   total+=(-1)**mask.bit_count()*parity_char(sites,subset)
  return total/(1<<k)
 c=np.empty((45,45))
 for i,a in enumerate(fs):
  for j in range(i,45):
   v=all_one(set(a).union(fs[j]))-means[i]*means[j]
   c[i,j]=c[j,i]=v
 return c

def construct(b,m):
 return build_spatial_burst_circuit(memory_basis='z',regime='balanced',distance=3,rounds=5,gate_p=.003,measurement_p=float(m),bias_ratio=10.,burst_probability=float(b),burst_pair=(8,10))

def circuit_signature(c):
 noise={'PAULI_CHANNEL_1','PAULI_CHANNEL_2','X_ERROR','E'}
 return tuple((i.name,tuple(str(t) for t in i.targets_copy()),None if i.name in noise else tuple(i.gate_args_copy())) for i in c)

def run_grid(template,signature):
 exact={}; approx={}; validation_error=0.0
 for b in BG:
  for m in MG:
   key=(float(b),float(m)); c=construct(*key);
   if circuit_signature(c)!=signature: raise RuntimeError("circuit structure changed across parameter grid")
   sites=reweight(template,c); exact[key]=means_from_characters(sites); direct=means_by_direct_xor(sites); validation_error=max(validation_error,float(np.max(np.abs(exact[key]-direct)))); approx[key]=feature_means(build_dem(*key)[1])
 return exact,approx,validation_error

def nearest_dist(profiles,scale):
 rows=sorted(profiles); near={'distance':float('inf'),'left':None,'right':None}; both=float('inf')
 for i,a in enumerate(rows):
  for b in rows[i+1:]:
   d=float(np.linalg.norm((profiles[a]-profiles[b])/scale)/np.sqrt(45))
   if d<near['distance']: near={'distance':d,'left':a,'right':b}
   if a[0]!=b[0] and a[1]!=b[1]: both=min(both,d)
 return near,both

def main():
 template_circuit=construct(.010,.003); signature=circuit_signature(template_circuit); template,_=categorical_sites(template_circuit); ex,dm,direct_error=run_grid(template,signature)
 if direct_error>2e-12: raise RuntimeError('grid direct XOR recursion mismatch')
 nominal=ex[(.01,.003)]; cov=exact_cov(reweight(template,construct(.01,.003)),nominal); scale=np.sqrt(np.maximum(np.diag(cov),1e-12)); eig=np.linalg.eigvalsh(cov); symmetry_error=float(np.max(np.abs(cov-cov.T))); variance_error=float(np.max(np.abs(np.diag(cov)-nominal*(1-nominal))))
 if symmetry_error>1e-12 or variance_error>1e-12 or eig[0]<=0: raise RuntimeError('exact feature covariance validation failed')
 ne,both_e=nearest_dist(ex,scale); nd,both_d=nearest_dist(dm,scale); gap={'absolute':-1.0}
 for key in ex:
  delta=ex[key]-dm[key]; idx=int(np.argmax(np.abs(delta))); value=float(abs(delta[idx]))
  if value>gap['absolute']:
   pairnames=['D%d&D%d'%pair for pair in ((8,10),(16,18),(24,26),(32,34),(36,38))]; name=f'D{idx}' if idx<40 else pairnames[idx-40]; gap={'absolute':value,'burst_p':key[0],'measurement_p':key[1],'feature_index':idx,'feature':name,'exact_mean':float(ex[key][idx]),'approximate_dem_mean':float(dm[key][idx])}
 max_gap=gap['absolute']
 probes=[(.002,.001),(.018,.001),(.002,.005),(.018,.005),(.010,.003),(.006,.004),(.014,.002)]; probe=[]
 for b,m in probes:
  rec={'burst_p':b,'measurement_p':m}
  for name,func in [('exact_categorical_circuit',lambda x,y: means_from_characters(reweight(template,construct(x,y)))),('approximate_dem',lambda x,y: feature_means(build_dem(x,y)[1]))]:
   jb=(func(b+H,m)-func(b-H,m))/(2*H); jm=(func(b,m+H)-func(b,m-H))/(2*H); J=np.column_stack((jb,jm)); sv=np.linalg.svd(J,compute_uv=False); sw=np.linalg.svd(J/scale[:,None],compute_uv=False)
   rec[name]={'rank':int(np.linalg.matrix_rank(J)),'raw_singular_values':sv.tolist(),'raw_condition_ratio':float(sv[0]/sv[-1]),'nominal_variance_standardized_singular_values':sw.tolist(),'standardized_condition_ratio':float(sw[0]/sw[-1])}
  probe.append(rec)
 result={'classification':'DETERMINISTIC_EXACT_CATEGORICAL_CIRCUIT_VS_APPROXIMATE_DEM_PROFILE_SCREEN','configuration':{'gate_p':.003,'bias_ratio':10.,'burst_pair':[8,10],'distance':3,'rounds':5,'stim_version':stim.__version__,'dem_options':{'decompose_errors':True,'approximate_disjoint_errors':True}},'parameter_grid':{'burst_probability':BG.tolist(),'measurement_probability':MG.tolist(),'measurement_range_status':'exploratory sensitivity range only; not a frozen or owner-approved experimental condition'},'profile_count':len(ex),'max_direct_xor_validation_error_over_grid':direct_error,'distance_metric':'RMS Euclidean distance between feature-mean vectors standardized by exact categorical-circuit nominal single-shot feature standard deviations.','exact_categorical_circuit':{'nearest_distinct_grid_profiles':ne,'minimum_distance_both_parameters_differ':both_e},'approximate_dem':{'nearest_distinct_grid_profiles':nd,'minimum_distance_both_parameters_differ':both_d},'max_abs_exact_categorical_vs_approximate_dem_mean_difference_over_grid':max_gap,'maximum_mean_difference_location':gap,'nominal_exact_feature_covariance_eigenvalue_range':[float(eig[0]),float(eig[-1])],'covariance_symmetry_error':symmetry_error,'binary_variance_identity_error':variance_error,'nominal_exact_feature_covariance_condition_ratio':float(eig[-1]/eig[0]),'local_jacobian_probes':probe,'limitations':['Grid screen cannot prove global injectivity or exclude off-grid collisions.','Population profile separation is not finite-history estimation accuracy or decoder utility.','Exact categorical means use the actual independent categorical Pauli channel probabilities and deterministic single-fault supports; validity depends on the verified common Clifford topology and independent site semantics.','Readout mechanisms in this circuit are independent X_ERROR sites; correlated readout nuisance and temporal drift are not varied.','The approximate DEM is separately computed with disjoint-error approximation; differences quantify means for this fixed model/configuration only.'],'sampling_calls':0,'decoder_calls':0}
 path=HERE/'CATEGORICAL_CIRCUIT_PARAMETER_GRID_AUDIT.json'; path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); print(json.dumps({'output':path.relative_to(ROOT).as_posix(),'profiles':len(ex),'exact_nearest':ne,'dem_nearest':nd,'both_parameter_distance_exact':both_e,'max_dem_mean_gap':max_gap,'max_gap_location':gap,'exact_cov_condition':result['nominal_exact_feature_covariance_condition_ratio'],'all_probe_ranks_exact':[x['exact_categorical_circuit']['rank'] for x in probe]},indent=2))
if __name__=='__main__': main()
