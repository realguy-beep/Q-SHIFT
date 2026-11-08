"""Screen isolated safety-test seeds and freeze safety source before sampling."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ints(obj):
    if isinstance(obj,bool): return
    if isinstance(obj,int) and obj>=1_000_000: yield obj
    elif isinstance(obj,list):
        for x in obj: yield from ints(x)
    elif isinstance(obj,dict):
        for k,v in obj.items():
            if k=='seed' or k.endswith('_seed'): yield from ints(v)
            else: yield from ints(v)

def main():
    freeze=json.loads((ROOT/'outputs/stage5_secondary_inference_repair_v1/STAGE5_PRETEST_FREEZE_V2.json').read_text(encoding='utf-8'))
    for rel,want in freeze['sha256'].items():
        if sha(ROOT/rel)!=want: raise RuntimeError(f'historical Stage 5 hash mismatch: {rel}')
    configs=['benchmark_config.json','active_sampler_config.json','fault_config.json']
    candidate=[]
    for name in configs:
        c=json.loads((HERE/name).read_text(encoding='utf-8'))
        candidate.extend(int(x['seed']) for x in c['streams'])
    if len(candidate)!=len(set(candidate)): raise RuntimeError('duplicate safety benchmark seeds')
    old_inv=json.loads((ROOT/'outputs/stage5_secondary_inference_repair_v1/STAGE5_SECONDARY_REPAIR_SEED_INVENTORY.json').read_text(encoding='utf-8'))
    recovered=set(); checked=[]
    for row in old_inv['historical_sources_checked']:
        p=ROOT/row['path']; digest=sha(p)
        if digest!=row['sha256']: raise RuntimeError(f'historical seed metadata hash mismatch: {row["path"]}')
        recovered.update(ints(json.loads(p.read_text(encoding='utf-8'))))
        checked.append({'path':row['path'],'sha256':digest})
    old_benchmark=ROOT/'outputs/stage5_execution_preflight_v1/BENCHMARK_SEED_INVENTORY.json'
    recovered.update(ints(json.loads(old_benchmark.read_text(encoding='utf-8'))))
    checked.append({'path':str(old_benchmark.relative_to(ROOT)),'sha256':sha(old_benchmark)})
    prior_safety=ROOT/'outputs/stage5_execution_safety_v3_2/SAFETY_SEED_AUDIT.json'
    recovered.update(ints(json.loads(prior_safety.read_text(encoding='utf-8'))))
    checked.append({'path':str(prior_safety.relative_to(ROOT)),'sha256':sha(prior_safety)})
    collisions=sorted(set(candidate)&recovered)
    # The frozen Stage 5 rows are not opened; only the documented contiguous
    # reservation interval is compared to the separate benchmark namespace.
    stage5_base=14_000_000_001; stage5_count=12_100
    reserved_collisions=[x for x in candidate if stage5_base<=x<stage5_base+stage5_count]
    if collisions or reserved_collisions or min(candidate)<80_000_000_000:
        raise RuntimeError('safety benchmark namespace overlaps a recoverable allocation')
    inv={'purpose':'safety tests only; not Stage 5 evaluation','created_before_benchmark_sampling':True,
         'streams':candidate,'stream_count':len(candidate),'all_distinct':True,
         'recoverable_historical_integer_values_screened':len(recovered),'historical_files_checked':checked,
         'historical_collision_count':len(collisions),'stage5_reserved_namespace_collision_count':len(reserved_collisions),
         'stage5_seed_rows_opened':False,'stage5_evaluation_shots_generated':0,
         'screening_note':'Stage 5 reserved seed rows were not opened; test allocation uses a separately reserved high numeric namespace.'}
    (HERE/'SAFETY_SEED_AUDIT.json').write_text(json.dumps(inv,indent=2)+'\n',encoding='utf-8')
    file_names=['safety_runtime.py','safety_runner_v3.py','worker_v3.py','audit_saved_run.py','finalize_v3.py','benchmark_harness.py',
                'test_safety_v3.py','prepare_safety_freeze.py','benchmark_config.json','active_sampler_config.json',
                'fault_config.json','SAFETY_PROTOCOL.md','SAFETY_SEED_AUDIT.json']
    hashed={f:sha(HERE/f) for f in file_names}
    record={'name':'Q-SHIFT Stage 5 execution safety repair v3.3','state':'FROZEN_BEFORE_BENCHMARK_SAMPLING',
      'created_before_safety_benchmark_sampling':True,'stage5_sampling_authorized':False,
      'stage5_evaluation_shots_generated':0,'historical_stage5_freeze_sha256':sha(ROOT/'outputs/stage5_secondary_inference_repair_v1/STAGE5_PRETEST_FREEZE_V2.json'),
      'historical_stage5_frozen_hash_count':len(freeze['sha256']),'safety_seed_audit_sha256':sha(HERE/'SAFETY_SEED_AUDIT.json'),
      'benchmark_stream_count':len(candidate),'sha256':hashed}
    (HERE/'SAFETY_FREEZE.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'FROZEN_BEFORE_BENCHMARK_SAMPLING','stage5_hashes_verified':len(freeze['sha256']),
                      'safety_streams':len(candidate),'distinct':len(set(candidate)),'historical_collisions':len(collisions),
                      'stage5_rows_opened':False,'stage5_sampling':False},indent=2))
if __name__=='__main__': main()
