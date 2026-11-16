"""Correctness gates C1-C4 for V3 BP+OSD (deterministic; no sampler, no random generator)."""
from __future__ import annotations

import itertools
import math
import unittest

import numpy as np
import stim

from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
from outputs.qshift_scalable_decoder_dev_v2.factor_bp_v2 import FactorBPV2
from outputs.qshift_scalable_decoder_dev_v3.bposd import (
    BPOSD, BeliefPropagation, ImpossibleSyndromeError, OrderedStatisticsDecoder, dem_to_matrix)

# Fixed, source-authored toy DEMs (<= 12 mechanisms), including hyperedges and logical bits.
TOYS = [
    "error(0.1) D0 D1\nerror(0.05) D1 D2 L0\nerror(0.2) D2 D3\nerror(0.07) D0 D2 D3\nerror(0.03) D3 L0\n"
    "error(0.12) D1\nerror(0.04) D0 D3 L0\nerror(0.09) D2\n",
    "error(0.02) D0 D1 D2\nerror(0.15) D0\nerror(0.08) D1 L0\nerror(0.11) D2 D3\nerror(0.06) D3 D4 L0\n"
    "error(0.05) D4\nerror(0.13) D1 D3\nerror(0.01) D0 D4\nerror(0.07) D2 L0\nerror(0.04) D3\n",
    "error(0.1) D0 D1 L0\nerror(0.1) D0 D1\nerror(0.2) D1 D2\nerror(0.05) D2 D3 D4\nerror(0.08) D0 D4\n"
    "error(0.06) D3\nerror(0.09) D4 L0\nerror(0.03) D1 D3\nerror(0.12) D2\nerror(0.07) D0\nerror(0.02) D1 D2 D3 D4 L0\n",
]


def brute(dem_text: str):
    dm = dem_to_matrix(stim.DetectorErrorModel(dem_text), merge=False)
    n = dm.H.shape[1]
    w = np.log1p(-dm.p) - np.log(dm.p)
    best = {}
    joint = {}
    for bits in itertools.product((0, 1), repeat=n):
        e = np.asarray(bits, dtype=np.uint8)
        s = tuple(int(v) for v in (dm.H.astype(int) @ e) % 2)
        cost = float(e @ w)
        if s not in best or cost < best[s][0] - 1e-12:
            best[s] = (cost, e)
        prob = math.prod(dm.p[j] if e[j] else 1 - dm.p[j] for j in range(n))
        joint.setdefault(s, np.zeros(n + 1))
        joint[s][:n] += prob * e
        joint[s][n] += prob
    return dm, best, joint


class C1OrderedStatistics(unittest.TestCase):
    def test_exhaustive_osd_equals_brute_force_most_probable_fault(self) -> None:
        for text in TOYS:
            dm, best, _ = brute(text)
            osd = OrderedStatisticsDecoder(dm, exhaustive=True)
            ranking = np.argsort(-dm.p, kind="stable")
            for s, (cost, _) in best.items():
                vecs, costs, _ = osd.candidates(np.asarray(s, dtype=np.uint8), ranking)
                self.assertAlmostEqual(float(costs.min()), cost, places=10)

    def test_osd_cs_candidates_are_always_syndrome_consistent(self) -> None:
        for text in TOYS:
            dm, best, _ = brute(text)
            osd = OrderedStatisticsDecoder(dm, order=3, weight1_columns=5)
            for s in best:
                sv = np.asarray(s, dtype=np.uint8)
                vecs, _, _ = osd.candidates(sv, np.argsort(-dm.p, kind="stable"))
                for v in vecs:
                    np.testing.assert_array_equal((dm.H.astype(int) @ v) % 2, sv)


class C2TreeMarginals(unittest.TestCase):
    def test_bp_marginals_exact_on_tree_factor_graphs(self) -> None:
        trees = ["error(0.1) D0 D1\nerror(0.2) D1 D2\nerror(0.05) D2 D3\nerror(0.15) D0\nerror(0.08) D3 L0\n",
                 "error(0.1) D0 D1 D2\nerror(0.2) D0\nerror(0.3) D1\nerror(0.12) D2 L0\n"]
        for text in trees:
            dm, best, joint = brute(text)
            bp = BeliefPropagation(dm, iterations=500, damping=0.5, tolerance=1e-15)
            for s, row in joint.items():
                llr, _ = bp.posterior_llr(np.asarray(s, dtype=np.uint8))
                p1 = 1 / (1 + np.exp(llr))
                exact = row[:-1] / row[-1]
                np.testing.assert_allclose(p1, exact, atol=1e-9)


class C3CrossImplementation(unittest.TestCase):
    def test_bp_posteriors_equal_scalable_v2_on_its_fixture_family(self) -> None:
        for d in (3, 5, 7):
            spec = m.CodeSpec(distance=d)
            qubits = m.burst_qubits(spec, "scaled_v1")
            for q in (0.0, 0.01):
                dem = m.build_candidate_circuit(spec, q, qubits).detector_error_model(
                    decompose_errors=False, approximate_disjoint_errors=True)
                v2 = FactorBPV2(dem)
                v3 = BeliefPropagation(dem_to_matrix(dem, merge=False))
                events = m.extract_burst_events(spec, qubits)
                syndromes = [np.zeros(dem.num_detectors, dtype=np.uint8)]
                for e in events:
                    row = np.zeros(dem.num_detectors, dtype=np.uint8)
                    row[list(e.detector_ids)] = 1
                    syndromes.append(row)
                for s in syndromes:
                    ref = np.asarray(v2.decode_one(s, include_fault_marginals=True)["fault_p1_approx"])
                    llr, _ = v3.posterior_llr(s)
                    np.testing.assert_allclose(1 / (1 + np.exp(llr)), ref, atol=1e-6, err_msg=f"d={d} q={q}")


class C4MatrixContract(unittest.TestCase):
    def test_columns_equal_dem_signatures_with_hyperedges_and_degenerate_pairs(self) -> None:
        dm = dem_to_matrix(stim.DetectorErrorModel(TOYS[2]), merge=True)
        cols = {(tuple(np.nonzero(dm.H[:, j])[0]), int(dm.L[j])) for j in range(dm.H.shape[1])}
        self.assertIn(((0, 1), 1), cols)
        self.assertIn(((0, 1), 0), cols)          # same detectors, different logical: kept apart
        self.assertIn(((1, 2, 3, 4), 1), cols)    # hyperedge stays one column
        self.assertEqual(dm.H.shape[1], 11)

    def test_identical_mechanisms_merge_exactly_and_separators_do_not_split(self) -> None:
        dm = dem_to_matrix(stim.DetectorErrorModel("error(0.1) D0 D1 L0\nerror(0.2) D0 D1 L0\nerror(0.05) D0 ^ D1\n"))
        self.assertEqual(dm.H.shape[1], 2)
        merged = [dm.p[j] for j in range(2) if dm.L[j] == 1][0]
        self.assertAlmostEqual(merged, 0.1 * 0.8 + 0.2 * 0.9)

    def test_impossible_syndrome_and_boundary_probabilities(self) -> None:
        dem = stim.DetectorErrorModel("error(0.1) D0 D1\nerror(0.2) D1 L0\nerror(1) D0 L0\nerror(0) D1\ndetector D2\n")
        dec = BPOSD(dem)
        self.assertEqual(int(dec.dm.offset_detectors[0]), 1)
        self.assertEqual(dec.dm.offset_logical, 1)
        with self.assertRaises(ImpossibleSyndromeError):
            dec.decode_one(np.asarray([0, 0, 1], dtype=np.uint8))
        out = dec.decode_one(np.asarray([1, 0, 0], dtype=np.uint8))  # only the p=1 offset fired
        self.assertEqual(out["prediction"], 1)

    def test_real_d3_dem_burst_columns_and_trivial_syndromes(self) -> None:
        spec = m.CodeSpec()
        qubits = m.burst_qubits(spec, "scaled_v1")
        dem = m.build_candidate_circuit(spec, 0.01, qubits).detector_error_model(
            decompose_errors=False, approximate_disjoint_errors=True)
        dec = BPOSD(dem)
        cols = {(tuple(np.nonzero(dec.dm.H[:, j])[0]), int(dec.dm.L[j])) for j in range(dec.dm.H.shape[1])}
        for e in m.extract_burst_events(spec, qubits):
            self.assertIn((e.detector_ids, e.observable_flip), cols)
        self.assertEqual(dec.decode_one(np.zeros(40, dtype=np.uint8))["prediction"], 0)
        for variant in ("min", "lc"):
            for e in m.extract_burst_events(spec, qubits):
                row = np.zeros(40, dtype=np.uint8)
                row[list(e.detector_ids)] = 1
                self.assertEqual(dec.decode_one(row, variant)["prediction"], e.observable_flip)


if __name__ == "__main__":
    unittest.main()
