"""Read-only Stage 5 evidence audit, independent of runner and reporting code."""
from __future__ import annotations
import argparse, hashlib, json, math, sys
from pathlib import Path
import numpy as np
import pymatching

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit

PS=(0.,.004,.008,.012,.016); STREAMS=('calibration_detector_only','paired_evaluation_detector_observable')

def digest(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

def features(det):
 d=np.asarray(det)
 if d.ndim!=2 or d.shape[1]!=40 or not np.isin(d,(0,1)).all(): raise ValueError('invalid detector matrix')
 return np.column_stack([d,np.column_stack([d[:,a]&d[:,b] for a,b in ((8,10),(16,18),(24,26),(32,34),(36,38))])]).astype(float)

def independent_estimate(det,profile):
 obs=features(det).mean(axis=0); knots=np.asarray(profile['probabilities'],float)
 means=np.asarray(profile['means'],float); scales=np.asarray(profile['scales'],float); step=float(profile.get('grid_step',1e-5))
 if means.shape!=(len(knots),45) or scales.shape!=(45,) or np.any(scales<=0): raise ValueError('profile shape invalid')
 count=round((knots[-1]-knots[0])/step)+1; grid=np.linspace(knots[0],knots[-1],max(2,int(count)))
 interp=np.empty((len(grid),45))
 for j in range(45): interp[:,j]=np.interp(grid,knots,means[:,j])
 scores=np.square((interp-obs)/scales).mean(axis=1)
 return float(grid[np.argmin(scores)])

def independent_matcher(p):
 c=build_spatial_burst_circuit(memory_basis='z',regime='balanced',distance=3,rounds=5,
  gate_p=.003,measurement_p=.003,bias_ratio=10.,burst_probability=float(p),burst_pair=(8,10))
 if (c.num_detectors,c.num_observables)!=(40,1): raise ValueError('circuit mismatch')
 dem=c.detector_error_model(decompose_errors=True,approximate_disjoint_errors=True)
 if (dem.num_detectors,dem.num_observables)!=(40,1): raise ValueError('DEM mismatch')
 return pymatching.Matching.from_detector_error_model(dem,enable_correlations=True)

def decode(matcher,d):
 x=np.asarray(matcher.decode_batch(np.asarray(d,dtype=np.uint8)),dtype=np.uint8).reshape(-1)
 if x.shape!=(len(d),) or not np.isin(x,(0,1)).all(): raise ValueError('invalid independent prediction')
 return x

def holm(p):
 p=np.asarray(p,float); order=np.argsort(p,kind='stable'); out=np.empty_like(p); running=0.
 for rank,i in enumerate(order): running=max(running,(len(p)-rank)*p[i]); out[i]=min(1.,running)
 return out.tolist()

def sign_test(x,rng,n):
 x=np.asarray(x,float); observed=abs(x.mean()); extreme=0
 for start in range(0,n,5000):
  b=min(5000,n-start); s=rng.integers(0,2,size=(b,len(x)),dtype=np.int8)*2-1
  extreme+=int(np.count_nonzero(np.abs(s@x/len(x))>=observed-1e-15))
 return (extreme+1)/(n+1)

def boot_ci(groups,rng,n):
 means=[]
 for p in sorted(groups):
  x=np.asarray(groups[p],float); ids=rng.integers(0,len(x),size=(n,len(x)))
  means.append(x[ids].mean(axis=1))
 v=np.mean(means,axis=0)
 return [float(np.quantile(v,.025)),float(np.quantile(v,.975))]

def independent_stats(groups,cfg):
 st=cfg['statistical_plan']; ps=[.004,.008,.012,.016]
 primary=float(np.mean([np.asarray(groups[p]).mean() for p in ps]))
 rng=np.random.Generator(np.random.PCG64(st['bootstrap']['seed']))
 ci=boot_ci({p:groups[p] for p in ps},rng,st['bootstrap']['resamples'])
 x0=np.asarray(groups[0.]); idx=rng.integers(0,len(x0),size=(st['bootstrap']['resamples'],len(x0)))
 upper=float(np.quantile(x0[idx].mean(axis=1),.95))
 rng2=np.random.Generator(np.random.PCG64(st['primary_signflip']['seed']))
 p_primary=sign_test(np.concatenate([groups[p] for p in ps]),rng2,st['primary_signflip']['assignments'])
 p_secondary=[sign_test(groups[p],rng2,st['primary_signflip']['assignments']) for p in ps]
 return {'primary_delta':primary,'primary_bootstrap_95ci':ci,'primary_signflip_p':p_primary,
  'secondary_signflip_p_raw':p_secondary,'secondary_signflip_p_holm':holm(p_secondary),
  'zero_burst_one_sided_bootstrap_95_upper':upper,
  'condition_mean_differences':{str(p):float(np.mean(groups[p])) for p in sorted(groups)},
  'resampling_unit':'independent root; no shot-level resampling'}

def audit(root_dir,output=None):
 root_dir=Path(root_dir); cfg=json.loads((HERE/'STAGE5_V2_CONFIG.json').read_text(encoding='utf-8'))
 freeze=json.loads((HERE/'STAGE5_V2_FREEZE.json').read_text(encoding='utf-8'))
 for rel,expected_hash in freeze['sha256'].items():
  f=ROOT/rel
  if not f.is_file() or digest(f)!=expected_hash: raise ValueError(f'frozen source/configuration hash mismatch: {rel}')
 inv=json.loads((HERE/'seed_inventory.json').read_text(encoding='utf-8'))
 seed={}
 for r in inv['streams']:
  k=(r['kind'],float(r['probability']),int(r['root']))
  if k in seed: raise ValueError(f'duplicate stream {k}')
  seed[k]=int(r['seed'])
 expected={(kind,p,i) for kind in STREAMS for p in PS for i in range(100)}
 all_seeds=list(seed.values())+list(inv['analysis_rngs'].values())
 if set(seed)!=expected or len(all_seeds)!=1002 or len(set(all_seeds))!=1002: raise ValueError('seed inventory incomplete/colliding')
 profile=json.loads((HERE/'FROZEN_PROFILE_ESTIMATOR.json').read_text(encoding='utf-8'))
 fixed=independent_matcher(0.); oracles={p:independent_matcher(p) for p in PS}
 groups={p:[] for p in PS}; roots=[]; hashes={}; total_cal=total_eval=0
 condition={p:{'fixed_errors':0,'profile_errors':0,'oracle_errors':0,'candidate_only':0,'fixed_only':0,'prediction_disagreements':0} for p in PS}
 for p in PS:
  for i in range(100):
   f=root_dir/f'root_p{p:.3f}_r{i:03d}.npz'
   if not f.is_file(): raise FileNotFoundError(f'missing {f.name}')
   hashes[f.name]=digest(f)
   with np.load(f,allow_pickle=False) as z:
    required={'phase','calibration_detectors','evaluation_detectors','observables','predictions','p_hat','probability','root','seed_calibration','seed_evaluation'}
    if set(z.files)!=required or str(np.asarray(z['phase']).item())!='complete': raise ValueError(f'invalid schema/phase {f.name}')
    cal=np.asarray(z['calibration_detectors']); det=np.asarray(z['evaluation_detectors']); obs=np.asarray(z['observables']); pred=np.asarray(z['predictions'])
    if cal.shape!=(2000,40) or det.shape!=(2500,40) or obs.shape!=(2500,) or pred.shape!=(3,2500): raise ValueError(f'shape invalid {f.name}')
    if any(not np.isin(a,(0,1)).all() for a in (cal,det,obs,pred)): raise ValueError(f'nonbinary values {f.name}')
    if float(np.asarray(z['probability']).item())!=p or int(np.asarray(z['root']).item())!=i: raise ValueError(f'filename metadata mismatch {f.name}')
    if int(np.asarray(z['seed_calibration']).item())!=seed[(STREAMS[0],p,i)] or int(np.asarray(z['seed_evaluation']).item())!=seed[(STREAMS[1],p,i)]: raise ValueError(f'seed mismatch {f.name}')
    ph=independent_estimate(cal,profile)
    if not math.isclose(ph,float(np.asarray(z['p_hat']).item()),rel_tol=0,abs_tol=1e-12): raise ValueError(f'estimator mismatch {f.name}')
    adaptive=independent_matcher(ph)
    regenerated=np.stack([decode(fixed,det),decode(adaptive,det),decode(oracles[p],det)])
    if not np.array_equal(regenerated,pred): raise ValueError(f're-decode mismatch {f.name}')
    err=np.count_nonzero(regenerated^obs[None,:],axis=1).astype(int).tolist()
    co=int(np.count_nonzero((regenerated[1]!=obs)&(regenerated[0]==obs)))
    fo=int(np.count_nonzero((regenerated[1]==obs)&(regenerated[0]!=obs)))
    disagreement=int(np.count_nonzero(regenerated[1]!=regenerated[0]))
    effect=(err[1]-err[0])/2500; groups[p].append(effect)
    roots.append({'probability':p,'root':i,'shots':2500,'p_hat':ph,'fixed_errors':err[0],
      'profile_errors':err[1],'oracle_errors':err[2],'candidate_only':co,'fixed_only':fo,
      'prediction_disagreements':disagreement,'profile_minus_fixed':effect})
    for key,value in zip(('fixed_errors','profile_errors','oracle_errors'),err): condition[p][key]+=value
    condition[p]['candidate_only']+=co; condition[p]['fixed_only']+=fo; condition[p]['prediction_disagreements']+=disagreement
    total_cal+=2000; total_eval+=2500
 stats=independent_stats(groups,cfg)
 condition_summary={str(p):{**v,'shots':250000,'fixed_ler':v['fixed_errors']/250000,
  'profile_ler':v['profile_errors']/250000,'oracle_ler':v['oracle_errors']/250000,
  'paired_difference':(v['profile_errors']-v['fixed_errors'])/250000} for p,v in condition.items()}
 manifest=root_dir.parent/'ROOT_ARCHIVE_MANIFEST.json'
 if manifest.exists():
  m=json.loads(manifest.read_text(encoding='utf-8'))
  if m.get('root_count')!=500 or m.get('sha256')!=hashes: raise ValueError('root hash manifest mismatch')
 summary=root_dir/'RUNNER_SUMMARY.json'; summary_checked=False
 if summary.exists():
  s=json.loads(summary.read_text(encoding='utf-8'))
  if (s.get('roots'),s.get('calibration_shots'),s.get('evaluation_shots'),s.get('unique_shots'))!=(500,1000000,1250000,2250000): raise ValueError('runner summary totals mismatch')
  for k in ('primary_delta','primary_signflip_p','zero_burst_one_sided_bootstrap_95_upper'):
   if not math.isclose(float(s['statistics'][k]),float(stats[k]),rel_tol=0,abs_tol=1e-12): raise ValueError(f'runner aggregate mismatch {k}')
  for k in ('primary_bootstrap_95ci','secondary_signflip_p_raw','secondary_signflip_p_holm'):
   if not np.allclose(s['statistics'][k],stats[k],rtol=0,atol=1e-12): raise ValueError(f'runner aggregate mismatch {k}')
  if s.get('condition_summary')!=condition_summary: raise ValueError('runner per-condition aggregate mismatch')
  claimed_rows=s.get('per_root',[])
  if len(claimed_rows)!=500: raise ValueError('runner per-root summary coverage mismatch')
  by_key={(float(x['probability']),int(x['root'])):x for x in claimed_rows}
  for row in roots:
   other=by_key.get((row['probability'],row['root']))
   if other is None or any(other.get(k)!=row[k] for k in ('shots','fixed_errors','profile_errors','oracle_errors','candidate_only','fixed_only','prediction_disagreements')):
    raise ValueError(f'runner per-root evidence mismatch at p={row["probability"]}, root={row["root"]}')
  summary_checked=True
 status_path=root_dir.parent/'status.json'
 status=json.loads(status_path.read_text(encoding='utf-8'))
 if status.get('status')!='completed' or status.get('completed_roots')!=500 or status.get('unique_shots_generated')!=2250000:
  raise ValueError('persisted controller status is not a complete 2.25M-shot run')
 if not manifest.exists() or not summary_checked: raise ValueError('required root hash manifest or runner summary missing')
 result={'audit':'PASS','roots_verified':len(roots),'calibration_shots':total_cal,'evaluation_shots':total_eval,
  'unique_shots':total_cal+total_eval,'independent_test_access':0,'per_root':roots,
  'per_condition':condition_summary,'statistics':stats,
  'archive_sha256':hashes,'runner_summary_independently_recomputed':summary_checked}
 if output: Path(output).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 return result

def main():
 p=argparse.ArgumentParser(); p.add_argument('root_dir',type=Path); p.add_argument('--output',type=Path); a=p.parse_args()
 print(json.dumps(audit(a.root_dir,a.output),indent=2))
if __name__=='__main__': main()
