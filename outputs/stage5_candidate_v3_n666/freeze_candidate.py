from __future__ import annotations
import hashlib,json,os
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
FILES=[
 'outputs/stage5_candidate_v3_n666/STAGE5_V3_CANDIDATE_PROTOCOL.md',
 'outputs/stage5_candidate_v3_n666/STAGE5_V3_CANDIDATE_CONFIG.json',
 'outputs/stage5_candidate_v3_n666/STAGE5_V3_SEED_INVENTORY.json',
 'outputs/stage5_candidate_v3_n666/CALIBRATED_CRITICALS_N666.json',
 'outputs/stage5_candidate_v3_n666/FROZEN_PROFILE_ESTIMATOR.json',
 'outputs/stage5_candidate_v3_n666/prepare_seed_inventory.py',
 'outputs/stage5_candidate_v3_n666/stage5_runner_candidate.py',
 'outputs/stage5_candidate_v3_n666/stage5_saved_array_audit_candidate.py',
 'outputs/stage5_candidate_v3_n666/stage5_statistics_candidate.py',
 'outputs/stage5_candidate_v3_n666/integrity.py',
 'outputs/stage5_candidate_v3_n666/tests/test_candidate_v3.py',
 'outputs/stage5_candidate_v3_n666/freeze_candidate.py',
 'outputs/phase3a_correlated_noise_preflight/simulator.py',
 'outputs/stage4_noise_adaptive_feasibility_v1/prototype.py',
 'outputs/stage5_preexecution_v1/STAGE5_V2_FREEZE.json',
 'outputs/stage4c_cnn_noise_estimation_v1/FREEZE.json',
 'outputs/stage5_design_validation_v2/DESIGN_VALIDATION_FREEZE.json',
 'outputs/stage5_design_validation_v2/DESIGN_SIMULATION_RESULTS.json',
]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
record={'status':'CANDIDATE_NOT_AUTHORIZED_TO_SAMPLE','stage5_evaluation_shots_generated':0,
 'sealed_historical_test_accessed':False,'sampling_authorized':False,
 'sha256':{rel:sha(ROOT/rel) for rel in FILES},
 'note':'Candidate runner/auditor frozen for code review only. The tested allocation failed the predeclared power gate.'}
path=HERE/'STAGE5_V3_CANDIDATE_FREEZE.json'; tmp=path.with_suffix('.json.tmp')
tmp.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8'); os.replace(tmp,path)
record['freeze_sha256']=sha(path)
print(json.dumps({'path':str(path),'freeze_sha256':record['freeze_sha256'],'files':len(FILES)},indent=2))
