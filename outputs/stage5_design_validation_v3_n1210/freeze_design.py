"""Freeze the prospective design simulation inputs before Monte Carlo."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FILES=[
 'outputs/stage5_design_validation_v3_n1210/DESIGN_VALIDATION_PROTOCOL.md',
 'outputs/stage5_design_validation_v3_n1210/DESIGN_CONFIG.json',
 'outputs/stage5_design_validation_v3_n1210/DESIGN_SEED_INVENTORY.json',
 'outputs/stage5_design_validation_v3_n1210/prepare_inventory.py',
 'outputs/stage5_design_validation_v3_n1210/freeze_design.py',
 'outputs/stage5_design_validation_v3_n1210/design_mc.py',
 'outputs/stage5_design_validation_v3_n1210/independent_audit.py',
 'outputs/stage5_design_validation_v3_n1210/tests/test_design_v3.py',
]
HIST=[
 'outputs/stage5_preexecution_v1/STAGE5_V2_FREEZE.json',
 'outputs/stage4c_cnn_noise_estimation_v1/FREEZE.json',
 'outputs/stage5_design_validation_v2/DESIGN_VALIDATION_FREEZE.json',
 'outputs/stage5_design_validation_v2/DESIGN_SIMULATION_RESULTS.json',
 'outputs/stage5_final_decision_v1/STAGE5_FINAL_DECISION_MEMO.md',
 'outputs/stage5_final_decision_v1/ALLOCATION_ESTIMATES.json',
]
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
doc={'name':'Stage 5 n=1210 design-validation freeze v1','created_before_monte_carlo':True,
 'scope':'synthetic statistical root-effect design simulations only; no Stage 5 sampling',
 'stage5_evaluation_shots_generated':0,'sealed_historical_test_accessed':False,
 'sampling_authorized':False,
 'design_input_sha256':{rel:sha(ROOT/rel) for rel in FILES},
 'historical_evidence_sha256':{rel:sha(ROOT/rel) for rel in HIST}}
path=HERE/'DESIGN_VALIDATION_FREEZE.json'
path.write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
print('Froze',len(FILES),'design inputs; historical hashes',len(HIST))
