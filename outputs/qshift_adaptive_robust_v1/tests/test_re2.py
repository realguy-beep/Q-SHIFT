"""RE2 build tests: conditions, pool rules, seal hygiene, seeds, NI floor and analysis on synthetic records.
No sampling. RE2's hidden supports are never opened here; RE1's seal is never read."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import tempfile
import unittest
from multiprocessing import get_context
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import re2  # noqa: E402
import re2_config as C  # noqa: E402

PRIOR_CONFIGS = ("dev2_config", "re1_config", "bre_config", "brs_config", "brt_config")


def _key(kw):
    return (round(kw["gate_p"], 6), round(kw["measurement_p"], 6), kw.get("regime", "balanced"),
            round(kw.get("bias_ratio", 1.0), 6) if kw.get("regime", "balanced") != "balanced" else None)


def _prior_keys():
    import importlib
    keys = set()
    for name in PRIOR_CONFIGS:
        mod = importlib.import_module(name)
        for attr in ("CONDITIONS", "OG", "E2E", "MISMATCH"):
            for v in getattr(mod, attr, {}).values():
                kw = v[0] if isinstance(v, tuple) else v
                if isinstance(kw, dict) and "gate_p" in kw:
                    keys.add(_key(kw))
        for kw in getattr(mod, "MODELS", {}).values() if isinstance(getattr(mod, "MODELS", None), dict) else []:
            if isinstance(kw, dict) and "gate_p" in kw:
                keys.add(_key(kw))
    import ad1_config as A
    for s in ("C0", "D3", "D4"):
        for t in (0, 23):
            keys.add(_key(A.SCHEDULES[s](t)[0]))
    return keys


class ConditionTests(unittest.TestCase):
    def test_distinct_from_prior(self):
        prior = _prior_keys()
        self.assertIn(_key(C.CONDITIONS["G3"][0]), prior | {_key(dict(gate_p=0.0028, measurement_p=0.0028,
                                                                        regime="z_biased", bias_ratio=4.0))})
        for c, v in C.CONDITIONS.items():
            if c == C.REPEATS_R6:
                continue
            self.assertNotIn(_key(v[0]), prior, c)

    def test_g3_is_r6(self):
        import re1_config as R1
        self.assertEqual(C.CONDITIONS["G3"][0], R1.CONDITIONS["R6"][0])

    def test_recipe(self):
        self.assertEqual((C.DET_PER_Q * 3, C.LAB_PER_Q * 3), (12_000, 1_500))
        self.assertEqual(C.ALPHA_ONE_SIDED, 0.0025)
        self.assertEqual(len(C.GATED), 5)
        self.assertEqual(C.arms("G3")[-1], "L2L_B2")
        self.assertNotIn("L2L_B2", C.arms("G1"))
        self.assertNotIn("L2L_B2", C.arms("G3", drop_b2=True))


def _pool_facts():
    import mm_contract as K
    import re2_pool as P
    cl = K.B.load_classes()
    el, pl, reh = P.eligible(), P.pools(), P.rehearsal_bursts()
    dev = P.dev_bursts()
    dev_cls = {K.B.truth(cl, s)[0] for s in dev}
    bad = [ci for v in pl.values() for ci in v
           if ci in dev_cls or any(len(set(el[ci][0]) & set(b)) >= 2 for b in dev)]
    reh_cls = {h: K.B.truth(cl, tuple(s))[0] for h, s in reh.items()}
    strata_ok = all(P.stratum_of(el[ci][1]) == h for h, v in pl.items() for ci in v)
    return {"sizes": {h: len(v) for h, v in pl.items()}, "bad": bad, "strata_ok": strata_ok,
            "reh_in_pool": [h for h, ci in reh_cls.items() if ci in pl[h]], "hash": P.pool_doc()["pool_sha256"]}


class PoolAndSealTests(unittest.TestCase):
    def test_pool(self):
        with get_context("spawn").Pool(1) as pool:
            f = pool.apply(_pool_facts)
        self.assertEqual(f["sizes"], {"H3": 34, "H4": 146})
        self.assertEqual(f["bad"], [])
        self.assertTrue(f["strata_ok"])
        self.assertEqual(f["reh_in_pool"], [])
        commit = json.loads((PKG / "HIDDEN_COMMITMENT_RE2.json").read_text(encoding="utf-8"))
        self.assertEqual(f["hash"], commit["pool"]["pool_sha256"])

    def test_re1_seal_never_read(self):
        for name in ("re2.py", "re2_config.py", "re2_pool.py", "re2_seal.py", "re2_overlap.py", "prepare_re2.py",
                     "preflight_re2.py", "freeze_re2.py"):
            p = PKG / name
            if p.exists():
                src = p.read_text(encoding="utf-8")
                self.assertNotIn("re1_seal.open_seal", src, name)
                self.assertNotIn("qshift_re1_hidden_SEALED", src, name)
        src = (PKG / "re2_contamination.py").read_text(encoding="utf-8")
        self.assertIn("--owner-opened-re1-seal", src)

    def test_seal_roundtrip_dummy(self):
        import re2_seal
        plain = {"schema": "x", "salt": "00", "H3": [1, 2, 3], "H4": [4, 5, 6]}
        self.assertEqual(re2_seal.canonical(plain), b'{"H3":[1,2,3],"H4":[4,5,6],"salt":"00","schema":"x"}')
        commit = json.loads((PKG / "HIDDEN_COMMITMENT_RE2.json").read_text(encoding="utf-8"))
        self.assertEqual(len(commit["sha256_of_canonical_plaintext"]), 64)
        self.assertNotIn("H3", json.dumps(commit["pool"]["rehearsal_bursts"]).replace('"H3"', ""))

    def test_scrub(self):
        rec = {"p_hat": 0.003, "b_hat": 4.0, "excluded": 27, "excluded_set": [1, 2], "flagged": False, "S1": False,
               "S2": False, "class_index": 17, "flip": 0, "support": [1, 2, 3], "class_correct": True,
               "learned_correct": True}
        s = re2.scrub(rec)
        for k in ("excluded_set", "class_index", "flip", "support"):
            self.assertNotIn(k, s)
        self.assertTrue(s["learned_correct"])


def _screened_values():
    import prepare_re2
    return prepare_re2.screened()[0]


class SeedTests(unittest.TestCase):
    def test_seeds(self):
        s = json.loads((PKG / "RE2_SEEDS.json").read_text(encoding="utf-8"))
        self.assertEqual(set(s["seeds"]), set(C.all_keys()))
        self.assertEqual(set(s["rehearsal_seeds"]), set(C.rehearsal_keys()))
        ev, rh = set(s["seeds"].values()), set(s["rehearsal_seeds"].values())
        self.assertEqual(len(ev), len(s["seeds"]))
        self.assertFalse(ev & rh)
        with get_context("spawn").Pool(1) as pool:
            screened = pool.apply(_screened_values)
        self.assertFalse((ev | rh) & screened)


class AnalysisTests(unittest.TestCase):
    def _run(self, extra_l2=None, unlearned=False, oracle_err=3):
        tmp = Path(tempfile.mkdtemp())
        orig = re2.WORK
        try:
            run = tmp / "rehearsal"
            (run / "roots").mkdir(parents=True)
            (run / "archives").mkdir()
            n = 4000
            for c, v in C.CONDITIONS.items():
                for r in range(v[3]):
                    rng = np.random.default_rng(hash((c, r)) % 2**32)
                    arms = C.arms(c)
                    bits, per_q = {}, {}
                    for qi, q in enumerate(C.QS):
                        base = 0 if qi == 0 else oracle_err
                        errs = {}
                        for a in arms:
                            k = {"L2L_E": base, "L2s_true": base, "L2L_B2": base, "A_nominal": 1 if qi == 0 else 30,
                                 "Astar_Em": 10 if qi else 0, "Astar_Nm": 12 if qi else 0, "Astar_true": 9 if qi else 0}[a]
                            if a == "L2L_E" and qi == 1 and r == 0 and extra_l2 and c in extra_l2:
                                k += extra_l2[c]
                            if a == "L2L_E" and qi and r == 0 and unlearned and c == "G3":
                                k += 50
                            e = np.zeros(n, bool)
                            if a in ("L2L_E", "L2s_true", "L2L_B2"):
                                e[:min(base, k)] = True
                                e[base:k] = True
                            else:
                                e[rng.choice(n, size=k, replace=False)] = True
                            bits[f"q{qi}_{a}"] = np.packbits(e)
                            errs[a] = int(e.sum())
                        per_q[str(q)] = {"shots": n, "errors": errs, "seconds": {}}
                    arc = run / "archives" / f"{c}_r{r:02d}.npz"
                    np.savez_compressed(arc, **bits)
                    est = {"p_hat": 0.003, "b_hat": 1.0, "flagged": False, "learned_correct": True}
                    rec = {"cond": c, "root": r, "seeds": {}, "arms": list(arms), "e1t": est,
                           "b2": est if "L2L_B2" in arms else None, "s_star": "Astar_Em", "per_q": per_q,
                           "archive": f"archives/{arc.name}",
                           "archive_sha256": hashlib.sha256(arc.read_bytes()).hexdigest()}
                    (run / "roots" / f"{c}_r{r:02d}.json").write_text(json.dumps(rec), encoding="utf-8")
            (run / "RUN_STATUS.json").write_text(json.dumps({"state": "ready_for_analysis", "head": "x", "started": "",
                                                             "finished": "", "wall_seconds": 0, "n_jobs": 66}))
            return re2.analyze("rehearsal", run)
        finally:
            re2.WORK = orig
            shutil.rmtree(tmp)

    def test_confirmed(self):
        a = self._run()
        self.assertEqual(a["overall_verdict"], "CONFIRMED", {c: v.get("status") for c, v in a["conditions"].items()})

    def test_floor_tolerates_small_discordance(self):
        a = self._run(extra_l2={"G2": 2}, oracle_err=1)
        g2 = a["conditions"]["G2"]
        self.assertTrue(g2["NI"]["floor_binds"])
        self.assertTrue(g2["NI"]["passes"])
        self.assertFalse(g2["NI_strict"]["passes"])

    def test_floor_rejects_three(self):
        a = self._run(extra_l2={"G2": 3}, oracle_err=1)
        self.assertFalse(a["conditions"]["G2"]["NI"]["passes"])

    def test_unlearned_root_fails(self):
        a = self._run(unlearned=True)
        self.assertEqual(a["conditions"]["G3"]["status"], "FAIL_DIRECTION")
        self.assertEqual(a["overall_verdict"], "NOT_CONFIRMED")


if __name__ == "__main__":
    unittest.main()
