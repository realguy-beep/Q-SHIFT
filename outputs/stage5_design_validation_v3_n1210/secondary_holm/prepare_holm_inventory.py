from __future__ import annotations
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]
CFG=json.loads((HERE/'SECONDARY_HOLM_CONFIG.json').read_text(encoding='utf-8'))
PARENT=json.loads((HERE.parent/'DESIGN_SEED_INVENTORY.json').read_text(encoding='utf-8'))

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def scan(x):
 if isinstance(x,bool): return
 if isinstance(x,int) and x>=1_000_000: yield x
 elif isinstance(x,list):
  for a in x: yield from scan(a)
 elif isinstance(x,dict):
  for a in x.values(): yield from scan(a)

sources=[]; historical=set()
# Recheck, not merely inherit, the exact explicit metadata allowlist used by the primary validation.
for record in PARENT['historical_sources_checked']:
 rel=record['path']; path=ROOT/rel
 if sha(path)!=record['sha256']: raise RuntimeError(f'historical metadata hash changed: {rel}')
 vals=list(scan(json.loads(path.read_text(encoding='utf-8')))); historical.update(vals)
 sources.append({'path':rel,'sha256':sha(path),'large_integer_values_screened':len(vals)})
for rel in [
 'outputs/stage5_design_validation_v3_n1210/DESIGN_SEED_INVENTORY.json',
 'outputs/stage5_design_validation_v3_n1210/DESIGN_MC_RESULTS.json',
 'outputs/stage5_candidate_v3_n666/STAGE5_V3_SEED_INVENTORY.json',
 'outputs/stage5_final_decision_v1/ALLOCATION_ESTIMATES.json']:
 path=ROOT/rel
 if not path.is_file(): raise FileNotFoundError(rel)
 vals=list(scan(json.loads(path.read_text(encoding='utf-8')))); historical.update(vals)
 sources.append({'path':rel,'sha256':sha(path),'large_integer_values_screened':len(vals)})
entries=[]; base=int(CFG['rng']['namespace_start'])
for s in CFG['scenario_families']: entries.append({'cell':s['name'],'seed':base+len(entries)})
seeds=[x['seed'] for x in entries]; collisions=sorted(set(seeds)&historical)
if collisions: raise RuntimeError(f'new Holm validation stream collision: {collisions[:20]}')
if len(seeds)!=len(set(seeds)): raise RuntimeError('duplicate new Holm validation seeds')
out={'purpose':'secondary Holm operating-characteristic validation only','stage5_evaluation_seeds_allocated':False,
 'stage5_shots_generated':0,'sealed_test_accessed':False,
 'historical_coverage':'Exact primary-design allowlist rehashed and rescanned, plus parent n=1210 design inventory/results and the n=666 candidate seed inventory; sealed data excluded and not opened.',
 'historical_sources_checked':sources,'distinct_recoverable_large_integers_screened':len(historical),
 'collision_count':0,'stream_count':len(entries),'streams':entries,
 'rng':{'bit_generator':'PCG64','namespace_start':base,'namespace_end':base+len(entries)-1}}
(HERE/'SECONDARY_HOLM_SEED_INVENTORY.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(f'PASS: {len(entries)} unique Holm-only streams; {len(historical)} large recoverable integers screened; zero collisions')
