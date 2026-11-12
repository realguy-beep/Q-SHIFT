from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from outputs.qshift_advanced_research_v3a.qshift_estimators import (
    CandidateA, CandidateB, EstimatorInputError, FEATURE_COUNT, TemplateBank,
    detector_features,
)

BASE=Path(__file__).resolve().parents[1]
BANK_PATH=BASE/'template_bank_v1.json'


class QShiftEstimatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bank=TemplateBank.load(BANK_PATH)

    def test_feature_extraction_and_pair_feature_indices(self):
        d=np.zeros((3,40),dtype=np.uint8)
        d[0,[8,10]]=1
        d[1,[16,18]]=1
        d[2,[36,38]]=1
        f=detector_features(d)
        self.assertEqual(f.shape,(3,45))
        self.assertEqual(f[0,40],1)
        self.assertEqual(f[1,41],1)
        self.assertEqual(f[2,44],1)
        self.assertEqual(int(f[:,:40].sum()),6)
        self.assertEqual(int(f[:,40:45].sum()),3)

    def test_candidate_b_recovers_nominal_and_mismatch_population_means(self):
        estimator=CandidateB(self.bank,'exact_categorical')
        for expected in ((.008,.003),(.008,.006)):
            mean=self.bank.interpolated('exact_categorical',*expected)
            estimate=estimator.estimate_mean(mean)
            self.assertEqual((estimate.p_burst,estimate.p_measurement),expected)
            self.assertLess(estimate.objective,1e-20)

    def test_source_faithful_candidate_a_population_limit(self):
        estimator=CandidateA(self.bank,'exact_categorical')
        nominal=self.bank.interpolated('exact_categorical',.008,.003)
        mismatch=self.bank.interpolated('exact_categorical',.008,.006)
        self.assertAlmostEqual(estimator.estimate_mean(nominal).p_burst,.008,places=8)
        result=estimator.estimate_mean(mismatch)
        self.assertAlmostEqual(result.p_burst,.01091,places=8)
        self.assertEqual(result.p_measurement,.003)
        self.assertEqual(len(np.linspace(0,.020,2001)),2001)

    def test_parameter_boundaries_and_boundary_reporting(self):
        estimator=CandidateB(self.bank,'exact_categorical')
        for p in ((0.,0.),(.020,.010)):
            result=estimator.estimate_mean(self.bank.interpolated('exact_categorical',*p))
            self.assertEqual((result.p_burst,result.p_measurement),p)
            self.assertTrue(result.boundary_hit)

    def test_exact_ties_choose_lowest_burst_then_measurement(self):
        table=np.full((21,11,45),.25,dtype=np.float64)
        provenance={'gate_p':.003,'test_bank':True}
        bank=TemplateBank.from_tables(table,table.copy(),provenance)
        target=np.full(45,.25)
        result=CandidateB(bank,'exact_categorical').estimate_mean(target)
        self.assertEqual((result.p_burst,result.p_measurement),(0.,0.))

    def test_malformed_detector_and_mean_inputs_are_rejected(self):
        with self.assertRaises(EstimatorInputError): detector_features(np.zeros((4,39)))
        with self.assertRaises(EstimatorInputError): detector_features(np.zeros((0,40)))
        bad=np.zeros((2,40)); bad[0,2]=.5
        with self.assertRaises(EstimatorInputError): detector_features(bad)
        nan=np.zeros((2,40)); nan[0,0]=np.nan
        with self.assertRaises(EstimatorInputError): detector_features(nan)
        with self.assertRaises(EstimatorInputError):
            CandidateB(self.bank,'exact_categorical').estimate_mean(np.zeros(44))
        invalid=np.zeros(45); invalid[0]=1.01
        with self.assertRaises(EstimatorInputError):
            CandidateA(self.bank,'exact_categorical').estimate_mean(invalid)
        with self.assertRaises(EstimatorInputError): CandidateB(self.bank,'mixed')

    def test_template_serialization_round_trip_and_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'bank.json'
            digest=self.bank.save(target)
            loaded=TemplateBank.load(target)
            self.assertEqual(len(digest),64)
            for family in ('exact_categorical','approximate_dem'):
                np.testing.assert_array_equal(loaded.means[family],self.bank.means[family])
                np.testing.assert_array_equal(loaded.scales[family],self.bank.scales[family])
            payload=json.loads(target.read_text())
            self.assertEqual(payload['schema_version'],'qshift-template-bank-v1')
            self.assertEqual(payload['feature_definition']['features'],FEATURE_COUNT)
            payload['feature_definition']['pairs'][0]=[7,10]
            target.write_text(json.dumps(payload))
            with self.assertRaises(EstimatorInputError): TemplateBank.load(target)

    def test_template_families_and_gate_provenance_are_separate(self):
        self.assertEqual(self.bank.provenance['gate_p'],.003)
        exact=self.bank.means['exact_categorical']
        dem=self.bank.means['approximate_dem']
        self.assertGreater(float(np.max(np.abs(exact-dem))),1e-6)
        exact_result=CandidateB(self.bank,'exact_categorical').estimate_mean(
            self.bank.interpolated('exact_categorical',.008,.006))
        dem_result=CandidateB(self.bank,'approximate_dem').estimate_mean(
            self.bank.interpolated('approximate_dem',.008,.006))
        self.assertEqual(exact_result.family,'exact_categorical')
        self.assertEqual(dem_result.family,'approximate_dem')

    def test_gate_noise_sensitivity_is_documented_not_estimated(self):
        sensitivity=json.loads((ROOT/'outputs/qshift_advanced_decoder_research_v2c_review' /
                                'guard_distribution_results.json').read_text())['fixed_gate_noise_sensitivity']
        fits=sensitivity['population_fits_with_templates_fixed_at_gate_p_003']
        self.assertEqual(fits['0.002']['exact_truth_fit_exact_templates'],[.0083,.0004])
        self.assertEqual(fits['0.004']['exact_truth_fit_exact_templates'],[.0077,.0056])
        # Estimator APIs accept only a template family, not a gate parameter.
        self.assertEqual(self.bank.provenance['gate_p'],.003)

    def test_frozen_phase2c_sources_match_their_reviewed_hash_manifest(self):
        manifest=json.loads((ROOT/'outputs/qshift_advanced_decoder_research_v2c_review' /
                             'SOURCE_MANIFEST.json').read_text())
        entries=[e for e in manifest['source_files']
                 if e['path'].startswith('outputs/qshift_advanced_decoder_research_v2c/')]
        self.assertGreaterEqual(len(entries),8)
        import hashlib
        for entry in entries:
            actual=hashlib.sha256((ROOT/entry['path']).read_bytes()).hexdigest()
            self.assertEqual(actual,entry['sha256'],entry['path'])

    def test_future_runner_fails_closed_without_explicit_authorization(self):
        from outputs.qshift_advanced_research_v3a.run_finite_history_study import validate_authorization
        config=json.loads((BASE/'finite_history_study_config.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            auth=Path(tmp)/'authorization.json'
            auth.write_text('{}')
            absent_seed_manifest=Path(tmp)/'must-not-be-opened.json'
            with self.assertRaises(PermissionError):
                validate_authorization(auth,absent_seed_manifest,BASE/'finite_history_study_config.json',
                                       BANK_PATH,config)

    def test_study_protocol_config_allocation_is_internally_consistent(self):
        config=json.loads((BASE/'finite_history_study_config.json').read_text())
        self.assertEqual(config['status'],'proposal_not_authorized')
        self.assertEqual(config['sampling_authorized'],False)
        for scenario,segments in config['conditions'].items():
            self.assertEqual(sum(s['shots'] for s in segments),config['shots_per_root'],scenario)
        self.assertEqual(config['history_lengths'],[200,1000,5000,10000])

    def test_study_analysis_uses_paired_root_strata_deterministically(self):
        from outputs.qshift_advanced_research_v3a.analyze_finite_history_study import analyze_payload
        records=[]
        errors={'measurement_step_up':([.004,.006,.008],[.001,.003,.002]),
                'measurement_step_down':([.006,.008,.010],[.002,.003,.004])}
        for scenario,(aerr,berr) in errors.items():
            for i in range(3):
                for arm,error in (('A',aerr[i]),('B',berr[i])):
                    records.append({'split':'heldout_development','scenario':scenario,
                        'template_family':'exact_categorical','history_length':1000,
                        'history_end_exclusive':6000,'next_block_start':6000,
                        'root_id':f'{scenario}-{i}','arm':arm,
                        'truth_p_burst':.008,'p_burst':.008+error,
                        'truth_p_measurement':.006,'p_measurement':.006})
        out=analyze_payload({'records':records})
        self.assertLess(out['primary_interval']['estimate_B_minus_A'],0)
        self.assertEqual(out['primary_strata']['measurement_step_up']['root_count'],3)
        self.assertEqual(out['sampling_performed_by_analysis'],False)


if __name__=='__main__':
    unittest.main(verbosity=2)
