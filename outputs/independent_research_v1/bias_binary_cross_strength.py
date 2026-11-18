"""Rescore held-out strength streams with the previously frozen binary classifier."""
from __future__ import annotations
import json,sys,time
from pathlib import Path
import numpy as np
from scipy.stats import beta
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from bias_identification import feature_masks,make_features,ROUNDS,FEATURES,exact_interval,WINDOWS,PROFILES
from basis_alignment_distance7 import build
from bias_strength_identification import CONDS,VALID_SEEDS,DISTANCES,BUDGETS
BINARY=json.loads((HERE/'bias_identification_results.json').read_text())
W=np.asarray(BINARY['training']['weights']);B=float(BINARY['training']['intercept'])
def main():
    started=time.perf_counter();by=[]
    for d,profile,regime,ratio in CONDS:
        seed=VALID_SEEDS[(d,profile,regime,ratio)];rounds=ROUNDS[d];c=build('z',regime,d,rounds,bias_ratio=ratio);masks=feature_masks(c,d,rounds)
        det=c.compile_detector_sampler(seed=seed).sample(shots=WINDOWS*500);f=make_features(det,masks).reshape(WINDOWS,500,len(FEATURES));true=None if profile=='balanced' else PROFILES.index(profile)
        for n in BUDGETS:
            block=f[:,:n,:].mean(axis=1);pred=((block@W+B)>0).astype(int)
            if true is None:by.append({'distance':d,'bias_ratio':ratio,'profile':profile,'calibration_shots':n,'windows':WINDOWS,'x_selected':int(np.count_nonzero(pred==0)),'z_selected':int(np.count_nonzero(pred==1)),'direction_accuracy':None})
            else:
                correct=int(np.count_nonzero(pred==true));by.append({'distance':d,'bias_ratio':ratio,'profile':profile,'calibration_shots':n,'windows':WINDOWS,'correct_direction':correct,'accuracy':correct/WINDOWS,'exact_95_ci':exact_interval(correct,WINDOWS)})
    summary=[]
    for d in DISTANCES:
      for ratio in (2.,5.,10.):
        for n in BUDGETS:
          rows=[r for r in by if r['distance']==d and r['bias_ratio']==ratio and r['calibration_shots']==n]
          k=sum(r['correct_direction'] for r in rows);total=sum(r['windows'] for r in rows)
          summary.append({'distance':d,'bias_ratio':ratio,'calibration_shots':n,'correct_direction':k,'windows':total,'balanced_direction_accuracy':k/total,'exact_95_ci':exact_interval(k,total)})
    out={'status':'frozen_binary_classifier_cross_strength_rescore','classifier_source':'unchanged two-class LDA trained on independent d3 ratio10 samples in bias_identification_results.json','validation_samples':'same deterministic validation seeds and circuits as the separately reported three-class stress test; no new random streams and no model fit','individual_cells':by,'direction_accuracy_by_distance_ratio_budget':summary,'elapsed_seconds':time.perf_counter()-started,'scope':'held-out cross-strength scoring only; not end-to-end adaptive LER'}
    p=HERE/'bias_binary_cross_strength_results.json';p.write_text(json.dumps(out,indent=2)+'\n');print(f'Wrote {p}; elapsed={out["elapsed_seconds"]:.1f}s')
    for r in summary:print(r)
if __name__=='__main__':main()
