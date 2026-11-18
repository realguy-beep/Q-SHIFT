"""Exploratory prefix-budget rescore of frozen end-to-end streams; no new seeds."""
import json,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from adaptive_basis_end_to_end import W,B
from bias_identification import feature_masks,make_features,FEATURES
from basis_alignment_distance7 import build
SOURCE=json.load(open(HERE/'adaptive_basis_end_to_end_results.json'))
POLICY=[r for r in SOURCE['condition_rows'] if r['kind']=='policy'];BY={(r['ratio'],r['profile']):r for r in POLICY}
def main():
 rng=np.random.default_rng(2026111892);summ=[];details=[]
 for ratio in (2.,5.,10.):
  for n in (25,100,500):
   observed={'policy':0,'fixed_x':0,'fixed_z':0,'oracle':0};conf={}
   boot={k:[] for k in ('policy','fixed_z')}
   profile_boot=[]
   for profile in ('x_biased','z_biased'):
    row=BY[(ratio,profile)];c=build('z',profile,3,5,bias_ratio=ratio);m=feature_masks(c,3,5)
    det=c.compile_detector_sampler(seed=row['calibration_seed']).sample(shots=500000);f=make_features(det,m).reshape(1000,500,len(FEATURES))
    blocks=f[:,:n,:].mean(axis=1);choose_x=blocks@W+B<0
    arms={'x':np.asarray(row['fixed_x_failures_by_window']),'z':np.asarray(row['fixed_z_failures_by_window'])}
    pol=np.where(choose_x,arms['x'],arms['z']);oracle=arms['x'] if profile=='x_biased' else arms['z']
    observed['policy']+=int(pol.sum());observed['fixed_x']+=int(arms['x'].sum());observed['fixed_z']+=int(arms['z'].sum());observed['oracle']+=int(oracle.sum())
    idx=rng.integers(0,1000,size=(5000,1000));bp=pol[idx].sum(axis=1)/100000;bf=arms['z'][idx].sum(axis=1)/100000;profile_boot.append((bp,bf))
    conf[profile]={'x_selected_windows':int(choose_x.sum()),'z_selected_windows':int((~choose_x).sum())}
    details.append({'ratio':ratio,'profile':profile,'calibration_shots':n,'x_selected':int(choose_x.sum()),'z_selected':int((~choose_x).sum()),'policy_failures':int(pol.sum())})
   boot_delta=(profile_boot[0][0]+profile_boot[1][0]-profile_boot[0][1]-profile_boot[1][1])/2
   rates={k:v/200000 for k,v in observed.items()}
   summ.append({'bias_ratio':ratio,'calibration_shots':n,'calibration_shots_per_logical_shot':n/100,'policy_ler':rates['policy'],'fixed_x_ler':rates['fixed_x'],'fixed_z_ler':rates['fixed_z'],'oracle_ler':rates['oracle'],'policy_minus_fixed_z':rates['policy']-rates['fixed_z'],'cluster_bootstrap_95_ci':[float(np.quantile(boot_delta,.025)),float(np.quantile(boot_delta,.975))],'relative_reduction_vs_fixed_z':1-rates['policy']/rates['fixed_z'],'policy_confusion_by_profile':conf})
 out={'status':'exploratory_prefix_rescore','sample_streams':'same exact deterministic calibration seeds and logical per-window outcomes as adaptive_basis_end_to_end_results.json; no new random sample stream','nested_budgets_correlated':True,'budgets':[25,100,500],'bootstrap_replicates':5000,'bootstrap_seed':2026111892,'summary':summ,'per_profile':details,'scope':'descriptive calibration-cost frontier; not the primary preregistered endpoint'}
 p=HERE/'adaptive_basis_cost_frontier.json';p.write_text(json.dumps(out,indent=2)+'\n');print(f'Wrote {p}');[print(r) for r in summ]
if __name__=='__main__':main()
