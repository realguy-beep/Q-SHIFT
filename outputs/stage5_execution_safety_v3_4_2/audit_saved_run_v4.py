"""Independent archive/prediction audit; does not import Stage 5 reporting code."""
from __future__ import annotations
import json, os, sys
import argparse, threading, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from ownership_runtime_v4 import (verify_committed_npz, file_sha256, atomic_json,
                                  ChildOwnership, Deadline, start_deadline_watchdog)

def audit(run_dir: Path, benchmark_config: Path|None=None, *, deadline: Deadline|None=None):
    # Heavy simulator/decoder imports happen only after the child deadline guard starts.
    import numpy as np
    from collections import OrderedDict
    from outputs.stage4_noise_adaptive_feasibility_v1.prototype import DetectorProfileEstimator, build_decoder, decode_prediction
    deadline = deadline or Deadline(seconds=3600)
    deadline.check('audit start')
    run_dir=Path(run_dir); rootdir=run_dir/'roots'
    if benchmark_config:
        cfg=json.loads(Path(benchmark_config).read_text(encoding='utf-8'))
        probs=[float(x) for x in cfg['probabilities']]; roots=int(cfg['roots_per_condition'])
        cal_n=int(cfg['calibration_shots_per_root']); eval_n=int(cfg['evaluation_shots_per_root'])
        seed_rows={(x['kind'],float(x['probability']),int(x['root'])):int(x['seed']) for x in cfg['streams']}
        out_path=run_dir/'INDEPENDENT_AUDIT.json'
    else:
        frozen=json.loads((ROOT/'outputs/stage5_secondary_inference_repair_v1/STAGE5_REPAIR_CONFIG.json').read_text(encoding='utf-8'))
        probs=[float(x) for x in frozen['probabilities']]; roots=int(frozen['roots_per_condition'])
        cal_n=int(frozen['calibration_shots_per_root']); eval_n=int(frozen['evaluation_shots_per_root'])
        inv=json.loads((ROOT/'outputs/stage5_secondary_inference_repair_v1/FROZEN_PROFILE_ESTIMATOR.json').read_text(encoding='utf-8'))
        out_path=run_dir/'INDEPENDENT_AUDIT.json'
        seed_rows=None
    prof_data=json.loads((ROOT/'outputs/stage5_secondary_inference_repair_v1/FROZEN_PROFILE_ESTIMATOR.json').read_text(encoding='utf-8'))
    profile=DetectorProfileEstimator(np.asarray(prof_data['probabilities'],float),np.asarray(prof_data['means'],float),
                                     np.asarray(prof_data['scales'],float),float(prof_data.get('grid_step',.00001)))
    fixed=build_decoder(0.)[2]; oracle={p:build_decoder(p)[2] for p in probs}; adaptive=OrderedDict()
    records=[]; arrays_seen=0
    for p in probs:
        for r in range(roots):
            deadline.check('audit root start')
            path=rootdir/f'root_p{p:.3f}_r{r:03d}.npz'
            digest=verify_committed_npz(path)
            with np.load(path,allow_pickle=False) as z:
                phase=str(np.asarray(z['phase']).item())
                cal=np.asarray(z['calibration_detectors']); det=np.asarray(z['evaluation_detectors'])
                obs=np.asarray(z['observables']).reshape(-1); pred=np.asarray(z['predictions'])
                p_hat=float(np.asarray(z['p_hat']).item())
                if phase!='complete' or cal.shape!=(cal_n,40) or det.shape!=(eval_n,40) or obs.shape!=(eval_n,) or pred.shape!=(3,eval_n):
                    raise ValueError(f'schema/shape mismatch: {path.name}')
                if any(not np.isin(x,(0,1)).all() for x in (cal,det,obs,pred)):
                    raise ValueError(f'nonbinary value: {path.name}')
                if int(np.asarray(z['root']).item())!=r or float(np.asarray(z['probability']).item())!=p:
                    raise ValueError(f'root/condition mismatch: {path.name}')
                if abs(profile.estimate(cal)-p_hat)>1e-12:
                    raise ValueError(f'calibration estimator mismatch: {path.name}')
                if seed_rows is not None:
                    if int(np.asarray(z['seed_calibration']).item())!=seed_rows[('calibration_detector_only',p,r)] or int(np.asarray(z['seed_evaluation']).item())!=seed_rows[('paired_evaluation_detector_observable',p,r)]:
                        raise ValueError(f'benchmark seed mapping mismatch: {path.name}')
                if p_hat not in adaptive: adaptive[p_hat]=build_decoder(p_hat)[2]
                adaptive.move_to_end(p_hat)
                while len(adaptive)>64: adaptive.popitem(last=False)
                deadline.check('audit before independent re-decoding')
                expected=np.stack([decode_prediction(fixed,det),decode_prediction(adaptive[p_hat],det),decode_prediction(oracle[p],det)])
                deadline.check('audit after independent re-decoding')
                if not np.array_equal(expected,pred): raise ValueError(f'independent decode mismatch: {path.name}')
                errors=[int(np.count_nonzero(pred[k]!=obs)) for k in range(3)]
                records.append({'probability':p,'root':r,'shots':eval_n,'errors':errors,
                                'candidate_only':int(np.count_nonzero((pred[1]!=obs)&(pred[0]==obs))),
                                'fixed_only':int(np.count_nonzero((pred[1]==obs)&(pred[0]!=obs))),
                                'archive_sha256':digest})
                arrays_seen+=cal_n+eval_n
    expected_files=roots*len(probs)
    actual_files=list(rootdir.glob('root_p*.npz'))
    if len(actual_files)!=expected_files: raise ValueError(f'archive count mismatch: {len(actual_files)} != {expected_files}')
    archive_manifest_path=run_dir/'ROOT_ARCHIVE_MANIFEST.json'
    if archive_manifest_path.exists():
        archive_manifest=json.loads(archive_manifest_path.read_text(encoding='utf-8'))
        actual_manifest={p.name:verify_committed_npz(p) for p in actual_files}
        frozen_manifest=archive_manifest.get('sha256',{})
        if frozen_manifest and frozen_manifest!=actual_manifest:
            raise ValueError('root archive manifest does not match committed checkpoint hashes')
    summary_path=rootdir/'RUNNER_SUMMARY.json'
    if not summary_path.is_file(): raise ValueError('runner summary is missing')
    summary=json.loads(summary_path.read_text(encoding='utf-8'))
    if benchmark_config:
        expected_errors={f"{x['probability']:.3f}:{x['root']}":x['errors'] for x in records}
        saved_errors={f"{x['probability']:.3f}:{x['root']}":x['errors'] for x in summary.get('per_root',[])}
        if expected_errors!=saved_errors: raise ValueError('saved benchmark summary disagrees with recomputed arrays')
    else:
        saved={f"{x['probability']:.3f}:{x['root']}":[x['fixed_errors'],x['profile_errors'],x['oracle_errors']] for x in summary.get('per_root',[])}
        expected={f"{x['probability']:.3f}:{x['root']}":x['errors'] for x in records}
        if saved!=expected: raise ValueError('saved Stage 5 summary disagrees with recomputed arrays')
    result={'status':'PASS_INDEPENDENT_AUDIT','benchmark_only':benchmark_config is not None,
            'roots_verified':len(records),'unique_shots_recomputed':arrays_seen,
            'predictions_independently_redecoded':True,'checkpoint_hashes_verified':expected_files,
            'per_root':records}
    atomic_json(out_path,result)
    deadline.check('audit output committed')
    return result

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--qshift-owner-token',required=True)
    parser.add_argument('--qshift-deadline-monotonic',required=True,type=float)
    args=parser.parse_args(argv)
    run=Path(os.environ['QSHIFT_STAGE5_RUN_DIR']).resolve()
    conf=Path(os.environ['QSHIFT_SAFETY_BENCH_CONFIG']) if os.environ.get('QSHIFT_SAFETY_BENCHMARK')=='1' else None
    deadline=Deadline(absolute_monotonic=args.qshift_deadline_monotonic)
    completed=threading.Event()
    try:
        start_deadline_watchdog(deadline.deadline,completed,'auditor-bootstrap')
        with ChildOwnership(run,'auditor',args.qshift_owner_token,deadline.deadline):
            result=audit(run,conf,deadline=deadline)
            print(json.dumps({k:v for k,v in result.items() if k!='per_root'},sort_keys=True))
            return 0
    finally:
        completed.set()

if __name__=='__main__': raise SystemExit(main())
