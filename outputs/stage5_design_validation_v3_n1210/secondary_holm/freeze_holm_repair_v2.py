from __future__ import annotations
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]
FILES=[
 'outputs/stage5_design_validation_v3_n1210/secondary_holm/SECONDARY_HOLM_VALIDATION_PLAN.md',
 'outputs/stage5_design_validation_v3_n1210/secondary_holm/SECONDARY_HOLM_CONFIG.json',
 'outputs/stage5_design_validation_v3_n1210/secondary_holm/SECONDARY_HOLM_SEED_INVENTORY.json',
 'outputs/stage5_design_validation_v3_n1210/secondary_holm/validate_holm.py',
 'outputs/stage5_design_validation_v3_n1210/secondary_holm/audit_holm.py',
 'outputs/stage5_design_validation_v3_n1210/secondary_holm/validate_holm_repair_v1.py',
 'outputs/stage5_design_validation_v3_n1210/secondary_holm/audit_holm_repair_v1.py',
 'outputs/stage5_design_validation_v3_n1210/secondary_holm/freeze_holm_repair_v1.py',
 'outputs/stage5_design_validation_v3_n1210/secondary_holm/tests/test_holm.py',
 'outputs/stage5_design_validation_v3_n1210/secondary_holm/tests/test_holm_repair_v1.py',
 'outputs/stage5_design_validation_v3_n1210/secondary_holm/SECONDARY_HOLM_SERIALIZATION_FAILURE.md']
PARENTS=[
 'outputs/stage5_design_validation_v3_n1210/secondary_holm/SECONDARY_HOLM_FREEZE.json',
 'outputs/stage5_design_validation_v3_n1210/DESIGN_VALIDATION_FREEZE.json',
 'outputs/stage5_design_validation_v3_n1210/DESIGN_MC_RESULTS.json',
 'outputs/stage5_design_validation_v3_n1210/INDEPENDENT_AUDIT.json',
 'outputs/stage5_candidate_v3_n666/stage5_statistics_candidate.py',
 'outputs/stage5_candidate_v3_n666/STAGE5_V3_CANDIDATE_FREEZE.json',
 'outputs/stage5_preexecution_v1/STAGE5_V2_FREEZE.json',
 'outputs/stage4c_cnn_noise_estimation_v1/FREEZE.json']
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
doc={'name':'Stage 5 n=1210 secondary Holm serialization-repair freeze v1',
 'created_before_deterministic_replay':True,'change_scope':'JSON serialization only; same frozen seeds and statistical procedure',
 'stage5_shots_generated':0,'sealed_test_accessed':False,
 'repair_design_input_sha256':{rel:sha(ROOT/rel) for rel in FILES},
 'parent_and_failure_evidence_sha256':{rel:sha(ROOT/rel) for rel in PARENTS}}
(HERE/'SECONDARY_HOLM_REPAIR_FREEZE.json').write_text(json.dumps(doc,indent=2)+'\n',encoding='utf-8')
print(f'Froze {len(FILES)} repair inputs and {len(PARENTS)} parent/failure records')
