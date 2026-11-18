"""Fresh d5 2x2 CSS/XZZX and logical-memory-basis screen."""
from __future__ import annotations
import json,time,sys,resource
from pathlib import Path
import numpy as np
import pymatching,stim
from scipy.stats import beta
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'outputs/phase2b_pauli_bias'))
from basis_alignment_distance7 import build
from xzzx_native_xcx import native_transform,resources

CONDITIONS=(('css','x'),('css','z'),('xzzx','x'),('xzzx','z'))
PREFLIGHT_SEEDS=(2026114101,2026114102,2026114103,2026114104)
MAIN_SEEDS=(2026114111,2026114112,2026114113,2026114114)
PREFLIGHT_SHOTS=10000;MAIN_SHOTS=500000;MAX_SECONDS=300


def make_circuit(code,basis,distance=5,rounds=None):
    if rounds is None:rounds=2*distance-1
    c=build(basis,'x_biased',distance=distance,rounds=rounds,bias_ratio=10.,gate_p=.003,measurement_p=.003)
    if code=='xzzx':c,_,_,_=native_transform(c)
    return c


def full_resources(c):
    r=resources(c)
    r['measurement_flip_targets']=sum(len(i.targets_copy()) for i in c.flattened() if i.name in ('X_ERROR','Z_ERROR'))
    r['pauli_channel_2_probability_vectors']=[list(i.gate_args_copy()) for i in c.flattened() if i.name=='PAULI_CHANNEL_2']
    return r


def rr(a,na,b,nb):
    if a==0 and b==0:return {'point':None,'conditional_exact_95_ci':[0.0,None],
                             'conditional_failures':0,'upper_unbounded':True}
    lo=0. if a==0 else beta.ppf(.025,a,b+1)
    hi=1. if b==0 else beta.ppf(.975,a+1,b)
    return {'point':None if b==0 else (a/na)/(b/nb),
            'conditional_exact_95_ci':[float(lo/(1-lo)*nb/na),None if b==0 else float(hi/(1-hi)*nb/na)],
            'conditional_failures':a+b,'upper_unbounded':b==0}


def one(code,basis,seed,shots,preflight=False,distance=5,rounds=None):
    c=make_circuit(code,basis,distance,rounds)
    dem=c.detector_error_model(decompose_errors=True,approximate_disjoint_errors=.0018)
    matching=pymatching.Matching.from_detector_error_model(dem,enable_correlations=True)
    clean=stim.Circuit()
    for inst in c.flattened():
        if inst.name in ('PAULI_CHANNEL_1','PAULI_CHANNEL_2','X_ERROR','Z_ERROR'):continue
        clean.append(inst.name,inst.targets_copy(),inst.gate_args_copy())
    ideal=clean.compile_detector_sampler(seed=seed+100000).sample(shots=128,separate_observables=True)
    if np.any(ideal[0]) or np.any(ideal[1]):raise RuntimeError(f'noiseless checks failed {code}/{basis}')
    start=time.perf_counter();d,o=c.compile_detector_sampler(seed=seed).sample(shots=shots,separate_observables=True)
    sample_seconds=time.perf_counter()-start
    start=time.perf_counter();pred=np.asarray(matching.decode_batch(d,enable_correlations=True),dtype=np.bool_).reshape(shots,-1)
    decode_seconds=time.perf_counter()-start
    if pred.shape!=o.shape:raise RuntimeError(f'prediction shape mismatch {code}/{basis}')
    check=min(100,shots)
    scalar=np.asarray([matching.decode(d[i],enable_correlations=True) for i in range(check)],dtype=np.bool_).reshape(check,-1)
    if not np.array_equal(scalar,pred[:check]):raise RuntimeError(f'scalar/batch mismatch {code}/{basis}')
    fails=int(np.count_nonzero(np.any(pred!=o,axis=1)))
    return {'code':code,'basis':basis,'seed':seed,'shots':shots,'failures':fails,'ler':fails/shots,
            'wilson_95':wilson(fails,shots),'sample_seconds':sample_seconds,'decode_seconds':decode_seconds,
            'resources':full_resources(c),'detectors':c.num_detectors,'observables':c.num_observables,
            'scalar_batch_checks':check,'noiseless_checks':128,
            'process_max_rss_kib':int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)}


def wilson(k,n):
    from scipy.stats import norm
    z=float(norm.ppf(.975));p=k/n;den=1+z*z/n
    center=(p+z*z/(2*n))/den;half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [float(max(0.0,center-half)),float(min(1.0,center+half))]


def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');ap.add_argument('--replication',action='store_true');a=ap.parse_args()
    shots=PREFLIGHT_SHOTS if a.preflight else MAIN_SHOTS
    replicate_pre=(2026114201,2026114202,2026114203,2026114204)
    replicate_main=(2026114211,2026114212,2026114213,2026114214)
    seeds=(replicate_pre if a.preflight else replicate_main) if a.replication else (PREFLIGHT_SEEDS if a.preflight else MAIN_SEEDS)
    circuits=[make_circuit(*condition) for condition in CONDITIONS]
    counts=[full_resources(c) for c in circuits]
    keys=('qubits','detectors','observables','two_qubit_interactions','one_qubit_noise_targets','ticks','measurement_flip_targets')
    if any(any(counts[0][k]!=r[k] for k in keys) for r in counts[1:]):
        raise RuntimeError(f'resource mismatch: {counts}')
    if any(r['pauli_channel_2_probability_vectors']!=counts[0]['pauli_channel_2_probability_vectors'] for r in counts[1:]):
        raise RuntimeError('PAULI_CHANNEL_2 vectors differ across factorial cells')
    start=time.perf_counter()
    rows=[one(*condition,seed,shots,a.preflight) for condition,seed in zip(CONDITIONS,seeds,strict=True)]
    elapsed=time.perf_counter()-start
    projection=sum((r['sample_seconds']+r['decode_seconds'])*MAIN_SHOTS/shots for r in rows) if a.preflight else None
    passed=projection is None or projection<=MAX_SECONDS
    label='xzzx_basis_factorial_replication' if a.replication else 'xzzx_basis_factorial'
    out={'status':(label+'_preflight_passed' if passed else label+'_preflight_stopped') if a.preflight else ('development_xzzx_basis_factorial_replication' if a.replication else 'development_xzzx_basis_factorial'),
         'conditions':rows,'resources_equal':True,'equal_resource_fields':list(keys),
         'shots_per_condition':shots,'projected_main_seconds':projection,'max_main_seconds':MAX_SECONDS,
         'elapsed_seconds':elapsed,'new_source_equivalent_samples':shots*len(rows),
         'hardware_assumption':'native CX/XCX/CZ duration and PAULI_CHANNEL_2 distributions equal; unverified',
         'comparisons':{},'scope':'development-only finite-size code and memory-basis comparison; independent streams'}
    by={(r['code'],r['basis']):r for r in rows}
    if all(r['failures']>0 for r in rows):
        css_total=sum(by[('css',basis)]['failures'] for basis in ('x','z'))
        xzzx_total=sum(by[('xzzx',basis)]['failures'] for basis in ('x','z'))
        out['comparisons']={
          'xzzx_x_over_css_x':rr(by[('xzzx','x')]['failures'],shots,by[('css','x')]['failures'],shots),
          'xzzx_z_over_css_z':rr(by[('xzzx','z')]['failures'],shots,by[('css','z')]['failures'],shots),
          'css_x_over_css_z':rr(by[('css','x')]['failures'],shots,by[('css','z')]['failures'],shots),
          'xzzx_x_over_xzzx_z':rr(by[('xzzx','x')]['failures'],shots,by[('xzzx','z')]['failures'],shots),
          'exploratory_equal_weight_memory_basis_mix_xzzx_over_css':rr(xzzx_total,2*shots,css_total,2*shots),
          'exploratory_best_basis_per_code':{'css':min(by[('css',b)]['ler'] for b in ('x','z')),
                                             'xzzx':min(by[('xzzx',b)]['ler'] for b in ('x','z')),
                                             'selection':'post hoc; do not interpret as a predeclared adaptive result'}}
    suffix='_replication' if a.replication else ''
    target=HERE/(f'xzzx_basis_factorial{suffix}_preflight.json' if a.preflight else f'xzzx_basis_factorial{suffix}_results.json')
    target.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'status':out['status'],'projected_main_seconds':projection,'elapsed_seconds':elapsed,'output':str(target)},indent=2))
    return int(a.preflight and not passed)

if __name__=='__main__':raise SystemExit(main())
