from __future__ import annotations
import hashlib,json
from pathlib import Path

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

sim=HERE/'DESIGN_SIMULATION_RESULTS.json'
candidate=ROOT/'outputs/stage5_candidate_v3_n666/STAGE5_V3_CANDIDATE_FREEZE.json'
v2=ROOT/'outputs/stage5_preexecution_v1/STAGE5_V2_FREEZE.json'
stage4c=ROOT/'outputs/stage4c_cnn_noise_estimation_v1/FREEZE.json'
finalization={
 'design_simulation_status':'completed',
 'statistical_design_replicates':{
  'primary_null_calibration':len(json.loads(sim.read_text(encoding='utf-8'))['critical_values_by_allocation'])*len(json.loads(sim.read_text(encoding='utf-8'))['critical_values_by_allocation'][0]['calibration_cells'])*100000,
  'primary_null_validation':len(json.loads(sim.read_text(encoding='utf-8'))['primary_null_validation'])*100000,
  'primary_power':len(json.loads(sim.read_text(encoding='utf-8'))['primary_power'])*100000,
  'p0_null_calibration':len(json.loads(sim.read_text(encoding='utf-8'))['p0_calibration'])*len(json.loads(sim.read_text(encoding='utf-8'))['p0_calibration'][0]['scenario_calibration'])*100000,
  'p0_null_validation':len(json.loads(sim.read_text(encoding='utf-8'))['p0_null_validation'])*100000,
  'p0_safety_power':len(json.loads(sim.read_text(encoding='utf-8'))['p0_safety_power'])*100000,
 },
 'stage5_evaluation_shots_generated':0,'sealed_historical_test_accessed':False,
 'design_simulation_results_sha256':sha(sim),
 'design_validation_freeze_sha256':sha(HERE/'DESIGN_VALIDATION_FREEZE.json'),
 'candidate_n666_freeze_sha256':sha(candidate),
 'historical_stage5_v2_freeze_sha256':sha(v2),
 'historical_stage4c_freeze_sha256':sha(stage4c),
 'note':'The full design-simulation process wall time is recorded in DESIGN_SIMULATION_RESULTS.json. Peak RSS for that process was not captured; separate max-batch memory probe is recorded.'
}
(HERE/'RUN_FINALIZATION.json').write_text(json.dumps(finalization,indent=2)+'\n',encoding='utf-8')

files=[]
for folder in [HERE,ROOT/'outputs/stage5_candidate_v3_n666']:
 for p in sorted(folder.rglob('*')):
  if not p.is_file() or '__pycache__' in p.parts or p.suffix in {'.pyc','.tmp'} or p.name=='EVIDENCE_MANIFEST.json': continue
  rel=p.relative_to(ROOT).as_posix()
  files.append({'path':rel,'bytes':p.stat().st_size,'sha256':sha(p)})
if any(p['path'].lower().endswith(('.npz','.pt','.pth','.ckpt')) for p in files): raise RuntimeError('raw dataset/checkpoint unexpectedly in evidence package')
manifest={
 'study':'Stage 5 statistical design validation v2 and review-only v3 candidate',
 'stage5_sampling_performed':False,'stage5_shots':0,'sealed_historical_test_access':False,
 'design_simulation_freeze_sha256':sha(HERE/'DESIGN_VALIDATION_FREEZE.json'),
 'candidate_runner_freeze_sha256':sha(candidate),
 'historical_freeze_hashes':{'stage5_v2':sha(v2),'stage4c':sha(stage4c)},
 'disposable_pipeline_benchmark':'outputs/stage5_design_validation_v1/benchmark_run/ROOT_ARCHIVE_MANIFEST.json; 50 development-only roots/225,000 shots; raw NPZ remain ignored/local',
 'files':files,'manifest_self_hash':'omitted by design'
}
(HERE/'EVIDENCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(f"Wrote finalization and manifest for {len(files)} files; no Stage 5 sample arrays included")
