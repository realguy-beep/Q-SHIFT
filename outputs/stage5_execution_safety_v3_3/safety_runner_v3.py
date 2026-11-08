"""Stage 5 safety supervisor. Scientific runner remains frozen v2."""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time, uuid
from pathlib import Path
from safety_runtime import RunDirectoryLock, Deadline, atomic_json, verify_committed_npz, UncommittedCheckpointError

ROOT=Path(__file__).resolve().parents[2]
V2=ROOT/'outputs/stage5_secondary_inference_repair_v1/stage5_sampling_runner_v2.py'
WORKER=Path(__file__).with_name('worker_v3.py')
AUDITOR=Path(__file__).with_name('audit_saved_run.py')
FINALIZER=Path(__file__).with_name('finalize_v3.py')
FREEZE=ROOT/'outputs/stage5_secondary_inference_repair_v1/STAGE5_PRETEST_FREEZE_V2.json'
CONFIG=ROOT/'outputs/stage5_secondary_inference_repair_v1/STAGE5_REPAIR_CONFIG.json'
SAFETY_FREEZE=Path(__file__).with_name('SAFETY_FREEZE.json')

def verify_safety_sources():
    import hashlib
    if not SAFETY_FREEZE.is_file(): raise RuntimeError('Stage 5 safety source freeze is missing')
    record=json.loads(SAFETY_FREEZE.read_text(encoding='utf-8'))
    if record.get('state')!='FROZEN_BEFORE_BENCHMARK_SAMPLING' or record.get('stage5_sampling_authorized') is not False:
        raise RuntimeError('safety source freeze is invalid or authorizes sampling')
    for rel,want in record['sha256'].items():
        actual=hashlib.sha256((Path(__file__).parent/rel).read_bytes()).hexdigest()
        if actual!=want: raise RuntimeError(f'Safety implementation/config hash mismatch: {rel}')
    old_digest=hashlib.sha256(FREEZE.read_bytes()).hexdigest()
    if old_digest!=record.get('historical_stage5_freeze_sha256'):
        raise RuntimeError('historical Stage 5 freeze hash differs from safety freeze')
    return record

def verify_frozen_inputs():
    import hashlib
    record=json.loads(FREEZE.read_text(encoding='utf-8'))
    if record.get('status')!='PRETEST_FROZEN_NOT_AUTHORIZED':
        raise RuntimeError('Stage 5 freeze status changed')
    for rel,want in record['sha256'].items():
        h=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
        if h!=want: raise RuntimeError(f'Frozen Stage 5 source/config hash mismatch: {rel}')
    return record

def _checkpoint_for(run_dir, inflight):
    from importlib.util import spec_from_file_location,module_from_spec
    spec=spec_from_file_location('stage5_v2_constants',V2); m=module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m)
    return Path(run_dir)/'roots'/m.filename(float(inflight['p']),int(inflight['root']))

def reconcile_uncommitted(run_dir: Path, *, explicit_recovery: bool):
    run_dir=Path(run_dir); status_path=run_dir/'status.json'
    if not status_path.exists(): return {'state':'clean'}
    status=json.loads(status_path.read_text(encoding='utf-8'))
    # Any archive without an authenticated sidecar is ambiguous and blocks resume.
    roots=run_dir/'roots'
    for archive in roots.glob('root_p*.npz') if roots.exists() else []:
        verify_committed_npz(archive)
    inflight=status.get('in_flight')
    if not inflight: return {'state':'no_inflight'}
    if not explicit_recovery:
        raise UncommittedCheckpointError('in-flight work found; resume requires explicit --recover-uncommitted')
    archive=_checkpoint_for(run_dir,inflight)
    phase=None
    if archive.exists():
        verify_committed_npz(archive)
        import numpy as np
        with np.load(archive,allow_pickle=False) as z: phase=str(np.asarray(z['phase']).item())
    committed=(phase in {'calibration_complete','evaluation_complete','complete'} and
               not (inflight.get('kind')=='evaluation' and phase=='calibration_complete'))
    journal_path=run_dir/'RECOVERY_JOURNAL.json'
    journal=json.loads(journal_path.read_text(encoding='utf-8')) if journal_path.exists() else {'events':[]}
    event={'event_id':uuid.uuid4().hex,'kind':inflight.get('kind'),'probability':inflight.get('p'),
           'root':inflight.get('root'),'checkpoint_phase':phase,
           'outcome':'committed_checkpoint_reconciled' if committed else 'uncommitted_stream_will_replay_same_frozen_seed',
           'timestamp_unix':time.time(),'explicit_recovery':True}
    journal['events'].append(event); atomic_json(journal_path,journal)
    status['in_flight']=None
    status['status']='recovering'
    status['last_recovery_event']=event['event_id']
    atomic_json(status_path,status)
    return {'state':event['outcome'],'phase':phase}

def _mark_status(run_dir, value):
    path=Path(run_dir)/'status.json'
    old={}
    if path.exists():
        try: old=json.loads(path.read_text(encoding='utf-8'))
        except Exception: pass
    old.update(value); atomic_json(path,old)

def _terminate(proc):
    if proc.poll() is not None: return
    proc.terminate()
    try: proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill(); proc.wait(timeout=2)

def supervise_command(command, run_dir:Path, timeout_seconds:float, env=None, *, deadline=None):
    """Run one process under a hard parent deadline; usable for failure tests."""
    run_dir=Path(run_dir); run_dir.mkdir(parents=True,exist_ok=True)
    deadline=deadline or Deadline(timeout_seconds)
    process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    out=[]; err=[]
    while process.poll() is None and deadline.remaining()>0:
        time.sleep(min(.025,deadline.remaining()))
    if process.poll() is None:
        _terminate(process)
        _mark_status(run_dir,{'status':'deadline_exceeded','deadline_phase':_current_phase(run_dir),
                              'in_flight':_read_inflight(run_dir),'deadline_unix':time.time()})
        stdout,stderr=process.communicate(timeout=2)
        return {'status':'deadline_exceeded','returncode':process.returncode,'stdout':stdout,'stderr':stderr}
    stdout,stderr=process.communicate()
    return {'status':'exited','returncode':process.returncode,'stdout':stdout,'stderr':stderr}

def _read_inflight(run_dir):
    try: return json.loads((Path(run_dir)/'status.json').read_text(encoding='utf-8')).get('in_flight')
    except Exception: return None
def _current_phase(run_dir):
    try: return json.loads((Path(run_dir)/'status.json').read_text(encoding='utf-8')).get('phase')
    except Exception: return 'unknown'

def _audit_and_finalize(run_dir, deadline, benchmark_config=None):
    deadline.check('artifact verification start')
    env=os.environ.copy(); env['QSHIFT_STAGE5_RUN_DIR']=str(Path(run_dir).resolve())
    if benchmark_config:
        env['QSHIFT_SAFETY_BENCHMARK']='1'; env['QSHIFT_SAFETY_BENCH_CONFIG']=str(Path(benchmark_config).resolve())
    remaining=deadline.remaining()
    try:
        result=subprocess.run([sys.executable,str(AUDITOR)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=remaining)
    except subprocess.TimeoutExpired:
        _mark_status(run_dir,{'status':'deadline_exceeded','deadline_phase':'independent_artifact_verification',
                              'in_flight':_read_inflight(run_dir),'deadline_unix':time.time()})
        return {'status':'deadline_exceeded','phase':'independent_artifact_verification'}
    try:
        deadline.check('artifact verification completion')
    except TimeoutError:
        _mark_status(run_dir,{'status':'deadline_exceeded','deadline_phase':'independent_artifact_verification',
                              'in_flight':_read_inflight(run_dir),'deadline_unix':time.time()})
        return {'status':'deadline_exceeded','phase':'independent_artifact_verification'}
    if result.returncode: raise RuntimeError(f'independent artifact audit failed: {result.stderr[-2000:]}')
    audit=json.loads(result.stdout)
    if audit.get('status')!='PASS_INDEPENDENT_AUDIT': raise RuntimeError('independent audit did not pass')
    status=json.loads((Path(run_dir)/'status.json').read_text(encoding='utf-8'))
    if int(status.get('unique_shots_generated',-1))!=int(audit.get('unique_shots_recomputed',-2)):
        raise RuntimeError('persisted unique-shot count disagrees with independent checkpoint audit')
    if int(status.get('completed_roots',-1))!=int(audit.get('roots_verified',-2)):
        raise RuntimeError('persisted completed-root count disagrees with independent checkpoint audit')
    remaining=deadline.remaining()
    if remaining<=0:
        _mark_status(run_dir,{'status':'deadline_exceeded','deadline_phase':'finalization_start',
                              'in_flight':None,'deadline_unix':time.time()})
        return {'status':'deadline_exceeded','phase':'finalization_start'}
    try:
        finalized=subprocess.run([sys.executable,str(FINALIZER),str(Path(run_dir).resolve()),str(remaining)],
                                 cwd=ROOT,env=env,capture_output=True,text=True,timeout=remaining)
    except subprocess.TimeoutExpired:
        _mark_status(run_dir,{'status':'deadline_exceeded','deadline_phase':'finalization_artifact_write',
                              'in_flight':None,'deadline_unix':time.time()})
        return {'status':'deadline_exceeded','phase':'finalization_artifact_write'}
    if finalized.returncode==3:
        return {'status':'deadline_exceeded','phase':'finalizer_reserve'}
    if finalized.returncode!=0:
        raise RuntimeError(f'finalizer failed: {finalized.stderr[-2000:]}')
    final_status=json.loads((Path(run_dir)/'status.json').read_text(encoding='utf-8'))
    if final_status.get('status')!='completed': raise RuntimeError('finalizer did not persist completed status')
    return audit

def safe_execute(run_dir:Path, *, timeout_seconds:float, benchmark_config:Path|None=None,
                 recover_uncommitted=False, test_fault=None, kill_on_sample_marker=False):
    started=time.monotonic(); deadline=Deadline(timeout_seconds,started)
    run_dir=Path(run_dir).resolve()
    safety_record=verify_safety_sources()
    record=verify_frozen_inputs()
    cfg=json.loads(CONFIG.read_text(encoding='utf-8'))
    if benchmark_config:
        benchmark_config=Path(benchmark_config).resolve()
        try: benchmark_config.relative_to(Path(__file__).parent.resolve())
        except ValueError as exc: raise ValueError('benchmark config must be inside the versioned safety directory') from exc
    elif test_fault or kill_on_sample_marker:
        raise ValueError('failure injection is restricted to benchmark-only runs')
    if not benchmark_config and timeout_seconds>float(cfg['resources']['wall_seconds_max']):
        raise ValueError('requested timeout exceeds frozen Stage 5 maximum')
    run_dir.mkdir(parents=True,exist_ok=True)
    with RunDirectoryLock(run_dir,kind='launcher') as lock:
        # Detect a worker orphaned by a dead supervisor before starting another.
        worker_probe=RunDirectoryLock(run_dir,kind='worker').acquire()
        worker_probe.release()
        recovery=reconcile_uncommitted(run_dir,explicit_recovery=recover_uncommitted)
        env=os.environ.copy(); env['QSHIFT_STAGE5_RUN_DIR']=str(run_dir)
        marker=run_dir/'.sampling-active'
        if benchmark_config:
            env['QSHIFT_SAFETY_BENCHMARK']='1'; env['QSHIFT_SAFETY_BENCH_CONFIG']=str(Path(benchmark_config).resolve())
        if test_fault:
            env['QSHIFT_SAFETY_TEST_MODE']='1'; env['QSHIFT_SAFETY_FAULT']=test_fault
            env['QSHIFT_SAFETY_SAMPLE_RETURNED_MARKER']=str(run_dir/'.sample-returned')
        if kill_on_sample_marker:
            env['QSHIFT_SAFETY_TEST_MODE']='1'
            env['QSHIFT_SAFETY_ACTIVE_SAMPLE_MARKER']=str(marker)
        proc=subprocess.Popen([sys.executable,str(WORKER)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        while proc.poll() is None and deadline.remaining()>0:
            if kill_on_sample_marker and marker.exists():
                _terminate(proc)
                _mark_status(run_dir,{'status':'interrupted_active_sampler','interruption_boundary':'sample_call_in_progress',
                                      'in_flight':_read_inflight(run_dir)})
                out,err=proc.communicate(timeout=2)
                return {'status':'interrupted_active_sampler','returncode':proc.returncode,'stdout':out,'stderr':err,'recovery':recovery}
            time.sleep(min(.02,deadline.remaining()))
        if proc.poll() is None:
            _terminate(proc)
            _mark_status(run_dir,{'status':'deadline_exceeded','deadline_phase':_current_phase(run_dir),
                                  'in_flight':_read_inflight(run_dir),'deadline_unix':time.time()})
            out,err=proc.communicate(timeout=2)
            return {'status':'deadline_exceeded','returncode':proc.returncode,'stdout':out,'stderr':err,'recovery':recovery}
        out,err=proc.communicate()
        if proc.returncode!=0:
            return {'status':'worker_failed','returncode':proc.returncode,'stdout':out,'stderr':err,'recovery':recovery}
        # Worker maps the frozen runner's success state to finalizing. Only the
        # parent can write completed, after independent audit and within budget.
        try:
            audit=_audit_and_finalize(run_dir,deadline,benchmark_config)
        except TimeoutError as exc:
            _mark_status(run_dir,{'status':'deadline_exceeded','deadline_phase':str(exc),'in_flight':None,
                                  'deadline_unix':time.time()})
            return {'status':'deadline_exceeded','phase':str(exc),'recovery':recovery}
        except Exception as exc:
            _mark_status(run_dir,{'status':'failed_finalization','failure_type':type(exc).__name__,
                                  'failure_message':str(exc),'in_flight':None})
            raise
        if audit.get('status')=='deadline_exceeded':
            return {'status':'deadline_exceeded','phase':audit.get('phase'),'recovery':recovery}
        return {'status':'completed','worker_returncode':proc.returncode,'stdout':out,'stderr':err,
                'audit':audit,'recovery':recovery,'runtime_seconds':time.monotonic()-started,
                'frozen_main_head':record.get('main_head'),'safety_source_hashes':len(safety_record['sha256'])}

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--preflight',action='store_true')
    ap.add_argument('--run',action='store_true'); ap.add_argument('--authorize-stage5-sampling',action='store_true')
    ap.add_argument('--recover-uncommitted',action='store_true')
    ap.add_argument('--benchmark-config',type=Path)
    a=ap.parse_args(argv)
    if a.preflight:
        s=verify_safety_sources(); f=verify_frozen_inputs(); print(json.dumps({'status':'PASS_NO_SAMPLING','frozen_hashes':len(f['sha256']),
                  'safety_source_hashes':len(s['sha256']),
                  'stage5_sampling_invoked':False,'stage5_run_directory_exists':(ROOT/'outputs/stage5_secondary_inference_repair_v1/run').exists()},indent=2)); return 0
    if a.benchmark_config:
        # Test-only benchmark entry point cannot target the frozen run directory.
        run_dir=Path(__file__).parent/'benchmark_runs'/'current'
        cfg=a.benchmark_config
        result=safe_execute(run_dir,timeout_seconds=60,benchmark_config=cfg,recover_uncommitted=a.recover_uncommitted)
    elif a.run and a.authorize_stage5_sampling:
        cfg=json.loads(CONFIG.read_text(encoding='utf-8'))
        result=safe_execute(ROOT/'outputs/stage5_secondary_inference_repair_v1/run',
                            timeout_seconds=cfg['resources']['wall_seconds_max'],recover_uncommitted=a.recover_uncommitted)
    else:
        print('No sampling started; use --preflight. Production execution requires both explicit flags.'); return 2
    print(json.dumps(result,indent=2,default=str)); return 0 if result['status']=='completed' else 1
if __name__=='__main__': raise SystemExit(main())
