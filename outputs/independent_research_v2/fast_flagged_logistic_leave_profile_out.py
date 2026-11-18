"""Leave-one-regime-out transfer of the shared relative-choice classifier."""
from __future__ import annotations
import json,math,sys,time
from pathlib import Path
import numpy as np
import pymatching,stim
from scipy.stats import binomtest
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/"outputs"/"phase2b_pauli_bias"))
from noise_model import MEMORY_BASES,REGIMES,build_circuit
from fast_flagged_logistic import features,fit_logistic,wilson,DEM_THRESHOLD,make_models
CONDITIONS=tuple((b,r) for b in MEMORY_BASES for r in REGIMES)
FOLDS=REGIMES
PREFLIGHT_SEEDS=(2026118941,2026118942,2026118943,2026118944,2026118945,2026118946)
FOLD_TRAIN_SEEDS=((2026118901,2026118902,2026118903,2026118904),(2026118911,2026118912,2026118913,2026118914),(2026118921,2026118922,2026118923,2026118924))
VALIDATION_SEEDS=(2026118931,2026118932,2026118933,2026118934,2026118935,2026118936)
PREFLIGHT_SHOTS=10_000;SHOTS=1_000_000;MAX_SECONDS=300.

def paired(a,b):
 d=b.astype(np.int8)-a.astype(np.int8);delta=float(d.mean());se=float(d.std(ddof=1)/math.sqrt(len(d)))
 ao=int(np.count_nonzero(a&~b));bo=int(np.count_nonzero(b&~a));n=ao+bo
 return {"delta_second_minus_first":delta,"normal_95_ci":[delta-1.95996398454*se,delta+1.95996398454*se],"first_only_failures":ao,"second_only_failures":bo,"mcnemar_exact_two_sided":float(binomtest(ao,n,.5).pvalue) if n else 1.}

def main():
 start=time.perf_counter();pre=[];prepared={}
 for (basis,regime),seed in zip(CONDITIONS,PREFLIGHT_SEEDS,strict=True):
  c=build_circuit(basis,regime);m=make_models(c)
  if (c.num_qubits,c.num_detectors,c.num_observables)!=(26,40,1):raise RuntimeError("geometry mismatch")
  clean=stim.Circuit()
  for ins in c.flattened():
   if ins.name not in ("PAULI_CHANNEL_1","PAULI_CHANNEL_2","X_ERROR","Z_ERROR"):clean.append(ins.name,ins.targets_copy(),ins.gate_args_copy())
  nd,no=clean.compile_detector_sampler(seed=1).sample(20,separate_observables=True)
  if nd.any() or no.any():raise RuntimeError("noiseless check failed")
  t=time.perf_counter();det,obs=c.compile_detector_sampler(seed=seed).sample(shots=PREFLIGHT_SHOTS,separate_observables=True);st=time.perf_counter()-t
  t=time.perf_counter();cp=np.asarray(m[0].decode_batch(det,enable_correlations=True),dtype=bool).reshape(PREFLIGHT_SHOTS,-1);ct=time.perf_counter()-t
  t=time.perf_counter();pp=np.asarray(m[1].decode_batch(det,enable_correlations=False),dtype=bool).reshape(PREFLIGHT_SHOTS,-1);pt=time.perf_counter()-t
  cs=np.asarray([m[0].decode(s,enable_correlations=True) for s in det[:20]],dtype=bool).reshape(20,-1)
  ps=np.asarray([m[1].decode(s,enable_correlations=False) for s in det[:20]],dtype=bool).reshape(20,-1)
  if not np.array_equal(cp[:20],cs) or not np.array_equal(pp[:20],ps):raise RuntimeError("scalar/batch mismatch")
  _,flag=features(det,cp,pp)
  pre.append({"memory_basis":basis,"regime":regime,"seed":seed,"shots":PREFLIGHT_SHOTS,"flags":int(flag.sum()),"sample_seconds":st,"correlated_seconds":ct,"ordinary_seconds":pt})
  prepared[(basis,regime)]=(c,m)
 projection=sum((r['sample_seconds']+r['correlated_seconds']+r['ordinary_seconds'])*3*SHOTS/PREFLIGHT_SHOTS for r in pre)
 if projection>MAX_SECONDS:raise RuntimeError(f"projected runtime {projection:.1f}s exceeds cap")
 prior=json.load(open(HERE/'fast_flagged_logistic_relative_choice_replication_results.json'))['pooled_training']
 prior_coef=np.asarray(prior['coefficients'],dtype=np.float64);prior_bias=prior['intercept']
 absprior=json.load(open(HERE/'fast_flagged_logistic_shared_selector_replication_results.json'))['pooled_training']
 abscoef=np.asarray(absprior['coefficients'],dtype=np.float64);absbias=absprior['intercept']
 spec=json.load(open(HERE/'fast_flagged_logistic_replication_results.json'))['trained_models']
 fold_rows=[];all_training=[];all_validation=[];total_train_time=0.
 for fi,heldout in enumerate(FOLDS):
  train_conditions=[q for q in CONDITIONS if q[1]!=heldout]
  xs=[];ys=[];train_rows=[]
  for j,(basis,regime) in enumerate(train_conditions):
   c,m=prepared[(basis,regime)];seed=FOLD_TRAIN_SEEDS[fi][j]
   t=time.perf_counter();det,obs=c.compile_detector_sampler(seed=seed).sample(shots=SHOTS,separate_observables=True)
   cp=np.asarray(m[0].decode_batch(det,enable_correlations=True),dtype=bool).reshape(SHOTS,-1)
   pp=np.asarray(m[1].decode_batch(det,enable_correlations=False),dtype=bool).reshape(SHOTS,-1)
   _,flag=features(det,cp,pp);wrong=np.any(cp!=obs,axis=1)
   xs.append(det[flag].astype(np.float64));ys.append(wrong[flag].astype(np.uint8))
   elapsed=time.perf_counter()-t;total_train_time+=elapsed
   train_rows.append({"memory_basis":basis,"regime":regime,"seed":seed,"shots":SHOTS,"flags":int(flag.sum()),"correlated_wrong":int(wrong[flag].sum()),"seconds":elapsed})
  X=np.concatenate(xs,axis=0);Y=np.concatenate(ys)
  if len(np.unique(Y))<2:raise RuntimeError(f"fold {heldout} training labels have one class")
  fit_start=time.perf_counter();coef,bias,fit=fit_logistic(X,Y);fit_s=time.perf_counter()-fit_start
  val_rows=[]
  for vi,(basis,regime) in enumerate(q for q in CONDITIONS if q[1]==heldout):
   c,m=prepared[(basis,regime)];seed=VALIDATION_SEEDS[CONDITIONS.index((basis,regime))]
   det,obs=c.compile_detector_sampler(seed=seed).sample(shots=SHOTS,separate_observables=True)
   t=time.perf_counter();cp=np.asarray(m[0].decode_batch(det,enable_correlations=True),dtype=bool).reshape(SHOTS,-1);ct=time.perf_counter()-t
   t=time.perf_counter();pp=np.asarray(m[1].decode_batch(det,enable_correlations=False),dtype=bool).reshape(SHOTS,-1);pt=time.perf_counter()-t
   _,flag=features(det,cp,pp);wrong_pred=np.zeros(SHOTS,dtype=bool)
   t=time.perf_counter()
   if flag.any():wrong_pred[flag]=det[flag].astype(np.float64)@coef+bias>=0
   rt=time.perf_counter()-t
   pred=cp.copy();pred[flag]=np.where(wrong_pred[flag,None],pp[flag],cp[flag])
   prior_pred=cp.copy();abs_pred=cp.copy();x=np.concatenate((det.astype(np.float64),cp.astype(np.float64),pp.astype(np.float64)),axis=1)
   if flag.any():
    prior_pred[flag]=np.where((det[flag].astype(np.float64)@prior_coef+prior_bias>=0)[:,None],pp[flag],cp[flag])
    abs_pred[flag]=(x[flag]@abscoef+absbias>=0).reshape(-1,1)
   si=CONDITIONS.index((basis,regime));q=spec[si];spcoef=np.asarray(q['coefficients'],dtype=np.float64);spbias=q['intercept'];specpred=cp.copy()
   if flag.any():specpred[flag]=(x[flag]@spcoef+spbias>=0).reshape(-1,1)
   cf=np.any(cp!=obs,axis=1);rf=np.any(pred!=obs,axis=1);pf=np.any(prior_pred!=obs,axis=1);af=np.any(abs_pred!=obs,axis=1);sf=np.any(specpred!=obs,axis=1)
   val_rows.append({"memory_basis":basis,"regime":regime,"seed":seed,"shots":SHOTS,"flagged":int(flag.sum()),"flag_rate":float(flag.mean()),
    "failures":{"correlated":int(cf.sum()),"leave_profile_out":int(rf.sum()),"all_profile_relative_reference":int(pf.sum()),"all_profile_absolute_reference":int(af.sum()),"specialized_reference":int(sf.sum())},
    "ler":{"correlated":float(cf.mean()),"leave_profile_out":float(rf.mean()),"all_profile_relative_reference":float(pf.mean()),"all_profile_absolute_reference":float(af.mean()),"specialized_reference":float(sf.mean())},
    "paired_transfer_minus_correlated":paired(cf,rf),"time_ratio":(ct+pt+rt)/ct})
  base=float(np.mean([r['ler']['correlated'] for r in val_rows]));candidate=float(np.mean([r['ler']['leave_profile_out'] for r in val_rows]));red=1-candidate/base
  cells=[1-r['ler']['leave_profile_out']/r['ler']['correlated'] for r in val_rows]
  fold_rows.append({"held_out_regime":heldout,"training":train_rows,"training_flagged":int(len(Y)),"training_correlated_wrong":int(Y.sum()),"training_fit":fit,"fit_seconds":fit_s,"validation":val_rows,"macro_ler":{"correlated":base,"leave_profile_out":candidate},"macro_relative_reduction":red,"per_cell_reductions":cells,"passed_fold_positive_direction":red>0})
  all_training.extend(train_rows);all_validation.extend(val_rows)
 base=float(np.mean([r['ler']['correlated'] for r in all_validation]));candidate=float(np.mean([r['ler']['leave_profile_out'] for r in all_validation]));red=1-candidate/base
 cells=[1-r['ler']['leave_profile_out']/r['ler']['correlated'] for r in all_validation];ratio=float(np.mean([r['time_ratio'] for r in all_validation]))
 out={"status":"fast_flagged_logistic_leave_profile_out","folds":fold_rows,"validation":all_validation,"training":all_training,"preflight":pre,
  "macro_ler":{"correlated":base,"leave_profile_out":candidate,"all_profile_relative_reference":float(np.mean([r['ler']['all_profile_relative_reference'] for r in all_validation])),"all_profile_absolute_reference":float(np.mean([r['ler']['all_profile_absolute_reference'] for r in all_validation])),"specialized_reference":float(np.mean([r['ler']['specialized_reference'] for r in all_validation]))},
  "macro_relative_reduction":red,"per_condition_relative_reductions":cells,"mean_time_ratio":ratio,
  "advancement_gate_passed":red>=.10 and min(cells)>=-.05 and ratio<2 and all(r['passed_fold_positive_direction'] for r in fold_rows),
  "preflight_samples":len(CONDITIONS)*PREFLIGHT_SHOTS,"training_samples":3*4*SHOTS,"validation_samples":len(CONDITIONS)*SHOTS,
  "projected_sampling_matching_seconds":projection,"training_runtime_seconds":total_train_time,"elapsed_seconds":time.perf_counter()-start,
  "scope":"leave-one-regime-out transfer of relative-choice classifier; held-out regime absent from fit labels"}
 (HERE/'fast_flagged_logistic_leave_profile_out_results.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({"macro_ler":out['macro_ler'],"reduction":red,"per_cell":cells,"time_ratio":ratio,"folds":[(r['held_out_regime'],r['macro_relative_reduction']) for r in fold_rows],"gate":out['advancement_gate_passed'],"elapsed":out['elapsed_seconds']},indent=2))
if __name__=='__main__':main()
