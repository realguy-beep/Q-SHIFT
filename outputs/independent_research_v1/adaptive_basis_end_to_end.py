"""Direct development test of detector-only basis selection on fresh streams."""
from __future__ import annotations
import json,sys,time
from pathlib import Path
import numpy as np
import pymatching
from scipy.stats import beta
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from bias_identification import feature_masks,make_features,FEATURES,exact_interval
from basis_alignment_distance7 import build
MODEL=json.loads((HERE/'bias_identification_results.json').read_text())['training']
W=np.asarray(MODEL['weights']);B=float(MODEL['intercept'])
PROFILES=('x_biased','z_biased'); RATIOS=(2.,5.,10.); CONDITIONS=[(r,p) for r in RATIOS for p in PROFILES]
PREFLIGHT_SEEDS=tuple(range(2026111801,2026111819));MAIN_SEEDS=tuple(range(2026111821,2026111839))

def source_check():
    from noise_model import build_circuit as source_build
    out={}
    for ratio in RATIOS:
      for p in PROFILES:
       for b in ('x','z'):
        out[f'{ratio}_{p}_{b}']=str(build(b,p,3,5,bias_ratio=ratio))==str(source_build(b,p,distance=3,rounds=5,bias_ratio=ratio))
    if not all(out.values()):raise RuntimeError('generated d3 circuit differs from source builder')
    return out

def sampler(basis,profile,ratio,n,seed):
    c=build(basis,profile,3,5,bias_ratio=ratio)
    dem=c.detector_error_model(decompose_errors=True,approximate_disjoint_errors=.0018)
    matching=pymatching.Matching.from_detector_error_model(dem,enable_correlations=True)
    t=time.perf_counter();det,obs=c.compile_detector_sampler(seed=seed).sample(shots=n,separate_observables=True);sampling=time.perf_counter()-t
    t=time.perf_counter();pred=np.asarray(matching.decode_batch(det),dtype=np.bool_).reshape(n,-1);decoding=time.perf_counter()-t
    if pred.shape!=obs.shape:raise RuntimeError('decoder observable shape mismatch')
    check=min(n,100);scalar=np.asarray([matching.decode(det[i]) for i in range(check)],dtype=np.bool_).reshape(check,-1)
    if not np.array_equal(scalar,pred[:check]):raise RuntimeError('batch/scalar decode mismatch')
    return np.any(pred!=obs,axis=1),sampling,decoding,c.num_detectors

def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');a=ap.parse_args();start=time.perf_counter();copies=source_check()
    training_means=np.asarray(MODEL['means']);training_scores=training_means@W+B
    if not (training_scores[0] < 0 < training_scores[1]):raise RuntimeError(f'classifier sign check failed: {training_scores}')
    pre=a.preflight;seeds=PREFLIGHT_SEEDS if pre else MAIN_SEEDS;si=0;cache=[];rows=[]
    calibration_n=1000 if pre else 500000;logical_n=1000 if pre else 100000;windows=1000
    for ratio,profile in CONDITIONS:
        cal_seed=seeds[si];si+=1
        c=build('z',profile,3,5,bias_ratio=ratio);masks=feature_masks(c,3,5)
        t=time.perf_counter();det=c.compile_detector_sampler(seed=cal_seed).sample(shots=calibration_n);cal_sampling=time.perf_counter()-t
        feats=make_features(det,masks)
        if not np.isfinite(feats).all():raise RuntimeError('nonfinite calibration features')
        if pre:
            rows.append({'ratio':ratio,'profile':profile,'kind':'calibration','shots':calibration_n,'seed':cal_seed,'sampling_seconds':cal_sampling,'detectors':c.num_detectors})
            for basis in ('x','z'):
                seed=seeds[si];si+=1;fails,ss,ds,nd=sampler(basis,profile,ratio,logical_n,seed)
                rows.append({'ratio':ratio,'profile':profile,'basis':basis,'kind':'logical','shots':logical_n,'seed':seed,'sampling_seconds':ss,'decode_seconds':ds,'detectors':nd,'failures_preflight_only':int(fails.sum())})
            continue
        cal_windows=feats.reshape(windows,500,len(FEATURES)).mean(axis=1)
        select_x=(cal_windows@W+B)<0
        per_basis={}
        for basis in ('x','z'):
            seed=seeds[si];si+=1;fails,ss,ds,nd=sampler(basis,profile,ratio,logical_n,seed)
            per_basis[basis]=fails.reshape(windows,100).sum(axis=1).astype(int)
            rows.append({'ratio':ratio,'profile':profile,'basis':basis,'kind':'logical','shots':logical_n,'seed':seed,'sampling_seconds':ss,'decode_seconds':ds,'detectors':nd})
        selected=np.where(select_x,per_basis['x'],per_basis['z'])
        oracle=per_basis['x'] if profile=='x_biased' else per_basis['z']
        rows.append({'ratio':ratio,'profile':profile,'kind':'policy','calibration_seed':cal_seed,'calibration_shots':calibration_n,'x_selected_windows':int(select_x.sum()),'z_selected_windows':int((~select_x).sum()),'policy_failures_by_window':selected.tolist(),'fixed_x_failures_by_window':per_basis['x'].tolist(),'fixed_z_failures_by_window':per_basis['z'].tolist(),'oracle_failures_by_window':oracle.tolist(),'policy_failures':int(selected.sum()),'fixed_x_failures':int(per_basis['x'].sum()),'fixed_z_failures':int(per_basis['z'].sum()),'oracle_failures':int(oracle.sum())})
    elapsed=time.perf_counter()-start
    if pre:
        projected=sum((r['sampling_seconds']+r.get('decode_seconds',0))*(500 if r['kind']=='calibration' else 100) for r in rows)
        out={'status':'preflight','source_builder_matches':copies,'classifier_training_score_check':training_scores.tolist(),'rows':rows,'projected_main_sample_and_decode_seconds':projected,'elapsed_seconds':elapsed,'stochastic_circuit_shots':sum(r['shots'] for r in rows)}
        path=HERE/'adaptive_basis_end_to_end_preflight.json';path.write_text(json.dumps(out,indent=2)+'\n');print(f'Wrote {path}; projected {projected:.1f}s');return 1 if projected>300 else 0
    policy=[r for r in rows if r['kind']=='policy'];rng=np.random.default_rng(2026111891);summary=[];boot_n=5000
    for ratio in RATIOS:
        selected=[r for r in policy if r['ratio']==ratio];profiles={r['profile']:r for r in selected}
        total=2*100000
        observed={}
        for name in ('policy','fixed_x','fixed_z','oracle'):
            observed[name]=sum(r[f'{name}_failures'] for r in selected)/total
        bx=[];bz=[]
        for profile,r in profiles.items():
            pol=np.asarray(r['policy_failures_by_window']);fz=np.asarray(r['fixed_z_failures_by_window'])
            idx=rng.integers(0,windows,size=(boot_n,windows))
            bp=pol[idx].sum(axis=1)/100000;bf=fz[idx].sum(axis=1)/100000
            (bx if profile=='x_biased' else bz).append((bp,bf))
        boot_delta=((bx[0][0]+bz[0][0])/2)-((bx[0][1]+bz[0][1])/2)
        delta=float(observed['policy']-observed['fixed_z'])
        summary.append({'bias_ratio':ratio,'profiles_equally_weighted':True,'policy_ler':observed['policy'],'fixed_x_ler':observed['fixed_x'],'fixed_z_ler':observed['fixed_z'],'oracle_ler':observed['oracle'],'policy_minus_fixed_z':delta,'policy_minus_fixed_z_cluster_bootstrap_95_ci':[float(np.quantile(boot_delta,.025)),float(np.quantile(boot_delta,.975))],'relative_reduction_vs_fixed_z':1-observed['policy']/observed['fixed_z'],'calibration_shots_per_profile_job':500,'logical_shots_per_profile_basis':100000,'policy_confusion_by_profile':{r['profile']:{'x_selected_windows':r['x_selected_windows'],'z_selected_windows':r['z_selected_windows']} for r in selected}})
    out={'status':'development_end_to_end_validation','distance':3,'rounds':5,'gate_and_measurement_p':.003,'training_classifier':'frozen binary d3 ratio10 LDA from independent training data','profiles_equally_weighted':True,'decoder':'correlation-enabled PyMatching from per-circuit approximate DEM threshold .0018','source_builder_matches':copies,'classifier_training_score_check':training_scores.tolist(),'condition_rows':rows,'summary':summary,'bootstrap_replicates':boot_n,'bootstrap_seed':2026111891,'elapsed_seconds':elapsed,'stochastic_circuit_shots':3*(2*500000+2*2*100000),'scope':'direct synthetic selected-policy development check; calibration/test streams independent; no confirmatory or hardware evidence'}
    path=HERE/'adaptive_basis_end_to_end_results.json';path.write_text(json.dumps(out,indent=2)+'\n');print(f'Wrote {path}; elapsed={elapsed:.1f}s')
    for s in summary:print(s)
    return 0
if __name__=='__main__':raise SystemExit(main())
