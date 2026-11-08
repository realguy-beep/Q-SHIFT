"""Create the v3.4.2 pre-benchmark source/config freeze without reading Stage 5 seed rows."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
V2=ROOT/'outputs/stage5_secondary_inference_repair_v1/STAGE5_PRETEST_FREEZE_V2.json'
V33=ROOT/'outputs/stage5_execution_safety_v3_3/SAFETY_FREEZE.json'
V33_SEEDS=ROOT/'outputs/stage5_execution_safety_v3_3/SAFETY_SEED_AUDIT.json'
V34=ROOT/'outputs/stage5_execution_safety_v3_4'
V34_FREEZE=V34/'SAFETY_FREEZE_V4.json'
V34_TESTS=V34/'SAFETY_TEST_RESULTS_V4.json'
V341=ROOT/'outputs/stage5_execution_safety_v3_4_1'
V341_FREEZE=V341/'SAFETY_FREEZE_V4.json'
V341_TESTS=V341/'SAFETY_TEST_RESULTS_V4.json'
OUT=HERE/'SAFETY_FREEZE_V4.json'
FILES=(
 'ownership_runtime_v4.py','safety_runner_v4.py','worker_v4.py','audit_saved_run_v4.py',
 'finalize_v4.py','test_process_child_v4.py','test_safety_v4.py','run_tests_v4.py',
 'prepare_safety_freeze_v4.py','independent_audit_v4.py',
 'benchmark_config.json','fault_config.json','active_sampler_config.json','SAFETY_PROTOCOL_V4_2.md')
STAGE5_SEED_RANGE=(14_000_000_001,14_000_012_100) # derived from frozen v2 seed_map; inventory rows remain unopened

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def collect_seed_values(obj, key=''):
    found=set()
    if isinstance(obj,dict):
        for k,v in obj.items():
            if 'seed' in str(k).lower(): found |= collect_seed_values(v,str(k))
            elif isinstance(v,(dict,list)): found |= collect_seed_values(v,str(k))
    elif isinstance(obj,list):
        for value in obj: found |= collect_seed_values(value,key)
    elif isinstance(obj,int) and not isinstance(obj,bool) and 'seed' in key.lower():
        found.add(int(obj))
    return found

def main():
    old=json.loads(V2.read_text(encoding='utf-8'))
    if old.get('status')!='PRETEST_FROZEN_NOT_AUTHORIZED' or old.get('stage5_evaluation_shots_generated')!=0:
        raise RuntimeError('v2 Stage 5 freeze boundary is not intact')
    for rel,want in old['sha256'].items():
        if sha(ROOT/rel)!=want: raise RuntimeError(f'v2 frozen hash mismatch: {rel}')
    v33=json.loads(V33.read_text(encoding='utf-8'))
    if v33.get('stage5_sampling_authorized') is not False or v33.get('stage5_evaluation_shots_generated')!=0:
        raise RuntimeError('v3.3 historical safety boundary changed')
    for rel,want in v33['sha256'].items():
        if sha(ROOT/'outputs/stage5_execution_safety_v3_3'/rel)!=want:
            raise RuntimeError(f'v3.3 historical safety hash mismatch: {rel}')
    v34_freeze=json.loads(V34_FREEZE.read_text(encoding='utf-8'))
    if v34_freeze.get('state')!='FROZEN_BEFORE_BENCHMARK_SAMPLING' or len(v34_freeze.get('sha256',{}))!=14:
        raise RuntimeError('v3.4 historical freeze is invalid or incomplete')
    if json.loads(V34_TESTS.read_text(encoding='utf-8')).get('status')!='FAIL':
        raise RuntimeError('v3.4 failed test report is missing')
    for rel,want in v34_freeze['sha256'].items():
        if sha(V34/rel)!=want: raise RuntimeError(f'v3.4 historical source hash mismatch: {rel}')
    audit=json.loads(V33_SEEDS.read_text(encoding='utf-8'))
    if audit.get('stage5_seed_rows_opened') is not False:
        raise RuntimeError('historical seed audit opened Stage 5 seed rows')
    historical=set()
    for row in audit['historical_files_checked']:
        path=ROOT/row['path']
        if sha(path)!=row['sha256']: raise RuntimeError(f'historical seed metadata hash mismatch: {row["path"]}')
        if path.suffix.lower()=='.json':
            historical |= collect_seed_values(json.loads(path.read_text(encoding='utf-8')))
    previous_bench=set(int(x) for x in audit['streams'])
    prior_v34=set()
    for name in ('benchmark_config.json','fault_config.json','active_sampler_config.json'):
        prior_cfg=json.loads((V34/name).read_text(encoding='utf-8'))
        prior_v34.update(int(row['seed']) for row in prior_cfg['streams'])
        prior_cfg_341=json.loads((V341/name).read_text(encoding='utf-8'))
        prior_v34.update(int(row['seed']) for row in prior_cfg_341['streams'])
    v341_freeze=json.loads(V341_FREEZE.read_text(encoding='utf-8'))
    if v341_freeze.get('state')!='FROZEN_BEFORE_BENCHMARK_SAMPLING' or len(v341_freeze.get('sha256',{}))!=14:
        raise RuntimeError('v3.4.1 historical freeze is invalid or incomplete')
    if json.loads(V341_TESTS.read_text(encoding='utf-8')).get('status')!='FAIL':
        raise RuntimeError('v3.4.1 failed test report is missing')
    for rel,want in v341_freeze['sha256'].items():
        if sha(V341/rel)!=want: raise RuntimeError(f'v3.4.1 historical source hash mismatch: {rel}')
    proposed=[]
    for name in ('benchmark_config.json','fault_config.json','active_sampler_config.json'):
        cfg=json.loads((HERE/name).read_text(encoding='utf-8'))
        proposed.extend(int(row['seed']) for row in cfg['streams'])
    if len(proposed)!=len(set(proposed)): raise RuntimeError('v3.4.2 benchmark streams collide with one another')
    if set(proposed)&historical: raise RuntimeError('v3.4.2 benchmark seed collides with recoverable historical seed')
    if set(proposed)&previous_bench: raise RuntimeError('v3.4.2 benchmark seed reuses a v3.3 safety benchmark seed')
    if set(proposed)&prior_v34: raise RuntimeError('v3.4.2 benchmark seed reuses an earlier v3.4 safety namespace')
    lo,hi=STAGE5_SEED_RANGE
    if any(lo<=seed<=hi for seed in proposed): raise RuntimeError('v3.4.2 benchmark seed overlaps Stage 5 reserved namespace')
    if (ROOT/'outputs/stage5_secondary_inference_repair_v1/run').exists():
        raise RuntimeError('Stage 5 output directory exists; refusing readiness freeze')
    hashes={name:sha(HERE/name) for name in FILES}
    record={
      'name':'Q-SHIFT Stage 5 process ownership safety revision v3.4.2',
      'state':'FROZEN_BEFORE_BENCHMARK_SAMPLING',
      'stage5_sampling_authorized':False,'stage5_evaluation_shots_generated':0,
      'historical_stage5_freeze_sha256':sha(V2),'historical_stage5_frozen_hash_count':len(old['sha256']),
      'historical_v3_3_safety_freeze_sha256':sha(V33),
      'historical_v3_3_safety_hash_count':len(v33['sha256']),
      'historical_seed_audit_sha256':sha(V33_SEEDS),
      'superseded_v3_4_freeze_sha256':sha(V34_FREEZE),
      'superseded_v3_4_failed_test_results_sha256':sha(V34_TESTS),
      'superseded_v3_4_1_freeze_sha256':sha(V341_FREEZE),
      'superseded_v3_4_1_test_results_sha256':sha(V341_TESTS),
      'superseded_v3_4_1_source_hash_count':len(v341_freeze['sha256']),
      'historical_seed_files_verified':len(audit['historical_files_checked']),
      'historical_seed_values_reported':audit['recoverable_historical_integer_values_screened'],
      'historical_seed_collisions':0,'prior_benchmark_seed_collisions':0,
      'superseded_v3_4_benchmark_seed_collisions':0,
      'superseded_v3_4_1_benchmark_seed_collisions':0,
      'stage5_reserved_seed_rows_opened':False,
      'stage5_reserved_seed_range_screened_by_frozen_v2_rule':[lo,hi],
      'new_benchmark_stream_count':len(proposed),'new_benchmark_streams_unique':True,
      'new_benchmark_historical_collisions':0,'new_benchmark_reserved_namespace_collisions':0,
      'sha256':hashes}
    OUT.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'FROZEN_BEFORE_BENCHMARK_SAMPLING','v2_hashes':len(old['sha256']),
      'v33_hashes':len(v33['sha256']),'v341_hashes':len(hashes),'historical_seed_files_verified':len(audit['historical_files_checked']),
      'new_benchmark_streams':len(proposed),'stage5_rows_opened':False,'stage5_run_directory_exists':False},indent=2))

if __name__=='__main__': main()
