"""Z-aligned d5 equal-duration round schedule screen."""
from __future__ import annotations

import json, math, sys, time
from pathlib import Path

import numpy as np
import pymatching
import stim

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/"outputs"/"phase2b_pauli_bias"))
sys.path.insert(0,str(REPO/"outputs"/"independent_research_v1"))
from noise_model import one_qubit_probabilities
from code_distance_scaling import build_scaled_circuit

PREFLIGHT_SEEDS=(2026114001,2026114002)
MAIN_SEEDS=(2026114011,2026114012)
PREFLIGHT_SHOTS=10_000
MAIN_SHOTS=1_000_000
BASE_P=.003
BIAS=10.
THRESHOLD=.0018


def idle_arm(active_rounds: int = 5, idle_cycles: int = 4) -> tuple[stim.Circuit,dict]:
    source=build_scaled_circuit("z","z_biased",5,active_rounds).flattened()
    p1=one_qubit_probabilities("z_biased",BASE_P,BIAS)
    out=stim.Circuit(); data=None; inserted=False
    for inst in source:
        if inst.name in ("M","MX","MY"):
            data=list(inst.targets_copy())
            if len(data)!=25: raise RuntimeError(f"expected 25 terminal data qubits, got {len(data)}")
            for k in range(idle_cycles):
                out.append("PAULI_CHANNEL_1",data,p1)
                if k<idle_cycles-1: out.append("TICK")
            inserted=True
        out.append(inst.name,inst.targets_copy(),inst.gate_args_copy())
    if not inserted: raise RuntimeError("terminal measurement missing")
    return out,{"active_rounds":active_rounds,"idle_cycles":idle_cycles,"idle_data_qubits_per_cycle":25,
                "idle_channel_targets":25*idle_cycles,"idle_probability_per_data_qubit_per_cycle":float(sum(p1)),
                "idle_pauli_probabilities_XYZ":list(p1),
                "terminal_data_qubits":[int(t.value) for t in data]}


def arm_circuit(arm:str)->tuple[stim.Circuit,dict]:
    if arm=="five_rounds_plus_idle": return idle_arm()
    if arm=="nine_active_rounds":
        c=build_scaled_circuit("z","z_biased",5,9)
        return c,{"active_rounds":9,"idle_cycles":0,"idle_data_qubits_per_cycle":0,
                  "idle_channel_targets":0,"terminal_data_qubits":[]}
    raise ValueError(arm)


def terminal_data(c):
    ms=[i for i in c.flattened() if i.name in ("M","MX","MY")]
    if len(ms)!=1:return None
    return [int(t.value) for t in ms[0].targets_copy()]


def make_decoder(c):
    dem=c.detector_error_model(decompose_errors=True,approximate_disjoint_errors=THRESHOLD)
    return pymatching.Matching.from_detector_error_model(dem,enable_correlations=True)


def resources(c):
    flat=c.flattened()
    return {"qubits":int(c.num_qubits),"detectors":int(c.num_detectors),
            "observables":int(c.num_observables),
            "two_qubit_pair_sites":sum(len(i.targets_copy())//2 for i in flat if i.name=="PAULI_CHANNEL_2"),
            "one_qubit_pauli_targets":sum(len(i.targets_copy()) for i in flat if i.name=="PAULI_CHANNEL_1")}


def wilson(k,n):
    z=1.959963984540054;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [c-h,c+h]


def main():
    start=time.perf_counter(); models={}; pre=[]
    for ix,arm in enumerate(("five_rounds_plus_idle","nine_active_rounds")):
        c,extra=arm_circuit(arm)
        exp_det=120 if arm=="five_rounds_plus_idle" else 216
        if (c.num_qubits,c.num_detectors,c.num_observables)!=(64,exp_det,1):
            raise RuntimeError("d5 circuit geometry mismatch")
        ref=build_scaled_circuit("z","z_biased",5,9)
        if terminal_data(c)!=terminal_data(ref): raise RuntimeError("terminal data targets differ")
        if arm=="nine_active_rounds" and str(c)!=str(ref): raise RuntimeError("nine-round source mismatch")
        if arm=="five_rounds_plus_idle" and extra["idle_channel_targets"]!=100:
            raise RuntimeError("idle target count mismatch")
        clean=stim.Circuit()
        for inst in c.flattened():
            if inst.name not in ("PAULI_CHANNEL_1","PAULI_CHANNEL_2","X_ERROR","Z_ERROR"):
                clean.append(inst.name,inst.targets_copy(),inst.gate_args_copy())
        nd,no=clean.compile_detector_sampler(seed=1).sample(50,separate_observables=True)
        if nd.any() or no.any(): raise RuntimeError("noiseless check failed")
        decoder=make_decoder(c)
        t0=time.perf_counter()
        det,obs=c.compile_detector_sampler(seed=PREFLIGHT_SEEDS[ix]).sample(PREFLIGHT_SHOTS,separate_observables=True)
        sample_time=time.perf_counter()-t0
        t0=time.perf_counter(); batch=np.asarray(decoder.decode_batch(det,enable_correlations=True),dtype=bool).reshape(PREFLIGHT_SHOTS,-1)
        decode_time=time.perf_counter()-t0
        scalar=np.asarray([decoder.decode(s,enable_correlations=True) for s in det[:50]],dtype=bool).reshape(50,-1)
        if batch.shape!=obs.shape or not np.array_equal(batch[:50],scalar): raise RuntimeError("scalar/batch mismatch")
        models[arm]=(c,decoder,extra)
        pre.append({"arm":arm,"seed":PREFLIGHT_SEEDS[ix],"shots":PREFLIGHT_SHOTS,
                    "resources":resources(c),"extra":extra,"sample_seconds":sample_time,
                    "decode_seconds":decode_time})
    projected=sum((x["sample_seconds"]+x["decode_seconds"])*MAIN_SHOTS/PREFLIGHT_SHOTS for x in pre)
    if projected>300: raise RuntimeError(f"runtime projection over cap: {projected:.2f}s")

    arms={};
    for ix,arm in enumerate(("five_rounds_plus_idle","nine_active_rounds")):
        c,decoder,extra=models[arm]
        det,obs=c.compile_detector_sampler(seed=MAIN_SEEDS[ix]).sample(MAIN_SHOTS,separate_observables=True)
        pred=np.asarray(decoder.decode_batch(det,enable_correlations=True),dtype=bool).reshape(MAIN_SHOTS,-1)
        errors=int(np.count_nonzero(np.any(pred!=obs,axis=1)))
        arms[arm]={"errors":errors,"shots":MAIN_SHOTS,"ler":errors/MAIN_SHOTS,
                   "wilson_95":wilson(errors,MAIN_SHOTS),"seed":MAIN_SEEDS[ix],
                   "resources":resources(c),"extra":extra}
    a,b=arms["five_rounds_plus_idle"],arms["nine_active_rounds"]
    rr=a["ler"]/b["ler"];se=math.sqrt(1/a["errors"]+1/b["errors"])
    result={"status":"equal_duration_d5_development","condition":{"memory_basis":"z","regime":"z_biased"},
            "arms":arms,"rate_ratio_five_active_plus_idle_over_nine_active":rr,
            "rate_ratio_log_normal_95_ci":[math.exp(math.log(rr)-1.95996398454*se),math.exp(math.log(rr)+1.95996398454*se)],
            "preflight":pre,"preflight_samples":2*PREFLIGHT_SHOTS,"main_samples":2*MAIN_SHOTS,
            "projected_main_seconds":projected,"elapsed_seconds":time.perf_counter()-start,
            "scope":"single aligned d5 memory workload; p=.003 biased data-idle assumption; development only"}
    (HERE/"equal_duration_d5_results.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"candidate_errors":a["errors"],"baseline_errors":b["errors"],
                      "rr":rr,"ci":result["rate_ratio_log_normal_95_ci"],"projection":projected,
                      "elapsed":result["elapsed_seconds"]},indent=2))


if __name__=="__main__":main()
