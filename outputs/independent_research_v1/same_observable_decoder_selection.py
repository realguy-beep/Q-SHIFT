"""Select a noise-matched matching decoder using detector-only calibration."""
from __future__ import annotations
import json,re,sys,time
from pathlib import Path
import numpy as np,pymatching,stim
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from basis_alignment_distance7 import build
from bias_identification import feature_masks,make_features,FEATURES
from noise_model import (DEFAULT_GATE_P,DEFAULT_MEAS_P,one_qubit_probabilities,two_qubit_probabilities,build_circuit as source_build)
MODEL=json.load(open(HERE/'bias_identification_results.json'))['training'];W=np.asarray(MODEL['weights']);B=float(MODEL['intercept'])
PROFILES=('x_biased','z_biased');PRE=(2026112001,2026112002,2026112003,2026112004);MAIN=(2026112011,2026112012,2026112013,2026112014)

def pooled_circuit():
    p1=np.mean([one_qubit_probabilities(p,DEFAULT_GATE_P,10.) for p in PROFILES],axis=0)
    p2=np.mean([two_qubit_probabilities(p,DEFAULT_GATE_P,10.) for p in PROFILES],axis=0)
    c=stim.Circuit.generated('surface_code:rotated_memory_z',distance=3,rounds=5,after_clifford_depolarization=DEFAULT_GATE_P,before_measure_flip_probability=DEFAULT_MEAS_P)
    body=str(c)
    body,n1=re.subn(r'DEPOLARIZE1\([^)]*\)','PAULI_CHANNEL_1('+','.join(format(float(v),'.17g') for v in p1)+')',body)
    body,n2=re.subn(r'DEPOLARIZE2\([^)]*\)','PAULI_CHANNEL_2('+','.join(format(float(v),'.17g') for v in p2)+')',body)
    if not n1 or not n2:raise RuntimeError('pooled channel substitution failed')
    return stim.Circuit(body)

def graph(c):
    d=c.detector_error_model(decompose_errors=True,approximate_disjoint_errors=.0018)
    return pymatching.Matching.from_detector_error_model(d,enable_correlations=True)

def check_circuits():
    originals={p:build('z',p,3,5,bias_ratio=10.) for p in PROFILES}
    source={p:str(originals[p])==str(source_build('z',p,distance=3,rounds=5,bias_ratio=10.)) for p in PROFILES}
    if not all(source.values()):raise RuntimeError('profile circuit differs from source')
    pool=pooled_circuit()
    dims={(c.num_qubits,c.num_detectors,c.num_observables,str(c.get_detector_coordinates())) for c in [*originals.values(),pool]}
    if len(dims)!=1:raise RuntimeError('pooled/profile circuits have different detector dimensions or coordinates')
    return originals,pool,source

def decode(m,det,obs):
    t=time.perf_counter();pred=np.asarray(m.decode_batch(det),dtype=np.bool_).reshape(len(det),-1);dt=time.perf_counter()-t
    n=min(100,len(det));scalar=np.asarray([m.decode(det[i]) for i in range(n)],dtype=np.bool_).reshape(n,-1)
    if not np.array_equal(pred[:n],scalar):raise RuntimeError('batch/scalar disagreement')
    if pred.shape!=obs.shape:raise RuntimeError('observable shape mismatch')
    return np.any(pred!=obs,axis=1),dt

def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');a=ap.parse_args();start=time.perf_counter();circuits,pool,source=check_circuits()
    graphs={p:graph(circuits[p]) for p in PROFILES};graphs['pooled']=graph(pool)
    pre=a.preflight;seeds=PRE if pre else MAIN;caln=1000 if pre else 500000;memn=1000 if pre else 100000;si=0;rows=[]
    for profile in PROFILES:
        sc=seeds[si];si+=1;c=circuits[profile];masks=feature_masks(c,3,5)
        t=time.perf_counter();detc=c.compile_detector_sampler(seed=sc).sample(shots=caln);calsec=time.perf_counter()-t;feat=make_features(detc,masks)
        if not np.isfinite(feat).all():raise RuntimeError('nonfinite calibration features')
        if pre:rows.append({'kind':'calibration','profile':profile,'shots':caln,'seed':sc,'sampling_seconds':calsec,'detectors':c.num_detectors})
        else:select_x=(feat.reshape(1000,500,len(FEATURES)).mean(axis=1)@W+B)<0
        sm=seeds[si];si+=1;t=time.perf_counter();deto,obs=c.compile_detector_sampler(seed=sm).sample(shots=memn,separate_observables=True);samsec=time.perf_counter()-t
        fails={};times={}
        for name,m in graphs.items():fails[name],times[name]=decode(m,deto,obs)
        if pre:rows.append({'kind':'logical','profile':profile,'shots':memn,'seed':sm,'sampling_seconds':samsec,'decode_seconds':times,'failures_preflight_only':{k:int(v.sum()) for k,v in fails.items()},'detectors':c.num_detectors})
        else:
            batches={k:v.reshape(1000,100).sum(axis=1).astype(int) for k,v in fails.items()}
            selected=np.where(select_x,batches['x_biased'],batches['z_biased']);oracle=batches[profile]
            rows.append({'kind':'policy','profile':profile,'calibration_seed':sc,'memory_seed':sm,'x_selected':int(select_x.sum()),'z_selected':int((~select_x).sum()),'failures_by_model_and_window':{k:v.tolist() for k,v in batches.items()},'selected_failures_by_window':selected.tolist(),'oracle_failures_by_window':oracle.tolist(),'selected_failures':int(selected.sum()),'oracle_failures':int(oracle.sum()),'decoder_sampling_seconds':samsec,'decode_seconds':times})
    elapsed=time.perf_counter()-start
    if pre:
        projection=sum(r.get('sampling_seconds',0)*(500 if r['kind']=='calibration' else 100) + (max(r.get('decode_seconds',{}).values())*100 if r['kind']=='logical' else 0) for r in rows)
        out={'status':'preflight','d3_profile_circuits_byte_identical_to_source':source,'decoder_graphs':{k:{'nodes':m.num_detectors,'edges':m.num_edges} for k,m in graphs.items()},'rows':rows,'projected_main_seconds':projection,'elapsed_seconds':elapsed,'stochastic_circuit_shots':sum(r['shots'] for r in rows)}
        p=HERE/'same_observable_decoder_selection_preflight.json';p.write_text(json.dumps(out,indent=2)+'\n');print(f'Wrote {p}; projection {projection:.1f}s');return int(projection>300)
    rng=np.random.default_rng(2026112091);pol=[r for r in rows if r['kind']=='policy'];summary=[];boot=5000
    # Equal weights for the two profile distributions; cluster bootstrap resamples 100-shot batches within profile.
    names=('selected','pooled','x_biased','z_biased','oracle')
    all_errors={}
    for name in names:
        if name=='selected':all_errors[name]=[np.asarray(r['selected_failures_by_window']) for r in pol]
        elif name=='oracle':all_errors[name]=[np.asarray(r['oracle_failures_by_window']) for r in pol]
        else:all_errors[name]=[np.asarray(r['failures_by_model_and_window'][name]) for r in pol]
    rates={name:sum(a.sum() for a in arr)/(2*100000) for name,arr in all_errors.items()}
    boot_deltas=[]
    for arr in all_errors['selected'],all_errors['pooled']:
        pass
    per_profile=[]
    for j,r in enumerate(pol):
        per_profile.append({'profile':r['profile'],'selected_failures':r['selected_failures'],'pooled_failures':int(np.asarray(r['failures_by_model_and_window']['pooled']).sum()),'oracle_failures':r['oracle_failures'],'x_selected_windows':r['x_selected'],'z_selected_windows':r['z_selected']})
    idx=[rng.integers(0,1000,size=(boot,1000)) for _ in range(2)]
    sel_boot=sum(np.asarray(r['selected_failures_by_window'])[ix].sum(axis=1)/100000 for r,ix in zip(pol,idx,strict=True))/2
    pool_boot=sum(np.asarray(r['failures_by_model_and_window']['pooled'])[ix].sum(axis=1)/100000 for r,ix in zip(pol,idx,strict=True))/2
    delta=sel_boot-pool_boot
    out={'status':'development_same_observable_validation','distance':3,'rounds':5,'bias_ratio':10.,'gate_measurement_p':.003,'logical_observable':'same Z-memory observable for all decoders and profiles','decoder_bank':'correlation-enabled PyMatching graphs from x-profile, z-profile, and pooled mean-channel DEM; approximate_disjoint_errors=.0018','pooled_channel':'elementwise average of source X- and Z-profile categorical channel vectors at each location','policy':'frozen detector-only binary LDA, 500-shot Z-memory calibration windows','primary_comparator':'single static pooled mean-channel graph','per_profile':per_profile,'rates':rates,'selected_minus_pooled':rates['selected']-rates['pooled'],'selected_minus_pooled_cluster_bootstrap_95_ci':[float(np.quantile(delta,.025)),float(np.quantile(delta,.975))],'relative_reduction_vs_pooled':1-rates['selected']/rates['pooled'],'bootstrap_replicates':boot,'bootstrap_seed':2026112091,'source_builder_matches':source,'decoder_graphs':{k:{'nodes':m.num_detectors,'edges':m.num_edges} for k,m in graphs.items()},'elapsed_seconds':elapsed,'stochastic_circuit_shots':2*(500000+100000),'scope':'decoder selection with a fixed circuit and observable; development-only and not compared against every possible static decoder'}
    p=HERE/'same_observable_decoder_selection_results.json';p.write_text(json.dumps(out,indent=2)+'\n');print(f'Wrote {p}; elapsed={elapsed:.2f}s');print(out['rates'],out['selected_minus_pooled_cluster_bootstrap_95_ci'])
if __name__=='__main__':raise SystemExit(main())
