"""Verify the V5 source tree without sampling or opening any outcome archive."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "outputs/ns4a_v2_integrated_runner_v1"))
from qshift_ns4a_v2_runner.benchmark_identity_v5 import (  # noqa: E402
    V5_MANIFEST_REL,
    _inside,
    verify_source_manifest_v5,
)


def main() -> int:
    manifest = _inside(ROOT, V5_MANIFEST_REL)
    record = verify_source_manifest_v5(ROOT, manifest)
    print(json.dumps({
        "status": "PASS",
        "manifest_sha256": record["manifest_sha256"],
        "source_tree_sha256": record["source_tree_sha256"],
        "verified_file_count": record["verified_file_count"],
        "sampling_performed": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
