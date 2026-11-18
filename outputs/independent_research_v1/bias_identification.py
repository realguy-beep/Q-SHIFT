"""Detector-only X/Z bias classifier feasibility, train/validation separated."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
import stim
from scipy.stats import beta
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from basis_alignment_distance7 import build
DISTANCES=(3,5,7); ROUNDS={3:5,5:9,7:13}
PROFILES=('x_biased','z_biased')
FEATURES=('type0_early','type0_late','type2_early','type2_late')
PREFLIGHT_SEEDS={(3,'x_biased'):2026111591,(3,'z_biased'):2026111592,(5,'x_biased'):2026111593,(5,'z_biased'):2026111594,(7,'x_biased'):2026111595,(7,'z_biased'):2026111596}
TRAIN_SEEDS={'x_biased':2026111601,'z_biased':2026111602}
VALID_SEEDS={(3,'x_biased'):2026111611,(3,'z_biased'):2026111612,(5,'x_biased'):2026111613,(5,'z_biased'):2026111614,(7,'x_biased'):2026111615,(7,'z_biased'):2026111616}
BUDGETS=(25,100,500); WINDOWS=1000

def feature_masks(circuit,distance,rounds):
    coords=circuit.get_detector_coordinates()
    if len(coords)!=circuit.num_detectors:raise RuntimeError('detector coordinate count mismatch')
    xy=np.asarray([coords[i] for i in range(circuit.num_detectors)],dtype=float)
    parity=np.rint(xy[:,0]+xy[:,1]).astype(int)%4
    t=xy[:,2]
    masks=[]
    for typ in (0,2):
        for early in (True,False):
            temporal=(t<=rounds/2) if early else (t>rounds/2)
            mask=(parity==typ)&temporal
            if not np.any(mask):raise RuntimeError(f'empty detector feature bucket d={distance},type={typ},early={early}')
            masks.append(mask)
    return masks

def make_features(detectors,masks):
    return np.column_stack([detectors[:,m].mean(axis=1) for m in masks])

def sample_features(distance,profile,n,seed):
    rounds=ROUNDS[distance]; c=build('z',profile,distance,rounds); masks=feature_masks(c,distance,rounds)
    started=time.perf_counter(); det=c.compile_detector_sampler(seed=seed).sample(shots=n); elapsed=time.perf_counter()-started
    f=make_features(det,masks)
    if not np.all(np.isfinite(f)):raise RuntimeError('nonfinite detector feature')
    return f,elapsed,c

def exact_interval(k,n):
    lo=0.0 if k==0 else float(beta.ppf(.025,k,n-k+1))
    hi=1.0 if k==n else float(beta.ppf(.975,k+1,n-k))
    return [lo,hi]

def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');a=ap.parse_args();started=time.perf_counter()
    # Verify calibration circuit generator remains source-identical at d=3.
    from noise_model import REGIMES,build_circuit as source_build
    source={f'z_{r}':str(build('z',r,3,5))==str(source_build('z',r,distance=3,rounds=5)) for r in REGIMES}
    if not all(source.values()):raise RuntimeError('d3 calibration circuit differs from source')
    if a.preflight:
        checks=[]
        for d in DISTANCES:
            for profile in PROFILES:
                f,seconds,c=sample_features(d,profile,1000,PREFLIGHT_SEEDS[d,profile])
                checks.append({'distance':d,'profile':profile,'shots':1000,'seconds':seconds,'feature_means':f.mean(axis=0).tolist(),'feature_finite':bool(np.all(np.isfinite(f))),'bucket_counts':[int(m.sum()) for m in feature_masks(c,d,ROUNDS[d])]})
        projected=sum(row['seconds']*(500000/1000) for row in checks)
        out={'status':'preflight','stim_version':stim.__version__,'d3_source_byte_identical':source,'checks':checks,'projected_validation_sampling_seconds':projected,'elapsed_seconds':time.perf_counter()-started,'stochastic_circuit_shots':6000}
        path=HERE/'bias_identification_preflight.json';path.write_text(json.dumps(out,indent=2)+'\n');print(f'Wrote {path}; projected validation sampling={projected:.1f}s')
        return 1 if projected>300 else 0
    # Fresh supervised training stream: labels known to the synthetic calibration designer.
    train=[];labels=[]
    train_rows=[]
    for label,profile in enumerate(PROFILES):
        f,sec,_=sample_features(3,profile,100000,TRAIN_SEEDS[profile]);train.append(f);labels.extend([label]*len(f));train_rows.append({'profile':profile,'distance':3,'shots':len(f),'seed':TRAIN_SEEDS[profile],'sampling_seconds':sec})
    X=np.vstack(train); y=np.asarray(labels); means=np.stack([X[y==k].mean(axis=0) for k in (0,1)])
    residual=np.vstack([X[y==k]-means[k] for k in (0,1)])
    cov=np.cov(residual,rowvar=False); shrink=.1*float(np.trace(cov))/cov.shape[0]
    cov=cov+shrink*np.eye(cov.shape[0]);w=np.linalg.solve(cov,means[1]-means[0]);intercept=-.5*float((means[0]+means[1])@w)
    results=[];validation_seconds=0.
    for d in DISTANCES:
        for profile in PROFILES:
            seed=VALID_SEEDS[d,profile]; f,sec,c=sample_features(d,profile,WINDOWS*500,seed);validation_seconds+=sec
            windows=f.reshape(WINDOWS,500,len(FEATURES)); row={'distance':d,'profile':profile,'seed':seed,'independent_windows':WINDOWS,'sampling_seconds':sec,'budget_results':[]}
            true=PROFILES.index(profile)
            for n in BUDGETS:
                block=windows[:,:n,:].mean(axis=1); pred=((block@w+intercept)>0).astype(int);correct=int(np.count_nonzero(pred==true))
                row['budget_results'].append({'calibration_shots':n,'correct':correct,'windows':WINDOWS,'accuracy':correct/WINDOWS,'exact_95_ci':exact_interval(correct,WINDOWS)})
            results.append(row)
    agg=[]
    for d in DISTANCES:
        for n in BUDGETS:
            rows=[r for r in results if r['distance']==d]
            correct=sum(next(x for x in r['budget_results'] if x['calibration_shots']==n)['correct'] for r in rows)
            agg.append({'distance':d,'calibration_shots':n,'correct':correct,'windows':2*WINDOWS,'balanced_accuracy':correct/(2*WINDOWS),'exact_95_ci':exact_interval(correct,2*WINDOWS)})
    out={'status':'development_validation','stim_version':stim.__version__,'calibration_circuit':'fixed Z-memory; detector outcomes only; observable bits not sampled or used','feature_names':FEATURES,'feature_definition':'normalized detector event rates grouped by (coord_x+coord_y) mod 4 in {0,2}, then early/late time halves','d3_source_byte_identical':source,'training':{'shots_per_profile':100000,'seeds':TRAIN_SEEDS,'profiles':list(PROFILES),'means':means.tolist(),'covariance_shrinkage_fraction':.1,'weights':w.tolist(),'intercept':intercept,'training_rows':train_rows},'validation':results,'balanced_accuracy_by_distance_and_budget':agg,'windows_per_profile_distance':WINDOWS,'elapsed_seconds':time.perf_counter()-started,'validation_sampling_seconds':validation_seconds,'stochastic_circuit_shots':200000+len(DISTANCES)*len(PROFILES)*WINDOWS*500,'scope':'detector-only profile identification feasibility; no end-to-end adaptive LER claim'}
    path=HERE/'bias_identification_results.json';path.write_text(json.dumps(out,indent=2)+'\n');print(f'Wrote {path}; elapsed={out["elapsed_seconds"]:.1f}s')
    for r in agg:print(r)
    return 0
if __name__=='__main__':raise SystemExit(main())
