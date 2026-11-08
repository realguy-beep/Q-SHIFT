"""Independent read-only audit of v3.4.2 safety freeze and benchmark evidence."""
from __future__ import annotations
import hashlib, json, time
from pathlib import Path
import psutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
V34=ROOT/'outputs/stage5_execution_safety_v3_4'
V341=ROOT/'outputs/stage5_execution_safety_v3_4_1'

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def independent_archive_check(path):
    path=Path(path); sidecar=path.with_suffix(path.suffix+'.commit.json')
    marker=json.loads(sidecar.read_text(encoding='utf-8'))
    actual=sha(path)
    if marker.get('archive')!=path.name or marker.get('committed') is not True or marker.get('sha256')!=actual:
        raise ValueError(f'independent archive/sidecar mismatch: {path.name}')
    return actual

def audit():
    freeze=json.loads((HERE/'SAFETY_FREEZE_V4.json').read_text(encoding='utf-8'))
    mismatches=[]; event_failures=[]
    for rel,want in freeze['sha256'].items():
        path=HERE/rel
        if not path.is_file() or sha(path)!=want: mismatches.append(f'v3.4.2:{rel}')
    v2_path=ROOT/'outputs/stage5_secondary_inference_repair_v1/STAGE5_PRETEST_FREEZE_V2.json'
    v33_path=ROOT/'outputs/stage5_execution_safety_v3_3/SAFETY_FREEZE.json'
    v2=json.loads(v2_path.read_text(encoding='utf-8')); v33=json.loads(v33_path.read_text(encoding='utf-8'))
    if sha(v2_path)!=freeze['historical_stage5_freeze_sha256']: mismatches.append('historical v2 freeze')
    for rel,want in v2.get('sha256',{}).items():
        path=ROOT/rel
        if not path.is_file() or sha(path)!=want: mismatches.append(f'v2:{rel}')
    if sha(v33_path)!=freeze['historical_v3_3_safety_freeze_sha256']: mismatches.append('historical v3.3 safety freeze')
    for rel,want in v33.get('sha256',{}).items():
        path=ROOT/'outputs/stage5_execution_safety_v3_3'/rel
        if not path.is_file() or sha(path)!=want: mismatches.append(f'v3.3:{rel}')
    v34_freeze_path=V34/'SAFETY_FREEZE_V4.json'
    v34_tests_path=V34/'SAFETY_TEST_RESULTS_V4.json'
    if sha(v34_freeze_path)!=freeze['superseded_v3_4_freeze_sha256']: mismatches.append('superseded v3.4 freeze')
    if sha(v34_tests_path)!=freeze['superseded_v3_4_failed_test_results_sha256']: mismatches.append('superseded v3.4 failed test report')
    v34=json.loads(v34_freeze_path.read_text(encoding='utf-8'))
    for rel,want in v34.get('sha256',{}).items():
        path=V34/rel
        if not path.is_file() or sha(path)!=want: mismatches.append(f'v3.4:{rel}')
    v341_freeze_path=V341/'SAFETY_FREEZE_V4.json'
    v341_tests_path=V341/'SAFETY_TEST_RESULTS_V4.json'
    if sha(v341_freeze_path)!=freeze['superseded_v3_4_1_freeze_sha256']: mismatches.append('superseded v3.4.1 freeze')
    if sha(v341_tests_path)!=freeze['superseded_v3_4_1_test_results_sha256']: mismatches.append('superseded v3.4.1 failed test report')
    v341=json.loads(v341_freeze_path.read_text(encoding='utf-8'))
    for rel,want in v341.get('sha256',{}).items():
        path=V341/rel
        if not path.is_file() or sha(path)!=want: mismatches.append(f'v3.4.1:{rel}')
    results=json.loads((HERE/'SAFETY_TEST_RESULTS_V4.json').read_text(encoding='utf-8'))
    if results.get('status')!='PASS' or results.get('failures') or results.get('errors'):
        event_failures.append('v3.4.1 test suite did not pass')
    evroot=Path(results['evidence_root'])
    lifecycle=json.loads((evroot/'OWNERSHIP_FAILURE_INJECTION_V4.json').read_text(encoding='utf-8'))
    events=lifecycle.get('process_lifecycle_events',[])
    required={('worker','startup'),('worker','active'),('auditor','startup'),('auditor','active'),
              ('finalizer','startup'),('finalizer','active')}
    observed={(x['role'],x['phase']) for x in events}
    if observed!=required: event_failures.append('lifecycle phase coverage mismatch')
    for event in events:
        handoff_safe=(event.get('second_launcher_rejected') and event.get('child_alive_after_second_launcher_probe')) or (
            not event.get('child_alive_after_second_launcher_probe') and event.get('second_launcher_accepted_only_after_child_dead'))
        if not (event.get('supervisor_terminated') and handoff_safe and
                event.get('child_deadline_released_ownership') and event.get('second_launcher_accepted_after_release')):
            event_failures.append(f"failed lifecycle event {event.get('role')}:{event.get('phase')}")
        try:
            proc=psutil.Process(int(event['child_pid']))
            if abs(proc.create_time()-float(event['child_create_time']))<0.01:
                event_failures.append(f"child still alive: {event['role']}:{event['phase']}")
        except psutil.NoSuchProcess: pass
        except psutil.AccessDenied: event_failures.append(f"child liveness unverifiable: {event['role']}:{event['phase']}")
    if not lifecycle.get('all_six_cases_passed'): event_failures.append('lifecycle fixture summary failed')
    normal=evroot/'paired_audit'; recovery=evroot/'recovery'
    normal_audit=json.loads((normal/'INDEPENDENT_AUDIT.json').read_text())
    normal_status=json.loads((normal/'status.json').read_text())
    normal_manifest=json.loads((normal/'FINALIZATION_MANIFEST.json').read_text())
    hash_count=0
    for name,want in normal_manifest['root_sha256'].items():
        if independent_archive_check(normal/'roots'/name)!=want: event_failures.append(f'archive mismatch {name}')
        hash_count+=1
    if normal_status.get('status')!='completed' or normal_audit.get('roots_verified')!=2 or normal_audit.get('unique_shots_recomputed')!=1536 or hash_count!=2:
        event_failures.append('normal benchmark completion/count/hash mismatch')
    recovery_status=json.loads((recovery/'status.json').read_text())
    recovery_audit=json.loads((recovery/'INDEPENDENT_AUDIT.json').read_text())
    journal=json.loads((recovery/'RECOVERY_JOURNAL.json').read_text())
    if recovery_status.get('status')!='completed' or recovery_status.get('unique_shots_generated')!=256 or recovery_audit.get('unique_shots_recomputed')!=256:
        event_failures.append('recovery count/status mismatch')
    if not journal.get('events') or journal['events'][-1].get('outcome')!='uncommitted_stream_will_replay_same_frozen_seed':
        event_failures.append('same-seed recovery journal mismatch')
    seed_audit_path=ROOT/'outputs/stage5_execution_safety_v3_3/SAFETY_SEED_AUDIT.json'
    if sha(seed_audit_path)!=freeze['historical_seed_audit_sha256']:
        event_failures.append('historical seed-audit hash mismatch')
    seed_audit=json.loads(seed_audit_path.read_text(encoding='utf-8'))
    for row in seed_audit.get('historical_files_checked',[]):
        path=ROOT/row['path']
        if not path.is_file() or sha(path)!=row['sha256']:
            event_failures.append(f"historical seed-source hash mismatch: {row['path']}")
    proposed=[]
    for name in ('benchmark_config.json','fault_config.json','active_sampler_config.json'):
        cfg=json.loads((HERE/name).read_text(encoding='utf-8'))
        proposed.extend(int(x['seed']) for x in cfg['streams'])
    prior=set(int(x) for x in seed_audit['streams'])
    previous_v34=set(); previous_v341=set()
    for name in ('benchmark_config.json','fault_config.json','active_sampler_config.json'):
        previous_v34.update(int(x['seed']) for x in json.loads((ROOT/'outputs/stage5_execution_safety_v3_4'/name).read_text(encoding='utf-8'))['streams'])
        previous_v341.update(int(x['seed']) for x in json.loads((V341/name).read_text(encoding='utf-8'))['streams'])
    lo,hi=freeze['stage5_reserved_seed_range_screened_by_frozen_v2_rule']
    if len(proposed)!=freeze['new_benchmark_stream_count'] or len(set(proposed))!=len(proposed):
        event_failures.append('new benchmark seed uniqueness mismatch')
    if set(proposed)&prior or set(proposed)&previous_v34 or set(proposed)&previous_v341 or any(lo<=x<=hi for x in proposed):
        event_failures.append('new benchmark seed collision')
    if len(v2.get('sha256',{}))!=53 or len(v33.get('sha256',{}))!=13:
        event_failures.append('historical hash inventory count mismatch')
    if v2.get('stage5_evaluation_shots_generated')!=0 or freeze.get('stage5_evaluation_shots_generated')!=0:
        event_failures.append('Stage 5 zero-shot boundary mismatch')
    if (ROOT/'outputs/stage5_secondary_inference_repair_v1/run').exists(): event_failures.append('Stage 5 run directory exists')
    return {'status':'PASS' if not mismatches and not event_failures else 'FAIL',
      'independent_recomputation':True,'source_hash_mismatches':mismatches,
      'failure_injection_issues':event_failures,'v3_4_2_source_hash_count':len(freeze['sha256']),
      'historical_v2_hash_count':len(v2['sha256']),'historical_v3_3_hash_count':len(v33['sha256']),
      'superseded_v3_4_source_hash_count':len(v34.get('sha256',{})),
      'superseded_v3_4_1_source_hash_count':len(v341.get('sha256',{})),
      'lifecycle_cases_verified':len(events),'paired_benchmark_roots':normal_audit.get('roots_verified'),
      'paired_benchmark_shots_recomputed':normal_audit.get('unique_shots_recomputed'),
      'paired_checkpoint_hashes_verified':hash_count,
      'recovery_shots_recomputed':recovery_audit.get('unique_shots_recomputed'),
      'recovery_event':journal['events'][-1].get('outcome') if journal.get('events') else None,
      'stage5_evaluation_shots_generated':0,'sealed_stage5_seed_rows_opened':False,
      'audited_unix':time.time()}

if __name__=='__main__':
    result=audit(); (HERE/'INDEPENDENT_AUDIT_V4.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2)); raise SystemExit(0 if result['status']=='PASS' else 1)
