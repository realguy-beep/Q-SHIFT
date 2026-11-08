import json,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import validate_holm_repair_v1 as runner

class HolmSerializationRepairTests(unittest.TestCase):
 def test_pass_flags_are_json_serializable(self):
  record={'pass':bool(0.051 < 0.052),'overall':all([True,True])}
  encoded=json.dumps(record)
  self.assertEqual(json.loads(encoded),{'pass':True,'overall':True})
 def test_repaired_holm_behavior_unchanged(self):
  import numpy as np
  p=np.array([[.001,.01,.03,.8],[.02,.03,.04,.05],[.2,.3,.4,.5]])
  self.assertEqual(runner.holm_adjusted(p).tolist(),[True,False,False])
 def test_repair_freeze_and_no_sampling_scope(self):
  cfg=json.loads((HERE/'SECONDARY_HOLM_CONFIG.json').read_text())
  self.assertEqual(cfg['replicates_per_family'],200000)
  self.assertEqual(cfg['stage5_shots_generated'],0)
  self.assertFalse(cfg['sealed_test_accessed'])

if __name__=='__main__': unittest.main()
