"""Fixed checkerboard-H XZZX transform of rotated surface-memory circuits."""
from __future__ import annotations
import argparse,json,resource,sys,time
from pathlib import Path
import numpy as np,pymatching,stim
from scipy.stats import beta,binomtest
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'outputs'/'phase2b_pauli_bias'))
sys.path.insert(0,str(HERE))
from basis_alignment_distance7 import build as source_build
from noise_model import REGIMES,DEFAULT_GATE_P,DEFAULT_MEAS_P
DISTS=(3,5);ROUNDS={3:5,5:9};PROFILES=('x_biased','z_biased')
CONDS=tuple((d,p,code) for d in DISTS for p in PROFILES for code in ('css','xzzx'))
PRE=tuple(range(2026112101,2026112101+len(CONDS)));MAIN=tuple(range(2026112111,2026112111+len(CONDS)))

def transform_xzzx(c):
    coords={}
    oneq_args=next(inst.gate_args_copy() for inst in c.flattened() if inst.name=='PAULI_CHANNEL_1')
    for inst in c.flattened():
        if inst.name=='QUBIT_COORDS':
            coords[inst.targets_copy()[0].value]=inst.gate_args_copy()
    data={q for q,(x,y) in coords.items() if int(x)%2==1 and int(y)%2==1}
    marked={q for q in data if int(xy_sum(coords[q]))%4==2}
    if not marked or marked==data:raise RuntimeError('checkerboard data partition invalid')
    out=stim.Circuit()
    for inst in c.flattened():
        name=inst.name;targets=inst.targets_copy();args=inst.gate_args_copy()
        if name=='CX':
            if len(targets)%2:raise RuntimeError('odd CX target count')
            converted=[]
            for i in range(0,len(targets),2):
                a,b=targets[i].value,targets[i+1].value
                ma,mb=a in marked,b in marked
                if ma and not mb:
                    # H on the CNOT control is not itself a CNOT; compile the exact conjugate H-CX-H and model both added H errors.
                    out.append('H',[a]);out.append('PAULI_CHANNEL_1',[a],oneq_args)
                    out.append('CX',[a,b])
                    out.append('H',[a]);out.append('PAULI_CHANNEL_1',[a],oneq_args)
                elif mb and not ma:out.append('CZ',[a,b])
                else:out.append('CX',[a,b])
            continue
        if name in ('R','RX','M','MX'):
            for t in targets:
                q=t.value;marked_q=q in marked
                n=name
                if marked_q:
                    n={'R':'RX','RX':'R','M':'MX','MX':'M'}[name]
                out.append(n,[q],args)
            continue
        if name in ('X_ERROR','Z_ERROR'):
            for t in targets:
                q=t.value;n=name
                if q in marked:n='Z_ERROR' if name=='X_ERROR' else 'X_ERROR'
                out.append(n,[q],args)
            continue
        if name=='S':
            for t in targets:out.append('SQRT_X' if t.value in marked else 'S',[t.value],args)
            continue
        if name=='S_DAG':
            for t in targets:out.append('SQRT_X_DAG' if t.value in marked else 'S_DAG',[t.value],args)
            continue
        if name=='SQRT_X':
            for t in targets:out.append('S' if t.value in marked else 'SQRT_X',[t.value],args)
            continue
        if name=='SQRT_X_DAG':
            for t in targets:out.append('S_DAG' if t.value in marked else 'SQRT_X_DAG',[t.value],args)
            continue
        if name in ('X','Z','Y'):
            for t in targets:
                n={'X':'Z','Z':'X','Y':'Y'}[name] if t.value in marked else name
                out.append(n,[t.value],args)
            continue
        out.append(name,targets,args)
    return out,sorted(data),sorted(marked)
def xy_sum(xy):return xy[0]+xy[1]

def resources(c):
    flat=list(c.flattened())
    counts={name:0 for name in ('PAULI_CHANNEL_1','PAULI_CHANNEL_2','X_ERROR','Z_ERROR')};targets={'one_qubit':0,'two_qubit_pairs':0,'measurement_flips':0}
    for i in flat:
        if i.name in counts:counts[i.name]+=1
        if i.name=='PAULI_CHANNEL_1':targets['one_qubit']+=len(i.targets_copy())
        elif i.name=='PAULI_CHANNEL_2':targets['two_qubit_pairs']+=len(i.targets_copy())//2
        elif i.name in ('X_ERROR','Z_ERROR'):targets['measurement_flips']+=len(i.targets_copy())
    return {'qubits':c.num_qubits,'detectors':c.num_detectors,'observables':c.num_observables,'pauli_channel_counts':counts,'noise_targets':targets,'ticks':sum(i.name=='TICK' for i in flat),'hadamard_targets':sum(len(i.targets_copy()) for i in flat if i.name=='H')}
def wilson(k,n):
    z=1.959963984540054;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/d;return [float(c-h),float(c+h)]
def rr(a,b):
    if a==0 or b==0:return {'ratio':None,'conditional_exact_95_ci':None,'equal_rate_exact_p':float(binomtest(a,a+b,.5).pvalue) if a+b else None}
    q=beta.ppf([.025,.975],a,a+b and b+1);return {'ratio':a/b,'conditional_exact_95_ci':[float(v/(1-v)) for v in q],'equal_rate_exact_p':float(binomtest(a,a+b,.5).pvalue)}
def run(d,profile,code,n,seed):
    c=source_build('z',profile,distance=d,rounds=ROUNDS[d],bias_ratio=10.)
    if code=='xzzx':c,_,_=transform_xzzx(c)
    dem=c.detector_error_model(decompose_errors=True,approximate_disjoint_errors=.0018);m=pymatching.Matching.from_detector_error_model(dem,enable_correlations=True)
    t=time.perf_counter();det,obs=c.compile_detector_sampler(seed=seed).sample(shots=n,separate_observables=True);ss=time.perf_counter()-t
    t=time.perf_counter();pred=np.asarray(m.decode_batch(det),dtype=np.bool_).reshape(n,-1);ds=time.perf_counter()-t
    if pred.shape!=obs.shape:raise RuntimeError('observable shape mismatch')
    if not np.array_equal(np.asarray([m.decode(det[i]) for i in range(min(100,n))],dtype=np.bool_).reshape(min(100,n),-1),pred[:min(100,n)]):raise RuntimeError('batch/scalar mismatch')
    return {'distance':d,'profile':profile,'code':code,'seed':seed,'shots':n,'failures':int(np.count_nonzero(np.any(pred!=obs,axis=1))),'ler':float(np.count_nonzero(np.any(pred!=obs,axis=1))/n),'wilson_95':wilson(int(np.count_nonzero(np.any(pred!=obs,axis=1))),n),'sampling_seconds':ss,'decode_seconds':ds,'resources':resources(c)}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');ap.add_argument('--shots',type=int,default=500000);a=ap.parse_args()
    if a.shots<=0:ap.error('--shots must be positive')
    source_ok={};core_resource_match={};patterns={}
    for d in DISTS:
      for p in PROFILES:
        c=source_build('z',p,distance=d,rounds=ROUNDS[d],bias_ratio=10.);x,dat,mark=transform_xzzx(c)
        source_ok[f'{d}_{p}']=str(c)==str(source_build('z',p,distance=d,rounds=ROUNDS[d],bias_ratio=10.))
        
        rc,rx=resources(c),resources(x)
        core_resource_match[f'{d}_{p}']=(rc['qubits'],rc['detectors'],rc['observables'],rc['noise_targets']['two_qubit_pairs'],rc['ticks'])==(rx['qubits'],rx['detectors'],rx['observables'],rx['noise_targets']['two_qubit_pairs'],rx['ticks'])
        patterns[f'{d}_{p}']={'data_qubits':len(dat),'hadamard_data_qubits':len(mark),'css':resources(c),'xzzx':resources(x)}
    if not all(source_ok.values()) or not all(core_resource_match.values()):raise RuntimeError('source or resource check failed')
    pre=a.preflight;n=100 if pre else a.shots;seeds=PRE if pre else MAIN;start=time.perf_counter();rows=[]
    for cond,seed in zip(CONDS,seeds,strict=True):rows.append(run(*cond,n,seed))
    elapsed=time.perf_counter()-start;comparisons=[]
    for d in DISTS:
      for p in PROFILES:
        css=next(r for r in rows if r['distance']==d and r['profile']==p and r['code']=='css');x=next(r for r in rows if r['distance']==d and r['profile']==p and r['code']=='xzzx')
        comparisons.append({'distance':d,'profile':p,'css_failures':css['failures'],'xzzx_failures':x['failures'],'css_ler':css['ler'],'xzzx_ler':x['ler'],'xzzx_over_css_rate_ratio':rr(x['failures'],css['failures'])})
    out={'status':'preflight' if pre else 'development_codesign_screen','stim_version':stim.__version__,'pymatching_version':pymatching.__version__,'gate_meas_p':.003,'bias_ratio':10.,'distance_rounds':ROUNDS,'source_css_reproductions':source_ok,'core_resource_match':core_resource_match,'resource_details':patterns,'shots_per_condition':n,'conditions':rows,'xzzx_vs_css':comparisons,'elapsed_seconds':elapsed,'projected_main_seconds':sum((r['sampling_seconds']+r['decode_seconds'])*(500000/n) for r in rows) if pre else None,'stochastic_circuit_shots':n*len(rows),'scope':'fixed XZZX local-Clifford code/circuit comparison with abstract logical-Z memory task held fixed; not a threshold or arbitrary qubit process claim'}
    name='xzzx_codesign_preflight.json' if pre else 'xzzx_codesign_results.json';(HERE/name).write_text(json.dumps(out,indent=2)+'\n');print(f'Wrote {HERE/name}; elapsed={elapsed:.2f}s; projection={out["projected_main_seconds"]}')
    for r in comparisons:print(r)
    if pre and out['projected_main_seconds']>300:return 1
    return 0
if __name__=='__main__':raise SystemExit(main())
