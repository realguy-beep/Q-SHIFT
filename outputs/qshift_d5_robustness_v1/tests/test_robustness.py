"""Unit tests for the d=5 robustness Step E package (no evaluation sampling)."""
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
import contract as D  # noqa: E402
import eval_contract as K  # noqa: E402
import eval_job  # noqa: E402
import prepare_eval_seeds  # noqa: E402


class ContractTests(unittest.TestCase):
    def test_allocation(self):
        self.assertEqual(K.FROZEN.roots_per_q * K.FROZEN.shots_per_root, 200_016)
        self.assertEqual(K.FROZEN.jobs, 216)
        self.assertEqual(K.FROZEN.jobs * K.FROZEN.shots_per_root, 1_800_144)

    def test_selection_matches_dev_record(self):
        dev = json.loads((PKG / "DEV_SELECTION.json").read_text(encoding="utf-8"))["conditions"]
        for c in K.CONDITIONS:
            _, corr, qd = dev[c]["Astar_selected"].split("_")
            self.assertEqual(K.SELECTION[c]["astar_q_dec"], float(qd))
            self.assertEqual(K.SELECTION[c]["astar_correlations"], corr == "on")
            self.assertEqual(K.SELECTION[c]["l2_prior"], dev[c]["L2_selected_prior"])
            self.assertFalse(dev[c]["L2_guard_failed"])
            self.assertFalse(dev[c]["projected_under_powered"])

    def test_conditions(self):
        self.assertEqual(D.CONDITIONS, {"F2": ("centre_row", 0.003), "P2": ("scaled_v1", 0.002), "P4": ("scaled_v1", 0.004)})


class SeedTests(unittest.TestCase):
    def test_complete_and_disjoint(self):
        s = json.loads((PKG / "EVAL_SEEDS.json").read_text(encoding="utf-8"))
        keys = {K.root_key(*j) for j in K.jobs(K.FROZEN)} | {k for c in K.CONDITIONS for k in K.stats_keys(c)}
        self.assertEqual(set(s["seeds"]), keys)
        ev, rh = set(s["seeds"].values()), set(s["rehearsal_seeds"].values())
        self.assertEqual(len(ev), len(keys))
        self.assertFalse(ev & rh)
        screened, _ = prepare_eval_seeds.screened_values()
        self.assertFalse((ev | rh) & screened)


class DecisionTests(unittest.TestCase):
    def test_decide(self):
        self.assertEqual(analyze.decide([-2e-3, -1e-3], -5e-4, 7e-5), "GO")
        self.assertEqual(analyze.decide([-2e-3, 1e-4], -5e-4, 7e-5), "INCONCLUSIVE")
        self.assertEqual(analyze.decide([1e-4, 1e-3], -5e-4, 7e-5), "NO-GO")
        self.assertEqual(analyze.decide([-2e-3, -1e-3], 1e-4, 7e-5), "NO-GO")
        self.assertEqual(analyze.decide([-2e-3, -1e-3], 0.0, 0.0), "GO")

    def test_overall(self):
        def v(dec, bonf, safe=True):
            return {"decision": dec, "co_primary": {"passes_bonferroni": bonf}, "safety_q0": {"passes": safe}}
        self.assertEqual(analyze.overall({"a": v("GO", True), "b": v("GO", True), "c": v("GO", True)}), "ROBUST")
        self.assertEqual(analyze.overall({"a": v("GO", True), "b": v("GO", False), "c": v("INCONCLUSIVE", False)}), "PARTIAL")
        self.assertEqual(analyze.overall({"a": v("GO", True), "b": v("NO-GO", False), "c": v("GO", True)}), "NOT_ROBUST")
        self.assertEqual(analyze.overall({"a": v("INCONCLUSIVE", False)} | {"b": v("GO", False)}), "INCONCLUSIVE")


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_fake_sampler_deterministic(self):
        spec, qb = D.spec("F2")
        a = eval_job.fake_sample(spec, 0.02, qb, 40, 5)
        b = eval_job.fake_sample(spec, 0.02, qb, 40, 5)
        self.assertTrue(np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1]))
        self.assertEqual(a[0].shape, (40, spec.detectors))

    def test_job_writes_once(self):
        rec = eval_job.run("fake", "P4", 1, 0, self.tmp / "once")
        self.assertEqual(set(rec["errors"]), set(K.ARMS))
        with self.assertRaises(SystemExit):
            eval_job.run("fake", "P4", 1, 0, self.tmp / "once")

    def test_analyzer_synthetic_deterministic_and_tamper(self):
        run, alloc, rng = self.tmp / "syn", K.FAKE, np.random.default_rng(3)
        (run / "archives").mkdir(parents=True)
        (run / "roots").mkdir(parents=True)
        for c, qi, r in K.jobs(alloc):
            y = rng.integers(0, 2, alloc.shots_per_root).astype(np.uint8)
            preds = {a: y.copy() for a in K.ARMS}
            preds["Astar"][:4] ^= 1
            preds["L2s"][:1] ^= 1
            path = run / "archives" / f"{K.stem(c, qi, r)}.npz"
            np.savez_compressed(path, detectors=np.zeros((alloc.shots_per_root, 1), np.uint8), observables=y,
                                **{f"pred_{a}": np.packbits(p) for a, p in preds.items()})
            rec = {"seed": 0, "shots": alloc.shots_per_root, "archive": f"archives/{path.name}",
                   "archive_sha256": analyze.sha(path), "errors": {a: int((p != y).sum()) for a, p in preds.items()}}
            (run / "roots" / f"{K.stem(c, qi, r)}.json").write_text(json.dumps(rec), encoding="utf-8")
        (run / "RUN_STATUS.json").write_text(json.dumps({"state": "ready_for_analysis", "mode": "fake",
                                                         "allocation": alloc.as_dict()}), encoding="utf-8")
        a1 = analyze.analyze("fake", run, self.tmp / "o1")
        analyze.analyze("fake", run, self.tmp / "o2")
        self.assertEqual((self.tmp / "o1" / "ANALYSIS.json").read_bytes(), (self.tmp / "o2" / "ANALYSIS.json").read_bytes())
        for c in K.CONDITIONS:
            self.assertEqual(a1["conditions"][c]["arm_errors_q0_q001_q002"]["Astar"], [96, 96, 96])
            self.assertEqual(a1["conditions"][c]["decision"], "GO")
        self.assertEqual(a1["overall_verdict"], "ROBUST")
        path = run / "archives" / f"{K.stem('F2', 0, 0)}.npz"
        raw = path.read_bytes()
        try:
            path.write_bytes(raw + b"x")
            with self.assertRaises(ValueError):
                analyze.analyze("fake", run, self.tmp / "o3")
        finally:
            path.write_bytes(raw)


if __name__ == "__main__":
    unittest.main()
