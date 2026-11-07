import unittest
import numpy as np
from core import NoiseEstimator,Controller
from evaluation import evaluate_blocks,REGIME_DECODER,GRID_TO_REGIME
class Tests(unittest.TestCase):
 def test_causal_warmup_and_switch(self):
  e=NoiseEstimator(np.array([[.1,.9],[.9,.1]]),window=4);idx,conf=e.observe(np.zeros((3,2)));self.assertIsNone(idx)
  idx,conf,post=e.observe(np.zeros((1,2)));self.assertEqual(idx,0)
  c=Controller(fallback=1,confidence=.5,hysteresis=2,dwell=1);self.assertEqual(c.choose(0,.99),1);self.assertEqual(c.choose(0,.99),0)
 def test_alternating_candidates_reset_streak(self):
  c=Controller(fallback=8,confidence=.5,hysteresis=2,dwell=1)
  self.assertEqual(c.choose(0,.99),8);self.assertEqual(c.choose(2,.99),8);self.assertEqual(c.choose(0,.99),8);self.assertEqual(c.choose(0,.99),0)
 def test_dwell_and_confidence(self):
  c=Controller(fallback=1,confidence=.8,hysteresis=1,dwell=3)
  self.assertEqual(c.choose(0,.79),1);self.assertEqual(c.choose(0,.99),1);self.assertEqual(c.choose(0,.99),0)
 def test_utility_fallback_penalty(self):
  c=Controller(fallback=1,confidence=.5,hysteresis=1,dwell=1,switch_penalty=.2)
  self.assertEqual(c.choose(0,.99,[.1,.0]),1);self.assertEqual(c.choose(0,.99,[.5,0]),1)
 def test_all_regime_decoder_mappings(self): self.assertEqual([REGIME_DECODER[x] for x in ['data_heavy','nominal','measurement_heavy']],[6,4,2]);self.assertEqual(GRID_TO_REGIME.shape,(9,))
 def test_metrics_are_named_and_causal(self):
  class M:
   def __init__(self,v):self.v=v
   def decode_batch(self,d):return np.full((len(d),1),self.v,dtype=np.uint8)
  blocks=[{'state':'data_heavy','detectors':np.zeros((4,40),dtype=np.uint8),'observables':np.zeros(4,dtype=bool)} for _ in range(3)]
  out=evaluate_blocks(blocks,np.full((9,40),.1),[M(i%2) for i in range(9)],np.zeros((3,9)),policy='utility',confidence=0)
  self.assertEqual(out['errors']['pooled_fixed'],12);self.assertEqual(out['errors']['adaptive'],12);self.assertTrue(out['causal_previous_block_only'])
if __name__=='__main__':unittest.main()
