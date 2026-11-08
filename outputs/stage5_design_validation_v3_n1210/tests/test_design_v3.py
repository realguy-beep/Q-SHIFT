import json
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import design_mc as sim

HERE=Path(__file__).resolve().parents[1]

class DesignV3Tests(unittest.TestCase):
    def test_allocation_and_scenario_completeness(self):
        cfg=json.loads((HERE/'DESIGN_CONFIG.json').read_text())
        self.assertEqual(cfg['allocation_roots_per_stratum'],1210)
        self.assertEqual(cfg['stage5_shot_projection']['total_projected_if_later_authorized'],27_225_000)
        self.assertEqual(len(cfg['null_scenarios']),11)
        self.assertEqual(len(cfg['power_scenarios']),10)
        self.assertTrue(any(x['name']=='zero_inflated65_q2' for x in cfg['power_scenarios']))
        self.assertEqual(sum(x['formal_gate'] for x in cfg['power_scenarios']),5)

    def test_studentized_equal_weight_fixture(self):
        values=np.array([[[1.,2.,3.],[2.,3.,4.],[0.,1.,2.],[4.,5.,6.]]])
        estimate,se,t,df=sim.stat(values,0.)
        self.assertAlmostEqual(float(estimate[0]),2.75)
        self.assertGreater(float(se[0]),0.)
        self.assertGreater(float(t[0]),0.)
        self.assertGreater(float(df[0]),1.)

    def test_distribution_moments_and_zero_mass(self):
        rng=np.random.Generator(np.random.PCG64(5566778899))
        mu=np.array([-.0002,.0001,.0003,.0]); sd=np.array([.001,.0012,.0015,.0008])
        for family in ['normal','student_t5','student_t3','lognormal_sigma1','zero_inflated65_normal','tied_asymmetric65']:
            arr=sim.draw(rng,12000,1,mu[:1],sd[:1],family)[:,0,0]
            self.assertLess(abs(float(arr.mean())-mu[0]),.00008,family)
            self.assertLess(abs(float(arr.std(ddof=1)/sd[0])-1),.07,family)
            if family in {'zero_inflated65_normal','tied_asymmetric65'}:
                self.assertLess(abs(float(np.mean(arr==0))-.65),.015,family)

    def test_frozen_seed_inventory_unique_and_separated(self):
        inv=json.loads((HERE/'DESIGN_SEED_INVENTORY.json').read_text())
        seeds=[x['seed'] for x in inv['rng_streams']]
        self.assertEqual(len(seeds),len(set(seeds)))
        self.assertEqual(inv['collision_count'],0)
        self.assertFalse(inv['stage5_evaluation_seeds_allocated'])
        self.assertEqual(inv['stage5_evaluation_shots_generated'],0)

if __name__=='__main__': unittest.main()
