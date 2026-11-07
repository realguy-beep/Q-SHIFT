import unittest, numpy as np
from experiment import (GRID, REGIME_NAMES, REGIME_DECODER, RegimeEstimator,
    AdaptivePolicy, schedule_states, POLICIES, make_circuit)

class DemoTests(unittest.TestCase):
    def test_grid_order_and_specialist_mapping(self):
        self.assertEqual(len(GRID),9); self.assertEqual(GRID[1],(.001,.003)); self.assertEqual(GRID[4],(.003,.003)); self.assertEqual(GRID[6],(.006,.001)); self.assertEqual(GRID[2],(.001,.006))
        self.assertEqual([REGIME_DECODER[x] for x in REGIME_NAMES],[6,4,2])
    def test_circuit_and_noiseless_behavior(self):
        c=make_circuit('nominal'); self.assertEqual((c.num_detectors,c.num_observables),(40,1))
        text=str(c); self.assertIn('DEPOLARIZE1(0.003)',text); self.assertIn('DEPOLARIZE2(0.003)',text); self.assertIn('X_ERROR(0.003)',text)
        c0=__import__('stim').Circuit.generated('surface_code:rotated_memory_z',distance=3,rounds=5)
        d,y=c0.compile_detector_sampler(seed=99400002).sample(shots=40,separate_observables=True)
        self.assertFalse(d.any()); self.assertFalse(y.any())
    def test_prior_block_only_and_hysteresis(self):
        prof=np.array([[.02]*4,[.5]*4,[.8]*4]); est=RegimeEstimator(prof)
        util=np.ones((3,9))*.01; util[:,1]=.03; util[0,6]=.001; util[2,2]=.001
        se=np.zeros((3,9,9)); ctl=AdaptivePolicy(est,util,se,confidence=.5,hysteresis=2,dwell=2,penalty=0)
        first,_=ctl.select_for_next_block(None); self.assertEqual(first,1)
        old,_=ctl.select_for_next_block(np.zeros((32,4),dtype=np.uint8)); self.assertEqual(old,1)
        new,_=ctl.select_for_next_block(np.ones((32,4),dtype=np.uint8)); self.assertEqual(new,1) # different best decoder resets streak
        new,_=ctl.select_for_next_block(np.zeros((32,4),dtype=np.uint8)); self.assertEqual(new,1)
        new,_=ctl.select_for_next_block(np.zeros((32,4),dtype=np.uint8)); self.assertEqual(new,6)
    def test_confidence_and_fallback(self):
        est=RegimeEstimator(np.array([[.2,.2],[.5,.5],[.8,.8]])); u=np.zeros((3,9));u[:,1]=.1;u[:,2]=.001;se=np.zeros((3,9,9))
        ctl=AdaptivePolicy(est,u,se,confidence=1.0,hysteresis=1,dwell=1,penalty=0)
        choice,post=ctl.select_for_next_block(np.array([[0,1]],dtype=np.uint8)); self.assertEqual(choice,1); self.assertIsNotNone(post)
    def test_schedules_have_expected_transitions(self):
        self.assertEqual(schedule_states('stationary').count('nominal'),12)
        self.assertEqual(schedule_states('data_to_measurement')[5:7],['data_heavy','measurement_heavy'])
        self.assertEqual(len(schedule_states('rapid_cycle')),12)
    def test_identity_baseline_is_explicit(self): self.assertEqual(POLICIES[0],'identity_no_decode')

if __name__=='__main__': unittest.main()
