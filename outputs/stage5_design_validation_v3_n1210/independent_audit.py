"""Independent full replay and audit; does not import design_mc.py."""
from __future__ import annotations
import hashlib,json,math,os,time
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
CFG=json.loads((HERE/'DESIGN_CONFIG.json').read_text(encoding='utf-8'))
INV=json.loads((HERE/'DESIGN_SEED_INVENTORY.json').read_text(encoding='utf-8'))
R=int(CFG['monte_carlo']['calibration_replicates_per_scenario']); B=int(CFG['monte_carlo']['batch_size']); N=int(CFG['allocation_roots_per_stratum'])
SM={(x['stream'],x['cell']):int(x['seed']) for x in INV['rng_streams']}

def digest(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  while True:
   block=f.read(1<<20)
   if not block: break
   h.update(block)
 return h.hexdigest()

def interval(success,total):
 # Wilson score interval, coded independently from production.
 z=1.959963984540054; phat=success/total; z2=z*z; d=1+z2/total
 mid=(phat+z2/(2*total))/d
 rad=z*math.sqrt(phat*(1-phat)/total+z2/(4*total*total))/d
 return [max(0.,mid-rad),min(1.,mid+rad)]

def family_draw(generator,kind,mu,sigma,shape):
 # Reference construction is intentionally expressed separately; random-call order matches the frozen stream definition.
 mu=np.array(mu,dtype=np.float64); sigma=np.array(sigma,dtype=np.float64); loc=mu[None,:,None]; scale=sigma[None,:,None]
 if kind=='normal': return generator.normal(loc=loc,scale=scale,size=shape)
 if kind.startswith('student_t'):
  df=int(kind.split('student_t',1)[1]); standardized=generator.standard_t(df,size=shape)/math.sqrt(df/(df-2))
  return loc+scale*standardized
 if kind=='lognormal_sigma1':
  a=generator.lognormal(mean=0.,sigma=1.,size=shape)
  return loc+scale*((a-math.exp(.5))/math.sqrt((math.e-1)*math.e))
 if kind=='zero_inflated65_normal':
  keep=.35; cm=mu/keep; cv=(sigma**2+mu**2)/keep-cm**2
  values=generator.normal(cm[None,:,None],np.sqrt(cv)[None,:,None],size=shape)
  return np.where(generator.random(size=shape)<.65,0.,values)
 if kind=='tied_asymmetric65':
  p_low=.28; p_high=.07; p_active=p_low+p_high; w_low=p_low/p_active; w_high=p_high/p_active
  cm=mu/p_active; cv=(sigma**2+mu**2)/p_active-cm**2
  lower=cm-np.sqrt(cv*w_high/w_low); upper=cm+np.sqrt(cv*w_low/w_high)
  u=generator.random(size=shape)
  return np.where(u<.65,0.,np.where(u<.93,lower[None,:,None],upper[None,:,None]))
 raise KeyError(kind)

def t_stat(matrix,center):
 # Independently compute the stratified mean variance and Satterthwaite degrees of freedom.
 m=np.mean(matrix,axis=-1); v=np.var(matrix,axis=-1,ddof=1); k=matrix.shape[1]; n=matrix.shape[2]
 component=v/(k*k*n); total=np.sum(component,axis=1); mean=np.mean(m,axis=1); se=np.sqrt(total)
 t=np.zeros_like(mean); nz=se!=0; t[nz]=(mean[nz]-center)/se[nz]
 t[(~nz)&(mean<center)]=-np.inf; t[(~nz)&(mean>center)]=np.inf
 denom=np.sum(component**2/(n-1),axis=1); df=np.full_like(total,np.inf); q=denom!=0; df[q]=total[q]**2/denom[q]
 return mean,se,t,df

def scalar_stat(matrix,center):
 avg=np.mean(matrix,axis=1); stdev=np.std(matrix,axis=1,ddof=1); se=stdev/math.sqrt(matrix.shape[1])
 t=np.zeros_like(avg); nz=se!=0; t[nz]=(avg[nz]-center)/se[nz]
 t[(~nz)&(avg<center)]=-np.inf; t[(~nz)&(avg>center)]=np.inf
 return avg,se,t

def batches(seed,means,sds,kind):
 g=np.random.Generator(np.random.PCG64(seed)); finished=0
 while finished<R:
  count=min(B,R-finished); yield family_draw(g,kind,means,sds,(count,len(means),N)); finished+=count

def main():
 freeze_path=HERE/'DESIGN_VALIDATION_FREEZE.json'; freeze=json.loads(freeze_path.read_text(encoding='utf-8'))
 for rel,want in freeze['design_input_sha256'].items():
  if digest(ROOT/rel)!=want: raise AssertionError(f'frozen input hash mismatch: {rel}')
 for rel,want in freeze['historical_evidence_sha256'].items():
  if digest(ROOT/rel)!=want: raise AssertionError(f'historical hash mismatch: {rel}')
 if json.loads((HERE/'DESIGN_MC_RESULTS.json').read_text(encoding='utf-8'))['stage5_evaluation_shots_generated']!=0: raise AssertionError('Stage 5 shots field not zero')
 if freeze.get('sealed_historical_test_accessed') is not False: raise AssertionError('sealed-access flag invalid')
 seeds=[r['seed'] for r in INV['rng_streams']]
 if len(seeds)!=len(set(seeds)) or INV.get('collision_count')!=0: raise AssertionError('RNG inventory collision or duplicate')
 saved=json.loads((HERE/'DESIGN_MC_RESULTS.json').read_text(encoding='utf-8'))
 started=time.time(); base=np.asarray(CFG['condition_sd'],dtype=float); boundary=float(CFG['null_boundary']); q=CFG['monte_carlo']['critical_quantiles']
 refcal=[]
 for sc in CFG['null_scenarios']:
  key=f'n{N}/{sc["name"]}'; means=boundary+np.asarray(sc.get('offsets',[0,0,0,0]),dtype=float); sds=base*sc['sd_multiplier']; neg=[]; pos=[]
  for block in batches(SM[('primary_null_calibration',key)],means,sds,sc['distribution']):
   _,_,z,_=t_stat(block,boundary); neg.append(-z); pos.append(z)
  left=np.concatenate(neg); right=np.concatenate(pos)
  refcal.append({'scenario':sc['name'],'q_one_sided':float(np.quantile(left,q['one_sided_calibration'],method='higher')),
    'q_central_lower':float(np.quantile(left,q['central_tail'],method='higher')),
    'q_central_upper':float(np.quantile(right,q['central_tail'],method='higher'))})
 c1=max(x['q_one_sided'] for x in refcal); clo=max(x['q_central_lower'] for x in refcal); chi=max(x['q_central_upper'] for x in refcal)
 prod=saved['primary_critical_values']
 for key,ref in [('one_sided_critical',c1),('central_lower_critical',clo),('central_upper_critical',chi)]:
  if abs(prod[key]-ref)>1e-12: raise AssertionError(f'critical value mismatch {key}: {prod[key]} vs {ref}')
 vrows=[]
 for sc in CFG['null_scenarios']:
  key=f'n{N}/{sc["name"]}'; means=boundary+np.asarray(sc.get('offsets',[0,0,0,0]),dtype=float); sds=base*sc['sd_multiplier']; hits=inside=0; done=0
  for block in batches(SM[('primary_null_validation',key)],means,sds,sc['distribution']):
   _,_,z,_=t_stat(block,boundary); hits+=int(np.count_nonzero(z < -c1)); inside+=int(np.count_nonzero((z>=-clo)&(z<=chi))); done+=len(z)
  w=interval(hits,R); cw=interval(inside,R); r={'scenario':sc['name'],'rejections':hits,'type1':hits/R,'type1_wilson95':w,
   'upper_bound_coverage':1-hits/R,'upper_bound_coverage_wilson95':[1-w[1],1-w[0]],'central_interval_coverage_count':inside,
   'central_interval_coverage':inside/R,'central_interval_coverage_wilson95':cw}
  vrows.append(r)
  corresponding=next(x for x in saved['primary_null_validation'] if x['scenario']==sc['name'])
  for field in ['rejections','central_interval_coverage_count']:
   if corresponding[field]!=r[field]: raise AssertionError(f'validation exact replay mismatch {sc["name"]}/{field}')
  if abs(corresponding['type1']-r['type1'])>1e-15: raise AssertionError(f'type-I rate mismatch {sc["name"]}')
 powerrows=[]
 for sc in CFG['power_scenarios']:
  for effect in CFG['power_effects']:
   key=f'n{N}/{sc["name"]}/delta{effect}'; means=float(effect)+np.asarray(sc.get('offsets',[0,0,0,0]),dtype=float); sds=base*sc['sd_multiplier']; count=0
   for block in batches(SM[('primary_power',key)],means,sds,sc['distribution']):
    _,_,z,_=t_stat(block,boundary); count+=int(np.count_nonzero(z < -c1))
   row={'scenario':sc['name'],'true_delta':effect,'rejections':count,'power':count/R,'power_wilson95':interval(count,R)}; powerrows.append(row)
   p=next(x for x in saved['primary_power'] if x['scenario']==sc['name'] and x['true_delta']==effect)
   if p['rejections']!=count: raise AssertionError(f'power exact replay mismatch {sc["name"]}/{effect}')
 # Rebuild the independent p=0 cutoff envelope and then verify null and safety-power counts.
 p0=CFG['p0_no_harm']; bd=float(p0['boundary']); sd=float(p0['base_sd']); pcal=[]
 for sc in p0['scenarios']:
  key=f'n{N}/{sc["name"]}'; collect=[]
  for block in batches(SM[('p0_null_calibration',key)],[bd],[sd*sc['sd_multiplier']],sc['distribution']):
   _,_,z=scalar_stat(block[:,0,:],bd); collect.append(-z)
  arr=np.concatenate(collect); pcal.append(float(np.quantile(arr,q['one_sided_calibration'],method='higher')))
 cp=max(pcal); pv=[]; pp=[]
 for sc in p0['scenarios']:
  key=f'n{N}/{sc["name"]}'; reject=0
  for block in batches(SM[('p0_null_validation',key)],[bd],[sd*sc['sd_multiplier']],sc['distribution']):
   _,_,z=scalar_stat(block[:,0,:],bd); reject+=int(np.count_nonzero(z < -cp))
  w=interval(reject,R); pv.append({'scenario':sc['name'],'rejections':reject,'type1':reject/R,'type1_wilson95':w,'upper_bound_coverage':1-reject/R,'upper_bound_coverage_wilson95':[1-w[1],1-w[0]]})
  p=next(x for x in saved['p0_null_validation'] if x['scenario']==sc['name'])
  if p['rejections']!=reject: raise AssertionError(f'p0 null exact replay mismatch {sc["name"]}')
  for effect in p0['power_true_effects']:
   pk=f'n{N}/{sc["name"]}/effect{effect}'; success=0
   for block in batches(SM[('p0_safety_power',pk)],[float(effect)],[sd*sc['sd_multiplier']],sc['distribution']):
    _,_,z=scalar_stat(block[:,0,:],bd); success+=int(np.count_nonzero(z < -cp))
   pp.append({'scenario':sc['name'],'true_effect':effect,'pass_count':success,'pass_probability':success/R,'wilson95':interval(success,R)})
   pwr=next(x for x in saved['p0_safety_power'] if x['scenario']==sc['name'] and x['true_effect']==effect)
   if pwr['no_harm_pass_count']!=success: raise AssertionError(f"p0 power exact replay mismatch {sc['name']}/{effect}")
 # Independent re-evaluation of frozen gates.
 acc=CFG['monte_carlo']['acceptance']; formal=[x for x in powerrows if x['true_delta']==acc['formal_power_effect'] and x['scenario'].endswith('q1_5')]
 gates={'primary_type1_pass':all(max(x['type1_wilson95'])<=acc['type1_wilson_upper_max'] for x in vrows),
  'primary_one_sided_coverage_pass':all(min(x['upper_bound_coverage_wilson95'])>=acc['one_sided_coverage_wilson_lower_min'] for x in vrows),
  'primary_central_coverage_pass':all(min(x['central_interval_coverage_wilson95'])>=acc['central_coverage_wilson_lower_min'] for x in vrows),
  'p0_type1_pass':all(max(x['type1_wilson95'])<=acc['type1_wilson_upper_max'] for x in pv),
  'p0_coverage_pass':all(min(x['upper_bound_coverage_wilson95'])>=acc['one_sided_coverage_wilson_lower_min'] for x in pv),
  'formal_power_pass':len(formal)==5 and all(min(x['power_wilson95'])>=acc['formal_power_wilson_lower_min'] for x in formal)}
 report={'audit':'Independent full PCG64 stream replay and inferential recomputation; no import from production design_mc.py',
  'freeze_sha256':digest(freeze_path),'stage5_shots_generated':0,'sealed_historical_test_accessed':False,
  'historical_evidence_hashes_verified':len(freeze['historical_evidence_sha256']),'input_hashes_verified':len(freeze['design_input_sha256']),
  'primary_calibration_cells_replayed':len(refcal),'primary_validation_cells_replayed':len(vrows),
  'primary_power_cells_replayed':len(powerrows),'p0_calibration_cells_replayed':len(pcal),
  'p0_validation_cells_replayed':len(pv),'p0_safety_power_cells_replayed':len(pp),
  'all_replay_counts_match':True,'recomputed_gates':gates,'audit_runtime_seconds':time.time()-started,
  'limitations':['Exact replay verifies implementation consistency under NumPy/PCG64 on this environment; it cannot validate the completeness of the finite distribution envelope or seven-root SD inputs.',
   'Holm secondary condition-level inference is not covered by this primary-endpoint operating-characteristic audit.']}
 temp=HERE/'INDEPENDENT_AUDIT.json.tmp'; temp.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8'); os.replace(temp,HERE/'INDEPENDENT_AUDIT.json')
 print(json.dumps({'audit':'PASS','counts_match':True,'gates':gates,'runtime_seconds':report['audit_runtime_seconds']},indent=2))

if __name__=='__main__': main()
