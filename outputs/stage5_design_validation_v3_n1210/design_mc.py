"""Frozen synthetic operating-characteristic simulation; never imports Stim."""
from __future__ import annotations
import argparse, hashlib, json, math, os, time
from pathlib import Path
import numpy as np
from scipy.stats import t as student_t

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CFG=json.loads((HERE/'DESIGN_CONFIG.json').read_text(encoding='utf-8'))
INV=json.loads((HERE/'DESIGN_SEED_INVENTORY.json').read_text(encoding='utf-8'))
FREEZE=HERE/'DESIGN_VALIDATION_FREEZE.json'
SEEDS={(x['stream'],x['cell']):int(x['seed']) for x in INV['rng_streams']}
N=int(CFG['allocation_roots_per_stratum'])
REPS=int(CFG['monte_carlo']['calibration_replicates_per_scenario'])
BATCH=int(CFG['monte_carlo']['batch_size'])

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

def verify_freeze():
 f=json.loads(FREEZE.read_text(encoding='utf-8'))
 for rel,expected in f['design_input_sha256'].items():
  if sha(ROOT/rel)!=expected: raise RuntimeError(f'Frozen design input hash mismatch: {rel}')
 for rel,expected in f['historical_evidence_sha256'].items():
  if sha(ROOT/rel)!=expected: raise RuntimeError(f'Historical evidence changed: {rel}')
 if f['stage5_evaluation_shots_generated']!=0 or f['sealed_historical_test_accessed'] is not False:
  raise RuntimeError('Invalid no-sampling freeze')
 return sha(FREEZE)

def wilson(k,n):
 z=1.959963984540054; p=k/n; den=1+z*z/n
 center=(p+z*z/(2*n))/den
 half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
 return [max(0.,center-half),min(1.,center+half)]

def draw(rng,batch,n,means,sds,family):
 means=np.asarray(means,dtype=np.float64); sds=np.asarray(sds,dtype=np.float64)
 shape=(batch,len(means),n); loc=means[None,:,None]; scale=sds[None,:,None]
 if family=='normal': return rng.normal(loc=loc,scale=scale,size=shape)
 if family.startswith('student_t'):
  df=int(family.removeprefix('student_t'))
  return loc+scale*rng.standard_t(df,size=shape)/math.sqrt(df/(df-2))
 if family=='lognormal_sigma1':
  raw=rng.lognormal(0.,1.,size=shape)
  return loc+scale*((raw-math.exp(.5))/math.sqrt((math.e-1)*math.e))
 if family=='zero_inflated65_normal':
  q=.35; cm=means/q; cv=(sds*sds+means*means)/q-cm*cm
  if np.any(cv<=0): raise ValueError('infeasible zero-inflated moments')
  y=rng.normal(cm[None,:,None],np.sqrt(cv)[None,:,None],size=shape)
  return np.where(rng.random(size=shape)<.65,0.,y)
 if family=='tied_asymmetric65':
  p0,pl,ph=.65,.28,.07; q=pl+ph; plo,phi=pl/q,ph/q
  cm=means/q; cv=(sds*sds+means*means)/q-cm*cm
  if np.any(cv<=0): raise ValueError('infeasible tied moments')
  low=cm-np.sqrt(cv*phi/plo); high=cm+np.sqrt(cv*plo/phi)
  u=rng.random(size=shape)
  return np.where(u<p0,0.,np.where(u<p0+pl,low[None,:,None],high[None,:,None]))
 raise ValueError(f'unknown family {family}')

def stat(x,null):
 # x = replicate x independent condition strata x root; preserves per-root pairing.
 means=x.mean(axis=2); var=x.var(axis=2,ddof=1); k=x.shape[1]; n=x.shape[2]
 parts=var/(k*k*n); v=parts.sum(axis=1); est=means.mean(axis=1); se=np.sqrt(v)
 t=np.divide(est-null,se,out=np.zeros_like(est),where=se>0)
 t=np.where((se==0)&(est<null),-np.inf,t); t=np.where((se==0)&(est>null),np.inf,t)
 den=(parts*parts/(n-1)).sum(axis=1)
 df=np.divide(v*v,den,out=np.full_like(v,np.inf),where=den>0)
 return est,se,t,df

def p0stat(x,null):
 mean=x.mean(axis=1); var=x.var(axis=1,ddof=1); se=np.sqrt(var/x.shape[1])
 t=np.divide(mean-null,se,out=np.zeros_like(mean),where=se>0)
 t=np.where((se==0)&(mean<null),-np.inf,t); t=np.where((se==0)&(mean>null),np.inf,t)
 return mean,se,t

def atomic(path,obj):
 path=Path(path); temp=path.with_suffix(path.suffix+'.tmp')
 temp.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf-8'); os.replace(temp,path)

def cell_path(phase,key): return HERE/'cells'/f'{phase}__{hashlib.sha256(key.encode()).hexdigest()[:16]}.json'
def get_cell(phase,key,freeze_hash):
 p=cell_path(phase,key)
 if not p.exists(): return None
 d=json.loads(p.read_text(encoding='utf-8'))
 if d.get('freeze_sha256')!=freeze_hash or d.get('cell_key')!=key or d.get('phase')!=phase:
  raise RuntimeError(f'Checkpoint identity mismatch: {p.name}')
 return d
def save_cell(phase,key,freeze_hash,obj):
 d={'phase':phase,'cell_key':key,'freeze_sha256':freeze_hash,**obj}; atomic(cell_path(phase,key),d); return d

def seed(stream,key):
 try: return SEEDS[(stream,key)]
 except KeyError: raise RuntimeError(f'Missing frozen RNG seed {stream}/{key}')

def batches(seed_value,means,sds,family):
 rng=np.random.Generator(np.random.PCG64(seed_value)); done=0
 while done<REPS:
  b=min(BATCH,REPS-done); yield draw(rng,b,N,means,sds,family); done+=b

def do_primary(freeze_hash,progress):
 sd0=np.asarray(CFG['condition_sd'],dtype=float); null=float(CFG['null_boundary']); offsets0=np.zeros(4)
 cal=[]
 # Calibration critical values use independent streams and the exact prospectively frozen envelope.
 for s in CFG['null_scenarios']:
  key=f'n{N}/{s["name"]}'; saved=get_cell('primary_calibration',key,freeze_hash)
  if saved: row=saved['row']
  else:
   off=np.asarray(s.get('offsets',offsets0),dtype=float); means=null+off; sds=sd0*float(s['sd_multiplier']); all_neg=[]; all_pos=[]
   for x in batches(seed('primary_null_calibration',key),means,sds,s['distribution']):
    _,_,ts,_=stat(x,null); all_neg.append(-ts); all_pos.append(ts)
   tn=np.concatenate(all_neg); tp=np.concatenate(all_pos)
   q=CFG['monte_carlo']['critical_quantiles']; row={'scenario':s['name'],'distribution':s['distribution'],'sd_multiplier':s['sd_multiplier'],
     'offsets':s.get('offsets',[0,0,0,0]),'seed':seed('primary_null_calibration',key),'replicates':REPS,
     'q_one_sided':float(np.quantile(tn,q['one_sided_calibration'],method='higher')),
     'q_central_lower':float(np.quantile(tn,q['central_tail'],method='higher')),
     'q_central_upper':float(np.quantile(tp,q['central_tail'],method='higher')),
     'mean_t':float(tp.mean()),'sd_t':float(tp.std(ddof=1))}
   save_cell('primary_calibration',key,freeze_hash,{'row':row})
  cal.append(row); progress({'phase':'primary_calibration','cell':s['name'],'done':len(cal),'total':len(CFG['null_scenarios'])})
 critical={'n':N,'one_sided_critical':max(r['q_one_sided'] for r in cal),
  'central_lower_critical':max(r['q_central_lower'] for r in cal),
  'central_upper_critical':max(r['q_central_upper'] for r in cal),'calibration_cells':cal}
 validations=[]
 for s in CFG['null_scenarios']:
  key=f'n{N}/{s["name"]}'; saved=get_cell('primary_validation',key,freeze_hash)
  if saved: row=saved['row']
  else:
   offsets=np.asarray(s.get('offsets',offsets0),dtype=float); means=null+offsets; sds=sd0*float(s['sd_multiplier'])
   rejects=central=welch=0; done=0; rng=np.random.Generator(np.random.PCG64(seed('primary_null_validation',key)))
   while done<REPS:
    b=min(BATCH,REPS-done); x=draw(rng,b,N,means,sds,s['distribution']); est,se,ts,df=stat(x,null)
    rejects+=int(np.count_nonzero(ts < -critical['one_sided_critical']))
    central+=int(np.count_nonzero((ts>=-critical['central_lower_critical'])&(ts<=critical['central_upper_critical'])))
    welch+=int(np.count_nonzero(ts < -student_t.ppf(.95,df)))
    done+=b
   w=wilson(rejects,REPS); wc=wilson(central,REPS)
   row={'scenario':s['name'],'distribution':s['distribution'],'sd_multiplier':s['sd_multiplier'],'offsets':s.get('offsets',[0,0,0,0]),
    'seed':seed('primary_null_validation',key),'replicates':REPS,'rejections':rejects,'type1':rejects/REPS,'type1_wilson95':w,
    'upper_bound_coverage':1-rejects/REPS,'upper_bound_coverage_wilson95':[1-w[1],1-w[0]],'central_interval_coverage_count':central,
    'central_interval_coverage':central/REPS,'central_interval_coverage_wilson95':wc,'welch_rejections_descriptive':welch,
    'welch_type1_descriptive':welch/REPS,'critical':critical['one_sided_critical']}
   save_cell('primary_validation',key,freeze_hash,{'row':row})
  validations.append(row); progress({'phase':'primary_validation','cell':s['name'],'type1':row['type1']})
 powers=[]
 for s in CFG['power_scenarios']:
  for effect in CFG['power_effects']:
   key=f'n{N}/{s["name"]}/delta{effect}'; saved=get_cell('primary_power',key,freeze_hash)
   if saved: row=saved['row']
   else:
    means=float(effect)+np.asarray(s.get('offsets',np.zeros(4)),dtype=float); sds=sd0*float(s['sd_multiplier']); count=welch=0; done=0
    rng=np.random.Generator(np.random.PCG64(seed('primary_power',key)))
    while done<REPS:
     b=min(BATCH,REPS-done); x=draw(rng,b,N,means,sds,s['distribution']); _,_,ts,df=stat(x,null)
     count+=int(np.count_nonzero(ts < -critical['one_sided_critical'])); welch+=int(np.count_nonzero(ts < -student_t.ppf(.95,df))); done+=b
    row={'scenario':s['name'],'distribution':s['distribution'],'sd_multiplier':s['sd_multiplier'],'formal_gate':s['formal_gate'],
     'true_delta':effect,'seed':seed('primary_power',key),'replicates':REPS,'rejections':count,'power':count/REPS,
     'power_wilson95':wilson(count,REPS),'welch_power_descriptive':welch/REPS,'critical':critical['one_sided_critical']}
    save_cell('primary_power',key,freeze_hash,{'row':row})
   powers.append(row); progress({'phase':'primary_power','cell':s['name'],'effect':effect,'power':row['power']})
 return critical,validations,powers

def do_p0(freeze_hash,progress):
 cfg=CFG['p0_no_harm']; boundary=float(cfg['boundary']); base=float(cfg['base_sd']); cal=[]
 for s in cfg['scenarios']:
  key=f'n{N}/{s["name"]}'; saved=get_cell('p0_calibration',key,freeze_hash)
  if saved: row=saved['row']
  else:
   vals=[]; rng=np.random.Generator(np.random.PCG64(seed('p0_null_calibration',key)))
   done=0
   while done<REPS:
    b=min(BATCH,REPS-done); x=draw(rng,b,N,[boundary],[base*s['sd_multiplier']],s['distribution'])[:,0,:]
    _,_,ts=p0stat(x,boundary); vals.append(-ts); done+=b
   q=float(np.quantile(np.concatenate(vals),CFG['monte_carlo']['critical_quantiles']['one_sided_calibration'],method='higher'))
   row={'scenario':s['name'],'distribution':s['distribution'],'sd_multiplier':s['sd_multiplier'],'seed':seed('p0_null_calibration',key),'replicates':REPS,'critical':q}
   save_cell('p0_calibration',key,freeze_hash,{'row':row})
  cal.append(row); progress({'phase':'p0_calibration','cell':s['name']})
 critical=max(x['critical'] for x in cal); nullrows=[]; powerrows=[]
 for s in cfg['scenarios']:
  key=f'n{N}/{s["name"]}'; saved=get_cell('p0_validation',key,freeze_hash)
  if saved: row=saved['row']
  else:
   rng=np.random.Generator(np.random.PCG64(seed('p0_null_validation',key))); rejects=done=0
   while done<REPS:
    b=min(BATCH,REPS-done); x=draw(rng,b,N,[boundary],[base*s['sd_multiplier']],s['distribution'])[:,0,:]
    _,_,ts=p0stat(x,boundary); rejects+=int(np.count_nonzero(ts < -critical)); done+=b
   w=wilson(rejects,REPS); row={'scenario':s['name'],'seed':seed('p0_null_validation',key),'replicates':REPS,'critical':critical,
    'rejections':rejects,'type1':rejects/REPS,'type1_wilson95':w,'upper_bound_coverage':1-rejects/REPS,
    'upper_bound_coverage_wilson95':[1-w[1],1-w[0]]}
   save_cell('p0_validation',key,freeze_hash,{'row':row})
  nullrows.append(row); progress({'phase':'p0_validation','cell':s['name'],'type1':row['type1']})
  for effect in cfg['power_true_effects']:
   pkey=f'n{N}/{s["name"]}/effect{effect}'; stored=get_cell('p0_safety_power',pkey,freeze_hash)
   if stored: prow=stored['row']
   else:
    rng=np.random.Generator(np.random.PCG64(seed('p0_safety_power',pkey))); passed=done=0
    while done<REPS:
     b=min(BATCH,REPS-done); x=draw(rng,b,N,[float(effect)],[base*s['sd_multiplier']],s['distribution'])[:,0,:]
     _,_,ts=p0stat(x,boundary); passed+=int(np.count_nonzero(ts < -critical)); done+=b
    prow={'scenario':s['name'],'true_effect':effect,'seed':seed('p0_safety_power',pkey),'replicates':REPS,
     'no_harm_pass_count':passed,'no_harm_pass_probability':passed/REPS,'wilson95':wilson(passed,REPS),'critical':critical}
    save_cell('p0_safety_power',pkey,freeze_hash,{'row':prow})
   powerrows.append(prow); progress({'phase':'p0_safety_power','cell':s['name'],'effect':effect,'pass_probability':prow['no_harm_pass_probability']})
 return {'n':N,'one_sided_critical':critical,'scenario_calibration':cal},nullrows,powerrows

def decision(critical,nullrows,powers,p0cal,p0null,p0power):
 a=CFG['monte_carlo']['acceptance']
 power_gate=[r for r in powers if r['formal_gate'] and r['true_delta']==a['formal_power_effect']]
 return {
  'primary_type1_pass':len(nullrows)==len(CFG['null_scenarios']) and all(max(r['type1_wilson95'])<=a['type1_wilson_upper_max'] for r in nullrows),
  'primary_one_sided_coverage_pass':all(min(r['upper_bound_coverage_wilson95'])>=a['one_sided_coverage_wilson_lower_min'] for r in nullrows),
  'primary_central_coverage_pass':all(min(r['central_interval_coverage_wilson95'])>=a['central_coverage_wilson_lower_min'] for r in nullrows),
  'p0_type1_pass':len(p0null)==len(CFG['p0_no_harm']['scenarios']) and all(max(r['type1_wilson95'])<=a['type1_wilson_upper_max'] for r in p0null),
  'p0_coverage_pass':all(min(r['upper_bound_coverage_wilson95'])>=a['one_sided_coverage_wilson_lower_min'] for r in p0null),
  'formal_power_cells_count':len(power_gate),
  'formal_power_pass':len(power_gate)==5 and all(min(r['power_wilson95'])>=a['formal_power_wilson_lower_min'] for r in power_gate),
  'all_1_5x_and_2x_power_cells_completed':len(powers)==len(CFG['power_scenarios'])*len(CFG['power_effects']),
  'missing_q2_zero_inflated_cell_present':any(r['scenario']=='zero_inflated65_q2' for r in powers),
  'stage5_sampling_authorized':False,
  'readiness_statistical_gates_pass':all([
   len(nullrows)==len(CFG['null_scenarios']),
   all(max(r['type1_wilson95'])<=a['type1_wilson_upper_max'] for r in nullrows),
   all(min(r['upper_bound_coverage_wilson95'])>=a['one_sided_coverage_wilson_lower_min'] for r in nullrows),
   all(min(r['central_interval_coverage_wilson95'])>=a['central_coverage_wilson_lower_min'] for r in nullrows),
   len(p0null)==len(CFG['p0_no_harm']['scenarios']),
   all(max(r['type1_wilson95'])<=a['type1_wilson_upper_max'] for r in p0null),
   all(min(r['upper_bound_coverage_wilson95'])>=a['one_sided_coverage_wilson_lower_min'] for r in p0null),
   len(power_gate)==5 and all(min(r['power_wilson95'])>=a['formal_power_wilson_lower_min'] for r in power_gate),
   len(powers)==20])
 }

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--preflight',action='store_true'); ap.add_argument('--run-design-mc',action='store_true'); args=ap.parse_args()
 if args.preflight==args.run_design_mc: ap.error('choose exactly one of --preflight or --run-design-mc')
 freeze_hash=verify_freeze()
 if not args.run_design_mc:
  rng=np.random.Generator(np.random.PCG64(seed('independent_statistic_fixture','fixed-small-matrix')))
  x=draw(rng,8,31,np.full(4,-.0002),np.array(CFG['condition_sd'])*1.5,'zero_inflated65_normal')
  assert x.shape==(8,4,31) and np.isfinite(x).all()
  assert len(set(x.shape))==3
  print(json.dumps({'preflight':'PASS','freeze_sha256':freeze_hash,'replicates_per_full_cell':REPS,
   'primary_null_cells':len(CFG['null_scenarios']),'primary_power_cells':len(CFG['power_scenarios'])*2,
   'p0_cells':len(CFG['p0_no_harm']['scenarios'])*4,'stage5_shots_generated':0,'sealed_access':False}))
  return
 start=time.time(); (HERE/'cells').mkdir(exist_ok=True)
 progress_path=HERE/'DESIGN_MC_PROGRESS.jsonl'
 def progress(d):
  with progress_path.open('a',encoding='utf-8') as f: f.write(json.dumps(d)+'\n')
  print(json.dumps(d),flush=True)
 critical,nullrows,powers=do_primary(freeze_hash,progress)
 p0cal,p0null,p0power=do_p0(freeze_hash,progress)
 try:
  import psutil
  rss=int(psutil.Process().memory_info().rss)
 except Exception: rss=None
 out={'study':CFG['study'],'freeze_sha256':freeze_hash,'config_sha256':sha(HERE/'DESIGN_CONFIG.json'),
  'inventory_sha256':sha(HERE/'DESIGN_SEED_INVENTORY.json'),'stage5_evaluation_shots_generated':0,
  'sealed_historical_test_accessed':False,'replicates_per_cell':REPS,'allocation_roots_per_stratum':N,
  'primary_critical_values':critical,'primary_null_validation':nullrows,'primary_power':powers,
  'p0_calibration':p0cal,'p0_null_validation':p0null,'p0_safety_power':p0power,
  'run_seconds':time.time()-start,'process_rss_bytes_at_completion':rss,
  'decision':decision(critical,nullrows,powers,p0cal,p0null,p0power),
  'note':'Synthetic root-effect MC only. Stage 5 allocation and endpoint samples were not generated.'}
 atomic(HERE/'DESIGN_MC_RESULTS.json',out)
 print(json.dumps({'finished':True,'seconds':out['run_seconds'],'decision':out['decision']},indent=2),flush=True)

if __name__=='__main__': main()
