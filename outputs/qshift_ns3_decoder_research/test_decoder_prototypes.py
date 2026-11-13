import unittest
from fractions import Fraction
import numpy as np
import stim

from decoder_prototypes import (BPConvergenceError, DetectorModel, ExactMAPOracle,
                                FactorGraphBP, FaultMechanism)


class DecoderTests(unittest.TestCase):
    def model(self, faults, n=2):
        return DetectorModel(n, tuple(FaultMechanism(tuple(ds), l, p) for ds,l,p in faults))

    def test_zero_syndrome_and_output_contract(self):
        m=self.model([((0,),0,.1)],n=1)
        x=np.zeros((2,1),dtype=np.uint8)
        for dec in (ExactMAPOracle(m),FactorGraphBP(m)):
            y=dec.decode_batch(x,detector_ids=(0,),observable_ids=(0,))
            self.assertEqual(y.shape,(2,1)); self.assertEqual(y.dtype,np.uint8)
            np.testing.assert_array_equal(y,np.zeros((2,1),dtype=np.uint8))

    def test_single_detector_boundary_fault(self):
        m=self.model([((0,),0,.1)],n=1)
        x=np.array([[1]],dtype=np.uint8)
        self.assertEqual(int(ExactMAPOracle(m).decode_batch(x)[0,0]),0)
        self.assertEqual(int(FactorGraphBP(m).decode_batch(x)[0,0]),0)

    def test_single_detector_logical_fault(self):
        m=self.model([((0,),1,.1)],n=1)
        x=np.array([[1]],dtype=np.uint8)
        self.assertEqual(int(ExactMAPOracle(m).decode_batch(x)[0,0]),1)
        self.assertEqual(int(FactorGraphBP(m).decode_batch(x)[0,0]),1)

    def test_two_detector_hyperedge(self):
        m=self.model([((0,1),1,.1)],n=2)
        x=np.array([[1,1]],dtype=np.uint8)
        self.assertEqual(int(ExactMAPOracle(m).decode_batch(x)[0,0]),1)
        self.assertEqual(int(FactorGraphBP(m).decode_batch(x)[0,0]),1)

    def test_multiple_faults(self):
        m=self.model([((0,),1,.1),((1,),1,.1)],n=2)
        x=np.array([[1,1]],dtype=np.uint8)
        self.assertEqual(int(ExactMAPOracle(m).decode_batch(x)[0,0]),0)

    def test_degenerate_class_sum(self):
        m=self.model([((0,),0,.1),((0,),1,.2)],n=1)
        x=np.array([[1]],dtype=np.uint8)
        self.assertEqual(int(ExactMAPOracle(m).decode_batch(x)[0,0]),1)

    def test_exact_tie_chooses_zero(self):
        m=self.model([((0,),0,.5),((0,),1,.5)],n=1)
        x=np.array([[1]],dtype=np.uint8)
        self.assertEqual(int(ExactMAPOracle(m).decode_batch(x)[0,0]),0)

    def test_repeated_mechanisms_cancel_detector_and_logical_parity(self):
        m=self.model([((0,),1,.1),((0,),1,.2)],n=1)
        x=np.array([[0],[1]],dtype=np.uint8)
        np.testing.assert_array_equal(ExactMAPOracle(m).decode_batch(x),np.array([[0],[1]],dtype=np.uint8))

    def test_repeated_targets_inside_mechanism_cancel_modulo_two(self):
        f=FaultMechanism((0,0,1,1,1),1,.1)
        self.assertEqual(f.detectors,(1,))
        m=DetectorModel(2,(f,))
        self.assertEqual(int(ExactMAPOracle(m).decode_batch(np.array([[0,1]],dtype=np.uint8))[0,0]),1)

    def test_stim_dem_probability_and_target_parsing(self):
        dem=stim.DetectorErrorModel("detector D0\ndetector D1\nerror(0.125) D0 D0 D1 L0 L0 L0\nerror(0.25) D0 L0")
        m=DetectorModel.from_stim_dem(dem)
        self.assertEqual(m.n_mechanisms,2)
        self.assertEqual(m.mechanisms[0],FaultMechanism((1,),1,.125))
        self.assertEqual(m.mechanisms[1],FaultMechanism((0,),1,.25))

    def test_exact_oracle_matches_independent_fraction_enumeration(self):
        m=self.model([((0,),1,.1),((0,1),0,.2),((1,),1,.3),((0,),0,.4)],n=2)
        x=np.array([[0,0],[0,1],[1,0],[1,1]],dtype=np.uint8)
        expected=[]
        for row in x:
            classes=[Fraction(0),Fraction(0)]
            for bits in range(1 << m.n_mechanisms):
                det=[0]*m.n_detectors; logical=0; prob=Fraction(1)
                for j,fault in enumerate(m.mechanisms):
                    fired=(bits>>j)&1; p=Fraction(str(fault.probability))
                    prob*=p if fired else (1-p)
                    if fired:
                        for d in fault.detectors: det[d]^=1
                        logical^=fault.logical
                if tuple(det)==tuple(map(int,row)):
                    classes[logical]+=prob
            expected.append(int(classes[1]>classes[0]))
        got=ExactMAPOracle(m).decode_batch(x)[:,0].tolist()
        self.assertEqual(got,expected)

    def test_probability_zero_and_one_oracle_boundaries(self):
        m=self.model([((0,),1,1.0)],n=1)
        oracle=ExactMAPOracle(m)
        self.assertEqual(int(oracle.decode_batch(np.array([[1]],dtype=np.uint8))[0,0]),1)
        with self.assertRaisesRegex(ValueError,"zero probability"):
            oracle.decode_batch(np.array([[0]],dtype=np.uint8))

    def test_bp_matches_oracle_on_tree_factor_graph(self):
        m=self.model([((0,),1,.07),((0,1),0,.11),((1,),0,.04)],n=2)
        x=np.array([[0,0],[1,0],[0,1],[1,1]],dtype=np.uint8)
        np.testing.assert_array_equal(FactorGraphBP(m,iterations=80,damping=0).decode_batch(x),
                                      ExactMAPOracle(m).decode_batch(x))

    def test_multiple_rows_and_repeatability(self):
        m=self.model([((0,),1,.1),((1,),0,.2)],n=2)
        x=np.array([[0,0],[1,0],[0,1],[1,1]],dtype=np.uint8)
        d=FactorGraphBP(m)
        a=d.decode_batch(x); b=d.decode_batch(x)
        np.testing.assert_array_equal(a,b)
        self.assertEqual(a.shape,(4,1))

    def test_invalid_shape_and_nonbinary(self):
        d=FactorGraphBP(self.model([],n=2))
        with self.assertRaises(ValueError): d.decode_batch(np.zeros(2))
        with self.assertRaises(ValueError): d.decode_batch(np.array([[0,2]]))
        with self.assertRaises(ValueError): d.decode_batch(np.array([[np.nan,0.]]))

    def test_detector_and_observable_order_guard(self):
        d=FactorGraphBP(self.model([((0,),0,.1)],n=2))
        x=np.zeros((1,2),dtype=np.uint8)
        with self.assertRaisesRegex(ValueError,"detector column IDs/order"):
            d.decode_batch(x,detector_ids=(1,0))
        with self.assertRaisesRegex(ValueError,"observable output IDs/order"):
            d.decode_batch(x,observable_ids=(1,))

    def test_input_immutability(self):
        d=FactorGraphBP(self.model([((0,),0,.1)],n=1))
        x=np.array([[1]],dtype=np.uint8); before=x.copy()
        d.decode_batch(x)
        np.testing.assert_array_equal(x,before)

    def test_bp_diagnostics_and_nonconvergence_fail_closed(self):
        m=self.model([((0,),1,.1),((1,),0,.2),((0,1),1,.3)],n=2)
        bp=FactorGraphBP(m,iterations=1,damping=0,convergence_tol=1e-20)
        x=np.array([[1,0]],dtype=np.uint8)
        pred,diag=bp.decode_batch_with_diagnostics(x)
        self.assertEqual(pred.shape,(1,1)); self.assertEqual(len(diag),1)
        self.assertFalse(diag[0].converged)
        with self.assertRaises(BPConvergenceError): bp.decode_batch(x)
        self.assertEqual(bp.decode_batch(x,allow_nonconverged=True).shape,(1,1))

    def test_bp_extreme_probabilities_are_finite_and_flagged(self):
        m=self.model([((0,),1,1e-300),((1,),0,1-1e-15)],n=2)
        bp=FactorGraphBP(m,iterations=80,damping=.5)
        pred,diag=bp.decode_batch_with_diagnostics(np.array([[0,0],[1,1]],dtype=np.uint8))
        self.assertTrue(np.all((pred==0)|(pred==1)))
        self.assertTrue(all(np.isfinite(d.logical_llr) and np.isfinite(d.max_message_delta) for d in diag))
        self.assertTrue(all(d.probability_clipped for d in diag))

    def test_model_validation(self):
        with self.assertRaises(ValueError): self.model([((1,),0,.1)],n=1)
        with self.assertRaises(ValueError): self.model([((0,),0,1.1)],n=1)
        with self.assertRaises(ValueError): DetectorModel(1,(),detector_ids=(1,))
        with self.assertRaises(ValueError): DetectorModel(1,(),observable_ids=(1,))

    def test_oracle_cap(self):
        m=self.model([((0,),0,.1)]*8,n=1)
        with self.assertRaisesRegex(ValueError,"oracle cap exceeded"):
            ExactMAPOracle(m,max_states=128)

    def test_impossible_syndrome(self):
        m=self.model([((0,),0,0.0)],n=1)
        with self.assertRaisesRegex(ValueError,"zero probability"):
            ExactMAPOracle(m).decode_batch(np.array([[1]],dtype=np.uint8))


if __name__ == '__main__':
    unittest.main(verbosity=2)
