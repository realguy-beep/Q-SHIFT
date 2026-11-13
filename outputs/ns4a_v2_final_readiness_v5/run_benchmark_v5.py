"""Single supported V5 benchmark launcher; authorization remains separate."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "outputs/ns4a_v2_integrated_runner_v1"))

from qshift_ns4a_v2_runner.benchmark_identity_v5 import (  # noqa: E402
    AUTH_REL,
    INVENTORY_REL,
    PROTOCOL_REL,
    V5_MANIFEST_REL,
    _inside,
    load_approved_historical_seed_values,
)
from qshift_ns4a_v2_runner.benchmark_v5 import run_authorized_benchmark_v5  # noqa: E402


def main() -> int:
    result = run_authorized_benchmark_v5(
        repository_root=ROOT,
        protocol_path=_inside(ROOT, PROTOCOL_REL),
        seed_inventory_path=_inside(ROOT, INVENTORY_REL),
        authorization_path=_inside(ROOT, AUTH_REL),
        source_manifest_path=_inside(ROOT, V5_MANIFEST_REL),
        reserved_seed_values=load_approved_historical_seed_values(ROOT),
    )
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
