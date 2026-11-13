from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "outputs" / "ns4a_v2_integrated_runner_v1"))

from qshift_ns4a_v2_runner.benchmark_v6 import _validate_protocol, validate_fixture_limits  # noqa: E402


class V6ProtocolLimitTests(unittest.TestCase):
    def test_frozen_workload_and_all_hard_limits_remain_exact(self):
        protocol_path = ROOT / "outputs/ns4a_v2_final_readiness_v1/BENCHMARK_PROTOCOL.json"
        protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
        _validate_protocol(protocol)
        self.assertEqual(protocol["maximum_total_shots"], 6_000)
        self.assertEqual(protocol["shots_per_condition"], 1_000)
        self.assertEqual(protocol["hard_limits"], {
            "sampler_calls": 6,
            "maximum_sampler_shots_per_call": 1_000,
            "candidate_decoders": 12,
            "evaluation_arms": 5,
            "sampler_returns_observables": False,
            "maximum_wall_clock_seconds": 600,
            "maximum_peak_working_set_bytes": 1_073_741_824,
            "minimum_free_disk_bytes": 1_073_741_824,
            "maximum_output_bytes": 134_217_728,
        })

    def test_fixture_limit_validation_is_sampler_free(self):
        protocol_path = ROOT / "outputs/ns4a_v2_final_readiness_v1/BENCHMARK_PROTOCOL.json"
        protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
        self.assertEqual(validate_fixture_limits(protocol), {
            "maximum_total_shots": 6_000,
            "maximum_wall_clock_seconds": 600,
            "maximum_output_bytes": 134_217_728,
        })


if __name__ == "__main__":
    unittest.main()
