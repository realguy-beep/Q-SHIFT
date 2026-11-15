from __future__ import annotations

import json
from pathlib import Path
import unittest

import numpy as np

from outputs.qshift_performance_sprint_v1 import recovery_support_v1_1 as support
from outputs.qshift_performance_sprint_v1.run_recovery_v1_1 import CapturingDecoder
from outputs.qshift_performance_sprint_v1.freeze_recovery_v1_1 import FILES


class RecoveryV11Tests(unittest.TestCase):
    def test_preserved_input_inventory_matches_failed_attempt_and_archives(self):
        found = support.verify_recovery_inputs(require_no_output=True)
        self.assertEqual(found["status"]["sampler_calls_started"], 56)
        self.assertEqual(found["status"]["shots_started"], 32000)
        self.assertEqual(found["inventory"]["training_rows"], 5000)
        self.assertEqual(found["inventory"]["calibration_rows"], 25000)
        self.assertEqual(found["inventory"]["persisted_evaluation_archives"], 0)

    def test_training_and_calibration_are_reconstructed_without_sampling(self):
        model = support.load_training_and_fit()
        result = support.reconstruct_calibration(model)
        self.assertEqual(len(result["estimates"]), 50)
        self.assertGreaterEqual(result["p_global"], 0.0)
        self.assertLessEqual(result["p_global"], 0.016)

    def test_recovery_source_manifest_is_complete_and_explicit(self):
        self.assertEqual(len(FILES), 10)
        for rel in FILES:
            self.assertTrue((support.ROOT / rel).is_file(), rel)

    def test_seed_inventory_has_unique_original_partition_ids(self):
        data = support.load_json(support.ROOT / "seed_inventory.json")
        self.assertEqual(len(data["seeds"]), 108)
        self.assertEqual(len(set(data["seeds"].values())), 108)
        self.assertEqual(data["seeds"]["eval:p0:r00"], 1757890542)

    def test_profile_decoder_registration_name_is_fixed_key(self):
        from outputs.qshift_performance_sprint_v1.run_recovery_v1_1 import decoder_for
        decoder, _, _, _ = decoder_for(0.004, "profile_estimated")
        self.assertEqual(decoder.metadata.name, "profile_estimated")

    def test_capturing_adapter_passes_prediction_and_preserves_metadata(self):
        from qshift_core_v1.contracts import DecoderMetadata, DecoderPrediction

        class Fixture:
            metadata = DecoderMetadata(name="profile_estimated", implementation="fixture",
                                       version="1", detector_count=3, observable_count=1)
            def decode(self, detectors):
                return DecoderPrediction(np.zeros((len(detectors), 1), dtype=np.uint8), self.metadata)

        wrapper = CapturingDecoder(Fixture())
        result = wrapper.decode(np.zeros((2, 3), dtype=np.uint8))
        np.testing.assert_array_equal(wrapper.last_bits, result.bits)
        self.assertEqual(result.metadata.name, "profile_estimated")

    def test_recovery_output_path_is_separate_and_original_status_unmodified(self):
        status_path = support.SAMPLES / "status.json"
        before = support.sha_file(status_path)
        self.assertEqual(support.RECOVERY, support.SAMPLES / "recovery_v1_1")
        self.assertFalse(support.RECOVERY.exists())
        after = support.sha_file(status_path)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
