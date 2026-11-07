import unittest, sys
from pathlib import Path
import numpy as np
import stim
P=Path(__file__).resolve().parent; ROOT=P.parents[1]
sys.path.insert(0,str(ROOT/'outputs/prototype_development'))
sys.path.insert(0,str(P))
from experiment import GRID
from analyze_phase2a import wilson, exact_mcnemar, holm, cluster_bootstrap
from decoder_bank import build_bank

class Phase2ATests(unittest.TestCase):
    def test_grid_order(self):
        self.assertEqual(GRID,tuple((g,m) for g in (.001,.003,.006) for m in (.001,.003,.006)))
    def test_native_noise_and_surface_circuit(self):
        c=stim.Circuit.generated('surface_code:rotated_memory_z',distance=3,rounds=5,after_clifford_depolarization=.003,before_measure_flip_probability=.006)
        self.assertEqual((c.num_detectors,c.num_observables),(40,1)); t=str(c)
        self.assertIn('DEPOLARIZE1(0.003)',t); self.assertIn('DEPOLARIZE2(0.003)',t); self.assertIn('X_ERROR(0.006)',t)
    def test_bank_shared_topology_distinct_weights(self):
        bank=build_bank(); self.assertEqual(len(bank),9)
        top=[]; weighted=[]
        import hashlib
        for m in bank:
            e=m.edges(); top.append(hashlib.sha256(repr(sorted((min(-1 if u is None else u,-1 if v is None else v),max(-1 if u is None else u,-1 if v is None else v)) for u,v,_ in e)).encode()).hexdigest())
            weighted.append(tuple(sorted(round(a['weight'],8) for _,_,a in e)))
        self.assertEqual(len(set(top)),1); self.assertEqual(len(set(weighted)),9)
    def test_statistics_helpers(self):
        lo,hi=wilson(0,100); self.assertGreaterEqual(lo,0); self.assertLess(lo,1e-12); self.assertGreater(hi,0)
        self.assertEqual(exact_mcnemar(0,0),(1.0,0.0)); self.assertAlmostEqual(exact_mcnemar(5,5)[0],1.0)
        self.assertEqual(holm([.01,.04,.03]),[.03,.06,.06])
    def test_paired_decoder_shapes_and_outputs(self):
        m=build_bank(); c=stim.Circuit.generated('surface_code:rotated_memory_z',distance=3,rounds=5,after_clifford_depolarization=.003,before_measure_flip_probability=.003)
        d,y=c.compile_detector_sampler(seed=99880001).sample(shots=16,separate_observables=True); pred=np.stack([x.decode_batch(d)[:,0] for x in m])
        self.assertEqual(pred.shape,(9,16)); self.assertTrue(set(np.unique(pred)).issubset({0,1}))

if __name__=='__main__': unittest.main()
