"""Deterministic Pilot 2 integrity/correctness regression tests."""
import unittest
import numpy as np
import stim
from outputs.qshift_v2_pilot2_v1.controller import EventGLR, categories
from outputs.qshift_v2_pilot2_v1.run_pilot2 import replay_stream, score_predictions, discordance_counts, build, BLOCK, POLS

class FakeMatcher:
    def __init__(self, mode): self.mode=mode; self.calls=0
    def decode_batch(self,d,enable_correlations=False):
        self.calls+=1
        if bool(enable_correlations)!=self.mode: raise AssertionError('correlation decode flag mismatch')
        return np.zeros(len(d),dtype=np.uint8)

class StubEstimator:
    probabilities=np.array([0.,.02]); grid_step=.01
    means=np.zeros((2,45)); scales=np.ones(45)
    def estimate(self,d):
        a=np.asarray(d)
        return float(np.clip(np.mean(a[:,8]&a[:,10])*.02,0,.02))

class Pilot2Tests(unittest.TestCase):
    def test_pair_summary_shape_and_categories(self):
        d=np.zeros((5,40),dtype=np.uint8); d[:,8]=1; d[:,10]=1
        np.testing.assert_array_equal(categories(d,'all5'),np.ones(5,dtype=np.int8))
        np.testing.assert_array_equal(categories(d,'first3'),np.ones(5,dtype=np.int8))
        np.testing.assert_array_equal(categories(d,'any5'),np.ones(5,dtype=np.int8))
        with self.assertRaises(ValueError): categories(d,'unknown')

    def test_event_switches_only_after_completed_block(self):
        grid=np.linspace(0,.02,11); lik=np.full((11,6),.02); lik[:,0]=.90; lik[:,1:]=.02
        lik[0,0]=.10; lik[0,1:]=.18
        ev=EventGLR(grid,lik,0.,.1,2,1,0.,'all5')
        d=np.zeros((50,40),dtype=np.uint8)
        p,alarm,_=ev.observe(d,lambda:.02)
        self.assertFalse(alarm); self.assertEqual(p,0.)
        p,alarm,_=ev.observe(d,lambda:.02)
        self.assertTrue(alarm); self.assertAlmostEqual(p,.02); self.assertEqual(ev.switches,1)
        self.assertGreaterEqual(ev.raw_crossings,1)

    def test_future_detector_rows_cannot_change_earlier_graphs(self):
        rng=np.random.default_rng(7531); warm=rng.integers(0,2,(200,40),dtype=np.uint8)
        d=rng.integers(0,2,(150,40),dtype=np.uint8); obs=np.zeros(150,dtype=np.uint8)
        grid=np.linspace(0,.02,11); lik=np.full((11,6),1/6)
        candidate={'threshold':1e9,'history_blocks':2,'min_dwell_blocks':2,'hysteresis':.002,'profile_window':100,'pair_summary':'all5'}
        bank={(mode,float(p)):FakeMatcher(mode) for mode in (False,True) for p in grid}
        kwargs=(warm,obs,'step_up',StubEstimator(),candidate,lik,grid,bank,.004,150,{},[0.])
        pred1,ids1,ends1,*_=replay_stream(d,*kwargs)
        changed=d.copy(); changed[100:]=1-changed[100:]
        pred2,ids2,ends2,*_=replay_stream(changed,*kwargs)
        for method in POLS:
            np.testing.assert_array_equal(ids1[method][:3],ids2[method][:3])
            np.testing.assert_array_equal(ends1[method][:3],ends2[method][:3])
        self.assertEqual(len(pred1[False]['event_glr']),150) # warm-up excluded from score
        np.testing.assert_array_equal(pred1[False]['event_glr'],pred2[False]['event_glr'])

    def test_explicit_decoder_mode_and_deterministic_sampling(self):
        m0=FakeMatcher(False); m1=FakeMatcher(True); d=np.zeros((4,40),dtype=np.uint8)
        score_predictions(m0,d,False); score_predictions(m1,d,True)
        for mode in (False,True):
            circuit,dem,matcher=build(0.0,mode)
            sample=circuit.compile_detector_sampler(seed=77201).sample(4)
            pred=score_predictions(matcher,sample,mode)
            self.assertEqual(pred.shape,(4,))
        c=stim.Circuit('R 0\nX_ERROR(0.02) 0\nM 0\nDETECTOR rec[-1]')
        a=c.compile_detector_sampler(seed=982347).sample(64)
        b=c.compile_detector_sampler(seed=982347).sample(64)
        np.testing.assert_array_equal(a,b)

    def test_frozen_unique_shot_allocation(self):
        import json
        from pathlib import Path
        out=Path(__file__).resolve().parent
        cfg=json.loads((out/'PILOT2_CONFIG.json').read_text(encoding='utf-8'))
        inv=json.loads((out/'PILOT2_SEED_INVENTORY.json').read_text(encoding='utf-8'))
        self.assertEqual(sum(x['shots'] for x in inv['samples']),cfg['allocation']['planned_unique_shots'])
        self.assertLessEqual(cfg['allocation']['planned_unique_shots'],300000)

    def test_paired_outcome_alignment_is_lossless(self):
        obs=np.array([0,1,0,1],dtype=np.uint8)
        pa=np.array([0,1,1,0],dtype=np.uint8); pb=np.array([1,1,0,0],dtype=np.uint8)
        ea=(pa^obs).astype(bool); eb=(pb^obs).astype(bool)
        both=int(np.count_nonzero(ea&eb)); aonly=int(np.count_nonzero(ea&~eb)); bonly=int(np.count_nonzero(~ea&eb)); neither=int(np.count_nonzero(~ea&~eb))
        self.assertEqual(both+aonly+bonly+neither,len(obs))
        self.assertEqual(aonly-bonly,int(ea.sum()-eb.sum()))
        self.assertEqual(discordance_counts(pa^obs,pb^obs),(both,aonly,bonly,neither))

if __name__=='__main__': unittest.main(verbosity=2)
