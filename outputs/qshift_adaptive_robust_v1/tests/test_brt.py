"""BRT build tests: E1T flag, burst sets, seeds, analysis logic (no sampling)."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import brt  # noqa: E402
import brt_config as C  # noqa: E402
import estimate5 as E5  # noqa: E402
import prepare_brt  # noqa: E402


class FlagTests(unittest.TestCase):
    def test_e1t_is_cap_or_structure_only(self):
        for exc in (0, 30, 31):
            for s1 in (False, True):
                for s2 in (False, True):
                    for stat in (0.5, 99.0):                 # the statistic never matters
                        got = E5.e1t_flag({"excluded": exc, "stat": stat}, {"S1_shape": s1, "S2_consistency": s2})
                        self.assertEqual(got, exc > 30 or s1 or s2)


class BurstSeedTests(unittest.TestCase):
    def test_bursts_fresh_and_reproducible(self):
        import mm_contract as K
        b = json.loads((PKG / "BRT_BURSTS.json").read_text(encoding="utf-8"))
        bre = json.loads((PKG / "BRE_BURSTS.json").read_text(encoding="utf-8"))
        brs = json.loads((PKG / "BRS_BURSTS.json").read_text(encoding="utf-8"))
        prior = [tuple(v) for v in list(bre["T"].values()) + list(bre["V"].values()) + list(brs["V"].values())]
        cl = K.B.load_classes()
        prior_cls = {K.B.truth(cl, s)[0] for s in prior}
        cls = [K.B.truth(cl, tuple(s))[0] for s in b["V"].values()]
        self.assertEqual(len(set(cls)), 16)
        self.assertFalse(set(cls) & prior_cls)
        for s in b["V"].values():
            self.assertTrue(all(len(set(s) & set(x)) < 2 for x in prior))
        self.assertEqual(sorted(b["footprint"].values()).count(30), C.PER_STRATUM)
        self.assertEqual(b, json.loads(json.dumps(prepare_brt.draw_bursts(), sort_keys=True)))

    def test_seeds(self):
        b = json.loads((PKG / "BRT_BURSTS.json").read_text(encoding="utf-8"))
        s = json.loads((PKG / "BRT_SEEDS.json").read_text(encoding="utf-8"))
        self.assertEqual(set(s["seeds"]), set(C.all_keys(b)))
        self.assertEqual(set(s["rehearsal_seeds"]), set(C.rehearsal_keys(b)))
        ev, rh = set(s["seeds"].values()), set(s["rehearsal_seeds"].values())
        self.assertEqual(len(ev), len(s["seeds"]))
        self.assertFalse(ev & rh)
        from multiprocessing import get_context
        with get_context("spawn").Pool(1) as pool:
            screened = pool.apply(_screened_values)
        self.assertFalse((ev | rh) & screened)


def _screened_values():
    return prepare_brt.screened()[0]


def _rec(c, kind, bid, *, stat, exc, s1, s2, ok, acc):
    L = {"class_index": 5 if acc else None, "class_correct": ok, "learned_correct": ok}
    return {"cond": c, "kind": kind, "burst": bid, "pool": 0, "seeds": {}, "role": C.CONDITIONS[c][1],
            "fit": {"B2": {"objective": 60.0}, "E1": {"stat": stat, "excluded": exc, "set_matches_count": True}},
            "learn": {"B2": L, "E1": L}, "structural": {"S1_shape": s1, "S2_consistency": s2, "x_class": None}}


class AnalysisTests(unittest.TestCase):
    def _run(self, recs):
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "records").mkdir()
            for i, r in enumerate(recs):
                (tmp / "records" / f"{i:04d}.json").write_text(json.dumps(r), encoding="utf-8")
            (tmp / "RUN_STATUS.json").write_text(json.dumps({"state": "ready_for_analysis", "n_jobs": len(recs)}))
            return brt.analyze("rehearsal", tmp)
        finally:
            shutil.rmtree(tmp)

    def _synth(self, high_stat_in_t2):
        b = json.loads((PKG / "BRT_BURSTS.json").read_text(encoding="utf-8"))
        recs = []
        for c, (_, role) in C.CONDITIONS.items():
            inf = role == "in"
            for bid in b["V"]:
                for _ in range(C.POOLS_PER_BURST):
                    stat = 3.0 if (c == "T2" and high_stat_in_t2) else 1.0
                    recs.append(_rec(c, "burst", bid, stat=stat, exc=20, s1=not inf, s2=False, ok=inf, acc=True))
            for _ in range(C.Q0_POOLS):
                recs.append(_rec(c, "q0", "q0", stat=1.0, exc=0 if inf else 12, s1=not inf, s2=not inf, ok=False,
                                 acc=not inf))
        return recs

    def test_statistic_drift_does_not_flag_e1t(self):
        a = self._run(self._synth(True))
        self.assertEqual(a["verdict"], "BRT_SUPPORTED")
        self.assertEqual(a["arms"]["E1S"]["conditions"]["T2"]["flagged_burst"], 32)   # the BRS failure mode
        self.assertEqual(a["arms"]["E1T"]["conditions"]["T2"]["flagged_burst"], 0)

    def test_out_of_family_needs_structure(self):
        recs = self._synth(False)
        for r in recs:
            if r["cond"] == "TM2" and r["kind"] == "q0":
                r["structural"] = {"S1_shape": False, "S2_consistency": False, "x_class": 5}   # misfit passes
        a = self._run(recs)
        self.assertEqual(a["verdict"], "BRT_PARTIAL")
        self.assertFalse(a["E1T_endpoints"]["out_of_family"])


if __name__ == "__main__":
    unittest.main()
