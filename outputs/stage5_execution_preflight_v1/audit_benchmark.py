"""Independent rescore of the disposable Stage 5 execution-path benchmark."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RUN=HERE/'benchmark_run'
STAGE5=ROOT/'outputs/stage5_secondary_inference_repair_v1'
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(STAGE5))
from outputs.phase3a_correlated_noise_preflight.simulator import build_spatial_burst_circuit
from outputs.stage4_noise_adaptive_feasibility_v1.prototype import DetectorProfileEstimator, decode_prediction, logical_error_mask, build_decoder

PROBS=(0.0,0.004,0.008,0.012,0.016); ROOTS=4; CAL=2000; EVAL=2500

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def main():
    freeze=json.loads((HERE/'BENCHMARK_FREEZE.json').read_text(encoding='utf-8'))
    for rel,digest in freeze['sha256'].items():
        if sha(ROOT/rel)!=digest: raise RuntimeError(f'benchmark freeze mismatch: {rel}')
    inventory=json.loads((HERE/'BENCHMARK_SEED_INVENTORY.json').read_text(encoding='utf-8'))
    seeds={(x['kind'],float(x['probability']),int(x['root'])):int(x['seed']) for x in inventory['streams']}
    if len(seeds)!=40: raise RuntimeError('benchmark stream keys are not unique')
    profile_json=json.loads((STAGE5/'FROZEN_PROFILE_ESTIMATOR.json').read_text(encoding='utf-8'))
    profile=DetectorProfileEstimator(np.asarray(profile_json['probabilities'],float),np.asarray(profile_json['means'],float),
                                     np.asarray(profile_json['scales'],float),float(profile_json.get('grid_step',.00001)))
    fixed=build_decoder(0.0)[2]
    oracle={p:build_decoder(p)[2] for p in PROBS}
    rows=[]; file_hashes={}
    for p in PROBS:
        for root in range(ROOTS):
            name=f'root_p{p:.3f}_r{root:03d}.npz'; path=RUN/'roots'/name
            if not path.is_file(): raise FileNotFoundError(name)
            file_hashes[name]=sha(path)
            with np.load(path,allow_pickle=False) as z:
                if str(np.asarray(z['phase']).item())!='complete': raise RuntimeError(f'incomplete benchmark root {name}')
                cal=np.asarray(z['calibration_detectors']); det=np.asarray(z['evaluation_detectors'])
                obs=np.asarray(z['observables']); pred=np.asarray(z['predictions'])
                if cal.shape!=(CAL,40) or det.shape!=(EVAL,40) or obs.shape!=(EVAL,) or pred.shape!=(3,EVAL):
                    raise RuntimeError(f'shape failure {name}')
                if any(not np.isin(x,(0,1)).all() for x in (cal,det,obs,pred)):
                    raise RuntimeError(f'nonbinary benchmark data {name}')
                sc=int(np.asarray(z['seed_calibration']).item()); se=int(np.asarray(z['seed_evaluation']).item())
                if sc!=seeds[('calibration_detector_only',p,root)] or se!=seeds[('paired_evaluation_detector_observable',p,root)]:
                    raise RuntimeError(f'benchmark stream mapping mismatch {name}')
                p_hat=profile.estimate(cal)
                if not np.isclose(p_hat,float(np.asarray(z['p_hat']).item()),rtol=0,atol=1e-12):
                    raise RuntimeError(f'profile estimate mismatch {name}')
                rebuilt=np.stack([decode_prediction(fixed,det),
                                  decode_prediction(build_decoder(p_hat)[2],det),
                                  decode_prediction(oracle[p],det)])
                if not np.array_equal(rebuilt,pred): raise RuntimeError(f'independent prediction rescore mismatch {name}')
                errs=[int(np.count_nonzero(logical_error_mask(pred[i],obs))) for i in range(3)]
                rows.append({'probability':p,'root':root,'calibration_shots':CAL,'evaluation_shots':EVAL,
                             'p_hat':float(p_hat),'fixed_errors':errs[0],'adaptive_errors':errs[1],
                             'reference_errors':errs[2],'paired_difference':(errs[1]-errs[0])/EVAL,
                             'candidate_only':int(np.count_nonzero((pred[1]!=obs)&(pred[0]==obs))),
                             'fixed_only':int(np.count_nonzero((pred[1]==obs)&(pred[0]!=obs)))})
    status=json.loads((RUN/'status.json').read_text(encoding='utf-8'))
    summary=json.loads((RUN/'roots'/'RUNNER_SUMMARY.json').read_text(encoding='utf-8'))
    archived=json.loads((RUN/'ROOT_ARCHIVE_MANIFEST.json').read_text(encoding='utf-8'))
    if status.get('status')!='completed' or status.get('completed_roots')!=20 or status.get('unique_shots_generated')!=90000:
        raise RuntimeError('persisted benchmark status mismatch')
    if summary.get('roots')!=20 or summary.get('unique_shots')!=90000 or summary.get('calibration_shots')!=40000 or summary.get('evaluation_shots')!=50000:
        raise RuntimeError('benchmark summary totals mismatch')
    if archived.get('root_count')!=20 or archived.get('sha256')!=file_hashes:
        raise RuntimeError('root archive manifest mismatch')
    interruption=json.loads((HERE/'INTERRUPTION_TEST.json').read_text(encoding='utf-8'))
    if interruption.get('status')!='PASS_PLANNED_INTERRUPTION' or interruption.get('sampled_shots')!=CAL:
        raise RuntimeError('interruption evidence missing or invalid')
    runtime=json.loads((HERE/'BENCHMARK_RUNTIME.json').read_text(encoding='utf-8'))
    result={'audit':'PASS_BENCHMARK_EVIDENCE','benchmark_only':True,'stage5_samples_generated':0,
      'sealed_stage5_stream_rows_read':False,'sealed_historical_test_access':0,
      'roots_verified':len(rows),'unique_benchmark_shots_verified':90000,
      'calibration_shots_verified':40000,'evaluation_shots_verified':50000,
      'all_predictions_independently_redecoded':True,'archive_manifest_verified':True,
      'restart_without_calibration_resampling':bool(runtime.get('sample_calls')+interruption.get('sample_calls')==40
          and runtime.get('sampled_shots')+interruption.get('sampled_shots')==90000),
      'first_process_sampled_shots':interruption.get('sampled_shots'),
      'resume_process_sampled_shots':runtime.get('sampled_shots'),
      'resume_process_sampler_calls':runtime.get('sample_calls'),
      'runtime':runtime,'per_root':rows,'sha256_roots':file_hashes}
    (HERE/'BENCHMARK_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('per_root','sha256_roots')},indent=2))
    if result['restart_without_calibration_resampling'] is not True:
        raise RuntimeError('restart stream accounting does not demonstrate one use per seed')
if __name__=='__main__': main()
