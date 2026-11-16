from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from outputs.qshift_correlated_decoder_v1_6b import contract as K
from outputs.qshift_correlated_decoder_v1_6b import run_eval
from outputs.qshift_correlated_decoder_v1_6b.analyze_saved import analyze, decide, target
from outputs.qshift_correlated_decoder_v1_6b.common import (
    COMMITMENT_PATH, canonical, load_json, open_hidden_support, sha256_bytes, sha256_file)
from outputs.qshift_correlated_decoder_v1_6b.prepare_seeds import SCREENED, build_inventory, planned_labels
from outputs.qshift_correlated_decoder_v1_6b.recount_from_scratch import main as recount
from outputs.qshift_correlated_decoder_v1_6b.rehearsal import REHEARSAL_ALLOCATION, rehearse

PKG = Path(__file__).resolve().parents[1]
REPO = PKG.parents[1]


class RehearsalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.work = Path(cls.temp.name)
        cls.result = rehearse(cls.work)
        cls.run_dir = cls.work / "rehearsal_run"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_completes_with_every_file_and_key(self) -> None:
        status = load_json(self.run_dir / K.FILE_STATUS)
        self.assertEqual(status["state"], K.STATE_COMPLETED)
        self.assertEqual(len(status["sampler_calls_started"]), REHEARSAL_ALLOCATION.sampler_calls)
        for name in (K.FILE_IDENTITY, K.FILE_ANALYSIS, K.FILE_PAIRED_CSV, K.FILE_MANIFEST):
            self.assertTrue((self.run_dir / name).is_file(), name)
        for c in K.CONDITIONS:
            models = load_json(self.run_dir / c / K.FILE_MODELS)
            for key in K.MODEL_REQUIRED_KEYS:
                self.assertIn(key, models)

    def test_learner_recovers_class_and_flip_in_both_conditions(self) -> None:
        for c in K.CONDITIONS:
            learned = self.result["conditions"][c]["learned"]
            self.assertTrue(learned["class_correct"], c)
            self.assertTrue(learned["flip_correct"], c)
        # The decoy hidden burst shares the known burst's signature but flips the logical.
        self.assertEqual(self.result["conditions"]["hidden"]["learned"]["flip"], 1)

    def test_blearn_equals_bexact_oracle_when_learning_is_correct(self) -> None:
        for c in K.CONDITIONS:
            for qi, r in ((1, 0), (2, 7)):
                with np.load(self.run_dir / c / K.DIR_EVALUATION / K.eval_archive_name(qi, r)) as z:
                    np.testing.assert_array_equal(z[K.pred_member("Blearn")], z[K.pred_member("Bexact_oracle")])

    def test_device_and_calibration_partitions_respect_label_rules(self) -> None:
        for c in K.CONDITIONS:
            with np.load(self.run_dir / c / "device" / "device_det_q1.npz") as z:
                self.assertEqual(z.files, ["detectors"])
            with np.load(self.run_dir / c / K.DIR_CALIBRATION / K.calibration_archive_name(0, 0)) as z:
                self.assertEqual(z.files, ["detectors"])

    def test_reanalysis_is_identical_and_non_mutating(self) -> None:
        before = {p.relative_to(self.run_dir): p.read_bytes() for p in self.run_dir.rglob("*") if p.is_file()}
        again = analyze(self.run_dir, self.work / "reanalysis", allocation=REHEARSAL_ALLOCATION)
        self.assertEqual(again, self.result)
        self.assertEqual({p.relative_to(self.run_dir): p.read_bytes() for p in self.run_dir.rglob("*") if p.is_file()}, before)

    def test_frozen_recount_matches(self) -> None:
        self.assertEqual(recount([str(self.run_dir)]), 0)

    def test_tampered_archive_is_rejected_before_output(self) -> None:
        copy = self.work / "tampered"
        shutil.copytree(self.run_dir, copy)
        (copy / K.FILE_ANALYSIS).unlink()
        target_file = copy / "known" / K.DIR_EVALUATION / K.eval_archive_name(1, 3)
        target_file.write_bytes(target_file.read_bytes() + b"x")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            analyze(copy, allocation=REHEARSAL_ALLOCATION)
        self.assertFalse((copy / K.FILE_ANALYSIS).exists())


class HiddenBurstTests(unittest.TestCase):
    def test_commitment_is_the_committed_v1_6_seal(self) -> None:
        self.assertEqual(load_json(COMMITMENT_PATH)["sha256_of_canonical_plaintext"],
                         "caa9fd07b823b8844408fb8ea9f210d149e4c23ad2c6e6761db1dbf6b85fd0e5")

    def test_open_verifies_hash_and_rejects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            plain = {"support": [1, 12], "salt": "ab" * 32, "schema": "qshift-v1.6-hidden-burst-plaintext-v1"}
            sealed = Path(temp) / "sealed.json"
            sealed.write_text(json.dumps(plain), encoding="utf-8")
            commit = Path(temp) / "commit.json"
            commit.write_text(json.dumps({"sha256_of_canonical_plaintext": sha256_bytes(canonical(plain))}), encoding="utf-8")
            self.assertEqual(open_hidden_support(sealed, commit), (1, 12))
            sealed.write_text(json.dumps({**plain, "support": [3, 12]}), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "does not match"):
                open_hidden_support(sealed, commit)


class RuleTests(unittest.TestCase):
    base = dict(known_co_primary_upper=[-0.004, -0.001], known_gap_upper=0.0001, known_static_errors=500,
                known_q0_bounds=[-0.002, -0.001], hidden_gap_upper=0.0001, hidden_not_worse_upper=-0.0001,
                known_vs_oracle_lower=-0.006)

    def test_go_requires_every_condition(self) -> None:
        self.assertEqual(decide(**self.base), "GO_DEVELOPMENT_ONLY")
        for change in ({"known_co_primary_upper": [-0.004, 0.0001]}, {"known_gap_upper": 0.0005},
                       {"known_static_errors": 99}, {"known_q0_bounds": [-0.002, 0.0005]},
                       {"hidden_gap_upper": 0.0006}, {"hidden_not_worse_upper": 0.0001}):
            self.assertNotEqual(decide(**{**self.base, **change}), "GO_DEVELOPMENT_ONLY", change)

    def test_no_go(self) -> None:
        self.assertEqual(decide(**{**self.base, "known_vs_oracle_lower": 0.0,
                                   "known_co_primary_upper": [0.002, -0.001]}), "NO_GO")

    def test_target(self) -> None:
        self.assertEqual(target([0.40, 0.6]), "TARGET_MET")
        self.assertEqual(target([0.399, 0.6]), "TARGET_NOT_MET")
        self.assertEqual(target([float("-inf"), float("inf")]), "TARGET_NOT_MET")


class SeedAndGateTests(unittest.TestCase):
    def test_seeds_reproducible_complete_and_disjoint(self) -> None:
        committed = load_json(PKG / "seed_inventory.json")
        self.assertEqual(committed, build_inventory())
        self.assertEqual(set(committed["seeds"]), set(planned_labels()))
        mine = set(committed["seeds"].values())
        for rel in SCREENED:
            self.assertFalse(set(load_json(REPO / rel)["seeds"].values()) & mine, rel)

    def test_imported_learner_is_the_pre_registered_version(self) -> None:
        # learner.py must be unchanged since the V1.6 pre-registration commit 304767972.
        import subprocess
        committed = subprocess.check_output(["git", "show", "304767972:outputs/qshift_correlated_decoder_v1_6/learner.py"],
                                            cwd=REPO)
        self.assertEqual(sha256_file(REPO / "outputs/qshift_correlated_decoder_v1_6/learner.py"),
                         sha256_bytes(committed.replace(b"\r\n", b"\n")))

    def test_default_is_dry_run_and_execute_is_guarded(self) -> None:
        with mock.patch.object(sys, "argv", ["run_eval.py"]), \
             mock.patch.object(run_eval, "dry_run") as dry, mock.patch.object(run_eval, "execute") as ex:
            run_eval.main()
        dry.assert_called_once()
        ex.assert_not_called()
        with mock.patch.dict(os.environ, {run_eval.WATCHDOG_ENV: ""}):
            with self.assertRaisesRegex(RuntimeError, "watchdog"):
                run_eval.execute("0" * 40, Path("."))


if __name__ == "__main__":
    unittest.main()
