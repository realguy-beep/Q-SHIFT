import json,sys,unittest
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import validate_holm as vh

class HolmTests(unittest.TestCase):
 def test_holm_step_down_matches_known_cases(self):
  p=np.array([[.001,.01,.03,.8],[.02,.03,.04,.05],[.2,.3,.4,.5]])
  got=vh.holm_adjusted(p)
  self.assertEqual(got.tolist(),[True,False,False])
 def test_frozen_holm_levels(self):
  cfg=json.loads((HERE/'SECONDARY_HOLM_CONFIG.json').read_text())
  self.assertEqual(cfg['holm_step_thresholds'],[.0125,.016666666666666666,.025,.05])
  self.assertEqual(len(cfg['scenario_families']),10)
  self.assertTrue(any(x['name']=='zero_inflated65_q2' for x in cfg['scenario_families']))
 def test_inventory_collision_and_scope(self):
  inv=json.loads((HERE/'SECONDARY_HOLM_SEED_INVENTORY.json').read_text())
  seeds=[x['seed'] for x in inv['streams']]
  self.assertEqual(len(seeds),len(set(seeds)))
  self.assertEqual(inv['collision_count'],0)
  self.assertFalse(inv['stage5_evaluation_seeds_allocated'])
  self.assertFalse(inv['sealed_test_accessed'])

if __name__=='__main__': unittest.main()
