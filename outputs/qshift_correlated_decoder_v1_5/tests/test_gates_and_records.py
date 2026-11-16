from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from outputs.qshift_correlated_decoder_v1_5 import contract as K
from outputs.qshift_correlated_decoder_v1_5 import run_eval
from outputs.qshift_correlated_decoder_v1_5.analyze_saved import decide, target
from outputs.qshift_correlated_decoder_v1_5.common import V1_1_PACKAGE, sha256_file
from outputs.qshift_correlated_decoder_v1_5.prepare_seeds import build_inventory, planned_labels

PKG = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class DecisionRuleTests(unittest.TestCase):
    base = dict(ref_ci=[-0.003, -0.001], static_ci=[-0.008, -0.006], ref_nonzero_errors=500,
                cand_better_both=True, q0_bounds=[-0.001, 0.0001])

    def test_go_requires_every_condition(self) -> None:
        self.assertEqual(decide(**self.base), "GO_DEVELOPMENT_ONLY")
        for change in ({"ref_ci": [-0.002, 0.0001]}, {"static_ci": [-0.002, 0.0001]},
                       {"ref_nonzero_errors": 99}, {"cand_better_both": False},
                       {"q0_bounds": [-0.001, 0.0005]}):
            self.assertNotEqual(decide(**{**self.base, **change}), "GO_DEVELOPMENT_ONLY", change)

    def test_beating_astar_alone_is_not_go(self) -> None:
        self.assertEqual(decide(**{**self.base, "ref_ci": [-0.001, 0.0002]}), "INCONCLUSIVE")

    def test_no_go_conditions(self) -> None:
        self.assertEqual(decide(**{**self.base, "ref_ci": [0.0, 0.002]}), "NO_GO")
        self.assertEqual(decide(**{**self.base, "q0_bounds": [0.0006, 0.001]}), "NO_GO")

    def test_target_endpoint_uses_the_lower_bound(self) -> None:
        self.assertEqual(target([0.10, 0.30]), "TARGET_MET")
        self.assertEqual(target([0.099, 0.40]), "TARGET_NOT_MET")


class SeedInventoryTests(unittest.TestCase):
    def test_committed_inventory_is_reproducible_complete_and_disjoint(self) -> None:
        committed = load(PKG / "seed_inventory.json")
        self.assertEqual(committed, build_inventory())
        self.assertEqual(set(committed["seeds"]), set(planned_labels()))
        self.assertEqual(len(committed["seeds"]), 2 * K.FROZEN_ALLOCATION.roots + 2)
        mine = set(committed["seeds"].values())
        priors = [V1_1_PACKAGE / "seed_inventory.json"] + [PKG.parent / rel for rel in (
            "qshift_correlated_decoder_v1_2/seed_inventory.json", "qshift_correlated_decoder_v1_3/seed_inventory.json",
            "qshift_correlated_decoder_v1_4/GATE_SEEDS.json")]
        for prior in priors:
            self.assertFalse(set(load(prior)["seeds"].values()) & mine, prior)


class FrozenSettingsTests(unittest.TestCase):
    def test_v1_5_reads_v1_3_settings_unchanged(self) -> None:
        v13 = PKG.parent / "qshift_correlated_decoder_v1_3"
        self.assertEqual(run_eval.SELECTION_PATH, v13 / "STATIC_SELECTION.json")
        freeze = load(v13 / "PRETEST_FREEZE.json")["files"]
        self.assertEqual(sha256_file(run_eval.SELECTION_PATH),
                         freeze["outputs/qshift_correlated_decoder_v1_3/STATIC_SELECTION.json"])
        sel = load(run_eval.SELECTION_PATH)["selected"]
        self.assertEqual(sel[K.SEL_ASTAR], {"correlations": True, "q": 0.00375})
        self.assertEqual(sel[K.SEL_TAU], 0.0005)
        self.assertEqual(sel[K.SEL_BOFFSTATIC_Q], 0.01125)

    def test_imported_v1_3_decoder_and_v1_4b_exact_decoder_are_pinned(self) -> None:
        v13 = PKG.parent / "qshift_correlated_decoder_v1_3"
        freeze = load(v13 / "PRETEST_FREEZE.json")["files"]
        self.assertEqual(sha256_file(v13 / "multi_prior.py"), freeze["outputs/qshift_correlated_decoder_v1_3/multi_prior.py"])


class FrozenDependencyTests(unittest.TestCase):
    def test_imported_v1_1_files_match_the_v1_1_pretest_freeze(self) -> None:
        freeze = load(V1_1_PACKAGE / "PRETEST_FREEZE.json")["files"]
        for name in ("model.py", "verify_reuse.py", "REUSE_VERIFICATION.json", "seed_inventory.json"):
            rel = f"outputs/qshift_correlated_decoder_feasibility_v1_1/{name}"
            self.assertEqual(sha256_file(V1_1_PACKAGE / name), freeze[rel], name)


class RunnerGateTests(unittest.TestCase):
    def test_default_command_is_sampler_free_dry_run(self) -> None:
        with mock.patch.object(sys, "argv", ["run_eval.py"]), \
             mock.patch.object(run_eval, "dry_run") as dry, mock.patch.object(run_eval, "execute") as ex:
            run_eval.main()
        dry.assert_called_once()
        ex.assert_not_called()

    def test_execute_requires_full_commit_sha(self) -> None:
        with mock.patch.object(sys, "argv", ["run_eval.py", "--execute", "--expected-head", "abc"]), \
             mock.patch.object(run_eval, "execute") as ex:
            with self.assertRaises(SystemExit):
                run_eval.main()
        ex.assert_not_called()

    def test_execute_refuses_outside_watchdog(self) -> None:
        with mock.patch.dict(os.environ, {run_eval.WATCHDOG_ENV: ""}):
            with self.assertRaisesRegex(RuntimeError, "watchdog"):
                run_eval.execute("0" * 40, Path("."))


if __name__ == "__main__":
    unittest.main()
