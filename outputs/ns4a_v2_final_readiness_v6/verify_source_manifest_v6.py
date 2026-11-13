"""Verify every V6-inherited and V6-specific source identity."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "outputs" / "ns4a_v2_integrated_runner_v1"))
from qshift_ns4a_v2_runner.benchmark_identity_v6 import verify_source_manifest_v6  # noqa: E402


def main() -> int:
    result = verify_source_manifest_v6(ROOT)
    print(json.dumps({"status": "PASS", "manifest_sha256": result["manifest_sha256"],
                      "source_tree_sha256": result["source_tree_sha256"],
                      "verified_file_count": len(result["rows"]),
                      "sampling_performed": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
