import json,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import audit_holm_repair_v2 as audit

class AuditRepairV2Tests(unittest.TestCase):
 def test_correct_freeze_schema(self):
  d=json.loads((HERE/'SECONDARY_HOLM_AUDIT_REPAIR_V2_FREEZE.json').read_text())
  self.assertIn('audit_v2_input_sha256',d)
  self.assertIn('historical_and_failure_evidence_sha256',d)
 def test_holm_step_down_vector(self):
  import numpy as np
  self.assertEqual(audit.reject_holm(np.array([[.001,.01,.03,.8],[.02,.03,.04,.05]])).tolist(),[True,False])

if __name__=='__main__': unittest.main()
