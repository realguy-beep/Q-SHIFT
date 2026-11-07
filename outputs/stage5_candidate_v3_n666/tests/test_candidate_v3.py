import json,sys,unittest
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from stage5_statistics_candidate import analyze
from stage5_saved_array_audit_candidate import independent_statistics

class TestCandidateV3(unittest.TestCase):
    def setUp(self):
        self.cfg=json.loads((HERE/'STAGE5_V3_CANDIDATE_CONFIG.json').read_text(encoding='utf-8'))
        self.groups={p:np.asarray([(-0.00035 if p else 0.0)+((i%7)-3)*1e-6 for i in range(11)],float)
                     for p in (0.0,.004,.008,.012,.016)}

    def test_runner_and_independent_statistics_agree(self):
        a=analyze(self.groups,self.cfg,11)
        b=independent_statistics(self.groups,self.cfg,11)
        for key in ('primary_delta','primary_standard_error','primary_df_reference','primary_t_statistic_at_boundary',
                    'primary_one_sided_upper_bound','p0_mean_difference','p0_standard_error','p0_upper_bound'):
            self.assertAlmostEqual(a[key],b[key],places=14)
        self.assertEqual(a['primary_calibrated_reject'],b['primary_calibrated_reject'])
        self.assertEqual(a['secondary_welch_p_holm_descriptive'],b['secondary_welch_p_holm_descriptive'])

    def test_seed_inventory_cardinality_and_unique_streams(self):
        inv=json.loads((HERE/'STAGE5_V3_SEED_INVENTORY.json').read_text(encoding='utf-8'))
        self.assertEqual(len(inv['streams']),6660)
        seeds=[x['seed'] for x in inv['streams']]
        self.assertEqual(len(seeds),len(set(seeds)))
        self.assertEqual(inv['collision_count'],0)
        self.assertEqual(inv['stage5_evaluation_shots_generated'],0)

    def test_candidate_is_not_sampled(self):
        self.assertFalse((HERE/'run').exists())
        cfg=self.cfg
        self.assertEqual(cfg['data_boundary']['stage5_shots_generated'],0)
        self.assertFalse(cfg['data_boundary']['sealed_historical_test_accessed'])

if __name__=='__main__': unittest.main()
