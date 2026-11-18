"""Fresh-seed challenge to the equal-duration rounds development result."""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np
import stim

from equal_duration_rounds import (
    CONDITIONS, MAIN_SHOTS, PREFLIGHT_SHOTS, circuit_for, make_matching,
    resources, terminal_data_targets, phase2b_build_circuit,
    GATE_P, MEAS_P, BIAS_RATIO,
)

HERE = Path(__file__).resolve().parent
PREFLIGHT_SEEDS = (2026113801, 2026113802, 2026113803, 2026113804)
MAIN_SEEDS = (2026113811, 2026113812, 2026113813, 2026113814)
ARMS = ("three_rounds_plus_idle", "five_active_rounds")


def wilson(k: int, n: int) -> list[float]:
    z=1.959963984540054; p=k/n; den=1+z*z/n
    c=(p+z*z/(2*n))/den
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [c-h,c+h]


def main() -> None:
    start=time.perf_counter(); models={}; configs=[]; idx=0
    for basis,regime in CONDITIONS:
        for arm in ARMS:
            circuit,extra=circuit_for(arm,basis,regime)
            expected=24 if arm==ARMS[0] else 40
            if (circuit.num_qubits,circuit.num_detectors,circuit.num_observables)!=(26,expected,1):
                raise RuntimeError("circuit geometry mismatch")
            reference=phase2b_build_circuit(basis,regime,distance=3,rounds=5,
                gate_p=GATE_P,measurement_p=MEAS_P,bias_ratio=BIAS_RATIO)
            if terminal_data_targets(circuit)!=terminal_data_targets(reference):
                raise RuntimeError("terminal readout target mismatch")
            if arm==ARMS[1] and str(circuit)!=str(reference):
                raise RuntimeError("five-round source builder mismatch")
            dec=make_matching(circuit)
            clean=stim.Circuit()
            for ins in circuit.flattened():
                if ins.name not in ("PAULI_CHANNEL_1","PAULI_CHANNEL_2","X_ERROR","Z_ERROR"):
                    clean.append(ins.name,ins.targets_copy(),ins.gate_args_copy())
            nd,no=clean.compile_detector_sampler(seed=1).sample(20,separate_observables=True)
            if nd.any() or no.any(): raise RuntimeError("noiseless check failed")
            sample_start=time.perf_counter()
            det,obs=circuit.compile_detector_sampler(seed=PREFLIGHT_SEEDS[idx]).sample(
                PREFLIGHT_SHOTS,separate_observables=True)
            sample_time=time.perf_counter()-sample_start
            t0=time.perf_counter(); batch=np.asarray(dec.decode_batch(det,enable_correlations=True),dtype=bool).reshape(PREFLIGHT_SHOTS,-1)
            decode_time=time.perf_counter()-t0
            scalar=np.asarray([dec.decode(x,enable_correlations=True) for x in det[:20]],dtype=bool).reshape(20,-1)
            if not np.array_equal(batch[:20],scalar) or batch.shape!=obs.shape:
                raise RuntimeError("scalar/batch decoder mismatch")
            models[(basis,regime,arm)]=(circuit,dec,extra)
            configs.append({"basis":basis,"regime":regime,"arm":arm,
                            "resources":resources(circuit),"extra":extra,
                            "preflight_seed":PREFLIGHT_SEEDS[idx],"preflight_shots":PREFLIGHT_SHOTS,
                            "preflight_decode_seconds":decode_time,
                            "preflight_sample_seconds":sample_time})
            idx+=1
    projection=sum((x["preflight_decode_seconds"]+x["preflight_sample_seconds"])*MAIN_SHOTS/PREFLIGHT_SHOTS for x in configs)
    if projection>300: raise RuntimeError(f"runtime gate failed: {projection:.1f}s")

    results=[];idx=0
    for basis,regime in CONDITIONS:
        cell={}
        for arm in ARMS:
            circuit,dec,extra=models[(basis,regime,arm)]
            det,obs=circuit.compile_detector_sampler(seed=MAIN_SEEDS[idx]).sample(
                MAIN_SHOTS,separate_observables=True)
            pred=np.asarray(dec.decode_batch(det,enable_correlations=True),dtype=bool).reshape(MAIN_SHOTS,-1)
            errors=int(np.count_nonzero(np.any(pred!=obs,axis=1)))
            cell[arm]={"errors":errors,"shots":MAIN_SHOTS,"ler":errors/MAIN_SHOTS,
                       "wilson_95":wilson(errors,MAIN_SHOTS),"seed":MAIN_SEEDS[idx]}
            idx+=1
        ca=cell[ARMS[0]];cb=cell[ARMS[1]]; rr=ca["ler"]/cb["ler"]
        rr_se=math.sqrt(1/ca["errors"]+1/cb["errors"])
        cell_result={"memory_basis":basis,"regime":regime,ARMS[0]:ca,ARMS[1]:cb,
                     "rate_ratio_three_idle_over_five_active":rr,
                     "rate_ratio_log_normal_95_ci":[math.exp(math.log(rr)-1.95996398454*rr_se),
                                                     math.exp(math.log(rr)+1.95996398454*rr_se)]}
        results.append(cell_result)
    ratios=[r["rate_ratio_three_idle_over_five_active"] for r in results]
    macro=float(np.mean(ratios))
    out={"status":"equal_duration_rounds_independent_replication",
         "conditions":results,"preflight_conditions":configs,
         "equal_weight_macro_rate_ratio":macro,
         "directionally_replicated":all(x<1 for x in ratios) and macro<1,
         "same_positive_gate_replicated":macro<=.90 and all(x<=1.05 for x in ratios),
         "preflight_samples":400,"main_samples":2*len(CONDITIONS)*MAIN_SHOTS,
         "projected_decode_seconds":projection,"elapsed_seconds":time.perf_counter()-start,
         "scope":"fresh-seed independent development replication under the same assumed idle channel"}
    (HERE/"equal_duration_rounds_replication_results.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({"status":out["status"],"macro_rr":macro,
                      "directional":out["directionally_replicated"],
                      "same_gate":out["same_positive_gate_replicated"],
                      "conditions":[{k:r[k] for k in ("memory_basis","rate_ratio_three_idle_over_five_active","rate_ratio_log_normal_95_ci")} for r in results],
                      "elapsed":out["elapsed_seconds"]},indent=2))


if __name__=="__main__": main()
