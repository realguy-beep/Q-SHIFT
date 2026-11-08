from __future__ import annotations
import json, os, subprocess, sys, tempfile, time, unittest
from pathlib import Path
import hashlib
from unittest import mock

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
from safety_runtime import RunDirectoryLock, LockBusyError, atomic_json, atomic_npz, verify_committed_npz, UncommittedCheckpointError, Deadline
import safety_runner_v3 as safety_runner
from safety_runner_v3 import safe_execute, supervise_command, verify_frozen_inputs

def child_main(argv):
    mode=argv[0]
    if mode=='lock':
        run=Path(argv[1]); ready=Path(argv[2]); crash=argv[3]=='crash'
        lock=RunDirectoryLock(run).acquire(); ready.write_text('ready',encoding='utf-8')
        if crash: os._exit(0)
        time.sleep(5); lock.release(); return 0
    if mode=='worker-lock':
        run=Path(argv[1]); ready=Path(argv[2])
        lock=RunDirectoryLock(run,kind='worker').acquire(); ready.write_text('ready',encoding='utf-8')
        time.sleep(5); lock.release(); return 0
    if mode=='write-npz':
        path=Path(argv[1]); point=argv[2]
        def fault(stage):
            if stage==point: os._exit(91)
        atomic_npz(path,{'x':__import__('numpy').arange(32)},fault=fault); return 0
    if mode=='write-json':
        path=Path(argv[1])
        atomic_json(path,{'new':True},fault=lambda stage: os._exit(92) if stage=='after_temp_fsync_before_replace' else None); return 0
    if mode=='slow-phase':
        run=Path(argv[1]); phase=argv[2]
        atomic_json(run/'status.json',{'status':'running','phase':phase,'in_flight':None})
        time.sleep(10.0)
        atomic_json(run/'status.json',{'status':'completed','phase':'complete'})
        return 0
    raise ValueError(mode)

class SafetyV3Tests(unittest.TestCase):
    def setUp(self): self.temp=Path(tempfile.mkdtemp(prefix='qshift-safety-v3-'))
    def tearDown(self):
        import shutil; shutil.rmtree(self.temp,ignore_errors=True)

    def test_frozen_53_hashes(self):
        f=verify_frozen_inputs(); self.assertEqual(len(f['sha256']),53)

    def test_safety_sources_were_frozen_before_any_benchmark_sampling(self):
        freeze=json.loads((HERE/'SAFETY_FREEZE.json').read_text(encoding='utf-8'))
        self.assertEqual(freeze['state'],'FROZEN_BEFORE_BENCHMARK_SAMPLING')
        self.assertFalse(freeze['stage5_sampling_authorized'])
        self.assertEqual(freeze['historical_stage5_frozen_hash_count'],53)
        for rel,want in freeze['sha256'].items():
            self.assertEqual(hashlib.sha256((HERE/rel).read_bytes()).hexdigest(),want,rel)
        self.assertFalse((ROOT/'outputs/stage5_secondary_inference_repair_v1/run').exists())

    def test_cli_preflight_verifies_both_freezes_without_sampling(self):
        proc=subprocess.run([sys.executable,str(HERE/'safety_runner_v3.py'),'--preflight'],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(proc.returncode,0,proc.stderr)
        result=json.loads(proc.stdout)
        self.assertEqual(result['status'],'PASS_NO_SAMPLING')
        self.assertEqual(result['frozen_hashes'],53)
        self.assertEqual(result['safety_source_hashes'],13)
        self.assertFalse(result['stage5_sampling_invoked'])
        self.assertFalse(result['stage5_run_directory_exists'])

    def test_exclusive_lock_and_live_contention(self):
        run=self.temp/'lock'; ready=self.temp/'ready'
        proc=subprocess.Popen([sys.executable,__file__,'--child','lock',str(run),str(ready),'hold'],cwd=ROOT)
        try:
            limit=time.time()+8
            while not ready.exists() and time.time()<limit: time.sleep(.02)
            self.assertTrue(ready.exists())
            with self.assertRaises(LockBusyError): RunDirectoryLock(run).acquire()
        finally:
            proc.terminate(); proc.wait(timeout=5)

    def test_crash_releases_os_lock_and_stale_owner_is_visible(self):
        run=self.temp/'crashed-lock'; ready=self.temp/'crash-ready'
        proc=subprocess.run([sys.executable,__file__,'--child','lock',str(run),str(ready),'crash'],cwd=ROOT,timeout=8)
        self.assertEqual(proc.returncode,0)
        with RunDirectoryLock(run) as lock:
            self.assertIsNotNone(lock.previous_owner)
            self.assertEqual(lock.previous_owner['state'],'active')

    def test_worker_lock_survives_launcher_release_and_blocks_duplicate(self):
        run=self.temp/'orphan-worker'; ready=self.temp/'worker-ready'
        with RunDirectoryLock(run,kind='launcher'):
            proc=subprocess.Popen([sys.executable,__file__,'--child','worker-lock',str(run),str(ready)],cwd=ROOT)
            limit=time.time()+8
            while not ready.exists() and time.time()<limit: time.sleep(.02)
            self.assertTrue(ready.exists())
        try:
            with self.assertRaises(LockBusyError): RunDirectoryLock(run,kind='worker').acquire()
        finally:
            proc.terminate(); proc.wait(timeout=5)
        with RunDirectoryLock(run,kind='worker'): pass

    def test_npz_commit_markers_across_crash_boundaries(self):
        import numpy as np
        before=self.temp/'before.npz'
        c=subprocess.run([sys.executable,__file__,'--child','write-npz',str(before),'after_temp_fsync_before_replace'],cwd=ROOT)
        self.assertEqual(c.returncode,91); self.assertFalse(before.exists())
        with self.assertRaises(UncommittedCheckpointError): verify_committed_npz(before)
        between=self.temp/'between.npz'
        c=subprocess.run([sys.executable,__file__,'--child','write-npz',str(between),'after_replace_before_commit_marker'],cwd=ROOT)
        self.assertEqual(c.returncode,91); self.assertTrue(between.exists())
        with self.assertRaises(UncommittedCheckpointError): verify_committed_npz(between)
        committed=self.temp/'committed.npz'
        c=subprocess.run([sys.executable,__file__,'--child','write-npz',str(committed),'after_commit_marker'],cwd=ROOT)
        self.assertEqual(c.returncode,91); self.assertTrue(verify_committed_npz(committed))
        with np.load(committed,allow_pickle=False) as z: self.assertEqual(z['x'].shape,(32,))

    def test_json_replace_crash_preserves_previous_complete_document(self):
        path=self.temp/'status.json'; atomic_json(path,{'old':True})
        c=subprocess.run([sys.executable,__file__,'--child','write-json',str(path)],cwd=ROOT)
        self.assertEqual(c.returncode,92)
        self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['old'],True)

    def test_deadline_during_aggregation_and_artifact_write(self):
        for phase in ('final_aggregation','artifact_write'):
            run=self.temp/phase
            run.mkdir(parents=True,exist_ok=True)
            atomic_json(run/'status.json',{'status':'running','phase':phase,'in_flight':None})
            result=supervise_command([sys.executable,__file__,'--child','slow-phase',str(run),phase],run,2.0)
            self.assertEqual(result['status'],'deadline_exceeded')
            status=json.loads((run/'status.json').read_text(encoding='utf-8'))
            self.assertEqual(status['status'],'deadline_exceeded')
            self.assertEqual(status['deadline_phase'],phase)

    def test_deadline_during_finalizer_artifact_write_never_completes(self):
        run=self.temp/'finalizer-timeout'; run.mkdir()
        atomic_json(run/'status.json',{'status':'finalizing','unique_shots_generated':0,'completed_roots':0,'in_flight':None})
        audit_script=self.temp/'fake_auditor.py'
        audit_script.write_text("import os,json,pathlib\nr=pathlib.Path(os.environ['QSHIFT_STAGE5_RUN_DIR'])\na={'status':'PASS_INDEPENDENT_AUDIT','unique_shots_recomputed':0,'roots_verified':0}\n(r/'INDEPENDENT_AUDIT.json').write_text(json.dumps(a))\nprint(json.dumps(a))\n",encoding='utf-8')
        finalizer_script=self.temp/'slow_finalizer.py'
        finalizer_script.write_text("import os,json,pathlib,time\nr=pathlib.Path(os.environ['QSHIFT_STAGE5_RUN_DIR'])\np=r/'status.json'; x=json.loads(p.read_text()); x.update({'status':'finalizing','phase':'finalization_artifact_write'}); p.write_text(json.dumps(x)); time.sleep(10)\n",encoding='utf-8')
        with mock.patch.object(safety_runner,'AUDITOR',audit_script), mock.patch.object(safety_runner,'FINALIZER',finalizer_script):
            result=safety_runner._audit_and_finalize(run,Deadline(2.0))
        self.assertEqual(result['status'],'deadline_exceeded')
        status=json.loads((run/'status.json').read_text(encoding='utf-8'))
        self.assertEqual(status['status'],'deadline_exceeded')
        self.assertNotEqual(status['status'],'completed')

    def test_small_paired_benchmark_completes_and_audits(self):
        cfg=HERE/'benchmark_config.json'; run=self.temp/'paired-run'
        result=safe_execute(run,timeout_seconds=90,benchmark_config=cfg)
        self.assertEqual(result['status'],'completed')
        audit=json.loads((run/'INDEPENDENT_AUDIT.json').read_text(encoding='utf-8'))
        self.assertEqual(audit['status'],'PASS_INDEPENDENT_AUDIT')
        self.assertEqual(audit['roots_verified'],2)
        self.assertEqual(audit['unique_shots_recomputed'],1536)
        self.assertEqual(json.loads((run/'status.json').read_text(encoding='utf-8'))['status'],'completed')

    def test_post_sampler_precheckpoint_crash_replays_same_uncommitted_stream(self):
        cfg=HERE/'fault_config.json'; run=self.temp/'sampler-crash'
        first=safe_execute(run,timeout_seconds=90,benchmark_config=cfg,test_fault='after_sample_before_checkpoint')
        self.assertEqual(first['status'],'worker_failed')
        status=json.loads((run/'status.json').read_text(encoding='utf-8'))
        self.assertEqual(status['in_flight']['kind'],'calibration')
        self.assertFalse((run/'roots'/'root_p0.004_r000.npz').exists())
        second=safe_execute(run,timeout_seconds=90,benchmark_config=cfg,recover_uncommitted=True)
        self.assertEqual(second['status'],'completed')
        self.assertEqual(second['recovery']['state'],'uncommitted_stream_will_replay_same_frozen_seed')
        self.assertEqual(second['audit']['unique_shots_recomputed'],256)

    def test_commit_before_status_crash_resumes_without_duplicate_calibration(self):
        cfg=HERE/'fault_config.json'; run=self.temp/'committed-crash'
        first=safe_execute(run,timeout_seconds=90,benchmark_config=cfg,test_fault='after_npz_commit')
        self.assertEqual(first['status'],'worker_failed')
        archive=run/'roots'/'root_p0.004_r000.npz'
        self.assertTrue(verify_committed_npz(archive))
        second=safe_execute(run,timeout_seconds=90,benchmark_config=cfg,recover_uncommitted=True)
        self.assertEqual(second['status'],'completed')
        self.assertEqual(second['recovery']['state'],'committed_checkpoint_reconciled')
        self.assertEqual(second['audit']['unique_shots_recomputed'],256)

    def test_replace_without_commit_marker_fails_closed(self):
        cfg=HERE/'fault_config.json'; run=self.temp/'ambiguous-checkpoint'
        first=safe_execute(run,timeout_seconds=90,benchmark_config=cfg,test_fault='after_npz_replace_before_commit')
        self.assertEqual(first['status'],'worker_failed')
        with self.assertRaises(UncommittedCheckpointError):
            safe_execute(run,timeout_seconds=90,benchmark_config=cfg,recover_uncommitted=True)

    def test_active_sampler_interruption_is_not_claimed_completed(self):
        cfg=HERE/'active_sampler_config.json'; run=self.temp/'active-sampler'
        result=safe_execute(run,timeout_seconds=60,benchmark_config=cfg,kill_on_sample_marker=True)
        self.assertEqual(result['status'],'interrupted_active_sampler')
        status=json.loads((run/'status.json').read_text(encoding='utf-8'))
        self.assertEqual(status['status'],'interrupted_active_sampler')
        self.assertTrue(status['in_flight'])
        self.assertFalse((run/'roots'/'root_p0.004_r000.npz').exists())
        resumed=safe_execute(run,timeout_seconds=120,benchmark_config=cfg,recover_uncommitted=True)
        self.assertEqual(resumed['status'],'completed')
        self.assertEqual(resumed['recovery']['state'],'uncommitted_stream_will_replay_same_frozen_seed')
        self.assertEqual(resumed['audit']['unique_shots_recomputed'],1_000_064)

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--child': raise SystemExit(child_main(sys.argv[2:]))
    unittest.main()
