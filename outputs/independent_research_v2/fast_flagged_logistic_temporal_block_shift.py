"""Frozen stationary selector on a new blockwise per-round gate-rate pattern."""
from __future__ import annotations
import json,math,sys,time
from pathlib import Path
import numpy as np
import pymatching,stim
from scipy.stats import binomtest
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/"outputs"/"phase2b_pauli_bias"));sys.path.insert(0,str(HERE))
from noise_model import build_circuit
from temporal_rate_hotspot import clean,make_matching
from fast_flagged_logistic import features,wilson,make_models
FACTORS={'block_a':(.25,.25,1.75,1.75,1.),'block_b':(1.,1.75,1.75,.25,.25)}
PREFLIGHT_SEEDS=(2026121401,2026121402);MAIN_SEEDS=(2026121411,2026121412)
PRE=10_000;SHOTS=500_000;MAX_SECONDS=300.

def build_profile(factors):
 source=build_circuit('z','x_biased',distance=3,rounds=5,gate_p=.003,measurement_p=.003,bias_ratio=10.).flattened()
 out=stim.Circuit();round_index=0;rates=[];sites=0
 for ins in source:
  if ins.name=='PAULI_CHANNEL_2':
   args=np.asarray(ins.gate_args_copy(),dtype=np.float64)*factors[round_index]
   if float(args.sum())>=1:raise RuntimeError('invalid Pauli channel')
   out.append(ins.name,ins.targets_copy(),args.tolist());rates.append(float(args.sum()));sites+=len(ins.targets_copy())//2
  else:
   out.append(ins.name,ins.targets_copy(),ins.gate_args_copy())
   if ins.name=='MR':round_index+=1
 if round_index!=5 or sites!=120 or abs(sum(factors)/5-1)>1e-12:raise RuntimeError('unexpected temporal circuit structure')
 return out,{'factors':list(factors),'rounds':round_index,'pair_sites':sites,'factor_mean':sum(factors)/5,'mean_pair_rate':float(np.mean(rates))}

def paired(a,b):
 d=b.astype(np.int8)-a.astype(np.int8);m=float(d.mean());se=float(d.std(ddof=1)/math.sqrt(len(d)));ao=int(np.count_nonzero(a&~b));bo=int(np.count_nonzero(b&~a));n=ao+bo
 return {'delta_selector_minus_nominal_correlated':m,'normal_95_ci':[m-1.95996398454*se,m+1.95996398454*se],'nominal_only_failures':ao,'selector_only_failures':bo,'mcnemar_exact_two_sided':float(binomtest(ao,n,.5).pvalue) if n else 1.}

def main():
 saved=json.load(open(HERE/'fast_flagged_logistic_replication_results.json'));model=saved['trained_models'][0]
 coef=np.asarray(model['coefficients'],dtype=np.float64);bias=float(model['intercept'])
 nominal=build_circuit('z','x_biased',distance=3,rounds=5,gate_p=.003,measurement_p=.003,bias_ratio=10.)
 nc,np_=make_models(nominal);rows=[];pre=[];prepared=[];start=time.perf_counter()
 for (name,factors),seed in zip(FACTORS.items(),PREFLIGHT_SEEDS,strict=True):
  c,meta=build_profile(factors)
  if (c.num_qubits,c.num_detectors,c.num_observables)!=(26,40,1):raise RuntimeError('geometry mismatch')
  clean_c=clean(c);nd,no=clean_c.compile_detector_sampler(seed=1).sample(20,separate_observables=True)
  if nd.any() or no.any():raise RuntimeError('noiseless check failed')
  if abs(meta['mean_pair_rate']-.003)>1e-12:raise RuntimeError('mean two-qubit rate mismatch')
  actual=make_matching(c)
  t=time.perf_counter();det,obs=c.compile_detector_sampler(seed=seed).sample(shots=PRE,separate_observables=True);st=time.perf_counter()-t
  t=time.perf_counter();cp=np.asarray(nc.decode_batch(det,enable_correlations=True),dtype=bool).reshape(PRE,-1);ct=time.perf_counter()-t
  t=time.perf_counter();pp=np.asarray(np_.decode_batch(det,enable_correlations=False),dtype=bool).reshape(PRE,-1);pt=time.perf_counter()-t
  cs=np.asarray([nc.decode(s,enable_correlations=True) for s in det[:20]],dtype=bool).reshape(20,-1);ps=np.asarray([np_.decode(s,enable_correlations=False) for s in det[:20]],dtype=bool).reshape(20,-1)
  if not np.array_equal(cp[:20],cs) or not np.array_equal(pp[:20],ps):raise RuntimeError('scalar/batch mismatch')
  x,flag=features(det,cp,pp)
  if x.shape[1]!=42:raise RuntimeError('feature dimension mismatch')
  t=time.perf_counter();actual.decode_batch(det,enable_correlations=True);at=time.perf_counter()-t
  t=time.perf_counter();pred=cp.copy();pred[flag]=(x[flag]@coef+bias>=0).reshape(-1,1);cl=time.perf_counter()-t
  projected=(st+ct+pt+at+cl)*SHOTS/PRE
  pre.append({'profile':name,'seed':seed,'shots':PRE,'metadata':meta,'flags':int(flag.sum()),'sample_seconds':st,'nominal_correlated_seconds':ct,'nominal_ordinary_seconds':pt,'actual_diagnostic_seconds':at,'classifier_seconds':cl,'projected_seconds':projected})
  prepared.append((name,c,actual,factors))
 projection=sum(r['projected_seconds'] for r in pre)
 if projection>MAX_SECONDS:raise RuntimeError(f'projected runtime {projection:.1f}s exceeds cap')
 for (name,c,actual,factors),seed in zip(prepared,MAIN_SEEDS,strict=True):
  det,obs=c.compile_detector_sampler(seed=seed).sample(shots=SHOTS,separate_observables=True)
  t=time.perf_counter();cp=np.asarray(nc.decode_batch(det,enable_correlations=True),dtype=bool).reshape(SHOTS,-1);ct=time.perf_counter()-t
  t=time.perf_counter();pp=np.asarray(np_.decode_batch(det,enable_correlations=False),dtype=bool).reshape(SHOTS,-1);pt=time.perf_counter()-t
  x,flag=features(det,cp,pp);pred=cp.copy();t=time.perf_counter()
  if flag.any():pred[flag]=(x[flag]@coef+bias>=0).reshape(-1,1)
  cl=time.perf_counter()-t
  t=time.perf_counter();ap=np.asarray(actual.decode_batch(det,enable_correlations=True),dtype=bool).reshape(SHOTS,-1);at=time.perf_counter()-t
  cf=np.any(cp!=obs,axis=1);sf=np.any(pred!=obs,axis=1);af=np.any(ap!=obs,axis=1)
  rows.append({'profile':name,'seed':seed,'shots':SHOTS,'round_factors':list(factors),'flagged':int(flag.sum()),'failures':{'nominal_correlated':int(cf.sum()),'frozen_selector':int(sf.sum()),'actual_map_diagnostic':int(af.sum())},'ler':{'nominal_correlated':float(cf.mean()),'frozen_selector':float(sf.mean()),'actual_map_diagnostic':float(af.mean())},'wilson_95':{'nominal_correlated':wilson(int(cf.sum()),SHOTS),'frozen_selector':wilson(int(sf.sum()),SHOTS)},'paired':paired(cf,sf),'time_ratio':(ct+pt+cl)/ct})
 base=float(np.mean([r['ler']['nominal_correlated'] for r in rows]));cand=float(np.mean([r['ler']['frozen_selector'] for r in rows]));diag=float(np.mean([r['ler']['actual_map_diagnostic'] for r in rows]))
 red=1-cand/base;per=[1-r['ler']['frozen_selector']/r['ler']['nominal_correlated'] for r in rows];tr=float(np.mean([r['time_ratio'] for r in rows]))
 out={'status':'fast_flagged_logistic_temporal_block_shift','nominal_gate_p':.003,'temporal_mean_gate_p':.003,'measurement_p':.003,'bias_ratio':10.,'conditions':rows,'preflight':pre,'macro_ler':{'nominal_correlated':base,'frozen_selector':cand,'actual_profile_matcher_diagnostic':diag},'macro_relative_reduction':red,'per_profile_relative_reductions':per,'mean_time_ratio':tr,'advancement_gate_passed':red>=.10 and min(per)>=-.05 and tr<2,'preflight_samples':2*PRE,'main_samples':2*SHOTS,'projected_seconds':projection,'elapsed_seconds':time.perf_counter()-start,'scope':'frozen stationary selector on blockwise temporal gate-rate pair; Z-memory/X-bias d3 only'}
 (HERE/'fast_flagged_logistic_temporal_block_shift_results.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({'macro_ler':out['macro_ler'],'reduction':red,'profiles':per,'time_ratio':tr,'gate':out['advancement_gate_passed'],'elapsed':out['elapsed_seconds']},indent=2))
if __name__=='__main__':main()
