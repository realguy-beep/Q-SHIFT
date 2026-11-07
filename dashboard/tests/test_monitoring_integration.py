"""A bounded real Stim/PyMatching worker run through the dashboard job API."""
from __future__ import annotations
import sys, tempfile, time, unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import app as dashboard_app
import manager as manager_module
import storage
from configuration import DEFAULT_CONFIG
from seed_protocol import seed_plan, screen_plan

class MonitoringIntegrationTests(unittest.TestCase):
    def test_real_bounded_worker_persists_and_streams_measured_progress(self):
        with tempfile.TemporaryDirectory() as td:
            temp=Path(td); db=temp/'runs.sqlite3'; run_root=temp/'runs'
            cfg=dict(DEFAULT_CONFIG)
            cfg.update({'training_shots':4096,'validation_shots':1024,'test_shots':1024,
                'batch_size':128,'validation_frequency_steps':1,'checkpoint_frequency_steps':1,
                'seed':1_900_000_007,'device':'cpu','mixed_precision':False})
            plan=seed_plan(cfg['seed'],cfg['training_shots'],cfg['validation_shots'],cfg['test_shots'],cfg['batch_size'])
            self.assertTrue(screen_plan(plan)['passed'])
            with patch.object(storage,'DB_PATH',db), patch.object(dashboard_app,'RUNS_DIR',run_root), \
                 patch.object(manager_module,'RUNS_DIR',run_root):
                storage.init_db()
                with TestClient(dashboard_app.app,client=('127.0.0.1',54401)) as client:
                    response=client.post('/api/runs',json={'config':cfg})
                    self.assertEqual(response.status_code,201,response.text)
                    run_id=response.json()['run_id']
                    proc=dashboard_app.manager.processes[run_id]
                    # Attach while the real subprocess is working and verify a
                    # measured worker frame arrives over the production socket.
                    with client.websocket_connect(f'/ws/{run_id}') as websocket:
                        initial=websocket.receive_json()
                        self.assertEqual(initial['type'],'snapshot')
                        self.assertEqual(initial['run']['id'],run_id)
                        got_live_progress=False
                        for _ in range(64):
                            frame=websocket.receive_json()
                            if frame.get('type')=='progress' and frame.get('phase') in {
                                'simulation_validation','decoding_validation','training'}:
                                self.assertIsInstance(frame.get('completed_shots'),int)
                                self.assertGreater(frame.get('total_shots',0),0)
                                got_live_progress=True
                                break
                        self.assertTrue(got_live_progress,'no live measured progress frame received')
                    proc.wait(timeout=120)
                    thread=dashboard_app.manager.threads[run_id]
                    thread.join(timeout=10)
                    run=storage.get_run(run_id)
                    self.assertEqual(run['status'],'completed',run.get('error'))
                    persisted=storage.get_metrics(run_id,limit=2000)
                    progress=[x['payload'] for x in persisted if x['type']=='progress']
                    phases={x.get('phase') for x in progress}
                    self.assertIn('simulation_validation',phases)
                    self.assertIn('decoding_validation',phases)
                    self.assertIn('training',phases)
                    self.assertIn('simulation_test',phases)
                    self.assertIn('decoding_test',phases)
                    self.assertIn('analysis',phases)
                    final=progress[-1]
                    self.assertEqual(final['completed_shots'],6144)
                    self.assertEqual(final['total_shots'],6144)
                    self.assertEqual(final['progress_percent'],100.0)
                    self.assertGreater(final['throughput_shots_s'],0)
                    self.assertIsNotNone(final['eta_seconds'])
                    snapshot=client.get(f'/api/runs/{run_id}/progress')
                    self.assertEqual(snapshot.status_code,200)
                    self.assertEqual(snapshot.json()['status'],'completed')
                    self.assertEqual(snapshot.json()['progress']['completed_shots'],6144)
                    worker_log=run_root/run_id/'worker.log'
                    self.assertTrue(worker_log.is_file())
                    self.assertIn('"type":"completed"',worker_log.read_text(encoding='utf-8'))

if __name__=='__main__': unittest.main()
