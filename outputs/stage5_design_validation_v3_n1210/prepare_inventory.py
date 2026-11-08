"""Create a screened RNG inventory for synthetic design simulations only."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CFG=json.loads((HERE/'DESIGN_CONFIG.json').read_text(encoding='utf-8'))

# Explicit metadata-only allowlist. No Stage 5 evaluation archives, sealed
# directories, prediction arrays, or labels are opened by this script.
SOURCES=[
 'outputs/stage4_noise_adaptive_development_v1/seed_inventory.json',
 'outputs/stage4_noise_adaptive_development_v1/seed_audit.json',
 'outputs/stage4_noise_adaptive_development_v1/additional_development_seed_audit.json',
 'outputs/stage4c_cnn_noise_estimation_v1/seed_inventory.json',
 'outputs/stage4c_cnn_noise_estimation_v1/seed_audit.json',
 'outputs/stage5_preexecution_v1/seed_inventory.json',
 'outputs/stage5_preexecution_v1/STAGE5_V2_CONFIG.json',
 'outputs/stage5_design_validation_v1/VALIDATION_SEED_INVENTORY.json',
 'outputs/stage5_design_validation_v1/DESIGN_SIMULATION_CONFIG.json',
 'outputs/stage5_design_validation_v1/DESIGN_SIMULATION_RESULTS.json',
 'outputs/stage5_design_validation_v1/benchmark_run/ROOT_ARCHIVE_MANIFEST.json',
 'outputs/stage5_endpoint_review_v1/POWER_SENSITIVITY.json',
 'outputs/stage5_design_validation_v2/DESIGN_SEED_INVENTORY.json',
 'outputs/stage5_design_validation_v2/DESIGN_SIMULATION_CONFIG.json',
 'outputs/stage5_design_validation_v2/DESIGN_SIMULATION_RESULTS.json',
 'outputs/stage5_candidate_v3_n666/STAGE5_V3_SEED_INVENTORY.json',
 'outputs/stage5_final_decision_v1/ALLOCATION_ESTIMATES.json',
]

def sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

def integers(x,path='$'):
 if isinstance(x,bool): return
 if isinstance(x,int):
  if x>=1_000_000: yield (path,x)
 elif isinstance(x,list):
  for i,v in enumerate(x): yield from integers(v,f'{path}[{i}]')
 elif isinstance(x,dict):
  for k,v in x.items(): yield from integers(v,f'{path}.{k}')

historical=set(); records=[]
for rel in SOURCES:
 p=ROOT/rel
 if not p.is_file(): raise FileNotFoundError(f'recoverable metadata source missing: {rel}')
 data=json.loads(p.read_text(encoding='utf-8'))
 vals=list(integers(data))
 historical.update(v for _,v in vals)
 records.append({'path':rel,'sha256':sha(p),'large_integer_values_screened':len(vals),
                 'coverage_note':'Explicit nonsealed metadata file; raw/evaluation archives are not opened.'})

entries=[]; base=int(CFG['rng']['design_seed_namespace_start'])
def add(stream,cell): entries.append({'stream':stream,'cell':cell,'seed':base+len(entries)})
n=int(CFG['allocation_roots_per_stratum'])
for s in CFG['null_scenarios']:
 k=f'n{n}/{s["name"]}'; add('primary_null_calibration',k); add('primary_null_validation',k)
for s in CFG['power_scenarios']:
 for e in CFG['power_effects']: add('primary_power',f'n{n}/{s["name"]}/delta{e}')
for s in CFG['p0_no_harm']['scenarios']:
 k=f'n{n}/{s["name"]}'; add('p0_null_calibration',k); add('p0_null_validation',k)
 for e in CFG['p0_no_harm']['power_true_effects']: add('p0_safety_power',f'n{n}/{s["name"]}/effect{e}')
for fam in ['normal','student_t5','student_t3','lognormal_sigma1','zero_inflated65_normal','tied_asymmetric65']:
 add('independent_generator_check',fam)
add('independent_statistic_fixture','fixed-small-matrix')
seeds=[x['seed'] for x in entries]
collisions=sorted(set(seeds)&historical)
if collisions: raise RuntimeError(f'proposed design seeds collide with recoverable historical integer values: {collisions[:20]}')
if len(seeds)!=len(set(seeds)): raise RuntimeError('design RNG seeds are not unique')
out={
 'purpose':'Stage 5 statistical design Monte Carlo only; no Stage 5 simulator or evaluation samples',
 'stage5_evaluation_seeds_allocated':False,'stage5_evaluation_shots_generated':0,
 'sealed_historical_test_accessed':False,
 'historical_coverage':'Explicit allowlist of recoverable nonsealed seed/config/result metadata. Undocumented RNG uses and sealed records are outside coverage; no sealed data were enumerated or opened.',
 'historical_sources_checked':records,'recoverable_large_integer_values_screened':len(historical),
 'collision_count':0,'rng_stream_count':len(entries),'rng_streams':entries,
 'rng':{'bit_generator':'PCG64','namespace_start':base,'namespace_end':base+len(entries)-1}}
(HERE/'DESIGN_SEED_INVENTORY.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(f'PASS: {len(entries)} unique design-only streams; {len(historical)} distinct recoverable large integers screened; zero collisions; no sampling')
