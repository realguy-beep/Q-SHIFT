"""Train a small syndrome-only classifier for flagged matching disagreements."""
from __future__ import annotations
import json,math,sys,time
from pathlib import Path
import numpy as np
import pymatching,stim
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import binomtest
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/"outputs"/"phase2b_pauli_bias"))
from noise_model import MEMORY_BASES,REGIMES,build_circuit
CONDITIONS=tuple((b,r) for b in MEMORY_BASES for r in REGIMES)
PREFLIGHT_SEEDS=(2026114391,2026114392,2026114393,2026114394,2026114395,2026114396)
TRAIN_SEEDS=(2026114401,2026114402,2026114403,2026114404,2026114405,2026114406)
VALIDATION_SEEDS=(2026114411,2026114412,2026114413,2026114414,2026114415,2026114416)
PREFLIGHT_SHOTS=10_000
SHOTS=1_000_000
DEM_THRESHOLD=.0018
MAX_SECONDS=300.


def make_models(circuit):
    dem=circuit.detector_error_model(decompose_errors=True,approximate_disjoint_errors=DEM_THRESHOLD)
    corr=pymatching.Matching.from_detector_error_model(dem,enable_correlations=True)
    plain=pymatching.Matching.from_detector_error_model(dem,enable_correlations=False)
    return corr,plain


def features(det,corr,plain):
    c=np.asarray(corr,dtype=np.float64).reshape(len(det),-1)
    p=np.asarray(plain,dtype=np.float64).reshape(len(det),-1)
    return np.concatenate((det.astype(np.float64),c,p),axis=1),np.any(c!=p,axis=1)


def fit_logistic(x,y):
    y=np.asarray(y,dtype=np.float64).reshape(-1)
    if len(np.unique(y))<2: raise RuntimeError("flagged training rows contain only one logical class")
    n,d=x.shape
    def loss_grad(theta):
        w=theta[:d];b=theta[d];z=x@w+b
        loss=float(np.logaddexp(0,z).sum()-np.dot(y,z)+.5*np.dot(w,w))
        err=expit(z)-y
        grad=np.concatenate((x.T@err+w,[err.sum()]))
        return loss,grad
    result=minimize(lambda q:loss_grad(q),np.zeros(d+1),jac=True,method="L-BFGS-B",
                    options={"maxiter":300,"ftol":1e-10})
    if not result.success or not np.all(np.isfinite(result.x)):
        raise RuntimeError(f"fixed logistic optimizer failed: {result.message}")
    return result.x[:d],float(result.x[d]),{"iterations":int(result.nit),"objective":float(result.fun),
        "optimizer_message":str(result.message),"training_flag_rows":int(n),
        "training_class_counts":{"logical0":int(np.count_nonzero(y==0)),"logical1":int(np.count_nonzero(y==1))}}


def wilson(k,n):
    z=1.959963984540054;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [c-h,c+h]


def run_sample(circuit,models,shots,seed,coef=None,intercept=0.,labels=True):
    corr,plain=models
    t0=time.perf_counter();det,obs=circuit.compile_detector_sampler(seed=seed).sample(shots=shots,separate_observables=True)
    sample_s=time.perf_counter()-t0
    t0=time.perf_counter();cp=np.asarray(corr.decode_batch(det,enable_correlations=True),dtype=bool).reshape(shots,-1)
    corr_s=time.perf_counter()-t0
    t0=time.perf_counter();pp=np.asarray(plain.decode_batch(det,enable_correlations=False),dtype=bool).reshape(shots,-1)
    plain_s=time.perf_counter()-t0
    x,flag=features(det,cp,pp)
    hybrid=cp.copy();predict_s=0.
    if coef is not None and flag.any():
        t0=time.perf_counter();hybrid[flag]=(x[flag]@coef+intercept>=0).reshape(-1,1);predict_s=time.perf_counter()-t0
    result={"shots":shots,"seed":seed,"flagged":int(flag.sum()),"flag_rate":float(flag.mean()),
        "sample_seconds":sample_s,
        "corr_seconds":corr_s,"plain_seconds":plain_s,"classifier_seconds":predict_s,
        "hybrid_inference_seconds":corr_s+plain_s+predict_s,
        "hybrid_to_corr_time_ratio":(corr_s+plain_s+predict_s)/corr_s if corr_s else None,
        "feature_dimension":int(x.shape[1])}
    if labels:
        cf=np.any(cp!=obs,axis=1);pf=np.any(pp!=obs,axis=1);hf=np.any(hybrid!=obs,axis=1)
        d=hf.astype(np.int8)-cf.astype(np.int8);delta=float(d.mean());se=float(d.std(ddof=1)/math.sqrt(shots))
        co=int(np.count_nonzero(cf&~hf));ho=int(np.count_nonzero(hf&~cf));nflag=int(flag.sum())
        result.update({"failures":{"correlated":int(cf.sum()),"ordinary":int(pf.sum()),"hybrid":int(hf.sum())},
          "ler":{"correlated":float(cf.mean()),"ordinary":float(pf.mean()),"hybrid":float(hf.mean())},
          "hybrid_flagged_failures":int(hf[flag].sum()),"hybrid_unflagged_failures":int(hf[~flag].sum()),
          "flagged_logical_class_counts":{"logical0":int(np.count_nonzero(obs[flag]==0)),"logical1":int(np.count_nonzero(obs[flag]==1))},
          "paired_hybrid_minus_correlated_delta":delta,
          "paired_normal_95_ci":[delta-1.95996398454*se,delta+1.95996398454*se],
          "correlated_only_failures":co,"hybrid_only_failures":ho,
          "mcnemar_exact_two_sided":float(binomtest(co,co+ho,.5).pvalue) if co+ho else 1.,
          "classifier_error_on_flagged":int(hf[flag].sum())})
    return result


def main():
    start=time.perf_counter();prepared=[];pre=[]
    for (basis,regime),seed in zip(CONDITIONS,PREFLIGHT_SEEDS,strict=True):
        c=build_circuit(basis,regime)
        if (c.num_qubits,c.num_detectors,c.num_observables)!=(26,40,1):raise RuntimeError("circuit geometry mismatch")
        clean=stim.Circuit()
        for ins in c.flattened():
            if ins.name not in ("PAULI_CHANNEL_1","PAULI_CHANNEL_2","X_ERROR","Z_ERROR"):
                clean.append(ins.name,ins.targets_copy(),ins.gate_args_copy())
        nd,no=clean.compile_detector_sampler(seed=1).sample(20,separate_observables=True)
        if nd.any() or no.any():raise RuntimeError("noiseless circuit mismatch")
        models=make_models(c)
        # Exercise actual sample and both matchers on an independent preflight seed.
        row=run_sample(c,models,PREFLIGHT_SHOTS,seed,coef=np.zeros(42),intercept=0.,labels=True)
        prepared.append((c,models))
        pre.append({"basis":basis,"regime":regime,"metrics":row})
    per_shot=[(x["metrics"]["sample_seconds"]+x["metrics"]["corr_seconds"]+
               x["metrics"]["plain_seconds"])*2*SHOTS/PREFLIGHT_SHOTS for x in pre]
    projection=sum(per_shot)
    if projection>MAX_SECONDS:raise RuntimeError(f"preflight runtime projection {projection:.1f}s exceeds cap")

    models_info=[];train_runtime=0.;validated=[]
    for ix,((basis,regime),(c,mods)) in enumerate(zip(CONDITIONS,prepared,strict=True)):
        # Train on a fresh labeled stream; only flagged syndromes enter the classifier fit.
        t0=time.perf_counter()
        det,obs=c.compile_detector_sampler(seed=TRAIN_SEEDS[ix]).sample(shots=SHOTS,separate_observables=True)
        cp=np.asarray(mods[0].decode_batch(det,enable_correlations=True),dtype=bool).reshape(SHOTS,-1)
        pp=np.asarray(mods[1].decode_batch(det,enable_correlations=False),dtype=bool).reshape(SHOTS,-1)
        x,flag=features(det,cp,pp)
        fit_start=time.perf_counter();coef,bias,fit_info=fit_logistic(x[flag],obs[flag]);fit_s=time.perf_counter()-fit_start
        train_s=time.perf_counter()-t0
        models_info.append({"memory_basis":basis,"regime":regime,"train_seed":TRAIN_SEEDS[ix],
                            "train_shots":SHOTS,"train_flagged":int(flag.sum()),
                            "fit_seconds":fit_s,"train_total_seconds":train_s,
                            "fit":fit_info,"coefficients":coef.tolist(),"intercept":bias})
        train_runtime+=train_s
        row=run_sample(c,mods,SHOTS,VALIDATION_SEEDS[ix],coef=coef,intercept=bias,labels=True)
        row.update({"memory_basis":basis,"regime":regime,"validation_seed":VALIDATION_SEEDS[ix]})
        validated.append(row)
    base=float(np.mean([r["ler"]["correlated"] for r in validated]))
    hybrid=float(np.mean([r["ler"]["hybrid"] for r in validated]))
    reduction=1-hybrid/base
    percell=[1-r["ler"]["hybrid"]/r["ler"]["correlated"] for r in validated]
    time_ratio=float(np.mean([r["hybrid_to_corr_time_ratio"] for r in validated]))
    result={"status":"fast_flagged_logistic_development","conditions":validated,
      "preflight":pre,"trained_models":models_info,
      "macro_ler":{"correlated":base,"hybrid":hybrid},"macro_relative_reduction":reduction,
      "per_condition_relative_reductions":percell,"mean_total_inference_time_ratio":time_ratio,
      "training_total_seconds":train_runtime,
      "advancement_gate_passed":reduction>=.10 and min(percell)>=-.05 and time_ratio<2,
      "preflight_samples":len(CONDITIONS)*PREFLIGHT_SHOTS,
      "training_samples":len(CONDITIONS)*SHOTS,"validation_samples":len(CONDITIONS)*SHOTS,
      "projected_sampling_and_matching_seconds":projection,
      "elapsed_seconds":time.perf_counter()-start,
      "model":{"name":"binary logistic regression","loss":"sum binary cross-entropy + 0.5*L2 squared coefficient norm","intercept_unpenalized":True,"solver":"scipy L-BFGS-B","max_iterations":300,"decision":"logit >= 0 predicts logical 1","features":"40 detector bits plus correlated and ordinary logical prediction bits"},
      "scope":"fixed decoder outputs trained on independent development labels; held-out validation; no confirmatory data"}
    (HERE/"fast_flagged_logistic_results.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"macro_ler":result["macro_ler"],
      "reduction":reduction,"time_ratio":time_ratio,"gate":result["advancement_gate_passed"],
      "per_condition":percell,"elapsed":result["elapsed_seconds"]},indent=2))

if __name__=="__main__":main()
