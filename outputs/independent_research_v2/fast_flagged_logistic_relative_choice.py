"""Shared classifier predicts whether correlated matching is wrong on flagged syndromes."""
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
PREFLIGHT_SEEDS=(2026118701,2026118702,2026118703,2026118704,2026118705,2026118706)
TRAIN_SEEDS=(2026118711,2026118712,2026118713,2026118714,2026118715,2026118716)
VALIDATION_SEEDS=(2026118721,2026118722,2026118723,2026118724,2026118725,2026118726)
PREFLIGHT_SHOTS=10_000;SHOTS=1_000_000;MAX_SECONDS=300.

def paired(a,b):
 d=b.astype(np.int8)-a.astype(np.int8);delta=float(d.mean());se=float(d.std(ddof=1)/math.sqrt(len(d)))
 ao=int(np.count_nonzero(a&~b));bo=int(np.count_nonzero(b&~a));n=ao+bo
 return {"delta_second_minus_first":delta,"normal_95_ci":[delta-1.95996398454*se,delta+1.95996398454*se],"first_only_failures":ao,"second_only_failures":bo,"mcnemar_exact_two_sided":float(binomtest(ao,n,.5).pvalue) if n else 1.}

def main():
 start=time.perf_counter();pre=[];prepared=[]
 for (basis,regime),seed in zip(CONDITIONS,PREFLIGHT_SEEDS,strict=True):
  c=build_circuit(basis,regime);m=make_models(c)
  if (c.num_qubits,c.num_detectors,c.num_observables)!=(26,40,1):raise RuntimeError("d3 geometry mismatch")
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
  x,flag=features(det,cp,pp)
  if x.shape[1]!=42:raise RuntimeError("unexpected feature geometry")
  pre.append({"memory_basis":basis,"regime":regime,"seed":seed,"shots":PREFLIGHT_SHOTS,"flags":int(flag.sum()),"sample_seconds":st,"correlated_seconds":ct,"ordinary_seconds":pt})
  prepared.append((c,m))
 projection=sum((r["sample_seconds"]+r["correlated_seconds"]+r["ordinary_seconds"])*2*SHOTS/PREFLIGHT_SHOTS for r in pre)
 if projection>MAX_SECONDS:raise RuntimeError(f"projected train/validation runtime {projection:.1f}s exceeds cap")
 pooled_x=[];pooled_y=[];training=[];train_runtime=0.
 for i,((basis,regime),(c,m)) in enumerate(zip(CONDITIONS,prepared,strict=True)):
  t=time.perf_counter();det,obs=c.compile_detector_sampler(seed=TRAIN_SEEDS[i]).sample(shots=SHOTS,separate_observables=True)
  cp=np.asarray(m[0].decode_batch(det,enable_correlations=True),dtype=bool).reshape(SHOTS,-1)
  pp=np.asarray(m[1].decode_batch(det,enable_correlations=False),dtype=bool).reshape(SHOTS,-1)
  _,flag=features(det,cp,pp);corr_wrong=np.any(cp!=obs,axis=1)
  pooled_x.append(det[flag].astype(np.float64));pooled_y.append(corr_wrong[flag].astype(np.uint8))
  elapsed=time.perf_counter()-t;train_runtime+=elapsed
  training.append({"memory_basis":basis,"regime":regime,"seed":TRAIN_SEEDS[i],"shots":SHOTS,"flagged":int(flag.sum()),"correlated_wrong_labels":int(corr_wrong[flag].sum()),"training_seconds":elapsed})
 X=np.concatenate(pooled_x,axis=0);Y=np.concatenate(pooled_y)
 if len(np.unique(Y))<2:raise RuntimeError("pooled relative labels have one class")
 fit_start=time.perf_counter();coef,bias,fit=fit_logistic(X,Y);fit_s=time.perf_counter()-fit_start
 nominal=json.load(open(HERE/"fast_flagged_logistic_replication_results.json"))
 shared_abs=json.load(open(HERE/"fast_flagged_logistic_shared_selector_replication_results.json"))['pooled_training']
 abs_coef=np.asarray(shared_abs['coefficients'],dtype=np.float64);abs_bias=shared_abs['intercept']
 spec=nominal['trained_models'];validated=[]
 for i,((basis,regime),(c,m)) in enumerate(zip(CONDITIONS,prepared,strict=True)):
  seed=VALIDATION_SEEDS[i];det,obs=c.compile_detector_sampler(seed=seed).sample(shots=SHOTS,separate_observables=True)
  t=time.perf_counter();cp=np.asarray(m[0].decode_batch(det,enable_correlations=True),dtype=bool).reshape(SHOTS,-1);ct=time.perf_counter()-t
  t=time.perf_counter();pp=np.asarray(m[1].decode_batch(det,enable_correlations=False),dtype=bool).reshape(SHOTS,-1);pt=time.perf_counter()-t
  x,flag=features(det,cp,pp);corr_wrong_pred=np.zeros(SHOTS,dtype=bool);shared_abs_pred=cp.copy();special_pred=cp.copy()
  t=time.perf_counter()
  if flag.any():corr_wrong_pred[flag]=det[flag].astype(np.float64)@coef+bias>=0
  rel_time=time.perf_counter()-t
  relative=cp.copy();relative[flag]=np.where(corr_wrong_pred[flag,None],pp[flag],cp[flag])
  t=time.perf_counter()
  if flag.any():shared_abs_pred[flag]=(x[flag]@abs_coef+abs_bias>=0).reshape(-1,1)
  abs_time=time.perf_counter()-t
  q=spec[i];spcoef=np.asarray(q['coefficients'],dtype=np.float64);spbias=q['intercept']
  t=time.perf_counter()
  if flag.any():special_pred[flag]=(x[flag]@spcoef+spbias>=0).reshape(-1,1)
  specialist_time=time.perf_counter()-t
  cf=np.any(cp!=obs,axis=1);rf=np.any(relative!=obs,axis=1);af=np.any(shared_abs_pred!=obs,axis=1);sf=np.any(special_pred!=obs,axis=1)
  validated.append({"memory_basis":basis,"regime":regime,"seed":seed,"shots":SHOTS,"flagged":int(flag.sum()),"flag_rate":float(flag.mean()),
   "failures":{"correlated":int(cf.sum()),"relative_choice":int(rf.sum()),"shared_absolute_reference":int(af.sum()),"specialized_reference":int(sf.sum())},
   "ler":{"correlated":float(cf.mean()),"relative_choice":float(rf.mean()),"shared_absolute_reference":float(af.mean()),"specialized_reference":float(sf.mean())},
   "paired_relative_minus_correlated":paired(cf,rf),"paired_relative_minus_shared_absolute":paired(af,rf),"paired_relative_minus_specialized":paired(sf,rf),
   "time_ratio_relative_choice":(ct+pt+rel_time)/ct,"time_ratio_shared_absolute":(ct+pt+abs_time)/ct,"time_ratio_specialized":(ct+pt+specialist_time)/ct})
 base=float(np.mean([r['ler']['correlated'] for r in validated]));cand=float(np.mean([r['ler']['relative_choice'] for r in validated]));absbase=float(np.mean([r['ler']['shared_absolute_reference'] for r in validated]));specbase=float(np.mean([r['ler']['specialized_reference'] for r in validated]))
 rel=1-cand/base;cells=[1-r['ler']['relative_choice']/r['ler']['correlated'] for r in validated];tr=float(np.mean([r['time_ratio_relative_choice'] for r in validated]))
 out={"status":"fast_flagged_logistic_relative_choice","conditions":validated,"training":training,"preflight":pre,
  "pooled_training":{"flagged_rows":int(len(Y)),"correlated_wrong":int(Y.sum()),"correlated_right":int(len(Y)-Y.sum()),"feature_dimension":int(X.shape[1]),"fit":fit,"coefficients":coef.tolist(),"intercept":bias,"fit_seconds":fit_s},
  "macro_ler":{"correlated":base,"relative_choice":cand,"shared_absolute_reference_same_validation":absbase,"specialized_reference_same_validation":specbase},
  "macro_relative_reduction":rel,"per_condition_relative_reductions":cells,"mean_relative_policy_time_ratio":tr,
  "mean_shared_absolute_time_ratio":float(np.mean([r['time_ratio_shared_absolute'] for r in validated])),"mean_specialized_time_ratio":float(np.mean([r['time_ratio_specialized'] for r in validated])),
  "advancement_gate_passed":rel>=.10 and min(cells)>=-.05 and tr<2,
  "preflight_samples":len(CONDITIONS)*PREFLIGHT_SHOTS,"training_samples":len(CONDITIONS)*SHOTS,"validation_samples":len(CONDITIONS)*SHOTS,
  "projected_train_validation_sampling_matching_seconds":projection,"training_runtime_seconds":train_runtime,"elapsed_seconds":time.perf_counter()-start,
  "scope":"one shared relative matcher-choice model trained on flagged nominal d3 syndromes; validation held out"}
 (HERE/"fast_flagged_logistic_relative_choice_results.json").write_text(json.dumps(out,indent=2)+"\n")
 print(json.dumps({"macro_ler":out['macro_ler'],"reduction":rel,"cells":cells,"time_ratio":tr,"gate":out['advancement_gate_passed'],"flags":len(Y),"elapsed":out['elapsed_seconds']},indent=2))
if __name__=="__main__":main()
