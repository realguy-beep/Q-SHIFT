import json
from pathlib import Path
import numpy as np,stim
from decoder_bank import build_bank
from evaluation import evaluate_blocks
from schedules import schedule,REGIMES
P=Path(__file__).resolve().parent;profiles=np.array(json.loads((P/'profiles.json').read_text()));models=build_bank();utility_reps=[]
for rep in range(3):
 tab=np.zeros((3,9))
 for ri,(name,(g,m)) in enumerate(REGIMES.items()):
  c=stim.Circuit.generated('surface_code:rotated_memory_z',distance=3,rounds=5,after_clifford_depolarization=g,before_measure_flip_probability=m);d,y=c.compile_detector_sampler(seed=96000001+rep*100+ri).sample(shots=20000,separate_observables=True);y=y[:,0]
  for j,model in enumerate(models):tab[ri,j]=np.mean(model.decode_batch(d)[:,0]^y)
 utility_reps.append(tab)
util=np.mean(utility_reps,axis=0);unc=np.std(utility_reps,axis=0,ddof=1).tolist();spec=['stationary','data_to_measurement','measurement_to_data','nominal_measurement_nominal','slow','rapid','random'];out={'utility_shots':180000,'utility_mean_shape':list(util.shape),'utility_mean':util.tolist(),'utility_between_rep_sd':unc,'schedules':{},'seeds':'utility 96000001+; schedule 97000001+; shot streams 98000001+; development only'}
for si,s in enumerate(spec):
 seq=schedule(s,97000001+si,blocks=24,dwell=512);blocks=[]
 for bi,state in enumerate(seq):
  g,m=REGIMES[state];c=stim.Circuit.generated('surface_code:rotated_memory_z',distance=3,rounds=5,after_clifford_depolarization=g,before_measure_flip_probability=m);d,y=c.compile_detector_sampler(seed=98000001+si*100+bi).sample(shots=512,separate_observables=True);blocks.append({'state':state,'detectors':d,'observables':y[:,0].astype(bool)})
 out['schedules'][s]={'sequence':seq,'utility':evaluate_blocks(blocks,profiles,models,util,policy='utility'),'ml':evaluate_blocks(blocks,profiles,models,util,policy='ml')}
(P/'DEVELOPMENT_RESULTS_v3.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:{p:v[p]['rates'] for p in ['ml','utility']} for k,v in out['schedules'].items()},indent=2))
