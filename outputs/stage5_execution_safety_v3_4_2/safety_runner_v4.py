"""Stage 5 v3.4.2 supervisor with durable child intents and self-bounded children."""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, time, uuid
from pathlib import Path

from ownership_runtime_v4 import (RunDirectoryLock, Deadline, atomic_json,
    publish_child_intent, record_child_spawn, assert_child_ownership_clear,
    LockBusyError, OwnershipUncertainError, verify_committed_npz, WindowsChildJob)

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
V2=ROOT/'outputs/stage5_secondary_inference_repair_v1/stage5_sampling_runner_v2.py'
WORKER=HERE/'worker_v4.py'; AUDITOR=HERE/'audit_saved_run_v4.py'; FINALIZER=HERE/'finalize_v4.py'
FREEZE=ROOT/'outputs/stage5_secondary_inference_repair_v1/STAGE5_PRETEST_FREEZE_V2.json'
CONFIG=ROOT/'outputs/stage5_secondary_inference_repair_v1/STAGE5_REPAIR_CONFIG.json'
SAFETY_FREEZE=HERE/'SAFETY_FREEZE_V4.json'
V33_FREEZE=ROOT/'outputs/stage5_execution_safety_v3_3/SAFETY_FREEZE.json'
V34=ROOT/'outputs/stage5_execution_safety_v3_4'
V34_FREEZE=V34/'SAFETY_FREEZE_V4.json'
V34_TESTS=V34/'SAFETY_TEST_RESULTS_V4.json'
V341=ROOT/'outputs/stage5_execution_safety_v3_4_1'
V341_FREEZE=V341/'SAFETY_FREEZE_V4.json'
V341_TESTS=V341/'SAFETY_TEST_RESULTS_V4.json'


def verify_safety_sources():
    if not SAFETY_FREEZE.is_file(): raise RuntimeError('v3.4.2 safety freeze is missing')
    record=json.loads(SAFETY_FREEZE.read_text(encoding='utf-8'))
    if record.get('state')!='FROZEN_BEFORE_BENCHMARK_SAMPLING' or record.get('stage5_sampling_authorized') is not False:
        raise RuntimeError('v3.4.2 freeze does not preserve the no-sampling boundary')
    if record.get('stage5_evaluation_shots_generated')!=0 or record.get('historical_stage5_frozen_hash_count')!=53:
        raise RuntimeError('v3.4.2 freeze no longer records the 53-file Stage 5 freeze / zero-shot boundary')
    if record.get('historical_v3_3_safety_hash_count')!=13:
        raise RuntimeError('v3.4.2 freeze no longer records all 13 v3.3 safety hashes')
    for rel,want in record['sha256'].items():
        path=HERE/rel
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=want:
            raise RuntimeError(f'v3.4.2 source/config hash mismatch: {rel}')
    if hashlib.sha256(FREEZE.read_bytes()).hexdigest()!=record.get('historical_stage5_freeze_sha256'):
        raise RuntimeError('historical v2 freeze hash mismatch')
    if hashlib.sha256(V33_FREEZE.read_bytes()).hexdigest()!=record.get('historical_v3_3_safety_freeze_sha256'):
        raise RuntimeError('historical v3.3 safety freeze hash mismatch')
    if hashlib.sha256(V341_FREEZE.read_bytes()).hexdigest()!=record.get('superseded_v3_4_1_freeze_sha256'):
        raise RuntimeError('superseded v3.4.1 freeze hash mismatch')
    if hashlib.sha256(V341_TESTS.read_bytes()).hexdigest()!=record.get('superseded_v3_4_1_test_results_sha256'):
        raise RuntimeError('superseded v3.4.1 failed test report hash mismatch')
    if hashlib.sha256(V34_FREEZE.read_bytes()).hexdigest()!=record.get('superseded_v3_4_freeze_sha256'):
        raise RuntimeError('superseded v3.4 freeze hash mismatch')
    if hashlib.sha256(V34_TESTS.read_bytes()).hexdigest()!=record.get('superseded_v3_4_failed_test_results_sha256'):
        raise RuntimeError('superseded v3.4 failed test report hash mismatch')
    v34=json.loads(V34_FREEZE.read_text(encoding='utf-8'))
    if len(v34.get('sha256',{}))!=14:
        raise RuntimeError('superseded v3.4 source inventory changed')
    for rel,want in v34['sha256'].items():
        path=V34/rel
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=want:
            raise RuntimeError(f'superseded v3.4 source hash mismatch: {rel}')
    v341=json.loads(V341_FREEZE.read_text(encoding='utf-8'))
    if len(v341.get('sha256',{}))!=14:
        raise RuntimeError('superseded v3.4.1 source inventory changed')
    for rel,want in v341['sha256'].items():
        path=V341/rel
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=want:
            raise RuntimeError(f'superseded v3.4.1 source hash mismatch: {rel}')
    v33=json.loads(V33_FREEZE.read_text(encoding='utf-8'))
    if len(v33.get('sha256',{}))!=13:
        raise RuntimeError('historical v3.3 safety hash inventory count changed')
    for rel,want in v33['sha256'].items():
        path=ROOT/'outputs/stage5_execution_safety_v3_3'/rel
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=want:
            raise RuntimeError(f'historical v3.3 safety artifact hash mismatch: {rel}')
    seed_audit=ROOT/'outputs/stage5_execution_safety_v3_3/SAFETY_SEED_AUDIT.json'
    if hashlib.sha256(seed_audit.read_bytes()).hexdigest()!=record.get('historical_seed_audit_sha256'):
        raise RuntimeError('historical seed audit hash mismatch')
    return record


def verify_frozen_inputs():
    record=json.loads(FREEZE.read_text(encoding='utf-8'))
    if record.get('status')!='PRETEST_FROZEN_NOT_AUTHORIZED' or record.get('stage5_evaluation_shots_generated')!=0 or len(record.get('sha256',{}))!=53:
        raise RuntimeError('Stage 5 remains unauthorized or frozen state changed')
    for rel,want in record['sha256'].items():
        path=ROOT/rel
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=want:
            raise RuntimeError(f'frozen Stage 5 hash mismatch: {rel}')
    return record


def _mark_status(run_dir, value):
    path=Path(run_dir)/'status.json'; old={}
    if path.exists():
        try: old=json.loads(path.read_text(encoding='utf-8'))
        except Exception: pass
    old.update(value); atomic_json(path,old)


def _read_inflight(run_dir):
    try: return json.loads((Path(run_dir)/'status.json').read_text(encoding='utf-8')).get('in_flight')
    except Exception: return None


def _terminate(proc):
    if proc.poll() is not None: return
    proc.terminate()
    try: proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill(); proc.wait(timeout=2)


def _checkpoint_for(run_dir, inflight):
    import importlib.util
    spec=importlib.util.spec_from_file_location('stage5_v2_constants',V2)
    module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module)
    return Path(run_dir)/'roots'/module.filename(float(inflight['p']),int(inflight['root']))


def reconcile_uncommitted(run_dir:Path, *, explicit_recovery:bool):
    status_path=Path(run_dir)/'status.json'
    if not status_path.exists(): return {'state':'clean'}
    status=json.loads(status_path.read_text(encoding='utf-8'))
    roots=Path(run_dir)/'roots'
    for archive in roots.glob('root_p*.npz') if roots.exists() else []:
        verify_committed_npz(archive)
    inflight=status.get('in_flight')
    if not inflight: return {'state':'no_inflight'}
    if not explicit_recovery:
        raise RuntimeError('in-flight work found; resume requires explicit --recover-uncommitted')
    archive=_checkpoint_for(run_dir,inflight); phase=None
    if archive.exists():
        verify_committed_npz(archive)
        import numpy as np
        with np.load(archive,allow_pickle=False) as saved: phase=str(np.asarray(saved['phase']).item())
    committed=phase in {'calibration_complete','evaluation_complete','complete'} and not (
        inflight.get('kind')=='evaluation' and phase=='calibration_complete')
    journal_path=Path(run_dir)/'RECOVERY_JOURNAL.json'
    journal=json.loads(journal_path.read_text(encoding='utf-8')) if journal_path.exists() else {'events':[]}
    event={'event_id':uuid.uuid4().hex,'kind':inflight.get('kind'),'probability':inflight.get('p'),
      'root':inflight.get('root'),'checkpoint_phase':phase,
      'outcome':'committed_checkpoint_reconciled' if committed else 'uncommitted_stream_will_replay_same_frozen_seed',
      'timestamp_unix':time.time(),'explicit_recovery':True}
    journal['events'].append(event); atomic_json(journal_path,journal)
    status.update({'in_flight':None,'status':'recovering','last_recovery_event':event['event_id']})
    atomic_json(status_path,status)
    return {'state':event['outcome'],'phase':phase}


def _run_owned_child(role, script, run_dir, deadline, env, job, extra=(), timeout_phase='child'):
    """Publish intent before spawn; token scan covers Popen's PID handoff window."""
    token=publish_child_intent(run_dir,role,deadline.deadline)
    command=[sys.executable,str(script),*map(str,extra),f'--qshift-owner-token={token}',
             f'--qshift-deadline-monotonic={deadline.deadline:.17g}']
    try:
        proc=job.create_suspended(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    except BaseException:
        # No process was created if CreateProcess/Popen raises. A stale intent is
        # safely reconciled by the next launcher after it proves no token owner.
        raise
    try:
        job.assign(proc)
        record_child_spawn(run_dir,token,proc.pid)
        job.resume(proc)
    except BaseException:
        _terminate(proc)
        raise
    remaining=deadline.remaining()
    try:
        out,err=proc.communicate(timeout=remaining)
    except subprocess.TimeoutExpired:
        _terminate(proc)
        raise TimeoutError(f'Stage 5 deadline expired during {timeout_phase}')
    if proc.returncode!=0:
        tail=(err or '')[-4000:]
        raise RuntimeError(f'{role} child failed ({proc.returncode}): {tail}')
    assert_child_ownership_clear(run_dir)
    return out,err


def _audit_and_finalize(run_dir, deadline, job, benchmark_config=None):
    env=os.environ.copy(); env['QSHIFT_STAGE5_RUN_DIR']=str(Path(run_dir).resolve())
    if benchmark_config:
        env['QSHIFT_SAFETY_BENCHMARK']='1'; env['QSHIFT_SAFETY_BENCH_CONFIG']=str(Path(benchmark_config).resolve())
    deadline.check('artifact verification start')
    out,err=_run_owned_child('auditor',AUDITOR,run_dir,deadline,env,job,timeout_phase='independent artifact audit')
    audit=json.loads(out)
    if audit.get('status')!='PASS_INDEPENDENT_AUDIT': raise RuntimeError('independent audit did not pass')
    status=json.loads((Path(run_dir)/'status.json').read_text(encoding='utf-8'))
    if int(status.get('unique_shots_generated',-1))!=int(audit.get('unique_shots_recomputed',-2)):
        raise RuntimeError('persisted unique-shot count disagrees with independent audit')
    if int(status.get('completed_roots',-1))!=int(audit.get('roots_verified',-2)):
        raise RuntimeError('persisted completed-root count disagrees with independent audit')
    deadline.check('finalizer launch')
    _run_owned_child('finalizer',FINALIZER,run_dir,deadline,env,job,
                     extra=(str(Path(run_dir).resolve()),),timeout_phase='finalization')
    deadline.check('terminal status commit')
    manifest=json.loads((Path(run_dir)/'FINALIZATION_MANIFEST.json').read_text(encoding='utf-8'))
    if manifest.get('status')!='verified_not_terminal': raise RuntimeError('finalization evidence is incomplete')
    final_status=json.loads((Path(run_dir)/'status.json').read_text(encoding='utf-8'))
    if final_status.get('status')!='finalizing': raise RuntimeError('status changed during finalizer ownership')
    deadline.check('terminal status atomic replacement')
    final_status.update({'status':'completed','finalized_monotonic':time.monotonic(),
                         'finalized_unix':time.time(),'in_flight':None,
                         'independent_audit':'PASS_INDEPENDENT_AUDIT'})
    atomic_json(Path(run_dir)/'status.json',final_status)
    if deadline.remaining()<=0:
        _mark_status(run_dir,{'status':'deadline_exceeded','deadline_phase':'terminal status replacement',
                              'deadline_unix':time.time()})
        raise TimeoutError('Stage 5 deadline expired during terminal status replacement')
    return audit,out,err


def safe_execute(run_dir:Path, *, timeout_seconds:float, benchmark_config:Path|None=None,
                 recover_uncommitted=False, test_fault=None, kill_on_sample_marker=False):
    started=time.monotonic(); deadline=Deadline(seconds=timeout_seconds)
    run_dir=Path(run_dir).resolve()
    safety=verify_safety_sources(); frozen=verify_frozen_inputs()
    cfg=json.loads(CONFIG.read_text(encoding='utf-8'))
    if benchmark_config:
        benchmark_config=Path(benchmark_config).resolve()
        try: benchmark_config.relative_to(HERE.resolve())
        except ValueError as exc: raise ValueError('benchmark config must be inside v3.4.2') from exc
    elif test_fault or kill_on_sample_marker:
        raise ValueError('failure injection is benchmark-only')
    if not benchmark_config and timeout_seconds>float(cfg['resources']['wall_seconds_max']):
        raise ValueError('timeout exceeds the frozen Stage 5 limit')
    run_dir.mkdir(parents=True,exist_ok=True)
    job=WindowsChildJob()
    try:
      with RunDirectoryLock(run_dir,kind='launcher'):
        recovery=assert_child_ownership_clear(run_dir)
        checkpoint_recovery=reconcile_uncommitted(run_dir,explicit_recovery=recover_uncommitted)
        recovery={'ownership':recovery,'checkpoint':checkpoint_recovery}
        env=os.environ.copy(); env['QSHIFT_STAGE5_RUN_DIR']=str(run_dir)
        if benchmark_config:
            env['QSHIFT_SAFETY_BENCHMARK']='1'; env['QSHIFT_SAFETY_BENCH_CONFIG']=str(benchmark_config)
        if test_fault:
            env['QSHIFT_SAFETY_TEST_MODE']='1'; env['QSHIFT_SAFETY_FAULT']=test_fault
            env['QSHIFT_SAFETY_SAMPLE_RETURNED_MARKER']=str(run_dir/'.sample-returned')
        if kill_on_sample_marker:
            env['QSHIFT_SAFETY_TEST_MODE']='1'; env['QSHIFT_SAFETY_ACTIVE_SAMPLE_MARKER']=str(run_dir/'.sampling-active')
        try:
            out,err=_run_owned_child('worker',WORKER,run_dir,deadline,env,job,timeout_phase='worker/aggregation')
        except TimeoutError as exc:
            _mark_status(run_dir,{'status':'deadline_exceeded','deadline_phase':'worker/aggregation',
                                  'in_flight':_read_inflight(run_dir),'deadline_unix':time.time()})
            return {'status':'deadline_exceeded','error':str(exc),'recovery':recovery}
        except RuntimeError as exc:
            if test_fault:
                return {'status':'worker_failed','error':str(exc),'recovery':recovery}
            _mark_status(run_dir,{'status':'worker_failed','failure_message':str(exc),
                                  'in_flight':_read_inflight(run_dir)})
            raise
        try:
            audit,aout,aerr=_audit_and_finalize(run_dir,deadline,job,benchmark_config)
        except TimeoutError as exc:
            _mark_status(run_dir,{'status':'deadline_exceeded','deadline_phase':str(exc),
                                  'in_flight':_read_inflight(run_dir),'deadline_unix':time.time()})
            return {'status':'deadline_exceeded','error':str(exc),'recovery':recovery}
        except Exception as exc:
            _mark_status(run_dir,{'status':'failed_finalization','failure_type':type(exc).__name__,
                                  'failure_message':str(exc),'in_flight':None})
            raise
        return {'status':'completed','worker_stdout':out,'worker_stderr':err,
                'audit':audit,'audit_stdout':aout,'finalizer_stderr':aerr,
                'recovery':recovery,'runtime_seconds':time.monotonic()-started,
                'frozen_main_head':frozen.get('main_head'),
                'safety_source_hashes':len(safety['sha256'])}
    finally:
        job.close()


def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--preflight',action='store_true')
    ap.add_argument('--run',action='store_true'); ap.add_argument('--authorize-stage5-sampling',action='store_true')
    ap.add_argument('--recover-uncommitted',action='store_true')
    ap.add_argument('--benchmark-config',type=Path)
    args=ap.parse_args(argv)
    if args.preflight:
        s=verify_safety_sources(); f=verify_frozen_inputs()
        print(json.dumps({'status':'PASS_NO_SAMPLING','historical_hashes':len(f['sha256']),
          'safety_v3_4_2_hashes':len(s['sha256']),'stage5_sampling_authorized':False,
          'stage5_run_directory_exists':(ROOT/'outputs/stage5_secondary_inference_repair_v1/run').exists()},indent=2)); return 0
    if args.benchmark_config:
        run_dir=HERE/'benchmark_runs'/'current'
        result=safe_execute(run_dir,timeout_seconds=120,benchmark_config=args.benchmark_config,
                            recover_uncommitted=args.recover_uncommitted)
    elif args.run and args.authorize_stage5_sampling:
        cfg=json.loads(CONFIG.read_text(encoding='utf-8'))
        result=safe_execute(ROOT/'outputs/stage5_secondary_inference_repair_v1/run',
                            timeout_seconds=cfg['resources']['wall_seconds_max'],
                            recover_uncommitted=args.recover_uncommitted)
    else:
        print('No sampling started. Production requires both --run and --authorize-stage5-sampling.'); return 2
    print(json.dumps(result,indent=2,default=str)); return 0 if result.get('status')=='completed' else 1


if __name__=='__main__': raise SystemExit(main())
