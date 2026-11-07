"""Create/verify the prospective no-sampling code and protocol freeze."""
import argparse, hashlib, json
from pathlib import Path

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]; DEST=HERE/'STAGE5_V2_FREEZE.json'
FILES=[
 'AGENTS.md',
 'outputs/stage5_preexecution_v1/STAGE5_V2_PROTOCOL.md',
 'outputs/stage5_preexecution_v1/STAGE5_READINESS_DECISION.md',
 'outputs/stage5_preexecution_v1/STAGE5_V2_CONFIG.json',
 'outputs/stage5_preexecution_v1/freeze_stage5.py',
 'outputs/stage5_preexecution_v1/__init__.py',
 'outputs/stage5_preexecution_v1/seed_inventory.json',
 'outputs/stage5_preexecution_v1/FROZEN_PROFILE_ESTIMATOR.json',
 'outputs/stage5_preexecution_v1/PROFILE_PROVENANCE.json',
 'outputs/stage5_preexecution_v1/STAGE5_STATISTICAL_POWER_REVIEW.md',
 'outputs/stage5_preexecution_v1/STAGE5_REPRODUCE.md',
 'outputs/stage5_preexecution_v1/NO_SHOT_PREFLIGHT.json',
 'outputs/stage5_preexecution_v1/POWER_RECOMPUTATION.json',
 'outputs/stage5_preexecution_v1/stage5_runner.py',
 'outputs/stage5_preexecution_v1/stage5_saved_array_audit.py',
 'outputs/stage5_preexecution_v1/stage5_statistics.py',
 'outputs/stage5_preexecution_v1/stage5_preflight.py',
 'outputs/stage5_preexecution_v1/review_power.py',
 'outputs/stage5_preexecution_v1/tests/test_stage5_preflight.py',
 'outputs/stage5_independent_confirmation/STAGE5_CANDIDATE_FREEZE.json',
 'outputs/stage5_independent_confirmation/STAGE5_PROTOCOL_CANDIDATE.md',
 'outputs/stage5_independent_confirmation/STAGE5_CONFIG.json',
 'outputs/stage5_independent_confirmation/seed_audit.json',
 'outputs/stage5_independent_confirmation/PROFILE_PROVENANCE.json',
 'outputs/stage4c_cnn_noise_estimation_v1/FREEZE.json',
 'outputs/stage4c_cnn_noise_estimation_v1/EVIDENCE_MANIFEST.json',
 'outputs/phase3a_correlated_noise_preflight/simulator.py',
 'outputs/phase2b_pauli_bias/noise_model.py',
 'outputs/stage4_noise_adaptive_feasibility_v1/prototype.py',
 'outputs/stage4c_cnn_noise_estimation_v1/experiment.py',
 'outputs/stage4c_cnn_noise_estimation_v1/audit_results.py',
]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def expected():
 missing=[x for x in FILES if not (ROOT/x).is_file()]
 if missing: raise FileNotFoundError(f'freeze inputs missing: {missing}')
 return {'status':'PRETEST_IMPLEMENTATION_HASHED_NO_SAMPLING_AUTHORIZATION',
   'sampling_started':False,'independent_test_accessed':False,'independent_test_enumerated':False,
   'planned_unique_shots':2250000,'prospective_seed_count':1002,
   'sha256':{x:sha(ROOT/x) for x in FILES}}

def verify():
 record=json.loads(DEST.read_text(encoding='utf-8')); now=expected()
 if record.get('sha256')!=now['sha256']: raise SystemExit('Stage 5 pretest freeze hash mismatch')
 print(f"PASS: {len(now['sha256'])} frozen protocol/source inputs; sampling not authorized")

if __name__=='__main__':
 p=argparse.ArgumentParser(); p.add_argument('--create',action='store_true'); a=p.parse_args()
 if a.create:
  if DEST.exists(): raise SystemExit('freeze exists; refusing to overwrite')
  DEST.write_text(json.dumps(expected(),indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(f'created {DEST}')
 else: verify()
