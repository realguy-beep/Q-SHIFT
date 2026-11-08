from __future__ import annotations
import hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
paths=[]
for p in sorted(HERE.rglob('*')):
 if not p.is_file() or p.name=='EVIDENCE_MANIFEST.json' or '__pycache__' in p.parts or p.suffix=='.pyc' or p.name.endswith('.tmp'): continue
 paths.append(p)
historical=[
 'outputs/stage5_preexecution_v1/STAGE5_V2_FREEZE.json',
 'outputs/stage4c_cnn_noise_estimation_v1/FREEZE.json',
 'outputs/stage5_design_validation_v2/DESIGN_VALIDATION_FREEZE.json',
 'outputs/stage5_design_validation_v2/DESIGN_SIMULATION_RESULTS.json',
 'outputs/stage5_candidate_v3_n666/STAGE5_V3_CANDIDATE_FREEZE.json',
 'outputs/stage5_final_decision_v1/STAGE5_FINAL_DECISION_MEMO.md',
 'outputs/stage5_final_decision_v1/ALLOCATION_ESTIMATES.json'
]
files=[]
for p in paths:
 rel=p.relative_to(ROOT).as_posix()
 files.append({'path':rel,'bytes':p.stat().st_size,'sha256':sha(p)})
hist={rel:{'bytes':(ROOT/rel).stat().st_size,'sha256':sha(ROOT/rel)} for rel in historical}
head=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()
data={'manifest':'Stage 5 n=1210 design validation evidence manifest','created_before_commit':True,
 'baseline_repository_head':head,'design_package_sha256':files,'preserved_historical_hashes':hist,
 'stage5_evaluation_shots_generated':0,'sealed_historical_test_accessed':False,
 'stage4c_files_modified':False,'website_worktree_modified':False,
 'design_mc_cell_summaries':sum(1 for x in files if '/cells/' in x['path']),
 'large_raw_shot_arrays_included':False}
(HERE/'EVIDENCE_MANIFEST.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print(f"Manifested {len(files)} files; {sum(x['bytes'] for x in files)} bytes; base HEAD {head}")
