"""Distance-7 extension of known-profile memory-basis alignment screen."""
from __future__ import annotations
import argparse, json, re, resource, sys, time
from pathlib import Path
import numpy as np
import pymatching
import stim
from scipy.stats import beta, binomtest
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'outputs'/'phase2b_pauli_bias'))
from noise_model import (DEFAULT_GATE_P,DEFAULT_MEAS_P,DEFAULT_BIAS_RATIO,MEMORY_BASES,REGIMES,one_qubit_probabilities,two_qubit_probabilities,build_circuit as source_build_circuit)
D=7; R=13
TEST_REGIMES=('x_biased','z_biased')
CONDS=tuple((b,r) for r in TEST_REGIMES for b in MEMORY_BASES)
PREFLIGHT_SEEDS=tuple(range(2026111501,2026111505))
MAIN_SEEDS=tuple(range(2026111511,2026111515))
def build(basis,regime,distance=D,rounds=R):
    p1=one_qubit_probabilities(regime,DEFAULT_GATE_P,DEFAULT_BIAS_RATIO)
    p2=two_qubit_probabilities(regime,DEFAULT_GATE_P,DEFAULT_BIAS_RATIO)
    c=stim.Circuit.generated(f'surface_code:rotated_memory_{basis}',distance=distance,rounds=rounds,after_clifford_depolarization=DEFAULT_GATE_P,before_measure_flip_probability=DEFAULT_MEAS_P)
    body=str(c)
    body,n1=re.subn(r'DEPOLARIZE1\([^)]*\)','PAULI_CHANNEL_1('+','.join(format(v,'.17g') for v in p1)+')',body)
    body,n2=re.subn(r'DEPOLARIZE2\([^)]*\)','PAULI_CHANNEL_2('+','.join(format(v,'.17g') for v in p2)+')',body)
    if not n1 or not n2: raise RuntimeError('noise substitution failed')
    return stim.Circuit(body)
def wilson(k,n):
    z=1.959963984540054;p=k/n;d=1+z*z/n
    c=(p+z*z/(2*n))/d;h=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [float(c-h),float(c+h)]
def rr(a,b):
    if not a or not b:return {'ratio':None,'conditional_exact_95_ci':None,'equal_rate_exact_p':float(binomtest(a,a+b,.5).pvalue)}
    q=beta.ppf([.025,.975],a,b+1)
    return {'ratio':float(a/b),'conditional_exact_95_ci':[float(x/(1-x)) for x in q],'equal_rate_exact_p':float(binomtest(a,a+b,.5).pvalue)}
def run(basis,regime,n,seed):
    c=build(basis,regime); dem=c.detector_error_model(decompose_errors=True,approximate_disjoint_errors=.0018)
    m=pymatching.Matching.from_detector_error_model(dem,enable_correlations=True)
    t=time.perf_counter();det,obs=c.compile_detector_sampler(seed=seed).sample(shots=n,separate_observables=True);sample_s=time.perf_counter()-t
    t=time.perf_counter();pred=np.asarray(m.decode_batch(det),dtype=np.bool_);decode_s=time.perf_counter()-t
    pred=pred.reshape(n,-1)
    if pred.shape != obs.shape:raise RuntimeError(f'batch result shape {pred.shape} != observable shape {obs.shape}')
    # Scalar agreement is checked on every preflight syndrome, and the first 100
    # main-run syndromes as an implementation guard.
    check=min(n,100)
    scalar=np.asarray([m.decode(det[i]) for i in range(check)],dtype=np.bool_).reshape(check,-1)
    if not np.array_equal(pred[:check],scalar):raise RuntimeError('decode_batch disagrees with scalar decode')
    fails=int(np.count_nonzero(np.any(pred!=obs,axis=1)))
    return {'memory_basis':basis,'regime':regime,'seed':seed,'shots':n,'physical_qubits':int(c.num_qubits),'detectors':int(c.num_detectors),'observables':int(c.num_observables),'two_qubit_channel_pairs':sum(len(i.targets_copy())//2 for i in c.flattened() if i.name=='PAULI_CHANNEL_2'),'failures':fails,'ler':fails/n,'wilson_95':wilson(fails,n),'sampling_seconds':sample_s,'batched_decode_seconds':decode_s,'seconds_per_decode':decode_s/n,'batch_scalar_checks':check,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');ap.add_argument('--shots',type=int,default=500000);a=ap.parse_args()
    if a.shots<1:ap.error('--shots must be positive')
    # Exact source check at d3 and matched resource check at d7.
    d3={f'{b}_{r}':str(build(b,r,3,5))==str(source_build_circuit(b,r,distance=3,rounds=5)) for r in REGIMES for b in MEMORY_BASES}
    if not all(d3.values()):raise RuntimeError('d3 builder differs from source')
    pre=a.preflight;n=100 if pre else a.shots;seeds=PREFLIGHT_SEEDS if pre else MAIN_SEEDS
    start=time.perf_counter();rows=[run(b,r,n,s) for (b,r),s in zip(CONDS,seeds,strict=True)];elapsed=time.perf_counter()-start
    matched=all(len({(x['physical_qubits'],x['detectors'],x['observables'],x['two_qubit_channel_pairs']) for x in rows if x['regime']==reg})==1 for reg in TEST_REGIMES)
    if not matched:raise RuntimeError('basis circuits are not resource matched')
    comparisons=[]
    for regime,aligned in [('x_biased','x'),('z_biased','z')]:
        x={r['memory_basis']:r for r in rows if r['regime']==regime};al=x[aligned];mis=x['z' if aligned=='x' else 'x']
        comparisons.append({'regime':regime,'aligned_basis':aligned,'mismatched_basis':mis['memory_basis'],'aligned_failures':al['failures'],'mismatched_failures':mis['failures'],'aligned_ler':al['ler'],'mismatched_ler':mis['ler'],'aligned_over_mismatched_rate_ratio':rr(al['failures'],mis['failures'])})
    out={'status':'preflight' if pre else 'distance_7_development_screen','stim_version':stim.__version__,'pymatching_version':pymatching.__version__,'distance':D,'rounds':R,'gate_error_probability':DEFAULT_GATE_P,'measurement_error_probability':DEFAULT_MEAS_P,'bias_ratio':DEFAULT_BIAS_RATIO,'d3_builder_byte_identical_to_source':d3,'matched_resources_by_regime':matched,'shots_per_condition':n,'conditions':rows,'aligned_vs_mismatched':comparisons,'elapsed_seconds':elapsed,'projected_main_seconds':sum((r['sampling_seconds']+r['batched_decode_seconds'])*(500000/n) for r in rows) if pre else None,'stochastic_circuit_shots':n*len(rows),'scope':'third finite-distance point for fixed known-profile basis alignment; not threshold or adaptive-policy evidence'}
    path=HERE/('basis_alignment_d7_preflight.json' if pre else 'basis_alignment_d7_results.json');path.write_text(json.dumps(out,indent=2)+'\n');print(f'Wrote {path}; elapsed={elapsed:.3f}s; resources_match={matched}')
    for x in comparisons:print(x['regime'],x['aligned_ler'],x['mismatched_ler'],x['aligned_over_mismatched_rate_ratio'])
    if pre and out['projected_main_seconds']>300:print('sampling+batched-decode projection exceeds five-minute cap');return 1
    return 0
if __name__=='__main__':raise SystemExit(main())
