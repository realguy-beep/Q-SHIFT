"""Stage 5 v3.4.2 regression tests; Windows subprocesses use benchmark-only data."""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, tempfile, time, unittest, uuid
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
import safety_runner_v4 as runner
from ownership_runtime_v4 import (RunDirectoryLock, LockBusyError,
    assert_child_ownership_clear, verify_committed_npz, atomic_json)

EVIDENCE_ROOT=HERE/'benchmark_runs'/f"v342_{os.getpid()}_{time.time_ns()}"
EVIDENCE_ROOT.mkdir(parents=True,exist_ok=True)
_LIFECYCLE_EVENTS=[]


class ProcessOwnershipV4Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=Path(tempfile.mkdtemp(prefix='qshift-v34-'))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp,ignore_errors=True)

    def _probe(self, run):
        return subprocess.run([sys.executable,str(HERE/'test_process_child_v4.py'),'--probe',
            '--run-dir',str(run)],cwd=HERE,capture_output=True,text=True,timeout=10)

    def _process_alive(self,pid,create_time=None):
        import psutil
        try:
            proc=psutil.Process(pid)
            if create_time is not None and abs(proc.create_time()-float(create_time))>=0.01: return False
            dead_states={psutil.STATUS_ZOMBIE,psutil.STATUS_DEAD}
            if hasattr(psutil,'STATUS_STOPPED'): dead_states.add(psutil.STATUS_STOPPED)
            return proc.status() not in dead_states
        except psutil.NoSuchProcess:
            return False
        except psutil.AccessDenied:
            return True

    def _wait_exists(self,path,timeout=5):
        end=time.time()+timeout
        while time.time()<end:
            if path.exists(): return
            time.sleep(.02)
        self.fail(f'timed out waiting for {path}')

    def _wait_dead(self,pid,timeout=6):
        import psutil
        end=time.time()+timeout
        while time.time()<end:
            try:
                proc=psutil.Process(pid)
                if not proc.is_running(): return
            except psutil.NoSuchProcess: return
            time.sleep(.05)
        self.fail(f'owned child {pid} did not stop by its independent deadline')

    def _supervisor_kill_case(self,role,phase):
        run=self.tmp/f'{role}-{phase}'; run.mkdir()
        atomic_json(run/'status.json',{'status':'finalizing','in_flight':None})
        ready=self.tmp/f'{role}-{phase}-supervisor-ready.json'
        child_ready=self.tmp/f'{role}-{phase}-child-ready.txt'
        active=self.tmp/f'{role}-{phase}-active.txt'
        startup=phase=='startup'
        command=[sys.executable,str(HERE/'test_process_child_v4.py'),'--supervisor',
          '--run-dir',str(run),'--role',role,'--ready-marker',str(ready),
          '--child-ready-marker',str(child_ready),'--active-marker',str(active),
          '--child-lifetime','3.4','--preclaim-delay',('1.8' if startup else '0'),
          '--delay-record',('3.0' if startup else '0')]
        supervisor=subprocess.Popen(command,cwd=HERE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,text=True)
        self._wait_exists(child_ready if startup else active)
        info=json.loads(ready.read_text(encoding='utf-8')); child_pid=int(info['child_pid'])
        import psutil
        child_create_time=float(psutil.Process(child_pid).create_time())
        supervisor.kill(); supervisor.wait(timeout=5)
        alive_before_probe=self._process_alive(child_pid,child_create_time)
        blocked=self._probe(run)
        self.assertIn(blocked.returncode,(0,12),blocked.stdout+blocked.stderr)
        alive_after_probe=self._process_alive(child_pid,child_create_time)
        if blocked.returncode==0:
            self.assertFalse(alive_after_probe,'second launcher entered while a capable child remained alive')
        else:
            self.assertTrue(alive_after_probe,'launcher rejected without a live owner')
            self._wait_dead(child_pid)
        intent=json.loads((run/'.stage5-child-intent.json').read_text(encoding='utf-8'))
        _LIFECYCLE_EVENTS.append({'role':role,'phase':phase,'supervisor_terminated':True,
          'child_pid':child_pid,'child_create_time':child_create_time,
          'intent_state_at_probe':intent.get('state'),
          'child_alive_before_second_launcher_probe':alive_before_probe,
          'child_alive_after_second_launcher_probe':alive_after_probe,
          'second_launcher_rejected':blocked.returncode==12,
          'second_launcher_rejected_while_child_live':blocked.returncode==12,
          'second_launcher_accepted_only_after_child_dead':blocked.returncode==0 and not alive_after_probe,
          'rejection_exit_code':blocked.returncode})
        self._wait_dead(child_pid)
        # Child death releases its OS role lock. A new launcher reconciles the
        # now-provably stale intent and can safely enter.
        accepted=self._probe(run)
        self.assertEqual(accepted.returncode,0,accepted.stdout+accepted.stderr)
        self.assertFalse(self._process_alive(child_pid,child_create_time))
        _LIFECYCLE_EVENTS[-1].update({'child_deadline_released_ownership':True,
          'second_launcher_accepted_after_release':accepted.returncode==0,
          'release_probe_exit_code':accepted.returncode})
        status=json.loads((run/'status.json').read_text(encoding='utf-8'))
        self.assertNotEqual(status.get('status'),'completed')
        self.assertTrue(json.loads((run/'.stage5-child-intent.json').read_text())['state']=='stale_released')

    def test_windows_real_subprocess_supervisor_death_all_child_phases(self):
        self.assertEqual(os.name,'nt','require real Windows msvcrt/process semantics')
        for role,phase in [('worker','startup'),('worker','active'),
                           ('auditor','startup'),('auditor','active'),
                           ('finalizer','startup'),('finalizer','active')]:
            with self.subTest(role=role,phase=phase): self._supervisor_kill_case(role,phase)
        atomic_json(EVIDENCE_ROOT/'OWNERSHIP_FAILURE_INJECTION_V4.json',
            {'platform':sys.platform,'process_lifecycle_events':_LIFECYCLE_EVENTS,
             'all_six_cases_passed':len(_LIFECYCLE_EVENTS)==6 and all(
              (x['second_launcher_rejected_while_child_live'] or x['second_launcher_accepted_only_after_child_dead']) and x['child_deadline_released_ownership'] and
              x['second_launcher_accepted_after_release'] for x in _LIFECYCLE_EVENTS)})

    def test_suspended_process_handoff_gap_is_reclaimed_safely(self):
        run=self.tmp/'unconfirmed-spawn'; run.mkdir()
        ready=self.tmp/'unconfirmed-ready.json'
        child_ready=self.tmp/'never-started.txt'; active=self.tmp/'never-active.txt'
        supervisor=subprocess.Popen([sys.executable,str(HERE/'test_process_child_v4.py'),'--supervisor',
          '--run-dir',str(run),'--role','auditor','--ready-marker',str(ready),
          '--child-ready-marker',str(child_ready),'--active-marker',str(active),
          '--hold-suspended','--child-lifetime','10'],cwd=HERE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self._wait_exists(ready)
        info=json.loads(ready.read_text()); child_pid=int(info['child_pid'])
        supervisor.kill(); supervisor.wait(timeout=5)
        result=self._probe(run)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self._wait_dead(child_pid)
        self.assertFalse(child_ready.exists()); self.assertFalse(active.exists())

    def test_lock_contention_fails_closed_in_same_process(self):
        run=self.tmp/'lock'
        first=RunDirectoryLock(run,kind='launcher').acquire()
        try:
            with self.assertRaises(LockBusyError): RunDirectoryLock(run,kind='launcher').acquire()
        finally: first.release()

    def test_second_launcher_rejected_while_worker_role_lock_is_held(self):
        run=self.tmp/'live-role-owner'; run.mkdir()
        active=self.tmp/'live-role-active.txt'; ready=self.tmp/'live-role-ready.txt'
        deadline=time.monotonic()+8.0
        with RunDirectoryLock(run,kind='launcher'):
            token=runner.publish_child_intent(run,'worker',deadline)
            command=[sys.executable,str(HERE/'test_process_child_v4.py'),'--child',
              '--run-dir',str(run),'--role','worker','--active-marker',str(active),
              '--ready-marker',str(ready),f'--qshift-owner-token={token}',
              f'--qshift-deadline-monotonic={deadline:.17g}']
            child=subprocess.Popen(command,cwd=HERE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            runner.record_child_spawn(run,token,child.pid)
            self._wait_exists(active)
        blocked=self._probe(run)
        self.assertEqual(blocked.returncode,12,blocked.stdout+blocked.stderr)
        child.terminate(); child.wait(timeout=5)
        self.assertEqual(self._probe(run).returncode,0)

    def test_independent_deadline_watchdog_expires_child(self):
        child=subprocess.Popen([sys.executable,str(HERE/'test_process_child_v4.py'),
          '--watchdog-only','--watchdog-seconds','0.45','--run-dir',str(self.tmp/'watchdog')],cwd=HERE,
          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.assertEqual(child.wait(timeout=5),124)

    def test_atomic_temp_names_fit_long_windows_workspace_paths(self):
        target=EVIDENCE_ROOT/'paired_audit'/'roots'/'root_p0.004_r000.npz.commit-probe.json'
        self.assertGreater(len(str(target)),220)
        atomic_json(target,{'long_path_probe':True})
        self.assertTrue(target.is_file())

    def test_benchmark_normal_completion_counts_hashes_and_final_status(self):
        run=EVIDENCE_ROOT/'paired_audit'
        result=runner.safe_execute(run,timeout_seconds=60,
            benchmark_config=HERE/'benchmark_config.json')
        self.assertEqual(result['status'],'completed')
        audit=json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
        status=json.loads((run/'status.json').read_text())
        manifest=json.loads((run/'FINALIZATION_MANIFEST.json').read_text())
        self.assertEqual((audit['roots_verified'],audit['unique_shots_recomputed']),(2,1536))
        self.assertEqual((status['completed_roots'],status['unique_shots_generated']),(2,1536))
        self.assertEqual(status['status'],'completed')
        self.assertEqual(manifest['status'],'verified_not_terminal')
        for name,digest in manifest['root_sha256'].items():
            self.assertEqual(verify_committed_npz(run/'roots'/name),digest)

    def test_same_seed_crash_recovery_has_one_committed_count_and_journal(self):
        run=EVIDENCE_ROOT/'recovery'
        failed=runner.safe_execute(run,timeout_seconds=60,
            benchmark_config=HERE/'fault_config.json',test_fault='after_sample_before_checkpoint')
        self.assertEqual(failed['status'],'worker_failed')
        before=json.loads((run/'status.json').read_text())
        self.assertIsNotNone(before.get('in_flight'))
        completed=runner.safe_execute(run,timeout_seconds=60,
            benchmark_config=HERE/'fault_config.json',recover_uncommitted=True)
        self.assertEqual(completed['status'],'completed')
        journal=json.loads((run/'RECOVERY_JOURNAL.json').read_text())
        self.assertEqual(journal['events'][-1]['outcome'],'uncommitted_stream_will_replay_same_frozen_seed')
        audit=json.loads((run/'INDEPENDENT_AUDIT.json').read_text())
        self.assertEqual(audit['unique_shots_recomputed'],256)
        self.assertEqual(json.loads((run/'status.json').read_text())['unique_shots_generated'],256)

    def test_frozen_hashes_and_stage5_boundary(self):
        record=runner.verify_safety_sources(); frozen=runner.verify_frozen_inputs()
        self.assertEqual(len(frozen['sha256']),53)
        self.assertEqual(len(record['sha256']),14)
        self.assertFalse(frozen['stage5_evaluation_shots_generated'])
        self.assertFalse((ROOT/'outputs/stage5_secondary_inference_repair_v1/run').exists())


if __name__=='__main__': unittest.main(verbosity=2)
