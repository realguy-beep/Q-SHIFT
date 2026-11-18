"""Matched local-map versus pooled matching under stable spatial hotspots."""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pymatching
import stim
from scipy.stats import binomtest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO/"outputs/phase2b_pauli_bias"))
from noise_model import build_circuit

PROFILES = ("east_hot", "west_hot")
PREFLIGHT_SEEDS = (2026112901, 2026112902)
MAIN_SEEDS = (2026112911, 2026112912)
N_SITES = 120
N_PER_ZONE = 60
P_BASE = .003
HOT_FACTOR, COLD_FACTOR = 1.5, .5
SHOTS = 200_000
DEM_APPROXIMATION_THRESHOLD = .003


def coordinates(circuit):
    out = {}
    for inst in circuit.flattened():
        if inst.name == "QUBIT_COORDS":
            out[int(inst.targets_copy()[0].value)] = tuple(map(float, inst.gate_args_copy()))
    return out


def spatial_circuit(profile):
    source = build_circuit("z", "x_biased", distance=3, rounds=5,
                           gate_p=P_BASE, measurement_p=P_BASE, bias_ratio=10.)
    coords = coordinates(source)
    sites = []
    for ii, inst in enumerate(source.flattened()):
        if inst.name != "PAULI_CHANNEL_2":
            continue
        targets = [int(t.value) for t in inst.targets_copy()]
        if len(targets)%2:
            raise RuntimeError("odd number of PAULI_CHANNEL_2 targets")
        for pi in range(len(targets)//2):
            a,b=targets[2*pi:2*pi+2]
            if a not in coords or b not in coords:
                raise RuntimeError("missing qubit coordinate for channel pair")
            xa,ya=coords[a][:2]; xb,yb=coords[b][:2]
            sites.append({"key":(ii,pi),"qubits":[a,b],
                          "mid_x":(xa+xb)/2,"mid_y":(ya+yb)/2})
    if len(sites)!=N_SITES:
        raise RuntimeError(f"expected {N_SITES} pair sites, found {len(sites)}")
    ordered=sorted(sites,key=lambda x:(x["mid_x"],x["mid_y"],x["key"][0],x["key"][1]))
    west={x["key"] for x in ordered[:N_PER_ZONE]}
    east={x["key"] for x in ordered[N_PER_ZONE:]}
    if len(west)!=N_PER_ZONE or len(east)!=N_PER_ZONE:
        raise RuntimeError("spatial split is not an equal partition")
    side_by_key={key:("west" if key in west else "east") for key in west|east}
    channels={}
    for ii,inst in enumerate(source.flattened()):
        if inst.name!="PAULI_CHANNEL_2":continue
        probabilities=np.asarray(inst.gate_args_copy(),dtype=np.float64)
        targets=[int(t.value) for t in inst.targets_copy()]
        for pi in range(len(targets)//2):
            key=(ii,pi);side=side_by_key[key]
            hot_side=profile.split("_")[0]
            is_hot=side==hot_side
            factor=HOT_FACTOR if is_hot else COLD_FACTOR
            channels[key]=probabilities*factor
    out=stim.Circuit()
    for ii,inst in enumerate(source.flattened()):
        if inst.name!="PAULI_CHANNEL_2":
            out.append(inst.name,inst.targets_copy(),inst.gate_args_copy())
            continue
        targets=[int(t.value) for t in inst.targets_copy()]
        for pi in range(len(targets)//2):
            out.append("PAULI_CHANNEL_2",targets[2*pi:2*pi+2],channels[(ii,pi)].tolist())
    by_side={side:[channels[k] for k,v in side_by_key.items() if v==side] for side in ("east","west")}
    means={side:float(np.mean([float(x.sum()) for x in values])) for side,values in by_side.items()}
    overall=float(np.mean([float(x.sum()) for x in channels.values()]))
    stats={"profile":profile,"pair_sites":len(sites),"east_sites":len(east),"west_sites":len(west),
           "mean_pair_probability_by_zone":means,"overall_mean_pair_probability":overall,
           "hot_factor":HOT_FACTOR,"cold_factor":COLD_FACTOR,
           "side_assignments":{f"{k[0]}:{k[1]}":v for k,v in side_by_key.items()},
           "pair_probabilities":{f"{k[0]}:{k[1]}":v.tolist() for k,v in channels.items()}}
    return source,out,stats


def clean(circuit):
    out=stim.Circuit()
    for inst in circuit.flattened():
        if inst.name in ("PAULI_CHANNEL_1","PAULI_CHANNEL_2","X_ERROR","Z_ERROR"):
            continue
        out.append(inst.name,inst.targets_copy(),inst.gate_args_copy())
    return out


def make_matching(circuit):
    dem=circuit.detector_error_model(decompose_errors=True,
                                     approximate_disjoint_errors=DEM_APPROXIMATION_THRESHOLD)
    return pymatching.Matching.from_detector_error_model(dem,enable_correlations=True)


def preflight():
    outputs={}; circuits={}; matchings={}
    for profile,seed in zip(PROFILES,PREFLIGHT_SEEDS,strict=True):
        source,actual,meta=spatial_circuit(profile)
        pooled=build_circuit("z","x_biased",distance=3,rounds=5,gate_p=P_BASE,
                             measurement_p=P_BASE,bias_ratio=10.)
        for c in (actual,pooled):
            if (c.num_qubits,c.num_detectors,c.num_observables)!=(26,40,1):
                raise RuntimeError("spatial intervention changed circuit shape")
            sample=clean(c).compile_detector_sampler(seed=2026112900).sample(
                shots=32,separate_observables=True)
            if np.any(sample[0]) or np.any(sample[1]):
                raise RuntimeError("spatial circuit noiseless determinism failed")
        local_m=make_matching(actual); pooled_m=make_matching(pooled)
        t=time.perf_counter()
        det,obs=actual.compile_detector_sampler(seed=seed).sample(shots=100,separate_observables=True)
        sample_time=time.perf_counter()-t
        t=time.perf_counter()
        lp=np.asarray(local_m.decode_batch(det),dtype=np.bool_).reshape(100,-1)
        pp=np.asarray(pooled_m.decode_batch(det),dtype=np.bool_).reshape(100,-1)
        if lp.shape!=obs.shape or pp.shape!=obs.shape:
            raise RuntimeError("local/pooled prediction shape mismatch")
        if not np.array_equal(lp[:10],np.asarray([local_m.decode(x) for x in det[:10]],dtype=np.bool_).reshape(10,-1)):
            raise RuntimeError("local scalar/batch mismatch")
        if not np.array_equal(pp[:10],np.asarray([pooled_m.decode(x) for x in det[:10]],dtype=np.bool_).reshape(10,-1)):
            raise RuntimeError("pooled scalar/batch mismatch")
        decode_time=time.perf_counter()-t
        outputs[profile]={"metadata":meta,"preflight_shots":100,
                          "sample_seconds":sample_time,"decode_both_seconds":decode_time}
        circuits[profile]=actual;matchings[profile]=(local_m,pooled_m)
    # Paired hot/cold assignment must reverse every location; average channel remains p=.003.
    east=outputs["east_hot"]["metadata"];west=outputs["west_hot"]["metadata"]
    if east["side_assignments"]!=west["side_assignments"]:
        raise RuntimeError("spatial side assignment changed between profiles")
    if abs(east["overall_mean_pair_probability"]-P_BASE)>1e-12 or abs(west["overall_mean_pair_probability"]-P_BASE)>1e-12:
        raise RuntimeError("spatial mean pair rate differs from pooled source")
    for key,side in east["side_assignments"].items():
        if side=="east":
            eh=east["pair_probabilities"][key];wh=west["pair_probabilities"][key]
        else:
            eh=west["pair_probabilities"][key];wh=east["pair_probabilities"][key]
        if not np.allclose(np.asarray(eh)/np.asarray(wh),3.0,rtol=1e-10,atol=1e-10):
            raise RuntimeError("east/west profiles are not pointwise hot/cold reversals")
    return outputs


def run_profile(profile,seed,shots):
    _,actual,meta=spatial_circuit(profile)
    pooled=build_circuit("z","x_biased",distance=3,rounds=5,gate_p=P_BASE,
                         measurement_p=P_BASE,bias_ratio=10.)
    local_m=make_matching(actual);pooled_m=make_matching(pooled)
    det,obs=actual.compile_detector_sampler(seed=seed).sample(shots=shots,separate_observables=True)
    start=time.perf_counter();local=np.asarray(local_m.decode_batch(det),dtype=np.bool_).reshape(shots,-1);local_seconds=time.perf_counter()-start
    start=time.perf_counter();pool=np.asarray(pooled_m.decode_batch(det),dtype=np.bool_).reshape(shots,-1);pool_seconds=time.perf_counter()-start
    local_fail=np.any(local!=obs,axis=1);pool_fail=np.any(pool!=obs,axis=1)
    local_only=int(np.count_nonzero(local_fail&~pool_fail));pool_only=int(np.count_nonzero(pool_fail&~local_fail))
    diffs=local_fail.astype(np.float64)-pool_fail.astype(np.float64)
    delta=float(diffs.mean());se=float(diffs.std(ddof=1)/math.sqrt(shots))
    discord=local_only+pool_only
    return {"profile":profile,"seed":seed,"shots":shots,"local_failures":int(local_fail.sum()),
            "pooled_failures":int(pool_fail.sum()),"local_ler":float(local_fail.mean()),
            "pooled_ler":float(pool_fail.mean()),"paired_delta_local_minus_pooled":delta,
            "paired_delta_normal_95_ci":[delta-1.95996398454*se,delta+1.95996398454*se],
            "local_only":local_only,"pooled_only":pool_only,"discordant":discord,
            "mcnemar_exact_two_sided":float(binomtest(local_only,discord,.5).pvalue) if discord else 1.0,
            "local_decode_seconds":local_seconds,"pooled_decode_seconds":pool_seconds,
            "metadata":meta}


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--preflight',action='store_true');args=parser.parse_args()
    start=time.perf_counter(); pf=preflight(); preflight_seconds=time.perf_counter()-start
    if args.preflight:
        projected=sum((pf[p]['sample_seconds']+pf[p]['decode_both_seconds'])*SHOTS/100
                      for p in PROFILES)
        result={"status":"spatial_noise_preflight","profiles":pf,"preflight_elapsed_seconds":preflight_seconds,
                "projected_main_seconds":projected,"preflight_stochastic_shots":200,
                "stop_if_projected_over_seconds":300}
        (HERE/'spatial_noise_decoder_preflight.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({"status":result['status'],"projected_main_seconds":projected},indent=2))
        return int(projected>300)
    rows=[run_profile(profile,seed,SHOTS) for profile,seed in zip(PROFILES,MAIN_SEEDS,strict=True)]
    reductions=[1-r['local_ler']/r['pooled_ler'] if r['pooled_ler'] else None for r in rows]
    valid=[x for x in reductions if x is not None]
    macro=float(np.mean(valid)) if valid else None
    passed=(len(valid)==2 and macro>=.10 and min(valid)>=-.05)
    result={"status":"spatial_noise_decoder_development","hypothesis":"known local two-qubit rates improve matching over pooled mean under spatial hotspots",
            "profiles":rows,"per_profile_relative_reduction":reductions,
            "equal_weight_macro_relative_reduction":macro,"advancement_gate_passed":passed,
            "shots_per_profile":SHOTS,"stochastic_qshift_shots":2*SHOTS,
            "scope":"synthetic spatial-noise stress test; profile map known to local decoder; not adaptive or hardware-calibrated",
            "elapsed_seconds":time.perf_counter()-start}
    (HERE/'spatial_noise_decoder_results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({"status":result['status'],"macro_reduction":macro,"gate":passed,
                      "profiles":[{k:r[k] for k in ('profile','local_ler','pooled_ler','local_only','pooled_only')}
                                  for r in rows]},indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
