"""Categorical flags for two-qubit, one-qubit, and explicit readout faults."""
from __future__ import annotations
import argparse,json,sys,time
from pathlib import Path
import numpy as np
import pymatching
import stim

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'outputs/phase2b_pauli_bias'))
sys.path.insert(0,str(HERE))
from noise_model import PAULI_PAIRS,build_circuit

CONDS=(("z","x_biased"),("x","z_biased"))
PREFLIGHT_SEEDS=(2026113501,2026113502)
PREFLIGHT_SOURCE_SEEDS=(2026113521,2026113522)
MAIN_SEEDS=(2026113511,2026113512)
N_PREFLIGHT=5000;N_MAIN=100000;MAX_SECONDS=300
P1_LABELS=("X","Y","Z")
P1_TARGET={"X":stim.target_x,"Y":stim.target_y,"Z":stim.target_z}
PAIR_TARGET={"X":stim.target_x,"Y":stim.target_y,"Z":stim.target_z}


def instrument_all(circuit):
    source=circuit.flattened();out=stim.Circuit();events=[];flag_qubits=[]
    next_flag=circuit.num_qubits;event_index=0
    for instruction_index,inst in enumerate(source):
        name=inst.name;targets=inst.targets_copy();args=[float(x) for x in inst.gate_args_copy()]
        if name=="PAULI_CHANNEL_2":
            if len(args)!=15 or len(targets)%2:raise RuntimeError("invalid PAULI_CHANNEL_2 shape")
            for pi in range(len(targets)//2):
                qpair=(int(targets[2*pi].value),int(targets[2*pi+1].value));flags=tuple(range(next_flag,next_flag+4));next_flag+=4
                remaining=1.0
                reconstructed=[]
                for code,p in enumerate(args,1):
                    q=float(p/remaining)
                    reconstructed.append(remaining*q)
                    pair=PAULI_PAIRS[code-1];err=[]
                    for symbol,qubit in zip(pair,qpair,strict=True):
                        if symbol!="I":err.append(PAIR_TARGET[symbol](qubit))
                    for bit,flag in enumerate(flags):
                        if (code>>bit)&1:err.append(stim.target_x(flag))
                    out.append("E" if code==1 else "ELSE_CORRELATED_ERROR",err,[q])
                    remaining-=p
                if not np.allclose(reconstructed,args,rtol=0,atol=2e-16):
                    raise RuntimeError("PAULI_CHANNEL_2 probabilities changed during instrumentation")
                events.append({"kind":"two_qubit_pair","instruction_index":instruction_index,
                               "pair_index":pi,"qubits":qpair,"flags":flags,
                               "flag_bits":4,"flag_offset":len(flag_qubits),"event_index":event_index})
                flag_qubits.extend(flags);event_index+=1
            continue
        if name=="PAULI_CHANNEL_1":
            if len(args)!=3:raise RuntimeError("invalid PAULI_CHANNEL_1 shape")
            for ti,target in enumerate(targets):
                qbit=int(target.value);flags=tuple(range(next_flag,next_flag+2));next_flag+=2;remaining=1.0
                reconstructed=[]
                for code,p in enumerate(args,1):
                    q=float(p/remaining);reconstructed.append(remaining*q)
                    err=[P1_TARGET[P1_LABELS[code-1]](qbit)]
                    for bit,flag in enumerate(flags):
                        if (code>>bit)&1:err.append(stim.target_x(flag))
                    out.append("E" if code==1 else "ELSE_CORRELATED_ERROR",err,[q])
                    remaining-=p
                if not np.allclose(reconstructed,args,rtol=0,atol=2e-16):
                    raise RuntimeError("PAULI_CHANNEL_1 probabilities changed during instrumentation")
                events.append({"kind":"one_qubit_pauli","instruction_index":instruction_index,
                               "target_index":ti,"qubits":[qbit],"flags":flags,
                               "flag_bits":2,"flag_offset":len(flag_qubits),"event_index":event_index})
                flag_qubits.extend(flags);event_index+=1
            continue
        if name in ("X_ERROR","Z_ERROR"):
            if len(args)!=1 or not (0<=args[0]<=1):raise RuntimeError("invalid explicit error probability")
            for ti,target in enumerate(targets):
                qbit=int(target.value);flag=next_flag;next_flag+=1
                pauli=stim.target_x(qbit) if name=="X_ERROR" else stim.target_z(qbit)
                out.append("E",[pauli,stim.target_x(flag)],[args[0]])
                events.append({"kind":"measurement_flip_"+name,"instruction_index":instruction_index,
                               "target_index":ti,"qubits":[qbit],"flags":[flag],
                               "flag_bits":1,"flag_offset":len(flag_qubits),"event_index":event_index})
                flag_qubits.append(flag);event_index+=1
            continue
        out.append(name,targets,args)
    out.append("M",flag_qubits)
    nflags=len(flag_qubits)
    for i in range(nflags):
        out.append("OBSERVABLE_INCLUDE",[stim.target_rec(-nflags+i)],[circuit.num_observables+i])
    if out.num_detectors!=circuit.num_detectors or out.num_observables!=circuit.num_observables+nflags:
        raise RuntimeError("instrumented detector/observable layout mismatch")
    return out,events


def decode_codes(outputs,shots,source_observables,events):
    flags=outputs[:,source_observables:]
    codes=np.zeros((shots,len(events)),dtype=np.uint8)
    for j,event in enumerate(events):
        b=event['flag_bits'];off=event['flag_offset']
        bits=flags[:,off:off+b].astype(np.uint8)
        weights=(1<<np.arange(b,dtype=np.uint8))
        codes[:,j]=(bits@weights).astype(np.uint8)
    return codes


def matching_for_condition(basis,profile,assumed_ratio):
    c=build_circuit(basis,profile,distance=3,rounds=5,gate_p=.003,
                    measurement_p=.003,bias_ratio=float(assumed_ratio))
    dem=c.detector_error_model(decompose_errors=True,approximate_disjoint_errors=.0018)
    return pymatching.Matching.from_detector_error_model(dem,enable_correlations=True)


def summarize(codes,fail5,fail10,events):
    groups={"both_correct":(~fail5&~fail10),"both_wrong":(fail5&fail10),
            "ratio10_fixes_ratio5":(fail5&~fail10),"ratio10_breaks_ratio5":(~fail5&fail10)}
    result={}
    for name,mask in groups.items():
        rows=codes[mask];size=int(mask.sum());faults=rows>0
        counts_by_kind={};outcomes_by_kind={}
        for j,event in enumerate(events):
            kind=event['kind'];counts_by_kind.setdefault(kind,[])
            outcomes_by_kind.setdefault(kind,{})
            vals=rows[:,j] if size else np.asarray([],dtype=np.uint8)
            counts_by_kind[kind].append(int(np.count_nonzero(vals)))
            if kind=='two_qubit_pair':
                label_counts=np.bincount(vals, minlength=16)[1:]
                for label,count in zip(PAULI_PAIRS,label_counts,strict=True):
                    outcomes_by_kind[kind][label]=outcomes_by_kind[kind].get(label,0)+int(count)
            elif kind=='one_qubit_pauli':
                label_counts=np.bincount(vals,minlength=4)[1:]
                for label,count in zip(P1_LABELS,label_counts,strict=True):
                    outcomes_by_kind[kind][label]=outcomes_by_kind[kind].get(label,0)+int(count)
            else:
                outcomes_by_kind[kind]["flip"]=outcomes_by_kind[kind].get("flip",0)+int(np.count_nonzero(vals))
        totals={k:int(sum(v)) for k,v in counts_by_kind.items()}
        result[name]={"shots":size,"mean_fault_events_per_shot":{
            k:(v/size if size else None) for k,v in totals.items()},
            "zero_fault_fraction_by_kind":{
                k:(float(np.mean(np.sum(np.asarray(v),axis=0)==0)) if False else None) for k,v in []},
            "fault_event_totals_by_kind":totals,
            "outcome_counts_by_kind":outcomes_by_kind,
            "mean_all_tracked_faults_per_shot":float(faults.sum(axis=1).mean()) if size else None}
        result[name]["zero_fault_fraction_by_kind"]={}
        for kind in counts_by_kind:
            event_indices=[j for j,e in enumerate(events) if e['kind']==kind]
            kind_faults=faults[:,event_indices].sum(axis=1) if size else np.asarray([],dtype=np.uint8)
            result[name]["mean_fault_events_per_shot"][kind]=float(kind_faults.mean()) if size else None
            result[name]["zero_fault_fraction_by_kind"][kind]=float(np.mean(kind_faults==0)) if size else None
    return result


def make_source(basis,profile):
    return build_circuit(basis,profile,distance=3,rounds=5,gate_p=.003,
                         measurement_p=.003,bias_ratio=10.)


def preflight_one(basis,profile,seed,source_seed):
    source=make_source(basis,profile);inst,events=instrument_all(source)
    kinds={kind:sum(e['kind']==kind for e in events) for kind in
           ('two_qubit_pair','one_qubit_pauli','measurement_flip_X_ERROR','measurement_flip_Z_ERROR')}
    if kinds['two_qubit_pair']!=120 or kinds['one_qubit_pauli']>100 or \
       kinds['measurement_flip_X_ERROR']+kinds['measurement_flip_Z_ERROR']>100:
        raise RuntimeError(f"unexpected all-fault location count: {kinds}")
    m5=matching_for_condition(basis,profile,5);m10=matching_for_condition(basis,profile,10)
    t=time.perf_counter();d1,o1=source.compile_detector_sampler(seed=source_seed).sample(
        shots=N_PREFLIGHT,separate_observables=True)
    _,f1=decoder_fail(m10,d1,o1);source_seconds=time.perf_counter()-t
    t=time.perf_counter();d2,o2,codes,inst,events=sample_instrument(source,seed,N_PREFLIGHT)
    _,f2=decoder_fail(m10,d2,o2[:,:1]);instrument_seconds=time.perf_counter()-t
    se=np.sqrt(f1.mean()*(1-f1.mean())/N_PREFLIGHT+f2.mean()*(1-f2.mean())/N_PREFLIGHT)
    z=(f2.mean()-f1.mean())/se if se else 0.
    return {"basis":basis,"profile":profile,"event_counts":kinds,
            "source_detectors":source.num_detectors,"source_observables":source.num_observables,
            "instrumented_qubits":inst.num_qubits,"total_events":len(events),
            "source_failures":int(f1.sum()),"instrumented_failures":int(f2.sum()),
            "independent_rate_z":float(z),"source_seconds":source_seconds,
            "instrument_seconds":instrument_seconds}


def decoder_fail(matching,detectors,observables):
    prediction=np.asarray(matching.decode_batch(detectors,enable_correlations=True),dtype=np.bool_).reshape(len(detectors),-1)
    if prediction.shape!=observables.shape:raise RuntimeError('decoder output shape mismatch')
    return prediction,np.any(prediction!=observables,axis=1)


def sample_instrument(source,seed,shots):
    inst,events=instrument_all(source)
    detectors,outputs=inst.compile_detector_sampler(seed=seed).sample(shots=shots,separate_observables=True)
    codes=decode_codes(outputs,shots,source.num_observables,events)
    return detectors,outputs,codes,inst,events


def validate_synthetic():
    p1=[.25,.25,.25];p2=[.01]*15
    c=stim.Circuit('R 0 1 2 3 4\nH 4\nPAULI_CHANNEL_1('+','.join(map(str,p1))+') 0\n'
                   'PAULI_CHANNEL_2('+','.join(map(str,p2))+') 1 2\n'
                   'X_ERROR(0.25) 3\nZ_ERROR(0.25) 4\nH 4\nM 0 1 2 3 4')
    inst,events=instrument_all(c)
    raw=inst.compile_sampler(seed=2026113599).sample(shots=50_000)
    data=raw[:,:5];outs=raw[:,5:]
    codes=decode_codes(outs,50_000,0,events)
    mismatches=0
    for j,event in enumerate(events):
        q=event['qubits'][0];code=codes[:,j]
        if event['kind']=='one_qubit_pauli':
            expected=(code==1)|(code==2)
            mismatches+=int(np.count_nonzero(data[:,q]!=expected))
        elif event['kind']=='two_qubit_pair':
            pair=event['qubits']
            label_map={i+1:p for i,p in enumerate(PAULI_PAIRS)}
            for index,qubit in enumerate(pair):
                expected=np.asarray([label_map.get(int(v),'II')[index] in 'XY' for v in code])
                mismatches+=int(np.count_nonzero(data[:,qubit]!=expected))
        elif event['kind']=='measurement_flip_X_ERROR':
            mismatches+=int(np.count_nonzero(data[:,q]!=(code==1)))
        elif event['kind']=='measurement_flip_Z_ERROR':
            mismatches+=int(np.count_nonzero(data[:,q]!=(code==1)))
    if mismatches:raise RuntimeError(f"synthetic all-fault flag/data mismatches={mismatches}")
    return {"shots":50_000,"events":len(events),"categories_seen":{
        e['kind']:int(len(np.unique(codes[:,j]))) for j,e in enumerate(events)},
        "data_flag_mismatches":mismatches}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');ap.add_argument('--shots',type=int,default=N_MAIN);a=ap.parse_args()
    if a.shots<=0:ap.error('--shots must be positive')
    start=time.perf_counter();synthetic=validate_synthetic()
    rows=[]
    if a.preflight:
        for i,(basis,profile) in enumerate(CONDS):
            rows.append(preflight_one(basis,profile,PREFLIGHT_SEEDS[i],PREFLIGHT_SOURCE_SEEDS[i]))
        elapsed=time.perf_counter()-start
        projection=sum((r['instrument_seconds']+r['source_seconds'])*N_MAIN/N_PREFLIGHT for r in rows)
        passed=all(r['source_detectors']==40 and r['source_observables']==1 and abs(r['independent_rate_z'])<4 for r in rows)
        output={'status':'all_fault_preflight_passed' if passed and projection<=MAX_SECONDS else 'all_fault_preflight_stopped',
                'synthetic_validation':synthetic,'conditions':rows,'preflight_shots_per_arm_condition':N_PREFLIGHT,
                'projected_main_seconds':projection,'max_projected_seconds':MAX_SECONDS,
                'elapsed_seconds':elapsed}
        target=HERE/'all_fault_mechanism_preflight.json'
    else:
        seeds=MAIN_SEEDS
        for (basis,profile),seed in zip(CONDS,seeds,strict=True):
            source=make_source(basis,profile);m5=matching_for_condition(basis,profile,5);m10=matching_for_condition(basis,profile,10)
            detectors,outputs,codes,inst,events=sample_instrument(source,seed,a.shots)
            observable=outputs[:,:source.num_observables]
            pred5,f5=decoder_fail(m5,detectors,observable);pred10,f10=decoder_fail(m10,detectors,observable)
            groups=summarize(codes,f5,f10,events)
            rows.append({'basis':basis,'profile':profile,'seed':seed,'shots':a.shots,
                         'source_detectors':source.num_detectors,'source_observables':source.num_observables,
                         'instrumented_qubits':inst.num_qubits,'event_counts':{
                            k:sum(e['kind']==k for e in events) for k in sorted(set(e['kind'] for e in events))},
                         'failures_by_assumed_ratio':{'5':int(f5.sum()),'10':int(f10.sum())},
                         'prediction_disagreements':int(np.count_nonzero(np.any(pred5!=pred10,axis=1))),
                         'fault_group_summaries':groups})
        elapsed=time.perf_counter()-start
        output={'status':'development_all_fault_composition_screen','synthetic_validation':synthetic,
                'conditions':rows,'shots_per_condition':a.shots,
                'new_source_equivalent_samples':a.shots*len(CONDS),'elapsed_seconds':elapsed,
                'limitation':'development conditional compositions only; not causal decoder attribution or hardware model'}
        target=HERE/'all_fault_mechanism_results.json'
    target.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'status':output['status'],'output':str(target),
                      'projected_main_seconds':output.get('projected_main_seconds'),
                      'synthetic_mismatches':synthetic['data_flag_mismatches']},indent=2))
    if a.preflight and output['status']!='all_fault_preflight_passed':return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
