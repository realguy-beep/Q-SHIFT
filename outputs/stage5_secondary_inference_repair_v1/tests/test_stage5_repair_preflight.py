from __future__ import annotations
import json, subprocess, sys, unittest
from pathlib import Path
from unittest.mock import patch
import tempfile
import numpy as np

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import stage5_statistics_repaired as stats
import stage5_sampling_runner as runner
from audit_reporting_bounds import audit as audit_reporting


class Stage5RepairTests(unittest.TestCase):
    def test_amended_analysis_keeps_endpoint_and_four_holm_pvalues(self):
        cfg=json.loads((HERE/'STAGE5_REPAIR_CONFIG.json').read_text(encoding='utf-8'))
        n=1210
        groups={0.0:np.zeros(n)}
        for index,p in enumerate((.004,.008,.012,.016)):
            groups[p]=np.linspace(-.0005+index*.00002,.0001+index*.00002,n)
        refs=[np.linspace(-5,5,2001) for _ in range(6)]
        fingerprints=[{'family':str(i),'n':2001,'sha256_sorted_t':str(i)} for i in range(6)]
        with patch.object(stats,'calibrated_secondary_reference',return_value=(refs,.001,{'0.0125':-2.6,'0.05':-1.8},fingerprints)):
            result=stats.analyze(groups,cfg,n)
        self.assertEqual(result['primary_boundary'],-.0002)
        self.assertEqual(result['primary_calibrated_critical'],1.7816207021549997)
        self.assertEqual(len(result['secondary_finite_envelope_p_raw']),4)
        self.assertEqual(len(result['secondary_finite_envelope_p_holm']),4)
        self.assertEqual(len(result['secondary_condition_details']),4)
        self.assertTrue(all('simultaneous_upper_95_bound' in x for x in result['secondary_condition_details'].values()))

    def test_no_sampling_flags_never_enter_execution(self):
        runner=HERE/'stage5_sampling_runner.py'
        proc=subprocess.run([sys.executable,str(runner)],capture_output=True,text=True,timeout=30)
        self.assertEqual(proc.returncode,2)
        self.assertIn('No sampling started',proc.stdout)
        self.assertFalse((HERE/'run').exists())

    def test_one_sampling_flag_is_insufficient(self):
        script=HERE/'stage5_sampling_runner.py'
        for args in (['--run'],['--authorize-stage5-sampling']):
            proc=subprocess.run([sys.executable,str(script),*args],capture_output=True,text=True,timeout=30)
            self.assertEqual(proc.returncode,2)
            self.assertIn('No sampling started',proc.stdout)
        self.assertFalse((HERE/'run').exists())

    def test_stage5_inventory_is_separate_and_complete(self):
        inv=json.loads((HERE/'STAGE5_SAMPLE_SEED_INVENTORY.json').read_text(encoding='utf-8'))
        seeds=[x['seed'] for x in inv['streams']]
        self.assertEqual(len(seeds),12100)
        self.assertEqual(len(set(seeds)),12100)
        self.assertEqual(inv['collision_count'],0)
        self.assertEqual(inv['stage5_evaluation_shots_generated'],0)
        self.assertFalse(inv['sealed_historical_test_accessed'])

    def test_failed_evaluation_stream_cannot_resume_from_calibration_only_checkpoint(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            f=root/runner.filename(.004,0)
            runner.atomic_npz(f,phase=np.asarray('calibration_complete'),probability=np.asarray(.004),
                root=np.asarray(0),seed_calibration=np.asarray(14000000001))
            with self.assertRaisesRegex(RuntimeError,'no durable checkpoint'):
                runner.verify_inflight_checkpoint(root,{'kind':'evaluation','p':.004,'root':0})

    def test_durable_evaluation_checkpoint_allows_resume_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            f=root/runner.filename(.004,0)
            runner.atomic_npz(f,phase=np.asarray('evaluation_complete'),probability=np.asarray(.004),
                root=np.asarray(0),seed_calibration=np.asarray(14000000001))
            self.assertEqual(runner.verify_inflight_checkpoint(root,{'kind':'evaluation','p':.004,'root':0}),
                             'evaluation_complete')

    def test_reporting_intervals_are_independently_recomputed(self):
        result=audit_reporting()
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['recomputed_interval_counts']['fwer'],516)
        self.assertTrue(result['gate_summary']['overall_secondary_method_pass'])


if __name__=='__main__': unittest.main()
