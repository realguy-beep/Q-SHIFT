from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
TARGET=HERE/'STAGE5_REPAIR_EVIDENCE_MANIFEST_V2.json'

def sha(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

def main():
 if TARGET.exists(): raise RuntimeError('refusing to overwrite v2 evidence manifest')
 if (HERE/'run').exists(): raise RuntimeError('unexpected Stage 5 run directory exists')
 if list(HERE.rglob('*.npz')): raise RuntimeError('unexpected shot archive exists in repair package')
 freeze=json.loads((HERE/'STAGE5_PRETEST_FREEZE_V2.json').read_text(encoding='utf-8'))
 preflight=json.loads((HERE/'STAGE5_NO_SAMPLING_PREFLIGHT_V2.json').read_text(encoding='utf-8'))
 audit=json.loads((HERE/'INDEPENDENT_AUDIT_V4.json').read_text(encoding='utf-8'))
 interval=json.loads((HERE/'INDEPENDENT_REPORTING_AUDIT.json').read_text(encoding='utf-8'))
 if freeze.get('status')!='PRETEST_FROZEN_NOT_AUTHORIZED' or freeze.get('stage5_evaluation_shots_generated')!=0:
  raise RuntimeError('freeze has incorrect authorization/sampling status')
 if preflight.get('status')!='PASS_NO_SAMPLING' or preflight.get('stage5_evaluation_shots_generated')!=0 or preflight.get('sampling_invoked') is not False:
  raise RuntimeError('no-sampling preflight did not pass')
 if audit.get('all_counts_and_reference_fingerprints_exactly_match') is not True or audit.get('stage5_evaluation_shots_generated')!=0 or audit.get('sealed_test_accessed') is not False:
  raise RuntimeError('independent simulation audit boundary or result failed')
 if interval.get('status')!='PASS' or not interval['gate_summary']['overall_secondary_method_pass']:
  raise RuntimeError('independent Wilson audit failed')
 paths=sorted(p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p!=TARGET)
 files={p.relative_to(HERE).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in paths}
 body={
  'created_utc':datetime.now(timezone.utc).isoformat(),
  'decision':'GO_READINESS_ONLY_SAMPLING_NOT_AUTHORIZED',
  'repository_base_commit':'0146f756d5d419b0f5afa6d99c7a3dfac38361eb',
  'branch':'main',
  'stage5_evaluation_shots_generated':0,
  'sealed_historical_test_accessed':False,
  'website_worktree_modified':False,
  'active_freeze':'STAGE5_PRETEST_FREEZE_V2.json',
  'active_freeze_sha256':sha(HERE/'STAGE5_PRETEST_FREEZE_V2.json'),
  'no_sampling_preflight':'STAGE5_NO_SAMPLING_PREFLIGHT_V2.json',
  'no_sampling_preflight_sha256':sha(HERE/'STAGE5_NO_SAMPLING_PREFLIGHT_V2.json'),
  'independent_audit':'INDEPENDENT_AUDIT_V4.json',
  'reporting_audit':'INDEPENDENT_REPORTING_AUDIT.json',
  'unit_test_commands':[
   'python -m unittest discover -s outputs/stage5_secondary_inference_repair_v1/tests -v',
   'python -m unittest outputs.stage5_secondary_inference_repair_v1.tests.test_stage5_repair_preflight_v2 -v'
  ],
  'unit_test_results':{'combined_discovery':{'passed':19,'failed':0},'v2_repeat':{'passed':4,'failed':0}},
  'active_freeze_file_count':len(freeze['sha256']),
  'no_sampling_preflight_runtime_seconds':preflight['preflight_runtime_seconds'],
  'secondary_validation_cells':744,
  'secondary_validation_independent_replay':'PASS',
  'secondary_interval_independent_recompute':'PASS',
  'files':files
 }
 tmp=TARGET.with_suffix('.json.tmp')
 tmp.write_text(json.dumps(body,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 tmp.replace(TARGET)
 print(json.dumps({'status':body['decision'],'files_hashed':len(files),'manifest_sha256':sha(TARGET),
                   'stage5_evaluation_shots_generated':0},indent=2))

if __name__=='__main__': main()
