"""Independent training and validation stream for the fast flagged selector."""
from __future__ import annotations
import json,math,sys,time
from pathlib import Path
import numpy as np
import pymatching,stim
from ldpc import BpLsdDecoder
from scipy.stats import binomtest

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/"outputs"/"independent_research_v1"))
from bplsd_feasibility import model_matrices
from fast_flagged_logistic import (CONDITIONS,build_circuit,make_models,features,fit_logistic,
    run_sample,SHOTS,PREFLIGHT_SHOTS)

PREFLIGHT_SEEDS=(2026114491,2026114492,2026114493,2026114494,2026114495,2026114496)
TRAIN_SEEDS=(2026114501,2026114502,2026114503,2026114504,2026114505,2026114506)
VALIDATION_SEEDS=(2026114511,2026114512,2026114513,2026114514,2026114515,2026114516)


def wilson(k,n):
    z=1.959963984540054;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [c-h,c+h]


def pair(a,b):
    d=b.astype(np.int8)-a.astype(np.int8);delta=float(d.mean());se=float(d.std(ddof=1)/math.sqrt(len(d)))
    ao=int(np.count_nonzero(a&~b));bo=int(np.count_nonzero(b&~a));n=ao+bo
    return {"delta_second_minus_first":delta,"normal_95_ci":[delta-1.95996398454*se,delta+1.95996398454*se],
            "first_only_failures":ao,"second_only_failures":bo,
            "mcnemar_exact_two_sided":float(binomtest(ao,n,.5).pvalue) if n else 1.}


def main():
    start=time.perf_counter();prepared=[];pre=[]
    for (basis,regime),seed in zip(CONDITIONS,PREFLIGHT_SEEDS,strict=True):
        c=build_circuit(basis,regime)
        if (c.num_qubits,c.num_detectors,c.num_observables)!=(26,40,1):raise RuntimeError("geometry mismatch")
        clean=stim.Circuit()
        for ins in c.flattened():
            if ins.name not in ("PAULI_CHANNEL_1","PAULI_CHANNEL_2","X_ERROR","Z_ERROR"):
                clean.append(ins.name,ins.targets_copy(),ins.gate_args_copy())
        nd,no=clean.compile_detector_sampler(seed=1).sample(20,separate_observables=True)
        if nd.any() or no.any():raise RuntimeError("noiseless check failed")
        mods=make_models(c)
        pf=run_sample(c,mods,PREFLIGHT_SHOTS,seed,coef=np.zeros(42),intercept=0.,labels=True)
        pre.append({"basis":basis,"regime":regime,"metrics":pf})
        prepared.append((c,mods))
    projection=sum((p["metrics"]["sample_seconds"]+p["metrics"]["corr_seconds"]+
                    p["metrics"]["plain_seconds"])*2*SHOTS/PREFLIGHT_SHOTS for p in pre)
    if projection>300:raise RuntimeError("runtime projection gate failed")

    train_models=[];fit_s_total=0.;train_elapsed=0.
    for ix,((basis,regime),(c,mods)) in enumerate(zip(CONDITIONS,prepared,strict=True)):
        t0=time.perf_counter();det,obs=c.compile_detector_sampler(seed=TRAIN_SEEDS[ix]).sample(SHOTS,separate_observables=True)
        cp=np.asarray(mods[0].decode_batch(det,enable_correlations=True),dtype=bool).reshape(SHOTS,-1)
        pp=np.asarray(mods[1].decode_batch(det,enable_correlations=False),dtype=bool).reshape(SHOTS,-1)
        x,flag=features(det,cp,pp)
        tf=time.perf_counter();coef,bias,info=fit_logistic(x[flag],obs[flag]);fit_time=time.perf_counter()-tf
        train_time=time.perf_counter()-t0;fit_s_total+=fit_time;train_elapsed+=train_time
        train_models.append({"basis":basis,"regime":regime,"seed":TRAIN_SEEDS[ix],"flagged":int(flag.sum()),
                             "fit_seconds":fit_time,"train_seconds":train_time,"fit":info,
                             "coefficients":coef.tolist(),"intercept":bias})

    rows=[]
    for ix,((basis,regime),(c,mods)) in enumerate(zip(CONDITIONS,prepared,strict=True)):
        t0=time.perf_counter();det,obs=c.compile_detector_sampler(seed=VALIDATION_SEEDS[ix]).sample(SHOTS,separate_observables=True)
        sample_s=time.perf_counter()-t0
        t0=time.perf_counter();cp=np.asarray(mods[0].decode_batch(det,enable_correlations=True),dtype=bool).reshape(SHOTS,-1);corr_s=time.perf_counter()-t0
        t0=time.perf_counter();pp=np.asarray(mods[1].decode_batch(det,enable_correlations=False),dtype=bool).reshape(SHOTS,-1);plain_s=time.perf_counter()-t0
        x,flag=features(det,cp,pp);spec=train_models[ix];coef=np.asarray(spec["coefficients"]);bias=spec["intercept"]
        logistic=cp.copy();t0=time.perf_counter()
        if flag.any():logistic[flag]=(x[flag]@coef+bias>=0).reshape(-1,1)
        logit_s=time.perf_counter()-t0
        # Stronger comparator is the same fixed BP+LSD intervention tested earlier.
        dem=c.detector_error_model(decompose_errors=True,approximate_disjoint_errors=.0018)
        h,l,probs=model_matrices(dem)
        lsd=BpLsdDecoder(pcm=h,error_channel=probs.tolist(),max_iter=200,bp_method="minimum_sum",
            ms_scaling_factor=.9,lsd_order=0,lsd_method="LSD_CS",bits_per_step=1)
        bplsd=cp.copy();lsd_s=0.;invalid=0
        for j in np.flatnonzero(flag):
            t0=time.perf_counter();f=np.asarray(lsd.decode(det[j]),dtype=np.uint8).reshape(-1);lsd_s+=time.perf_counter()-t0
            good=f.shape==(h.shape[1],) and np.array_equal((h@f)&1,det[j]);invalid+=not good
            bplsd[j]=((l@f)&1).astype(bool) if good else True
        cf=np.any(cp!=obs,axis=1);of=np.any(pp!=obs,axis=1);lf=np.any(logistic!=obs,axis=1);bf=np.any(bplsd!=obs,axis=1)
        def rates(v):
            k=int(v.sum());return {"errors":k,"ler":k/SHOTS,"wilson_95":wilson(k,SHOTS)}
        rows.append({"memory_basis":basis,"regime":regime,"seed":VALIDATION_SEEDS[ix],"shots":SHOTS,
          "flagged":int(flag.sum()),"flag_rate":float(flag.mean()),
          "correlated":rates(cf),"ordinary":rates(of),"logistic_hybrid":rates(lf),"bplsd_hybrid":rates(bf),
          "invalid_bplsd_syndromes":invalid,
          "paired_logistic_minus_correlated":pair(cf,lf),"paired_bplsd_minus_correlated":pair(cf,bf),
          "paired_bplsd_minus_logistic":pair(lf,bf),
          "timing":{"sample":sample_s,"correlated":corr_s,"ordinary":plain_s,"logistic_flagged":logit_s,"bplsd_flagged":lsd_s},
          "logistic_total_to_correlated_time_ratio":(corr_s+plain_s+logit_s)/corr_s,
          "bplsd_total_to_correlated_time_ratio":(corr_s+plain_s+lsd_s)/corr_s})
    macro={name:float(np.mean([r[name]["ler"] for r in rows])) for name in ("correlated","ordinary","logistic_hybrid","bplsd_hybrid")}
    reduction=1-macro["logistic_hybrid"]/macro["correlated"]
    percell=[1-r["logistic_hybrid"]["ler"]/r["correlated"]["ler"] for r in rows]
    time_ratio=float(np.mean([r["logistic_total_to_correlated_time_ratio"] for r in rows]))
    bp_reduction=1-macro["bplsd_hybrid"]/macro["correlated"]
    out={"status":"fast_flagged_logistic_independent_replication","conditions":rows,"preflight":pre,
      "trained_models":train_models,"macro_ler":macro,"macro_relative_reduction_logistic":reduction,
      "macro_relative_reduction_bplsd":bp_reduction,"per_condition_logistic_reductions":percell,
      "mean_logistic_total_inference_ratio":time_ratio,
      "logistic_advancement_gate_passed":reduction>=.10 and min(percell)>=-.05 and time_ratio<2,
      "mean_bplsd_total_inference_ratio":float(np.mean([r["bplsd_total_to_correlated_time_ratio"] for r in rows])),
      "training_and_fit_seconds":train_elapsed,"fit_seconds_only":fit_s_total,
      "preflight_samples":len(CONDITIONS)*PREFLIGHT_SHOTS,"training_samples":len(CONDITIONS)*SHOTS,
      "validation_samples":len(CONDITIONS)*SHOTS,"projected_sampling_and_matching_seconds":projection,
      "elapsed_seconds":time.perf_counter()-start,
      "scope":"fresh independent train/validation split; BP+LSD is a same-validation stronger comparator; development only"}
    (HERE/"fast_flagged_logistic_replication_results.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({"macro_ler":macro,"logistic_reduction":reduction,"BP_LSD_reduction":bp_reduction,
      "logistic_time_ratio":time_ratio,"gate":out["logistic_advancement_gate_passed"],
      "per_condition":percell,"elapsed":out["elapsed_seconds"]},indent=2))

if __name__=="__main__":main()
