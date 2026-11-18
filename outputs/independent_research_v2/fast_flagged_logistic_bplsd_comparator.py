"""Same-validation-stream comparison of learned and BP+LSD flagged policies."""
from __future__ import annotations
import json,sys,time,math
from pathlib import Path
import numpy as np
from ldpc import BpLsdDecoder
from scipy.stats import binomtest

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/"outputs"/"independent_research_v1"))
from bplsd_feasibility import model_matrices
from fast_flagged_logistic import CONDITIONS,build_circuit,make_models,features,VALIDATION_SEEDS,SHOTS,DEM_THRESHOLD

def summary(a,b):
    d=b.astype(np.int8)-a.astype(np.int8);delta=float(d.mean());se=float(d.std(ddof=1)/np.sqrt(len(d)))
    ao=int(np.count_nonzero(a&~b));bo=int(np.count_nonzero(b&~a));disc=ao+bo
    return {"delta_second_minus_first":delta,"normal_95_ci":[delta-1.95996398454*se,delta+1.95996398454*se],
            "first_only_failures":ao,"second_only_failures":bo,
            "mcnemar_exact_two_sided":float(binomtest(ao,disc,.5).pvalue) if disc else 1.}

def main():
    saved=json.load(open(HERE/"fast_flagged_logistic_results.json"))
    tstart=time.perf_counter();rows=[]
    for i,((basis,regime),seed) in enumerate(zip(CONDITIONS,VALIDATION_SEEDS,strict=True)):
        model=saved["trained_models"][i];coef=np.asarray(model["coefficients"],dtype=np.float64);bias=model["intercept"]
        circuit=build_circuit(basis,regime)
        dem=circuit.detector_error_model(decompose_errors=True,approximate_disjoint_errors=DEM_THRESHOLD)
        corr,plain=make_models(circuit)
        det,obs=circuit.compile_detector_sampler(seed=seed).sample(shots=SHOTS,separate_observables=True)
        cp=np.asarray(corr.decode_batch(det,enable_correlations=True),dtype=bool).reshape(SHOTS,-1)
        pp=np.asarray(plain.decode_batch(det,enable_correlations=False),dtype=bool).reshape(SHOTS,-1)
        x,flags=features(det,cp,pp)
        logit=cp.copy();logit[flags]=(x[flags]@coef+bias>=0).reshape(-1,1)
        n_det,n_obs,probs=model_matrices(dem)
        lsd=BpLsdDecoder(pcm=n_det,error_channel=probs.tolist(),max_iter=200,
            bp_method="minimum_sum",ms_scaling_factor=.9,lsd_order=0,
            lsd_method="LSD_CS",bits_per_step=1)
        hybrid=cp.copy();lsd_time=0.;invalid=0
        for j in np.flatnonzero(flags):
            t0=time.perf_counter();fault=np.asarray(lsd.decode(det[j]),dtype=np.uint8).reshape(-1);lsd_time+=time.perf_counter()-t0
            valid=fault.shape==(n_det.shape[1],) and np.array_equal((n_det@fault)&1,det[j])
            invalid+=not valid
            hybrid[j]=((n_obs@fault)&1).astype(bool) if valid else True
        corr_fail=np.any(cp!=obs,axis=1);logit_fail=np.any(logit!=obs,axis=1);lsd_fail=np.any(hybrid!=obs,axis=1)
        expected=saved["conditions"][i]
        if int(corr_fail.sum())!=expected["failures"]["correlated"] or int(logit_fail.sum())!=expected["failures"]["hybrid"] or int(flags.sum())!=expected["flagged"]:
            raise RuntimeError("replayed validation stream does not match saved logistic evidence")
        rows.append({"memory_basis":basis,"regime":regime,"validation_seed":seed,"shots":SHOTS,
          "flagged":int(flags.sum()),"correlated_failures":int(corr_fail.sum()),
          "logistic_hybrid_failures":int(logit_fail.sum()),"bplsd_hybrid_failures":int(lsd_fail.sum()),
          "invalid_bplsd_syndromes":invalid,
          "ler":{"correlated":float(corr_fail.mean()),"logistic_hybrid":float(logit_fail.mean()),"bplsd_hybrid":float(lsd_fail.mean())},
          "paired_logistic_vs_correlated":summary(corr_fail,logit_fail),
          "paired_bplsd_vs_correlated":summary(corr_fail,lsd_fail),
          "paired_bplsd_vs_logistic":summary(logit_fail,lsd_fail),
          "bplsd_flagged_decode_seconds":lsd_time})
    corr_macro=float(np.mean([r["ler"]["correlated"] for r in rows]))
    lr_macro=float(np.mean([r["ler"]["logistic_hybrid"] for r in rows]))
    bp_macro=float(np.mean([r["ler"]["bplsd_hybrid"] for r in rows]))
    out={"status":"same_validation_stream_stronger_comparator_reanalysis","conditions":rows,
      "macro_ler":{"correlated":corr_macro,"logistic_hybrid":lr_macro,"bplsd_hybrid":bp_macro},
      "relative_reduction_vs_correlated":{"logistic":1-lr_macro/corr_macro,"bplsd":1-bp_macro/corr_macro},
      "bplsd_reanalysis_runtime_seconds":time.perf_counter()-tstart,
      "new_stochastic_samples":0,
      "scope":"replays exactly the held-out logistic validation seeds; labels used only for scoring, no model refit"}
    (HERE/"fast_flagged_logistic_bplsd_comparator.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({"macro_ler":out["macro_ler"],"reductions":out["relative_reduction_vs_correlated"],
                      "invalid":sum(r["invalid_bplsd_syndromes"] for r in rows)},indent=2))

if __name__=="__main__":main()
