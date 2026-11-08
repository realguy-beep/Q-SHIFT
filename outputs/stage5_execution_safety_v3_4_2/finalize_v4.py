"""Owned, deadline-bound finalizer. Only the live supervisor marks completed."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import threading
import time
from pathlib import Path

from ownership_runtime_v4 import (ChildOwnership, Deadline, atomic_json,
                                  start_deadline_watchdog, verify_committed_npz)

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "outputs/stage5_secondary_inference_repair_v1/STAGE5_REPAIR_CONFIG.json"


def finalize(run_dir: Path, deadline: Deadline):
    run_dir=Path(run_dir).resolve()
    deadline.check('finalizer start')
    status_path=run_dir/'status.json'
    status=json.loads(status_path.read_text(encoding='utf-8'))
    if status.get('status')!='finalizing':
        raise RuntimeError('finalizer requires finalizing status')
    audit_path=run_dir/'INDEPENDENT_AUDIT.json'
    audit=json.loads(audit_path.read_text(encoding='utf-8'))
    if audit.get('status')!='PASS_INDEPENDENT_AUDIT':
        raise RuntimeError('independent audit failed')
    if os.environ.get('QSHIFT_SAFETY_BENCHMARK')=='1':
        cfg=json.loads(Path(os.environ['QSHIFT_SAFETY_BENCH_CONFIG']).read_text(encoding='utf-8'))
        expected_roots=int(cfg['roots_per_condition'])*len(cfg['probabilities'])
        expected_shots=expected_roots*(int(cfg['calibration_shots_per_root'])+int(cfg['evaluation_shots_per_root']))
    else:
        cfg=json.loads(CONFIG.read_text(encoding='utf-8'))
        expected_roots=int(cfg['roots_per_condition'])*len(cfg['probabilities'])
        expected_shots=int(cfg['allocation']['unique_shots'])
    rootdir=run_dir/'roots'; files={}
    for archive in sorted(rootdir.glob('root_p*.npz')):
        deadline.check('finalization archive hashing')
        files[archive.name]=verify_committed_npz(archive)
    if len(files)!=expected_roots or len(files)!=int(audit.get('roots_verified',-1)):
        raise RuntimeError(f'finalizer root-count mismatch: {len(files)} != {expected_roots}')
    counts=int(audit['unique_shots_recomputed'])
    if counts!=expected_shots:
        raise RuntimeError(f'finalizer shot-count mismatch: {counts} != {expected_shots}')
    if int(status.get('unique_shots_generated',-1))!=counts or int(status.get('completed_roots',-1))!=len(files):
        raise RuntimeError('persisted runner counts disagree with independent audit')
    summary=rootdir/'RUNNER_SUMMARY.json'
    deadline.check('finalization manifest preparation')
    final_manifest={'status':'verified_not_terminal','root_count':len(files),'unique_shots':counts,
      'root_sha256':files,'summary_sha256':hashlib.sha256(summary.read_bytes()).hexdigest(),
      'audit_sha256':hashlib.sha256(audit_path.read_bytes()).hexdigest(),'created_unix':time.time(),
      'terminal_status_owner':'supervisor_after_finalizer_exit'}
    status.update({'status':'finalizing','phase':'finalization_artifact_write'})
    atomic_json(status_path,status)
    deadline.check('finalization manifest write')
    atomic_json(run_dir/'FINALIZATION_MANIFEST.json',final_manifest)
    deadline.check('finalization artifact verification')
    persisted=json.loads((run_dir/'FINALIZATION_MANIFEST.json').read_text(encoding='utf-8'))
    if persisted!=final_manifest:
        raise RuntimeError('finalization manifest failed read-after-write verification')
    return final_manifest


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('run_dir',type=Path)
    parser.add_argument('--qshift-owner-token',required=True)
    parser.add_argument('--qshift-deadline-monotonic',required=True,type=float)
    args=parser.parse_args(argv)
    deadline=Deadline(absolute_monotonic=args.qshift_deadline_monotonic)
    done=threading.Event()
    try:
        start_deadline_watchdog(deadline.deadline,done,'finalizer-bootstrap')
        with ChildOwnership(args.run_dir,'finalizer',args.qshift_owner_token,deadline.deadline):
            result=finalize(args.run_dir,deadline)
            print(json.dumps({k:v for k,v in result.items() if k!='root_sha256'},sort_keys=True))
            return 0
    finally:
        done.set()


if __name__=='__main__': raise SystemExit(main())
