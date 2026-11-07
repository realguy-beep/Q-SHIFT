import time,hashlib,numpy as np
from core import NoiseEstimator,Controller
from decoder_bank import GRID
REGIME_ID={'data_heavy':0,'nominal':1,'measurement_heavy':2}
REGIME_DECODER={'data_heavy':6,'nominal':4,'measurement_heavy':2}
GRID_TO_REGIME=np.array([0,1,2,0,1,2,0,1,2])
def evaluate_blocks(blocks,profiles,models,utility,window=128,policy='utility',confidence=.65,static_prefix_blocks=1):
 est=NoiseEstimator(profiles,window);ctl=Controller(fallback=1,confidence=confidence,hysteresis=2,dwell=2,switch_penalty=.00005)
 names=('pooled_fixed','nominal_fixed','static_calibrated','adaptive','oracle');errors={k:0 for k in names};n=0;previous=None;static_idx=1;selected=[];estimates=[];switches=[];switches_false=0;decsec=0.;rows=[];delay_events=[]
 for t,b in enumerate(blocks):
  d,y,state=b['detectors'],b['observables'],b['state']; estimate=None;conf=0.;gp=None;rp=None
  if previous is not None:
   obs=est.observe(previous)
   if len(obs)==3:
    gi,conf,gp=obs;rp=np.array([gp[GRID_TO_REGIME==r].sum() for r in range(3)]);estimate=int(rp.argmax())
   if t==static_prefix_blocks and gp is not None:static_idx=int(gp.argmax())
   before=ctl.current
   if policy=='ml': chosen=ctl.choose(gi if gp is not None else None,conf)
   elif policy=='utility': chosen=ctl.choose(estimate,conf,utility_scores=rp@utility if rp is not None else None)
   else:raise ValueError(policy)
   if chosen!=before:
    switches.append(t);switches_false+=int(estimate is None or estimate!=REGIME_ID[state])
  else:chosen=ctl.current
  predictions={};st=time.perf_counter()
  idxs={'pooled_fixed':1,'nominal_fixed':4,'static_calibrated':static_idx,'adaptive':chosen,'oracle':REGIME_DECODER[state]}
  for k,idx in idxs.items():predictions[k]=models[idx].decode_batch(d)[:,0].astype(bool)
  decsec+=time.perf_counter()-st
  errs={k:int(np.count_nonzero(predictions[k]^y)) for k in names}
  for k in names:errors[k]+=errs[k]
  paired={k:{'candidate_only':int(np.count_nonzero((predictions[k]^y)&~(predictions['pooled_fixed']^y))),'pooled_only':int(np.count_nonzero(~(predictions[k]^y)&(predictions['pooled_fixed']^y)))} for k in names}
  rows.append({'block':t,'state':state,'estimate_regime':estimate,'chosen_decoder':chosen,'static_decoder':static_idx,'errors':errs,'paired_shot_discordance':paired,'samples_hash':hashlib.sha256(d.tobytes()+y.tobytes()).hexdigest()})
  estimates.append(estimate);selected.append(chosen);previous=d;n+=len(y)
 transitions=[i for i in range(1,len(blocks)) if blocks[i]['state']!=blocks[i-1]['state']];delays=[]
 for tr in transitions:
  tgt=REGIME_ID[blocks[tr]['state']];hit=next((i-tr for i in range(tr+1,len(blocks)) if estimates[i]==tgt),None);delays.append(hit)
 return {'shots':n,'errors':errors,'rates':{k:v/n for k,v in errors.items()},'paired_vs_pooled':{k:{'candidate_only':sum(r['paired_shot_discordance'][k]['candidate_only'] for r in rows),'pooled_only':sum(r['paired_shot_discordance'][k]['pooled_only'] for r in rows)} for k in names},'switch_blocks':switches,'switch_count':len(switches),'false_switches':switches_false,'transition_delays_blocks':delays,'censored_transitions':sum(x is None for x in delays),'mean_detected_delay':float(np.mean([x for x in delays if x is not None])) if any(x is not None for x in delays) else None,'decoder_sequence':selected,'decode_seconds':decsec,'blocks':rows,'causal_previous_block_only':True,'static_prefix_blocks':static_prefix_blocks}
