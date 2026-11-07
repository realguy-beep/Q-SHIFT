"""Development-only specialization audit and paired dynamic feasibility study."""
import json,hashlib,csv,time
from pathlib import Path
import numpy as np,stim
from decoder_bank import build_bank,GRID
from schedules import REGIMES,schedule
from core import NoiseEstimator,Controller
P=Path(__file__).resolve().parent;bank=build_bank();names=list(REGIMES);pairs=list(GRID);profiles=np.array(json.loads((P/'profiles.json').read_text()))
reg_to_dec={'data_heavy':6,'nominal':4,'measurement_heavy':2};roots=[101000001,101100001,101200001]
assert len(set(roots))==3 and all(r>100000000 for r in roots)
def circ(name):
 g,m=REGIMES[name];return stim.Circuit.generated('surface_code:rotated_memory_z',distance=3,rounds=5,after_clifford_depolarization=g,before_measure_flip_probability=m)
def sample(name,seed,n):return circ(name).compile_detector_sampler(seed=seed).sample(shots=n,separate_observables=True)
def batchpred(d):return np.array([m.decode_batch(d)[:,0].astype(bool) for m in bank])
# Three independent calibration replicates; labels select regime-best only here.
cal=[]
for rep,root in enumerate(roots):
 by={}
 for ri,name in enumerate(names):
  d,y=sample(name,root+ri,5000);pred=batchpred(d);by[name]=[(pred[i]^y[:,0]).mean() for i in range(9)]
 cal.append(by)
calmean={n:np.mean([x[n] for x in cal],axis=0).tolist() for n in names}; best={n:int(np.argmin(calmean[n])) for n in names}
# Independent paired stationary eval, agreement matrix and paired error comparisons.
dis=np.zeros((9,9),dtype=np.int64);evals={};seed_results=[]
for ri,name in enumerate(names):
 err=np.zeros(9,dtype=int);shots=0
 for rep in range(3):
  d,y=sample(name,102000001+rep*100+ri,10000);pred=batchpred(d);shots+=len(y)
  for i in range(9):
   err[i]+=np.count_nonzero(pred[i]^y[:,0])
   for j in range(9):dis[i,j]+=np.count_nonzero(pred[i]!=pred[j])
  seed_results.append({'regime':name,'replicate':rep,'errors':[(pred[i]^y[:,0]).sum().item() for i in range(9)]})
 evals[name]={'shots':shots,'errors':err.tolist(),'rates':(err/shots).tolist(),'best_calibrated_decoder':best[name]}
# Paired dynamic schedules; one generated sample set shared by all policies.
dyn={}; schedule_kinds=['stationary','data_to_measurement','measurement_to_data','nominal_measurement_nominal','slow','rapid','random']
for si,kind in enumerate(schedule_kinds):
 reps=[]
 for rep in range(4):
  seq=schedule(kind,103000001+si*10+rep,blocks=24,dwell=512);blocks=[]
  for bi,state in enumerate(seq):
   d,y=sample(state,104000001+si*1000+rep*100+bi,512);blocks.append((state,d,y[:,0]))
  outputs={k:{'errors':0,'switches':0,'false_switches':0,'chosen':[],'estimate':[],'delays':[]} for k in ['ml','utility','regime_matched']}
  # development utility matrix from calibration error rates
  U=np.array([calmean[n] for n in names]);
  for policy in outputs:
   est=NoiseEstimator(profiles,window=128);ctl=Controller(fallback=1,confidence=.55,hysteresis=2,dwell=2,switch_penalty=.00002);prev=None;est_hist=[];chosen_hist=[];switches=[];false=0;errs=0
   for bi,(state,d,y) in enumerate(blocks):
    if prev is None: chosen=1;estimate=None
    else:
     obs=est.observe(prev)
     if len(obs)==3:
      gi,conf,gp=obs; rp=np.array([gp[[0,3,6]].sum(),gp[[1,4,7]].sum(),gp[[2,5,8]].sum()]);estimate=int(rp.argmax())
      if policy=='ml':target=gi;ch=ctl.choose(target,conf)
      elif policy=='utility': ch=ctl.choose(estimate,conf,utility_scores=rp@U)
      else: ch=reg_to_dec[state]
     else: estimate=None; ch=ctl.current if policy!='regime_matched' else reg_to_dec[state]
     chosen=ch
     if chosen!=chosen_hist[-1]:switches.append(bi);false+=int(estimate is None or estimate!=names.index(state))
    pred=bank[chosen].decode_batch(d)[:,0].astype(bool);errs+=int(np.count_nonzero(pred^y));prev=d;est_hist.append(estimate);chosen_hist.append(chosen)
   trans=[i for i in range(1,len(seq)) if seq[i]!=seq[i-1]];delays=[]
   for tr in trans:
    target=names.index(seq[tr]);hit=next((i-tr for i in range(tr+1,len(seq)) if est_hist[i]==target),None);delays.append(hit)
   outputs[policy].update({'errors':errs,'shots':len(seq)*512,'switches':len(switches),'false_switches':false,'chosen':chosen_hist,'estimator_delay_blocks':delays,'censored':sum(x is None for x in delays)})
  reps.append({'sequence':seq,'policies':outputs})
 dyn[kind]=reps
out={'calibration_roots':roots,'evaluation_seed_start':102000001,'dynamic_seed_start':103000001,'block_seed_start':104000001,'grid':pairs,'regime_decoder_mapping':reg_to_dec,'calibration_rate_matrix':calmean,'selected_best_decoders':best,'stationary_evaluation':evals,'pairwise_disagreements':dis.tolist(),'dynamic':dyn,'seed_level_stationary':seed_results,'confirmatory_test_run':False}
(P/'PHASE5D_RESULTS.json').write_text(json.dumps(out,indent=2)+'\n');print('stationary',json.dumps(evals));print('best',best)
