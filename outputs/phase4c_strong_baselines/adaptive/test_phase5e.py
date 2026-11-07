import json,unittest
from pathlib import Path
P=Path(__file__).resolve().parent
class Phase5EAudit(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.d=json.loads((P/'PHASE5E_RESULTS.json').read_text())
 def test_regime_matrices_independent_valid(self):
  mats=[self.d['regime_disagreement'][r]['disagreements'] for r in ['data_heavy','nominal','measurement_heavy']]
  for m in mats:
   self.assertTrue(all(m[i][j]==m[j][i] for i in range(9) for j in range(9)));self.assertTrue(all(m[i][i]==0 for i in range(9)))
  self.assertEqual(len({json.dumps(m) for m in mats}),3)
 def test_graphs_not_declared_equivalent(self):
  hs=[x['edge_signature_sha256'] for x in self.d['graph_audit']];self.assertEqual(len(set(hs)),9)
if __name__=='__main__':unittest.main()
