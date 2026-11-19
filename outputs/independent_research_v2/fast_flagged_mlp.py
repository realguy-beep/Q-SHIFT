"""Fixed small tanh MLP vs logistic on the flagged d3 subset."""
from __future__ import annotations
import json,math,time,sys,platform,resource,hashlib
from pathlib import Path
import numpy as np,stim,pymatching
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import binomtest
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(HERE));sys.path.insert(0,str(REPO/'outputs'/'phase2b_pauli_bias'))
from fast_flagged_logistic import CONDITIONS,features,fit_logistic,make_models,wilson
from noise_model import build_circuit
PRE_SEEDS=(2026122401,2026122402,2026122403,2026122404,2026122405,2026122406)
TRAIN_SEEDS=(2026122411,2026122412,2026122413,2026122414,2026122415,2026122416)
VALID_SEEDS=(2026122421,2026122422,2026122423,2026122424,2026122425,2026122426)
PRE=5_000;TRAIN=500_000;VALID=500_000;HIDDEN=8;CAP=300.
def pair(a,b):
 d=b.astype(np.int8)-a.astype(np.int8);m=float(d.mean());se=float(d.std(ddof=1)/math.sqrt(len(d)));ao=int(np.count_nonzero(a&~b));bo=int(np.count_nonzero(b&~a));n=ao+bo
 return {'delta_candidate_minus_reference':m,'normal_95_ci':[m-1.95996398454*se,m+1.95996398454*se],'reference_only_failures':ao,'candidate_only_failures':bo,'mcnemar_exact_two_sided':float(binomtest(ao,n,.5).pvalue) if n else 1.}
def fit_mlp(x,y,seed):
 y=np.asarray(y,float).reshape(-1);n,d=x.shape
 mu=x.mean(axis=0);scale=x.std(axis=0);scale=np.where(scale>1e-8,scale,1.)
 z=(x-mu)/scale
 h=HIDDEN;rng=np.random.default_rng(seed)
 w1=rng.normal(0,np.sqrt(2/(d+h)),(d,h));b1=np.zeros(h);w2=rng.normal(0,np.sqrt(2/(h+1)),h);b2=0.
 theta0=np.concatenate([w1.ravel(),b1,w2,[b2]])
 def objective(theta):
  k=d*h;w1=theta[:k].reshape(d,h);b1=theta[k:k+h];w2=theta[k+h:k+h+h];b2=theta[-1]
  u=z@w1+b1;hidden=np.tanh(u);logits=hidden@w2+b2
  loss=float(np.logaddexp(0,logits).sum()-np.dot(y,logits)+.5*(np.sum(w1*w1)+np.dot(w2,w2)))
  e=expit(logits)-y;gw2=hidden.T@e+w2;gb2=e.sum();dh=e[:,None]*w2[None,:];du=dh*(1-hidden*hidden);gw1=z.T@du+w1;gb1=du.sum(axis=0)
  grad=np.concatenate([gw1.ravel(),gb1,gw2,[gb2]])
  return loss,grad
 res=minimize(objective,theta0,jac=True,method='L-BFGS-B',options={'maxiter':500,'ftol':1e-9,'maxls':30})
 if not res.success or not np.isfinite(res.x).all():raise RuntimeError(f'MLP fit failed: {res.message}')
 return {'mean':mu,'scale':scale,'theta':res.x,'fit':{'iterations':int(res.nit),'objective':float(res.fun),'message':str(res.message),'training_flag_rows':n,'classes':{'logical0':int((y==0).sum()),'logical1':int((y==1).sum())}}}
def predict_mlp(x,model):
 x=(x-model['mean'])/model['scale'];d=x.shape[1];theta=model['theta'];h=HIDDEN;k=d*h
 w1=theta[:k].reshape(d,h);b1=theta[k:k+h];w2=theta[k+h:k+h+h];b2=theta[-1]
 return np.tanh(x@w1+b1)@w2+b2
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
  t=time.perf_counter();det,obs=c.compile_detector_sampler(seed=seed).sample(shots=PRE,separate_observables=True);ss=time.perf_counter()-t
  t=time.perf_counter();cp=np.asarray(mods[0].decode_batch(det,enable_correlations=True),bool).reshape(PRE,-1);ct=time.perf_counter()-t
  t=time.perf_counter();pp=np.asarray(mods[1].decode_batch(det,enable_correlations=False),bool).reshape(PRE,-1);pt=time.perf_counter()-t
  x,flag=features(det,cp,pp)
  if cp.shape!=(PRE,1) or x.shape[1]!=42:raise RuntimeError('preflight shape mismatch')
  pre.append({'memory_basis':basis,'regime':regime,'seed':seed,'flags':int(flag.sum()),'sample_seconds':ss,'correlated_seconds':ct,'ordinary_seconds':pt})
  prepared.append((c,mods))
 projection=sum((x['sample_seconds']+x['correlated_seconds']+x['ordinary_seconds'])*(TRAIN+VALID)/PRE for x in pre)
 if projection>CAP:raise RuntimeError(f'projected sample/matching runtime {projection:.1f}s exceeds cap')
 fitted=[];training=[]
 # Finish all train-readiness checks and fits before opening any validation data.
 for ix,((basis,regime),(c,mods)) in enumerate(zip(CONDITIONS,prepared,strict=True)):
  det,obs=c.compile_detector_sampler(seed=TRAIN_SEEDS[ix]).sample(shots=TRAIN,separate_observables=True)
  cp=np.asarray(mods[0].decode_batch(det,enable_correlations=True),bool).reshape(TRAIN,-1)
  pp=np.asarray(mods[1].decode_batch(det,enable_correlations=False),bool).reshape(TRAIN,-1)
  x,flag=features(det,cp,pp);y=obs.reshape(-1)[flag]
  row={'memory_basis':basis,'regime':regime,'seed':TRAIN_SEEDS[ix],'flags':int(flag.sum()),'classes':{'logical0':int((y==0).sum()),'logical1':int((y==1).sum())}}
  training.append(row)
  if row['flags']<100 or min(row['classes'].values())==0:raise RuntimeError('training readiness gate failed; validation not opened')
  lc,lb,li=fit_logistic(x[flag],y);t=time.perf_counter();mlp=fit_mlp(x[flag],y,2026122431+ix);mlp['fit_seconds']=time.perf_counter()-t
  fitted.append({'logistic_coef':lc,'logistic_bias':lb,'logistic_fit':li,'mlp':mlp})
 rows=[];macro_pair_deltas=[]
 for ix,((basis,regime),(c,mods),model) in enumerate(zip(CONDITIONS,prepared,fitted,strict=True)):
  det,obs=c.compile_detector_sampler(seed=VALID_SEEDS[ix]).sample(shots=VALID,separate_observables=True)
  t=time.perf_counter();cp=np.asarray(mods[0].decode_batch(det,enable_correlations=True),bool).reshape(VALID,-1);ct=time.perf_counter()-t
  t=time.perf_counter();pp=np.asarray(mods[1].decode_batch(det,enable_correlations=False),bool).reshape(VALID,-1);pt=time.perf_counter()-t
  x,flag=features(det,cp,pp);base=np.any(cp!=obs,axis=1);ordinary=np.any(pp!=obs,axis=1)
  row={'memory_basis':basis,'regime':regime,'seed':VALID_SEEDS[ix],'shots':VALID,'flags':int(flag.sum()),'failures':{'correlated':int(base.sum()),'ordinary':int(ordinary.sum())},'ler':{'correlated':float(base.mean()),'ordinary':float(ordinary.mean())},'models':{}}
  fail_vectors={}
  for name in ('logistic','mlp'):
   pred=cp.copy();t=time.perf_counter()
   if flag.any():
    if name=='logistic':logit=x[flag]@model['logistic_coef']+model['logistic_bias']
    else:logit=predict_mlp(x[flag],model['mlp'])
    pred[flag]=(logit>=0).reshape(-1,1)
   cls=time.perf_counter()-t;fail=np.any(pred!=obs,axis=1)
   fail_vectors[name]=fail
   row['models'][name]={'failures':int(fail.sum()),'ler':float(fail.mean()),'wilson_95':wilson(int(fail.sum()),VALID),'relative_reduction_vs_correlated':1-fail.mean()/base.mean(),'paired_vs_correlated':pair(base,fail),'classifier_seconds':cls,'time_ratio':(ct+pt+cls)/ct}
  row['models']['mlp']['paired_vs_logistic']=pair(fail_vectors['logistic'],fail_vectors['mlp'])
  macro_pair_deltas.append(fail_vectors['mlp'].astype(np.int8)-fail_vectors['logistic'].astype(np.int8))
  rows.append(row)
 base=float(np.mean([r['ler']['correlated'] for r in rows]));lm=float(np.mean([r['models']['logistic']['ler'] for r in rows]));mm=float(np.mean([r['models']['mlp']['ler'] for r in rows]))
 all_delta=np.concatenate(macro_pair_deltas);macro_delta=float(all_delta.mean());macro_se=float(all_delta.std(ddof=1)/math.sqrt(len(all_delta)))
 macro_ci=[macro_delta-1.95996398454*macro_se,macro_delta+1.95996398454*macro_se]
 ret=1-mm/lm if lm>0 else None
 per=[r['models']['mlp']['relative_reduction_vs_correlated'] for r in rows];tr=float(np.mean([r['models']['mlp']['time_ratio'] for r in rows]))
 gain_vs_logistic=1-mm/lm if lm>0 else None
 passed=bool(gain_vs_logistic is not None and gain_vs_logistic>=.02 and macro_ci[1]<0 and mm<lm and 1-mm/base>=.10 and min(per)>=-.05 and tr<2)
 result={'status':'completed','preflight':pre,'training':training,'conditions':rows,'macro_ler':{'correlated':base,'logistic':lm,'mlp':mm},'mlp_relative_reduction_vs_correlated':1-mm/base,'mlp_relative_reduction_vs_logistic':gain_vs_logistic,'macro_absolute_delta_mlp_minus_logistic':macro_delta,'macro_paired_95_ci_mlp_minus_logistic':macro_ci,'per_condition_mlp_reductions_vs_correlated':per,'mean_mlp_inference_time_ratio':tr,'advancement_gate_passed':passed,'unique_preflight_samples':6*PRE,'training_samples':6*TRAIN,'validation_samples':6*VALID,'projected_sampling_matching_seconds':projection,'elapsed_seconds':time.perf_counter()-start,'peak_rss_kib':int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),'software_versions':{'python':platform.python_version(),'numpy':np.__version__,'scipy':'1.18.1','stim':stim.__version__,'pymatching':pymatching.__version__},'scope':'fixed 8-unit tanh MLP vs logistic on flagged d3 syndromes; development only'}
 (HERE/'fast_flagged_mlp_results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'macro_ler':result['macro_ler'],'mlp_gain_vs_logistic':gain_vs_logistic,'per_cell_vs_baseline':per,'time_ratio':tr,'gate':passed,'elapsed':result['elapsed_seconds']},indent=2))
if __name__=='__main__':main()
