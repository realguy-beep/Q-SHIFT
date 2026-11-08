import unittest

import numpy as np

from outputs.qshift_v2_dev_v1.controller import EventTriggeredProfile, pair_category


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.grid = np.array([0.0, 0.01, 0.02])
        self.probs = np.array([[.90,.02,.02,.02,.02,.02], [.35,.10,.12,.14,.14,.15], [.10,.10,.15,.20,.20,.25]])

    def test_updates_only_after_completed_block_and_respects_dwell(self):
        c = EventTriggeredProfile(self.grid, self.probs, .0, window_blocks=4, min_dwell_blocks=2, threshold=0)
        called=[]
        cb=lambda _: called.append(True) or .02
        self.assertEqual(c.active_p, 0.)
        c.observe_completed_block(np.full(50,5), cb)
        self.assertEqual(c.active_p,0.)
        c.observe_completed_block(np.full(50,5), cb)
        self.assertEqual(c.active_p,.02)
        self.assertEqual(c.switches,1)
        self.assertTrue(called)

    def test_rejects_invalid_category(self):
        c = EventTriggeredProfile(self.grid, self.probs, .0, threshold=0)
        with self.assertRaises(ValueError): c.observe_completed_block(np.array([6]), lambda _: 0.)

    def test_pair_summary_is_detector_only(self):
        d=np.zeros((2,40),dtype=np.uint8); d[0,8]=d[0,10]=1; d[1,1]=1
        self.assertEqual(pair_category(d,((8,10),(16,18),(24,26),(32,34),(36,38))).tolist(),[1,0])


if __name__ == '__main__': unittest.main()
