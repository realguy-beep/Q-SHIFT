"""CF1 tests: the loop is DB4's, the cf1 seed mode, the statistics on hand-checked cases, Holm, the
non-inferiority shift, DB4 dev totals reproduced, seeds, LF-only files and no seal. No sampling."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from multiprocessing import get_context
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import cf1_analyze as A  # noqa: E402
import cf1_config as C  # noqa: E402
import cf1_run as R  # noqa: E402


class ConfigTests(unittest.TestCase):
    def test_config(self):
        self.assertEqual(sum(C.EPISODES.values()), 48)
        self.assertEqual(set(C.EPISODES), set(C.C4.EPISODES))
        self.assertEqual(C.ARMS, C.C4.ARMS)
        self.assertEqual(C.C4.CANDIDATES[C.TEST_ARM], ("worst", 0.0))
        self.assertEqual([h[0] for h in C.HYPOTHESES], ["H1", "H2", "H3", "H4"])
        self.assertEqual(dict((h[0], h[4]) for h in C.HYPOTHESES), {"H1": 0, "H2": 0, "H3": 24, "H4": 2})
        self.assertTrue(all(k.startswith("cf1:") for k in C.all_keys()))


class LoopTests(unittest.TestCase):
    def test_job_is_db4_episode_job(self):
        src = (PKG / "cf1_run.py").read_text(encoding="utf-8")
        self.assertNotIn("def episode_job", src)
        self.assertIn("return R4.episode_job(args)", src)

    def test_db4_run_unchanged_since_db4_results(self):
        old = subprocess.run(["git", "show", "780d1c9f0:outputs/qshift_decoder_bank_v4/db4_run.py"], cwd=PKG,
                             capture_output=True, check=True).stdout
        self.assertEqual(old, (C.DB4 / "db4_run.py").read_bytes())

    def test_setup_modes(self):
        self.assertIs(R.R4._setup, R._setup)
        a = R._setup("dev", "AA", 3)
        b = R._db4_setup("dev", "AA", 3)
        self.assertEqual(a[3], b[3])
        self.assertEqual([a[0](t) for t in range(30)], [b[0](t) for t in range(30)])
        self.assertEqual(a[1](7, "eval"), b[1](7, "eval"))
        if (PKG / "CF1_SEEDS.json").exists():
            f = R._setup("cf1", "U", 2)
            sd = json.loads((PKG / "CF1_SEEDS.json").read_text(encoding="utf-8"))["seeds"]
            self.assertEqual(f[1](9, "det"), sd["cf1:U:e2:b09:det"])
            self.assertEqual(f[3], C.C4.episode_params("U", 2, sd["cf1:params:U:e2"]))


class StatsTests(unittest.TestCase):
    def test_exact_signflip(self):
        self.assertEqual(A.signflip_p([-1, -2, -3], 0), (1 / 8, "exact"))
        self.assertEqual(A.signflip_p([1, -1], 0), (3 / 4, "exact"))
        self.assertEqual(A.signflip_p([0, 0, 0], 0), (1.0, "exact"))

    def test_noninferiority_shift(self):
        self.assertEqual(A.signflip_p([0] * 6, 2), (1 / 64, "exact"))
        self.assertEqual(A.signflip_p([3] * 6, 2)[0], 1.0)

    def test_monte_carlo(self):
        p, how = A.signflip_p([-5] * 20, 0, n_flips=1000)
        self.assertEqual((how, p), ("monte_carlo", 1 / 1001))
        p, _ = A.signflip_p(list(range(-10, 10)), 0, n_flips=20_000)
        self.assertGreater(p, 0.2)
        self.assertEqual(A.signflip_p([-1, 2] * 10, 0, n_flips=5000), A.signflip_p([-1, 2] * 10, 0, n_flips=5000))

    def test_holm(self):
        self.assertEqual(A.holm({"H1": 0.01, "H2": 0.04, "H3": 0.03, "H4": 0.005}),
                         {"H4": True, "H1": True, "H3": False, "H2": False})
        self.assertEqual(A.holm({"H1": 0.012, "H2": 0.016, "H3": 0.024, "H4": 0.05}),
                         {"H1": True, "H2": True, "H3": True, "H4": True})

    def test_boot(self):
        self.assertEqual(A.boot_upper([4] * 5), 4.0)
        self.assertGreater(A.boot_upper([0, 10] * 5), 5.0)


class Db4ReproTests(unittest.TestCase):
    def test_db4_dev_totals(self):
        run = C.DB4 / "work" / "dev"
        if not (run / "archives").exists():
            self.skipTest("DB4 archives not present")
        T = A.episode_totals(run, C.C4.EPISODES)
        an = json.loads((C.DB4 / "results" / "dev" / "ANALYSIS.json").read_text(encoding="utf-8"))
        for s, v in an["schedules"].items():
            for a in C.ARMS:
                self.assertEqual(T[s][a], v["errors_per_episode"][a], (s, a))
            self.assertEqual(T[s]["_switches_W0F"], v["key_switches_per_episode"]["W0F"])
        self.assertEqual(sum(sum(T[s]["_triggers_W0F"]) for s in T), an["trigger_rate"]["triggers"])


class SourceTests(unittest.TestCase):
    def test_no_seal(self):
        for p in PKG.glob("*.py"):
            s = p.read_text(encoding="utf-8")
            for bad in ("open_seal", "_SEALED", "re1_seal", "re2_seal", "HIDDEN_COMMITMENT", "R6_"):
                self.assertNotIn(bad, s, p.name)

    def test_lf_only(self):
        for p in list(PKG.glob("*.py")) + list(PKG.glob("*.md")) + list((PKG / "tests").glob("*.py")):
            self.assertNotIn(b"\r\n", p.read_bytes(), p.name)


def _screened():
    import prepare_cf1
    return prepare_cf1.screened()[0]


class SeedTests(unittest.TestCase):
    def test_seeds(self):
        p = PKG / "CF1_SEEDS.json"
        if not p.exists():
            self.skipTest("seeds not written yet")
        s = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(set(s["seeds"]), set(C.all_keys()))
        v = set(s["seeds"].values())
        self.assertEqual(len(v), len(s["seeds"]))
        with get_context("spawn").Pool(1) as pool:
            self.assertFalse(v & pool.apply(_screened))


if __name__ == "__main__":
    unittest.main()
