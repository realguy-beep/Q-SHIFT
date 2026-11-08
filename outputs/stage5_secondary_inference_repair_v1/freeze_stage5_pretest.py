"""Create the prospective Stage 5 implementation freeze; never samples data."""
from __future__ import annotations
import hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
TARGET=HERE/'STAGE5_PRETEST_FREEZE.json'

FROZEN_PATHS=[
 'AGENTS.md',
 'outputs/stage5_preexecution_v1/STAGE5_V2_PROTOCOL.md',
 'outputs/stage5_preexecution_v1/STAGE5_V2_FREEZE.json',
 'outputs/stage5_design_validation_v3_n1210/DESIGN_VALIDATION_PROTOCOL.md',
 'outputs/stage5_design_validation_v3_n1210/DESIGN_VALIDATION_FREEZE.json',
 'outputs/stage5_design_validation_v3_n1210/DESIGN_CONFIG.json',
 'outputs/stage5_design_validation_v3_n1210/DESIGN_MC_RESULTS.json',
 'outputs/stage5_design_validation_v3_n1210/INDEPENDENT_AUDIT.json',
 'outputs/stage5_design_validation_v3_n1210/STATISTICAL_VALIDATION_REPORT.md',
 'outputs/stage5_design_validation_v3_n1210/READINESS_DECISION.md',
 'outputs/stage5_secondary_inference_repair_v1/STAGE5_REPAIR_PROTOCOL_AMENDMENT.md',
 'outputs/stage5_secondary_inference_repair_v1/PROSPECTIVE_METHOD.md',
 'outputs/stage5_secondary_inference_repair_v1/STATISTICAL_JUSTIFICATION.md',
 'outputs/stage5_secondary_inference_repair_v1/STAGE5_STATISTICAL_VALIDATION.md',
 'outputs/stage5_secondary_inference_repair_v1/REPRODUCE.md',
 'outputs/stage5_secondary_inference_repair_v1/STAGE5_REPAIR_CONFIG.json',
 'outputs/stage5_secondary_inference_repair_v1/DESIGN_CONFIG.json',
 'outputs/stage5_secondary_inference_repair_v1/DESIGN_FREEZE.json',
 'outputs/stage5_secondary_inference_repair_v1/STAGE5_SECONDARY_REPAIR_SEED_INVENTORY.json',
 'outputs/stage5_secondary_inference_repair_v1/STAGE5_SAMPLE_SEED_INVENTORY.json',
 'outputs/stage5_secondary_inference_repair_v1/FROZEN_PROFILE_ESTIMATOR.json',
 'outputs/stage5_secondary_inference_repair_v1/SIMULATION_RESULTS.json',
 'outputs/stage5_secondary_inference_repair_v1/SIMULATION_RESULTS_REANALYZED_V2.json',
 'outputs/stage5_secondary_inference_repair_v1/INDEPENDENT_AUDIT_V4.json',
 'outputs/stage5_secondary_inference_repair_v1/INDEPENDENT_REPORTING_AUDIT.json',
 'outputs/stage5_secondary_inference_repair_v1/INDEPENDENT_AUDIT_FAILURE_V1.md',
 'outputs/stage5_secondary_inference_repair_v1/INDEPENDENT_AUDIT_FAILURE_V2.md',
 'outputs/stage5_secondary_inference_repair_v1/INDEPENDENT_AUDIT_FAILURE_V3.md',
 'outputs/stage5_secondary_inference_repair_v1/stage5_secondary_stats.py',
 'outputs/stage5_secondary_inference_repair_v1/stage5_statistics_repaired.py',
 'outputs/stage5_secondary_inference_repair_v1/stage5_sampling_runner.py',
 'outputs/stage5_secondary_inference_repair_v1/stage5_saved_array_audit.py',
 'outputs/stage5_secondary_inference_repair_v1/audit_secondary_v4.py',
 'outputs/stage5_secondary_inference_repair_v1/audit_reporting_bounds.py',
 'outputs/stage5_secondary_inference_repair_v1/simulate_secondary.py',
 'outputs/stage5_secondary_inference_repair_v1/recompute_reporting.py',
 'outputs/stage5_secondary_inference_repair_v1/prepare_stage5_seed_inventory.py',
 'outputs/stage5_secondary_inference_repair_v1/prepare_seed_inventory.py',
 'outputs/stage5_secondary_inference_repair_v1/freeze_design.py',
 'outputs/stage5_secondary_inference_repair_v1/freeze_stage5_pretest.py',
 'outputs/stage5_secondary_inference_repair_v1/run_no_sampling_preflight.py',
 'outputs/stage5_secondary_inference_repair_v1/tests/test_secondary_stats.py',
 'outputs/stage5_secondary_inference_repair_v1/tests/test_stage5_repair_preflight.py',
 'outputs/phase3a_correlated_noise_preflight/simulator.py',
 'outputs/stage4_noise_adaptive_feasibility_v1/prototype.py',
]


def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()


def large_ints(x):
 if isinstance(x,bool): return
 if isinstance(x,int) and x>=1_000_000: yield x
 elif isinstance(x,list):
  for y in x: yield from large_ints(y)
 elif isinstance(x,dict):
  for y in x.values(): yield from large_ints(y)


def check_record(path, maps):
 record_path=ROOT/path
 record=json.loads(record_path.read_text(encoding='utf-8'))
 for field in maps:
  for rel,digest in record[field].items():
   candidate=ROOT/rel
   if not candidate.is_file(): candidate=record_path.parent/rel
   actual=sha(candidate)
   if actual!=digest: raise RuntimeError(f'historical freeze mismatch in {path}: {rel}')
 return record


def main():
 if TARGET.exists(): raise RuntimeError('refusing to overwrite pre-test freeze')
 v2=check_record(Path('outputs/stage5_preexecution_v1/STAGE5_V2_FREEZE.json'),['sha256'])
 primary=check_record(Path('outputs/stage5_design_validation_v3_n1210/DESIGN_VALIDATION_FREEZE.json'),
                      ['design_input_sha256','historical_evidence_sha256'])
 secondary=check_record(Path('outputs/stage5_secondary_inference_repair_v1/DESIGN_FREEZE.json'),
                        ['source_and_config_sha256','historical_metadata_sha256'])
 if sha(ROOT/'outputs/stage5_secondary_inference_repair_v1/STAGE5_SECONDARY_REPAIR_SEED_INVENTORY.json')!=secondary['seed_inventory_sha256']:
  raise RuntimeError('secondary design seed inventory freeze mismatch')
 primary_results=json.loads((ROOT/'outputs/stage5_design_validation_v3_n1210/DESIGN_MC_RESULTS.json').read_text(encoding='utf-8'))
 primary_audit=json.loads((ROOT/'outputs/stage5_design_validation_v3_n1210/INDEPENDENT_AUDIT.json').read_text(encoding='utf-8'))
 secondary_audit=json.loads((HERE/'INDEPENDENT_AUDIT_V4.json').read_text(encoding='utf-8'))
 interval_audit=json.loads((HERE/'INDEPENDENT_REPORTING_AUDIT.json').read_text(encoding='utf-8'))
 secondary_results=json.loads((HERE/'SIMULATION_RESULTS_REANALYZED_V2.json').read_text(encoding='utf-8'))
 config=json.loads((HERE/'STAGE5_REPAIR_CONFIG.json').read_text(encoding='utf-8'))
 inventory=json.loads((HERE/'STAGE5_SAMPLE_SEED_INVENTORY.json').read_text(encoding='utf-8'))
 if not primary_results['decision']['readiness_statistical_gates_pass'] or not primary_audit['all_replay_counts_match']:
  raise RuntimeError('historical primary Endpoint B gates or independent audit are not passing')
 if primary_results.get('stage5_evaluation_shots_generated')!=0 or primary_audit.get('sealed_historical_test_accessed') is not False:
  raise RuntimeError('primary design audit violates isolation boundary')
 if not secondary_results['gate_summary']['overall_secondary_method_pass'] or secondary_audit.get('all_counts_and_reference_fingerprints_exactly_match') is not True:
  raise RuntimeError('secondary method validation or independent replay failed')
 if secondary_audit['marginal_cells_replayed']!=192 or secondary_audit['complete_and_partial_fwer_cells_replayed']!=516 or secondary_audit['coverage_cells_replayed']!=12 or secondary_audit['power_cells_replayed']!=24:
  raise RuntimeError('secondary audit cell coverage is incomplete')
 if interval_audit.get('status')!='PASS': raise RuntimeError('independent Monte Carlo interval audit failed')
 if config['roots_per_condition']!=1210 or config['primary_inference']['null_boundary']!=-0.0002 or config['primary_inference']['planning_alternative']!=-0.0003:
  raise RuntimeError('candidate Stage 5 config changed the frozen primary design')
 if inventory.get('stage5_evaluation_shots_generated')!=0 or inventory.get('sealed_historical_test_accessed') is not False or inventory.get('collision_count')!=0 or inventory.get('stream_count')!=12100:
  raise RuntimeError('candidate sample-seed inventory violates its allocation/isolation claims')
 if len(inventory['streams'])!=12100 or len({int(x['seed']) for x in inventory['streams']})!=12100:
  raise RuntimeError('Stage 5 sample seed uniqueness failure')
 expected_seed=14_000_000_001
 for kind in ('calibration_detector_only','paired_evaluation_detector_observable'):
  for pi,p in enumerate((0.0,0.004,0.008,0.012,0.016)):
   for root in range(1210):
    # Check the serialized entry's identity and its documented sequential allocation.
    index=((0 if kind=='calibration_detector_only' else 6050)+pi*1210+root)
    row=inventory['streams'][index]
    if row['kind']!=kind or float(row['probability'])!=p or int(row['root'])!=root or int(row['seed'])!=expected_seed:
     raise RuntimeError(f'Stage 5 seed allocation formula mismatch at {kind}, p={p}, root={root}')
    expected_seed+=1
 used=set()
 for row in inventory['historical_sources_checked']:
  path=ROOT/row['path']
  if sha(path)!=row['sha256']: raise RuntimeError(f'historical seed source changed: {row["path"]}')
  used.update(large_ints(json.loads(path.read_text(encoding='utf-8'))))
 seeds={int(x['seed']) for x in inventory['streams']}
 if seeds & used: raise RuntimeError('Stage 5 sample seed collides with recoverable historical metadata')
 missing=[rel for rel in FROZEN_PATHS if not (ROOT/rel).is_file()]
 if missing: raise FileNotFoundError(missing)
 hashes={rel:sha(ROOT/rel) for rel in FROZEN_PATHS}
 out={
   'name':'Q-SHIFT Stage 5 secondary-inference repair and sampling implementation freeze v1',
   'created_utc':datetime.now(timezone.utc).isoformat(),
   'status':'PRETEST_FROZEN_NOT_AUTHORIZED',
   'supersedes':'No existing Stage 5 frozen protocol. The historical Stage 5 v2 protocol remains unchanged; this prospective amendment repairs only the secondary inference method.',
   'scope':'Stage 5 readiness and implementation only; no Stage 5 evaluation sampling authorization.',
   'primary_endpoint_unchanged':True,
   'stage5_evaluation_shots_generated':0,
   'sealed_historical_test_accessed':False,
   'website_worktree_modified':False,
   'historical_freezes_verified':{
     'stage5_v2_hashes':len(v2['sha256']),
     'n1210_design_input_and_historical_hashes':len(primary['design_input_sha256'])+len(primary['historical_evidence_sha256']),
     'secondary_repair_source_and_historical_hashes':len(secondary['source_and_config_sha256'])+len(secondary['historical_metadata_sha256']),
     'primary_independent_replay':True,
     'secondary_independent_replay_cells':744,
     'secondary_interval_audit':True
   },
   'allocation':{'roots_per_condition':1210,'conditions':5,'total_roots':6050,'calibration_shots':12100000,
                 'paired_evaluation_shots':15125000,'unique_shots':27225000},
   'seed_inventory':{'path':'outputs/stage5_secondary_inference_repair_v1/STAGE5_SAMPLE_SEED_INVENTORY.json',
                     'stream_count':12100,'distinct_recoverable_historical_integer_values_screened':inventory['distinct_recoverable_historical_integer_values_screened'],
                     'historical_metadata_sources_checked':len(inventory['historical_sources_checked']),'collisions':0},
   'sha256':hashes
 }
 tmp=TARGET.with_suffix('.json.tmp')
 tmp.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 os.replace(tmp,TARGET)
 print(json.dumps({'status':out['status'],'frozen_files':len(hashes),'stage5_evaluation_shots_generated':0,
                   'historical_freezes_verified':out['historical_freezes_verified']},indent=2))


if __name__=='__main__': main()
