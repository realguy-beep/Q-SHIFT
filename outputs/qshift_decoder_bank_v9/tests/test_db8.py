"""DB8 tests: config and selection, the support/truth extensions, loop = DB6 + DB8 lines, the rule truth table, the
analyzer criteria, run-guard wiring, a sampler-free synthetic truth-invariance run, seeds, no seal, LF only."""
from __future__ import annotations

import inspect
import json
import sys
import tempfile
import unittest
from multiprocessing import get_context
from pathlib import Path

import numpy as np

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
import db8_config as C  # noqa: E402
import db8_analyze as A  # noqa: E402
import db8_core as L8  # noqa: E402
import db8_run as R  # noqa: E402

TR = json.loads((C.DB1 / "TRAINING.json").read_text(encoding="utf-8"))
TPL = {k: np.array(v) for k, v in TR["templates"].items()}


class ConfigTests(unittest.TestCase):
    def test_config(self):
        self.assertEqual(sum(C.EPISODES.values()), 64)
        self.assertEqual(sum(C.INBANK.values()), 24)
        self.assertEqual(C.ARMS[:len(C.C6.ARMS)], C.C6.ARMS)
        self.assertEqual(set(C.ARMS) - set(C.C6.ARMS),
                         {"LA_R1", "LA_R2", "LA_R2_170", "CB", "FIX_OFF", "FIX_A", "FIX_B", "FIX_C", "FIX_D"})
        self.assertTrue(all(k.startswith("db8:") for k in C.all_keys()))
        self.assertEqual((C.R2_CAP, C.R2_CAP_SECONDARY), (180.0, 170.0))
        prm = {"onset": 10}
        self.assertEqual([C.block_state("U_OUT", t, prm) for t in (9, 10, 29)], ["A", "UO", "UO"])
        self.assertEqual(C.changes("U_NEAR", prm), [10])

    def test_selection_reproduces(self):
        import select_unknowns as S
        sel = S.select()
        saved = json.loads((PKG / "SELECTION.json").read_text(encoding="utf-8"))["states"]
        self.assertEqual(json.loads(json.dumps(sel)), saved)
        for k in ("UF", "UO", "UN"):
            self.assertEqual(tuple(sel[k]["support"]), C.NEW_UNKNOWN[k])
        self.assertEqual((sel["UF"]["label"], sel["UO"]["label"], sel["UN"]["label"]), ("X03", "V01+q3", "X09"))
        self.assertFalse(sel["UO"]["in_catalog"])
        self.assertTrue(all(sel[k]["in_catalog"] for k in ("E", "UF", "UN")))


class ExtensionTests(unittest.TestCase):
    def test_support(self):
        import db_config as DC
        self.assertIs(DC.support, C.support)
        self.assertEqual(C.support("UO"), (1, 3, 12, 38))
        for s in C.STATES + ("E",):
            self.assertEqual(C.support(s), C._support0(s))

    def test_truth_only_for_out_of_catalog(self):
        import mm_contract as K
        classes = K.B.load_classes()
        self.assertEqual(K.B.truth(classes, (38, 12, 3, 1)), (None, None))
        self.assertEqual(K.B.truth(classes, C.support("E")), C._truth0(classes, C.support("E")))
        with self.assertRaises(KeyError):
            K.B.truth(classes, (1, 3, 12, 40))                 # any other out-of-catalog support still raises

    def test_models_build_for_new_supports(self):
        from outputs.qshift_correlated_decoder_v1_4 import model_v14 as m
        import db_core as D
        sp = D.C.spec(gate_p=D.C.P0, measurement_p=D.C.P0)
        for s in C.NEW_UNKNOWN:
            c = m.build_candidate_circuit(sp, D.C.BURST_Q, C.support(s))
            self.assertEqual(c.num_detectors, TPL["A"].size)


class LoopTests(unittest.TestCase):
    src = (PKG / "db8_run.py").read_text(encoding="utf-8")

    def test_loop_is_db6_plus_db8_lines(self):
        d6 = (C.DB6 / "db6_run.py").read_text(encoding="utf-8")
        cut = lambda s: s[s.index("def _bank_arm"):s.index("# ------------------------------------------------------------------ input tracing")]  # noqa: E731
        mine = cut(self.src).splitlines()
        added = [ln for ln in mine if "# DB8" in ln or "L8." in ln or "C.NEW_UNKNOWN" in ln or "C.FIX_ARMS" in ln
                 or 'blocks[-1]["db8"]' in ln]
        added_idx = [i for i, ln in enumerate(mine) if ln in added]
        self.assertEqual(len(added), 9)      # for-loop, cb_prev, gf1, R1, R2, R2_170, CB, FIX, db8 field
        nxt = mine[added_idx[0] + 1]                       # the models line under the DB8 for-loop is a DB6 line copy
        self.assertEqual(nxt.strip(), 'models["bank:" + st] = (p0, C.support(st))')
        rest = [ln for i, ln in enumerate(mine) if i not in added_idx and i != added_idx[0] + 1]
        self.assertEqual("\n".join(rest).rstrip("\n"), cut(d6).rstrip("\n"))

    def test_order(self):
        s = self.src
        i_la2 = s.index("keys[arm], srcs[arm] = L6.la_key(keys[base], la, gated=False)")
        i_r = s.index("L8.rule_key(")
        self.assertLess(s.index("prev.update(keys)"), i_r)
        self.assertLess(i_la2, i_r)
        self.assertLess(i_r, s.index('x, y = D.sample(st_t, n_eval, seed(t, "eval"))'))


class RuleTests(unittest.TestCase):
    def test_rule_key(self):
        gf = {"OFF": 300, "A": 300, "B": 150, "C": 300, "D": 300}
        la = {"alarm": True, "P1": ["B"]}
        self.assertEqual(L8.rule_key("bank:A", la, gf, None), ("bank:B", "lookahead"))
        self.assertEqual(L8.rule_key("bank:A", la, gf, 180.0), ("bank:B", "lookahead"))
        self.assertEqual(L8.rule_key("bank:A", la, {**gf, "B": 190}, 180.0), ("bank:A", "base"))
        self.assertEqual(L8.rule_key("bank:A", la, {**gf, "B": 180}, 180.0), ("bank:B", "lookahead"))   # <= cap
        self.assertEqual(L8.rule_key("bank:B", la, gf, None), ("bank:B", "base"))           # no-op suppressed
        self.assertEqual(L8.rule_key("bank:A", {"alarm": False, "P1": ["B"]}, gf, None), ("bank:A", "base"))
        self.assertEqual(L8.rule_key("bank:A", {"alarm": True, "P1": ["A", "B"]}, gf, None), ("bank:A", "base"))
        self.assertEqual(L8.rule_key("ad:x", {"alarm": True, "P1": []}, gf, None), ("ad:x", "base"))

    def test_cb_key(self):
        tau, risk = TR["tau_fit"], TR["risk"]
        gf = {"OFF": 300, "A": 300, "B": 150, "C": 300, "D": 300}
        self.assertEqual(L8.cb_key(gf, tau, risk, "A", "bank:A"), ("bank:B", "cb", "B"))
        self.assertEqual(L8.cb_key({k: 999 for k in gf}, tau, risk, "B", "bank:OFF"), ("bank:OFF", "w0f", "B"))

    def test_single_fit_reads_only_t(self):
        rng = np.random.default_rng(3)
        cnt = [(rng.binomial(2000, TPL["OFF"]), 2000) for _ in range(9)]
        a = L8.single_fit(cnt, 7, TPL)
        cnt2 = cnt[:7] + [cnt[7]] + [(rng.binomial(2000, TPL["A"]), 2000)]
        cnt2[:7] = [(rng.binomial(2000, TPL["B"]), 2000) for _ in range(7)]
        self.assertEqual(a, L8.single_fit(cnt2, 7, TPL))


def _row(s, e, err, fires=None, wrong=None, block_harm=None):
    base = {a: 10 for a in C.ARMS}
    base.update(err)
    return {"schedule": s, "episode": e, "errors": base,
            "block_harm": {a: (block_harm or {}).get(a, 0) for a in ("LA_R2", "LA_R2_170", "LA_R1", "CB")},
            "shot_harm": {}, "fires": fires or {}, "wrong_actions": {a: (wrong or {}).get(a, 0)
                                                                     for a in ("LA_R2", "LA_R2_170", "LA_R1")},
            "wrong_ident_LA_W0F": 0}


class AnalysisTests(unittest.TestCase):
    def rows(self, **kw):
        rows = []
        for s, n in C.INBANK.items():
            for e in range(n):
                rows.append(_row(s, e, {"W0F": 20, "LA_W0F": 10, "LA_R2": 11, "LA_R2_170": 12, "LA_R1": 10,
                                        "CB": 30, "LA_DB2": 15}))
        for s, n in C.UNKNOWN_EP.items():
            for e in range(n):
                rows.append(_row(s, e, {"W0F": 20, "LA_W0F": 20, "LA_R2": 20, "LA_R2_170": 20, "LA_R1": 20,
                                        "CB": 30, "LA_DB2": 20}, wrong={"LA_R1": 1 if e < 5 else 0}))
        return rows

    def test_advance(self):
        c = A.criteria(self.rows(), "LA_R2")
        self.assertAlmostEqual(c["A1"]["retention"], 0.9)
        self.assertTrue(c["A1"]["pass"] and c["A2"]["pass"] and c["A3"]["pass"] and c["A4"]["pass"])
        self.assertEqual(c["A2"]["LA_R1_wrong_action_episodes"], 10)
        self.assertFalse(A.criteria(self.rows(), "LA_R2_170")["A1"]["pass"])        # retention 0.8

    def test_failures(self):
        rows = self.rows()
        for x in rows:
            if x["schedule"] == "U_FAR" and x["episode"] < 3:
                x["wrong_actions"]["LA_R2"] = 1
        self.assertFalse(A.criteria(rows, "LA_R2")["A2"]["pass"])                    # 3 > 2
        rows = self.rows()
        rows[-1]["errors"]["LA_R2"] = 33                                                # U_NEAR episode +13
        self.assertFalse(A.criteria(rows, "LA_R2")["A3"]["pass"])
        rows = self.rows()
        for x in rows:
            x["errors"]["CB"] = 0
        self.assertFalse(A.criteria(rows, "LA_R2")["A4"]["pass"])

    def test_decide_secondary_only_when_primary_fails_only_a2(self):
        p = {"ADVANCE": False, "A1": {"pass": True}, "A2": {"pass": False}, "A3": {"pass": True}, "A4": {"pass": True}}
        s = {"ADVANCE": True}
        self.assertEqual(A.decide(p, s, {"CB": 9, "LA_R2": 5})["arm_for_CF3_plan"], "LA_R2_170")
        p["A1"]["pass"] = False
        self.assertIsNone(A.decide(p, s, {"CB": 9, "LA_R2": 5})["arm_for_CF3_plan"])

    def test_loader_and_descriptive(self):
        src = inspect.getsource(A.analyze)
        self.assertIn("RK.load_strict(", src)
        self.assertNotIn("sign_p", inspect.getsource(A.analyze).split('"reported"')[1])


class RunGuardTests(unittest.TestCase):
    def test_wiring(self):
        body = inspect.getsource(R.cmd_run)
        for need in ("RK.check_revision(expected_head, FREEZE_REL, fz[\"code_head\"], _git, (RESULTS_REL,))",
                     "RK.check_runtime(fz[\"runtime\"])", "check_freeze(fz)", "all_pass", "RK.Reservation(run",
                     "RK.run_jobs(jobs, episode_job, run, _outputs"):
            self.assertIn(need, body)
        self.assertNotIn("except", body)
        self.assertIn("ldpc", R.RK.RUNTIME_PACKAGES)


# ------------------------------------------------------------------ sampler-free synthetic truth invariance
STATES9 = ["OFF"] * 6 + ["B", "B", "B"]
PARTS = {"det": 1, "lab": 2, "eval": 3}


def _seed(t, p):
    return 1_000 * t + PARTS[p]


def _mini(args):
    perturb, out = args
    sys.path.insert(0, str(PKG))
    import db8_config as CC
    import ad2
    import db_core as D
    import db8_run as RD
    import stim

    def no_sampler(*a, **k):
        raise AssertionError("stim sampler used")
    stim.Circuit.compile_detector_sampler = no_sampler
    stim.Circuit.compile_sampler = no_sampler
    tpl = {k: np.array(v) for k, v in json.loads((CC.DB1 / "TRAINING.json").read_text(encoding="utf-8"))["templates"].items()}

    def sample(state, n, sd):
        t, code = divmod(sd, 1_000)
        part = {v: k for k, v in PARTS.items()}[code]
        st = "A" if perturb == "future_det" and part == "det" and t == len(STATES9) - 1 else state
        rng = np.random.default_rng(sd)
        x = (rng.random((n, tpl["OFF"].size)) < tpl[st]).astype(np.uint8)
        y = (rng.random(n) < 0.03).astype(np.uint8)
        if (perturb == "eval" and part == "eval") or (perturb == "lab_current" and part == "lab" and t == 7):
            y = 1 - y
        return x, y
    CC.BLOCKS = len(STATES9)
    RD._setup = lambda mode, s, e: ((lambda t: STATES9[t]), _seed, 64, {}, [6])
    D.sample = sample
    if perturb == "truth_meta":
        est = ad2.estimate
        ad2.estimate = lambda dets, labx, laby, classes, truth_sup: est(dets, labx, laby, classes, CC.support("A"))
    Path(out, "records").mkdir(parents=True, exist_ok=True)
    RD.episode_job(("mini", "MINI", 0, out))
    return json.loads(Path(out, "records", "MINI_e0.json").read_text(encoding="utf-8"))


def _decisions(rec, upto):
    return [({a: k for a, k in b["keys"].items() if a != "ORACLE"}, b["source"], b["lookahead"], b["plausible"],
             b["alarm"], b["seg0"], b["db8"]) for b in rec["blocks"] if b["block"] <= upto]


class TruthInvarianceTests(unittest.TestCase):
    def test_synthetic_invariance(self):
        d = Path(tempfile.mkdtemp())
        modes = ("base", "eval", "lab_current", "truth_meta", "future_det")
        with get_context("spawn").Pool(len(modes)) as pool:
            recs = dict(zip(modes, pool.map(_mini, [(m, str(d / m)) for m in modes])))
        base = recs["base"]
        b6 = base["blocks"][0]
        self.assertEqual(b6["source"]["LA_R2"], "lookahead")
        self.assertEqual(b6["keys"]["LA_R2"], "bank:B")
        self.assertEqual({b6["keys"][a] for a in C.FIX_ARMS}, {"bank:" + s for s in C.STATES})
        for m in ("eval", "truth_meta"):
            self.assertEqual(_decisions(recs[m], 8), _decisions(base, 8), m)
        self.assertEqual(_decisions(recs["lab_current"], 7), _decisions(base, 7))
        self.assertEqual(_decisions(recs["future_det"], 7), _decisions(base, 7))
        self.assertNotEqual(recs["future_det"]["blocks"][2]["db8"], base["blocks"][2]["db8"])


class SourceTests(unittest.TestCase):
    def test_no_seal(self):
        for p in list(PKG.glob("*.py")) + list((PKG / "tests").glob("*.py")):
            s = p.read_text(encoding="utf-8")
            for bad in ("open_" "seal", "_SEA" "LED", "re1_" "seal", "re2_" "seal", "HIDDEN_" "COMMITMENT",
                        "R" "6_*", "cf1/" "records", "results/" "cf", "work/" "cf"):
                self.assertNotIn(bad, s, p.name)

    def test_lf_only(self):
        for p in list(PKG.rglob("*.py")) + list(PKG.rglob("*.md")) + list(PKG.rglob("*.json")):
            if "__pycache__" not in p.parts and "work" not in p.parts:
                self.assertNotIn(b"\r\n", p.read_bytes(), p.name)


class SeedTests(unittest.TestCase):
    def test_seeds(self):
        s = json.loads((PKG / "DB8_SEEDS.json").read_text(encoding="utf-8"))
        self.assertEqual(set(s["seeds"]), set(C.all_keys()))
        v = set(s["seeds"].values())
        self.assertEqual(len(v), len(s["seeds"]))
        self.assertIn("outputs/qshift_decoder_bank_v7/CF2_SEEDS.json", s["screened"])
        import prepare_db8                            # its child never imports db8_config (module docstring)
        with get_context("spawn").Pool(1) as pool:
            self.assertFalse(v & pool.apply(prepare_db8.screened_values))


if __name__ == "__main__":
    unittest.main()
