from __future__ import annotations

import json
import unittest

from outputs.qshift_performance_sprint_v1.recovery_support_v1_1 import (
    RECOVERY, ROOT, sha_file, verify_recovery_inputs, verify_recovery_manifest,
)


class CompletedRecoveryTests(unittest.TestCase):
    def test_original_failed_evidence_and_source_freezes_remain_intact(self):
        inputs = verify_recovery_inputs(require_no_output=False)
        manifest = verify_recovery_manifest()
        self.assertEqual(inputs["status"]["status"], "incomplete")
        self.assertEqual(inputs["inventory"]["original_attempt_status_sha256"],
                         "aae010949baa43dc1d9837ef73ce430d7bc4dac49ca5d5158ab12432285bc65e")
        self.assertEqual(len(manifest["files"]), 10)

    def test_complete_root_and_shot_counts_are_persisted(self):
        status = json.loads((RECOVERY / "status.json").read_text(encoding="utf-8"))
        self.assertEqual(status["status"], "completed")
        self.assertEqual(status["committed_roots"], 50)
        self.assertEqual(status["committed_evaluation_rows"], 100000)
        self.assertEqual(status["verified_unique_total_rows"], 130000)
        self.assertEqual(status["cumulative_sampler_calls_completed"], 106)
        self.assertEqual(status["cumulative_sampler_rows_returned"], 132000)
        self.assertEqual(len(status["unique_sample_ids"]), 50)
        self.assertEqual(len(set(status["unique_sample_ids"])), 50)

    def test_independent_audit_reconstructed_all_predictions_without_sampling(self):
        report = json.loads((ROOT / "independent_audit_v1_1.json").read_text(encoding="utf-8"))
        self.assertEqual(report["audit_status"], "PASS")
        self.assertEqual(report["sampler_calls"], 0)
        self.assertEqual(report["new_shots"], 0)
        self.assertEqual(report["reconstructed_roots"], 50)
        self.assertEqual(report["unique_evaluation_rows"], 100000)
        self.assertEqual(report["prediction_reconstructions"], 200)
        self.assertEqual(report["calibration_max_abs_difference"], 0.0)

    def test_analysis_primary_matches_independent_audit(self):
        result = json.loads((ROOT / "analysis_v1_1.json").read_text(encoding="utf-8"))
        audit = json.loads((ROOT / "independent_audit_v1_1.json").read_text(encoding="utf-8"))
        self.assertEqual(result["decision"], "NO-GO")
        self.assertEqual(result["primary"]["difference"], audit["primary_difference"])
        self.assertEqual(result["primary"]["percentile_95_ci"], audit["primary_percentile_95_ci"])
        self.assertEqual(result["zero_burst_no_harm"]["bootstrap_lower_upper_5_95"],
                         audit["zero_gate_5_95"])

    def test_all_committed_root_results_reference_verified_archives(self):
        audit = json.loads((ROOT / "independent_audit_v1_1.json").read_text(encoding="utf-8"))
        self.assertEqual(len(audit["archive_hashes"]), 50)
        for stem, expected in audit["archive_hashes"].items():
            self.assertEqual(sha_file(RECOVERY / f"{stem}.npz"), expected)
            marker = json.loads((RECOVERY / f"{stem}.commit.json").read_text(encoding="utf-8"))
            self.assertEqual(marker["archive_sha256"], expected)


if __name__ == "__main__":
    unittest.main()
