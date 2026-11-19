"""BRE build tests: estimator identities, burst sets, seeds, and the analysis decision logic on synthetic records."""
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
import bre  # noqa: E402
import bre_config as C  # noqa: E402
import estimate2 as E  # noqa: E402
import estimate3 as E3  # noqa: E402
import prepare_bre  # noqa: E402


def _rates(spec, q, sup):
    import he1 as H
    from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
    c = m.build_candidate_circuit(spec, q, tuple(sup)) if q > 0 else m.build_base_circuit(spec)
    return H.detector_rates(c.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True))


class EstimatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(7)          # synthetic rows from exact rates (independent bits; no circuit sampling)
        spec = C.spec(gate_p=0.0029, measurement_p=0.0029, regime="z_biased", bias_ratio=5.0)
        cls.base = _rates(spec, 0.0, None)
        cls.x = (rng.random((12_000, 120)) < cls.base).astype(np.uint8)

    def test_fit_masked_reproduces_b2(self):
        a = E.fit_b2(self.x)
        o, n = E3.rates_from_rows(self.x)
        b = E3.fit_masked(o, n)
        for k in ("p_grid", "b_grid", "obj_grid", "p_hat", "b_hat", "objective"):
            self.assertEqual(a[k], b[k], k)

    def test_e1_equals_untrimmed_fit_without_outliers(self):
        o, n = E3.rates_from_rows(self.x)
        e1 = E3.fit_e1(o, n)
        self.assertEqual(e1["excluded"], 0)
        self.assertTrue(e1["stable"])
        f = E3.fit_masked(o, n, np.ones(120, bool), trim=0.0)
        self.assertEqual((e1["p_hat"], e1["b_hat"]), (f["p_hat"], f["b_hat"]))

    def test_e1_excludes_exactly_a_large_burst_on_expected_rates(self):
        import mm_contract as K
        spec = C.spec(gate_p=0.003, measurement_p=0.003, regime="z_biased", bias_ratio=4.0)
        cl = K.B.load_classes()
        big = next(c for c in cl if len(E3.class_detectors(c)) == 30)
        sup = (big.supports_flip0 or big.supports_flip1)[0]
        base = _rates(spec, 0.0, None)
        obs = (base + _rates(spec, 0.01, sup) + _rates(spec, 0.02, sup)) / 3
        e1 = E3.fit_e1(obs, C.N_CAL)
        self.assertEqual(e1["excluded"], 30)
        self.assertAlmostEqual(e1["b_hat"], 4.0, delta=0.05)
        self.assertAlmostEqual(e1["p_hat"] / 0.003, 1.0, delta=0.01)

    def test_class_detectors_equal_burst_events(self):
        import mm_contract as K
        cl = K.B.load_classes()
        i, _ = K.B.truth(cl, C.FIXED_T["K"])
        self.assertEqual(E3.class_detectors(cl[i]), E3.burst_detectors(C.FIXED_T["K"]))


class BurstSetTests(unittest.TestCase):
    def test_sets(self):
        import mm_contract as K
        import re1_seal
        b = json.loads((PKG / "BRE_BURSTS.json").read_text(encoding="utf-8"))
        self.assertEqual(b, json.loads(json.dumps(prepare_bre.draw_bursts(), sort_keys=True)))   # reproducible
        self.assertEqual(len(b["T"]), len(C.FIXED_T) + C.N_RANDOM_T)
        self.assertEqual(len(b["V"]), C.N_V)
        cl = K.B.load_classes()
        cls = [K.B.truth(cl, tuple(s))[0] for s in list(b["T"].values()) + list(b["V"].values())]
        self.assertEqual(len(set(cls)), len(cls))                      # one support per class, T and V disjoint
        pool = set(re1_seal.candidate_pool())
        for s in b["V"].values():
            self.assertIn(tuple(s), pool)                                # never a development/Phase C class or near one
        per = {}
        for k, fp in b["footprint"].items():
            if k in b["V"]:
                per[fp >= 26] = per.get(fp >= 26, 0) + 1
        self.assertEqual(per.get(True), C.N_V // len(C.FOOTPRINT_STRATA))


def _screened_values():
    return prepare_bre.screened()[0]


class SeedTests(unittest.TestCase):
    def test_complete_disjoint_screened(self):
        b = json.loads((PKG / "BRE_BURSTS.json").read_text(encoding="utf-8"))
        s = json.loads((PKG / "BRE_SEEDS.json").read_text(encoding="utf-8"))
        self.assertEqual(set(s["seeds"]), set(C.all_keys(b)))
        self.assertEqual(set(s["rehearsal_seeds"]), set(C.rehearsal_keys()))
        ev, rh = set(s["seeds"].values()), set(s["rehearsal_seeds"].values())
        self.assertEqual(len(ev), len(s["seeds"]))
        self.assertFalse(ev & rh)
        from multiprocessing import get_context
        with get_context("spawn").Pool(1) as pool:   # separate process: two prior packages both ship `contract.py`
            screened = pool.apply(_screened_values)
        self.assertFalse((ev | rh) & screened)


def _rec(c, kind, bid, k, tuning, *, b2obj, e1stat, e1exc, e2obj, learnE1, learnN, learnB2=None, learnE2=None):
    L = lambda ok, acc: {"class_index": 1 if acc else None, "class_correct": ok, "learned_correct": ok}   # noqa: E731
    return {"cond": c, "kind": kind, "burst": bid, "pool": k, "tuning": tuning, "in_family": C.CONDITIONS[c][1],
            "seeds": {}, "fit": {"B2": {"objective": b2obj}, "E1": {"stat": e1stat, "excluded": e1exc},
                                 "E2": {"objective": e2obj}},
            "learn": {"N": L(*learnN), "E1": L(*learnE1), "B2": L(*(learnB2 or learnE1)), "E2": L(*(learnE2 or learnE1))}}


class AnalysisTests(unittest.TestCase):
    def _run(self, recs):
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "records").mkdir()
            for i, r in enumerate(recs):
                (tmp / "records" / f"{i:04d}.json").write_text(json.dumps(r), encoding="utf-8")
            (tmp / "RUN_STATUS.json").write_text(json.dumps({"state": "ready_for_analysis", "n_jobs": len(recs)}))
            return bre.analyze("rehearsal", tmp)
        finally:
            shutil.rmtree(tmp)

    def _synthetic(self, e1_v_burst_stat):
        b = json.loads((PKG / "BRE_BURSTS.json").read_text(encoding="utf-8"))
        recs = []
        for c, (_, inf) in C.CONDITIONS.items():
            for bid in C.burst_ids(b):
                tun = bid in b["T"]
                for k in range(C.POOLS_PER_BURST):
                    stat = 1.0 if (tun or not inf) else e1_v_burst_stat
                    recs.append(_rec(c, "burst", bid, k, tun, b2obj=300.0 if inf else 3000.0,
                                     e1stat=stat if inf else 50.0, e1exc=20 if inf else 90,
                                     e2obj=80.0 if inf else 3000.0, learnE1=(inf, inf), learnN=(False, False)))
            for k in range(C.Q0_POOLS):
                recs.append(_rec(c, "q0", "q0", k, k in C.Q0_TUNING, b2obj=60.0, e1stat=1.0 if inf else 50.0,
                                 e1exc=0 if inf else 90, e2obj=60.0 if inf else 3000.0, learnE1=(False, False),
                                 learnN=(False, False)))
        return recs

    def test_e1_supported_and_b2_flags_everything(self):
        a = self._run(self._synthetic(1.0))
        self.assertEqual(a["verdict"], "BRE_SUPPORTED")
        self.assertEqual(a["chosen_arm"], "E1")
        self.assertFalse(a["arms"]["B2"]["endpoints"]["false_flag"])      # 300 > frozen 118.4 in every burst pool
        self.assertEqual(a["arms"]["E1"]["conditions"]["B3"]["V"]["learned_exactly"], 24)

    def test_held_out_misfit_is_flagged_and_fails(self):
        a = self._run(self._synthetic(5.0))       # V pools exceed the T-derived E1 threshold (1.0)
        self.assertFalse(a["arms"]["E1"]["endpoints"]["false_flag"])
        self.assertFalse(a["arms"]["E1"]["endpoints"]["learn"])
        self.assertTrue(a["arms"]["E3"]["conditions"]["B3"]["V"]["flagged_burst"] == 24)


if __name__ == "__main__":
    unittest.main()
