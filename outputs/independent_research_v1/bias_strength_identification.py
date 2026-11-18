"""Three-class detector-only bias-strength robustness test."""
from __future__ import annotations
import json,sys,time
from pathlib import Path
import numpy as np
from scipy.stats import beta
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from bias_identification import feature_masks,make_features,ROUNDS,FEATURES,exact_interval,WINDOWS
from basis_alignment_distance7 import build
TRAIN_SEEDS={'balanced':2026111701,'x_biased':2026111702,'z_biased':2026111703}
DISTANCES=(3,5,7); RATIOS=(1.,2.,5.,10.); WINDOWS=1000; BUDGETS=(25,100,500)
CONDS=[]
for d in DISTANCES:
    CONDS.append((d,'balanced','x_biased',1.0))
    for ratio in (2.,5.,10.):
        CONDS.extend([(d,'x_biased','x_biased',ratio),(d,'z_biased','z_biased',ratio)])
VALID_SEEDS={condition:seed for condition,seed in zip(CONDS,range(2026111711,2026111711+len(CONDS)),strict=True)}
def draw(d,regime,ratio,n,seed):
    rounds=ROUNDS[d];c=build('z',regime,d,rounds,bias_ratio=ratio);masks=feature_masks(c,d,rounds)
    t=time.perf_counter();det=c.compile_detector_sampler(seed=seed).sample(shots=n);seconds=time.perf_counter()-t
    return make_features(det,masks),seconds

def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');a=ap.parse_args();started=time.perf_counter()
    if a.preflight:
        rows=[]
        for condition,seed in VALID_SEEDS.items():
            d,label,regime,ratio=condition;f,sec=draw(d,regime,ratio,1000,seed)
            rows.append({'distance':d,'profile':label,'regime':regime,'bias_ratio':ratio,'seed':seed,'shots':1000,'sampling_seconds':sec,'finite':bool(np.isfinite(f).all())})
        projected=sum(r['sampling_seconds']*(500000/1000) for r in rows)
        out={'status':'preflight','conditions':rows,'projected_sampling_seconds':projected,'elapsed_seconds':time.perf_counter()-started,'stochastic_circuit_shots':len(rows)*1000}
        path=HERE/'bias_strength_identification_preflight.json';path.write_text(json.dumps(out,indent=2)+'\n');print(f'Wrote {path}; projected validation sampling {projected:.1f}s');return int(projected>300)
    train_profiles=[('balanced','x_biased',1.),('x_biased','x_biased',10.),('z_biased','z_biased',10.)]
    xs=[];ys=[];train_rows=[]
    for cls,(name,regime,ratio) in enumerate(train_profiles):
        f,sec=draw(3,regime,ratio,100000,TRAIN_SEEDS[name]);xs.append(f);ys.extend([cls]*len(f));train_rows.append({'class':name,'distance':3,'bias_ratio':ratio,'seed':TRAIN_SEEDS[name],'shots':len(f),'sampling_seconds':sec})
    X=np.vstack(xs);y=np.asarray(ys);means=np.stack([X[y==k].mean(axis=0) for k in range(3)])
    resid=np.vstack([X[y==k]-means[k] for k in range(3)]);cov=np.cov(resid,rowvar=False);shrink=.1*float(np.trace(cov))/cov.shape[0];cov+=shrink*np.eye(cov.shape[0]);inv=np.linalg.inv(cov)
    bias=means@inv;offset=-.5*np.einsum('ij,jk,ik->i',means,inv,means)
    results=[];val_seconds=0.
    for cond,seed in VALID_SEEDS.items():
        d,label,regime,ratio=cond;f,sec=draw(d,regime,ratio,WINDOWS*500,seed);val_seconds+=sec;w=f.reshape(WINDOWS,500,len(FEATURES));row={'distance':d,'profile':label,'regime':regime,'bias_ratio':ratio,'seed':seed,'windows':WINDOWS,'sampling_seconds':sec,'budget_results':[]}
        truth={'balanced':0,'x_biased':1,'z_biased':2}[label]
        for n in BUDGETS:
            block=w[:,:n,:].mean(axis=1);scores=block@bias.T+offset;pred=np.argmax(scores,axis=1);correct=int(np.count_nonzero(pred==truth));
            # For the action, both bases are equivalent at ratio 1; biased profiles require the correct direction.
            action_correct=int(np.count_nonzero((pred==1) if label=='x_biased' else (pred==2) if label=='z_biased' else np.ones(WINDOWS,dtype=bool)))
            row['budget_results'].append({'calibration_shots':n,'class_correct':correct,'class_accuracy':correct/WINDOWS,'exact_95_ci':exact_interval(correct,WINDOWS),'basis_action_correct':action_correct,'basis_action_accuracy':action_correct/WINDOWS})
        results.append(row)
    summary=[]
    for d in DISTANCES:
        for ratio in RATIOS:
            group=[r for r in results if r['distance']==d and r['bias_ratio']==ratio]
            for n in BUDGETS:
                cells=[next(x for x in r['budget_results'] if x['calibration_shots']==n) for r in group]
                correct=sum(x['class_correct'] for x in cells);total=sum(x['windows'] for x in group)
                action=sum(x['basis_action_correct'] for x in cells)
                summary.append({'distance':d,'bias_ratio':ratio,'calibration_shots':n,'profile_classes':[r['profile'] for r in group],'class_correct':correct,'windows':total,'class_accuracy':correct/total,'exact_95_ci':exact_interval(correct,total),'basis_action_accuracy':action/total})
    out={'status':'development_validation','features':FEATURES,'feature_definition':'normalized detector event rates grouped by coord_x+coord_y mod4 ==0 or2, and early/late time halves','calibration_circuit':'fixed Z-memory; detector outcomes only','class_names':['balanced','x_biased','z_biased'],'train':{'distance':3,'shots_per_class':100000,'seeds':TRAIN_SEEDS,'profiles':train_profiles,'covariance_shrinkage_fraction':.1,'means':means.tolist(),'discriminant_weights':bias.tolist(),'offsets':offset.tolist(),'rows':train_rows},'validation_conditions':results,'summary_by_distance_ratio_budget':summary,'windows_per_profile':WINDOWS,'elapsed_seconds':time.perf_counter()-started,'validation_sampling_seconds':val_seconds,'stochastic_circuit_shots':300000+len(VALID_SEEDS)*WINDOWS*500,'scope':'cross-strength detector-only profile classification; no end-to-end adaptive LER claim'}
    path=HERE/'bias_strength_identification_results.json';path.write_text(json.dumps(out,indent=2)+'\n');print(f'Wrote {path}; elapsed={out["elapsed_seconds"]:.1f}s')
    for x in summary:print(x)
    return 0
if __name__=='__main__':raise SystemExit(main())
