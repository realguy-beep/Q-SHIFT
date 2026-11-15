from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from outputs.qshift_correlated_decoder_v1_3 import contract as K
from outputs.qshift_correlated_decoder_v1_3 import run_eval
from outputs.qshift_correlated_decoder_v1_3.analyze_saved import decide
from outputs.qshift_correlated_decoder_v1_3.common import V1_1_PACKAGE, sha256_file
from outputs.qshift_correlated_decoder_v1_3.prepare_seeds import build_inventory, planned_labels
from outputs.qshift_correlated_decoder_v1_3.select_static import select_min

PKG = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class DecisionRuleTests(unittest.TestCase):
    base = dict(star_ci=[-0.003, -0.001], a2_ci=[-0.003, -0.001], astar_nonzero_errors=500,
                b_better_both=True, q0_bounds=[-0.001, 0.0001])

    def test_go_requires_every_condition(self) -> None:
        self.assertEqual(decide(**self.base), "GO_DEVELOPMENT_ONLY")
        for change in ({"a2_ci": [-0.002, 0.0001]}, {"star_ci": [-0.002, 0.0001]},
                       {"astar_nonzero_errors": 99}, {"b_better_both": False},
                       {"q0_bounds": [-0.001, 0.0005]}):
            self.assertNotEqual(decide(**{**self.base, **change}), "GO_DEVELOPMENT_ONLY", change)

    def test_beating_a2_alone_is_not_go(self) -> None:
        self.assertEqual(decide(**{**self.base, "star_ci": [-0.001, 0.0002]}), "INCONCLUSIVE")

    def test_no_go_conditions(self) -> None:
        self.assertEqual(decide(**{**self.base, "star_ci": [0.0, 0.002]}), "NO_GO")
        self.assertEqual(decide(**{**self.base, "q0_bounds": [0.0006, 0.001]}), "NO_GO")


class SeedInventoryTests(unittest.TestCase):
    def test_committed_inventory_is_reproducible_complete_and_disjoint(self) -> None:
        committed = load(PKG / "seed_inventory.json")
        self.assertEqual(committed, build_inventory())
        self.assertEqual(set(committed["seeds"]), set(planned_labels()))
        self.assertEqual(len(committed["seeds"]), 2 * K.FROZEN_ALLOCATION.roots + 2)
        mine = set(committed["seeds"].values())
        for prior in (V1_1_PACKAGE / "seed_inventory.json", PKG.parent / "qshift_correlated_decoder_v1_2" / "seed_inventory.json"):
            self.assertFalse(set(load(prior)["seeds"].values()) & mine, prior)


class SelectionRecordTests(unittest.TestCase):
    def test_selection_rule_and_tie_break(self) -> None:
        self.assertEqual(select_min({0.0: 5, 0.005: 3, 0.01: 3}), 0.005)
        on_first = lambda k: (k[1], not k[0])  # noqa: E731
        self.assertEqual(select_min({(True, 0.0): 3, (False, 0.0): 3}, on_first), (True, 0.0))

    def test_committed_selection_is_consistent_with_its_own_tables(self) -> None:
        record = load(PKG / "STATIC_SELECTION.json")
        sel = record["selected"]
        static = {(row["correlations"], row["q"]): row["total"] for row in record["static_matching"]}
        self.assertEqual(static, {(r["correlations"], r["q"]): sum(r["errors_by_condition"])
                                  for r in record["static_matching"]})
        astar = select_min(static, lambda k: (k[1], not k[0]))
        self.assertEqual(sel[K.SEL_ASTAR], {"correlations": astar[0], "q": astar[1]})
        alt = select_min({k: v for k, v in static.items() if k[0] != astar[0]}, lambda k: k[1])
        self.assertEqual(sel[K.SEL_ASTAR_ALT], {"correlations": alt[0], "q": alt[1]})
        self.assertEqual(sel[K.SEL_TAU], select_min({r["tau"]: r["total"] for r in record["a2sw"]}))
        self.assertEqual(sel[K.SEL_BOFFSTATIC_Q], select_min({r["q"]: r["total"] for r in record["boff_static"]}))
        self.assertEqual(record["sampler_calls"], 0)
        self.assertTrue(record["selection_set"]["recomputed_on_at_qhat_matches_saved_A2"])

    def test_static_on_matching_reconciles_with_v1_2_astar(self) -> None:
        record = load(PKG / "STATIC_SELECTION.json")
        row = next(r for r in record["static_matching"] if r["correlations"] and r["q"] == 0.005)
        self.assertEqual(row["errors_by_condition"], [835, 1186, 1543])  # V1.2 RESULTS.md, arm Astar


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
