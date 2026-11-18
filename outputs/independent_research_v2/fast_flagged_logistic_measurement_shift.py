"""Apply frozen nominal flagged selectors to fresh measurement-shifted circuits."""
from __future__ import annotations
import json,math,time
from pathlib import Path
import numpy as np
import pymatching
import stim
from scipy.stats import binomtest

from fast_flagged_logistic import CONDITIONS,features,make_models,run_sample,SHOTS as NOMINAL_SHOTS
from fast_flagged_logistic import DEM_THRESHOLD as THRESHOLD
import sys
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/"outputs"/"phase2b_pauli_bias"))
from noise_model import build_circuit

PREFLIGHT_SEEDS=(2026114601,2026114602,2026114603,2026114604,2026114605,2026114606)
MAIN_SEEDS=(2026114611,2026114612,2026114613,2026114614,2026114615,2026114616)
PREFLIGHT_SHOTS=10_000
MAIN_SHOTS=500_000
SHIFTED_MEASUREMENT_P=.006


def wilson(k,n):
    z=1.959963984540054;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [c-h,c+h]


def paired(a,b):
    d=b.astype(np.int8)-a.astype(np.int8);delta=float(d.mean());se=float(d.std(ddof=1)/math.sqrt(len(d)))
    ao=int(np.count_nonzero(a&~b));bo=int(np.count_nonzero(b&~a));n=ao+bo
    return {"delta_second_minus_first":delta,"normal_95_ci":[delta-1.95996398454*se,delta+1.95996398454*se],
            "first_only_failures":ao,"second_only_failures":bo,
            "mcnemar_exact_two_sided":float(binomtest(ao,n,.5).pvalue) if n else 1.}


def main():
    saved=json.load(open(HERE/"fast_flagged_logistic_replication_results.json"))
    start=time.perf_counter();pre=[];models=[]
    for i,((basis,regime),seed) in enumerate(zip(CONDITIONS,PREFLIGHT_SEEDS,strict=True)):
        shifted=build_circuit(basis,regime,gate_p=.003,measurement_p=SHIFTED_MEASUREMENT_P,bias_ratio=10.)
        nominal=build_circuit(basis,regime,gate_p=.003,measurement_p=.003,bias_ratio=10.)
        if (shifted.num_qubits,shifted.num_detectors,shifted.num_observables)!=(26,40,1):raise RuntimeError("shifted geometry mismatch")
        nom_corr,nom_plain=make_models(nominal)
        clean=stim.Circuit()
        for ins in shifted.flattened():
            if ins.name not in ("PAULI_CHANNEL_1","PAULI_CHANNEL_2","X_ERROR","Z_ERROR"):
                clean.append(ins.name,ins.targets_copy(),ins.gate_args_copy())
        nd,no=clean.compile_detector_sampler(seed=1).sample(20,separate_observables=True)
        if nd.any() or no.any():raise RuntimeError("shifted circuit noiseless check failed")
        pdet,pobs=shifted.compile_detector_sampler(seed=seed).sample(PREFLIGHT_SHOTS,separate_observables=True)
        cb=np.asarray(nom_corr.decode_batch(pdet,enable_correlations=True),dtype=bool).reshape(PREFLIGHT_SHOTS,-1)
        pb=np.asarray(nom_plain.decode_batch(pdet,enable_correlations=False),dtype=bool).reshape(PREFLIGHT_SHOTS,-1)
        cs=np.asarray([nom_corr.decode(v,enable_correlations=True) for v in pdet[:20]],dtype=bool).reshape(20,-1)
        ps=np.asarray([nom_plain.decode(v,enable_correlations=False) for v in pdet[:20]],dtype=bool).reshape(20,-1)
        if not np.array_equal(cs,cb[:20]) or not np.array_equal(ps,pb[:20]) or cb.shape!=pobs.shape:
            raise RuntimeError("nominal matcher scalar/batch mismatch under shifted input")
        actual_dem=shifted.detector_error_model(decompose_errors=True,approximate_disjoint_errors=THRESHOLD)
        actual_corr=pymatching.Matching.from_detector_error_model(actual_dem,enable_correlations=True)
        row=run_sample(shifted,(nom_corr,nom_plain),PREFLIGHT_SHOTS,seed,
                       coef=np.asarray(saved["trained_models"][i]["coefficients"]),
                       intercept=saved["trained_models"][i]["intercept"],labels=True)
        # Conservatively budget an additional correlated decode pass for the oracle diagnostic.
        projection=(row["sample_seconds"]+2*row["corr_seconds"]+row["plain_seconds"]+
                    row["classifier_seconds"])*MAIN_SHOTS/PREFLIGHT_SHOTS
        pre.append({"basis":basis,"regime":regime,"metrics":row,"projected_seconds":projection})
        models.append((shifted,nom_corr,nom_plain,actual_corr,saved["trained_models"][i]))
    total_projection=sum(p["projected_seconds"] for p in pre)
    if total_projection>300:raise RuntimeError("runtime projection exceeded five-minute cap")

    rows=[]
    for i,((basis,regime),seed,(c,nc,np_,oracle,m)) in enumerate(zip(CONDITIONS,MAIN_SEEDS,models,strict=True)):
        det,obs=c.compile_detector_sampler(seed=seed).sample(MAIN_SHOTS,separate_observables=True)
        t0=time.perf_counter();cp=np.asarray(nc.decode_batch(det,enable_correlations=True),dtype=bool).reshape(MAIN_SHOTS,-1);ct=time.perf_counter()-t0
        t0=time.perf_counter();pp=np.asarray(np_.decode_batch(det,enable_correlations=False),dtype=bool).reshape(MAIN_SHOTS,-1);pt=time.perf_counter()-t0
        x,flag=features(det,cp,pp);co=np.asarray(m["coefficients"],dtype=np.float64);bias=m["intercept"]
        pred=cp.copy();t0=time.perf_counter()
        if flag.any():pred[flag]=(x[flag]@co+bias>=0).reshape(-1,1)
        lt=time.perf_counter()-t0
        t0=time.perf_counter();op=np.asarray(oracle.decode_batch(det,enable_correlations=True),dtype=bool).reshape(MAIN_SHOTS,-1);ot=time.perf_counter()-t0
        cf=np.any(cp!=obs,axis=1);pf=np.any(pp!=obs,axis=1);lf=np.any(pred!=obs,axis=1);of=np.any(op!=obs,axis=1)
        # Verify the frozen selector replay matches the saved nominal feature/model behavior only by shape;
        # shifted noise intentionally changes outcomes and cannot match the nominal validation counts.
        rows.append({"memory_basis":basis,"regime":regime,"seed":seed,"shots":MAIN_SHOTS,
          "flagged":int(flag.sum()),"flag_rate":float(flag.mean()),
          "failures":{"nominal_correlated":int(cf.sum()),"nominal_ordinary":int(pf.sum()),
                      "frozen_logistic":int(lf.sum()),"actual_profile_matcher_diagnostic":int(of.sum())},
          "ler":{"nominal_correlated":float(cf.mean()),"nominal_ordinary":float(pf.mean()),
                 "frozen_logistic":float(lf.mean()),"actual_profile_matcher_diagnostic":float(of.mean())},
          "wilson_95":{"nominal_correlated":wilson(int(cf.sum()),MAIN_SHOTS),"frozen_logistic":wilson(int(lf.sum()),MAIN_SHOTS),
                       "actual_profile_matcher_diagnostic":wilson(int(of.sum()),MAIN_SHOTS)},
          "paired_logistic_minus_nominal_correlated":paired(cf,lf),
          "paired_actual_oracle_minus_nominal_correlated":paired(cf,of),
          "timing":{"nominal_correlated":ct,"nominal_ordinary_flag":pt,"frozen_classifier":lt,"actual_oracle":ot},
          "frozen_policy_time_ratio":(ct+pt+lt)/ct})
    base=float(np.mean([r["ler"]["nominal_correlated"] for r in rows]))
    candidate=float(np.mean([r["ler"]["frozen_logistic"] for r in rows]))
    oracle=float(np.mean([r["ler"]["actual_profile_matcher_diagnostic"] for r in rows]))
    rel=1-candidate/base;percell=[1-r["ler"]["frozen_logistic"]/r["ler"]["nominal_correlated"] for r in rows]
    tr=float(np.mean([r["frozen_policy_time_ratio"] for r in rows]))
    out={"status":"fast_flagged_logistic_measurement_shift","measurement_p":SHIFTED_MEASUREMENT_P,
      "gate_p":.003,"frozen_models":"trained on nominal p_measure=.003; no shift retraining",
      "conditions":rows,"preflight":pre,
      "macro_ler":{"nominal_correlated":base,"frozen_logistic":candidate,"actual_profile_matcher_diagnostic":oracle},
      "macro_relative_reduction_frozen_selector":rel,"per_condition_relative_reductions":percell,
      "mean_frozen_policy_time_ratio":tr,
      "advancement_gate_passed":rel>=.10 and min(percell)>=-.05 and tr<2,
      "preflight_samples":len(CONDITIONS)*PREFLIGHT_SHOTS,"main_samples":len(CONDITIONS)*MAIN_SHOTS,
      "projected_total_main_seconds":total_projection,"elapsed_seconds":time.perf_counter()-start,
      "scope":"frozen nominal selector and nominal matchers under measurement composition shift; actual-profile matcher is a diagnostic, not an optimality bound"}
    (HERE/"fast_flagged_logistic_measurement_shift_results.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({"macro_ler":out["macro_ler"],"reduction":rel,"time_ratio":tr,
                      "gate":out["advancement_gate_passed"],"per_cell":percell,
                      "elapsed":out["elapsed_seconds"]},indent=2))

if __name__=="__main__":main()
