import math
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"outputs"/"categorical_decoder_feasibility"))
from categorical_dem_analysis import dem_mechanisms,enumerate_independent_dem
from separator_ablation import parse_events,remove_decomposition_hints,pm_decode
from toy_circuits import two_qubit_model
from categorical_reference import exact_posterior


class TestDemAttribution(unittest.TestCase):
    def test_exact_independent_dem_and_original_categorical_map(self):
        dem,events=dem_mechanisms()
        joint,decisions,posterior,ties,total=enumerate_independent_dem(events)
        self.assertEqual(len(events),6)
        self.assertEqual(2**len(events),64)
        self.assertAlmostEqual(total,1.0,places=14)
        categorical=exact_posterior(two_qubit_model())
        self.assertEqual(decisions,categorical.decisions)
        self.assertEqual(decisions[3],1)
        self.assertAlmostEqual(posterior[3][1],0.9691017201104268,places=13)

    def test_separator_removal_keeps_independent_event_law_but_changes_pm(self):
        original,_=dem_mechanisms()
        stripped=remove_decomposition_hints(original)
        a,b=parse_events(original),parse_events(stripped)
        self.assertEqual(len(a),len(b))
        for x,y in zip(a,b):
            self.assertEqual((x["probability"],x["detector_mask"],x["observable_mask"]),
                             (y["probability"],y["detector_mask"],y["observable_mask"]))
        for correlated in (False,True):
            pred_a,_,_=pm_decode(original,correlated)
            pred_b,_,_=pm_decode(stripped,correlated)
            self.assertEqual(pred_a[3],0)
            self.assertEqual(pred_b[3],1)


if __name__=="__main__": unittest.main()
