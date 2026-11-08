"""Independent replay of secondary Welch/Holm operating characteristics."""
from __future__ import annotations
import hashlib,json,math,os,time
from pathlib import Path
import numpy as np
from scipy.stats import norm,t as tdist
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]; PARENT=HERE.parent
CFG=json.loads((HERE/'SECONDARY_HOLM_CONFIG.json').read_text(encoding='utf-8'))
INV=json.loads((HERE/'SECONDARY_HOLM_SEED_INVENTORY.json').read_text(encoding='utf-8'))
BASE=json.loads((PARENT/'DESIGN_CONFIG.json').read_text(encoding='utf-8'))
N=CFG['n_roots_per_condition']; R=CFG['replicates_per_family']; B=CFG['batch_size']
SEED={v['cell']:v['seed'] for v in INV['streams']}

def file_hash(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for block in iter(lambda:f.read(1<<20),b''): h.update(block)
 return h.hexdigest()
def draw_family(rng,family,mu,sigma,size):
 # Independent transcription of the frozen categorical root-effect stress laws.
 mu=np.asarray(mu,float); sigma=np.asarray(sigma,float); L=mu[None,:,None]; S=sigma[None,:,None]
 if family=='normal': return rng.normal(loc=L,scale=S,size=size)
 if family.startswith('student_t'):
  df=int(family.replace('student_t','')); return L+S*(rng.standard_t(df,size=size)/math.sqrt(df/(df-2)))
 if family=='lognormal_sigma1':
  raw=rng.lognormal(mean=0.,sigma=1.,size=size); standardized=(raw-math.exp(.5))/math.sqrt((math.e-1.)*math.e)
  return L+S*standardized
 if family=='zero_inflated65_normal':
  active=.35; cm=mu/active; cv=(sigma*sigma+mu*mu)/active-cm*cm
  y=rng.normal(loc=cm[None,:,None],scale=np.sqrt(cv)[None,:,None],size=size)
  zeros=rng.random(size=size)<.65
  return np.where(zeros,0.,y)
 if family=='tied_asymmetric65':
  pl=.28; ph=.07; q=pl+ph; cm=mu/q; cv=(sigma*sigma+mu*mu)/q-cm*cm
  lo=cm-np.sqrt(cv*(ph/q)/(pl/q)); hi=cm+np.sqrt(cv*(pl/q)/(ph/q))
  draw=rng.random(size=size)
  return np.where(draw<.65,0.,np.where(draw<.93,lo[None,:,None],hi[None,:,None]))
 raise ValueError(family)
def reference_pvalues(sample):
 avg=np.mean(sample,axis=2); spread=np.sqrt(np.var(sample,axis=2,ddof=1)); stderr=spread/np.sqrt(sample.shape[2])
 ratio=np.zeros_like(avg); nz=stderr>0; ratio[nz]=avg[nz]/stderr[nz]
 result=tdist.cdf(ratio,sample.shape[2]-1)
 result=np.where((stderr==0)&(avg<0),0.,result)
 return np.where((stderr==0)&(avg>=0),1.,result)
def reject_holm(p):
 ordered=np.sort(p,axis=1); reject=np.zeros(p.shape[0],dtype=bool); continuing=np.ones(p.shape[0],dtype=bool)
 for j,critical in enumerate([.05/4,.05/3,.05/2,.05]):
  current=continuing & (ordered[:,j] <= critical)
  reject |= current; continuing &= (ordered[:,j] <= critical)
 return reject
def upper(success,trials,z):
 p=success/trials; zsq=z*z; den=1+zsq/trials
 mid=(p+zsq/(2*trials))/den; half=z*math.sqrt(p*(1-p)/trials+zsq/(4*trials*trials))/den
 return min(1.,mid+half)
def main():
 fr=json.loads((HERE/'SECONDARY_HOLM_REPAIR_FREEZE.json').read_text(encoding='utf-8'))
 for rel,h in fr['repair_design_input_sha256'].items():
  if file_hash(ROOT/rel)!=h: raise AssertionError(f'secondary frozen hash mismatch: {rel}')
 for rel,h in fr['parent_and_failure_evidence_sha256'].items():
  if file_hash(ROOT/rel)!=h: raise AssertionError(f'parent evidence hash mismatch: {rel}')
 saved=json.loads((HERE/'SECONDARY_HOLM_RESULTS_REPAIR_V1.json').read_text(encoding='utf-8'))
 thresholds=np.asarray(CFG['holm_step_thresholds']); started=time.time(); matrix=[]; fwer=[]
 for scenario in CFG['scenario_families']:
  rng=np.random.Generator(np.random.PCG64(SEED[scenario['name']])); counts=np.zeros((4,4),dtype=np.int64); rejects=0; done=0
  scale=np.asarray(BASE['condition_sd'])*scenario['sd_multiplier']
  while done<R:
   size=min(B,R-done)
   x=draw_family(rng,scenario['distribution'],np.zeros(4),scale,(size,4,N))
   p=reference_pvalues(x)
   for c in range(4):
    for a,cut in enumerate(thresholds): counts[c,a]+=int(np.count_nonzero(p[:,c] <= cut))
   rejects+=int(np.count_nonzero(reject_holm(p))); done+=size
  for c in range(4):
   for a,cut in enumerate(thresholds): matrix.append((scenario['name'],c,float(cut),int(counts[c,a])))
  fwer.append((scenario['name'],rejects))
 point_z=norm.ppf(.975); simultaneous_z=norm.ppf(1-.05/CFG['acceptance']['marginal_simultaneous_cells'])
 fwer_z=norm.ppf(1-.05/CFG['acceptance']['holm_family_cells'])
 for row in saved['marginal_pvalue_validation']:
  item=(row['scenario'],row['condition_index'],row['holm_step_alpha'],row['rejections'])
  if item not in matrix: raise AssertionError(f'independent marginal replay mismatch: {item}')
  k=row['rejections']; alpha=row['holm_step_alpha']
  point=upper(k,R,point_z); sim=upper(k,R,simultaneous_z)
  if abs(point-row['wilson95_pointwise_upper'])>1e-12 or abs(sim-row['wilson95_familywise_simultaneous_upper'])>1e-12:
   raise AssertionError('independent Wilson bound differs from saved result')
 for row in saved['complete_null_holm_fwer']:
  got=next(v for name,v in fwer if name==row['scenario'])
  if got!=row['holm_family_rejections']: raise AssertionError(f"Holm family replay mismatch: {row['scenario']}")
  if abs(upper(got,R,fwer_z)-row['simultaneous_wilson_upper'])>1e-12: raise AssertionError('Holm Wilson bound mismatch')
 gates={'marginal_pvalue_validity_pass':all(x['pass'] for x in saved['marginal_pvalue_validation']),
  'complete_null_holm_fwer_pass':all(x['pass'] for x in saved['complete_null_holm_fwer']),
  'all_scenarios_replayed':len(fwer)==10,'all_marginal_counts_replayed':len(matrix)==160}
 audit={'audit':'Independent full PCG64 replay, Welch-pvalue reconstruction, Holm step-down, and Wilson recomputation; no import from validate_holm.py',
  'freeze_sha256':file_hash(HERE/'SECONDARY_HOLM_FREEZE.json'),'stage5_shots_generated':0,'sealed_test_accessed':False,
  'frozen_inputs_verified':len(fr['secondary_design_input_sha256']),'parent_hashes_verified':len(fr['reviewed_parent_and_historical_evidence_sha256']),
  'marginal_rejection_cells_replayed':len(matrix),'familywise_cells_replayed':len(fwer),'all_counts_exactly_match':True,
  'gates':gates,'runtime_seconds':time.time()-started,
  'limitations':['Finite null envelope only; it does not prove super-uniformity outside named families and frozen SDs.',
   'Marginal validations support Holm through the standard super-uniform-p-value condition within the simulated envelope; no arbitrary dependence is simulated between conditions.']}
 temp=HERE/'SECONDARY_HOLM_AUDIT_REPAIR_V1.json.tmp'; temp.write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8'); os.replace(temp,HERE/'SECONDARY_HOLM_AUDIT_REPAIR_V1.json')
 print(json.dumps({'audit':'PASS','gates':gates,'runtime_seconds':audit['runtime_seconds']},indent=2))
if __name__=='__main__': main()
