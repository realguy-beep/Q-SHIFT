"""AD3 build tests: change statistic, recall, causality, seeds, analysis tiers on synthetic records.
No sampling; no seal is read."""
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
import ad3  # noqa: E402
import ad3_config as C  # noqa: E402


class StatisticTests(unittest.TestCase):
    def test_g_zero_and_positive(self):
        k = np.array([10, 20, 30])
        self.assertAlmostEqual(ad3.g_stat(k, 100, 2 * k, 200), 0.0, places=9)
        self.assertGreater(ad3.g_stat(k, 100, k, 200), 0.0)
        self.assertAlmostEqual(ad3.g_stat(k, 100, 3 * k, 400), ad3.g_stat(3 * k, 400, k, 100), places=9)

    def test_null_scale(self):
        r = np.random.default_rng(1)
        a, b = (r.random((2000, 120)) < 0.03).astype(np.uint8), (r.random((8000, 120)) < 0.03).astype(np.uint8)
        g = ad3.g_stat(*ad3.counts(a), *ad3.counts(b))
        self.assertTrue(60 < g < 200, g)                 # about chi2 with 120 dof

    def test_segment_lo(self):
        self.assertEqual(ad3.segment_lo(0, 3), 0)
        self.assertEqual(ad3.segment_lo(0, 20), 14)
        self.assertEqual(ad3.segment_lo(18, 20), 18)

    def test_recall_picks_closest_within_tau(self):
        r = np.random.default_rng(2)
        rows = lambda p: (r.random((6000, 120)) < p).astype(np.uint8)   # noqa: E731
        lib = {"lo": {"k": ad3.counts(rows(0.02))[0], "n": 6000}, "hi": {"k": ad3.counts(rows(0.05))[0], "n": 6000}}
        k, n = ad3.counts(rows(0.05)[:2000])
        hit = ad3.recall(lib, k, n, tau=300.0)
        self.assertEqual(hit[1], "hi")
        self.assertIsNone(ad3.recall({"lo": lib["lo"]}, k, n, tau=300.0))


class SourceTests(unittest.TestCase):
    src = (PKG / "ad3.py").read_text(encoding="utf-8")

    def test_causal(self):
        s = self.src
        # the change test for block t-1 runs before block t is sampled; every estimate uses blocks < t
        self.assertLess(s.index("u = t - 1"), s.index("ad2.sample_block(s, t, nrow"))
        self.assertIn("ad2.estimate(dets[w0:t], labx[w0:t], laby[w0:t]", s)
        self.assertIn("ad2.estimate(dets[seg0:t], labx[seg0:t], laby[seg0:t]", s)
        self.assertIn("kk, nn = pool(cnt[seg0:t])", s)
        self.assertLess(s.index("ad2.estimate(dets[seg0:t]"), s.index('key = C.block_key(s, e, t, "eval")'))
        self.assertIn("for k in dict.fromkeys(arm_key.values())", s)

    def test_window_equals_ad_when_long(self):
        self.assertIn('src, k3, e3 = "window", k_ad, dict(est)', self.src)
        self.assertIn('src, k3, e3 = "ad_fallback", k_ad, dict(est)', self.src)

    def test_no_seal(self):
        for n in ("ad3.py", "ad3_config.py", "prepare_ad3.py", "screen_ad3.py"):
            s = (PKG / n).read_text(encoding="utf-8")
            for bad in ("open_seal", "_SEALED", "re1_seal", "re2_seal", "HIDDEN_COMMITMENT"):
                self.assertNotIn(bad, s, n)


def _screened_values():
    import prepare_ad3
    return prepare_ad3.screened()[0]


class SeedTests(unittest.TestCase):
    def test_seeds(self):
        s = json.loads((PKG / "AD3_SEEDS.json").read_text(encoding="utf-8"))
        self.assertEqual(set(s["seeds"]), set(C.all_keys()))
        self.assertEqual(set(s["rehearsal_seeds"]), set(C.rehearsal_keys()))
        self.assertEqual(set(s["screen_seeds"]), set(C.screen_keys()))
        a, b, c = (set(s[k].values()) for k in ("seeds", "rehearsal_seeds", "screen_seeds"))
        self.assertEqual(len(a) + len(b) + len(c), len(a | b | c))
        with get_context("spawn").Pool(1) as pool:
            screened = pool.apply(_screened_values)
        self.assertFalse((a | b | c) & screened)


BASE = {"AD3": 2, "AD": 4, "PERIODIC": 6, "ONCE": 10, "ORACLE": 2, "A_nominal": 30}


class AnalysisTests(unittest.TestCase):
    def _run(self, errs=None, per_sched=None, mislearn=None, lat=1, episodes=3):
        tmp = Path(tempfile.mkdtemp())
        try:
            run = tmp / "rehearsal"
            (run / "records").mkdir(parents=True)
            (run / "archives").mkdir()
            n = 1000
            for s in C.SCHEDULES:
                for e in range(episodes):
                    ek = {**BASE, **(errs or {}), **((per_sched or {}).get(s, {}))}
                    bits, blocks = {}, []
                    for t in C.SCORED:
                        prev = C.block_truth(s, t - 1)[1]
                        late = any(c < t <= c + lat - 1 for c in C.CHANGES.get(s, ()))  # still catching up
                        est = {"flagged": False, "learned_correct": prev is not None, "p_hat": 0.003, "b_hat": 1.0,
                               "class_index": 1 if prev else None, "true_class": 1 if prev else None}
                        e3 = {**est, "source": "window", "seg0": 0, "seg_len": 6}
                        if late:
                            e3 = {**e3, "learned_correct": False, "class_index": None if prev else 1}
                        if mislearn and s == mislearn and t == 8:
                            e3 = {**e3, "class_index": 2}
                        er = {}
                        for a in C.ARMS:
                            v = np.zeros(n, bool)
                            v[: ek[a]] = True
                            bits[f"b{t:02d}_{a}"] = np.packbits(v)
                            er[a] = ek[a]
                        blocks.append({"block": t, "true": C.block_truth(s, t)[0], "burst": C.block_truth(s, t)[1],
                                       "estimate": est, "estimate_ad3": e3, "errors": er})
                    arc = run / "archives" / f"{s}_e{e}.npz"
                    np.savez_compressed(arc, **bits)
                    rec = {"schedule": s, "episode": e, "arms": list(C.ARMS), "eval_per_block": n, "seeds": {},
                           "tau": 150.0, "M": 2, "changes_detected": list(C.CHANGES.get(s, ())), "blocks": blocks,
                           "archive": f"archives/{arc.name}",
                           "archive_sha256": hashlib.sha256(arc.read_bytes()).hexdigest()}
                    (run / "records" / f"{s}_e{e}.json").write_text(json.dumps(rec), encoding="utf-8")
            (run / "RUN_STATUS.json").write_text(json.dumps({"state": "ready_for_analysis", "n_jobs": 15}))
            return ad3.analyze("rehearsal", run)
        finally:
            shutil.rmtree(tmp)

    def test_strong(self):
        a, tl = self._run()
        self.assertEqual(a["verdict"], "AD3_STRONG", a["endpoints"])
        self.assertEqual(a["schedules"]["S1"]["latency_AD3_median"], 1.0)
        self.assertEqual(a["schedules"]["S1"]["detection_delays"], [0, 0, 0])
        self.assertEqual(set(tl["schedules"]), set(C.SCHEDULES))

    def test_supported_when_slow(self):
        a, _ = self._run(lat=4)
        self.assertEqual(a["verdict"], "AD3_SUPPORTED", a["endpoints"])

    def test_partial_when_f2_fails(self):
        a, _ = self._run(per_sched={"S1": {"AD3": 5}})
        self.assertFalse(a["endpoints"]["F2_S1"])
        self.assertEqual(a["verdict"], "AD3_PARTIAL")

    def test_not_supported(self):
        self.assertEqual(self._run(per_sched={"S2": {"AD3": 4}})[0]["verdict"], "AD3_NOT_SUPPORTED")
        self.assertEqual(self._run(per_sched={"C0": {"AD3": 9}})[0]["verdict"], "AD3_NOT_SUPPORTED")
        a, _ = self._run(mislearn="C0")
        self.assertFalse(a["endpoints"]["F4"])
        self.assertEqual(a["verdict"], "AD3_NOT_SUPPORTED")


if __name__ == "__main__":
    unittest.main()
