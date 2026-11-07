import ast
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from outputs.stage5_preexecution_v1 import stage5_runner as runner
from outputs.stage5_preexecution_v1 import stage5_statistics as runner_stats
from outputs.stage5_preexecution_v1 import stage5_saved_array_audit as audit
from outputs.stage5_preexecution_v1.review_power import power_review

HERE=Path(__file__).resolve().parents[1]

class Stage5PreflightTests(unittest.TestCase):
    def test_inventory_exactly_1000_streams_and_1002_unique_values(self):
        inv=json.loads((HERE/'seed_inventory.json').read_text(encoding='utf-8'))
        streams,_=runner.seed_map()
        self.assertEqual(len(streams),1000)
        self.assertEqual(len(set(streams.values())|set(inv['analysis_rngs'].values())),1002)

    def test_profile_estimator_independent_reimplementation(self):
        profile=runner.load_profile()
        # Hand-built detector fixture; no Stim sampling or Stage 5 evaluation data.
        d=np.zeros((257,40),dtype=np.uint8)
        for i in range(257):
            d[i,(i*11)%40]=1
            if i%3==0: d[i,(i*11+2)%40]=1
        self.assertAlmostEqual(profile.estimate(d),audit.independent_estimate(
            d,json.loads((HERE/'FROZEN_PROFILE_ESTIMATOR.json').read_text(encoding='utf-8'))),places=12)

    def test_auditor_rebuilt_matching_decodes_synthetic_zero_fixture(self):
        matcher=audit.independent_matcher(0.)
        pred=audit.decode(matcher,np.zeros((128,40),dtype=np.uint8))
        self.assertEqual(pred.shape,(128,))
        self.assertFalse(np.any(pred))

    def test_runner_is_inert_without_two_explicit_flags(self):
        self.assertEqual(runner.main([]),2)
        self.assertEqual(runner.main(['--run']),2)
        self.assertEqual(runner.main(['--authorize-stage5-sampling']),2)
        self.assertFalse(runner.RUN.exists())

    def test_durable_calibration_checkpoint_can_resume_without_regeneration(self):
        seeds,_=runner.seed_map(); sc=seeds[('calibration_detector_only',0.,0)]; se=seeds[('paired_evaluation_detector_observable',0.,0)]
        cal=np.zeros((2000,40),dtype=np.uint8)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'root_p0.000_r000.npz'
            runner.atomic_npz(path,phase=np.asarray('calibration_complete'),calibration_detectors=cal,
                probability=np.asarray(0.),root=np.asarray(0),seed_calibration=np.asarray(sc))
            phase,saved,det,obs=runner._partial_read(path,sc,se,0.,0)
            self.assertEqual(phase,'calibration_complete')
            np.testing.assert_array_equal(saved,cal)
            self.assertIsNone(det); self.assertIsNone(obs)

    def test_completed_checkpoint_is_independently_redecoded_before_resume(self):
        seeds,_=runner.seed_map(); sc=seeds[('calibration_detector_only',0.,0)]; se=seeds[('paired_evaluation_detector_observable',0.,0)]
        profile=runner.load_profile(); cal=np.zeros((2000,40),dtype=np.uint8); det=np.zeros((2500,40),dtype=np.uint8)
        p_hat=profile.estimate(cal); obs=np.zeros(2500,dtype=np.uint8)
        fixed=runner.build_decoder(0.)[2]; adaptive=runner.build_decoder(p_hat)[2]; oracle=runner.build_decoder(0.)[2]
        predictions=np.zeros((3,2500),dtype=np.uint8)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'root_p0.000_r000.npz'
            runner.atomic_npz(path,phase=np.asarray('complete'),calibration_detectors=cal,evaluation_detectors=det,
                observables=obs,predictions=predictions,p_hat=np.asarray(p_hat),probability=np.asarray(0.),
                root=np.asarray(0),seed_calibration=np.asarray(sc),seed_evaluation=np.asarray(se))
            runner.validate_complete(path,0.,0,sc,se,profile,fixed,oracle)
            bad=predictions.copy(); bad[1,0]=1
            runner.atomic_npz(path,phase=np.asarray('complete'),calibration_detectors=cal,evaluation_detectors=det,
                observables=obs,predictions=bad,p_hat=np.asarray(p_hat),probability=np.asarray(0.),
                root=np.asarray(0),seed_calibration=np.asarray(sc),seed_evaluation=np.asarray(se))
            with self.assertRaisesRegex(ValueError,'prediction mismatch'):
                runner.validate_complete(path,0.,0,sc,se,profile,fixed,oracle)

    def test_auditor_does_not_import_runner_or_reporting_statistics(self):
        tree=ast.parse((HERE/'stage5_saved_array_audit.py').read_text(encoding='utf-8'))
        imported=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom): imported.append(node.module or '')
            elif isinstance(node,ast.Import): imported.extend(x.name for x in node.names)
        self.assertFalse(any('stage5_runner' in x or 'stage5_statistics' in x for x in imported))

    def test_root_cluster_statistics_independently_recompute(self):
        # Deterministic synthetic root effects exercise analysis only, not sample generation.
        groups={p:np.array([((i%9)-4)*(1e-5+p/1000) for i in range(100)],float)
                for p in (0.,.004,.008,.012,.016)}
        cfg=json.loads((HERE/'STAGE5_V2_CONFIG.json').read_text(encoding='utf-8'))
        cfg['statistical_plan']['bootstrap']['resamples']=64
        cfg['statistical_plan']['primary_signflip']['assignments']=64
        left=runner_stats.analyze(groups,bootstrap_n=64,signflip_n=64)
        right=audit.independent_stats(groups,cfg)
        for key in ('primary_delta','primary_bootstrap_95ci','primary_signflip_p',
                    'secondary_signflip_p_raw','secondary_signflip_p_holm',
                    'zero_burst_one_sided_bootstrap_95_upper'):
            self.assertTrue(np.allclose(np.asarray(left[key],float),np.asarray(right[key],float),rtol=0,atol=1e-15),key)

    def test_binary_prediction_and_logical_residual_convention(self):
        obs=np.array([0,1,1,0],dtype=np.uint8)
        pred=np.array([0,0,1,1],dtype=np.uint8)
        self.assertEqual(np.bitwise_xor(pred,obs).tolist(),[0,1,0,1])

    def test_candidate_plan_cited_by_new_protocol_remains_unchanged(self):
        c=json.loads((HERE/'STAGE5_V2_CONFIG.json').read_text(encoding='utf-8'))
        self.assertEqual(c['evaluation']['total_unique_shots'],2_250_000)
        self.assertEqual(c['independent_test']['accessed'],False)

    def test_power_inputs_recompute_from_seven_roots_per_condition(self):
        p=power_review()
        self.assertEqual([x['stage4_development_n'] for x in p['per_condition']],[7]*4)
        self.assertEqual([x['stage4c_n'] for x in p['per_condition']],[7]*4)
        self.assertAlmostEqual(p['equal_stratum_mean_se'],0.0000643,places=7)
        self.assertAlmostEqual(p['power_two_sided_reject_zero_at_true_delta_minus_0.0002_normal_approx'],0.875,delta=0.01)
        self.assertAlmostEqual(p['probability_primary_point_estimate_at_or_below_minus_0.0002_at_boundary'],0.5)

if __name__=='__main__': unittest.main()
