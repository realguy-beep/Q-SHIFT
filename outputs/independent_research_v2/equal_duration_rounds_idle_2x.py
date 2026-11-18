"""Fresh robustness challenge with only data-idle Pauli p doubled to .006."""
from __future__ import annotations

import json, math, time
from pathlib import Path

import numpy as np
import stim

from equal_duration_rounds import (
    CONDITIONS, MAIN_SHOTS, PREFLIGHT_SHOTS, circuit_for, make_matching,
    resources, terminal_data_targets, phase2b_build_circuit,
    GATE_P, MEAS_P, BIAS_RATIO,
)

HERE=Path(__file__).resolve().parent
PREFLIGHT_SEEDS=(2026113901,2026113902,2026113903,2026113904)
MAIN_SEEDS=(2026113911,2026113912,2026113913,2026113914)
ARMS=("three_rounds_plus_idle","five_active_rounds")
IDLE_P=.006


def wilson(k,n):
    z=1.959963984540054;p=k/n;den=1+z*z/n;c=(p+z*z/(2*n))/den
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [c-h,c+h]


def main():
    start=time.perf_counter();models={};pf=[];idx=0
    for basis,regime in CONDITIONS:
        for arm in ARMS:
            circuit,extra=circuit_for(arm,basis,regime,idle_p=IDLE_P)
            expected=24 if arm==ARMS[0] else 40
            if (circuit.num_qubits,circuit.num_detectors,circuit.num_observables)!=(26,expected,1):
                raise RuntimeError("unexpected circuit geometry")
            ref=phase2b_build_circuit(basis,regime,distance=3,rounds=5,
                gate_p=GATE_P,measurement_p=MEAS_P,bias_ratio=BIAS_RATIO)
            if terminal_data_targets(circuit)!=terminal_data_targets(ref):
                raise RuntimeError("terminal readout target mismatch")
            if arm==ARMS[1] and str(circuit)!=str(ref):
                raise RuntimeError("five-round baseline differs from source")
            if arm==ARMS[0] and extra["idle_total_error_probability"]!=IDLE_P:
                raise RuntimeError("idle probability is not the fixed twofold stress")
            decoder=make_matching(circuit)
            clean=stim.Circuit()
            for ins in circuit.flattened():
                if ins.name not in ("PAULI_CHANNEL_1","PAULI_CHANNEL_2","X_ERROR","Z_ERROR"):
                    clean.append(ins.name,ins.targets_copy(),ins.gate_args_copy())
            nd,no=clean.compile_detector_sampler(seed=1).sample(20,separate_observables=True)
            if nd.any() or no.any(): raise RuntimeError("noiseless circuit check failed")
            ts=time.perf_counter()
            det,obs=circuit.compile_detector_sampler(seed=PREFLIGHT_SEEDS[idx]).sample(
                PREFLIGHT_SHOTS,separate_observables=True)
            st=time.perf_counter()-ts
            ts=time.perf_counter()
            pred=np.asarray(decoder.decode_batch(det,enable_correlations=True),dtype=bool).reshape(PREFLIGHT_SHOTS,-1)
            dt=time.perf_counter()-ts
            scalar=np.asarray([decoder.decode(x,enable_correlations=True) for x in det[:20]],dtype=bool).reshape(20,-1)
            if pred.shape!=obs.shape or not np.array_equal(pred[:20],scalar):
                raise RuntimeError("decoder shape/scalar-batch check failed")
            models[(basis,regime,arm)]=(circuit,decoder,extra)
            pf.append({"basis":basis,"regime":regime,"arm":arm,"resources":resources(circuit),
                       "extra":extra,"seed":PREFLIGHT_SEEDS[idx],"sample_seconds":st,
                       "decode_seconds":dt})
            idx+=1
    projection=sum((x["sample_seconds"]+x["decode_seconds"])*MAIN_SHOTS/PREFLIGHT_SHOTS for x in pf)
    if projection>300: raise RuntimeError(f"five-minute projection gate failed: {projection:.2f}s")

    rows=[];idx=0
    for basis,regime in CONDITIONS:
        cells={}
        for arm in ARMS:
            circuit,decoder,extra=models[(basis,regime,arm)]
            det,obs=circuit.compile_detector_sampler(seed=MAIN_SEEDS[idx]).sample(
                MAIN_SHOTS,separate_observables=True)
            pred=np.asarray(decoder.decode_batch(det,enable_correlations=True),dtype=bool).reshape(MAIN_SHOTS,-1)
            errors=int(np.count_nonzero(np.any(pred!=obs,axis=1)))
            cells[arm]={"errors":errors,"shots":MAIN_SHOTS,"ler":errors/MAIN_SHOTS,
                        "wilson_95":wilson(errors,MAIN_SHOTS),"seed":MAIN_SEEDS[idx]}
            idx+=1
        a,b=cells[ARMS[0]],cells[ARMS[1]];rr=a["ler"]/b["ler"]
        se=math.sqrt(1/a["errors"]+1/b["errors"])
        rows.append({"memory_basis":basis,"regime":regime,ARMS[0]:a,ARMS[1]:b,
                     "rate_ratio_three_idle_over_five_active":rr,
                     "rate_ratio_log_normal_95_ci":[math.exp(math.log(rr)-1.95996398454*se),
                                                     math.exp(math.log(rr)+1.95996398454*se)]})
    ratios=[r["rate_ratio_three_idle_over_five_active"] for r in rows]
    macro=float(np.mean(ratios))
    result={"status":"equal_duration_rounds_idle_2x_robustness",
            "idle_probability_per_cycle":IDLE_P,"active_gate_and_measurement_p":GATE_P,
            "profiles":rows,"preflight":pf,"equal_weight_macro_rate_ratio":macro,
            "directionally_retained":all(x<1 for x in ratios),
            "robustness_gate_passed":macro<=.90 and all(x<1 for x in ratios) and all(x<=1.05 for x in ratios),
            "robustness_gate_definition":"macro RR <= 0.90; both cell point estimates below 1; no cell above 1.05",
            "preflight_samples":400,"main_samples":2*len(CONDITIONS)*MAIN_SHOTS,
            "projected_main_seconds":projection,"elapsed_seconds":time.perf_counter()-start,
            "scope":"single declared twofold idle-rate stress; all comparator/source noise unchanged"}
    (HERE/"equal_duration_rounds_idle_2x_results.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"macro_rr":macro,
                      "directional":result["directionally_retained"],
                      "gate":result["robustness_gate_passed"],
                      "profiles":[{"basis":r["memory_basis"],"rr":r["rate_ratio_three_idle_over_five_active"],
                                   "ci":r["rate_ratio_log_normal_95_ci"]} for r in rows],
                      "elapsed":result["elapsed_seconds"]},indent=2))


if __name__=="__main__":main()
