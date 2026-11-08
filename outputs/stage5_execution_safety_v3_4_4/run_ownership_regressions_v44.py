"""Run the v3.4.2 Windows ownership regressions applicable to an existing run."""
from __future__ import annotations
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V42 = ROOT / "outputs/stage5_execution_safety_v3_4_2"
sys.path.insert(0, str(V42))
spec = importlib.util.spec_from_file_location("stage5_v42_process_tests", V42 / "test_safety_v4.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
suite = unittest.defaultTestLoader.loadTestsFromModule(module)
all_tests = []
def collect(node):
    for item in node:
        if isinstance(item, unittest.TestSuite): collect(item)
        else: all_tests.append(item)
collect(suite)
excluded = "test_frozen_hashes_and_stage5_boundary"
selected = [test for test in all_tests if test._testMethodName != excluded]
result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(selected))
payload = {
    "status": "PASS" if result.wasSuccessful() else "FAIL",
    "selected_tests": len(selected),
    "excluded_test": excluded,
    "exclusion_reason": "The legacy test asserts that the original run directory does not exist; this documented failed run must be preserved and exists.",
    "failures": [f"{test.id()}: {err.splitlines()[-1]}" for test, err in result.failures],
    "errors": [f"{test.id()}: {err.splitlines()[-1]}" for test, err in result.errors],
    "stage5_sampling_authorized": False,
    "stage5_sampling_started": False,
}
print(json.dumps(payload, sort_keys=True))
raise SystemExit(0 if result.wasSuccessful() else 1)
