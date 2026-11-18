"""One targeted d5 schedule: seven active rounds plus two idle cycles."""
from __future__ import annotations
import json, math, time
from pathlib import Path
import numpy as np
import stim
from equal_duration_d5 import (
    idle_arm, build_scaled_circuit, terminal_data, resources, make_decoder, wilson,
    PREFLIGHT_SHOTS, MAIN_SHOTS, THRESHOLD,
)

HERE=Path(__file__).resolve().parent
PREFLIGHT_SEEDS=(2026114101,2026114102)
MAIN_SEEDS=(2026114111,2026114112)

def main():
    start=time.perf_counter(); arms={}; pre=[]
    candidate,extra=idle_arm(active_rounds=7,idle_cycles=2)
    baseline=build_scaled_circuit("z","z_biased",5,9)
    for ix,(name,c) in enumerate((("seven_rounds_plus_idle",candidate),("nine_active_rounds",baseline))):
        expected=168 if ix==0 else 216
        if (c.num_qubits,c.num_detectors,c.num_observables)!=(64,expected,1):
            raise RuntimeError("unexpected d5 circuit geometry")
        if terminal_data(c)!=terminal_data(baseline): raise RuntimeError("terminal data measurement mismatch")
        if ix==1 and str(c)!=str(build_scaled_circuit("z","z_biased",5,9)):
            raise RuntimeError("baseline source-circuit mismatch")
        if ix==0 and (extra["active_rounds"],extra["idle_cycles"],extra["idle_channel_targets"])!=(7,2,50):
            raise RuntimeError("candidate schedule resource mismatch")
        clean=stim.Circuit()
        for ins in c.flattened():
            if ins.name not in ("PAULI_CHANNEL_1","PAULI_CHANNEL_2","X_ERROR","Z_ERROR"):
                clean.append(ins.name,ins.targets_copy(),ins.gate_args_copy())
        nd,no=clean.compile_detector_sampler(seed=1).sample(50,separate_observables=True)
        if nd.any() or no.any(): raise RuntimeError("noiseless check failed")
        dec=make_decoder(c)
        ts=time.perf_counter()
        det,obs=c.compile_detector_sampler(seed=PREFLIGHT_SEEDS[ix]).sample(PREFLIGHT_SHOTS,separate_observables=True)
        sample_s=time.perf_counter()-ts
        ts=time.perf_counter(); pred=np.asarray(dec.decode_batch(det,enable_correlations=True),dtype=bool).reshape(PREFLIGHT_SHOTS,-1)
        decode_s=time.perf_counter()-ts
        scalar=np.asarray([dec.decode(s,enable_correlations=True) for s in det[:50]],dtype=bool).reshape(50,-1)
        if pred.shape!=obs.shape or not np.array_equal(pred[:50],scalar): raise RuntimeError("scalar/batch mismatch")
        arms[name]=(c,dec)
        pre.append({"arm":name,"seed":PREFLIGHT_SEEDS[ix],"sample_seconds":sample_s,
                    "decode_seconds":decode_s,"resources":resources(c)})
    projection=sum((r["sample_seconds"]+r["decode_seconds"])*MAIN_SHOTS/PREFLIGHT_SHOTS for r in pre)
    if projection>300: raise RuntimeError("five-minute runtime gate failed")
    results={}
    for ix,name in enumerate(("seven_rounds_plus_idle","nine_active_rounds")):
        c,dec=arms[name]
        det,obs=c.compile_detector_sampler(seed=MAIN_SEEDS[ix]).sample(MAIN_SHOTS,separate_observables=True)
        pred=np.asarray(dec.decode_batch(det,enable_correlations=True),dtype=bool).reshape(MAIN_SHOTS,-1)
        k=int(np.count_nonzero(np.any(pred!=obs,axis=1)))
        results[name]={"errors":k,"shots":MAIN_SHOTS,"ler":k/MAIN_SHOTS,
                       "wilson_95":wilson(k,MAIN_SHOTS),"seed":MAIN_SEEDS[ix],
                       "resources":resources(c)}
    a,b=results["seven_rounds_plus_idle"],results["nine_active_rounds"]
    rr=a["ler"]/b["ler"];se=math.sqrt(1/a["errors"]+1/b["errors"])
    out={"status":"equal_duration_d5_intermediate_development",
         "condition":{"memory_basis":"z","regime":"z_biased"},"arms":results,
         "candidate_schedule":{"active_rounds":7,"idle_cycles":2,"idle_noise_p":.003,"idle_targets":50},
         "rate_ratio_candidate_over_nine_active":rr,
         "rate_ratio_log_normal_95_ci":[math.exp(math.log(rr)-1.95996398454*se),math.exp(math.log(rr)+1.95996398454*se)],
         "advancement_gate_passed":rr<=.90 and math.exp(math.log(rr)+1.95996398454*se)<1,
         "preflight":pre,"preflight_samples":2*PREFLIGHT_SHOTS,"main_samples":2*MAIN_SHOTS,
         "projected_main_seconds":projection,"elapsed_seconds":time.perf_counter()-start,
         "scope":"single targeted intermediate schedule; d5 Z-aligned simulator development only"}
    (HERE/"equal_duration_d5_intermediate_results.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({"status":out["status"],"candidate_errors":a["errors"],"baseline_errors":b["errors"],
                      "rr":rr,"ci":out["rate_ratio_log_normal_95_ci"],"gate":out["advancement_gate_passed"],
                      "projection":projection,"elapsed":out["elapsed_seconds"]},indent=2))

if __name__=="__main__":main()
