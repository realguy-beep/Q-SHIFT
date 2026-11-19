"""BRS build tests: structural rules, burst sets, seeds, frozen thresholds, analysis logic (no sampling)."""
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
import brs  # noqa: E402
import brs_config as C  # noqa: E402
import estimate4 as E4  # noqa: E402
import prepare_brs  # noqa: E402


class StructuralTests(unittest.TestCase):
    def test_class_sets_and_subsets_pass_random_sets_flag(self):
        sets = E4.class_sets()
        self.assertEqual(len(sets), 1003)
        rng = np.random.default_rng(3)
        for s, i in list(sets.items())[::37]:
            f = E4.structural_flags(sorted(s), i)
            self.assertEqual((f["S1_shape"], f["S2_consistency"], f["x_exact_class"]), (False, False, i))
            sub = sorted(rng.choice(sorted(s), size=max(1, len(s) - 3), replace=False).tolist())
            g = E4.structural_flags(sub, i)                       # E1 missing a few low-rise burst detectors
            self.assertEqual((g["S1_shape"], g["S2_consistency"]), (False, False))
        for _ in range(200):
            x = sorted(int(v) for v in rng.choice(120, size=int(rng.integers(8, 31)), replace=False))
            if not any(frozenset(x) <= s for s in sets):
                self.assertTrue(E4.structural_flags(x, None)["S1_shape"])

    def test_consistency(self):
        s, i = next(iter(E4.class_sets().items()))
        other = next(j for t, j in E4.class_sets().items() if not s <= t)
        self.assertFalse(E4.structural_flags([], None)["S2_consistency"])
        self.assertTrue(E4.structural_flags([], i)["S2_consistency"])            # nothing excluded, burst accepted
        self.assertTrue(E4.structural_flags(sorted(s), None)["S2_consistency"])  # burst-shaped exclusion, none learned
        self.assertTrue(E4.structural_flags(sorted(s), other)["S2_consistency"])  # learned class does not contain X
        self.assertFalse(E4.structural_flags(sorted(s), i)["S2_consistency"])

    def test_thresholds_frozen_from_bre(self):
        a = json.loads((PKG / "results/bre/ANALYSIS.json").read_text(encoding="utf-8"))["thresholds"]
        self.assertEqual(C.E1_STAT_THRESHOLD, a["E1"])
        self.assertEqual(C.E1_MAX_EXCLUDED, a["E1_max_excluded"])
        self.assertEqual(C.B2_THRESHOLD, a["B2"])


class BurstSeedTests(unittest.TestCase):
    def test_bursts_fresh_and_reproducible(self):
        import mm_contract as K
        b = json.loads((PKG / "BRS_BURSTS.json").read_text(encoding="utf-8"))
        bre = json.loads((PKG / "BRE_BURSTS.json").read_text(encoding="utf-8"))
        bre_sup = [tuple(v) for v in list(bre["T"].values()) + list(bre["V"].values())]
        cl = K.B.load_classes()
        bre_cls = {K.B.truth(cl, s)[0] for s in bre_sup}
        cls = [K.B.truth(cl, tuple(s))[0] for s in b["V"].values()]
        self.assertEqual(len(set(cls)), 16)
        self.assertFalse(set(cls) & bre_cls)
        for s in b["V"].values():
            self.assertTrue(all(len(set(s) & set(x)) < 2 for x in bre_sup))
        self.assertEqual(sorted(b["footprint"].values()).count(30), C.PER_STRATUM)
        self.assertEqual(b, json.loads(json.dumps(prepare_brs.draw_bursts(), sort_keys=True)))

    def test_seeds(self):
        b = json.loads((PKG / "BRS_BURSTS.json").read_text(encoding="utf-8"))
        s = json.loads((PKG / "BRS_SEEDS.json").read_text(encoding="utf-8"))
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
    return prepare_brs.screened()[0]


def _rec(c, kind, bid, *, stat, exc, s1, s2, b2obj, ok, acc):
    L = {"class_index": 5 if acc else None, "class_correct": ok, "learned_correct": ok}
    return {"cond": c, "kind": kind, "burst": bid, "pool": 0, "seeds": {}, "role": C.CONDITIONS[c][1],
            "fit": {"B2": {"objective": b2obj}, "E1": {"stat": stat, "excluded": exc, "set_matches_count": True}},
            "learn": {"B2": L, "E1": L}, "structural": {"S1_shape": s1, "S2_consistency": s2, "x_class": None}}


class AnalysisTests(unittest.TestCase):
    def _run(self, recs):
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "records").mkdir()
            for i, r in enumerate(recs):
                (tmp / "records" / f"{i:04d}.json").write_text(json.dumps(r), encoding="utf-8")
            (tmp / "RUN_STATUS.json").write_text(json.dumps({"state": "ready_for_analysis", "n_jobs": len(recs)}))
            return brs.analyze("rehearsal", tmp)
        finally:
            shutil.rmtree(tmp)

    def _synth(self, sm_q0_s1):
        b = json.loads((PKG / "BRS_BURSTS.json").read_text(encoding="utf-8"))
        recs = []
        for c, (_, role) in C.CONDITIONS.items():
            inf = role == "in"
            for bid in b["V"]:
                for _ in range(C.POOLS_PER_BURST):
                    recs.append(_rec(c, "burst", bid, stat=1.0 if inf else 9.0, exc=20, s1=False, s2=False,
                                     b2obj=60.0, ok=inf, acc=True))
            for k in range(C.Q0_POOLS):
                miss = c.startswith("SM") and k < 3            # E1 misses these (as in BRE's BM)
                recs.append(_rec(c, "q0", "q0", stat=1.0 if (inf or miss) else 9.0, exc=20 if miss else 0,
                                 s1=miss and sm_q0_s1, s2=False, b2obj=60.0, ok=False, acc=miss))
        return recs

    def test_structural_rule_catches_misses(self):
        a = self._run(self._synth(True))
        self.assertEqual(a["verdict"], "BRS_SUPPORTED")
        self.assertEqual(a["arms"]["E1"]["conditions"]["SM2"]["false_accepts_q0"], 3)
        self.assertEqual(a["arms"]["E1S"]["conditions"]["SM2"]["false_accepts_q0"], 0)

    def test_without_structural_catch_is_partial(self):
        a = self._run(self._synth(False))
        self.assertEqual(a["verdict"], "BRS_PARTIAL")
        self.assertFalse(a["E1S_endpoints"]["out_of_family"])


if __name__ == "__main__":
    unittest.main()
