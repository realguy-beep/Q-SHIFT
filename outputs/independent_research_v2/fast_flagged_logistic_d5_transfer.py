"""Distance-specific d5 train/held-out screen of the flagged logistic method."""
from __future__ import annotations
import json, math, sys, time
from pathlib import Path
import numpy as np
import pymatching, stim
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/"outputs"/"independent_research_v1"))
sys.path.insert(0,str(REPO/"outputs"/"phase2b_pauli_bias"))
from code_distance_scaling import build_scaled_circuit
from noise_model import MEMORY_BASES,REGIMES
from fast_flagged_logistic import features,fit_logistic,wilson,DEM_THRESHOLD
CONDITIONS=tuple((b,r) for b in MEMORY_BASES for r in REGIMES)
PREFLIGHT_SEEDS=(2026115201,2026115202,2026115203,2026115204,2026115205,2026115206)
TRAIN_SEEDS=(2026115211,2026115212,2026115213,2026115214,2026115215,2026115216)
VALIDATION_SEEDS=(2026115221,2026115222,2026115223,2026115224,2026115225,2026115226)
PREFLIGHT_SHOTS=10_000;SHOTS=1_000_000;DISTANCE=5;ROUNDS=9;MAX_SECONDS=300.

def models(c):
 dem=c.detector_error_model(decompose_errors=True,approximate_disjoint_errors=DEM_THRESHOLD)
 return (pymatching.Matching.from_detector_error_model(dem,enable_correlations=True),
         pymatching.Matching.from_detector_error_model(dem,enable_correlations=False))

def run(c,mods,n,seed,coef=None,bias=0.,labels=True):
 t=time.perf_counter();det,obs=c.compile_detector_sampler(seed=seed).sample(shots=n,separate_observables=True);sample_s=time.perf_counter()-t
 t=time.perf_counter();cp=np.asarray(mods[0].decode_batch(det,enable_correlations=True),dtype=bool).reshape(n,-1);corr_s=time.perf_counter()-t
 t=time.perf_counter();pp=np.asarray(mods[1].decode_batch(det,enable_correlations=False),dtype=bool).reshape(n,-1);plain_s=time.perf_counter()-t
 x,flag=features(det,cp,pp);hybrid=cp.copy();pred_s=0.
 if coef is not None and flag.any():
  t=time.perf_counter();hybrid[flag]=(x[flag]@coef+bias>=0).reshape(-1,1);pred_s=time.perf_counter()-t
 row={"seed":seed,"shots":n,"feature_dimension":int(x.shape[1]),"flagged":int(flag.sum()),"flag_rate":float(flag.mean()),"sample_seconds":sample_s,"correlated_seconds":corr_s,"ordinary_seconds":plain_s,"classifier_seconds":pred_s,"policy_to_correlated_time_ratio":(corr_s+plain_s+pred_s)/corr_s}
 if labels:
  cf=np.any(cp!=obs,axis=1);hf=np.any(hybrid!=obs,axis=1);delta=hf.astype(np.int8)-cf.astype(np.int8);se=float(delta.std(ddof=1)/math.sqrt(n))
  co=int(np.count_nonzero(cf&~hf));ho=int(np.count_nonzero(hf&~cf))
  row.update({"failures":{"correlated":int(cf.sum()),"ordinary":int(np.any(pp!=obs,axis=1).sum()),"selector":int(hf.sum())},"ler":{"correlated":float(cf.mean()),"selector":float(hf.mean())},"paired_selector_minus_correlated":float(delta.mean()),"paired_95_ci":[float(delta.mean()-1.95996398454*se),float(delta.mean()+1.95996398454*se)],"correlated_only":co,"selector_only":ho,"flagged_label_counts":{"logical0":int(np.count_nonzero(obs[flag]==0)),"logical1":int(np.count_nonzero(obs[flag]==1))}})
 return row

def main():
 start=time.perf_counter();prepared=[];pre=[]
 for (basis,regime),seed in zip(CONDITIONS,PREFLIGHT_SEEDS,strict=True):
  c=build_scaled_circuit(basis,regime,DISTANCE,ROUNDS)
  if (c.num_qubits,c.num_detectors,c.num_observables)!=(64,216,1):raise RuntimeError("unexpected d5 circuit geometry")
  clean=stim.Circuit()
  for ins in c.flattened():
   if ins.name not in ("PAULI_CHANNEL_1","PAULI_CHANNEL_2","X_ERROR","Z_ERROR"):clean.append(ins.name,ins.targets_copy(),ins.gate_args_copy())
  nd,no=clean.compile_detector_sampler(seed=1).sample(40,separate_observables=True)
  if nd.any() or no.any():raise RuntimeError("noiseless d5 check failed")
  m=models(c);row=run(c,m,PREFLIGHT_SHOTS,seed,coef=np.zeros(218))
  d,o=c.compile_detector_sampler(seed=seed+100).sample(40,separate_observables=True)
  cb=np.asarray(m[0].decode_batch(d,enable_correlations=True),dtype=bool).reshape(40,-1)
  pb=np.asarray(m[1].decode_batch(d,enable_correlations=False),dtype=bool).reshape(40,-1)
  cs=np.asarray([m[0].decode(s,enable_correlations=True) for s in d],dtype=bool).reshape(40,-1)
  ps=np.asarray([m[1].decode(s,enable_correlations=False) for s in d],dtype=bool).reshape(40,-1)
  if not np.array_equal(cb,cs) or not np.array_equal(pb,ps):raise RuntimeError("scalar/batch mismatch")
  if row["feature_dimension"]!=218:raise RuntimeError("unexpected d5 feature dimension")
  pre.append({"memory_basis":basis,"regime":regime,"metrics":row});prepared.append((c,m))
 projection=sum((r["metrics"]["sample_seconds"]+r["metrics"]["correlated_seconds"]+r["metrics"]["ordinary_seconds"])*2*SHOTS/PREFLIGHT_SHOTS for r in pre)
 if projection>MAX_SECONDS:raise RuntimeError(f"preflight projection {projection:.1f}s exceeds cap")
 trained=[];validated=[];train_s_total=0.
 for i,((basis,regime),(c,m)) in enumerate(zip(CONDITIONS,prepared,strict=True)):
  t=time.perf_counter();det,obs=c.compile_detector_sampler(seed=TRAIN_SEEDS[i]).sample(shots=SHOTS,separate_observables=True)
  cp=np.asarray(m[0].decode_batch(det,enable_correlations=True),dtype=bool).reshape(SHOTS,-1)
  pp=np.asarray(m[1].decode_batch(det,enable_correlations=False),dtype=bool).reshape(SHOTS,-1)
  x,flag=features(det,cp,pp)
  if flag.sum()==0 or len(np.unique(obs[flag]))<2:raise RuntimeError(f"training flagged labels lack both classes: {basis}/{regime}")
  fit_t=time.perf_counter();coef,bias,fit=fit_logistic(x[flag],obs[flag]);fit_s=time.perf_counter()-fit_t
  training_s=time.perf_counter()-t;train_s_total+=training_s
  trained.append({"memory_basis":basis,"regime":regime,"seed":TRAIN_SEEDS[i],"shots":SHOTS,"flagged":int(flag.sum()),"feature_dimension":int(x.shape[1]),"fit_seconds":fit_s,"training_seconds":training_s,"fit":fit,"coefficients":coef.tolist(),"intercept":bias})
  row=run(c,m,SHOTS,VALIDATION_SEEDS[i],coef,bias,True);row.update({"memory_basis":basis,"regime":regime});validated.append(row)
 base=float(np.mean([r["ler"]["correlated"] for r in validated]));cand=float(np.mean([r["ler"]["selector"] for r in validated]));red=1-cand/base
 cells=[1-r["ler"]["selector"]/r["ler"]["correlated"] for r in validated];ratio=float(np.mean([r["policy_to_correlated_time_ratio"] for r in validated]))
 out={"status":"fast_flagged_logistic_d5_distance_specific_development","distance":DISTANCE,"rounds":ROUNDS,"conditions":validated,"training":trained,"preflight":pre,"macro_ler":{"correlated":base,"selector":cand},"macro_relative_reduction":red,"per_condition_relative_reductions":cells,"mean_policy_time_ratio":ratio,"advancement_gate_passed":red>=.10 and min(cells)>=-.05 and ratio<2,"preflight_samples":len(CONDITIONS)*PREFLIGHT_SHOTS,"training_samples":len(CONDITIONS)*SHOTS,"validation_samples":len(CONDITIONS)*SHOTS,"projected_train_validation_sampling_matching_seconds":projection,"training_runtime_seconds":train_s_total,"elapsed_seconds":time.perf_counter()-start,"feature_definition":"all 216 d5 detector bits plus correlated and ordinary logical outputs","scope":"distance-specific d5 models; d3 coefficients not transferred; held-out development only"}
 (HERE/"fast_flagged_logistic_d5_transfer_results.json").write_text(json.dumps(out,indent=2)+"\n")
 print(json.dumps({"macro_ler":out["macro_ler"],"reduction":red,"cells":cells,"time_ratio":ratio,"gate":out["advancement_gate_passed"],"projection":projection,"elapsed":out["elapsed_seconds"]},indent=2))
if __name__=="__main__":main()
