from __future__ import annotations
import hashlib,json
from pathlib import Path

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
CONFIG=json.loads((HERE/'STAGE5_V3_CANDIDATE_CONFIG.json').read_text(encoding='utf-8'))
SAFE=[
 'outputs/stage4_noise_adaptive_development_v1/seed_inventory.json',
 'outputs/stage4_noise_adaptive_development_v1/seed_audit.json',
 'outputs/stage4_noise_adaptive_development_v1/additional_development_seed_audit.json',
 'outputs/stage4c_cnn_noise_estimation_v1/seed_inventory.json',
 'outputs/stage4c_cnn_noise_estimation_v1/seed_audit.json',
 'outputs/stage5_preexecution_v1/seed_inventory.json',
 'outputs/stage5_preexecution_v1/STAGE5_V2_CONFIG.json',
 'outputs/stage5_design_validation_v1/VALIDATION_SEED_INVENTORY.json',
 'outputs/stage5_design_validation_v2/DESIGN_SEED_INVENTORY.json',
 'outputs/stage5_design_validation_v2/DESIGN_SIMULATION_RESULTS.json',
 'outputs/stage5_endpoint_review_v1/POWER_SENSITIVITY.json',
]
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def ints(x):
 if isinstance(x,bool): return
 if isinstance(x,int) and x>=1_000_000: yield x
 elif isinstance(x,list):
  for y in x: yield from ints(y)
 elif isinstance(x,dict):
  for y in x.values(): yield from ints(y)

used=set(); sources=[]
for rel in SAFE:
 p=ROOT/rel
 if not p.is_file(): raise FileNotFoundError(rel)
 values=list(ints(json.loads(p.read_text(encoding='utf-8')))); used.update(values)
 sources.append({'path':rel,'sha256':sha(p),'integer_values_ge_1m_scanned':len(values)})
base=9_100_000_001; streams=[]
for kind in ['calibration_detector_only','paired_evaluation_detector_observable']:
 for p in CONFIG['probabilities']:
  for root in range(CONFIG['roots_per_condition']):
   streams.append({'kind':kind,'probability':float(p),'root':root,'seed':base+len(streams)})
seeds=[x['seed'] for x in streams]
collisions=sorted(set(seeds)&used)
if collisions: raise RuntimeError(f'candidate Stage 5 seed collision: {collisions[:10]}')
if len(seeds)!=6660 or len(set(seeds))!=len(seeds): raise RuntimeError('candidate inventory cardinality/uniqueness failed')
inv={'purpose':'prospective Stage 5 v3 candidate allocation only; no samples generated',
 'stage5_evaluation_shots_generated':0,'sealed_historical_test_accessed':False,
 'roots_per_condition':666,'probabilities':CONFIG['probabilities'],'recoverable_historical_integer_values_scanned':len(used),
 'historical_sources_checked':sources,'collision_count':0,'seed_stream_count':len(streams),
 'stream_namespace':{'start':base,'end':base+len(streams)-1},'streams':streams,
 'coverage_limitation':'No sealed historical test arrays or independent-confirmation directory were opened; undocumented RNG use remains unknowable.'}
tmp=HERE/'STAGE5_V3_SEED_INVENTORY.json.tmp'; tmp.write_text(json.dumps(inv,indent=2)+'\n',encoding='utf-8'); tmp.replace(HERE/'STAGE5_V3_SEED_INVENTORY.json')
print(f'PASS: {len(streams)} candidate streams, {len(used)} recoverable historical integers screened, 0 collisions')
