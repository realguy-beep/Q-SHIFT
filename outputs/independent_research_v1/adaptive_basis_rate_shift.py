"""Frozen detector-only basis policy under total-rate drift after calibration."""
from __future__ import annotations
import json,sys,time
from pathlib import Path
import numpy as np
import pymatching
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from bias_identification import feature_masks,make_features,FEATURES
from basis_alignment_distance7 import build
from noise_model import DEFAULT_GATE_P,DEFAULT_MEAS_P,build_circuit as source_build
MODEL=json.loads((HERE/'bias_identification_results.json').read_text())['training'];W=np.asarray(MODEL['weights']);B=float(MODEL['intercept'])
PROFILES=('x_biased','z_biased');RATIOS=(2.,5.,10.);CONDS=[(r,p) for r in RATIOS for p in PROFILES]
PRE=tuple(range(2026111901,2026111919));MAIN=tuple(range(2026111921,2026111939));CAL_P=.003;TEST_P=.006;WINDOWS=1000

def sampler(basis,profile,ratio,p,n,seed):
 c=build(basis,profile,3,5,bias_ratio=ratio,gate_p=p,measurement_p=p);dem=c.detector_error_model(decompose_errors=True,approximate_disjoint_errors=.004);m=pymatching.Matching.from_detector_error_model(dem,enable_correlations=True)
 t=time.perf_counter();det,obs=c.compile_detector_sampler(seed=seed).sample(shots=n,separate_observables=True);ss=time.perf_counter()-t
 t=time.perf_counter();pred=np.asarray(m.decode_batch(det),dtype=np.bool_).reshape(n,-1);ds=time.perf_counter()-t
 check=min(100,n);scalar=np.asarray([m.decode(det[i]) for i in range(check)],dtype=np.bool_).reshape(check,-1)
 if not np.array_equal(pred[:check],scalar):raise RuntimeError('batch/scalar mismatch')
 if pred.shape!=obs.shape:raise RuntimeError('observable shape mismatch')
 return np.any(pred!=obs,axis=1),ss,ds,c.num_detectors

def main():
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');a=ap.parse_args();start=time.perf_counter()
 copies={f'{r}_{p}_{b}':str(build(b,p,3,5,bias_ratio=r,gate_p=CAL_P,measurement_p=CAL_P))==str(source_build(b,p,distance=3,rounds=5,bias_ratio=r,gate_p=CAL_P,measurement_p=CAL_P)) for r in RATIOS for p in PROFILES for b in ('x','z')}
 if not all(copies.values()):raise RuntimeError('nominal calibration circuit differs from source')
 training_means=np.asarray(MODEL['means']);scores=training_means@W+B
 if not(scores[0]<0<scores[1]):raise RuntimeError(f'classifier sign check failed: {scores}')
 pre=a.preflight;seeds=PRE if pre else MAIN;si=0;rows=[];ncal=1000 if pre else 500000;nmem=1000 if pre else 100000
 for ratio,profile in CONDS:
  sc=seeds[si];si+=1;cc=build('z',profile,3,5,bias_ratio=ratio,gate_p=CAL_P,measurement_p=CAL_P);mask=feature_masks(cc,3,5)
  t=time.perf_counter();det=cc.compile_detector_sampler(seed=sc).sample(shots=ncal);cals=time.perf_counter()-t;feat=make_features(det,mask)
  if not np.isfinite(feat).all():raise RuntimeError('nonfinite calibration feature')
  if pre:rows.append({'kind':'calibration','ratio':ratio,'profile':profile,'shots':ncal,'seed':sc,'sampling_seconds':cals})
  else:
   win=feat.reshape(WINDOWS,500,len(FEATURES)).mean(axis=1);choose_x=win@W+B<0;arm={}
  for basis in ('x','z'):
   sm=seeds[si];si+=1;fails,ss,ds,nd=sampler(basis,profile,ratio,TEST_P,nmem,sm)
   if pre:rows.append({'kind':'logical','ratio':ratio,'profile':profile,'basis':basis,'shots':nmem,'seed':sm,'sampling_seconds':ss,'decode_seconds':ds,'detectors':nd})
   else:arm[basis]=fails.reshape(WINDOWS,100).sum(axis=1).astype(int);rows.append({'kind':'logical','ratio':ratio,'profile':profile,'basis':basis,'shots':nmem,'seed':sm,'sampling_seconds':ss,'decode_seconds':ds,'detectors':nd})
  if not pre:
   sel=np.where(choose_x,arm['x'],arm['z']);oracle=arm['x'] if profile=='x_biased' else arm['z']
   rows.append({'kind':'policy','ratio':ratio,'profile':profile,'calibration_seed':sc,'x_selected':int(choose_x.sum()),'z_selected':int((~choose_x).sum()),'policy_failures_by_window':sel.tolist(),'fixed_x_failures_by_window':arm['x'].tolist(),'fixed_z_failures_by_window':arm['z'].tolist(),'oracle_failures_by_window':oracle.tolist(),'policy_failures':int(sel.sum()),'fixed_x_failures':int(arm['x'].sum()),'fixed_z_failures':int(arm['z'].sum()),'oracle_failures':int(oracle.sum())})
 elapsed=time.perf_counter()-start
 if pre:
  projected=sum(r['sampling_seconds']*(500 if r['kind']=='calibration' else 100)+r.get('decode_seconds',0)*(100 if r['kind']=='logical' else 0) for r in rows)
  out={'status':'preflight','nominal_builder_matches_source':copies,'classifier_training_score_check':scores.tolist(),'rows':rows,'projected_main_seconds':projected,'elapsed_seconds':elapsed,'stochastic_circuit_shots':sum(r['shots'] for r in rows)}
  path=HERE/'adaptive_basis_rate_shift_preflight.json';path.write_text(json.dumps(out,indent=2)+'\n');print(f'Wrote {path}; projected {projected:.1f}s');return int(projected>300)
 rng=np.random.default_rng(2026111991);pol=[r for r in rows if r['kind']=='policy'];summ=[];boot=5000
 for ratio in RATIOS:
  group=[r for r in pol if r['ratio']==ratio];prof={r['profile']:r for r in group};obs={k:sum(r[f'{k}_failures'] for r in group)/200000 for k in ('policy','fixed_x','fixed_z','oracle')};bpol=[];bfz=[]
  for name,r in prof.items():
   p=np.asarray(r['policy_failures_by_window']);z=np.asarray(r['fixed_z_failures_by_window']);idx=rng.integers(0,WINDOWS,size=(boot,WINDOWS));bpol.append(p[idx].sum(axis=1)/100000);bfz.append(z[idx].sum(axis=1)/100000)
  delta=(bpol[0]+bpol[1]-bfz[0]-bfz[1])/2
  summ.append({'bias_ratio':ratio,'calibration_gate_meas_p':CAL_P,'logical_gate_meas_p':TEST_P,'policy_ler':obs['policy'],'fixed_x_ler':obs['fixed_x'],'fixed_z_ler':obs['fixed_z'],'oracle_ler':obs['oracle'],'policy_minus_fixed_z':obs['policy']-obs['fixed_z'],'cluster_bootstrap_95_ci':[float(np.quantile(delta,.025)),float(np.quantile(delta,.975))],'relative_reduction_vs_fixed_z':1-obs['policy']/obs['fixed_z'],'policy_confusion_by_profile':{r['profile']:{'x_selected':r['x_selected'],'z_selected':r['z_selected']} for r in group}})
 out={'status':'development_rate_shift_validation','distance':3,'rounds':5,'calibration_profile_gate_meas_p':CAL_P,'logical_run_gate_meas_p':TEST_P,'dem_approximate_disjoint_errors_threshold':.004,'bias_ratios':RATIOS,'classifier':'frozen d3 ratio10 binary LDA; detector-only calibration at p=.003, no retraining','decoder':'per-test-circuit correlation-enabled PyMatching from approximate DEM threshold .004','nominal_builder_matches_source':copies,'classifier_training_score_check':scores.tolist(),'summary':summ,'conditions':rows,'bootstrap_replicates':boot,'bootstrap_seed':2026111991,'elapsed_seconds':elapsed,'stochastic_circuit_shots':len(RATIOS)*(2*500000+2*2*100000),'scope':'synthetic total-rate drift with X/Z direction preserved; not X/Z change-point or hardware validation'}
 path=HERE/'adaptive_basis_rate_shift_results.json';path.write_text(json.dumps(out,indent=2)+'\n');print(f'Wrote {path}; elapsed={elapsed:.1f}s');[print(r) for r in summ]
if __name__=='__main__':raise SystemExit(main())
