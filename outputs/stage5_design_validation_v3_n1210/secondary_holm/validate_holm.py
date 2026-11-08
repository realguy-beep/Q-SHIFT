"""Synthetic operating characteristics for the frozen candidate Welch/Holm family."""
from __future__ import annotations
import argparse,hashlib,json,math,os,time
from pathlib import Path
import numpy as np
from scipy.stats import norm,t as student_t
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]; PARENT=HERE.parent
CFG=json.loads((HERE/'SECONDARY_HOLM_CONFIG.json').read_text(encoding='utf-8'))
INV=json.loads((HERE/'SECONDARY_HOLM_SEED_INVENTORY.json').read_text(encoding='utf-8'))
BASE=json.loads((PARENT/'DESIGN_CONFIG.json').read_text(encoding='utf-8'))
N=int(CFG['n_roots_per_condition']); R=int(CFG['replicates_per_family']); B=int(CFG['batch_size'])
SEEDS={r['cell']:int(r['seed']) for r in INV['streams']}

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def verify():
 f=json.loads((HERE/'SECONDARY_HOLM_FREEZE.json').read_text(encoding='utf-8'))
 for rel,want in f['secondary_design_input_sha256'].items():
  if sha(ROOT/rel)!=want: raise RuntimeError(f'secondary input hash mismatch: {rel}')
 for rel,want in f['reviewed_parent_and_historical_evidence_sha256'].items():
  if sha(ROOT/rel)!=want: raise RuntimeError(f'parent evidence hash mismatch: {rel}')
 return sha(HERE/'SECONDARY_HOLM_FREEZE.json')
def wilson_upper(k,n,z):
 p=k/n; zz=z*z; d=1+zz/n; mid=(p+zz/(2*n))/d
 half=z*math.sqrt(p*(1-p)/n+zz/(4*n*n))/d
 return min(1.,mid+half)
def draw(g,fam,mu,sd,shape):
 mu=np.asarray(mu,dtype=float); sd=np.asarray(sd,dtype=float); loc=mu[None,:,None]; scale=sd[None,:,None]
 if fam=='normal': return g.normal(loc,scale,size=shape)
 if fam.startswith('student_t'):
  df=int(fam.removeprefix('student_t')); return loc+scale*g.standard_t(df,size=shape)/math.sqrt(df/(df-2))
 if fam=='lognormal_sigma1':
  x=g.lognormal(0.,1.,size=shape); return loc+scale*((x-math.exp(.5))/math.sqrt((math.e-1)*math.e))
 if fam=='zero_inflated65_normal':
  q=.35; cm=mu/q; cv=(sd*sd+mu*mu)/q-cm*cm
  y=g.normal(cm[None,:,None],np.sqrt(cv)[None,:,None],size=shape)
  return np.where(g.random(size=shape)<.65,0.,y)
 if fam=='tied_asymmetric65':
  pl,ph=.28,.07; q=pl+ph; cm=mu/q; cv=(sd*sd+mu*mu)/q-cm*cm
  lo=cm-np.sqrt(cv*(ph/q)/(pl/q)); hi=cm+np.sqrt(cv*(pl/q)/(ph/q)); u=g.random(size=shape)
  return np.where(u<.65,0.,np.where(u<.93,lo[None,:,None],hi[None,:,None]))
 raise KeyError(fam)
def sample_pvalues(x):
 # Mirrors the frozen candidate's one_sample_summary + lower-tail t reference.
 avg=x.mean(axis=2); sd=x.std(axis=2,ddof=1); se=sd/math.sqrt(x.shape[2]); t=np.zeros_like(avg)
 positive=se>0; t[positive]=avg[positive]/se[positive]
 p=student_t.cdf(t,x.shape[2]-1)
 p=np.where((se==0)&(avg<0),0.,p); p=np.where((se==0)&(avg>=0),1.,p)
 return p
def holm_adjusted(p):
 ordered=np.sort(p,axis=1); factors=np.array([4.,3.,2.,1.],dtype=float)
 candidate=np.minimum(1.,ordered*factors[None,:]); candidate=np.maximum.accumulate(candidate,axis=1)
 # Any adjusted p<=.05 is a family rejection; sorting is only over 4 tests.
 return np.any(candidate<=.05,axis=1)
def main():
 ap=argparse.ArgumentParser(); group=ap.add_mutually_exclusive_group(required=True)
 group.add_argument('--preflight',action='store_true'); group.add_argument('--run-secondary-mc',action='store_true')
 args=ap.parse_args(); freeze_hash=verify()
 if args.preflight:
  rng=np.random.Generator(np.random.PCG64(SEEDS[CFG['scenario_families'][0]['name']]))
  smoke=draw(rng,'zero_inflated65_normal',np.zeros(4),np.asarray(BASE['condition_sd'])*2.,(32,4,N))
  assert smoke.shape==(32,4,N) and np.isfinite(smoke).all()
  assert np.array_equal(holm_adjusted(np.array([[.001,.01,.03,.8],[.02,.03,.04,.05],[.2,.3,.4,.5]])),[True,False,False])
  print(json.dumps({'secondary_holm_preflight':'PASS','freeze_sha256':freeze_hash,'MC_runs_started':False,
   'Stage5_shots_generated':0,'sealed_access':False})); return
 start=time.time(); rootsd=np.asarray(BASE['condition_sd'],dtype=float); thresholds=np.asarray(CFG['holm_step_thresholds'])
 levels=[]; families=[]; z_point=norm.ppf(.975); z_sim=norm.ppf(1-.05/CFG['acceptance']['marginal_simultaneous_cells'])
 z_fwer=norm.ppf(1-.05/CFG['acceptance']['holm_family_cells'])
 for sc in CFG['scenario_families']:
  seed=SEEDS[sc['name']]; g=np.random.Generator(np.random.PCG64(seed)); counts=np.zeros((4,4),dtype=np.int64); fam_rej=0; done=0
  while done<R:
   b=min(B,R-done); arr=draw(g,sc['distribution'],np.zeros(4),rootsd*sc['sd_multiplier'],(b,4,N)); p=sample_pvalues(arr)
   counts+=np.sum(p[:,:,None] <= thresholds[None,None,:],axis=0)
   fam_rej+=int(np.count_nonzero(holm_adjusted(p))); done+=b
  for cond in range(4):
   for j,alpha in enumerate(thresholds):
    k=int(counts[cond,j]); upper95=wilson_upper(k,R,z_point); upper_sim=wilson_upper(k,R,z_sim)
    levels.append({'scenario':sc['name'],'distribution':sc['distribution'],'sd_multiplier':sc['sd_multiplier'],
     'condition_index':cond,'holm_step_alpha':float(alpha),'replicates':R,'rejections':k,'rate':k/R,
     'wilson95_pointwise_upper':upper95,'wilson95_familywise_simultaneous_upper':upper_sim,
     'tolerance_limit':float(alpha)+CFG['acceptance']['marginal_wilson_upper_tolerance_above_step_alpha'],
     'pass':upper_sim <= float(alpha)+CFG['acceptance']['marginal_wilson_upper_tolerance_above_step_alpha']})
  fu=wilson_upper(fam_rej,R,z_fwer)
  families.append({'scenario':sc['name'],'distribution':sc['distribution'],'sd_multiplier':sc['sd_multiplier'],
    'replicates':R,'holm_family_rejections':fam_rej,'holm_familywise_rate':fam_rej/R,
    'simultaneous_wilson_upper':fu,'limit':CFG['acceptance']['holm_familywise_upper_max'],'pass':fu<=CFG['acceptance']['holm_familywise_upper_max']})
  print(json.dumps({'scenario':sc['name'],'familywise':fam_rej/R,'worst_marginal_simultaneous_upper':max(x['wilson95_familywise_simultaneous_upper'] for x in levels if x['scenario']==sc['name'])}),flush=True)
 result={'freeze_sha256':freeze_hash,'stage5_shots_generated':0,'sealed_test_accessed':False,
  'scenario_count':len(CFG['scenario_families']),'roots_per_condition':N,'replicates_per_scenario':R,
  'marginal_checks':len(levels),'holm_family_cells':len(families),'holm_step_thresholds':thresholds.tolist(),
  'marginal_z_simultaneous':float(z_sim),'holm_fwer_z_simultaneous':float(z_fwer),
  'marginal_pvalue_validation':levels,'complete_null_holm_fwer':families,
  'all_marginal_checks_pass':all(x['pass'] for x in levels),'all_holm_fwer_checks_pass':all(x['pass'] for x in families),
  'overall_secondary_validation_pass':all(x['pass'] for x in levels) and all(x['pass'] for x in families),
  'runtime_seconds':time.time()-start,
  'limitation':'Finite family simulation; not a universal proof of strong FWER control outside the frozen null distributions and SD values.'}
 tmp=HERE/'SECONDARY_HOLM_RESULTS.json.tmp'; tmp.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8'); os.replace(tmp,HERE/'SECONDARY_HOLM_RESULTS.json')
 print(json.dumps({'finished':True,'pass':result['overall_secondary_validation_pass'],'runtime_seconds':result['runtime_seconds']},indent=2))
if __name__=='__main__': main()
