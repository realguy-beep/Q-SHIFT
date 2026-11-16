"""E3: V3.1 batched BP passes V3's C2/C3 checks and matches V3 on small fixed batches."""
from __future__ import annotations

import unittest

import numpy as np
import stim

from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
from outputs.qshift_scalable_decoder_dev_v2.factor_bp_v2 import FactorBPV2
from outputs.qshift_scalable_decoder_dev_v3.bposd import BPOSD, BeliefPropagation, dem_to_matrix
from outputs.qshift_scalable_decoder_dev_v3.test_bposd import TOYS, brute
from outputs.qshift_scalable_decoder_dev_v3_1.bposd_batched import BatchedBP, BatchedBPOSD


class BatchedEquivalence(unittest.TestCase):
    def test_tree_marginals_exact(self) -> None:
        text = "error(0.1) D0 D1\nerror(0.2) D1 D2\nerror(0.05) D2 D3\nerror(0.15) D0\nerror(0.08) D3 L0\n"
        dm, _, joint = brute(text)
        bp = BatchedBP(dm, iterations=500, tolerance=1e-15)
        keys = list(joint)
        llr, _ = bp.posterior_llr(np.asarray(keys, dtype=np.uint8))
        for row, s in zip(llr, keys):
            np.testing.assert_allclose(1 / (1 + np.exp(row)), joint[s][:-1] / joint[s][-1], atol=1e-9)

    def test_matches_v2_and_v3_on_fixture_family(self) -> None:
        for d in (3, 5):
            spec = m.CodeSpec(distance=d)
            qubits = m.burst_qubits(spec, "scaled_v1")
            for q in (0.0, 0.01):
                dem = m.build_candidate_circuit(spec, q, qubits).detector_error_model(
                    decompose_errors=False, approximate_disjoint_errors=True)
                rows = [np.zeros(dem.num_detectors, dtype=np.uint8)]
                for e in m.extract_burst_events(spec, qubits):
                    r = np.zeros(dem.num_detectors, dtype=np.uint8)
                    r[list(e.detector_ids)] = 1
                    rows.append(r)
                x = np.vstack(rows)
                llr, _ = BatchedBP(dem_to_matrix(dem, merge=False)).posterior_llr(x)
                v2 = FactorBPV2(dem)
                v3 = BeliefPropagation(dem_to_matrix(dem, merge=False))
                for i, s in enumerate(x):
                    ref2 = np.asarray(v2.decode_one(s, include_fault_marginals=True)["fault_p1_approx"])
                    np.testing.assert_allclose(1 / (1 + np.exp(llr[i])), ref2, atol=1e-6)
                    np.testing.assert_allclose(llr[i], v3.posterior_llr(s)[0], atol=1e-8)

    def test_predictions_match_v3_on_toys_and_burst_syndromes(self) -> None:
        for text in TOYS:
            dem = stim.DetectorErrorModel(text)
            dm, best, _ = brute(text)
            x = np.asarray(list(best), dtype=np.uint8)
            for variant in ("min", "lc"):
                ref = [BPOSD(dem).decode_one(s, variant)["prediction"] for s in x]
                np.testing.assert_array_equal(BatchedBPOSD(dem).decode_batch(x, variant)[:, 0], ref)


if __name__ == "__main__":
    unittest.main()
