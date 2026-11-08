"""Read-only seed/budget preflight; deliberately excludes all Stage 5 paths."""
import hashlib,json
from pathlib import Path
OUT=Path(__file__).resolve().parent; ROOT=OUT.parents[1]
inv=json.loads((OUT/'PILOT2_SEED_INVENTORY.json').read_text(encoding='utf-8'))
cfg=json.loads((OUT/'PILOT2_CONFIG.json').read_text(encoding='utf-8'))
assert 'stage5' not in str(inv).lower() and 'sealed' not in str(inv).lower()
seeds=[int(x['seed']) for x in inv['samples']]
assert len(seeds)==len(set(seeds))==inv['sampler_seed_count']
assert not inv['collisions']
assert sum(int(x['shots']) for x in inv['samples'])==cfg['allocation']['planned_unique_shots']==298500
assert cfg['allocation']['planned_unique_shots']<=cfg['allocation']['unique_shot_budget']==300000
assert cfg['allocation']['evaluation_replicates']==20 and len(cfg['allocation']['evaluation_scenarios'])==8
for h in inv['historical_inventories_checked']:
    p=ROOT/h['path']; assert p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==h['sha256']
print(json.dumps({'status':'pass','sampler_seeds':len(seeds),'seed_min':min(seeds),'seed_max':max(seeds),
 'historical_seed_values_checked':inv['historical_unique_seed_values_checked'],'collisions':0,
 'planned_unique_shots':sum(int(x['shots']) for x in inv['samples']),
 'historical_inventories':[x['path'] for x in inv['historical_inventories_checked']]},indent=2))
