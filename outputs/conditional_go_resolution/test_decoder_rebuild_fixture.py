import unittest

import numpy as np
import stim

from decoder_rebuild_fixture import BoundaryDecoder, build_version, decode, noiseless_check


class DecoderRebuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = build_version("old", 0.003, 0.003)
        cls.new = build_version("new", 0.001, 0.006)
        cls.new_reference = build_version("new_reference", 0.001, 0.006)

    def test_schema_and_noiseless_behavior(self):
        self.assertEqual(self.old.matching.num_detectors, 40)
        self.assertEqual(self.old.matching.num_fault_ids, 1)
        self.assertEqual(noiseless_check(), {"detectors": 40, "observables": 1, "shots": 32})

    def test_rebuilt_decoder_matches_independent_reference(self):
        c = stim.Circuit.generated(
            "surface_code:rotated_memory_z", distance=3, rounds=5,
            after_clifford_depolarization=0.001,
            before_measure_flip_probability=0.006,
        )
        d, obs = c.compile_detector_sampler(seed=99870003).sample(
            512, separate_observables=True
        )
        p = decode(self.new, d)
        q = decode(self.new_reference, d)
        self.assertEqual(p.shape, (512,))
        self.assertEqual(obs.shape, (512, 1))
        np.testing.assert_array_equal(p, q)

    def test_no_mid_block_replacement_and_next_block_uses_new_version(self):
        bank = BoundaryDecoder(self.old)
        pinned = bank.begin_block(0)
        with self.assertRaisesRegex(RuntimeError, "during a block"):
            bank.publish_after(-1, self.new)
        bank.complete_block(0)
        bank.publish_after(0, self.new)
        self.assertIs(pinned, self.old)
        self.assertIs(bank.begin_block(1), self.new)
        bank.complete_block(1)

    def test_future_block_perturbation_cannot_change_its_decoder_choice(self):
        rng = np.random.default_rng(1234)
        prefix = rng.integers(0, 2, size=(16, 40), dtype=np.uint8)
        future_a = np.zeros((16, 40), dtype=np.uint8)
        future_b = np.ones((16, 40), dtype=np.uint8)

        def version_used_for_block_one(future):
            bank = BoundaryDecoder(self.old)
            b0 = bank.begin_block(0)
            decode(b0, prefix)
            bank.complete_block(0)
            # The update here is based only on completed block 0.
            bank.publish_after(0, self.new)
            b1 = bank.begin_block(1)
            decode(b1, future)
            bank.complete_block(1)
            return b1

        self.assertIs(version_used_for_block_one(future_a), self.new)
        self.assertIs(version_used_for_block_one(future_b), self.new)

    def test_block_order_is_enforced(self):
        bank = BoundaryDecoder(self.old)
        with self.assertRaisesRegex(RuntimeError, "in order"):
            bank.begin_block(1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
