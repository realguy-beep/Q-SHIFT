"""Nested 100k vs 1M training-shot screen for the d3 flagged selector."""
from __future__ import annotations
import json, math, sys, time, platform, hashlib, resource
from pathlib import Path
import numpy as np
import stim
from scipy.stats import binomtest
HERE=Path(__file__).resolve().parent; REPO=HERE.parents[1]
sys.path.insert(0,str(HERE)); sys.path.insert(0,str(REPO/"outputs"/"phase2b_pauli_bias"))
from fast_flagged_logistic import CONDITIONS, features, fit_logistic, make_models, wilson
from noise_model import build_circuit
PRE_SEEDS=(2026121801,2026121802,2026121803,2026121804,2026121805,2026121806)
TRAIN_SEEDS=(2026121811,2026121812,2026121813,2026121814,2026121815,2026121816)
VALID_SEEDS=(2026121821,2026121822,2026121823,2026121824,2026121825,2026121826)
PRE=5_000; TRAIN=1_000_000; LOW=100_000; VALID=500_000; CAP=300.

def paired(a,b):
 d=b.astype(np.int8)-a.astype(np.int8);m=float(d.mean());se=float(d.std(ddof=1)/math.sqrt(len(d)))
 ao=int(np.count_nonzero(a&~b));bo=int(np.count_nonzero(b&~a));n=ao+bo
 return {'delta_selector_minus_correlated':m,'normal_95_ci':[m-1.95996398454*se,m+1.95996398454*se],
         'correlated_only_failures':ao,'selector_only_failures':bo,
         'mcnemar_exact_two_sided':float(binomtest(ao,n,.5).pvalue) if n else 1.}

def main():
 start=time.perf_counter();prepared=[];pre=[]
 for (basis,regime),seed in zip(CONDITIONS,PRE_SEEDS,strict=True):
  c=build_circuit(basis,regime);mods=make_models(c)
  if (c.num_qubits,c.num_detectors,c.num_observables)!=(26,40,1):raise RuntimeError('geometry mismatch')
  clean=stim.Circuit()
  for ins in c.flattened():
   if ins.name not in ('PAULI_CHANNEL_1','PAULI_CHANNEL_2','X_ERROR','Z_ERROR'):clean.append(ins.name,ins.targets_copy(),ins.gate_args_copy())
  nd,no=clean.compile_detector_sampler(seed=1).sample(20,separate_observables=True)
  if nd.any() or no.any():raise RuntimeError('noiseless check failed')
  t=time.perf_counter();det,obs=c.compile_detector_sampler(seed=seed).sample(shots=PRE,separate_observables=True);sample_s=time.perf_counter()-t
  t=time.perf_counter();cp=np.asarray(mods[0].decode_batch(det,enable_correlations=True),dtype=bool).reshape(PRE,-1);corr_s=time.perf_counter()-t
  t=time.perf_counter();pp=np.asarray(mods[1].decode_batch(det,enable_correlations=False),dtype=bool).reshape(PRE,-1);plain_s=time.perf_counter()-t
  if cp.shape!=(PRE,1) or pp.shape!=(PRE,1):raise RuntimeError('decoder shape mismatch')
  x,flag=features(det,cp,pp)
  if x.shape[1]!=42:raise RuntimeError('feature geometry mismatch')
  pre.append({'basis':basis,'regime':regime,'seed':seed,'shots':PRE,'flags':int(flag.sum()),'sample_seconds':sample_s,'correlated_seconds':corr_s,'ordinary_seconds':plain_s})
  prepared.append((c,mods))
 projection=sum((r['sample_seconds']+r['correlated_seconds']+r['ordinary_seconds'])*(TRAIN+VALID)/PRE for r in pre)
 if projection>CAP:raise RuntimeError(f'projected matching runtime {projection:.1f}s exceeds cap')
 conditions=[];fit_seconds=0.;train_samples=0;train_rows=[]
 for ix,((basis,regime),(c,mods)) in enumerate(zip(CONDITIONS,prepared,strict=True)):
  det,obs=c.compile_detector_sampler(seed=TRAIN_SEEDS[ix]).sample(shots=TRAIN,separate_observables=True)
  cp=np.asarray(mods[0].decode_batch(det,enable_correlations=True),dtype=bool).reshape(TRAIN,-1)
  pp=np.asarray(mods[1].decode_batch(det,enable_correlations=False),dtype=bool).reshape(TRAIN,-1)
  x,flag=features(det,cp,pp);y=obs.reshape(-1)
  low_flag=flag[:LOW];low_y=y[:LOW][low_flag]
  train_rows.append({'basis':basis,'regime':regime,'flags':int(low_flag.sum()),'classes':{'logical0':int((low_y==0).sum()),'logical1':int((low_y==1).sum())}})
  if int(low_flag.sum())<100 or min(train_rows[-1]['classes'].values())==0:raise RuntimeError('low-budget trainability stop criterion failed; validation not launched')
  fitrows={}
  for label,n in [('100k',LOW),('1m',TRAIN)]:
   t=time.perf_counter();coef,bias,info=fit_logistic(x[:n][flag[:n]],y[:n][flag[:n]]);fs=time.perf_counter()-t;fit_seconds+=fs
   fitrows[label]={'coefficients':coef,'intercept':bias,'fit':info,'fit_seconds':fs}
  vd,vo=c.compile_detector_sampler(seed=VALID_SEEDS[ix]).sample(shots=VALID,separate_observables=True)
  vc=np.asarray(mods[0].decode_batch(vd,enable_correlations=True),dtype=bool).reshape(VALID,-1)
  vp=np.asarray(mods[1].decode_batch(vd,enable_correlations=False),dtype=bool).reshape(VALID,-1)
  vx,vflag=features(vd,vc,vp);base=np.any(vc!=vo,axis=1);ordinary=np.any(vp!=vo,axis=1)
  row={'memory_basis':basis,'regime':regime,'validation_seed':VALID_SEEDS[ix],'shots':VALID,'flagged':int(vflag.sum()),'failures':{'correlated':int(base.sum()),'ordinary':int(ordinary.sum())},'ler':{'correlated':float(base.mean()),'ordinary':float(ordinary.mean())},'wilson_95':{'correlated':wilson(int(base.sum()),VALID)},'models':{}}
  for label,fit in fitrows.items():
   t=time.perf_counter();pred=vc.copy()
   if vflag.any():pred[vflag]=(vx[vflag]@fit['coefficients']+fit['intercept']>=0).reshape(-1,1)
   policy_s=time.perf_counter()-t;fail=np.any(pred!=vo,axis=1);corr_only=int(np.count_nonzero(base&~fail));sel_only=int(np.count_nonzero(fail&~base))
   # Includes both matching passes and classifier cost, matching established reporting convention.
   row['models'][label]={'failures':int(fail.sum()),'ler':float(fail.mean()),'wilson_95':wilson(int(fail.sum()),VALID),'paired':paired(base,fail),'relative_reduction':1-fail.mean()/base.mean(),'classifier_seconds':policy_s,'fit_seconds':fit['fit_seconds'],'fit':fit['fit']}
  # Time ratio measured on a fresh validation batch by all policies below.
  t=time.perf_counter();mods[0].decode_batch(vd,enable_correlations=True);ct=time.perf_counter()-t
  t=time.perf_counter();mods[1].decode_batch(vd,enable_correlations=False);pt=time.perf_counter()-t
  for label,fit in fitrows.items():
   t=time.perf_counter()
   if vflag.any():vx[vflag]@fit['coefficients']+fit['intercept']
   row['models'][label]['time_ratio']=(ct+pt+(time.perf_counter()-t))/ct
  conditions.append(row);train_samples+=TRAIN
 def macro(label):
  return float(np.mean([r['models'][label]['ler'] for r in conditions]))
 base=float(np.mean([r['ler']['correlated'] for r in conditions]));low=macro('100k');full=macro('1m')
 lowgain=base-low;fullgain=base-full;retention=lowgain/fullgain if fullgain>0 else None
 per_low=[r['models']['100k']['relative_reduction'] for r in conditions]
 time_ratio=float(np.mean([r['models']['100k']['time_ratio'] for r in conditions]))
 gate=bool(retention is not None and retention>=.8 and 1-low/base>=.10 and min(per_low)>=-.05 and time_ratio<2)
 result={'status':'fast_flagged_logistic_training_efficiency','conditions':conditions,'preflight':pre,'low_budget_trainability':train_rows,'macro_ler':{'correlated':base,'100k_model':low,'1m_model':full},'relative_reduction':{'100k_model':1-low/base,'1m_model':1-full/base},'absolute_gain_retention_100k_vs_1m':retention,'per_condition_100k_relative_reductions':per_low,'mean_100k_inference_time_ratio':time_ratio,'advancement_gate_passed':gate,'preflight_samples':6*PRE,'unique_training_samples':6*TRAIN,'validation_samples':6*VALID,'projected_matching_seconds':projection,'elapsed_seconds':time.perf_counter()-start,'peak_rss_kib':int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),'software_versions':{'python':platform.python_version(),'numpy':np.__version__},'scope':'nested 100k vs 1M labeled training shots per d3 condition; shared independent validation; development only'}
 out=HERE/'fast_flagged_logistic_training_efficiency_results.json';out.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'macro_ler':result['macro_ler'],'relative_reduction':result['relative_reduction'],'gain_retention':retention,'per_condition_100k':per_low,'time_ratio':time_ratio,'gate':gate,'elapsed':result['elapsed_seconds']},indent=2))
if __name__=='__main__':main()
