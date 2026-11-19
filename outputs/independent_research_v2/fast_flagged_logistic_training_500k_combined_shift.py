"""Test half-budget selector training under combined measurement/bias shift."""
from __future__ import annotations
import json,math,time,sys,platform,resource,hashlib
from pathlib import Path
import numpy as np,pymatching,stim
from scipy.stats import binomtest
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(HERE));sys.path.insert(0,str(REPO/'outputs'/'phase2b_pauli_bias'))
from fast_flagged_logistic import CONDITIONS,features,fit_logistic,make_models,wilson
from noise_model import build_circuit
PRE_SEEDS=(2026122501,2026122502,2026122503,2026122504,2026122505,2026122506)
TRAIN_SEEDS=(2026122511,2026122512,2026122513,2026122514,2026122515,2026122516)
VALID_SEEDS=(2026122521,2026122522,2026122523,2026122524,2026122525,2026122526)
PRE=5_000;TRAIN=1_000_000;LOW=500_000;VALID=500_000;SHIFT_MEAS=.006;SHIFT_BIAS=5.;CAP=300.
def paired(a,b):
 d=b.astype(np.int8)-a.astype(np.int8);m=float(d.mean());se=float(d.std(ddof=1)/math.sqrt(len(d)));ao=int(np.count_nonzero(a&~b));bo=int(np.count_nonzero(b&~a));n=ao+bo
 return {'delta_candidate_minus_baseline':m,'normal_95_ci':[m-1.95996398454*se,m+1.95996398454*se],'baseline_only_failures':ao,'candidate_only_failures':bo,'mcnemar_exact_two_sided':float(binomtest(ao,n,.5).pvalue) if n else 1.}
def main():
 start=time.perf_counter();pre=[];prepared=[]
 for (basis,regime),seed in zip(CONDITIONS,PRE_SEEDS,strict=True):
  nom=build_circuit(basis,regime,gate_p=.003,measurement_p=.003,bias_ratio=10.);shift=build_circuit(basis,regime,gate_p=.003,measurement_p=SHIFT_MEAS,bias_ratio=SHIFT_BIAS)
  if (nom.num_qubits,nom.num_detectors,nom.num_observables)!=(26,40,1) or (shift.num_qubits,shift.num_detectors,shift.num_observables)!=(26,40,1):raise RuntimeError('geometry mismatch')
  mods=make_models(nom);clean=stim.Circuit()
  for ins in shift.flattened():
   if ins.name not in ('PAULI_CHANNEL_1','PAULI_CHANNEL_2','X_ERROR','Z_ERROR'):clean.append(ins.name,ins.targets_copy(),ins.gate_args_copy())
  nd,no=clean.compile_detector_sampler(seed=1).sample(20,separate_observables=True)
  if nd.any() or no.any():raise RuntimeError('shifted noiseless check failed')
  t=time.perf_counter();det,obs=shift.compile_detector_sampler(seed=seed).sample(shots=PRE,separate_observables=True);ss=time.perf_counter()-t
  t=time.perf_counter();cp=np.asarray(mods[0].decode_batch(det,enable_correlations=True),bool).reshape(PRE,-1);ct=time.perf_counter()-t
  t=time.perf_counter();pp=np.asarray(mods[1].decode_batch(det,enable_correlations=False),bool).reshape(PRE,-1);pt=time.perf_counter()-t
  x,flag=features(det,cp,pp)
  cs=np.asarray([mods[0].decode(v,enable_correlations=True) for v in det[:20]],bool).reshape(20,-1)
  if not np.array_equal(cs,cp[:20]) or x.shape[1]!=42:raise RuntimeError('shifted input decoder/feature preflight failed')
  projection=(ss+ct+pt)*(TRAIN+VALID)/PRE
  pre.append({'memory_basis':basis,'regime':regime,'seed':seed,'flags':int(flag.sum()),'sample_seconds':ss,'correlated_seconds':ct,'ordinary_seconds':pt,'projected_seconds':projection})
  prepared.append((nom,shift,mods))
 totalproj=sum(x['projected_seconds'] for x in pre)
 if totalproj>CAP:raise RuntimeError(f'projected runtime {totalproj:.1f}s exceeds cap')
 fitted=[];training=[]
 for ix,((basis,regime),(nom,shift,mods)) in enumerate(zip(CONDITIONS,prepared,strict=True)):
  det,obs=nom.compile_detector_sampler(seed=TRAIN_SEEDS[ix]).sample(shots=TRAIN,separate_observables=True)
  cp=np.asarray(mods[0].decode_batch(det,enable_correlations=True),bool).reshape(TRAIN,-1);pp=np.asarray(mods[1].decode_batch(det,enable_correlations=False),bool).reshape(TRAIN,-1)
  x,flag=features(det,cp,pp);y=obs.reshape(-1);lowmask=flag[:LOW];lowy=y[:LOW][lowmask]
  row={'memory_basis':basis,'regime':regime,'seed':TRAIN_SEEDS[ix],'flags_500k':int(lowmask.sum()),'classes_500k':{'logical0':int((lowy==0).sum()),'logical1':int((lowy==1).sum())},'flags_1m':int(flag.sum())}
  training.append(row)
  if row['flags_500k']<100 or min(row['classes_500k'].values())==0:raise RuntimeError('500k training readiness gate failed; validation not opened')
  model={}
  for label,n in [('500k',LOW),('1m',TRAIN)]:
   co,bi,info=fit_logistic(x[:n][flag[:n]],y[:n][flag[:n]]);model[label]={'coef':co,'bias':bi,'fit':info}
  fitted.append(model)
 rows=[]
 for ix,((basis,regime),(nom,shift,mods),model) in enumerate(zip(CONDITIONS,prepared,fitted,strict=True)):
  det,obs=shift.compile_detector_sampler(seed=VALID_SEEDS[ix]).sample(shots=VALID,separate_observables=True)
  t=time.perf_counter();cp=np.asarray(mods[0].decode_batch(det,enable_correlations=True),bool).reshape(VALID,-1);ct=time.perf_counter()-t
  t=time.perf_counter();pp=np.asarray(mods[1].decode_batch(det,enable_correlations=False),bool).reshape(VALID,-1);pt=time.perf_counter()-t
  actualdem=shift.detector_error_model(decompose_errors=True,approximate_disjoint_errors=.0018);actual=pymatching.Matching.from_detector_error_model(actualdem,enable_correlations=True)
  t=time.perf_counter();ap=np.asarray(actual.decode_batch(det,enable_correlations=True),bool).reshape(VALID,-1);at=time.perf_counter()-t
  x,flag=features(det,cp,pp);base=np.any(cp!=obs,axis=1);row={'memory_basis':basis,'regime':regime,'seed':VALID_SEEDS[ix],'shots':VALID,'flags':int(flag.sum()),'failures':{'nominal_correlated':int(base.sum()),'ordinary':int(np.any(pp!=obs,axis=1).sum()),'actual_shift_matcher_diagnostic':int(np.any(ap!=obs,axis=1).sum())},'ler':{'nominal_correlated':float(base.mean()),'actual_shift_matcher_diagnostic':float(np.any(ap!=obs,axis=1).mean())},'models':{}}
  for label in ('500k','1m'):
   pred=cp.copy();t=time.perf_counter()
   if flag.any():pred[flag]=(x[flag]@model[label]['coef']+model[label]['bias']>=0).reshape(-1,1)
   cls=time.perf_counter()-t;fail=np.any(pred!=obs,axis=1)
   row['models'][label]={'failures':int(fail.sum()),'ler':float(fail.mean()),'wilson_95':wilson(int(fail.sum()),VALID),'relative_reduction':1-fail.mean()/base.mean(),'paired_vs_nominal_correlated':paired(base,fail),'time_ratio':(ct+pt+cls)/ct,'fit':model[label]['fit']}
  rows.append(row)
 base=float(np.mean([r['ler']['nominal_correlated'] for r in rows]));g500=base-float(np.mean([r['models']['500k']['ler'] for r in rows]));g1m=base-float(np.mean([r['models']['1m']['ler'] for r in rows]));ret=g500/g1m if g1m>0 else None
 red500=1-(base-g500)/base;red1m=1-(base-g1m)/base
 per={label:[1-r['models'][label]['ler']/r['ler']['nominal_correlated'] for r in rows] for label in ('500k','1m')}
 tr={label:float(np.mean([r['models'][label]['time_ratio'] for r in rows])) for label in ('500k','1m')}
 passed=bool(ret is not None and ret>=.8 and red500>=.10 and red1m>=.10 and min(per['500k'])>=-.05 and min(per['1m'])>=-.05 and tr['500k']<2 and tr['1m']<2)
 out={'status':'completed','shift':{'gate_p':.003,'measurement_p':SHIFT_MEAS,'nominal_bias_ratio':10.,'physical_bias_ratio':SHIFT_BIAS},'preflight':pre,'training':training,'conditions':rows,'macro_ler':{'nominal_correlated':base,'500k_model':base-g500,'1m_model':base-g1m},'macro_relative_reduction':{'500k_model':red500,'1m_model':red1m},'absolute_gain_retention_500k_vs_1m':ret,'per_condition_relative_reductions':per,'mean_inference_time_ratio':tr,'advancement_gate_passed':passed,'unique_preflight_samples':6*PRE,'training_samples':6*TRAIN,'validation_samples':6*VALID,'projected_main_seconds':totalproj,'elapsed_seconds':time.perf_counter()-start,'peak_rss_kib':int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),'software_versions':{'python':platform.python_version(),'numpy':np.__version__,'stim':stim.__version__,'pymatching':pymatching.__version__},'scope':'500k vs 1M nominal training fit applied frozen to combined measurement/bias shift; development only'}
 (HERE/'fast_flagged_logistic_training_500k_combined_shift_results.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'macro_ler':out['macro_ler'],'reductions':out['macro_relative_reduction'],'retention':ret,'per_cell':per,'time_ratio':tr,'gate':passed,'elapsed':out['elapsed_seconds']},indent=2))
if __name__=='__main__':main()
