"""Convenient script entry point for the integrated NS-4A V2 runner."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "outputs" / "ns4a_v2_integrated_runner_v1"))
from qshift_ns4a_v2_runner.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
