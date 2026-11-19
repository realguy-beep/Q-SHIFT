"""Calibrate one false-alarm boundary for the frozen histogram CUSUM."""
from __future__ import annotations
import json,math,time,platform,resource,hashlib
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
from adaptive_histogram_cusum import sample_scores,hist_llr
from adaptive_basis_change_detection import initial_state,run_cusum,run_periodic_lda
MODEL=json.loads((HERE/'adaptive_histogram_cusum_results.json').read_text())['histogram_model']
EDGES=np.asarray(MODEL['edges'],float);PROBS={k:np.asarray(v,float) for k,v in MODEL['profile_bin_probabilities'].items()}
CAL_SEEDS=(2026122201,2026122202,2026122203,2026122204)
VAL_SEEDS=tuple(range(2026122211,2026122219))
MEAS=(('nominal',.003),('measurement_shift',.006));EPISODES=500;DWELL=1000;SEGMENTS=101;LOW=float(np.log(200));HIGH=100.;CAP=300.
def events(scores,h):
 state=initial_state(scores);gz=gx=0.;out=[];llr=hist_llr(scores,EDGES,PROBS)
 for i,v in enumerate(llr):
  if i<100:continue
  if state:
   gz=max(0.,gz+float(v))
   if gz>=h:state=False;gz=gx=0.;out.append((i,state))
  else:
   gx=max(0.,gx-float(v))
   if gx>=h:state=True;gz=gx=0.;out.append((i,state))
 return out
def stable_metrics(stream,profile,episodes,h):
 truth=profile=='x_biased';false=0;switches=0;initial=0
 for k in range(episodes):
  s=stream[k*DWELL:(k+1)*DWELL];ev=events(s,h);false+=sum(int(x!=truth) for _,x in ev);switches+=len(ev);initial+=int(initial_state(s)!=truth)
 return {'false_switches':false,'switches':switches,'initial_errors':initial,'false_switches_per_100k_shots':false*100000/max(1,episodes*(DWELL-100))}
def calibration_pass(cal,h):
 for regime,profile_data in cal.items():
  limit=5 if regime=='nominal' else 25
  for profile,scores in profile_data.items():
   if stable_metrics(scores,profile,EPISODES,h)['false_switches_per_100k_shots']>limit:return False
 return True
def alternating_metrics(stream,h):
 truth=[i%2==0 for i in range(SEGMENTS)];ev=events(stream,h);delays=[];miss=0;already=0
 for seg in range(1,SEGMENTS):
  b=seg*DWELL;prior=[x for x in ev if x[0]<b];state=initial_state(stream) if not prior else prior[-1][1]
  if state==truth[seg]:already+=1;delays.append(0);continue
  hit=next((x for x in ev if b<=x[0]<(b+DWELL) and x[1]==truth[seg]),None)
  if hit is None:miss+=1
  else:delays.append(hit[0]-b+1)
 return {'transition_count':SEGMENTS-1,'detected_or_already_correct':len(delays),'missed_transitions':miss,'already_correct_at_change':already,'median_delay_shots':float(np.median(delays)) if delays else None,'p90_delay_shots':float(np.quantile(delays,.9)) if delays else None,'switch_events':len(ev)}
def main():
 start=time.perf_counter();cal={};cal_rows=[];idx=0;total=0
 for regime,p in MEAS:
  cal[regime]={}
  for profile in ('x_biased','z_biased'):
   seed=CAL_SEEDS[idx];idx+=1;s,sec=sample_scores(profile,p,EPISODES*DWELL,seed);cal[regime][profile]=s;total+=len(s)
   cal_rows.append({'regime':regime,'profile':profile,'seed':seed,'shots':len(s),'sampling_seconds':sec})
 if not calibration_pass(cal,HIGH):
  out={'status':'calibration_threshold_stop','calibration':cal_rows,'upper_threshold':HIGH,'unique_calibration_samples':total,'elapsed_seconds':time.perf_counter()-start,'reason':'no threshold <=100 met every calibration false-switch limit'}
  (HERE/'adaptive_histogram_cusum_calibrated_results.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));return
 if calibration_pass(cal,LOW):
  chosen=LOW
 else:
  lo,hi=LOW,HIGH
  for _ in range(24):
   mid=(lo+hi)/2
   if calibration_pass(cal,mid):hi=mid
   else:lo=mid
  chosen=hi
 # release calibration arrays before fresh validation sampling
 del cal
 val_stable=[];val_alt=[];cursor=0
 for regime,p in MEAS:
  for profile in ('x_biased','z_biased'):
   seed=VAL_SEEDS[cursor];cursor+=1;s,sec=sample_scores(profile,p,EPISODES*DWELL,seed);total+=len(s)
   hist=stable_metrics(s,profile,EPISODES,chosen);fixed=stable_metrics(s,profile,EPISODES,LOW)
   gauss={n:{'false_switches':sum(sum(int(x!=(profile=='x_biased')) for _,x in ev) for ev in [run_cusum(s[k*DWELL:(k+1)*DWELL],m)[1] for k in range(EPISODES)]),'switches':sum(len(run_cusum(s[k*DWELL:(k+1)*DWELL],m)[1]) for k in range(EPISODES))} for n,m in [('gaussian_heteroscedastic','heteroscedastic'),('gaussian_common_variance','common_variance')]}
   periodic=sum(sum(int(x!=(profile=='x_biased')) for _,x in run_periodic_lda(s[k*DWELL:(k+1)*DWELL])[1]) for k in range(EPISODES))
   hist.update({'method':'calibrated_histogram','initialization_errors':hist['initial_errors']});fixed['method']='fixed_log200_histogram'
   val_stable.append({'regime':regime,'measurement_p':p,'profile':profile,'seed':seed,'shots':len(s),'sampling_seconds':sec,'calibrated':hist,'fixed_histogram':fixed,'gaussian_false_switches':gauss,'periodic_100_lda_false_switches':periodic})
  sx,tx=sample_scores('x_biased',p,((SEGMENTS+1)//2)*DWELL,VAL_SEEDS[cursor]);seedx=VAL_SEEDS[cursor];cursor+=1
  sz,tz=sample_scores('z_biased',p,(SEGMENTS//2)*DWELL,VAL_SEEDS[cursor]);seedz=VAL_SEEDS[cursor];cursor+=1;total+=len(sx)+len(sz)
  parts=[];ix=iz=0
  for seg in range(SEGMENTS):
   if seg%2==0:parts.append(sx[ix:ix+DWELL]);ix+=DWELL
   else:parts.append(sz[iz:iz+DWELL]);iz+=DWELL
  stream=np.concatenate(parts);val_alt.append({'regime':regime,'measurement_p':p,'seeds':[seedx,seedz],'shots':len(stream),'calibrated_histogram':alternating_metrics(stream,chosen),'fixed_histogram':alternating_metrics(stream,LOW)})
 rates=[r['calibrated']['false_switches_per_100k_shots'] for r in val_stable];detect=[r['calibrated_histogram']['detected_or_already_correct']/100 for r in val_alt];delays=[r['calibrated_histogram']['median_delay_shots'] for r in val_alt]
 passed=bool(max(rates[:2])<=5 and max(rates[2:])<=25 and min(detect)>=.95 and all(x is not None and x<=100 for x in delays))
 out={'status':'completed','threshold_calibration':{'method':'smallest threshold >=log(200) meeting each stable calibration false-switch limit','threshold':chosen,'baseline_log200':LOW,'calibration':cal_rows,'calibration_passed':True},'validation_stable':val_stable,'validation_alternating':val_alt,'advancement_gate_passed':passed,'unique_samples':total,'elapsed_seconds':time.perf_counter()-start,'peak_rss_kib':int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),'software_versions':{'python':platform.python_version(),'numpy':np.__version__},'scope':'single empirically calibrated histogram CUSUM boundary; detector-only development study'}
 (HERE/'adaptive_histogram_cusum_calibrated_results.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'threshold':chosen,'false_rates':rates,'transition_detection':detect,'median_delays':delays,'gate':passed,'samples':total,'elapsed':out['elapsed_seconds']},indent=2))
if __name__=='__main__':main()
