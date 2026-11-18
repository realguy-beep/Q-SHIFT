"""Route only correlation-vs-ordinary matching disagreements to fixed BP+LSD."""
from __future__ import annotations

import json, math, resource, sys, time
from pathlib import Path
import numpy as np
import pymatching, stim
from ldpc import BpLsdDecoder
from scipy.stats import binomtest

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
PHASE2B=REPO/"outputs"/"phase2b_pauli_bias"
sys.path.insert(0,str(PHASE2B))
sys.path.insert(0,str(REPO/"outputs"/"independent_research_v1"))
from noise_model import MEMORY_BASES,REGIMES,build_circuit
from bplsd_feasibility import model_matrices

CONDITIONS=tuple((b,r) for b in MEMORY_BASES for r in REGIMES)
PREFLIGHT_SEEDS=(2026114201,2026114202,2026114203,2026114204,2026114205,2026114206)
MAIN_SEEDS=(2026114211,2026114212,2026114213,2026114214,2026114215,2026114216)
PREFLIGHT_SHOTS=2000
MAIN_SHOTS=100_000
THRESHOLD=.0018


def decoder_set(circuit):
    dem=circuit.detector_error_model(decompose_errors=True,approximate_disjoint_errors=THRESHOLD)
    corr=pymatching.Matching.from_detector_error_model(dem,enable_correlations=True)
    plain=pymatching.Matching.from_detector_error_model(dem,enable_correlations=False)
    h,l,probs=model_matrices(dem)
    lsd=BpLsdDecoder(pcm=h,error_channel=probs.tolist(),max_iter=200,
        bp_method="minimum_sum",ms_scaling_factor=.9,lsd_order=0,
        lsd_method="LSD_CS",bits_per_step=1)
    zero=np.zeros(h.shape[0],dtype=np.uint8)
    first=np.asarray(lsd.decode(zero),dtype=np.uint8).reshape(-1)
    second=np.asarray(lsd.decode(zero),dtype=np.uint8).reshape(-1)
    if first.shape!=(h.shape[1],) or not np.array_equal(first,second):
        raise RuntimeError("BP+LSD zero-syndrome determinism/shape failure")
    return dem,corr,plain,lsd,h,l


def wilson(k,n):
    z=1.959963984540054;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [c-h,c+h]


def evaluate(circuit,decoders,shots,seed,save_predictions=False):
    dem,corr,plain,lsd,h,l=decoders
    t0=time.perf_counter()
    det,obs=circuit.compile_detector_sampler(seed=seed).sample(shots=shots,separate_observables=True)
    sample_time=time.perf_counter()-t0
    t0=time.perf_counter();pc=np.asarray(corr.decode_batch(det,enable_correlations=True),dtype=bool).reshape(shots,-1);tc=time.perf_counter()-t0
    t0=time.perf_counter();pp=np.asarray(plain.decode_batch(det,enable_correlations=False),dtype=bool).reshape(shots,-1);tp=time.perf_counter()-t0
    flags=np.any(pc!=pp,axis=1)
    hybrid=pc.copy(); invalid=0; lsd_time=0.
    for i in np.flatnonzero(flags):
        t0=time.perf_counter(); f=np.asarray(lsd.decode(det[i]),dtype=np.uint8).reshape(-1);lsd_time+=time.perf_counter()-t0
        syndrome_ok=f.shape==(h.shape[1],) and np.array_equal((h@f)&1,det[i])
        invalid+=not syndrome_ok
        if syndrome_ok:
            hybrid[i]=((l@f)&1).astype(bool)
        else:
            hybrid[i]=True # invalid syndrome estimate is deliberately scored as an error
    corr_fail=np.any(pc!=obs,axis=1)
    plain_fail=np.any(pp!=obs,axis=1)
    hybrid_fail=np.any(hybrid!=obs,axis=1)
    discord_a=int(np.count_nonzero(corr_fail & ~hybrid_fail))
    discord_b=int(np.count_nonzero(hybrid_fail & ~corr_fail))
    d=hybrid_fail.astype(np.int8)-corr_fail.astype(np.int8)
    delta=float(d.mean());se=float(d.std(ddof=1)/math.sqrt(shots))
    return {"shots":shots,"seed":seed,"flags":int(flags.sum()),"flag_rate":float(flags.mean()),
        "flagged_samples":int(flags.sum()),"invalid_lsd_syndromes":int(invalid),
        "failures":{"correlation_matching":int(corr_fail.sum()),"plain_matching":int(plain_fail.sum()),"hybrid":int(hybrid_fail.sum())},
        "ler":{"correlation_matching":float(corr_fail.mean()),"plain_matching":float(plain_fail.mean()),"hybrid":float(hybrid_fail.mean())},
        "hybrid_flagged_failures":int(hybrid_fail[flags].sum()),"hybrid_unflagged_failures":int(hybrid_fail[~flags].sum()),
        "paired_hybrid_minus_correlation_delta":delta,
        "paired_normal_95_ci":[delta-1.95996398454*se,delta+1.95996398454*se],
        "correlation_only_failures":discord_a,"hybrid_only_failures":discord_b,
        "mcnemar_exact_two_sided":float(binomtest(discord_a,discord_a+discord_b,.5).pvalue) if discord_a+discord_b else 1.,
        "decode_seconds":{"correlation_batch":tc,"plain_batch":tp,"lsd_flagged_only":lsd_time},
        "sample_seconds":sample_time,
        "hybrid_total_decode_seconds":tc+tp+lsd_time,
        "hybrid_to_correlation_decode_time_ratio":(tc+tp+lsd_time)/tc if tc else None,
        "max_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def main():
    start=time.perf_counter();prepared=[]; pre=[]
    for (basis,regime),seed in zip(CONDITIONS,PREFLIGHT_SEEDS,strict=True):
        circuit=build_circuit(basis,regime)
        if (circuit.num_qubits,circuit.num_detectors,circuit.num_observables)!=(26,40,1):
            raise RuntimeError("circuit shape mismatch")
        dem,corr,plain,lsd,h,l=decoder_set(circuit)
        # Validate noiseless references and both matching APIs without outcomes.
        clean=stim.Circuit()
        for ins in circuit.flattened():
            if ins.name not in ("PAULI_CHANNEL_1","PAULI_CHANNEL_2","X_ERROR","Z_ERROR"):
                clean.append(ins.name,ins.targets_copy(),ins.gate_args_copy())
        nd,no=clean.compile_detector_sampler(seed=1).sample(20,separate_observables=True)
        if nd.any() or no.any():raise RuntimeError("noiseless circuit check failed")
        result=evaluate(circuit,(dem,corr,plain,lsd,h,l),PREFLIGHT_SHOTS,seed)
        prepared.append((circuit,(dem,corr,plain,lsd,h,l)))
        per_shot=(result["sample_seconds"]+
                  result["decode_seconds"]["correlation_batch"]+
                  result["decode_seconds"]["plain_batch"]+
                  result["decode_seconds"]["lsd_flagged_only"])/PREFLIGHT_SHOTS
        projected=per_shot*MAIN_SHOTS
        pre.append({"memory_basis":basis,"regime":regime,"metrics":result,"projected_main_seconds":projected})
    projection=sum(x["projected_main_seconds"] for x in pre)
    if projection>300:
        out={"status":"preflight_runtime_stop","preflight":pre,"projected_total_main_seconds":projection,
             "runtime_cap_seconds":300,"stochastic_samples":len(CONDITIONS)*PREFLIGHT_SHOTS}
        (HERE/"selective_bplsd_escalation_results.json").write_text(json.dumps(out,indent=2)+"\n")
        print(json.dumps({"status":out["status"],"projection":projection}));return
    rows=[]
    for (basis,regime),seed,(circuit,decoders) in zip(CONDITIONS,MAIN_SEEDS,prepared,strict=True):
        row=evaluate(circuit,decoders,MAIN_SHOTS,seed)
        row.update({"memory_basis":basis,"regime":regime})
        rows.append(row)
    base_macro=float(np.mean([r["ler"]["correlation_matching"] for r in rows]))
    hybrid_macro=float(np.mean([r["ler"]["hybrid"] for r in rows]))
    rel=1-hybrid_macro/base_macro if base_macro else 0.
    per_cell_rel=[1-r["ler"]["hybrid"]/r["ler"]["correlation_matching"] if r["ler"]["correlation_matching"] else 0. for r in rows]
    time_ratio=float(np.mean([r["hybrid_to_correlation_decode_time_ratio"] for r in rows]))
    out={"status":"selective_bplsd_escalation_development","conditions":rows,"preflight":pre,
         "macro_ler":{"correlation_matching":base_macro,"hybrid":hybrid_macro},
         "equal_weight_macro_relative_reduction":rel,"per_condition_relative_reductions":per_cell_rel,
         "mean_decode_time_ratio_hybrid_to_correlation":time_ratio,
         "advancement_gate_passed":rel>=.10 and min(per_cell_rel)>=-.05 and time_ratio<2 and all(r["invalid_lsd_syndromes"]==0 for r in rows),
         "ldpc_version":"2.4.1","stim_version":stim.__version__,"pymatching_version":pymatching.__version__,
         "bp_lsd":{"method":"LSD_CS","bp_method":"minimum_sum","ms_scaling_factor":.9,"max_iter":200,"lsd_order":0,"bits_per_step":1},
         "preflight_samples":len(CONDITIONS)*PREFLIGHT_SHOTS,"main_samples":len(CONDITIONS)*MAIN_SHOTS,
         "projected_main_seconds":projection,"elapsed_seconds":time.perf_counter()-start,
         "scope":"development-only selective escalation using decoder disagreement as a fixed syndrome-only flag"}
    (HERE/"selective_bplsd_escalation_results.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({"status":out["status"],"flag_rates":[r["flag_rate"] for r in rows],
                      "macro_ler":out["macro_ler"],"reduction":rel,"time_ratio":time_ratio,
                      "gate":out["advancement_gate_passed"],"elapsed":out["elapsed_seconds"]},indent=2))

if __name__=="__main__":main()
