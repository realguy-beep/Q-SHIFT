"""Phase C contract tests (no sampling; the hidden seal is never opened here)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
REPO = PKG.parents[1]
sys.path.insert(0, str(PKG))
import c_analyze  # noqa: E402
import c_contract as C  # noqa: E402
import c_seal  # noqa: E402
import c_seeds  # noqa: E402


class ContractTests(unittest.TestCase):
    def test_allocation(self):
        self.assertEqual(C.FROZEN.jobs, 144)
        self.assertEqual(C.FROZEN.jobs * C.FROZEN.shots_per_root, 1_200_096)

    def test_frozen_selections_match_sources(self):
        prior = json.loads((REPO / "outputs/qshift_scalable_decoder_eval_d57_v1/PHASE2_D5_PRIOR.json").read_text(encoding="utf-8"))
        self.assertEqual(C.L2_PRIOR, prior["selected_q_dec"])
        src = (REPO / "outputs/qshift_scalable_decoder_eval_d5_phase2_v1/contract.py").read_text(encoding="utf-8")
        self.assertIn("ASTAR_Q_DEC = 0.0025", src)
        self.assertEqual(C.ASTAR_Q_DEC, 0.0025)
        self.assertEqual(C.KNOWN_SUPPORT, (23, 31, 34))

    def test_tau_is_committed_b2_threshold(self):
        self.assertAlmostEqual(C.tau(), 1561.2180618148327, places=9)

    def test_hidden_support_guarded(self):
        self.assertEqual(C.true_support("H", "rehearsal"), C.SURROGATE_H)
        self.assertEqual(C.true_support("H", "fake"), C.SURROGATE_H)
        with self.assertRaises(SystemExit):
            C.true_support("H", "eval", hidden_authorized=False)

    def test_seal_commitment_and_pool(self):
        commit = json.loads(c_seal.COMMITMENT.read_text(encoding="utf-8"))
        pool = c_seal.candidate_pool()
        self.assertEqual(commit["candidate_pool_size"], len(pool))
        self.assertEqual(len(pool), 2291)
        self.assertNotIn(C.KNOWN_SUPPORT, pool)
        self.assertEqual(len(commit["sha256_of_canonical_plaintext"]), 64)


class SeedTests(unittest.TestCase):
    def test_complete_disjoint_screened(self):
        s = json.loads((PKG / "C_SEEDS.json").read_text(encoding="utf-8"))
        self.assertEqual(set(s["seeds"]), set(C.all_seed_keys(C.FROZEN)))
        self.assertEqual(set(s["rehearsal_seeds"]), set(C.all_seed_keys(C.REHEARSAL)) | {"d5ls:C:fake"})
        ev, rh = set(s["seeds"].values()), set(s["rehearsal_seeds"].values())
        self.assertEqual(len(ev), len(s["seeds"]))
        self.assertFalse(ev & rh)
        screened, _ = c_seeds.screened_values()
        self.assertFalse((ev | rh) & screened)


class DecisionTests(unittest.TestCase):
    def test_decide(self):
        self.assertEqual(c_analyze.decide([-2e-3, -1e-3], -5e-4, 7e-5), "GO")
        self.assertEqual(c_analyze.decide([-2e-3, 1e-4], -5e-4, 7e-5), "INCONCLUSIVE")
        self.assertEqual(c_analyze.decide([1e-4, 1e-3], -5e-4, 7e-5), "NO-GO")
        self.assertEqual(c_analyze.decide([-2e-3, -1e-3], 1e-4, 7e-5), "NO-GO")

    def test_overall(self):
        def v(dec, bonf, safe=True):
            return {"decision": dec, "co_primary": {"passes_bonferroni": bonf}, "safety_q0": {"passes": safe}}
        self.assertEqual(c_analyze.overall({"K": v("GO", True), "H": v("GO", True)}), "CONFIRMED")
        self.assertEqual(c_analyze.overall({"K": v("GO", True), "H": v("INCONCLUSIVE", False)}), "PARTIAL")
        self.assertEqual(c_analyze.overall({"K": v("GO", True), "H": v("NO-GO", False)}), "NOT_CONFIRMED")
        self.assertEqual(c_analyze.overall({"K": v("GO", False), "H": v("INCONCLUSIVE", False)}), "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
