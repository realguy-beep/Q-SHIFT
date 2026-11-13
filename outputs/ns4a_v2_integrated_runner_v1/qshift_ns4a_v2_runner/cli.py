"""Command-line entry point; default mode never constructs a Stim sampler."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .dry_rehearsal import run_full_deterministic_rehearsal
from .integrity import IntegrityError
from .runner import execute_authorized


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NS-4A V2 integrated runner")
    parser.add_argument("--mode", choices=("dry-run", "execute"), default="dry-run")
    parser.add_argument("--repository-root", default=None)
    parser.add_argument("--execution-manifest", default=None)
    parser.add_argument("--owner-authorization", default=None)
    parser.add_argument("--report", default=None, help="Optional JSON summary path; no archive data are written there.")
    args = parser.parse_args(argv)
    try:
        if args.mode == "dry-run":
            result = run_full_deterministic_rehearsal()
        else:
            if not args.repository_root or not args.execution_manifest or not args.owner_authorization:
                parser.error("execute mode requires repository root, final immutable execution manifest, and owner authorization.")
            result = execute_authorized(
                args.execution_manifest,
                args.owner_authorization,
                repository_root=args.repository_root,
            )
        text = json.dumps(result, sort_keys=True, indent=2, allow_nan=False)
        if args.report:
            path = Path(args.report)
            if path.exists():
                raise FileExistsError("report path already exists; refusing overwrite.")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    except (IntegrityError, RuntimeError, ValueError, OSError) as exc:
        print(f"BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
