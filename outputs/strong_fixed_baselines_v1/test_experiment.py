"""Deterministic no-shot unit and structural tests for development v1."""
from __future__ import annotations

import json
import copy
import sys
import unittest
from pathlib import Path

import numpy as np
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import experiment_core as core  # noqa: E402
from experiment_core import (  # noqa: E402
    build_models, make_circuit, root_errors, safety_validation_accept,
    select_safety_constrained_static, validate_binary, decode_candidate_grid,
    dem_kwargs,
)
from run_development import (checkpoint, load_checkpoint, validate_seed_allocation,
                             nonzero_condition_probabilities, write_immutable_json)  # noqa: E402
from prepare_resume_copy import audit_key  # noqa: E402


class StrongBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((HERE / "experiment_config.json").read_text(encoding="utf-8"))

    def test_inventory_is_unique_and_allocation_matches_config(self):
        inventory = json.loads((HERE / "seed_inventory.json").read_text(encoding="utf-8"))
        seeds = [int(s["seed"]) for s in inventory["streams"]]
        self.assertEqual(len(seeds), len(set(seeds)))
        self.assertEqual(inventory["collisions"], [])
        self.assertEqual(inventory["historical_values_screened"], 11464)
        self.assertEqual(inventory["sampling_stream_count"], 1603)
        self.assertEqual(inventory["expected_unique_shots"], 3_660_000)
        self.assertEqual(inventory["benchmark_stream_count"], 20)
        self.assertEqual(inventory["analysis_stream_count"], 2)
        self.assertEqual(inventory["stream_count_including_analysis_rng"], 1625)
        self.assertEqual(sum(int(s["shots"]) for s in inventory["streams"] if s["included_in_allocation"]), 3_660_000)
        self.assertTrue(all(not s["included_in_allocation"] for s in inventory["streams"] if s["stream"] == "pcg64"))
        self.assertFalse(inventory["sampling_performed"])
        validate_seed_allocation(self.cfg, inventory)

    def test_circuit_and_dem_dimensions(self):
        for p in self.cfg["circuit"]["probabilities"]:
            circuit = make_circuit(float(p), self.cfg)
            dem = circuit.detector_error_model(**dem_kwargs(self.cfg))
            self.assertEqual((circuit.num_detectors, circuit.num_observables), (40, 1))
            self.assertEqual((dem.num_detectors, dem.num_observables), (40, 1))

    def test_noiseless_circuit_has_no_dem_fault_instructions(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["circuit"]["gate_p"] = 0.0
        cfg["circuit"]["measurement_p"] = 0.0
        circuit = make_circuit(0.0, cfg)
        dem = circuit.detector_error_model(**dem_kwargs(cfg))
        errors = [instruction for instruction in dem if instruction.type == "error"]
        self.assertEqual(errors, [])

    def test_matching_build_and_synthetic_batch_shapes(self):
        models = build_models([0.0, 0.008])
        detectors = np.zeros((4, 40), dtype=np.uint8)
        predictions = [np.asarray(model.decode_batch(detectors)).reshape(-1) for model in models.values()]
        self.assertEqual([p.shape for p in predictions], [(4,), (4,)])
        self.assertTrue(all(np.isin(p, (0, 1)).all() for p in predictions))

    def test_full_nine_candidate_grid_order_and_shapes(self):
        grid = list(map(float, self.cfg["decoders"]["static_candidate_grid"]))
        models = build_models(grid)
        d = np.zeros((11, 40), dtype=np.uint8)
        probabilities, predictions = decode_candidate_grid(d, models)
        self.assertEqual(probabilities, grid)
        self.assertEqual(predictions.shape, (9, 11))

    def test_positive_condition_iterator_is_complete_and_ordered(self):
        values = self.cfg["circuit"]["probabilities"]
        self.assertEqual(nonzero_condition_probabilities(values), [0.004, 0.008, 0.012, 0.016])

    def test_recovery_audit_key_uses_saved_native_windows_path(self):
        audit = json.loads((HERE / "partial_failure_audit" / "FAILED_RUN_PARTIAL_AUDIT.json").read_text(encoding="utf-8"))
        archive = HERE / "run" / "templates" / "p_0.000.npz"
        key = audit_key(archive)
        self.assertIn(key, audit["file_sha256"])
        self.assertEqual(key, "run\\templates\\p_0.000.npz")
        self.assertIn("status.json", audit["file_sha256"])
        self.assertNotIn("run\\status.json", audit["file_sha256"])

    def test_atomic_json_retries_transient_windows_replace_denial(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "status.json"
            path.write_text('{"old":true}\n', encoding="utf-8")
            original_replace = core.os.replace
            calls = {"n": 0}

            def transient(src, dst):
                calls["n"] += 1
                if calls["n"] < 3:
                    raise PermissionError(5, "simulated Windows sharing/access denial")
                return original_replace(src, dst)

            with patch.object(core.os, "replace", side_effect=transient), patch.object(core.time, "sleep") as sleep:
                core.atomic_json(path, {"new": True})
            self.assertEqual(calls["n"], 3)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"new": True})
            self.assertEqual(sleep.call_count, 2)
            self.assertEqual(list(Path(folder).glob("*.tmp")), [])

    def test_atomic_json_persistent_replace_denial_fails_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "status.json"
            original = '{"old":true}\n'
            path.write_text(original, encoding="utf-8")
            with patch.object(core.os, "replace", side_effect=PermissionError(5, "persistent denial")), patch.object(core.time, "sleep"):
                with self.assertRaises(PermissionError):
                    core.atomic_json(path, {"new": True})
            self.assertEqual(path.read_text(encoding="utf-8"), original)
            self.assertEqual(list(Path(folder).glob("*.tmp")), [])

    def test_immutable_json_resume_normalizes_json_object_keys(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "scores.json"
            record = {"totals": {0.0: {"errors": 2, "shots": 5}, 0.002: {"errors": 1, "shots": 5}}}
            write_immutable_json(path, record)
            write_immutable_json(path, record)
            with self.assertRaises(RuntimeError):
                write_immutable_json(path, {"totals": {0.0: {"errors": 3, "shots": 5}}})

    def test_binary_and_residual_xor_conventions(self):
        p = np.array([0, 1, 1, 0], dtype=np.uint8)
        o = np.array([0, 0, 1, 1], dtype=np.uint8)
        scored = root_errors(p, o)
        self.assertEqual(scored["errors"], 2)
        self.assertEqual(scored["shots"], 4)
        self.assertEqual(scored["ler"], 0.5)
        with self.assertRaises(ValueError):
            validate_binary("bad", np.array([0, 2]))

    def test_safe_static_uses_paired_roots_and_lower_p_tie_break(self):
        zero = {
            0.0: np.array([0.01, 0.02, 0.01]),
            0.002: np.array([0.01, 0.02, 0.01]),
            0.004: np.array([0.01, 0.02, 0.01]),
        }
        nonzero = {0.004: {
            0.0: np.array([0.020, 0.020, 0.020]),
            0.002: np.array([0.010, 0.020, 0.020]),
            0.004: np.array([0.010, 0.020, 0.020]),
        }}
        chosen, diagnostics = select_safety_constrained_static([0.0, 0.002, 0.004], zero, nonzero, 0.0002)
        self.assertEqual(chosen, 0.002)
        self.assertLessEqual(diagnostics[chosen]["p0_harm"], 0.0002)

    def test_selection_rejects_candidates_that_harm_zero_burst(self):
        zero = {0.0: np.zeros(3), 0.01: np.array([0.01, 0.0, 0.0])}
        nonzero = {0.004: {0.0: np.ones(3) * 0.02, 0.01: np.ones(3) * 0.01}}
        chosen, _ = select_safety_constrained_static([0.0, 0.01], zero, nonzero, 0.0002)
        self.assertEqual(chosen, 0.0)

    def test_validation_only_accepts_selected_candidate_or_fallback(self):
        accepted, ok = safety_validation_accept(0.008, 0.0001, 0.0002)
        self.assertEqual(accepted, 0.008)
        self.assertTrue(ok)
        fallback, ok = safety_validation_accept(0.008, 0.0003, 0.0002)
        self.assertEqual(fallback, 0.0)
        self.assertFalse(ok)

    def test_decoder_arms_share_same_sample_identity(self):
        # This is the contract used by the run format: a single stored detector matrix
        # is passed to every arm, and every arm must return one prediction per row.
        detectors = np.zeros((7, 40), dtype=np.uint8)
        observable = np.array([0, 1, 0, 0, 1, 0, 1], dtype=np.uint8)
        models = build_models([0.0, 0.008])
        arm_predictions = [np.asarray(m.decode_batch(detectors)).reshape(-1) for m in models.values()]
        self.assertTrue(all(len(x) == len(observable) for x in arm_predictions))
        self.assertTrue(np.array_equal(detectors, detectors.copy()))

    def test_checkpoint_commit_and_ambiguous_orphan_fail_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            run_dir = Path(folder)
            seed = {"seed": 123456789, "shots": None}
            detectors = np.zeros((3, 40), dtype=np.uint8)
            path = checkpoint(run_dir, "fixture", 0.0, 0, seed, {"detectors": detectors})
            stored, _ = load_checkpoint(path, partition="fixture", p=0.0, root=0, seed=123456789)
            self.assertTrue(np.array_equal(stored["detectors"], detectors))
            marker = path.with_suffix(path.suffix + ".commit.json")
            marker.unlink()
            with self.assertRaises(RuntimeError):
                checkpoint(run_dir, "fixture", 0.0, 0, seed, {"detectors": detectors})


if __name__ == "__main__":
    unittest.main(verbosity=2)
