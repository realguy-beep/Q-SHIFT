"""Create fresh prospective n=1210 Stage 5 sample streams; does not sample them."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
TARGET=HERE/'STAGE5_SAMPLE_SEED_INVENTORY.json'
BASE=14_000_000_001
PROBS=(0.0,0.004,0.008,0.012,0.016)
NROOTS=1210

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
    if TARGET.exists(): raise RuntimeError('refusing to overwrite Stage 5 sample seed inventory')
    prior=json.loads((HERE/'STAGE5_SECONDARY_REPAIR_SEED_INVENTORY.json').read_text(encoding='utf-8'))
    expected={x['path']:x['sha256'] for x in prior['historical_sources_checked']}
    paths=list(expected)
    paths += [
        'outputs/stage5_design_validation_v3_n1210/secondary_holm/SECONDARY_HOLM_SEED_INVENTORY.json',
        'outputs/stage5_design_validation_v3_n1210/secondary_holm/SECONDARY_HOLM_RESULTS_REPAIR_V1.json',
        'outputs/stage5_design_validation_v3_n1210/DESIGN_SEED_INVENTORY.json',
        'outputs/stage5_design_validation_v3_n1210/DESIGN_MC_RESULTS.json',
        'outputs/stage5_candidate_v3_n666/STAGE5_V3_SEED_INVENTORY.json',
        'outputs/stage5_preexecution_v1/seed_inventory.json',
        'outputs/stage5_secondary_inference_repair_v1/STAGE5_SECONDARY_REPAIR_SEED_INVENTORY.json',
        'outputs/stage5_secondary_inference_repair_v1/DESIGN_CONFIG.json'
    ]
    paths=list(dict.fromkeys(paths))
    used=set(); checked=[]
    for rel in paths:
        path=ROOT/rel
        if not path.is_file(): raise FileNotFoundError(rel)
        actual=sha(path)
        if rel in expected and actual!=expected[rel]: raise RuntimeError(f'historical hash changed: {rel}')
        values=list(large_ints(json.loads(path.read_text(encoding='utf-8'))))
        used.update(values)
        checked.append({'path':rel,'sha256':actual,'integer_values_ge_1m_screened':len(values),
                        'previous_seed_audit_hash_reverified':rel in expected})
    streams=[]
    for kind in ('calibration_detector_only','paired_evaluation_detector_observable'):
        for p in PROBS:
            for root in range(NROOTS):
                streams.append({'kind':kind,'probability':p,'root':root,'seed':BASE+len(streams)})
    seeds=[x['seed'] for x in streams]
    collision=sorted(set(seeds)&used)
    if collision: raise RuntimeError(f'Stage 5 sample-seed collision: {collision[:20]}')
    if len(streams)!=12100 or len(set(seeds))!=12100: raise AssertionError('sample stream coverage/uniqueness failed')
    record={'purpose':'prospective Stage 5 n=1210 calibration/evaluation streams only; no samples generated',
      'stage5_evaluation_shots_generated':0,'sealed_historical_test_accessed':False,
      'roots_per_condition':NROOTS,'probabilities':list(PROBS),'stream_count':len(streams),
      'distinct_recoverable_historical_integer_values_screened':len(used),'historical_sources_checked':checked,
      'collision_count':0,'streams':streams,
      'rng':{'bit_generator':'PCG64','namespace_start':BASE,'namespace_end':BASE+len(streams)-1},
      'coverage_limitation':'Only explicit recoverable nonsealed metadata was screened. Undocumented historical RNG use cannot be ruled out; no sealed arrays were listed or opened.'}
    TARGET.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(f'PASS: {len(streams)} unique Stage 5 sample streams, {len(used)} historical integers scanned, zero collisions; no samples generated')

if __name__=='__main__': main()
