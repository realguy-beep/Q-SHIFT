"""Nonparametric histogram-likelihood CUSUM for detector-only profile changes."""
from __future__ import annotations
import json,math,sys,time,platform,hashlib,resource
from pathlib import Path
import numpy as np
from scipy.stats import beta
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
V1=REPO/'outputs'/'independent_research_v1';sys.path.insert(0,str(V1));sys.path.insert(0,str(REPO/'outputs'/'phase2b_pauli_bias'))
from adaptive_basis_sprt import PROFILES
from adaptive_basis_sprt_common_variance import llr_stream
from adaptive_basis_change_detection import initial_state,run_cusum,run_periodic_lda
from bias_identification import feature_masks,make_features
from basis_alignment_distance7 import build
from noise_model import build_circuit as source_build
CAL_SEEDS=(2026122101,2026122102)
PRE_SEEDS=tuple(range(2026122111,2026122127));MAIN_SEEDS=tuple(range(2026122131,2026122139))
MEAS=(("nominal",.003),("measurement_shift",.006));TRAIN=100_000;EPISODES=100;DWELL=1_000;SEGMENTS=101;HIST_BINS=32;THRESHOLD=float(np.log(200));CAP=300.

def sample_scores(profile,measurement_p,count,seed):
 c=build('z',profile,3,5,bias_ratio=10.,gate_p=.003,measurement_p=measurement_p)
 s=source_build('z',profile,distance=3,rounds=5,bias_ratio=10.,gate_p=.003,measurement_p=measurement_p)
 if str(c)!=str(s):raise RuntimeError('source builder mismatch')
 masks=feature_masks(c,3,5);t=time.perf_counter();d=c.compile_detector_sampler(seed=seed).sample(shots=count);elapsed=time.perf_counter()-t
 model=json.loads((V1/'bias_identification_results.json').read_text())['training'];score=make_features(d,masks)@np.asarray(model['weights'],float)+float(model['intercept'])
 if not np.isfinite(score).all():raise RuntimeError('nonfinite score')
 return score,elapsed

def fit_hist(scores):
 pooled=np.concatenate([scores['x_biased'],scores['z_biased']]);edges=np.unique(np.quantile(pooled,np.linspace(0,1,HIST_BINS+1)))
 if len(edges)<12:raise RuntimeError(f'insufficient unique score bins: {len(edges)-1}')
 # Extend endpoints to cover any held-out score; observations outside fit limits map to edge bins.
 counts={p:np.histogram(scores[p],bins=edges)[0].astype(float)+.5 for p in PROFILES}
 probs={p:counts[p]/counts[p].sum() for p in PROFILES}
 return edges,probs

def hist_llr(scores,edges,probs):
 b=np.clip(np.searchsorted(edges,scores,side='right')-1,0,len(edges)-2)
 return np.log(probs['z_biased'][b])-np.log(probs['x_biased'][b])

def cusum_llr(scores,llr):
 state=initial_state(scores);gz=gx=0.;events=[]
 for i,v in enumerate(llr):
  if i<100:continue
  if state:
   gz=max(0.,gz+float(v))
   if gz>=THRESHOLD:state=False;gz=gx=0.;events.append((i,state))
  else:
   gx=max(0.,gx-float(v))
   if gx>=THRESHOLD:state=True;gz=gx=0.;events.append((i,state))
 return state,events

def methods(scores,edges,probs):
 return {'histogram_cusum':cusum_llr(scores,hist_llr(scores,edges,probs))[1],
         'gaussian_heteroscedastic_cusum':run_cusum(scores,'heteroscedastic')[1],
         'gaussian_common_variance_cusum':run_cusum(scores,'common_variance')[1],
         'periodic_100_shot_lda':run_periodic_lda(scores)[1]}

def stable_eval(stream,profile,edges,probs,episodes):
 truth=profile=='x_biased';rows={k:{'false_switches':0,'initial_errors':0,'switches':0} for k in ('histogram_cusum','gaussian_heteroscedastic_cusum','gaussian_common_variance_cusum','periodic_100_shot_lda')}
 for ep in range(episodes):
  s=stream[ep*DWELL:(ep+1)*DWELL]
  for name,ev in methods(s,edges,probs).items():
   rows[name]['false_switches']+=sum(int(x!=truth) for _,x in ev);rows[name]['switches']+=len(ev);rows[name]['initial_errors']+=int(initial_state(s)!=truth)
 for row in rows.values():row['false_switches_per_100k_shots']=row['false_switches']*100_000/max(1,episodes*(DWELL-100))
 return rows

def alternating_eval(stream,edges,probs):
 truth=[i%2==0 for i in range(SEGMENTS)];events=methods(stream,edges,probs);out={}
 for name,ev in events.items():
  delays=[];missed=0;already=0
  for seg in range(1,SEGMENTS):
   boundary=seg*DWELL;state=initial_state(stream) if not [x for x in ev if x[0]<boundary] else [x for x in ev if x[0]<boundary][-1][1]
   if state==truth[seg]:already+=1;delays.append(0);continue
   nxt=boundary+DWELL;hit=next((x for x in ev if boundary<=x[0]<nxt and x[1]==truth[seg]),None)
   if hit is None:missed+=1
   else:delays.append(hit[0]-boundary+1)
  out[name]={'transition_count':SEGMENTS-1,'detected_or_already_correct':len(delays),'missed_transitions':missed,'already_correct_at_change':already,'median_delay_shots':float(np.median(delays)) if delays else None,'p90_delay_shots':float(np.quantile(delays,.9)) if delays else None,'switch_events':len(ev)}
 return out

def main():
 started=time.perf_counter();pre=[];cursor=0;total=0
 train={}
 for p,seed in zip(PROFILES,CAL_SEEDS,strict=True):
  score,sec=sample_scores(p,.003,TRAIN,seed);train[p]=score;total+=TRAIN;pre.append({'stage':'calibration','profile':p,'seed':seed,'shots':TRAIN,'seconds':sec})
 edges,probs=fit_hist(train)
 pre_ok=True
 # Preflight uses 10 1k stable episodes and a 20k alternating stream per measurement rate.
 for regime,mp in MEAS:
  for p in PROFILES:
   seed=PRE_SEEDS[cursor];cursor+=1;s,sec=sample_scores(p,mp,10*DWELL,seed);total+=len(s)
   mm=stable_eval(s,p,edges,probs,10);pre.append({'stage':'preflight_stable','regime':regime,'profile':p,'seed':seed,'shots':len(s),'seconds':sec,'histogram_false_switches':mm['histogram_cusum']['false_switches']})
  sx,tx=sample_scores('x_biased',mp,10*DWELL,PRE_SEEDS[cursor]);seedx=PRE_SEEDS[cursor];cursor+=1
  sz,tz=sample_scores('z_biased',mp,10*DWELL,PRE_SEEDS[cursor]);seedz=PRE_SEEDS[cursor];cursor+=1;total+=len(sx)+len(sz)
  stream=np.concatenate([(sx if i%2==0 else sz)[(i//2)*DWELL:(i//2+1)*DWELL] for i in range(20)])
  pre.append({'stage':'preflight_alternating','regime':regime,'seeds':[seedx,seedz],'shots':len(stream),'seconds':tx+tz,'histogram_metrics':alternating_eval(stream,edges,probs)['histogram_cusum']})
 projection=(time.perf_counter()-started)*((EPISODES*DWELL*4+SEGMENTS*DWELL*2)/(10*DWELL*4+20*DWELL*2))
 if projection>CAP:raise RuntimeError(f'projected runtime {projection:.1f}s exceeds cap')
 stable=[];alternating=[];cursor=0
 for regime,mp in MEAS:
  for p in PROFILES:
   seed=MAIN_SEEDS[cursor];cursor+=1;s,sec=sample_scores(p,mp,EPISODES*DWELL,seed);total+=len(s)
   stable.append({'regime':regime,'measurement_p':mp,'profile':p,'seed':seed,'shots':len(s),'sampling_seconds':sec,'episodes':EPISODES,'methods':stable_eval(s,p,edges,probs,EPISODES)})
  sx,tx=sample_scores('x_biased',mp,((SEGMENTS+1)//2)*DWELL,MAIN_SEEDS[cursor]);seedx=MAIN_SEEDS[cursor];cursor+=1
  sz,tz=sample_scores('z_biased',mp,(SEGMENTS//2)*DWELL,MAIN_SEEDS[cursor]);seedz=MAIN_SEEDS[cursor];cursor+=1;total+=len(sx)+len(sz)
  parts=[];ix=iz=0
  for seg in range(SEGMENTS):
   if seg%2==0:parts.append(sx[ix:ix+DWELL]);ix+=DWELL
   else:parts.append(sz[iz:iz+DWELL]);iz+=DWELL
  stream=np.concatenate(parts)
  alternating.append({'regime':regime,'measurement_p':mp,'seeds':[seedx,seedz],'shots':len(stream),'sampling_seconds':tx+tz,'dwell_shots':DWELL,'segments':SEGMENTS,'methods':alternating_eval(stream,edges,probs)})
 hist_stable=[x['methods']['histogram_cusum']['false_switches_per_100k_shots'] for x in stable]
 hist_detect=[x['methods']['histogram_cusum']['detected_or_already_correct']/(SEGMENTS-1) for x in alternating]
 hist_delay=[x['methods']['histogram_cusum']['median_delay_shots'] for x in alternating]
 passed=bool(max(hist_stable[:2])<=5 and max(hist_stable[2:])<=25 and min(hist_detect)>=.95 and all(x is not None and x<=100 for x in hist_delay))
 result={'status':'completed','histogram_model':{'bins_requested':HIST_BINS,'effective_bins':len(edges)-1,'pseudocount':.5,'edges':edges.tolist(),'profile_bin_probabilities':{p:probs[p].tolist() for p in PROFILES},'training_shots_per_profile':TRAIN,'training_measurement_p':.003},'preflight':pre,'stable':stable,'alternating':alternating,'advancement_gate_passed':passed,'unique_samples':total,'projected_runtime_seconds':projection,'elapsed_seconds':time.perf_counter()-started,'peak_rss_kib':int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),'software_versions':{'python':platform.python_version(),'numpy':np.__version__},'scope':'detector-only change detection for two Pauli profiles, fixed 1k dwell, nominal and doubled measurement noise'}
 (HERE/'adaptive_histogram_cusum_results.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'hist_stable_false_per_100k':hist_stable,'hist_detect':hist_detect,'hist_delay':hist_delay,'gate':passed,'samples':total,'elapsed':result['elapsed_seconds']},indent=2))
if __name__=='__main__':main()
