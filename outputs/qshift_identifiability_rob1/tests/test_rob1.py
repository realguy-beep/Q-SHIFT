"""ROB1 section 7 checks that need no value for an unknown X under the new model, grids or test.

The T2-probability and T1-variance checks on SEEN classes run inside `rob1.py run`, before any result is written.
Toy of the union check: 3 detectors, 6 features, n = 12, limit 0.005, wrong model with all error probabilities 0.4."""
from __future__ import annotations

import itertools
import json
import math
import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from scipy.stats import binom

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import model as R  # noqa: E402,I001
import t1 as T1  # noqa: E402
import t2 as T2  # noqa: E402
import rob1 as X  # noqa: E402
from model import C, IDENT, M, Q, S, stim  # noqa: E402

sys.path.insert(0, str(IDENT / "tests"))
import test_ident1 as TI  # noqa: E402

FEATS3 = [(0,), (1,), (2,), (0, 1), (0, 2), (1, 2)]


def toy3(p):
    """Exact pmf over 8 outcomes and the feature rates of a 3-detector model with errors D0 D1, D1 D2, D0, D1, D2."""
    pmf = {}
    ers = [(0, 1), (1, 2), (0,), (1,), (2,)]
    for bits in itertools.product((0, 1), repeat=5):
        pr, s = 1.0, [0, 0, 0]
        for b, e in zip(bits, ers):
            pr *= p if b else 1 - p
            if b:
                for d in e:
                    s[d] ^= 1
        pmf[tuple(s)] = pmf.get(tuple(s), 0) + pr
    out = list(itertools.product((0, 1), repeat=3))
    return np.array([pmf[o] for o in out]), np.array([sum(pmf[o] for o in out if all(o[d] for d in f)) for f in FEATS3]), out


def vectors(n, k):
    """Every count vector of length k with sum n."""
    for bars in itertools.combinations(range(n + k - 1), k - 1):
        e = (-1, *bars, n + k - 1)
        yield [e[i + 1] - e[i] - 1 for i in range(k)]


# each check raises AssertionError when the module is wrong
def check_tail_and_interval():
    rng = np.random.default_rng(5)
    for _ in range(200):
        n, mm, r = 2000, int(rng.integers(1, 2139)), float(10 ** rng.uniform(-4.5, -0.3))
        a = T2.tail(mm)
        assert a <= 0.005 / (2 * mm)
        lo, hi = (int(v) for v in T2.interval(n, np.array(r), a))
        pm = [math.exp(math.lgamma(n + 1) - math.lgamma(j + 1) - math.lgamma(n - j + 1) + j * math.log(r) + (n - j) * math.log1p(-r))
              for j in range(n + 1)]
        assert math.fsum(pm[:lo]) <= a and math.fsum(pm[hi + 1:]) <= a
        assert math.fsum(pm[:lo + 1]) > a and math.fsum(pm[hi:]) > a


def check_bound():
    rng = np.random.default_rng(6)
    bank, x = rng.uniform(0.001, 0.2, (9, 40)), rng.uniform(0.3, 0.4, (6, 40))
    bank[0] = 0.25                                          # sets the upper end for every feature
    B, f, _ = T2.bound(300, x, bank)
    a = 0.005 / 80
    for j in range(6):
        best = []
        for c in range(40):
            los, his = [], []
            for r in bank[:, c]:
                pm = [math.comb(300, u) * r ** u * (1 - r) ** (300 - u) for u in range(301)]
                cum = np.cumsum(pm)
                los.append(int(np.flatnonzero(cum > a)[0]))
                his.append(int(np.flatnonzero(np.cumsum(pm[::-1])[::-1] > a)[-1]))
            best.append(X.direct_accept(300, x[j, c], min(los), max(his)))
        assert abs(min(best) - B[j]) < 1e-9 and abs(best[int(f[j])] - min(best)) < 1e-9


def check_pair_rates():
    feats = [(d,) for d in range(4)] + list(itertools.combinations(range(4), 2))
    E, w = M.errors(TI.TOY, 4)
    r = R.rates(M.means(M.signs(E, feats), w), feats)
    pmf = TI.brute()
    for i, f in enumerate(feats):
        assert abs(r[i] - sum(p for s, p in pmf.items() if all(s[d] for d in f))) < 1e-12
        assert 0 <= r[i] <= 1


class Checks(unittest.TestCase):
    def test_no_sampling_and_held(self):
        c = R.exact_circuit(M.circuit((1, 12, 38)))
        for f in (c.compile_detector_sampler, c.compile_sampler):
            with self.assertRaises(AssertionError):
                f()
        sp = S.split()
        self.assertFalse(any(sp[x[3]] == "HELD" for x in X.target_list()))

    def test_grids(self):
        g = R.main_grid()
        self.assertEqual((len(g), len(set(g)), len(R.slice_grid())), (203, 203, 45))
        self.assertIn(("OFF", (C.P0, C.P0), None), g)
        self.assertIn(("B", (C.P0, C.P0), 0.01), g)
        self.assertEqual(sum(R.is_edge(p) for p in g if p[0] == "OFF"), 2)
        self.assertEqual(sum(R.is_edge(p) for p in g if p[0] == "A"), 2 * 7 + 5 * 2)

    def test_exact_model_strict(self):
        seen = [x for x in X.target_list() if x[0] == "SEEN"][:20]
        for sup in [(), *(C.support(s) for s in C.STATES[1:]), *(x[2] for x in seen)]:
            E, w = R.exact_errors(sup, C.P0, C.P0, 0.01)
            self.assertGreater(len(E), 0)
        bad = stim.Circuit("R 0\nPAULI_CHANNEL_1(0.1,0.2,0.1) 0\nM 0\nDETECTOR rec[-1]")
        with self.assertRaises(ValueError):
            R.exact_circuit(bad)

    def test_exact_model_toy(self):
        """One channel on halves of Bell pairs: X flips the partner's detector, Z its own. Direct sum over exclusive outcomes."""
        for k in (1, 2):
            ps = 0.1 / (4 ** k - 1)
            q = range(k)
            c = stim.Circuit()
            c.append("R", range(2 * k))
            for i in q:
                c.append("H", [i])
                c.append("CX", [i, i + k])
            c.append(f"PAULI_CHANNEL_{k}", list(q), [ps] * (4 ** k - 1))
            for i in q:
                c.append("CX", [i, i + k])
                c.append("H", [i])
            c.append("M", range(2 * k))
            for i in range(2 * k):
                c.append("DETECTOR", [stim.target_rec(i - 2 * k)])
            feats = [f for n in range(1, 2 * k + 1) for f in itertools.combinations(range(2 * k), n)]
            E, w = M.errors(R.exact_circuit(c).detector_error_model(), 2 * k)
            got = M.means(M.signs(E, feats), w)
            E, w = M.errors(c.detector_error_model(approximate_disjoint_errors=True), 2 * k)
            old = M.means(M.signs(E, feats), w)
            want = []
            for f in feats:
                s = 0.0
                for paulis in itertools.product("IXYZ", repeat=k):
                    pr = 1 - 0.1 if set(paulis) == {"I"} else ps
                    det = [P in "YZ" for P in paulis] + [P in "XY" for P in paulis]
                    s += pr * (-1) ** sum(det[d] for d in f)
                want.append(s)
            self.assertLess(np.abs(got - want).max(), 1e-12)
            if k == 1:                                                  # Stim converts one-qubit channels exactly
                self.assertLess(np.abs(old - want).max(), 1e-12)
            else:                                                       # the check can see the old approximation
                self.assertGreater(np.abs(old - want).max(), 1e-6)

    def test_additivity(self):
        feats = R.features("F1")
        bank = R.bank_signs(feats)
        for s, g, r, q in (("A", 0.8, 1.2, 0.04), ("B", 1.2, 0.8, 0.0025), ("C", 0.7, 1.3, 0.01), ("D", 1.0, 1.2, 0.02)):
            p = (g * C.P0, r * C.P0)
            base = R.ExactBase(feats, p)
            E, w = R.exact_errors(C.support(s), *p, q)
            A = M.signs(E, feats)
            self.assertLess(np.abs(Q.model_mean(base, bank[s], q) - M.means(A, w)).max(), 1e-10)
            self.assertLess(np.abs(Q.model_cov(base, bank[s], q) - M.covariance(A, w)).max(), 1e-10)

    def test_gate_and_measurement_differ(self):
        f = R.features("F0")
        a, b, c = (R.ExactBase(f, (g * C.P0, r * C.P0)).lm for g, r in ((1, 1), (1.2, 1), (1, 1.2)))
        self.assertGreater(min(np.abs(a - b).max(), np.abs(a - c).max(), np.abs(b - c).max()), 1e-4)

    def test_stage1_reproduced(self):
        """Old noise model and stage 1 grid: T1 equals F1.json for the first 20 SEEN classes; two block sizes agree."""
        xs = [x for x in X.target_list() if x[0] == "SEEN"][:20]
        pts = [(s, (p, p), q) for p in Q.P_GRID for s in C.STATES for q in ((None,) if s == "OFF" else Q.Q_GRID)]
        feats = R.features("F1")
        old = {tuple(e["support"]): e for e in json.loads((IDENT / "results/stage1_run1/F1.json").read_text(encoding="utf-8"))["classes"]}
        J, _, _ = T1.j_values(pts, feats, [(Q.burst_signs(x[3], feats), 0.01) for x in xs], R.old_base, block=13)
        for j, x in enumerate(xs):
            for s in C.STATES:
                v = J[[i for i, p in enumerate(pts) if p[0] == s], j].min()
                w = old[tuple(x[2])]["states"][s]["J"]
                self.assertLessEqual(abs(v - w), 1e-6 * abs(w) + 1e-15, (x[2], s))

    def test_tail_and_interval(self):
        check_tail_and_interval()

    def test_bound(self):
        check_bound()

    def test_pair_rates(self):
        check_pair_rates()

    def test_union_bound(self):
        n = 12
        pt, rt, out = toy3(0.03)
        _, rt2, _ = toy3(0.05)
        pw, rw, _ = toy3(0.4)
        bank = np.array([rt, rt2])
        B, _, (lo, hi) = T2.bound(n, rw[None], bank)
        a, b = T2.hull(lo, hi)
        F = np.array([[all(o[d] for d in f) for o in out] for f in FEATS3], float)
        V = np.array(list(vectors(n, 8)))
        self.assertEqual(len(V), 50388)
        ok = ((V @ F.T >= a) & (V @ F.T <= b)).all(axis=1)
        coef = np.array([math.factorial(n) / math.prod(math.factorial(int(c)) for c in v) for v in V])
        acc = {}
        for nm, p in (("true", pt), ("wrong", pw)):
            pr = coef * np.prod(p ** V, axis=1)
            self.assertAlmostEqual(pr.sum(), 1, places=10)
            acc[nm] = pr[ok].sum()
        self.assertLessEqual(1 - acc["true"], 0.005)
        self.assertGreaterEqual(1 - acc["wrong"], 0.5)
        self.assertLessEqual(acc["wrong"], B[0] + 1e-12)

    def test_broken_versions_fail(self):
        iv, hl = T2.interval, T2.hull

        def parity(means, feats):
            return (1 - np.asarray(means, float)) / 2

        def most(p):
            i = p.argmax(axis=-1)
            return np.take_along_axis(p, i[..., None], -1)[..., 0], i
        broken = [("tail not divided", T2, "tail", lambda k: 0.005, check_tail_and_interval),
                  ("low end shifted", T2, "interval", lambda n, r, a: (iv(n, r, a)[0] + 1, iv(n, r, a)[1]), check_tail_and_interval),
                  ("high end shifted", T2, "interval", lambda n, r, a: (iv(n, r, a)[0], iv(n, r, a)[1] - 1), check_tail_and_interval),
                  ("max for min", T2, "least", most, check_bound),
                  ("point dropped", T2, "hull", lambda lo, hi: hl(lo[1:], hi[1:]), check_bound),
                  ("parity for co-firing", R, "rates", parity, check_pair_rates)]
        for nm, mod, attr, fn, chk in broken:
            chk()
            with self.subTest(nm), mock.patch.object(mod, attr, fn), self.assertRaises(AssertionError):
                chk()

    def test_readings(self):
        self.assertEqual([X.reading(c) for c in (418, 377, 376, 209, 208, 0)],
                         ["SURVIVES", "SURVIVES", "PARTIAL", "PARTIAL", "FAILS", "FAILS"])
        v = lambda b: {s: {"2000": {"B": b}} for s in C.STATES}  # noqa: E731
        e = {"own": [], "q": {"0.01": {"T2": {"main": v(0.05)}, "T1": {"main": {s: {"J": 21.6 / 2000} for s in C.STATES}}}}}
        self.assertTrue(X.passes(e, 0.01, "T2", "main", 2000))
        e["q"]["0.01"]["T2"]["main"]["OFF"]["2000"]["B"] = 0.0501
        self.assertFalse(X.passes(e, 0.01, "T2", "main", 2000))
        e["q"]["0.01"]["T1"]["main"]["D"]["J"] = 21.5 / 2000
        self.assertFalse(X.passes(e, 0.01, "T1", "main", 2000))

    def test_pipeline_end_to_end(self):
        """family() and the reports on bank states posing as targets (known models only), F0, so that the run cannot fail late."""
        one = S.single_signatures()
        sig = {s: S.signature(C.support(s), one)[0] for s in C.STATES[1:]}
        xs = [("SEEN", len(C.support(s)), tuple(C.support(s)), sig[s]) for s in C.STATES[1:]] * 21
        xs = xs[:84]
        res, info = X.family("F0", xs, lambda t: None)
        self.assertEqual((info["t2_pairs"], len(res)), (50, 84))
        self.assertGreater(res[0]["q"]["0.01"]["T2"]["main"]["A"]["2000"]["B"], 0.99)
        self.assertLess(res[0]["q"]["0.01"]["T1"]["main"]["A"]["J"], 1e-12)
        sm = X.summarise(res)
        self.assertEqual(sm["SEEN"]["classes"], 84)
        json.dumps(sm, sort_keys=True, default=float)

    def test_source(self):
        for p in PKG.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                b = p.read_bytes()
                self.assertNotIn(b"\r\n", b, p.name)
                for bad in (b"C:" + b"\\Users", b"LEN" + b"OVO"):
                    self.assertNotIn(bad, b)


if __name__ == "__main__":
    unittest.main()
