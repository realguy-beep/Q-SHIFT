"""Freeze the disposable benchmark sources before its first Stim sample."""
from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
TARGET=HERE/'BENCHMARK_FREEZE.json'
FILES=[
 'AGENTS.md',
 'outputs/stage5_secondary_inference_repair_v1/STAGE5_REPAIR_PROTOCOL_AMENDMENT_V2.md',
 'outputs/stage5_secondary_inference_repair_v1/STAGE5_READINESS_REPORT.md',
 'outputs/stage5_secondary_inference_repair_v1/STAGE5_STATISTICAL_VALIDATION.md',
 'outputs/stage5_secondary_inference_repair_v1/STAGE5_SECONDARY_REPAIR_SEED_INVENTORY.json',
 'outputs/stage5_execution_preflight_v1/BENCHMARK_PROTOCOL.md',
 'outputs/stage5_execution_preflight_v1/benchmark_config.json',
 'outputs/stage5_execution_preflight_v1/BENCHMARK_SEED_INVENTORY.json',
 'outputs/stage5_execution_preflight_v1/prepare_benchmark_inventory.py',
 'outputs/stage5_execution_preflight_v1/benchmark_runner.py',
 'outputs/stage5_execution_preflight_v1/audit_benchmark.py',
 'outputs/stage5_execution_preflight_v1/freeze_benchmark.py',
 'outputs/stage5_secondary_inference_repair_v1/STAGE5_PRETEST_FREEZE_V2.json',
 'outputs/stage5_design_validation_v3_n1210/DESIGN_VALIDATION_FREEZE.json',
 'outputs/stage5_design_validation_v3_n1210/STATISTICAL_VALIDATION_REPORT.md',
 'outputs/stage5_secondary_inference_repair_v1/stage5_secondary_stats.py',
 'outputs/stage5_secondary_inference_repair_v1/STAGE5_REPAIR_CONFIG.json',
 'outputs/stage5_secondary_inference_repair_v1/FROZEN_PROFILE_ESTIMATOR.json',
 'outputs/stage5_secondary_inference_repair_v1/stage5_sampling_runner_v2.py',
 'outputs/stage5_secondary_inference_repair_v1/stage5_statistics_repaired.py',
 'outputs/stage4_noise_adaptive_feasibility_v1/prototype.py',
 'outputs/phase3a_correlated_noise_preflight/simulator.py',
]
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def main():
 if TARGET.exists(): raise RuntimeError('refusing to overwrite benchmark freeze')
 missing=[x for x in FILES if not (ROOT/x).is_file()]
 if missing: raise FileNotFoundError(missing)
 data={'name':'Q-SHIFT disposable Stage 5 execution-path benchmark v1',
       'created_before_sampling':True,'benchmark_samples_generated':0,
       'stage5_evaluation_samples_generated':0,'sealed_historical_test_accessed':False,
       'main_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
       'shot_budget':90000,'root_count':20,'source_file_count':len(FILES),
       'sha256':{rel:sha(ROOT/rel) for rel in FILES}}
 TARGET.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'status':'FROZEN_BEFORE_SAMPLING','source_files':len(FILES),
                   'main_head':data['main_head'],'benchmark_samples_generated':0},indent=2))
if __name__=='__main__': main()
