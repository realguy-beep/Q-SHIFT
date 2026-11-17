"""Unit tests for the d=5 Phase 2 package (no evaluation sampling)."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import analyze  # noqa: E402
import contract as K  # noqa: E402
import eval_job  # noqa: E402
import prepare_seeds  # noqa: E402

D57 = PKG.parent / "qshift_scalable_decoder_eval_d57_v1"


class ContractTests(unittest.TestCase):
    def test_allocation(self):
        self.assertEqual(K.FROZEN.roots_per_q * K.FROZEN.shots_per_root, 200_016)
        self.assertEqual(K.FROZEN.jobs * K.FROZEN.shots_per_root, 600_048)

    def test_selections_match_development_records(self):
        prior = json.loads((D57 / "PHASE2_D5_PRIOR.json").read_text(encoding="utf-8"))
        self.assertEqual(prior["selected_q_dec"], K.STATIC_Q_DEC)
        self.assertFalse(prior["guard_failed"])
        p1 = json.loads((D57 / "PHASE1_RESULTS.json").read_text(encoding="utf-8"))["per_distance"]["5"]
        self.assertEqual(p1["Astar_selected"], f"match_on_{K.ASTAR_Q_DEC}")
        self.assertEqual(p1["BoffStatic_prior"], K.BOFF_PRIOR)


class SeedTests(unittest.TestCase):
    def test_seeds_complete_and_disjoint(self):
        s = json.loads((PKG / "SEEDS.json").read_text(encoding="utf-8"))
        keys = {K.root_key(qi, r) for qi in range(3) for r in range(K.FROZEN.roots_per_q)} | set(K.STATS_KEYS)
        self.assertEqual(set(s["seeds"]), keys)
        ev, rh = set(s["seeds"].values()), set(s["rehearsal_seeds"].values())
        self.assertEqual(len(ev), len(keys))
        self.assertFalse(ev & rh)
        screened, _ = prepare_seeds.screened_values()
        self.assertFalse((ev | rh) & screened)


class DecideTests(unittest.TestCase):
    def test_rules(self):
        self.assertEqual(analyze.decide([-0.002, -0.001], -0.0005, 0.00007), "GO_d5")
        self.assertEqual(analyze.decide([-0.002, 0.0001], -0.0005, 0.00007), "INCONCLUSIVE")
        self.assertEqual(analyze.decide([0.0001, 0.001], -0.0005, 0.00007), "NO-GO_d5")
        self.assertEqual(analyze.decide([-0.002, -0.001], 0.0001, 0.00007), "NO-GO_d5")
        self.assertEqual(analyze.decide([-0.002, -0.001], 0.0, 0.0), "GO_d5")  # zero comparator q=0 errors, tie


class FakeSamplerTests(unittest.TestCase):
    def test_deterministic_and_sparse(self):
        spec = eval_job.m.CodeSpec(distance=5)
        qb = eval_job.m.burst_qubits(spec, K.BURST_FAMILY)
        a = eval_job.fake_sample(spec, 0.02, qb, 50, 123)
        b = eval_job.fake_sample(spec, 0.02, qb, 50, 123)
        self.assertTrue(np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1]))
        self.assertEqual(a[0].shape, (50, spec.detectors))
        self.assertLess(a[0].mean(), 0.2)


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_job_writes_once(self):
        rec = eval_job.run("fake", 2, 0, self.tmp / "once")
        self.assertEqual(set(rec["errors"]), set(K.ARMS))
        self.assertEqual(rec["shots"], K.FAKE.shots_per_root)
        with self.assertRaises(SystemExit):
            eval_job.run("fake", 2, 0, self.tmp / "once")

    def test_analyzer_on_synthetic_run_is_deterministic(self):
        run = self.tmp / "synthetic"
        alloc, rng = K.FAKE, np.random.default_rng(7)
        for qi in range(3):
            for r in range(alloc.roots_per_q):
                y = rng.integers(0, 2, alloc.shots_per_root).astype(np.uint8)
                preds = {a: y.copy() for a in K.ARMS}
                preds["Astar"][: 3 + qi] ^= 1          # Astar: 3-5 errors per root
                preds["L2s"][:1] ^= 1                  # L2s: 1 error per root
                (run / "archives").mkdir(parents=True, exist_ok=True)
                (run / "roots").mkdir(parents=True, exist_ok=True)
                path = run / "archives" / f"{K.stem(qi, r)}.npz"
                np.savez_compressed(path, detectors=np.zeros((alloc.shots_per_root, 1), np.uint8), observables=y,
                                    **{f"pred_{a}": np.packbits(p) for a, p in preds.items()})
                rec = {"seed": 0, "shots": alloc.shots_per_root, "archive": f"archives/{path.name}",
                       "archive_sha256": analyze.sha(path), "errors": {a: int((p != y).sum()) for a, p in preds.items()}}
                (run / "roots" / f"{K.stem(qi, r)}.json").write_text(json.dumps(rec), encoding="utf-8")
        (run / "RUN_STATUS.json").write_text(json.dumps({"state": "ready_for_analysis", "mode": "fake",
                                                         "allocation": alloc.as_dict()}), encoding="utf-8")
        a1 = analyze.analyze("fake", run, self.tmp / "out1")
        a2 = analyze.analyze("fake", run, self.tmp / "out2")
        self.assertEqual((self.tmp / "out1" / "ANALYSIS.json").read_bytes(), (self.tmp / "out2" / "ANALYSIS.json").read_bytes())
        self.assertEqual(a1["arm_errors_q0_q001_q002"]["Astar"], [72, 96, 120])
        self.assertEqual(a1["arm_errors_q0_q001_q002"]["L2s"], [24, 24, 24])
        self.assertEqual(a1["decision"], "GO_d5")
        self.assertAlmostEqual(a1["relative_reduction_L2s_vs_Astar"]["estimate"], 1 - 1 / 4.5)
        self.assertEqual(a2["decision"], a1["decision"])

    def test_analyzer_rejects_tampered_archive(self):
        run = self.tmp / "synthetic"
        if not (run / "RUN_STATUS.json").exists():
            self.skipTest("synthetic run not built yet")
        path = run / "archives" / f"{K.stem(0, 0)}.npz"
        raw = path.read_bytes()
        try:
            path.write_bytes(raw + b"x")
            with self.assertRaises(ValueError):
                analyze.analyze("fake", run, self.tmp / "out3")
        finally:
            path.write_bytes(raw)


if __name__ == "__main__":
    unittest.main()
