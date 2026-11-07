"""Read-only v3 candidate audit; independent of runner/statistics modules."""
from __future__ import annotations
import argparse,hashlib,json,math,sys
from pathlib import Path
import numpy as np
import pymatching
from scipy.stats import t as student_t

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit
PROBS=(0.,.004,.008,.012,.016); STREAMS=('calibration_detector_only','paired_evaluation_detector_observable')
ROOTS=666; TOTAL_ROOTS=3330; TOTAL_SHOTS=14985000

def digest(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(1<<20),b''): h.update(block)
 return h.hexdigest()

def load_frozen():
 cfg=json.loads((HERE/'STAGE5_V3_CANDIDATE_CONFIG.json').read_text(encoding='utf-8'))
 inv=json.loads((HERE/'STAGE5_V3_SEED_INVENTORY.json').read_text(encoding='utf-8'))
 freeze=json.loads((HERE/'STAGE5_V3_CANDIDATE_FREEZE.json').read_text(encoding='utf-8'))
 for rel,h in freeze['sha256'].items():
  if digest(ROOT/rel)!=h: raise ValueError(f'frozen candidate hash mismatch: {rel}')
 return cfg,inv,freeze

def features(det):
 d=np.asarray(det)
 if d.ndim!=2 or d.shape[1]!=40 or not np.isin(d,(0,1)).all(): raise ValueError('invalid detector matrix')
 pairs=((8,10),(16,18),(24,26),(32,34),(36,38))
 return np.column_stack([d,np.column_stack([d[:,a]&d[:,b] for a,b in pairs])]).astype(float)

def estimate_profile(det,profile):
 obs=features(det).mean(axis=0); knots=np.asarray(profile['probabilities'],float)
 means=np.asarray(profile['means'],float); scales=np.asarray(profile['scales'],float); step=float(profile.get('grid_step',1e-5))
 if means.shape!=(len(knots),45) or scales.shape!=(45,) or np.any(scales<=0): raise ValueError('invalid detector-profile metadata')
 grid=np.linspace(knots[0],knots[-1],max(2,round((knots[-1]-knots[0])/step)+1))
 interpolated=np.stack([np.interp(grid,knots,means[:,j]) for j in range(45)],axis=1)
 score=np.square((interpolated-obs)/scales).mean(axis=1)
 return float(grid[int(np.argmin(score))])

def matcher(p):
 circuit=build_spatial_burst_circuit(memory_basis='z',regime='balanced',distance=3,rounds=5,
  gate_p=.003,measurement_p=.003,bias_ratio=10.,burst_probability=float(p),burst_pair=(8,10))
 if (circuit.num_detectors,circuit.num_observables)!=(40,1): raise ValueError('circuit detector/observable mismatch')
 dem=circuit.detector_error_model(decompose_errors=True,approximate_disjoint_errors=True)
 if (dem.num_detectors,dem.num_observables)!=(40,1): raise ValueError('DEM detector/observable mismatch')
 return pymatching.Matching.from_detector_error_model(dem,enable_correlations=True)

def decode(m,det):
 pred=np.asarray(m.decode_batch(np.asarray(det,dtype=np.uint8)),dtype=np.uint8).reshape(-1)
 if pred.shape!=(len(det),) or not np.isin(pred,(0,1)).all(): raise ValueError('invalid decoder predictions')
 return pred

def holm(p):
 p=np.asarray(p,float); order=np.argsort(p,kind='stable'); out=np.empty_like(p); running=0.
 for rank,i in enumerate(order): running=max(running,(len(p)-rank)*p[i]); out[i]=min(1.,running)
 return out.tolist()

def independent_statistics(groups,cfg,n):
 # Loop/formula implementation intentionally does not import the runner's statistics code.
 means={}; variances={}; secondary_raw=[]; condition={}
 for p in (.004,.008,.012,.016):
  values=np.asarray(groups[p],dtype=float)
  if values.shape!=(n,) or not np.isfinite(values).all(): raise ValueError('invalid root-difference vector')
  means[p]=float(sum(values)/n)
  variances[p]=float(sum((float(v)-means[p])**2 for v in values)/(n-1))
  se=math.sqrt(variances[p]/n); t0=means[p]/se if se else (float('-inf') if means[p]<0 else float('inf') if means[p]>0 else 0.)
  pv=float(student_t.cdf(t0,n-1)) if se else (0. if means[p]<0 else 1.)
  secondary_raw.append(pv)
  condition[str(p)]={'root_count':n,'mean_difference':means[p],'sample_sd':math.sqrt(variances[p]),
    'standard_error':se,'welch_t_reference_p_one_sided_vs_zero':pv,
    'status':'descriptive secondary; not validated by primary envelope simulations'}
 delta=sum(means.values())/4
 se=math.sqrt(sum(variances[p]/n for p in means)/16)
 denom=sum((variances[p]/(16*n))**2/(n-1) for p in means)
 df=(se**4/denom) if denom else float('inf')
 ci=cfg['primary_inference']; boundary=float(ci['null_boundary'])
 tstat=(delta-boundary)/se if se else (float('-inf') if delta<boundary else float('inf') if delta>boundary else 0.)
 upper=delta+float(ci['studentized_cutoff'])*se
 central=[delta-float(ci['central_lower_cutoff'])*se,delta+float(ci['central_upper_cutoff'])*se]
 p0=np.asarray(groups[0.],dtype=float)
 if p0.shape!=(n,) or not np.isfinite(p0).all(): raise ValueError('invalid p=0 roots')
 p0mean=float(sum(p0)/n); p0var=float(sum((float(v)-p0mean)**2 for v in p0)/(n-1)); p0se=math.sqrt(p0var/n)
 p0upper=p0mean+float(ci['p0_one_sided_cutoff'])*p0se
 raw=secondary_raw; adjusted=holm(raw)
 return {'estimand':'equal-weight mean of four nonzero-condition root-paired adaptive-minus-fixed LER differences',
  'primary_delta':delta,'primary_standard_error':se,'primary_df_reference':df,'primary_t_statistic_at_boundary':tstat,
  'primary_boundary':boundary,'primary_calibrated_critical':float(ci['studentized_cutoff']),
  'primary_one_sided_upper_bound':upper,'primary_central_interval_candidate':central,
  'primary_calibrated_reject':bool(upper<boundary),'p0_mean_difference':p0mean,'p0_standard_error':p0se,
  'p0_upper_bound':p0upper,'p0_no_harm_boundary':float(ci['p0_no_harm_boundary']),
  'p0_no_harm_pass':bool(p0upper<=float(ci['p0_no_harm_boundary'])),
  'nonzero_condition_means':{str(p):means[p] for p in means},
  'secondary_welch_p_raw_vs_zero_descriptive':raw,'secondary_welch_p_holm_descriptive':adjusted,
  'secondary_condition_details':condition,
  'overall_candidate_gate':bool(upper<boundary and p0upper<=float(ci['p0_no_harm_boundary']) and all(v<0 for v in means.values()) and max(means.values())<=.0002),
  'inference_scope':'primary calibrated cutoffs are limited to the simulated distribution envelope; secondary Welch p-values are descriptive until separately validated',
  'resampling_unit':'independent root; paired shot errors reduced to a root-level difference'}

def audit(root_dir,output=None):
 cfg,inv,freeze=load_frozen(); root_dir=Path(root_dir); n=int(cfg['roots_per_condition'])
 if inv.get('collision_count')!=0 or inv.get('seed_stream_count')!=2*len(PROBS)*n: raise ValueError('seed inventory invalid')
 seeds={}
 for r in inv['streams']:
  key=(r['kind'],float(r['probability']),int(r['root']))
  if key in seeds: raise ValueError(f'duplicate stream {key}')
  seeds[key]=int(r['seed'])
 expected={(kind,p,i) for kind in STREAMS for p in PROBS for i in range(n)}
 all_seeds=list(seeds.values())
 if set(seeds)!=expected or len(all_seeds)!=len(set(all_seeds)): raise ValueError('candidate seed coverage/collision error')
 profile=json.loads((HERE/'FROZEN_PROFILE_ESTIMATOR.json').read_text(encoding='utf-8'))
 fixed=matcher(0.); oracle={p:matcher(p) for p in PROBS}
 groups={p:[] for p in PROBS}; per_condition={p:{'fixed_errors':0,'profile_errors':0,'oracle_errors':0,'candidate_only':0,'fixed_only':0,'prediction_disagreements':0} for p in PROBS}
 roots=[]; hashes={}; cal_total=eval_total=0
 for p in PROBS:
  for i in range(n):
   name=f'root_p{p:.3f}_r{i:03d}.npz'; path=root_dir/name
   if not path.is_file(): raise FileNotFoundError(f'missing root archive {name}')
   hashes[name]=digest(path)
   with np.load(path,allow_pickle=False) as z:
    required={'phase','calibration_detectors','evaluation_detectors','observables','predictions','p_hat','seed_calibration','seed_evaluation','probability','root'}
    if set(z.files)!=required or str(np.asarray(z['phase']).item())!='complete': raise ValueError(f'invalid schema/phase {name}')
    cal=np.asarray(z['calibration_detectors']); det=np.asarray(z['evaluation_detectors']); obs=np.asarray(z['observables']); pred=np.asarray(z['predictions'])
    if cal.shape!=(2000,40) or det.shape!=(2500,40) or obs.shape!=(2500,) or pred.shape!=(3,2500): raise ValueError(f'shape mismatch {name}')
    if any(not np.isin(a,(0,1)).all() for a in (cal,det,obs,pred)): raise ValueError(f'nonbinary data {name}')
    if float(np.asarray(z['probability']).item())!=p or int(np.asarray(z['root']).item())!=i: raise ValueError(f'file/root identity mismatch {name}')
    if int(np.asarray(z['seed_calibration']).item())!=seeds[(STREAMS[0],p,i)] or int(np.asarray(z['seed_evaluation']).item())!=seeds[(STREAMS[1],p,i)]: raise ValueError(f'seed mismatch {name}')
    p_hat=estimate_profile(cal,profile)
    if not math.isclose(p_hat,float(np.asarray(z['p_hat']).item()),rel_tol=0,abs_tol=1e-12): raise ValueError(f'calibration estimate mismatch {name}')
    rebuilt=np.stack([decode(fixed,det),decode(matcher(p_hat),det),decode(oracle[p],det)])
    if not np.array_equal(rebuilt,pred): raise ValueError(f'independent decoder predictions differ {name}')
    errors=np.count_nonzero(rebuilt^obs[None,:],axis=1).astype(int).tolist()
    co=int(np.count_nonzero((rebuilt[1]!=obs)&(rebuilt[0]==obs)))
    fo=int(np.count_nonzero((rebuilt[1]==obs)&(rebuilt[0]!=obs)))
    disagree=int(np.count_nonzero(rebuilt[1]!=rebuilt[0])); effect=(errors[1]-errors[0])/2500
    groups[p].append(effect)
    row={'probability':p,'root':i,'shots':2500,'p_hat':p_hat,'fixed_errors':errors[0],
      'profile_errors':errors[1],'oracle_errors':errors[2],'candidate_only':co,'fixed_only':fo,
      'prediction_disagreements':disagree,'profile_minus_fixed':effect}
    roots.append(row)
    for k,v in zip(('fixed_errors','profile_errors','oracle_errors'),errors): per_condition[p][k]+=v
    per_condition[p]['candidate_only']+=co; per_condition[p]['fixed_only']+=fo; per_condition[p]['prediction_disagreements']+=disagree
    cal_total+=2000; eval_total+=2500
 stats=independent_statistics(groups,cfg,n)
 shots_per_cond=n*2500
 conditions={str(p):{**v,'shots':shots_per_cond,'fixed_ler':v['fixed_errors']/shots_per_cond,
   'profile_ler':v['profile_errors']/shots_per_cond,'oracle_ler':v['oracle_errors']/shots_per_cond,
   'paired_difference':(v['profile_errors']-v['fixed_errors'])/shots_per_cond} for p,v in per_condition.items()}
 manifest=root_dir.parent/'ROOT_ARCHIVE_MANIFEST.json'
 if not manifest.is_file(): raise ValueError('root archive manifest missing')
 m=json.loads(manifest.read_text(encoding='utf-8'))
 if m.get('root_count')!=TOTAL_ROOTS or m.get('sha256')!=hashes: raise ValueError('root archive hash manifest mismatch')
 summary_path=root_dir/'RUNNER_SUMMARY.json'; summary=json.loads(summary_path.read_text(encoding='utf-8'))
 expected_totals=(TOTAL_ROOTS,TOTAL_ROOTS*2000,TOTAL_ROOTS*2500,TOTAL_SHOTS)
 if (summary.get('roots'),summary.get('calibration_shots'),summary.get('evaluation_shots'),summary.get('unique_shots'))!=expected_totals:
  raise ValueError('runner summary shot/root totals mismatch')
 for key,value in stats.items():
  if isinstance(value,(int,float,bool,str)) and isinstance(summary['statistics'].get(key),type(value)):
   if isinstance(value,float) and not math.isclose(value,float(summary['statistics'][key]),rel_tol=0,abs_tol=1e-12): raise ValueError(f'aggregate mismatch {key}')
   if isinstance(value,(int,bool,str)) and summary['statistics'][key]!=value: raise ValueError(f'aggregate mismatch {key}')
 if summary.get('condition_summary')!=conditions: raise ValueError('condition aggregates differ')
 by_key={(float(r['probability']),int(r['root'])):r for r in summary.get('per_root',[])}
 if len(by_key)!=TOTAL_ROOTS: raise ValueError('runner root summary coverage mismatch')
 for r in roots:
  other=by_key.get((r['probability'],r['root']))
  if other is None or any(other.get(k)!=r[k] for k in ('fixed_errors','profile_errors','oracle_errors','candidate_only','fixed_only','prediction_disagreements')):
   raise ValueError(f'per-root evidence mismatch at p={r["probability"]}, root={r["root"]}')
 status=json.loads((root_dir.parent/'status.json').read_text(encoding='utf-8'))
 if status.get('status')!='completed' or status.get('completed_roots')!=TOTAL_ROOTS or status.get('unique_shots_generated')!=TOTAL_SHOTS:
  raise ValueError('persisted status is not complete')
 result={'audit':'PASS','roots_verified':len(roots),'calibration_shots':cal_total,'evaluation_shots':eval_total,
  'unique_shots':cal_total+eval_total,'stage5_independent_test_access':0,'per_root':roots,
  'per_condition':conditions,'statistics':stats,'archive_sha256':hashes,
  'runner_summary_independently_recomputed':True,'status_verified':True}
 if output:
  output=Path(output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 return result

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('root_dir',type=Path); ap.add_argument('--output',type=Path); a=ap.parse_args()
 print(json.dumps(audit(a.root_dir,a.output),indent=2))
if __name__=='__main__': main()
