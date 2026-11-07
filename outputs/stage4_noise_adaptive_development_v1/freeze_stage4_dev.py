"""Create/verify the prospective pre-sampling source and protocol freeze."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FREEZE = HERE / "STAGE4_DEVELOPMENT_FREEZE.json"

FROZEN_PATHS = [
    ".gitignore",
    "outputs/stage4_noise_adaptive_development_v1/STAGE4_DEVELOPMENT_PROTOCOL.md",
    "outputs/stage4_noise_adaptive_development_v1/stage4_development_config.json",
    "outputs/stage4_noise_adaptive_development_v1/seed_inventory.json",
    "outputs/stage4_noise_adaptive_development_v1/seed_audit.json",
    "outputs/stage4_noise_adaptive_development_v1/additional_development_seed_audit.json",
    "outputs/stage4_noise_adaptive_development_v1/ADDITIONAL_SEED_COVERAGE.md",
    "outputs/stage4_noise_adaptive_development_v1/REPRODUCE.md",
    "outputs/stage4_noise_adaptive_development_v1/STAGE4_PREFLIGHT.md",
    "outputs/stage4_noise_adaptive_development_v1/analysis.py",
    "outputs/stage4_noise_adaptive_development_v1/prepare_seeds.py",
    "outputs/stage4_noise_adaptive_development_v1/audit_additional_development_seeds.py",
    "outputs/stage4_noise_adaptive_development_v1/run_stage4.py",
    "outputs/stage4_noise_adaptive_development_v1/audit_stage4.py",
    "outputs/stage4_noise_adaptive_development_v1/freeze_stage4_dev.py",
    "outputs/stage4_noise_adaptive_development_v1/tests/test_stage4.py",
    "outputs/stage4_noise_adaptive_feasibility_v1/prototype.py",
    "outputs/phase3a_correlated_noise_preflight/simulator.py",
    "outputs/stage4_noise_adaptive_feasibility_v1/STAGE4_FEASIBILITY_FREEZE.json",
]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def build() -> dict:
    files = {}
    for rel in FROZEN_PATHS:
        path = REPO / rel
        if not path.is_file():
            raise FileNotFoundError(f"required freeze input missing: {rel}")
        files[rel] = digest(path)
    return {
        "status": "FROZEN_BEFORE_SAMPLING",
        "study": "qshift-stage4-full-development-v1",
        "freeze_scope": "protocol, configuration, RNG inventory/audit, runner, analysis, tests, and frozen upstream simulator/estimator sources",
        "files_sha256": files,
        "sampling_started_at_freeze": False,
        "sealed_independent_test_accessed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--create", action="store_true")
    action.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.create:
        if FREEZE.exists():
            raise FileExistsError(f"freeze already exists; refusing overwrite: {FREEZE}")
        run_dir = HERE / "run_v1"
        if run_dir.exists() and any(run_dir.iterdir()):
            raise RuntimeError("sampling/run artifacts exist before freeze; refusing to freeze retrospectively")
        payload = build()
        tmp = FREEZE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        tmp.replace(FREEZE)
        print(f"created {FREEZE} with {len(payload['files_sha256'])} hashes")
    else:
        expected = json.loads(FREEZE.read_text(encoding="utf-8"))
        actual = build()
        mismatches = {k: (expected["files_sha256"].get(k), v)
                      for k, v in actual["files_sha256"].items()
                      if expected["files_sha256"].get(k) != v}
        missing = sorted(set(expected["files_sha256"]) - set(actual["files_sha256"]))
        if mismatches or missing or expected.get("status") != "FROZEN_BEFORE_SAMPLING":
            raise RuntimeError(f"freeze verification failed; mismatches={mismatches}; missing={missing}")
        print(f"verified {len(actual['files_sha256'])} frozen hashes")


if __name__ == "__main__":
    main()
