"""K1: V3.2 correctness (deterministic; no sampler, no random generator)."""
from __future__ import annotations

import unittest

import numpy as np
import stim

from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
from outputs.qshift_scalable_decoder_dev_v3.test_bposd import TOYS, brute
from outputs.qshift_scalable_decoder_dev_v3_2.ldpc_bposd import LdpcBPOSD


class K1Correctness(unittest.TestCase):
    def test_fault_estimates_are_syndrome_consistent_on_toys(self) -> None:
        for text in TOYS:
            dm, best, _ = brute(text)
            dec = LdpcBPOSD(stim.DetectorErrorModel(text))
            for s in best:
                sv = np.asarray(s, dtype=np.uint8)
                e = dec.fault_estimate(sv)
                np.testing.assert_array_equal((dec.dm.H.astype(int) @ e) % 2, sv)

    def test_real_dems_burst_and_trivial_syndromes(self) -> None:
        for d in (3, 5, 7):
            spec = m.CodeSpec(distance=d)
            qubits = m.burst_qubits(spec, "scaled_v1")
            dem = m.build_candidate_circuit(spec, 0.01, qubits).detector_error_model(
                decompose_errors=False, approximate_disjoint_errors=True)
            dec = LdpcBPOSD(dem)
            self.assertEqual(dec.osd_order_used, 10)  # frozen order unchanged on every real DEM
            self.assertEqual(dec.decode_one(np.zeros(dem.num_detectors, dtype=np.uint8)), 0)
            for e in m.extract_burst_events(spec, qubits):
                row = np.zeros(dem.num_detectors, dtype=np.uint8)
                row[list(e.detector_ids)] = 1
                est = dec.fault_estimate(row)
                np.testing.assert_array_equal((dec.dm.H.astype(int) @ est) % 2, row)
                self.assertEqual(dec.decode_one(row), e.observable_flip, f"d={d}")


if __name__ == "__main__":
    unittest.main()
