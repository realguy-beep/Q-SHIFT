"""Bounded distance-9 extension of known-profile memory-basis alignment."""
from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path

import numpy as np
import pymatching
import stim
from scipy.stats import beta

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'outputs/phase2b_pauli_bias'))
sys.path.insert(0,str(HERE))
from basis_alignment_distance7 import build, wilson
from noise_model import build_circuit as source_build

DISTANCE=9
ROUNDS=17
REGIME='x_biased'
PRE_SEEDS=(2026113001,2026113002)
MAIN_SEEDS=(2026113011,2026113012)
SHOTS=500_000


def resources(circuit):
    pairs=oneq=meas=0
    for inst in circuit.flattened():
        if inst.name=='PAULI_CHANNEL_1':oneq+=len(inst.targets_copy())
        elif inst.name=='PAULI_CHANNEL_2':pairs+=len(inst.targets_copy())//2
        elif inst.name in ('X_ERROR','Z_ERROR'):meas+=len(inst.targets_copy())
    return {'qubits':circuit.num_qubits,'detectors':circuit.num_detectors,
            'observables':circuit.num_observables,'rounds':ROUNDS,
            'two_qubit_channel_pairs':pairs,'one_qubit_noise_targets':oneq,
            'measurement_flip_targets':meas}


def noiseless(circuit):
    out=stim.Circuit()
    for inst in circuit.flattened():
        if inst.name in ('PAULI_CHANNEL_1','PAULI_CHANNEL_2','X_ERROR','Z_ERROR'):continue
        out.append(inst.name,inst.targets_copy(),inst.gate_args_copy())
    return out


def rate_ratio(aligned, mismatched):
    total=aligned+mismatched
    ratio=(aligned/mismatched) if mismatched else (0.0 if aligned==0 else None)
    if total==0:
        interval=None
    else:
        lo=0.0 if aligned==0 else float(beta.ppf(.025,aligned,total-aligned+1))
        hi=1.0 if aligned==total else float(beta.ppf(.975,aligned+1,total-aligned))
        interval=[lo/(1-lo) if lo<1 else float('inf'),
                  hi/(1-hi) if hi<1 else float('inf')]
    return {'aligned_over_mismatched_rate_ratio':ratio,
            'conditional_exact_95_ci':interval,
            'upper_ci_at_or_below_1e-4':bool(interval is not None and interval[1]<=1e-4)}


def decode_one(basis, seed, shots):
    c=build(basis,REGIME,distance=DISTANCE,rounds=ROUNDS,bias_ratio=10.)
    dem=c.detector_error_model(decompose_errors=True,approximate_disjoint_errors=.0018)
    matching=pymatching.Matching.from_detector_error_model(dem,enable_correlations=True)
    t=time.perf_counter()
    det,obs=c.compile_detector_sampler(seed=seed).sample(shots=shots,separate_observables=True)
    sample_seconds=time.perf_counter()-t
    t=time.perf_counter()
    pred=np.asarray(matching.decode_batch(det),dtype=np.bool_).reshape(shots,-1)
    decode_seconds=time.perf_counter()-t
    if pred.shape!=obs.shape:raise RuntimeError('decoder observable shape mismatch')
    scalar=np.asarray([matching.decode(det[i]) for i in range(min(100,shots))],dtype=np.bool_).reshape(min(100,shots),-1)
    if not np.array_equal(scalar,pred[:len(scalar)]):raise RuntimeError('scalar/batch disagreement')
    failures=int(np.count_nonzero(np.any(pred!=obs,axis=1)))
    return {'memory_basis':basis,'seed':seed,'shots':shots,'failures':failures,
            'ler':failures/shots,'wilson_95':wilson(failures,shots),
            'sampling_seconds':sample_seconds,'decode_seconds':decode_seconds,
            'resources':resources(c)}


def verify():
    circuits={basis:build(basis,REGIME,distance=DISTANCE,rounds=ROUNDS,bias_ratio=10.)
              for basis in ('x','z')}
    results={}
    reference=None
    for basis,circuit in circuits.items():
        clean=noiseless(circuit)
        sample=clean.compile_detector_sampler(seed=2026113000).sample(shots=64,separate_observables=True)
        if np.any(sample[0]) or np.any(sample[1]):raise RuntimeError('noiseless deterministic circuit failed')
        circuit.detector_error_model(decompose_errors=True,approximate_disjoint_errors=.0018)
        res=resources(circuit)
        key=(res['qubits'],res['detectors'],res['observables'],res['rounds'],res['two_qubit_channel_pairs'])
        if reference is None:reference=key
        elif key!=reference:raise RuntimeError('basis resource mismatch')
        results[basis]=res
    if results['x']['qubits']!=2*DISTANCE**2+DISTANCE**2-1:
        # The generated circuit includes data and measurement ancillas; the resource equality is primary.
        if results['x']['qubits']<DISTANCE**2:raise RuntimeError('unexpected data qubit count')
    # d=3 byte-for-byte builder compatibility with the canonical noise model.
    for basis in ('x','z'):
        custom=build(basis,REGIME,distance=3,rounds=5,bias_ratio=10.)
        canonical=source_build(basis,REGIME,distance=3,rounds=5,bias_ratio=10.)
        if str(custom)!=str(canonical):raise RuntimeError('d3 source builder reproduction failed')
    return results


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--preflight',action='store_true');args=parser.parse_args()
    begin=time.perf_counter();verified=verify()
    shots=100 if args.preflight else SHOTS
    seeds=PRE_SEEDS if args.preflight else MAIN_SEEDS
    rows=[decode_one(basis,seed,shots) for basis,seed in zip(('z','x'),seeds,strict=True)]
    elapsed=time.perf_counter()-begin
    keys=('qubits','detectors','observables','rounds','two_qubit_channel_pairs')
    if any(tuple(r['resources'][k] for k in keys)!=tuple(rows[0]['resources'][k] for k in keys) for r in rows):
        raise RuntimeError('resource match failed')
    by_basis={r['memory_basis']:r for r in rows}
    aligned=by_basis['x'];mismatched=by_basis['z']
    comparison=rate_ratio(aligned['failures'],mismatched['failures'])
    zero_upper=(1-.05**(1/SHOTS)) if aligned['failures']==0 and not args.preflight else None
    projected=sum((r['sampling_seconds']+r['decode_seconds'])*SHOTS/shots for r in rows) if args.preflight else None
    output={'status':'distance9_preflight' if args.preflight else 'distance9_development_screen',
            'distance':DISTANCE,'rounds':ROUNDS,'regime':REGIME,'gate_p':.003,
            'measurement_p':.003,'bias_ratio':10.,'verified_circuit_resources':verified,
            'shots_per_condition':shots,'conditions':rows,'aligned_basis':'x','mismatched_basis':'z',
            'comparison':comparison,'aligned_zero_failure_one_sided_95_upper':zero_upper,
            'stochastic_samples':2*shots,'projected_main_seconds':projected,
            'elapsed_seconds':elapsed,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'scope':'fourth finite-distance point for fixed known-profile bias alignment; development only; not threshold or adaptation evidence'}
    target=HERE/('basis_alignment_d9_preflight.json' if args.preflight else 'basis_alignment_d9_results.json')
    target.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'status':output['status'],'projected_main_seconds':projected,
                      'conditions':[{'basis':r['memory_basis'],'failures':r['failures'],
                                     'seconds':r['sampling_seconds']+r['decode_seconds']} for r in rows],
                      'comparison':comparison,'output':str(target)},indent=2))
    return int(args.preflight and projected>300)


if __name__=='__main__':raise SystemExit(main())
