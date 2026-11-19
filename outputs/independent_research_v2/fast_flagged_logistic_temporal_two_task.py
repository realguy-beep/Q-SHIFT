"""Frozen task-specific selectors on a blockwise temporal rate map across two tasks."""
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
TASKS=(('z','x_biased',0),('x','z_biased',5))
PROFILES=(('block_a',(.25,.25,1.75,1.75,1.)),('block_b',(1.,1.75,1.75,.25,.25)))
PREFLIGHT_SEEDS=(2026121601,2026121602,2026121603,2026121604);MAIN_SEEDS=(2026121611,2026121612,2026121613,2026121614)
PRE=10_000;SHOTS=500_000;MAX_SECONDS=300.

def build_profile(basis,regime,factors):
 source=build_circuit(basis,regime,distance=3,rounds=5,gate_p=.003,measurement_p=.003,bias_ratio=10.).flattened();out=stim.Circuit();ri=0;rates=[];sites=0
 for inst in source:
  if inst.name=='PAULI_CHANNEL_2':
   args=np.asarray(inst.gate_args_copy(),dtype=np.float64)*factors[ri]
   if args.sum()>=1:raise RuntimeError('invalid categorical channel')
   out.append(inst.name,inst.targets_copy(),args.tolist());rates.append(float(args.sum()));sites+=len(inst.targets_copy())//2
  else:
   out.append(inst.name,inst.targets_copy(),inst.gate_args_copy())
   if inst.name=='MR':ri+=1
 if ri!=5 or sites!=120 or abs(sum(factors)/5-1)>1e-12:raise RuntimeError('temporal circuit structure mismatch')
 return out,{'rounds':ri,'pair_sites':sites,'factors':list(factors),'factor_mean':sum(factors)/5,'mean_pair_rate':float(np.mean(rates))}

def paired(a,b):
 d=b.astype(np.int8)-a.astype(np.int8);m=float(d.mean());se=float(d.std(ddof=1)/math.sqrt(len(d)));ao=int(np.count_nonzero(a&~b));bo=int(np.count_nonzero(b&~a));n=ao+bo
 return {'delta_selector_minus_nominal_correlated':m,'normal_95_ci':[m-1.95996398454*se,m+1.95996398454*se],'nominal_only_failures':ao,'selector_only_failures':bo,'mcnemar_exact_two_sided':float(binomtest(ao,n,.5).pvalue) if n else 1.}

def main():
 saved=json.load(open(HERE/'fast_flagged_logistic_replication_results.json'));models=saved['trained_models'];prepared=[];pre=[];start=time.perf_counter()
 for (basis,regime,model_i),(name,factors),seed in zip([t for t in TASKS for _ in PROFILES],[p for _ in TASKS for p in PROFILES],PREFLIGHT_SEEDS,strict=True):
  c,meta=build_profile(basis,regime,factors);nom=build_circuit(basis,regime,distance=3,rounds=5,gate_p=.003,measurement_p=.003,bias_ratio=10.);nc,np_=make_models(nom)
  if (c.num_qubits,c.num_detectors,c.num_observables)!=(26,40,1):raise RuntimeError('geometry mismatch')
  if abs(meta['mean_pair_rate']-.003)>1e-12:raise RuntimeError('mean rate mismatch')
  nd,no=clean(c).compile_detector_sampler(seed=1).sample(20,separate_observables=True)
  if nd.any() or no.any():raise RuntimeError('noiseless check failed')
  actual=make_matching(c);t=time.perf_counter();det,obs=c.compile_detector_sampler(seed=seed).sample(shots=PRE,separate_observables=True);st=time.perf_counter()-t
  cb=np.asarray(nc.decode_batch(det,enable_correlations=True),dtype=bool).reshape(PRE,-1);pb=np.asarray(np_.decode_batch(det,enable_correlations=False),dtype=bool).reshape(PRE,-1)
  cs=np.asarray([nc.decode(s,enable_correlations=True) for s in det[:20]],dtype=bool).reshape(20,-1);ps=np.asarray([np_.decode(s,enable_correlations=False) for s in det[:20]],dtype=bool).reshape(20,-1)
  if not np.array_equal(cb[:20],cs) or not np.array_equal(pb[:20],ps):raise RuntimeError('scalar/batch mismatch')
  x,flag=features(det,cb,pb)
  if x.shape[1]!=42:raise RuntimeError('feature dimension mismatch')
  row=models[model_i];coef=np.asarray(row['coefficients'],dtype=np.float64);bias=float(row['intercept'])
  pred=cb.copy()
  if flag.any():pred[flag]=(x[flag]@coef+bias>=0).reshape(-1,1)
  # Approximate runtime including the diagnostic graph pass.
  t=time.perf_counter();nc.decode_batch(det,enable_correlations=True);ct=time.perf_counter()-t
  t=time.perf_counter();np_.decode_batch(det,enable_correlations=False);pt=time.perf_counter()-t
  t=time.perf_counter();actual.decode_batch(det,enable_correlations=True);at=time.perf_counter()-t
  projected=(st+ct+pt+at)*SHOTS/PRE
  pre.append({'basis':basis,'regime':regime,'profile':name,'seed':seed,'flags':int(flag.sum()),'metadata':meta,'projected_seconds':projected})
  prepared.append((basis,regime,model_i,name,factors,c,nc,np_,actual,coef,bias))
 projection=sum(x['projected_seconds'] for x in pre)
 if projection>MAX_SECONDS:raise RuntimeError(f'projected runtime {projection:.1f}s exceeds cap')
 rows=[]
 for item,seed in zip(prepared,MAIN_SEEDS,strict=True):
  basis,regime,model_i,name,factors,c,nc,np_,actual,coef,bias=item
  det,obs=c.compile_detector_sampler(seed=seed).sample(shots=SHOTS,separate_observables=True)
  t=time.perf_counter();cp=np.asarray(nc.decode_batch(det,enable_correlations=True),dtype=bool).reshape(SHOTS,-1);ct=time.perf_counter()-t
  t=time.perf_counter();pp=np.asarray(np_.decode_batch(det,enable_correlations=False),dtype=bool).reshape(SHOTS,-1);pt=time.perf_counter()-t
  x,flag=features(det,cp,pp);pred=cp.copy();t=time.perf_counter()
  if flag.any():pred[flag]=(x[flag]@coef+bias>=0).reshape(-1,1)
  cl=time.perf_counter()-t
  t=time.perf_counter();ap=np.asarray(actual.decode_batch(det,enable_correlations=True),dtype=bool).reshape(SHOTS,-1);at=time.perf_counter()-t
  cf=np.any(cp!=obs,axis=1);sf=np.any(pred!=obs,axis=1);af=np.any(ap!=obs,axis=1)
  rows.append({'memory_basis':basis,'regime':regime,'profile':name,'seed':seed,'shots':SHOTS,'flags':int(flag.sum()),'failures':{'nominal_correlated':int(cf.sum()),'frozen_selector':int(sf.sum()),'actual_map_diagnostic':int(af.sum())},'ler':{'nominal_correlated':float(cf.mean()),'frozen_selector':float(sf.mean()),'actual_map_diagnostic':float(af.mean())},'wilson_95':{'nominal_correlated':wilson(int(cf.sum()),SHOTS),'frozen_selector':wilson(int(sf.sum()),SHOTS)},'paired':paired(cf,sf),'time_ratio':(ct+pt+cl)/ct})
 base=float(np.mean([r['ler']['nominal_correlated'] for r in rows]));cand=float(np.mean([r['ler']['frozen_selector'] for r in rows]));diag=float(np.mean([r['ler']['actual_map_diagnostic'] for r in rows]));red=1-cand/base
 per=[1-r['ler']['frozen_selector']/r['ler']['nominal_correlated'] for r in rows];tr=float(np.mean([r['time_ratio'] for r in rows]))
 out={'status':'fast_flagged_logistic_temporal_two_task','tasks':[{'memory_basis':x[0],'regime':x[1]} for x in TASKS],'conditions':rows,'preflight':pre,'macro_ler':{'nominal_correlated':base,'frozen_selector':cand,'actual_profile_matcher_diagnostic':diag},'macro_relative_reduction':red,'per_cell_relative_reductions':per,'mean_time_ratio':tr,'advancement_gate_passed':red>=.10 and min(per)>=-.05 and tr<2,'preflight_samples':4*PRE,'main_samples':4*SHOTS,'projected_seconds':projection,'elapsed_seconds':time.perf_counter()-start,'scope':'blockwise temporal pattern on Z-memory/X-bias and X-memory/Z-bias d3 using task-specific frozen selectors'}
 (HERE/'fast_flagged_logistic_temporal_two_task_results.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({'macro_ler':out['macro_ler'],'reduction':red,'per_cell':per,'time_ratio':tr,'gate':out['advancement_gate_passed'],'elapsed':out['elapsed_seconds']},indent=2))
if __name__=='__main__':main()
