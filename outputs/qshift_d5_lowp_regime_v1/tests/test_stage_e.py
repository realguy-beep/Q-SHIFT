"""Stage E unit tests (no evaluation sampling)."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
REPO = PKG.parents[1]
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(REPO))
import analyze  # noqa: E402
import contract as D  # noqa: E402
import eval_contract as K  # noqa: E402
import eval_job  # noqa: E402
import prepare_eval_seeds  # noqa: E402


class ContractTests(unittest.TestCase):
    def test_allocation_matches_stage_s_sizing(self):
        dev = json.loads((PKG / "DEV_SELECTION.json").read_text(encoding="utf-8"))
        self.assertEqual(dev["decision"], "PROCEED_TO_STAGE_E_FREEZE")
        for c in K.CONDITIONS:
            self.assertEqual(K.FROZEN.roots_per_q * K.FROZEN.shots(c), dev["conditions"][c]["stage_e_N_per_q"])
        self.assertEqual(K.FROZEN.jobs, 144)
        self.assertEqual(K.FROZEN.total_shots, 2_892_888)

    def test_selection_matches_dev_record(self):
        dev = json.loads((PKG / "DEV_SELECTION.json").read_text(encoding="utf-8"))["conditions"]
        for c in K.CONDITIONS:
            _, corr, qd = dev[c]["Astar_selected"].split("_")
            self.assertEqual(K.SELECTION[c]["astar_q_dec"], float(qd))
            self.assertEqual(K.SELECTION[c]["astar_correlations"], corr == "on")
            self.assertEqual(K.SELECTION[c]["l2_prior"], dev[c]["L2_selected_prior"])
            self.assertFalse(dev[c]["L2_guard_failed"])

    def test_ported_code_matches_robustness(self):
        rob = REPO / "outputs/qshift_d5_robustness_v1"
        self.assertEqual((rob / "recount.py").read_bytes(), (PKG / "recount.py").read_bytes())
        a = (rob / "run_all.py").read_text(encoding="utf-8").splitlines()[1:]
        b = (PKG / "run_all.py").read_text(encoding="utf-8").splitlines()[1:]
        self.assertEqual(a, b)


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

    def test_overall(self):
        def v(dec, bonf, safe=True):
            return {"decision": dec, "co_primary": {"passes_bonferroni": bonf}, "safety_q0": {"passes": safe}}
        self.assertEqual(analyze.overall({"a": v("GO", True), "b": v("GO", True)}), "CONFIRMED")
        self.assertEqual(analyze.overall({"a": v("GO", True), "b": v("INCONCLUSIVE", False)}), "PARTIAL")
        self.assertEqual(analyze.overall({"a": v("GO", True), "b": v("NO-GO", False)}), "NOT_CONFIRMED")
        self.assertEqual(analyze.overall({"a": v("INCONCLUSIVE", False), "b": v("GO", False)}), "INCONCLUSIVE")

    def test_target(self):
        self.assertEqual(analyze.target({"estimate": 0.97, "95ci": [0.951, 0.98]}), "TARGET_MET_WITH_MARGIN")
        self.assertEqual(analyze.target({"estimate": 0.96, "95ci": [0.93, 0.98]}), "TARGET_MET")
        self.assertEqual(analyze.target({"estimate": 0.95, "95ci": [0.92, 0.97]}), "TARGET_MET")
        self.assertEqual(analyze.target({"estimate": 0.94, "95ci": [0.90, 0.97]}), "TARGET_NOT_MET")
        self.assertEqual(analyze.target({"estimate": None, "95ci": [0, 1]}), "TARGET_UNDEFINED")


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_job_writes_once(self):
        rec = eval_job.run("fake", "L15", 1, 0, self.tmp / "once")
        self.assertEqual(set(rec["errors"]), set(K.ARMS))
        with self.assertRaises(SystemExit):
            eval_job.run("fake", "L15", 1, 0, self.tmp / "once")

    def test_analyzer_synthetic_deterministic_and_tamper(self):
        run, alloc, rng = self.tmp / "syn", K.FAKE, np.random.default_rng(3)
        (run / "archives").mkdir(parents=True)
        (run / "roots").mkdir(parents=True)
        for c, qi, r in K.jobs(alloc):
            n = alloc.shots(c)
            y = rng.integers(0, 2, n).astype(np.uint8)
            preds = {a: y.copy() for a in K.ARMS}
            preds["Astar"][:4] ^= 1
            if r == 0:
                preds["L2s"][:1] ^= 1
            path = run / "archives" / f"{K.stem(c, qi, r)}.npz"
            np.savez_compressed(path, detectors=np.zeros((n, 1), np.uint8), observables=y,
                                **{f"pred_{a}": np.packbits(p) for a, p in preds.items()})
            rec = {"seed": 0, "shots": n, "archive": f"archives/{path.name}",
                   "archive_sha256": analyze.sha(path), "errors": {a: int((p != y).sum()) for a, p in preds.items()}}
            (run / "roots" / f"{K.stem(c, qi, r)}.json").write_text(json.dumps(rec), encoding="utf-8")
        (run / "RUN_STATUS.json").write_text(json.dumps({"state": "ready_for_analysis", "mode": "fake",
                                                         "allocation": alloc.as_dict()}), encoding="utf-8")
        a1 = analyze.analyze("fake", run, self.tmp / "o1")
        analyze.analyze("fake", run, self.tmp / "o2")
        self.assertEqual((self.tmp / "o1" / "ANALYSIS.json").read_bytes(), (self.tmp / "o2" / "ANALYSIS.json").read_bytes())
        for c in K.CONDITIONS:
            self.assertEqual(a1["conditions"][c]["arm_errors_q0_q001_q002"]["Astar"], [96, 96, 96])
            self.assertEqual(a1["conditions"][c]["arm_errors_q0_q001_q002"]["L2s"], [1, 1, 1])
            self.assertEqual(a1["conditions"][c]["decision"], "GO")
        self.assertEqual(a1["overall_verdict"], "CONFIRMED")
        self.assertEqual(a1["target_verdict"], "TARGET_MET_WITH_MARGIN")      # R = 1 - 1/96 per nonzero q
        path = run / "archives" / f"{K.stem('L10', 0, 0)}.npz"
        raw = path.read_bytes()
        try:
            path.write_bytes(raw + b"x")
            with self.assertRaises(ValueError):
                analyze.analyze("fake", run, self.tmp / "o3")
        finally:
            path.write_bytes(raw)


if __name__ == "__main__":
    unittest.main()
