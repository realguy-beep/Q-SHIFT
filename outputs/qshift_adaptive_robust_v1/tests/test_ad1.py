"""AD1 build tests: schedules, causality, seeds, analysis logic on synthetic records (no sampling)."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import ad1  # noqa: E402
import ad1_config as C  # noqa: E402
import ad1_stream as ST  # noqa: E402
import prepare_ad1  # noqa: E402


class ScheduleTests(unittest.TestCase):
    def test_schedules(self):
        self.assertAlmostEqual(ST.block_truth("D1", 0)[0]["gate_p"], 0.0025)
        self.assertAlmostEqual(ST.block_truth("D1", 23)[0]["gate_p"], 0.0035)
        self.assertAlmostEqual(ST.block_truth("D2", 23)[0]["bias_ratio"], 8.0)
        self.assertEqual(ST.block_truth("D4", 11)[0]["gate_p"], 0.0025)
        self.assertEqual(ST.block_truth("D4", 12)[0]["gate_p"], 0.0035)
        on = [ST.block_truth("D3", t)[1] is not None for t in range(C.BLOCKS)]
        self.assertEqual(on, [8 <= t <= 15 for t in range(C.BLOCKS)])
        self.assertEqual(len(C.BURSTS["X13"]), 3)
        self.assertEqual(len(C.BURSTS["W13"]), 3)

    def test_large_bursts(self):
        import estimate3 as E3
        import mm_contract as K
        cl = K.B.load_classes()
        for b in ("X13", "W13"):
            self.assertEqual(len(E3.class_detectors(cl[K.B.truth(cl, C.BURSTS[b])[0]])), 30)

    def test_window_is_causal(self):
        """The estimate for block t is a function only of blocks t-6..t-1 (checked on the job's slicing)."""
        src = (PKG / "ad1.py").read_text(encoding="utf-8")
        self.assertIn("w0 = t - C.WINDOW", src)
        self.assertIn("estimate_window(dets[w0:t], labx[w0:t], laby[w0:t]", src)
        self.assertLess(src.index("estimate_window(dets[w0:t]"), src.index('key = C.block_key(s, e, t, "eval")'))


class SeedTests(unittest.TestCase):
    def test_seeds(self):
        s = json.loads((PKG / "AD1_SEEDS.json").read_text(encoding="utf-8"))
        self.assertEqual(set(s["seeds"]), set(C.all_keys()))
        self.assertEqual(set(s["rehearsal_seeds"]), set(C.rehearsal_keys()))
        ev, rh = set(s["seeds"].values()), set(s["rehearsal_seeds"].values())
        self.assertEqual(len(ev), len(s["seeds"]))
        self.assertFalse(ev & rh)
        from multiprocessing import get_context
        with get_context("spawn").Pool(1) as pool:
            screened = pool.apply(_screened_values)
        self.assertFalse((ev | rh) & screened)


def _screened_values():
    return prepare_ad1.screened()[0]


class AnalysisTests(unittest.TestCase):
    def _write(self, tmp, s, e, err_fn, est_fn, n=100):
        bits, blocks = {}, []
        rng = np.random.default_rng(hash((s, e)) % 2**32)
        for t in C.SCORED:
            errs = {}
            for a in C.ARMS:
                k = err_fn(a, t)
                v = np.zeros(n, bool)
                v[rng.choice(n, size=k, replace=False)] = True
                bits[f"b{t:02d}_{a}"] = np.packbits(v)
                errs[a] = k
            blocks.append({"block": t, "true": {}, "burst_on": True, "window_burst": True, "estimate": est_fn(t),
                           "errors": errs})
        arc = tmp / "archives" / f"{s}_e{e}.npz"
        np.savez_compressed(arc, **bits)
        rec = {"schedule": s, "episode": e, "seeds": {}, "eval_per_block": n, "blocks": blocks,
               "archive": f"archives/{arc.name}", "archive_sha256": hashlib.sha256(arc.read_bytes()).hexdigest()}
        (tmp / "records" / f"{s}_e{e}.json").write_text(json.dumps(rec), encoding="utf-8")

    def _run(self, adapt_good):
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "records").mkdir()
            (tmp / "archives").mkdir()
            n_jobs = 0
            for s in C.SCHEDULES:
                for e in range(3):
                    def err(a, t, s=s):
                        base = {"ORACLE": 2, "AD": 2 if adapt_good else 6, "ONCE": 2 if s == "C0" else 8,
                                "AD_M": 6, "A_nominal": 12}[a]
                        return base

                    def est(t, s=s):
                        on = s != "D3" or 8 <= t <= 15
                        learned = s != "D3" or 10 <= t <= 15
                        cls = 7 if (learned or (s == "D3" and 16 <= t <= 19)) else None
                        return {"flagged": False, "class_index": cls, "true_class": 7 if (on or (s == "D3" and 16 <= t <= 21)) else None,
                                "learned_correct": learned and on, "p_hat": 0.003, "b_hat": 1.0}
                    self._write(tmp, s, e, err, est)
                    n_jobs += 1
            (tmp / "RUN_STATUS.json").write_text(json.dumps({"state": "ready_for_analysis", "n_jobs": n_jobs}))
            return ad1.analyze("rehearsal", tmp)
        finally:
            shutil.rmtree(tmp)

    def test_supported(self):
        a = self._run(True)
        self.assertEqual(a["verdict"], "AD1_SUPPORTED", a["endpoints"])
        self.assertEqual(a["schedules"]["D3"]["onset_latency"], [2, 2, 2])
        self.assertEqual(a["schedules"]["D3"]["offset_latency"], [4, 4, 4])

    def test_poor_tracking(self):
        a = self._run(False)
        self.assertEqual(a["verdict"], "AD1_NOT_SUPPORTED")
        self.assertFalse(a["endpoints"]["tracking_D1"])


if __name__ == "__main__":
    unittest.main()
