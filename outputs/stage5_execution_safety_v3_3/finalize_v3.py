"""Deadline-bounded independent finalization of a verified Stage 5 run."""
from __future__ import annotations
import hashlib,json,sys,time
from pathlib import Path
from safety_runtime import Deadline,atomic_json,verify_committed_npz

def main(argv=None):
    run_dir=Path(sys.argv[1]).resolve(); budget=float(sys.argv[2]); deadline=Deadline(budget)
    status_path=run_dir/'status.json'
    status=json.loads(status_path.read_text(encoding='utf-8'))
    if status.get('status')!='finalizing': raise RuntimeError('finalizer requires finalizing status')
    audit_path=run_dir/'INDEPENDENT_AUDIT.json'; audit=json.loads(audit_path.read_text(encoding='utf-8'))
    if audit.get('status')!='PASS_INDEPENDENT_AUDIT': raise RuntimeError('independent audit failed')
    rootdir=run_dir/'roots'; files={}
    for p in sorted(rootdir.glob('root_p*.npz')):
        deadline.check('finalization archive hashing')
        files[p.name]=verify_committed_npz(p)
    if len(files)!=int(audit.get('roots_verified',-1)):
        raise RuntimeError('finalizer archive count disagrees with audit')
    summary=rootdir/'RUNNER_SUMMARY.json'
    counts=int(audit['unique_shots_recomputed'])
    if int(status.get('unique_shots_generated',-1))!=counts or int(status.get('completed_roots',-1))!=len(files):
        raise RuntimeError('persisted runner counts disagree with independent audit')
    # Leave a shutdown margin for the final status replacement and its fsync.
    if deadline.remaining()<3.0:
        status.update({'status':'deadline_exceeded','deadline_phase':'finalization_reserve','in_flight':None})
        atomic_json(status_path,status); return 3
    final_manifest={'status':'verified','root_count':len(files),'unique_shots':counts,
      'root_sha256':files,'summary_sha256':hashlib.sha256(summary.read_bytes()).hexdigest(),
      'audit_sha256':hashlib.sha256(audit_path.read_bytes()).hexdigest(),'created_unix':time.time()}
    status.update({'status':'finalizing','phase':'finalization_artifact_write'})
    atomic_json(status_path,status)
    atomic_json(run_dir/'FINALIZATION_MANIFEST.json',final_manifest)
    if deadline.remaining()<1.0:
        status.update({'status':'deadline_exceeded','deadline_phase':'final_status_reserve','in_flight':None})
        atomic_json(status_path,status); return 3
    status.update({'status':'completed','finalized_unix':time.time(),'in_flight':None,
                   'independent_audit':'PASS_INDEPENDENT_AUDIT'})
    atomic_json(status_path,status)
    if deadline.remaining()<=0:
        status.update({'status':'deadline_exceeded','deadline_phase':'final_status_write','in_flight':None})
        atomic_json(status_path,status); return 3
    return 0
if __name__=='__main__': raise SystemExit(main())
