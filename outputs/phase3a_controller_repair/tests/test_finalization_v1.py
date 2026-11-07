import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from finalization_v1 import FinalizationError, finalize_run  # noqa: E402


class FinalizationV1Tests(unittest.TestCase):
    def make_run(self, root: Path):
        (root / "PROGRESS.json").write_text(json.dumps({"status": "sampling", "run_id": "fixture"}))
        (root / "results.json").write_text('{"errors": 3}\n')

    def good_verifier(self, root: Path):
        state = json.loads((root / "PROGRESS.json").read_text())
        if state["status"] not in {"finalizing", "completed"}:
            return False
        data = json.loads((root / "results.json").read_text())
        return {"passed": data["errors"] == 3}

    def test_finalizes_then_idempotently_rechecks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.make_run(root)
            seen = []
            def verifier(run):
                seen.append(json.loads((run / "PROGRESS.json").read_text())["status"])
                return self.good_verifier(run)
            first = finalize_run(root, ["results.json"], verifier)
            self.assertEqual(first["status"], "completed")
            self.assertEqual(seen, ["finalizing"])
            state = json.loads((root / "PROGRESS.json").read_text())
            self.assertEqual(state["status"], "completed")
            manifest = json.loads((root / "EVIDENCE_MANIFEST.json").read_text())
            expected = hashlib.sha256((root / "results.json").read_bytes()).hexdigest()
            self.assertEqual(manifest["files"][0]["sha256"], expected)
            second = finalize_run(root, ["results.json"], verifier)
            self.assertTrue(second["idempotent"])

    def test_interrupted_finalizing_state_resumes_from_frozen_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.make_run(root)
            def interrupt(_):
                raise KeyboardInterrupt("simulated power loss")
            with self.assertRaises(KeyboardInterrupt):
                finalize_run(root, ["results.json"], interrupt)
            state = json.loads((root / "PROGRESS.json").read_text())
            self.assertEqual(state["status"], "finalizing")
            recovered = finalize_run(root, ["results.json"], self.good_verifier)
            self.assertEqual(recovered["status"], "completed")

    def test_changed_evidence_is_rejected_and_run_marked_failed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.make_run(root)
            def corrupt_during_verify(run):
                (run / "results.json").write_text('{"errors": 4}\n')
                return {"passed": True}
            with self.assertRaisesRegex(FinalizationError, "changed since finalization"):
                finalize_run(root, ["results.json"], corrupt_during_verify)
            state = json.loads((root / "PROGRESS.json").read_text())
            self.assertEqual(state["status"], "failed")

    def test_interrupted_finalizing_state_with_corruption_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.make_run(root)
            def interrupt(_):
                raise KeyboardInterrupt("simulated interruption")
            with self.assertRaises(KeyboardInterrupt):
                finalize_run(root, ["results.json"], interrupt)
            (root / "results.json").write_text('{"errors": 17}\n')
            with self.assertRaisesRegex(FinalizationError, "changed since finalization"):
                finalize_run(root, ["results.json"], self.good_verifier)
            state = json.loads((root / "PROGRESS.json").read_text())
            self.assertEqual(state["status"], "failed")

    def test_completed_manifest_detects_later_corruption(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.make_run(root)
            finalize_run(root, ["results.json"], self.good_verifier)
            (root / "results.json").write_text('{"errors": 99}\n')
            with self.assertRaisesRegex(FinalizationError, "Evidence changed"):
                finalize_run(root, ["results.json"], self.good_verifier)

    def test_missing_file_and_path_escape_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.make_run(root)
            with self.assertRaisesRegex(FinalizationError, "missing"):
                finalize_run(root, ["missing.bin"], self.good_verifier)
            with self.assertRaisesRegex(FinalizationError, "escapes"):
                finalize_run(root, ["../outside.bin"], self.good_verifier)


if __name__ == "__main__":
    unittest.main()
