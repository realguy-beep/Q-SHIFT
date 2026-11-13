"""Python-only fault fixture for supervisor tests; never samples or decodes."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", required=True, choices=("sampling", "analysis", "archive", "finalization"))
    parser.add_argument("--mode", required=True, choices=("fail", "block", "pass"))
    parser.add_argument("--marker", type=Path)
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--duration", type=float, default=0.0)
    args = parser.parse_args()
    if args.marker is not None:
        args.marker.write_text(json.dumps({"entered_phase": args.phase}) + "\n", encoding="utf-8")
    partial = None
    if args.phase in {"archive", "finalization"} and args.artifact is not None:
        args.artifact.parent.mkdir(parents=True, exist_ok=True)
        partial = args.artifact.with_name(args.artifact.name + ".partial")
        with partial.open("wb") as stream:
            stream.write(b"synthetic-partial-prefix")
            stream.flush()
            os.fsync(stream.fileno())
    if args.mode == "fail":
        raise RuntimeError(f"synthetic {args.phase} failure")
    if args.mode == "block":
        time.sleep(args.duration)
    if partial is not None:
        os.replace(partial, args.artifact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
