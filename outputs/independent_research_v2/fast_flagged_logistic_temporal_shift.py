"""Frozen stationary selector under two alternating temporal gate-rate maps."""
from __future__ import annotations
import json,math,sys,time
from pathlib import Path
import numpy as np
import pymatching,stim
from scipy.stats import binomtest
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/"outputs"/"phase2b_pauli_bias"))
sys.path.insert(0,str(HERE))
from noise_model import build_circuit
from temporal_rate_hotspot import FACTORS,BASE_P,profile_circuit,clean,make_matching
from fast_flagged_logistic import CONDITIONS,features,wilson,DEM_THRESHOLD,make_models
PREFLIGHT_SEEDS=(2026121201,2026121202);MAIN_SEEDS=(2026121211,2026121212)
PREFLIGHT_SHOTS=10_000;MAIN_SHOTS=500_000;MAX_SECONDS=300.

def paired(a,b):
 d=b.astype(np.int8)-a.astype(np.int8);delta=float(d.mean());se=float(d.std(ddof=1)/math.sqrt(len(d)))
 ao=int(np.count_nonzero(a&~b));bo=int(np.count_nonzero(b&~a));n=ao+bo
 return {"delta_selector_minus_nominal_correlated":delta,"normal_95_ci":[delta-1.95996398454*se,delta+1.95996398454*se],"nominal_only_failures":ao,"selector_only_failures":bo,"mcnemar_exact_two_sided":float(binomtest(ao,n,.5).pvalue) if n else 1.}

def main():
 saved=json.load(open(HERE/'fast_flagged_logistic_replication_results.json'))
 model=saved['trained_models'][0];coef=np.asarray(model['coefficients'],dtype=np.float64);bias=float(model['intercept'])
 nominal=build_circuit('z','x_biased',distance=3,rounds=5,gate_p=.003,measurement_p=.003,bias_ratio=10.)
 nom_corr,nom_plain=make_models(nominal);prepared=[];pre=[];start=time.perf_counter()
 if (nominal.num_qubits,nominal.num_detectors,nominal.num_observables)!=(26,40,1):raise RuntimeError('nominal d3 geometry mismatch')
 for (profile,factors),seed in zip(FACTORS.items(),PREFLIGHT_SEEDS,strict=True):
  c,meta=profile_circuit(profile)
  if (c.num_qubits,c.num_detectors,c.num_observables)!=(26,40,1):raise RuntimeError('temporal d3 geometry mismatch')
  if meta['round_factors']!=list(factors) or abs(meta['factor_mean']-1)>1e-12 or abs(meta['mean_two_qubit_instruction_rate']-BASE_P)>1e-12:raise RuntimeError('temporal rate map/mean check failed')
  clean_c=clean(c);nd,no=clean_c.compile_detector_sampler(seed=1).sample(20,separate_observables=True)
  if nd.any() or no.any():raise RuntimeError('noiseless check failed')
  actual=make_matching(c)
  t=time.perf_counter();det,obs=c.compile_detector_sampler(seed=seed).sample(shots=PREFLIGHT_SHOTS,separate_observables=True);sample_s=time.perf_counter()-t
  t=time.perf_counter();cp=np.asarray(nom_corr.decode_batch(det,enable_correlations=True),dtype=bool).reshape(PREFLIGHT_SHOTS,-1);ct=time.perf_counter()-t
  t=time.perf_counter();pp=np.asarray(nom_plain.decode_batch(det,enable_correlations=False),dtype=bool).reshape(PREFLIGHT_SHOTS,-1);pt=time.perf_counter()-t
  cs=np.asarray([nom_corr.decode(s,enable_correlations=True) for s in det[:20]],dtype=bool).reshape(20,-1)
  ps=np.asarray([nom_plain.decode(s,enable_correlations=False) for s in det[:20]],dtype=bool).reshape(20,-1)
  if not np.array_equal(cp[:20],cs) or not np.array_equal(pp[:20],ps):raise RuntimeError('nominal scalar/batch mismatch')
  x,flag=features(det,cp,pp)
  if x.shape[1]!=42:raise RuntimeError('feature shape mismatch')
  t=time.perf_counter();actual.decode_batch(det,enable_correlations=True);at=time.perf_counter()-t
  t=time.perf_counter();pred=cp.copy();pred[flag]=(x[flag]@coef+bias>=0).reshape(-1,1);cl=time.perf_counter()-t
  projection=(sample_s+ct+pt+at+cl)*MAIN_SHOTS/PREFLIGHT_SHOTS
  pre.append({'profile':profile,'seed':seed,'shots':PREFLIGHT_SHOTS,'flagged':int(flag.sum()),'sample_seconds':sample_s,'nominal_correlated_seconds':ct,'nominal_ordinary_seconds':pt,'actual_map_diagnostic_seconds':at,'classifier_seconds':cl,'projected_seconds':projection,'factors':list(factors),'mean_two_qubit_rate':meta['mean_two_qubit_instruction_rate']})
  prepared.append((profile,c,actual,list(factors)))
 projection=sum(r['projected_seconds'] for r in pre)
 if projection>MAX_SECONDS:raise RuntimeError(f'projected runtime {projection:.1f}s exceeds cap')
 rows=[]
 for (profile,c,actual,factors),seed in zip(prepared,MAIN_SEEDS,strict=True):
  det,obs=c.compile_detector_sampler(seed=seed).sample(shots=MAIN_SHOTS,separate_observables=True)
  t=time.perf_counter();cp=np.asarray(nom_corr.decode_batch(det,enable_correlations=True),dtype=bool).reshape(MAIN_SHOTS,-1);ct=time.perf_counter()-t
  t=time.perf_counter();pp=np.asarray(nom_plain.decode_batch(det,enable_correlations=False),dtype=bool).reshape(MAIN_SHOTS,-1);pt=time.perf_counter()-t
  x,flag=features(det,cp,pp);t=time.perf_counter();pred=cp.copy()
  if flag.any():pred[flag]=(x[flag]@coef+bias>=0).reshape(-1,1)
  cl=time.perf_counter()-t
  t=time.perf_counter();ap=np.asarray(actual.decode_batch(det,enable_correlations=True),dtype=bool).reshape(MAIN_SHOTS,-1);at=time.perf_counter()-t
  cf=np.any(cp!=obs,axis=1);sf=np.any(pred!=obs,axis=1);af=np.any(ap!=obs,axis=1)
  rows.append({'profile':profile,'seed':seed,'shots':MAIN_SHOTS,'round_factors':factors,'flagged':int(flag.sum()),'flag_rate':float(flag.mean()),
   'failures':{'nominal_correlated':int(cf.sum()),'frozen_selector':int(sf.sum()),'actual_map_diagnostic':int(af.sum())},
   'ler':{'nominal_correlated':float(cf.mean()),'frozen_selector':float(sf.mean()),'actual_map_diagnostic':float(af.mean())},
   'wilson_95':{'nominal_correlated':wilson(int(cf.sum()),MAIN_SHOTS),'frozen_selector':wilson(int(sf.sum()),MAIN_SHOTS)},
   'paired':paired(cf,sf),'time_ratio':(ct+pt+cl)/ct,'nominal_correlated_seconds':ct,'nominal_ordinary_seconds':pt,'classifier_seconds':cl,'diagnostic_seconds':at})
 base=float(np.mean([r['ler']['nominal_correlated'] for r in rows]));candidate=float(np.mean([r['ler']['frozen_selector'] for r in rows]));diag=float(np.mean([r['ler']['actual_map_diagnostic'] for r in rows]))
 rel=1-candidate/base;per=[1-r['ler']['frozen_selector']/r['ler']['nominal_correlated'] for r in rows];tr=float(np.mean([r['time_ratio'] for r in rows]))
 out={'status':'fast_flagged_logistic_temporal_shift','nominal_gate_p':.003,'temporal_mean_gate_p':.003,'measurement_p':.003,'bias_ratio':10.,'frozen_model':'nominal z-memory/x-biased per-condition selector; no temporal retraining',
  'conditions':rows,'preflight':pre,'macro_ler':{'nominal_correlated':base,'frozen_selector':candidate,'actual_profile_matcher_diagnostic':diag},
  'macro_relative_reduction':rel,'per_profile_relative_reductions':per,'mean_frozen_policy_time_ratio':tr,
  'advancement_gate_passed':rel>=.10 and min(per)>=-.05 and tr<2,
  'preflight_samples':2*PREFLIGHT_SHOTS,'main_samples':2*MAIN_SHOTS,'projected_main_seconds':projection,'elapsed_seconds':time.perf_counter()-start,
  'scope':'stationary-trained frozen selector on two alternating temporal gate-rate profiles; Z-memory/X-bias d3 only; actual-map matcher diagnostic only'}
 (HERE/'fast_flagged_logistic_temporal_shift_results.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({'macro_ler':out['macro_ler'],'reduction':rel,'per_profile':per,'time_ratio':tr,'gate':out['advancement_gate_passed'],'elapsed':out['elapsed_seconds']},indent=2))
if __name__=='__main__':main()
