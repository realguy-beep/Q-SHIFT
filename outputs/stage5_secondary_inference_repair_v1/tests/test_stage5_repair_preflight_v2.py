from __future__ import annotations
import json, subprocess, sys, tempfile, unittest
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import stage5_sampling_runner_v2 as runner


class Stage5V2PreflightTests(unittest.TestCase):
    def test_sampling_guard_needs_both_flags(self):
        script=HERE/'stage5_sampling_runner_v2.py'
        for args in ([],['--run'],['--authorize-stage5-sampling']):
            proc=subprocess.run([sys.executable,str(script),*args],capture_output=True,text=True,timeout=30)
            self.assertEqual(proc.returncode,2)
            self.assertIn('No sampling started',proc.stdout)
        self.assertFalse((HERE/'run').exists())

    def test_v2_seed_formula_and_allocation(self):
        seeds,inv=runner.seed_map()
        self.assertEqual(len(seeds),12100)
        self.assertEqual(inv['distinct_recoverable_historical_integer_values_screened'],11464)
        self.assertEqual(seeds[('calibration_detector_only',0.0,0)],14000000001)
        self.assertEqual(seeds[('calibration_detector_only',0.004,0)],14000001211)
        self.assertEqual(seeds[('paired_evaluation_detector_observable',0.0,0)],14000006051)
        self.assertEqual(seeds[('paired_evaluation_detector_observable',0.016,1209)],14000012100)

    def test_resume_rejects_unpersisted_or_wrong_phase_rng_stream(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            inflight={'kind':'evaluation','p':.004,'root':0}
            with self.assertRaisesRegex(RuntimeError,'no checkpoint'):
                runner.verify_inflight_checkpoint(root,inflight)
            path=root/runner.filename(.004,0)
            runner.atomic_npz(path,phase=np.asarray('calibration_complete'))
            with self.assertRaisesRegex(RuntimeError,'no durable checkpoint'):
                runner.verify_inflight_checkpoint(root,inflight)
            runner.atomic_npz(path,phase=np.asarray('evaluation_complete'))
            self.assertEqual(runner.verify_inflight_checkpoint(root,inflight),'evaluation_complete')

    def test_inventories_remain_unexecuted(self):
        inv=json.loads((HERE/'STAGE5_SAMPLE_SEED_INVENTORY.json').read_text(encoding='utf-8'))
        self.assertEqual(inv['stage5_evaluation_shots_generated'],0)
        self.assertFalse(inv['sealed_historical_test_accessed'])
        self.assertEqual(inv['collision_count'],0)
        self.assertEqual(inv['stream_count'],12100)


if __name__=='__main__': unittest.main()
