"""Explicit V6 bounded benchmark recovery launcher; requires new owner auth."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "outputs" / "ns4a_v2_integrated_runner_v1"))

from qshift_ns4a_v2_runner.benchmark_identity_v6 import (  # noqa: E402
    V6_AUTH_REL,
    V6_INVENTORY_REL,
    V6_MANIFEST_REL,
    V6_PROTOCOL_REL,
    _relpath,
    load_approved_historical_seed_values,
)
from qshift_ns4a_v2_runner.benchmark_v6 import run_authorized_benchmark_v6  # noqa: E402


def main() -> int:
    result = run_authorized_benchmark_v6(
        repository_root=ROOT,
        protocol_path=_relpath(ROOT, V6_PROTOCOL_REL),
        seed_inventory_path=_relpath(ROOT, V6_INVENTORY_REL),
        authorization_path=_relpath(ROOT, V6_AUTH_REL),
        source_manifest_path=_relpath(ROOT, V6_MANIFEST_REL),
        reserved_seed_values=load_approved_historical_seed_values(ROOT),
    )
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
