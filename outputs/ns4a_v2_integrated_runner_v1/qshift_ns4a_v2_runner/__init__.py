"""Fail-closed NS-4A V2 orchestration around the accepted deterministic modules."""

import sys
from pathlib import Path

_package_dir = Path(__file__).resolve().parent
_repo_root = _package_dir.parents[2]
_deterministic = _repo_root / "outputs" / "ns4a_v2_deterministic_implementation_v1"
for _path in (str(_repo_root), str(_deterministic)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

__version__ = "1.0.0"
