from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from outputs.qshift_correlated_decoder_v1_2 import contract as K
from outputs.qshift_correlated_decoder_v1_2 import run_eval
from outputs.qshift_correlated_decoder_v1_2.analyze_saved import decide
from outputs.qshift_correlated_decoder_v1_2.common import V1_1_PACKAGE, sha256_file
from outputs.qshift_correlated_decoder_v1_2.prepare_seeds import build_inventory, planned_labels
from outputs.qshift_correlated_decoder_v1_2.select_static import select_q

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
        v11 = set(load(V1_1_PACKAGE / "seed_inventory.json")["seeds"].values())
        self.assertFalse(v11 & set(committed["seeds"].values()))


class StaticSelectionRecordTests(unittest.TestCase):
    def test_selection_rule_and_tie_break(self) -> None:
        self.assertEqual(select_q({0.0: 5, 0.005: 3, 0.01: 3}), 0.005)

    def test_committed_selection_is_consistent_with_its_own_table(self) -> None:
        record = load(PKG / "STATIC_SELECTION.json")
        for table, key in (("matching", K.KEY_ASTAR_Q), ("five_factor", K.KEY_BSTATIC_Q)):
            totals = {row["q"]: sum(row["errors_by_condition"].values()) for row in record[table]}
            self.assertEqual(record["selected"][key], select_q(totals))
        self.assertEqual(record["sampler_calls"], 0)

    def test_matching_at_v1_1_pooled_qhat_reconciles_with_v1_1_arm_a(self) -> None:
        record = load(PKG / "STATIC_SELECTION.json")
        pooled = record["grid_extra_point_v1_1_pooled_qhat"]
        row = next(r for r in record["matching"] if r["q"] == pooled)
        self.assertEqual(sum(row["errors_by_condition"].values()), 821)  # V1.1 post-run audit, arm A


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
