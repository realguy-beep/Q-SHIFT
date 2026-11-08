"""Prospective Stage 5 sampler/decoder runner; inert without two explicit flags."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, time, traceback
from pathlib import Path
from collections import OrderedDict
import numpy as np
import psutil

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit
from outputs.stage4_noise_adaptive_feasibility_v1.prototype import DetectorProfileEstimator, decode_prediction, logical_error_mask, build_decoder
sys.path.insert(0,str(Path(__file__).resolve().parent))
from stage5_statistics_repaired import analyze, calibrated_secondary_reference

CONFIG=HERE/'STAGE5_REPAIR_CONFIG.json'; INVENTORY=HERE/'STAGE5_SAMPLE_SEED_INVENTORY.json'; PROFILE=HERE/'FROZEN_PROFILE_ESTIMATOR.json'
FREEZE=HERE/'STAGE5_PRETEST_FREEZE.json'; RUN=HERE/'run'; PROBS=(0.,.004,.008,.012,.016)
ROOTS=1210; CAL_SHOTS=2000; EVAL_SHOTS=2500; TOTAL_ROOTS=6050; TOTAL_SHOTS=27225000

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''): h.update(block)
    return h.hexdigest()

def atomic_json(path,obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf-8'); os.replace(tmp,path)

def atomic_npz(path,**arrays):
    path=Path(path); tmp=path.with_suffix(path.suffix+'.tmp')
    with open(tmp,'wb') as f: np.savez_compressed(f,**arrays)
    os.replace(tmp,path)

def scalar(z,key):
    x=np.asarray(z[key])
    if x.shape!=(): raise ValueError(f'{key} must be scalar')
    return x.item()

def load_profile():
    x=json.loads(PROFILE.read_text(encoding='utf-8'))
    return DetectorProfileEstimator(np.asarray(x['probabilities'],float),np.asarray(x['means'],float),
                                    np.asarray(x['scales'],float),float(x.get('grid_step',.00001)))

def verify_freeze():
    if not FREEZE.is_file(): raise RuntimeError('Stage 5 pre-test freeze is missing')
    record=json.loads(FREEZE.read_text(encoding='utf-8'))
    if record.get('status')!='READY_NOT_AUTHORIZED_TO_SAMPLE' or record.get('stage5_evaluation_shots_generated')!=0 or record.get('sealed_historical_test_accessed') is not False:
        raise RuntimeError('pretest freeze does not preserve no-sampling/no-sealed-data boundary')
    for rel,digest in record['sha256'].items():
        f=ROOT/rel
        if not f.is_file() or sha(f)!=digest: raise RuntimeError(f'frozen hash mismatch: {rel}')
    return record

def verify_candidate_screen():
    inv=json.loads(INVENTORY.read_text(encoding='utf-8'))
    if inv.get('stage5_evaluation_shots_generated')!=0 or inv.get('sealed_historical_test_accessed') is not False:
        raise RuntimeError('sample inventory violates no-sampling/no-sealed-data assertion')
    screened=inv.get('distinct_recoverable_historical_integer_values_screened')
    if not isinstance(screened,int) or screened<=0 or len(inv.get('historical_sources_checked',[]))==0:
        raise RuntimeError('sample inventory is missing recoverable-history coverage metadata')
    for row in inv['historical_sources_checked']:
        if sha(ROOT/row['path'])!=row['sha256']: raise RuntimeError(f'historical seed-source metadata changed: {row["path"]}')
    return f"candidate inventory screened {screened} recoverable historical integer values across {len(inv['historical_sources_checked'])} metadata files"

def seed_map():
    inv=json.loads(INVENTORY.read_text(encoding='utf-8')); out={}
    for x in inv['streams']:
        k=(x['kind'],float(x['probability']),int(x['root']))
        if k in out: raise ValueError(f'duplicate stream {k}')
        out[k]=int(x['seed'])
    expected={(kind,p,r) for kind in ('calibration_detector_only','paired_evaluation_detector_observable')
              for p in PROBS for r in range(ROOTS)}
    all_seeds=list(out.values())
    if set(out)!=expected or len(all_seeds)!=12100 or len(set(all_seeds))!=12100 or inv.get('collision_count')!=0:
        raise ValueError('frozen n=1210 seed inventory incomplete or colliding')
    expected_seed=14_000_000_001
    for kind in ('calibration_detector_only','paired_evaluation_detector_observable'):
        for p in PROBS:
            for r in range(ROOTS):
                if out[(kind,p,r)]!=expected_seed:
                    raise ValueError(f'seed inventory violates frozen contiguous allocation at {(kind,p,r)}')
                expected_seed+=1
    cfg=json.loads(CONFIG.read_text(encoding='utf-8'))
    if cfg.get('roots_per_condition')!=ROOTS or cfg.get('probabilities')!=list(PROBS):
        raise ValueError('candidate config disagrees with frozen Stage 5 allocation')
    allocation=cfg.get('allocation',{})
    if allocation.get('roots')!=TOTAL_ROOTS or allocation.get('calibration_shots')!=TOTAL_ROOTS*CAL_SHOTS or allocation.get('evaluation_shots')!=TOTAL_ROOTS*EVAL_SHOTS or allocation.get('unique_shots')!=TOTAL_SHOTS:
        raise ValueError('candidate configuration shot arithmetic is inconsistent')
    return out,inv

def filename(p,r): return f'root_p{p:.3f}_r{r:03d}.npz'

def validate_complete(path,p,r,sc,se,profile,fixed,oracle):
    with np.load(path,allow_pickle=False) as z:
        required={'phase','calibration_detectors','evaluation_detectors','observables','predictions','p_hat','seed_calibration','seed_evaluation','probability','root'}
        if set(z.files)!=required or scalar(z,'phase')!='complete': raise ValueError(f'checkpoint schema/phase invalid: {path}')
        cal=np.asarray(z['calibration_detectors']); det=np.asarray(z['evaluation_detectors']); obs=np.asarray(z['observables']); pred=np.asarray(z['predictions'])
        if cal.shape!=(CAL_SHOTS,40) or det.shape!=(EVAL_SHOTS,40) or obs.shape!=(EVAL_SHOTS,) or pred.shape!=(3,EVAL_SHOTS): raise ValueError(f'checkpoint shape invalid: {path}')
        if any(not np.isin(a,(0,1)).all() for a in (cal,det,obs,pred)): raise ValueError(f'nonbinary checkpoint: {path}')
        if scalar(z,'seed_calibration')!=sc or scalar(z,'seed_evaluation')!=se or float(scalar(z,'probability'))!=p or int(scalar(z,'root'))!=r: raise ValueError(f'checkpoint metadata mismatch: {path}')
        p_hat=float(scalar(z,'p_hat'))
        if abs(profile.estimate(cal)-p_hat)>1e-12: raise ValueError(f'checkpoint estimate mismatch: {path}')
        expected=np.stack([decode_prediction(fixed,det),decode_prediction(build_decoder(p_hat)[2],det),decode_prediction(oracle,det)])
        if not np.array_equal(expected,pred): raise ValueError(f'checkpoint prediction mismatch: {path}')

def _partial_read(path,sc,se,p,r):
    with np.load(path,allow_pickle=False) as z:
        phase=str(scalar(z,'phase'))
        if scalar(z,'probability')!=p or scalar(z,'root')!=r or scalar(z,'seed_calibration')!=sc:
            raise ValueError(f'partial checkpoint identity mismatch: {path}')
        cal=np.asarray(z['calibration_detectors'],dtype=np.uint8)
        if cal.shape!=(CAL_SHOTS,40) or not np.isin(cal,(0,1)).all(): raise ValueError(f'partial calibration invalid: {path}')
        if phase=='calibration_complete': return phase,cal,None,None
        if phase in ('evaluation_complete','complete'):
            if scalar(z,'seed_evaluation')!=se: raise ValueError(f'partial evaluation seed mismatch: {path}')
            det=np.asarray(z['evaluation_detectors'],dtype=np.uint8); obs=np.asarray(z['observables'],dtype=np.uint8)
            if det.shape!=(EVAL_SHOTS,40) or obs.shape!=(EVAL_SHOTS,) or not np.isin(det,(0,1)).all() or not np.isin(obs,(0,1)).all():
                raise ValueError(f'partial evaluation data invalid: {path}')
            return phase,cal,det,obs
        raise ValueError(f'unknown partial checkpoint phase {phase}: {path}')

def verify_inflight_checkpoint(rootdir,inflight):
    """Fail closed if an RNG stream may have been consumed without durable data."""
    if not isinstance(inflight,dict) or inflight.get('kind') not in {'calibration','evaluation'}:
        raise RuntimeError('safe resume blocked: malformed in-flight record')
    f=Path(rootdir)/filename(float(inflight['p']),int(inflight['root']))
    if not f.is_file(): raise RuntimeError('safe resume blocked: in-flight RNG stream has no checkpoint')
    with np.load(f,allow_pickle=False) as z: phase=str(scalar(z,'phase'))
    durable=phase in {'calibration_complete','evaluation_complete','complete'}
    if inflight['kind']=='evaluation' and phase=='calibration_complete': durable=False
    if not durable: raise RuntimeError('safe resume blocked: in-flight RNG stream has no durable checkpoint')
    return phase

def get_adaptive(bank,p_hat):
    if p_hat not in bank: bank[p_hat]=build_decoder(p_hat)[2]
    bank.move_to_end(p_hat)
    while len(bank)>64: bank.popitem(last=False)
    return bank[p_hat]

def summarize(rootdir,cfg):
    groups={p:[] for p in PROBS}; records=[]; condition={p:{'fixed_errors':0,'profile_errors':0,'oracle_errors':0,'candidate_only':0,'fixed_only':0,'prediction_disagreements':0} for p in PROBS}
    for p in PROBS:
        for r in range(ROOTS):
            path=rootdir/filename(p,r)
            with np.load(path,allow_pickle=False) as z:
                obs=np.asarray(z['observables'],dtype=np.uint8); pred=np.asarray(z['predictions'],dtype=np.uint8)
                errs=[int(np.count_nonzero(logical_error_mask(pred[k],obs))) for k in range(3)]
                diff=(errs[1]-errs[0])/EVAL_SHOTS; groups[p].append(diff)
                co=int(np.count_nonzero((pred[1]!=obs)&(pred[0]==obs))); fo=int(np.count_nonzero((pred[1]==obs)&(pred[0]!=obs)))
                dis=int(np.count_nonzero(pred[1]!=pred[0]))
                records.append({'probability':p,'root':r,'shots':EVAL_SHOTS,'p_hat':float(scalar(z,'p_hat')),
                    'fixed_errors':errs[0],'profile_errors':errs[1],'oracle_errors':errs[2],
                    'candidate_only':co,'fixed_only':fo,'prediction_disagreements':dis,
                    'profile_minus_fixed':diff})
                for key,value in zip(('fixed_errors','profile_errors','oracle_errors'),errs): condition[p][key]+=value
                condition[p]['candidate_only']+=co; condition[p]['fixed_only']+=fo; condition[p]['prediction_disagreements']+=dis
    stats=analyze(groups,cfg,ROOTS)
    per_condition_shots=ROOTS*EVAL_SHOTS
    condition_summary={str(p):{**values,'shots':per_condition_shots,'fixed_ler':values['fixed_errors']/per_condition_shots,
      'profile_ler':values['profile_errors']/per_condition_shots,'oracle_ler':values['oracle_errors']/per_condition_shots,
      'paired_difference':(values['profile_errors']-values['fixed_errors'])/per_condition_shots} for p,values in condition.items()}
    atomic_json(rootdir/'RUNNER_SUMMARY.json',{'roots':TOTAL_ROOTS,'evaluation_shots':TOTAL_ROOTS*EVAL_SHOTS,'calibration_shots':TOTAL_ROOTS*CAL_SHOTS,
                'unique_shots':TOTAL_SHOTS,'statistics':stats,'condition_summary':condition_summary,'per_root':records})
    return stats

def no_shot_preflight():
    """Build each frozen circuit/DEM/Matching graph. Never compiles or calls a sampler."""
    verify_freeze(); screen=verify_candidate_screen(); seeds,inv=seed_map(); profile=load_profile()
    cfg=json.loads(CONFIG.read_text(encoding='utf-8'))
    disk=shutil.disk_usage(ROOT); rss=psutil.Process().memory_info().rss
    resources={'current_process_rss_bytes':rss,'system_available_ram_bytes':psutil.virtual_memory().available,
      'free_disk_bytes':disk.free,'configured_rss_limit_bytes':cfg['resources']['rss_bytes_max'],
      'configured_free_disk_reserve_bytes':cfg['resources']['free_disk_min_bytes'],
      'configured_wall_limit_seconds':cfg['resources']['wall_seconds_max']}
    if rss>=cfg['resources']['rss_bytes_max'] or disk.free<cfg['resources']['free_disk_min_bytes']:
        raise RuntimeError('no-sampling resource preflight failed')
    graph=[]
    for p in PROBS:
        circuit=build_spatial_burst_circuit(memory_basis='z',regime='balanced',distance=3,rounds=5,
            gate_p=.003,measurement_p=.003,bias_ratio=10.,burst_probability=p,burst_pair=(8,10))
        if (circuit.num_detectors,circuit.num_observables)!=(40,1): raise RuntimeError('circuit dimension mismatch')
        dec=build_decoder(p)[2]
        if dec.num_detectors!=40: raise RuntimeError('matching detector count mismatch')
        graph.append({'p':p,'detectors':circuit.num_detectors,'observables':circuit.num_observables,
                      'matching_nodes':dec.num_detectors,'matching_edges':dec.num_edges})
    if len(seeds)!=12100 or not profile: raise RuntimeError('n=1210 preflight inventory/profile check failed')
    refs,epsilon,cutoffs,fingerprints=calibrated_secondary_reference()
    if len(refs)!=6 or len(fingerprints)!=6 or epsilon<=0 or not all(np.isfinite(cutoffs[k]) for k in ('0.0125','0.05')):
        raise RuntimeError('finite-envelope reference calibration preflight failed')
    return {'status':'PASS_NO_SAMPLING','stage5_shots':0,'sealed_historical_test_access':0,
            'roots':TOTAL_ROOTS,'unique_shots_if_later_authorized':TOTAL_SHOTS,'graphs':graph,
            'seed_screen':screen,'resources':resources,
            'secondary_reference':{'families':len(refs),'dkw_epsilon':epsilon,'cutoffs':cutoffs,'fingerprints':fingerprints}}

def execute():
    verify_freeze(); verify_candidate_screen(); seeds,inv=seed_map(); profile=load_profile(); cfg=json.loads(CONFIG.read_text(encoding='utf-8'))
    rootdir=RUN/'roots'; rootdir.mkdir(parents=True,exist_ok=True); RUN.mkdir(parents=True,exist_ok=True)
    statusfile=RUN/'status.json'; old=json.loads(statusfile.read_text(encoding='utf-8')) if statusfile.exists() else {}
    inflight=old.get('in_flight')
    if inflight:
        verify_inflight_checkpoint(rootdir,inflight)
    done=cal_done=eval_done=0
    for p in PROBS:
        for r in range(ROOTS):
            f=rootdir/filename(p,r)
            if f.exists():
                with np.load(f,allow_pickle=False) as z:
                    phase=str(scalar(z,'phase')); cal_done+=CAL_SHOTS
                    if phase in ('evaluation_complete','complete'): eval_done+=EVAL_SHOTS
                    if phase=='complete': done+=1
    prior_runtime=float(old.get('cumulative_runtime_seconds',0)); started=time.monotonic()
    status={'status':'running','total_roots':TOTAL_ROOTS,'completed_roots':done,'calibration_shots_generated':cal_done,
      'evaluation_shots_generated':eval_done,'unique_shots_generated':cal_done+eval_done,'independent_test_access':0,
      'cumulative_runtime_seconds':prior_runtime,'in_flight':None,'start_unix':time.time()}
    atomic_json(statusfile,status)
    fixed=build_decoder(0.)[2]; oracles={p:build_decoder(p)[2] for p in PROBS}; bank=OrderedDict()
    for p in PROBS:
        circuit=build_spatial_burst_circuit(memory_basis='z',regime='balanced',distance=3,rounds=5,
            gate_p=.003,measurement_p=.003,bias_ratio=10.,burst_probability=p,burst_pair=(8,10))
        if (circuit.num_detectors,circuit.num_observables)!=(40,1): raise RuntimeError('circuit dimension mismatch')
        for r in range(ROOTS):
            sc=seeds[('calibration_detector_only',p,r)]; se=seeds[('paired_evaluation_detector_observable',p,r)]
            f=rootdir/filename(p,r); phase=None; cal=det=obs=None
            if f.exists():
                phase,cal,det,obs=_partial_read(f,sc,se,p,r)
            if phase=='complete':
                validate_complete(f,p,r,sc,se,profile,fixed,oracles[p]); continue
            elapsed=prior_runtime+time.monotonic()-started
            if elapsed>=cfg['resources']['wall_seconds_max'] or psutil.Process().memory_info().rss>=cfg['resources']['rss_bytes_max']:
                status.update({'status':'paused_resource_limit','cumulative_runtime_seconds':elapsed,'updated_unix':time.time()})
                atomic_json(statusfile,status); return
            if phase is None:
                if psutil.Process().memory_info().rss>=cfg['resources']['rss_bytes_max'] or shutil.disk_usage(RUN).free<512*1024*1024: raise RuntimeError('resource preflight limit reached')
                status['cumulative_runtime_seconds']=elapsed
                status['in_flight']={'kind':'calibration','p':p,'root':r,'seed':sc}; atomic_json(statusfile,status)
                cal=circuit.compile_detector_sampler(seed=sc).sample(CAL_SHOTS).astype(np.uint8,copy=False)
                if cal.shape!=(CAL_SHOTS,40) or not np.isin(cal,(0,1)).all(): raise RuntimeError('invalid calibration detector batch')
                atomic_npz(f,phase=np.asarray('calibration_complete'),calibration_detectors=cal,
                    probability=np.asarray(p),root=np.asarray(r),seed_calibration=np.asarray(sc))
                status['calibration_shots_generated']+=CAL_SHOTS; status['unique_shots_generated']+=CAL_SHOTS
                status['cumulative_runtime_seconds']=prior_runtime+time.monotonic()-started
                status['in_flight']=None; atomic_json(statusfile,status); phase='calibration_complete'
            if phase=='calibration_complete':
                p_hat=profile.estimate(cal)
                get_adaptive(bank,p_hat)
                elapsed=prior_runtime+time.monotonic()-started
                status['cumulative_runtime_seconds']=elapsed
                if elapsed>=cfg['resources']['wall_seconds_max'] or psutil.Process().memory_info().rss>=cfg['resources']['rss_bytes_max']:
                    status.update({'status':'paused_resource_limit','updated_unix':time.time()}); atomic_json(statusfile,status); return
                status['in_flight']={'kind':'evaluation','p':p,'root':r,'seed':se}; atomic_json(statusfile,status)
                det,obs=circuit.compile_detector_sampler(seed=se).sample(EVAL_SHOTS,separate_observables=True)
                det=np.asarray(det,dtype=np.uint8); obs=np.asarray(obs,dtype=np.uint8).reshape(-1)
                if det.shape!=(EVAL_SHOTS,40) or obs.shape!=(EVAL_SHOTS,) or not np.isin(det,(0,1)).all() or not np.isin(obs,(0,1)).all(): raise RuntimeError('invalid paired evaluation arrays')
                atomic_npz(f,phase=np.asarray('evaluation_complete'),calibration_detectors=cal,evaluation_detectors=det,
                    observables=obs,probability=np.asarray(p),root=np.asarray(r),seed_calibration=np.asarray(sc),seed_evaluation=np.asarray(se))
                status['evaluation_shots_generated']+=EVAL_SHOTS; status['unique_shots_generated']+=EVAL_SHOTS
                status['cumulative_runtime_seconds']=prior_runtime+time.monotonic()-started
                status['in_flight']=None; atomic_json(statusfile,status); phase='evaluation_complete'
            if phase=='evaluation_complete':
                p_hat=profile.estimate(cal)
                predictions=np.stack([decode_prediction(fixed,det),decode_prediction(get_adaptive(bank,p_hat),det),decode_prediction(oracles[p],det)])
                atomic_npz(f,phase=np.asarray('complete'),calibration_detectors=cal,evaluation_detectors=det,observables=obs,
                    predictions=predictions,p_hat=np.asarray(p_hat),probability=np.asarray(p),root=np.asarray(r),
                    seed_calibration=np.asarray(sc),seed_evaluation=np.asarray(se))
                validate_complete(f,p,r,sc,se,profile,fixed,oracles[p]); status['completed_roots']+=1
            status['unique_shots_generated']=status['calibration_shots_generated']+status['evaluation_shots_generated']
            if status['unique_shots_generated']>cfg['resources']['max_unique_shots']: raise RuntimeError('shot cap exceeded')
            elapsed=prior_runtime+time.monotonic()-started
            status['cumulative_runtime_seconds']=elapsed
            status['updated_unix']=time.time(); atomic_json(statusfile,status)
            if elapsed>=cfg['resources']['wall_seconds_max'] or psutil.Process().memory_info().rss>=cfg['resources']['rss_bytes_max']:
                status['status']='paused_resource_limit'; atomic_json(statusfile,status); return
    summarize(rootdir,cfg)
    files={x.name:sha(x) for x in sorted(rootdir.glob('root_p*.npz'))}
    if len(files)!=TOTAL_ROOTS: raise RuntimeError(f'completion requires {TOTAL_ROOTS} verified root archives')
    atomic_json(RUN/'ROOT_ARCHIVE_MANIFEST.json',{'root_count':TOTAL_ROOTS,'sha256':files})
    status.update({'status':'completed','completed_roots':TOTAL_ROOTS,'calibration_shots_generated':TOTAL_ROOTS*CAL_SHOTS,
      'evaluation_shots_generated':TOTAL_ROOTS*EVAL_SHOTS,'unique_shots_generated':TOTAL_SHOTS,'cumulative_runtime_seconds':prior_runtime+time.monotonic()-started,
      'completed_unix':time.time(),'in_flight':None})
    atomic_json(statusfile,status)

def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument('--preflight',action='store_true')
    parser.add_argument('--run',action='store_true'); parser.add_argument('--authorize-stage5-sampling',action='store_true')
    args=parser.parse_args(argv)
    if args.preflight:
        print(json.dumps(no_shot_preflight(),indent=2)); return 0
    if not(args.run and args.authorize_stage5_sampling):
        print('No sampling started. Both --run and --authorize-stage5-sampling are required.'); return 2
    try:
        execute()
    except Exception as exc:
        # Preserve the failing boundary and any in-flight seed so a later
        # operator can inspect it; never silently mark a partial run complete.
        statusfile=RUN/'status.json'
        if statusfile.exists():
            try:
                status=json.loads(statusfile.read_text(encoding='utf-8'))
            except Exception:
                status={}
            status.update({'status':'failed','failure_type':type(exc).__name__,
                           'failure_message':str(exc),'failure_traceback':traceback.format_exc(),
                           'failed_unix':time.time()})
            atomic_json(statusfile,status)
        raise
    return 0

if __name__=='__main__': raise SystemExit(main())
