"""Create and screen disposable benchmark seeds without opening Stage 5 streams."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
TARGET=HERE/'BENCHMARK_SEED_INVENTORY.json'
BASE=80_000_000_001
PROBS=(0.0,0.004,0.008,0.012,0.016)
NROOTS=4
STAGE5_BASE=14_000_000_001
STAGE5_COUNT=12_100

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def large_ints(x):
    if isinstance(x,bool): return
    if isinstance(x,int) and x>=1_000_000: yield x
    elif isinstance(x,list):
        for y in x: yield from large_ints(y)
    elif isinstance(x,dict):
        for y in x.values(): yield from large_ints(y)

def main():
    if TARGET.exists(): raise RuntimeError('refusing to overwrite benchmark seed inventory')
    prior_path=ROOT/'outputs/stage5_secondary_inference_repair_v1/STAGE5_SECONDARY_REPAIR_SEED_INVENTORY.json'
    prior=json.loads(prior_path.read_text(encoding='utf-8'))
    recovered=set(); checked=[]
    for row in prior['historical_sources_checked']:
        rel=row['path']; path=ROOT/rel; actual=sha(path)
        if actual!=row['sha256']: raise RuntimeError(f'nonsealed historical metadata hash changed: {rel}')
        recovered.update(large_ints(json.loads(path.read_text(encoding='utf-8'))))
        checked.append({'path':rel,'sha256':actual})
    streams=[]; seed=BASE
    for kind in ('calibration_detector_only','paired_evaluation_detector_observable'):
        for p in PROBS:
            for root in range(NROOTS):
                streams.append({'kind':kind,'probability':p,'root':root,'seed':seed}); seed+=1
    seeds=[x['seed'] for x in streams]
    stage5_range=set(range(STAGE5_BASE,STAGE5_BASE+STAGE5_COUNT))
    collisions=set(seeds)&recovered
    stage5_collisions=set(seeds)&stage5_range
    if len(seeds)!=40 or len(set(seeds))!=40 or collisions or stage5_collisions:
        raise RuntimeError('benchmark seed collision, duplication, or allocation defect')
    output={'purpose':'disposable end-to-end runtime benchmark only; never Stage 5 evaluation',
      'created_before_sampling':True,'benchmark_samples_generated':0,'stage5_evaluation_samples_generated':0,
      'sealed_stage5_seed_values_loaded':False,'sealed_historical_outcomes_accessed':False,
      'probabilities':list(PROBS),'roots_per_condition':NROOTS,'stream_count':len(streams),
      'streams':streams,'runtime_bootstrap_seed':BASE+40,
      'historical_sources_checked':checked,'recoverable_historical_integer_count':len(recovered),
      'historical_collision_count':len(collisions),'stage5_reserved_allocation_collision_count':len(stage5_collisions),
      'stage5_namespace_check':'candidate values compared to the documented contiguous reservation bounds only; Stage 5 stream rows were not read',
      'rng':{'bit_generator':'Stim per-stream integer seeds; benchmark timing bootstrap uses NumPy PCG64',
             'benchmark_namespace_start':BASE,'benchmark_namespace_end':BASE+40}}
    TARGET.write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','benchmark_streams':len(streams),
      'historical_values_screened':len(recovered),'historical_collisions':len(collisions),
      'stage5_reserved_range_collisions':len(stage5_collisions),
      'sealed_stage5_stream_rows_read':False},indent=2))
if __name__=='__main__': main()
