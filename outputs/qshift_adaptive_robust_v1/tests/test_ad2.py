"""AD2 build tests: schedules, burst rule, arm selection, causality, seeds, analysis tiers and timeline on
synthetic records. No sampling; no seal is read."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from multiprocessing import get_context
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import ad2  # noqa: E402
import ad2_config as C  # noqa: E402


class ScheduleAndBurstTests(unittest.TestCase):
    def test_burst_rule(self):
        b = C.choose_bursts()
        self.assertEqual(b, C.BURSTS)
        self.assertEqual([b[k]["label"] for k in "ABCD"], ["W01", "W05", "W09", "W14"])
        fps = [b[k]["footprint"] for k in "ABCD"]
        self.assertEqual(fps, sorted(fps))
        for (lo, hi), k in zip(C.STRATA, "ABCD"):
            self.assertTrue(lo <= b[k]["footprint"] <= hi)
        import ad1_config as A1
        ad1_sup = {tuple(sorted(v)) for v in A1.BURSTS.values()}
        for v in b.values():
            self.assertNotIn(tuple(sorted(v["support"])), ad1_sup)
            self.assertEqual(len(v["support"]), 3)

    def test_schedules(self):
        name = lambda s, t: C.block_truth(s, t)[1]   # noqa: E731
        self.assertEqual({name("C0", t) for t in range(C.BLOCKS)}, {"A"})
        self.assertEqual([name("S1", t) for t in (14, 15)], ["A", "B"])
        self.assertEqual([name("S2", t) for t in range(C.BLOCKS)],
                         [("A" if (6 <= t <= 11 or 18 <= t <= 23) else None) for t in range(C.BLOCKS)])
        self.assertEqual([C.block_truth("S3", t)[0]["gate_p"] for t in (14, 15)], [0.0025, 0.0035])
        self.assertEqual([name("S3", t) for t in (14, 15)], ["A", "C"])
        self.assertEqual([name("S4", t) for t in (9, 10, 19, 20)], ["B", "C", "C", "D"])
        for s, cs in C.CHANGES.items():
            for c in cs:
                self.assertNotEqual(C.state(s, c - 1), C.state(s, c), (s, c))

    def test_settled(self):
        self.assertEqual([t for t in C.SCORED if ad2.settled_block("S2", t)], [])
        self.assertEqual([t for t in C.SCORED if ad2.settled_block("S1", t)], list(range(6, 15)) + list(range(21, 30)))
        self.assertEqual([t for t in C.SCORED if ad2.settled_block("S4", t)],
                         list(range(6, 10)) + list(range(16, 20)) + list(range(26, 30)))
        self.assertEqual(C.E3_SCHEDULES, ("S1", "S3", "S4"))


class SelectionTests(unittest.TestCase):
    def test_periodic_once_lg(self):
        sel = ad2.new_selector()
        out = {}
        flags = {9: True, 10: True, 13: True}
        for t in C.SCORED:
            k = ad2.NOMKEY if flags.get(t) else f"k{t}"
            out[t] = (ad2.advance(sel, t, k, flags.get(t, False)), sel["once"], sel["periodic"])
        self.assertTrue(all(v[1] == "k6" for v in out.values()))
        for t in C.SCORED:
            self.assertEqual(out[t][2], f"k{6 * (t // 6) if 6 * (t // 6) not in flags else 'x'}")
        self.assertEqual(out[9][0], "k8")
        self.assertEqual(out[10][0], "k8")
        self.assertEqual(out[11][0], "k11")
        self.assertEqual(out[13][0], "k12")
        self.assertEqual(out[14][0], "k14")

    def test_lg_nominal_when_none(self):
        sel = ad2.new_selector()
        self.assertEqual(ad2.advance(sel, 6, ad2.NOMKEY, True), ad2.NOMKEY)
        self.assertEqual(sel["once"], ad2.NOMKEY)

    def test_model_key(self):
        e = {"flagged": False, "p_hat": 0.003, "b_hat": 1.0}
        self.assertEqual(ad2.model_key({**e, "flagged": True}, (1, 2, 3)), ad2.NOMKEY)
        self.assertEqual(ad2.model_key(e, (3, 1, 2)), ad2.model_key(e, (1, 2, 3)))
        self.assertNotEqual(ad2.model_key(e, None), ad2.model_key(e, (1, 2, 3)))

    def test_causal_and_reuse(self):
        src = (PKG / "ad2.py").read_text(encoding="utf-8")
        self.assertIn("w0 = t - C.WINDOW", src)
        self.assertIn("estimate(dets[w0:t], labx[w0:t], laby[w0:t]", src)
        self.assertIn("estimate(dets[w3:t], labx[w3:t], laby[w3:t]", src)
        self.assertLess(src.index("estimate(dets[w0:t]"), src.index('key = C.block_key(s, e, t, "eval")'))
        self.assertIn("for k in dict.fromkeys(arm_key.values())", src)
        self.assertIn("ad1.estimate_window(", src)

    def test_no_seal(self):
        for n in ("ad2.py", "ad2_config.py", "prepare_ad2.py", "preflight_ad2.py"):
            src = (PKG / n).read_text(encoding="utf-8")
            for bad in ("open_seal", "_SEALED", "re1_seal", "re2_seal", "HIDDEN_COMMITMENT"):
                self.assertNotIn(bad, src, n)
        import freeze_ad2                                # names seal files only to exclude them
        self.assertFalse([f for f in freeze_ad2.FILES if "HIDDEN_COMMITMENT" in f or "seal" in f.lower()])


def _screened_values():
    import prepare_ad2
    return prepare_ad2.screened()[0]


class SeedTests(unittest.TestCase):
    def test_seeds(self):
        s = json.loads((PKG / "AD2_SEEDS.json").read_text(encoding="utf-8"))
        self.assertEqual(set(s["seeds"]), set(C.all_keys()))
        self.assertEqual(set(s["rehearsal_seeds"]), set(C.rehearsal_keys()))
        ev, rh = set(s["seeds"].values()), set(s["rehearsal_seeds"].values())
        self.assertEqual(len(ev), len(s["seeds"]))
        self.assertFalse(ev & rh)
        with get_context("spawn").Pool(1) as pool:
            screened = pool.apply(_screened_values)
        self.assertFalse((ev | rh) & screened)


BASE = {"ORACLE": 2, "AD": 2, "AD_LG": 2, "PERIODIC": 6, "ONCE": 10, "AD_M": 8, "A_nominal": 30, "AD_W3": 2}


class AnalysisTests(unittest.TestCase):
    def _run(self, errs=None, per_sched=None, mislearn=None, episodes=3):
        tmp = Path(tempfile.mkdtemp())
        try:
            run = tmp / "rehearsal"
            (run / "records").mkdir(parents=True)
            (run / "archives").mkdir()
            n = 1000
            seeds = json.loads((PKG / "AD2_SEEDS.json").read_text(encoding="utf-8"))["rehearsal_seeds"]
            for s in C.SCHEDULES:
                for e in range(episodes):
                    ek = {**BASE, **(errs or {}), **((per_sched or {}).get(s, {}))}
                    bits, blocks = {}, []
                    for t in C.SCORED:
                        prev = C.block_truth(s, t - 1)[1]
                        est = {"flagged": False, "learned_correct": prev is not None, "p_hat": 0.003, "b_hat": 1.0,
                               "class_index": 1 if prev else None, "true_class": 1 if prev else None}
                        if mislearn and s == mislearn and t == 8:
                            est["class_index"] = 2
                        er = {}
                        for a in C.ARMS:
                            v = np.zeros(n, bool)
                            v[: ek[a]] = True
                            bits[f"b{t:02d}_{a}"] = np.packbits(v)
                            er[a] = ek[a]
                        blocks.append({"block": t, "true": C.block_truth(s, t)[0], "burst": C.block_truth(s, t)[1],
                                       "estimate": est, "estimate_w3": est, "errors": er})
                    arc = run / "archives" / f"{s}_e{e}.npz"
                    np.savez_compressed(arc, **bits)
                    rec = {"schedule": s, "episode": e, "arms": list(C.ARMS), "eval_per_block": n,
                           "seeds": {C.block_key(s, 0, 0, "det"): seeds[C.block_key(s, 0, 0, "det")]}
                           if (s, 0) in C.REHEARSAL else {}, "blocks": blocks, "archive": f"archives/{arc.name}",
                           "archive_sha256": hashlib.sha256(arc.read_bytes()).hexdigest()}
                    (run / "records" / f"{s}_e{e}.json").write_text(json.dumps(rec), encoding="utf-8")
            (run / "RUN_STATUS.json").write_text(json.dumps({"state": "ready_for_analysis", "n_jobs": 15}))
            return ad2.analyze("rehearsal", run)
        finally:
            shutil.rmtree(tmp)

    def test_strong(self):
        a, tl = self._run()
        self.assertEqual(a["verdict"], "AD2_STRONG", a["endpoints"])
        self.assertNotIn("E3_S2", a["endpoints"])
        self.assertAlmostEqual(a["schedules"]["S1"]["R_vs_A_nominal"]["all"], 1 - 2 / 30)
        self.assertEqual(a["schedules"]["S1"]["latency_median"], 1.0)
        self.assertEqual(set(tl["schedules"]), set(C.SCHEDULES))
        s1 = tl["schedules"]["S1"]
        self.assertEqual(len(s1["arms"]["AD"]["ler_mean"]), len(C.SCORED))
        self.assertEqual(s1["true_burst"][0], "A")

    def test_supported_when_periodic_ties(self):
        a, _ = self._run(errs={"PERIODIC": 2})
        self.assertEqual(a["verdict"], "AD2_SUPPORTED", a["endpoints"])

    def test_partial(self):
        a, _ = self._run(per_sched={"S1": {"ONCE": 2}, "S3": {"ONCE": 2}})
        self.assertEqual(a["verdict"], "AD2_PARTIAL", a["endpoints"])

    def test_not_supported_on_mislearning(self):
        a, _ = self._run(mislearn="C0")
        self.assertFalse(a["endpoints"]["E6"])
        self.assertEqual(a["verdict"], "AD2_NOT_SUPPORTED")

    def test_oracle_excess_fails(self):
        a, _ = self._run(errs={"AD": 3, "AD_LG": 3})
        self.assertFalse(a["endpoints"]["E3_S1"])
        self.assertNotIn(a["verdict"], ("AD2_STRONG", "AD2_SUPPORTED"))


if __name__ == "__main__":
    unittest.main()
