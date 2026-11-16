import unittest, itertools, math, pathlib, sys
import numpy as np, stim
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from factor_bp import FactorBP
class BPTests(unittest.TestCase):
 def test_exhaustive_tree_reference(self):
  dem=stim.DetectorErrorModel('error(0.1) D0 L0\nerror(0.2) D0\nerror(0.3) L0\ndetector D0\nlogical_observable L0')
  d=FactorBP(dem)
  for syndrome in (0,1):
   joint=[0.,0.]
   for a,b,c in itertools.product((0,1),repeat=3):
    if a^b != syndrome: continue
    probability=math.prod(p if bit else 1-p for bit,p in zip((a,b,c),(.1,.2,.3)))
    joint[a^c]+=probability
   self.assertAlmostEqual(d.decode_one([syndrome])['p1'],joint[1]/sum(joint),places=6)
 def test_degenerate_logical_parity(self):
  dem=stim.DetectorErrorModel('error(0.2) D0 L0\nerror(0.1) L0\ndetector D0\nlogical_observable L0')
  d=FactorBP(dem)
  self.assertAlmostEqual(d.decode_one([0])['p1'],0.1,places=6)
  self.assertAlmostEqual(d.decode_one([1])['p1'],0.9,places=6)
 def test_correlated_mechanism(self):
  dem=stim.DetectorErrorModel('error(0.1) D0 D1 L0\ndetector D0\ndetector D1\nlogical_observable L0')
  d=FactorBP(dem); self.assertEqual(d.det,[(0,1)]);self.assertEqual(d.decode_one([1,1])['prediction'],1)
 def test_duplicate_faults_preserved(self):
  dem=stim.DetectorErrorModel('error(0.1) L0\nerror(0.2) L0\nlogical_observable L0')
  self.assertAlmostEqual(FactorBP(dem).decode_one([])['p1'],0.26)
 def test_separator_is_one_fault(self):
  dem=stim.DetectorErrorModel('error(0.1) D0 ^ D1 L0\ndetector D0\ndetector D1\nlogical_observable L0')
  self.assertEqual(FactorBP(dem).det,[(0,1)])
 def test_reject_invalid(self):
  dem=stim.DetectorErrorModel('error(0.1) D0 L0\ndetector D0\nlogical_observable L0');d=FactorBP(dem)
  for s in ([2],[],[0,1]):
   with self.assertRaises(ValueError):d.decode_one(s)
if __name__=='__main__':unittest.main()
