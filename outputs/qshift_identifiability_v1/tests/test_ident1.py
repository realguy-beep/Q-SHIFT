"""IDENT1 section 8 checks that do not depend on M1/M2. No sampling; no separation value is computed."""
from __future__ import annotations

import itertools
import sys
import unittest
from pathlib import Path

import numpy as np
import stim

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import split as S  # noqa: E402,I001
import harm as H  # noqa: E402
import moments as M  # noqa: E402

TOY = stim.DetectorErrorModel("""
error(0.1) D0
error(0.03) D0 D1
error(0.2) D1 D2 L0
error(0.05) D2
error(0.01) D0 D1 D2
error(0.3) D3 D1
error(0.07) D3 L0
error(0.02) D0 D3
error(0.11) L0
error(0.04) D0 D1
error(0.15) D2 D3
""")


def brute():
    ers = [(i.args_copy()[0], [t.val for t in i.targets_copy() if t.is_relative_detector_id()]) for i in TOY.flattened() if i.type == "error"]
    pmf = {}
    for bits in itertools.product((0, 1), repeat=len(ers)):
        p, s = 1.0, [0, 0, 0, 0]
        for b, (q, ds) in zip(bits, ers):
            p *= q if b else 1 - q
            if b:
                for d in ds:
                    s[d] ^= 1
        pmf[tuple(s)] = pmf.get(tuple(s), 0) + p
    return pmf


class Checks(unittest.TestCase):
    def test_no_sampling(self):
        c = M.circuit((1, 12, 38))
        for f in (c.compile_detector_sampler, c.compile_sampler, TOY.compile_sampler):
            with self.assertRaises(AssertionError):
                f()

    def test_moments_and_covariance(self):
        feats = [f for k in range(1, 5) for f in itertools.combinations(range(4), k)]
        E, w = M.errors(TOY, 4)
        A, pmf = M.signs(E, feats), brute()
        x = np.array([[(-1) ** sum(s[d] for d in f) for f in feats] for s in pmf], float)
        p = np.array(list(pmf.values()))
        mu = p @ x
        cov = (x * p[:, None]).T @ x - np.outer(mu, mu)
        self.assertLess(np.abs(M.means(A, w) - mu).max(), 1e-12)
        self.assertLess(np.abs(M.covariance(A, w) - cov).max(), 1e-12)

    def test_bank_covariance_psd(self):
        feats = M.families()["F0"]
        for s in H.BANK:
            E, w = M.dem_errors(S.C.support(s))
            K = M.covariance(M.signs(E, feats), w)
            self.assertEqual(np.abs(K - K.T).max() < 1e-12, True)
            self.assertGreater(np.linalg.eigvalsh(K)[0], -1e-12)

    def test_families(self):
        f = M.families()
        self.assertEqual((len(f["F0"]), len(f["F1"]), len(f["F2"])), (120, 2138, 7260))
        for k in f:
            self.assertEqual(len(set(f[k])), len(f[k]))

    def test_split(self):
        maps = S.class_maps()
        self.assertEqual(len(maps), 2)
        q = sorted(S.grid().values())
        self.assertEqual(len(q), 25)
        self.assertTrue(all(sorted(f) == q and sorted(f.values()) == q for f in maps))
        sp = S.split()
        self.assertEqual({k: sum(v == k for v in sp.values()) for k in ("DESIGN", "HELD", "SEEN")},
                         {"DESIGN": 1182, "HELD": 1297, "SEEN": 84})
        cls, hidden = S.classes(4)
        self.assertEqual((len(cls), len(hidden)), (2563, 26))
        where = {sup: s for s, v in cls.items() for sup in v}
        for f in maps:                                        # class onto exactly one class, in the same half
            img = {s: {where[tuple(sorted(f[x] for x in sup))] for sup in v} for s, v in cls.items()}
            self.assertTrue(all(len(t) == 1 for t in img.values()))
            self.assertTrue(all(sp[next(iter(t))] == sp[s] for s, t in img.items()))
        for sup in S.public().values():
            self.assertEqual(sp[where[sup]], "SEEN")

    def test_class_invariance(self):
        """Two supports of one class (first and last) have equal detector moments, for every DESIGN class of size > 1."""
        cls, _ = S.classes(4)
        sp, f, n = S.split(), M.families()["F1"], 0
        for s, v in cls.items():
            if sp[s] == "DESIGN" and len(v) > 1:
                a, b = (M.dem_errors(x) for x in (v[0], v[-1]))
                self.assertLess(np.abs(M.means(M.signs(a[0], f), a[1]) - M.means(M.signs(b[0], f), b[1])).max(), 1e-12, v[0])
                n += 1
        print("classes compared:", n)

    def test_source(self):
        for p in PKG.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                b = p.read_bytes()
                self.assertNotIn(b"\r\n", b, p.name)
                for bad in (b"C:" + b"\\Users", b"LEN" + b"OVO"):
                    self.assertNotIn(bad, b)


if __name__ == "__main__":
    unittest.main()
