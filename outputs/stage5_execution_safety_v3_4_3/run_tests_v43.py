from __future__ import annotations
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COMMAND = [sys.executable, "-m", "unittest", "-v",
           "outputs.stage5_execution_safety_v3_4_3.test_recovery_v43"]


def main():
    proc = subprocess.run(COMMAND, cwd=ROOT, capture_output=True, text=True, timeout=180)
    combined = proc.stdout + proc.stderr
    match = re.search(r"Ran (\d+) tests?", combined)
    tests = re.findall(r"^(test_[A-Za-z0-9_]+) \(.*\) \.\.\. (ok|FAIL|ERROR|skipped.*)$", combined, re.M)
    passed = proc.returncode == 0 and match is not None and "OK" in combined
    result = {
        "status": "PASS" if passed else "FAIL",
        "command": "python -m unittest -v outputs.stage5_execution_safety_v3_4_3.test_recovery_v43",
        "working_directory": str(ROOT),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "exit_code": proc.returncode,
        "test_count": int(match.group(1)) if match else None,
        "test_records": [{"name": name, "status": status} for name, status in tests],
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "stage5_sampling_performed": False,
        "fixtures_disposable_only": True,
    }
    (HERE / "TEST_RESULTS_V43.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {"stdout", "stderr"}}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
