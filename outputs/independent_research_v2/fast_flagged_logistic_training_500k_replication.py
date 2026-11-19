"""Prospective nested 500k vs 1M training budget for the d3 flagged selector."""
from __future__ import annotations
import json,math,sys,time,platform,resource,hashlib
from pathlib import Path
import numpy as np,stim,pymatching
from scipy.stats import binomtest
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(HERE));sys.path.insert(0,str(REPO/'outputs'/'phase2b_pauli_bias'))
from fast_flagged_logistic import CONDITIONS,features,fit_logistic,make_models,wilson
from noise_model import build_circuit
PRE_SEEDS=(2026122001,2026122002,2026122003,2026122004,2026122005,2026122006)
TRAIN_SEEDS=(2026122011,2026122012,2026122013,2026122014,2026122015,2026122016)
VALID_SEEDS=(2026122021,2026122022,2026122023,2026122024,2026122025,2026122026)
PRE=5_000;TRAIN=1_000_000;LOW=500_000;VALID=500_000;CAP=300.
def paired(a,b):
 d=b.astype(np.int8)-a.astype(np.int8);m=float(d.mean());se=float(d.std(ddof=1)/math.sqrt(len(d)));ao=int(np.count_nonzero(a&~b));bo=int(np.count_nonzero(b&~a));n=ao+bo
 return {'delta_selector_minus_correlated':m,'normal_95_ci':[m-1.95996398454*se,m+1.95996398454*se],'correlated_only_failures':ao,'selector_only_failures':bo,'mcnemar_exact_two_sided':float(binomtest(ao,n,.5).pvalue) if n else 1.}
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
  t=time.perf_counter();d,o=c.compile_detector_sampler(seed=seed).sample(shots=PRE,separate_observables=True);sample_s=time.perf_counter()-t
  t=time.perf_counter();cp=np.asarray(mods[0].decode_batch(d,enable_correlations=True),bool).reshape(PRE,-1);corr_s=time.perf_counter()-t
  t=time.perf_counter();pp=np.asarray(mods[1].decode_batch(d,enable_correlations=False),bool).reshape(PRE,-1);plain_s=time.perf_counter()-t
  x,flag=features(d,cp,pp)
  if cp.shape!=(PRE,1) or pp.shape!=(PRE,1) or x.shape[1]!=42:raise RuntimeError('preflight shape mismatch')
  pre.append({'basis':basis,'regime':regime,'seed':seed,'flags':int(flag.sum()),'sample_seconds':sample_s,'correlated_seconds':corr_s,'ordinary_seconds':plain_s})
  prepared.append((c,mods))
 projection=sum((r['sample_seconds']+r['correlated_seconds']+r['ordinary_seconds'])*(TRAIN+VALID)/PRE for r in pre)
 if projection>CAP:raise RuntimeError(f'projected sampling/matching runtime {projection:.1f}s exceeds cap')
 models=[];training=[];fit_seconds=0.
 for ix,((basis,regime),(c,mods)) in enumerate(zip(CONDITIONS,prepared,strict=True)):
  d,o=c.compile_detector_sampler(seed=TRAIN_SEEDS[ix]).sample(shots=TRAIN,separate_observables=True)
  cp=np.asarray(mods[0].decode_batch(d,enable_correlations=True),bool).reshape(TRAIN,-1)
  pp=np.asarray(mods[1].decode_batch(d,enable_correlations=False),bool).reshape(TRAIN,-1)
  x,flag=features(d,cp,pp);y=o.reshape(-1);lowmask=flag[:LOW];lowy=y[:LOW][lowmask]
  row={'memory_basis':basis,'regime':regime,'seed':TRAIN_SEEDS[ix],'low_budget_flags':int(lowmask.sum()),'low_budget_classes':{'logical0':int((lowy==0).sum()),'logical1':int((lowy==1).sum())},'full_budget_flags':int(flag.sum())}
  training.append(row)
  if row['low_budget_flags']<100 or min(row['low_budget_classes'].values())==0:
   out={'status':'stopped_at_training_readiness_gate','training':training,'preflight':pre,'stop_reason':row,'unique_preflight_samples':6*PRE,'unique_training_samples':(ix+1)*TRAIN,'validation_samples':0,'projected_seconds':projection,'elapsed_seconds':time.perf_counter()-start,'scope':'500k prefix training-feasibility screen; no validation opened'}
   (HERE/'fast_flagged_logistic_training_500k_replication_results.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));return
  fitrow={}
  for label,n in [('500k',LOW),('1m',TRAIN)]:
   t=time.perf_counter();coef,bias,info=fit_logistic(x[:n][flag[:n]],y[:n][flag[:n]]);dt=time.perf_counter()-t;fit_seconds+=dt
   fitrow[label]={'coef':coef,'bias':bias,'info':info,'fit_seconds':dt}
  models.append(fitrow)
 # Validation is opened only after all six prefix checks and model fits pass.
 rows=[]
 for ix,((basis,regime),(c,mods),fitrow) in enumerate(zip(CONDITIONS,prepared,models,strict=True)):
  d,o=c.compile_detector_sampler(seed=VALID_SEEDS[ix]).sample(shots=VALID,separate_observables=True)
  t=time.perf_counter();corr=np.asarray(mods[0].decode_batch(d,enable_correlations=True),bool).reshape(VALID,-1);ct=time.perf_counter()-t
  t=time.perf_counter();ordinary=np.asarray(mods[1].decode_batch(d,enable_correlations=False),bool).reshape(VALID,-1);pt=time.perf_counter()-t
  x,flag=features(d,corr,ordinary);obs=o.reshape(-1);base=np.any(corr!=o,axis=1)
  row={'memory_basis':basis,'regime':regime,'seed':VALID_SEEDS[ix],'shots':VALID,'flags':int(flag.sum()),'correlated_failures':int(base.sum()),'models':{}}
  for label,fit in fitrow.items():
   pred=corr.copy();t=time.perf_counter()
   if flag.any():pred[flag]=(x[flag]@fit['coef']+fit['bias']>=0).reshape(-1,1)
   cls=time.perf_counter()-t;fail=np.any(pred!=o,axis=1)
   row['models'][label]={'failures':int(fail.sum()),'ler':float(fail.mean()),'wilson_95':wilson(int(fail.sum()),VALID),'relative_reduction':1-fail.mean()/base.mean(),'paired':paired(base,fail),'fit_seconds':fit['fit_seconds'],'classifier_seconds':cls,'time_ratio':(ct+pt+cls)/ct}
  row.update({'correlated_ler':float(base.mean()),'correlated_wilson_95':wilson(int(base.sum()),VALID)})
  rows.append(row)
 macro=lambda label:float(np.mean([r['models'][label]['ler'] for r in rows]))
 base=float(np.mean([r['correlated_ler'] for r in rows]));low=macro('500k');full=macro('1m');ret=((base-low)/(base-full)) if base>full else None
 per=[r['models']['500k']['relative_reduction'] for r in rows];tr=float(np.mean([r['models']['500k']['time_ratio'] for r in rows]))
 passed=bool(ret is not None and ret>=.8 and 1-low/base>=.10 and min(per)>=-.05 and tr<2)
 result={'status':'completed','preflight':pre,'training':training,'conditions':rows,'macro_ler':{'correlated':base,'500k_model':low,'1m_model':full},'relative_reduction':{'500k_model':1-low/base,'1m_model':1-full/base},'absolute_gain_retention_500k_vs_1m':ret,'per_condition_500k_reductions':per,'mean_500k_inference_time_ratio':tr,'advancement_gate_passed':passed,'unique_preflight_samples':6*PRE,'unique_training_samples':6*TRAIN,'validation_samples':6*VALID,'projected_sampling_matching_seconds':projection,'fit_seconds':fit_seconds,'elapsed_seconds':time.perf_counter()-start,'peak_rss_kib':int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),'software_versions':{'python':platform.python_version(),'numpy':np.__version__,'scipy':'1.18.1','stim':stim.__version__,'pymatching':pymatching.__version__},'scope':'independent fresh-seed replication of nested 500k vs 1M training prefix; development only'}
 (HERE/'fast_flagged_logistic_training_500k_replication_results.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'macro_ler':result['macro_ler'],'reductions':result['relative_reduction'],'retention':ret,'per_cell':per,'time_ratio':tr,'gate':passed,'elapsed':result['elapsed_seconds']},indent=2))
if __name__=='__main__':main()
