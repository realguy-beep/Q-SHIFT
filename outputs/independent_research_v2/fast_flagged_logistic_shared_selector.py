"""Train one shared flagged-syndrome selector across six nominal d3 conditions."""
from __future__ import annotations
import json, math, sys, time
from pathlib import Path
import numpy as np
import pymatching, stim
from scipy.stats import binomtest
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/"outputs"/"phase2b_pauli_bias"))
from noise_model import MEMORY_BASES,REGIMES,build_circuit
from fast_flagged_logistic import features,fit_logistic,wilson,DEM_THRESHOLD,make_models
CONDITIONS=tuple((b,r) for b in MEMORY_BASES for r in REGIMES)
PREFLIGHT_SEEDS=(2026118501,2026118502,2026118503,2026118504,2026118505,2026118506)
TRAIN_SEEDS=(2026118511,2026118512,2026118513,2026118514,2026118515,2026118516)
VALIDATION_SEEDS=(2026118521,2026118522,2026118523,2026118524,2026118525,2026118526)
PREFLIGHT_SHOTS=10_000;SHOTS=1_000_000;MAX_SECONDS=300.

def paired(a,b):
 d=b.astype(np.int8)-a.astype(np.int8);delta=float(d.mean());se=float(d.std(ddof=1)/math.sqrt(len(d)))
 a_only=int(np.count_nonzero(a&~b));b_only=int(np.count_nonzero(b&~a));n=a_only+b_only
 return {"delta_second_minus_first":delta,"normal_95_ci":[delta-1.95996398454*se,delta+1.95996398454*se],
         "first_only_failures":a_only,"second_only_failures":b_only,
         "mcnemar_exact_two_sided":float(binomtest(a_only,n,.5).pvalue) if n else 1.}

def run_validation(c,m,seed,n,coef,bias,specialized_coef,specialized_bias):
 t=time.perf_counter();det,obs=c.compile_detector_sampler(seed=seed).sample(shots=n,separate_observables=True);sample_s=time.perf_counter()-t
 t=time.perf_counter();cp=np.asarray(m[0].decode_batch(det,enable_correlations=True),dtype=bool).reshape(n,-1);corr_s=time.perf_counter()-t
 t=time.perf_counter();pp=np.asarray(m[1].decode_batch(det,enable_correlations=False),dtype=bool).reshape(n,-1);plain_s=time.perf_counter()-t
 x,flag=features(det,cp,pp);shared=cp.copy();specialized=cp.copy()
 t=time.perf_counter()
 if flag.any():shared[flag]=(x[flag]@coef+bias>=0).reshape(-1,1)
 shared_s=time.perf_counter()-t
 t=time.perf_counter()
 if flag.any():specialized[flag]=(x[flag]@specialized_coef+specialized_bias>=0).reshape(-1,1)
 specialized_s=time.perf_counter()-t
 cf=np.any(cp!=obs,axis=1);sf=np.any(shared!=obs,axis=1);pf=np.any(specialized!=obs,axis=1)
 return {"seed":seed,"shots":n,"flagged":int(flag.sum()),"flag_rate":float(flag.mean()),
  "failures":{"correlated":int(cf.sum()),"shared":int(sf.sum()),"specialized_reference":int(pf.sum())},
  "ler":{"correlated":float(cf.mean()),"shared":float(sf.mean()),"specialized_reference":float(pf.mean())},
  "wilson_95":{"correlated":wilson(int(cf.sum()),n),"shared":wilson(int(sf.sum()),n)},
  "paired_shared_minus_correlated":paired(cf,sf),"paired_shared_minus_specialized":paired(pf,sf),
  "sample_seconds":sample_s,"correlated_seconds":corr_s,"ordinary_seconds":plain_s,
  "shared_classifier_seconds":shared_s,"specialized_classifier_seconds":specialized_s,
  "shared_policy_time_ratio":(corr_s+plain_s+shared_s)/corr_s,
  "specialized_policy_time_ratio":(corr_s+plain_s+specialized_s)/corr_s}

def main():
 start=time.perf_counter();prepared=[];pre=[]
 for (basis,regime),seed in zip(CONDITIONS,PREFLIGHT_SEEDS,strict=True):
  c=build_circuit(basis,regime);m=make_models(c)
  if (c.num_qubits,c.num_detectors,c.num_observables)!=(26,40,1):raise RuntimeError("d3 geometry mismatch")
  clean=stim.Circuit()
  for ins in c.flattened():
   if ins.name not in ("PAULI_CHANNEL_1","PAULI_CHANNEL_2","X_ERROR","Z_ERROR"):clean.append(ins.name,ins.targets_copy(),ins.gate_args_copy())
  nd,no=clean.compile_detector_sampler(seed=1).sample(20,separate_observables=True)
  if nd.any() or no.any():raise RuntimeError("noiseless check failed")
  t=time.perf_counter();det,obs=c.compile_detector_sampler(seed=seed).sample(shots=PREFLIGHT_SHOTS,separate_observables=True);sample_s=time.perf_counter()-t
  t=time.perf_counter();cb=np.asarray(m[0].decode_batch(det,enable_correlations=True),dtype=bool).reshape(PREFLIGHT_SHOTS,-1);corr_s=time.perf_counter()-t
  t=time.perf_counter();pb=np.asarray(m[1].decode_batch(det,enable_correlations=False),dtype=bool).reshape(PREFLIGHT_SHOTS,-1);plain_s=time.perf_counter()-t
  cs=np.asarray([m[0].decode(s,enable_correlations=True) for s in det[:20]],dtype=bool).reshape(20,-1)
  ps=np.asarray([m[1].decode(s,enable_correlations=False) for s in det[:20]],dtype=bool).reshape(20,-1)
  if not np.array_equal(cb[:20],cs) or not np.array_equal(pb[:20],ps):raise RuntimeError("scalar/batch mismatch")
  x,flag=features(det,cb,pb)
  if x.shape[1]!=42:raise RuntimeError("unexpected feature shape")
  pre.append({"memory_basis":basis,"regime":regime,"seed":seed,"shots":PREFLIGHT_SHOTS,"flags":int(flag.sum()),"feature_dimension":int(x.shape[1]),"sample_seconds":sample_s,"correlated_seconds":corr_s,"ordinary_seconds":plain_s})
  prepared.append((c,m))
 # Project main train+validation sampling and both matching passes from measured preflight rates.
 projection=sum((r["sample_seconds"]+r["correlated_seconds"]+r["ordinary_seconds"])*2*SHOTS/PREFLIGHT_SHOTS for r in pre)
 if projection>MAX_SECONDS:raise RuntimeError(f"projected sampling/matching runtime {projection:.1f}s exceeds cap")
 nominal=json.load(open(HERE/"fast_flagged_logistic_replication_results.json"))
 pooled_x=[];pooled_y=[];training=[];train_runtime=0.
 for i,((basis,regime),(c,m)) in enumerate(zip(CONDITIONS,prepared,strict=True)):
  t=time.perf_counter();det,obs=c.compile_detector_sampler(seed=TRAIN_SEEDS[i]).sample(shots=SHOTS,separate_observables=True)
  cp=np.asarray(m[0].decode_batch(det,enable_correlations=True),dtype=bool).reshape(SHOTS,-1)
  pp=np.asarray(m[1].decode_batch(det,enable_correlations=False),dtype=bool).reshape(SHOTS,-1)
  x,flag=features(det,cp,pp)
  pooled_x.append(x[flag]);pooled_y.append(obs[flag].astype(np.uint8).reshape(-1))
  elapsed=time.perf_counter()-t;train_runtime+=elapsed
  training.append({"memory_basis":basis,"regime":regime,"seed":TRAIN_SEEDS[i],"shots":SHOTS,"flagged":int(flag.sum()),"flagged_logical0":int(np.count_nonzero(obs[flag]==0)),"flagged_logical1":int(np.count_nonzero(obs[flag]==1)),"training_seconds":elapsed})
 X=np.concatenate(pooled_x,axis=0);Y=np.concatenate(pooled_y)
 if len(np.unique(Y))<2:raise RuntimeError("pooled training labels have one class")
 fit_start=time.perf_counter();coef,bias,fit=fit_logistic(X,Y);fit_s=time.perf_counter()-fit_start
 # Load the independent per-condition coefficients as a fixed same-stream reference.
 specialist=nominal["trained_models"]
 validated=[]
 for i,((basis,regime),(c,m)) in enumerate(zip(CONDITIONS,prepared,strict=True)):
  q=specialist[i]
  row=run_validation(c,m,VALIDATION_SEEDS[i],SHOTS,coef,bias,np.asarray(q["coefficients"],dtype=np.float64),q["intercept"])
  row.update({"memory_basis":basis,"regime":regime});validated.append(row)
 base=float(np.mean([r["ler"]["correlated"] for r in validated]));shared=float(np.mean([r["ler"]["shared"] for r in validated]));special=float(np.mean([r["ler"]["specialized_reference"] for r in validated]))
 rel=1-shared/base;cells=[1-r["ler"]["shared"]/r["ler"]["correlated"] for r in validated];tr=float(np.mean([r["shared_policy_time_ratio"] for r in validated]))
 out={"status":"fast_flagged_logistic_shared_selector","conditions":validated,"training":training,"preflight":pre,
  "pooled_training":{"flagged_rows":int(len(Y)),"logical0":int(np.count_nonzero(Y==0)),"logical1":int(np.count_nonzero(Y==1)),"feature_dimension":int(X.shape[1]),"fit":fit,"coefficients":coef.tolist(),"intercept":bias,"fit_seconds":fit_s},
  "macro_ler":{"correlated":base,"shared_selector":shared,"specialized_reference_same_validation":special},"macro_relative_reduction":rel,
  "per_condition_relative_reductions":cells,"mean_shared_policy_time_ratio":tr,"mean_specialized_policy_time_ratio":float(np.mean([r["specialized_policy_time_ratio"] for r in validated])),
  "advancement_gate_passed":rel>=.10 and min(cells)>=-.05 and tr<2,
  "preflight_samples":len(CONDITIONS)*PREFLIGHT_SHOTS,"training_samples":len(CONDITIONS)*SHOTS,"validation_samples":len(CONDITIONS)*SHOTS,
  "projected_sampling_matching_seconds":projection,"training_runtime_seconds":train_runtime,"elapsed_seconds":time.perf_counter()-start,
  "scope":"one pooled shared d3 selector across six nominal known-profile conditions; validation labels held out"}
 (HERE/"fast_flagged_logistic_shared_selector_results.json").write_text(json.dumps(out,indent=2)+"\n")
 print(json.dumps({"macro_ler":out["macro_ler"],"reduction":rel,"per_cell":cells,"time_ratio":tr,"gate":out["advancement_gate_passed"],"pooled_flags":len(Y),"elapsed":out["elapsed_seconds"]},indent=2))
if __name__=="__main__":main()
