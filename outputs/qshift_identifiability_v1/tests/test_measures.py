"""M1/M2 code checks on synthetic inputs and the bank only. No value is computed for any other support."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from scipy.stats import norm

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import split as S  # noqa: E402,I001
import ident1 as I  # noqa: E402
import measures as Q  # noqa: E402
import moments as M  # noqa: E402

C = S.C


class Measures(unittest.TestCase):
    def test_additive_model_equals_full_dem(self):
        feats, single = M.families()["F1"], S.single_signatures()
        for st in ("A", "B"):
            for p, q in ((C.P0, 0.01), (Q.P_GRID[0], 0.02)):
                B = Q.burst_signs(S.signature(C.support(st), single)[0], feats)
                base = Q.Base(feats, p)
                E, w = M.dem_errors(C.support(st), p, q)
                A = M.signs(E, feats)
                self.assertLess(np.abs(Q.model_mean(base, B, q) - M.means(A, w)).max(), 1e-10)
                self.assertLess(np.abs(Q.model_cov(base, B, q) - M.covariance(A, w)).max(), 1e-10)
        E, w = M.dem_errors(None)
        self.assertLess(np.abs(Q.model_mean(Q.Base(feats, C.P0)) - M.means(M.signs(E, feats), w)).max(), 1e-12)

    def test_solver(self):
        rng = np.random.default_rng(0)
        X = rng.normal(size=(40, 60))
        K, d = X @ X.T, rng.normal(size=(40, 3))
        a, b = Q.Solver(K), Q.Solver(K, force_eig=True)
        self.assertTrue(np.allclose(a.solve(d), np.linalg.solve(K, d)) and np.allclose(b.solve(d), a.solve(d)))
        K2 = np.vstack([np.hstack([K, K[:, :1]]), np.hstack([K[:1], K[:1, :1]])])       # duplicated feature
        s = Q.Solver(K2)
        self.assertEqual((s.dropped, s.dim), (1, 40))
        d2 = np.vstack([d, d[:1]])
        self.assertTrue(np.allclose((d2 * s.solve(d2)).sum(0), (d * a.solve(d)).sum(0)))

    def test_j(self):
        """Equal covariances: the old J. Unequal: the achieved error of the equal-error threshold, by quadrature."""
        self.assertAlmostEqual(float(Q.j_stat(np.array([0.3]), np.array([0.3]), np.array([0.3]))[0]), 0.3)
        wd, vs, vx, n = 0.02, 0.02, 0.05, 2000
        J = n * float(Q.j_stat(np.array([wd]), np.array([vs]), np.array([vx]))[0])
        cut = n * wd * np.sqrt(vs) / (np.sqrt(vs) + np.sqrt(vx))
        e1 = norm.sf(cut / np.sqrt(n * vs))
        e2 = norm.cdf((cut - n * wd) / np.sqrt(n * vx))
        self.assertAlmostEqual(e1, e2, places=12)
        self.assertAlmostEqual(norm.cdf(-np.sqrt(J) / 2), e1, places=12)
        self.assertEqual(float(Q.j_stat(np.zeros(1), np.zeros(1), np.ones(1))[0]), 0)
        self.assertEqual([Q.label(x) for x in (0, 10.79, 10.8, 21.59, 21.6)],
                         ["AMBIGUOUS", "AMBIGUOUS", "MARGINAL", "MARGINAL", "SEPARATED"])

    def test_accept(self):
        self.assertAlmostEqual(Q.accept_probability(0, 120), 0.995)
        self.assertAlmostEqual(Q.accept_probability(1e-9, 120), 0.995, places=6)
        self.assertLess(Q.accept_probability(95.5, 120), Q.accept_probability(28.2, 120))

    def test_grids(self):
        self.assertEqual([len(Q.grid(s)) for s in C.STATES], [5, 25, 25, 25, 25])
        self.assertIn(C.P0, Q.P_GRID)

    def test_targets_exclude_held(self):
        sp = S.split()
        for fam, n in (("F0", 1266), ("F1", 1266)):
            t = I.targets(fam)
            self.assertEqual(len(t), n)
            self.assertFalse([x for x in t if sp[x[3]] == "HELD"])
        self.assertTrue(all(x[1] <= 3 for x in I.targets("F2")))
        with patch.object(S, "split", return_value={k: "OTHER" for k in sp}), self.assertRaises(AssertionError):
            I.targets("F0")

    def test_pipeline_on_bank_only(self):
        """compute, second_pass, templates and summaries, with the bank states as the only targets."""
        single, real = S.single_signatures(), I.targets
        fake = [("SEEN", 3, C.support(st), S.signature(C.support(st), single)[0]) for st in C.STATES[1:]]
        with patch.object(I, "targets", return_value=fake):
            res, info = I.compute("F0", lambda x: None)
            again, _ = I.compute("F0", lambda x: None)
            worst, tpl = I.second_pass(lambda x: None), I.template_pass()
        self.assertIs(I.targets, real)
        self.assertEqual(res, again)
        self.assertEqual((info["features"], info["targets"], info["dropped_directions"]), (120, 4, 0))
        for e, st, v, t in zip(res, C.STATES[1:], worst, tpl):
            self.assertLess(abs(e["states"][st]["J"]), 1e-12)
            self.assertTrue(e["states"][st]["own_class"])
            for o in C.STATES:
                x = e["states"][o]
                self.assertLessEqual(x["J"], x["J_nominal"] + 1e-15)
                self.assertLessEqual(v["J"][o], x["J"] * (1 + 1e-4) + 1e-9)
                self.assertGreaterEqual(t["ncp"][o], 0)
        s = I.summarise(res, 2000)
        self.assertEqual(s["SEEN/weight_1_3"]["classes"], 4)
        self.assertEqual(s["SEEN/weight_1_3"]["table"]["A"]["ALIASED"], 1)


if __name__ == "__main__":
    unittest.main()
