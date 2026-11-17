"""Belief-matching unit tests (no stim sampling; deterministic syndromes from DEM columns)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pymatching

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(PKG.parents[1]))
import bm  # noqa: E402
from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m  # noqa: E402


def dem_for(d: int, q: float = 0.01):
    spec = m.CodeSpec(distance=d)
    return m.build_decomposed_dem(m.build_candidate_circuit(spec, q, m.burst_qubits(spec, "scaled_v1")))


def det_syndromes(g: bm.BMGraph, k: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    H = g.H.toarray().astype(np.int64)
    rows = []
    for j in range(k):
        cols = rng.choice(H.shape[1], size=1 + j % 5, replace=False)
        rows.append((H[:, cols].sum(axis=1) % 2).astype(np.uint8))
    return np.vstack(rows)


class MappingTests(unittest.TestCase):
    def test_consistency_all_distances(self):
        for d in (3, 5, 7):
            dem = dem_for(d)
            g = bm.build_graph(dem)
            self.assertTrue(set(np.diff(g.He.indptr)) <= {1, 2})
            xor = (g.M @ g.He.T.astype(np.float64)).toarray().round().astype(np.int64) % 2
            self.assertTrue(np.array_equal(xor, g.H.T.toarray()))
            lx = (g.M @ g.Le.T.astype(np.float64)).toarray().round().astype(np.int64)[:, 0] % 2
            self.assertTrue(np.array_equal(lx, g.L))
            nonempty = sum(1 for ins in dem.flattened() if ins.type == "error")
            self.assertEqual(len(g.p), nonempty)  # no undetectable instructions here

    def test_prior_edge_probabilities_equal_pymatching(self):
        for d in (3, 5, 7):
            dem = dem_for(d)
            g = bm.build_graph(dem)
            pe = bm.edge_probabilities(g, g.p)
            mt = pymatching.Matching.from_detector_error_model(dem)
            ref = {}
            for u, v, data in mt.edges():
                key = (u,) if v is None else tuple(sorted((u, v)))
                ref[key] = data["error_probability"]
            rows, cols = g.He.nonzero()
            mine = {}
            for e in range(g.He.shape[1]):
                key = tuple(sorted(rows[cols == e]))
                mine[key] = pe[e]
            self.assertEqual(set(mine), set(ref))
            for key in ref:
                self.assertAlmostEqual(mine[key], ref[key], delta=1e-12 + 1e-9 * ref[key])

    def test_sign_parity_rule(self):
        g = bm.build_graph(dem_for(3))
        r = np.full(len(g.p), 0.9)
        pe = bm.edge_probabilities(g, r)
        cnt = np.asarray(g.M.sum(axis=0)).reshape(-1)
        np.testing.assert_allclose(pe, np.clip((1 - (-0.8) ** cnt) / 2, bm.CLIP, 1 - bm.CLIP), rtol=1e-9)


class IdentityTests(unittest.TestCase):
    def test_no_bp_equals_plain_matching(self):
        for d in (3, 5, 7):
            dem = dem_for(d)
            dec = bm.BeliefMatching(dem, {"max_iter": 0})
            s = det_syndromes(dec.g, 400, seed=d)
            ref = pymatching.Matching.from_detector_error_model(dem).decode_batch(s).reshape(-1).astype(np.uint8)
            self.assertTrue(np.array_equal(dec.decode_batch(s), ref), f"d={d}")


class BehaviourTests(unittest.TestCase):
    def test_zero_syndrome(self):
        dec = bm.BeliefMatching(dem_for(5))
        self.assertEqual(dec.decode_one(np.zeros(dec.g.num_detectors, np.uint8)), 0)

    def test_shortcut_reproduces_syndrome(self):
        dec = bm.BeliefMatching(dem_for(5), use_converged_bp=True)
        for s in det_syndromes(dec.g, 50, seed=11):
            dec.decode_one(s)
            if dec.bp.converge:
                e = np.asarray(dec.bp.decoding, dtype=np.int64)
                self.assertTrue(np.array_equal(dec.g.H.toarray().astype(np.int64) @ e % 2, s))
        self.assertGreater(dec.stats["bp_shortcut_used"], 0)

    def test_variants_build(self):
        for name, (cfg, conv, q) in bm.VARIANTS.items():
            dec = bm.BeliefMatching(dem_for(3, q), cfg, conv)
            self.assertEqual(len(dec.decode_batch(det_syndromes(dec.g, 5, 1))), 5, name)


if __name__ == "__main__":
    unittest.main()
