"""Superseding implementation freeze after the pre-sampling Windows path fix."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FREEZE = HERE / "STAGE4_DEVELOPMENT_FREEZE_V2.json"
PRIOR_FREEZE = HERE / "STAGE4_DEVELOPMENT_FREEZE.json"
FROZEN_PATHS = [
    ".gitignore",
    "outputs/stage4_noise_adaptive_development_v1/STAGE4_DEVELOPMENT_PROTOCOL.md",
    "outputs/stage4_noise_adaptive_development_v1/STAGE4_PREFLIGHT.md",
    "outputs/stage4_noise_adaptive_development_v1/STAGE4_PREFLIGHT_REPAIR_AMENDMENT.md",
    "outputs/stage4_noise_adaptive_development_v1/stage4_development_config.json",
    "outputs/stage4_noise_adaptive_development_v1/seed_inventory.json",
    "outputs/stage4_noise_adaptive_development_v1/seed_audit.json",
    "outputs/stage4_noise_adaptive_development_v1/additional_development_seed_audit.json",
    "outputs/stage4_noise_adaptive_development_v1/ADDITIONAL_SEED_COVERAGE.md",
    "outputs/stage4_noise_adaptive_development_v1/REPRODUCE.md",
    "outputs/stage4_noise_adaptive_development_v1/analysis.py",
    "outputs/stage4_noise_adaptive_development_v1/prepare_seeds.py",
    "outputs/stage4_noise_adaptive_development_v1/audit_additional_development_seeds.py",
    "outputs/stage4_noise_adaptive_development_v1/run_stage4.py",
    "outputs/stage4_noise_adaptive_development_v1/audit_stage4.py",
    "outputs/stage4_noise_adaptive_development_v1/tests/test_stage4.py",
    "outputs/stage4_noise_adaptive_development_v1/freeze_stage4_dev.py",
    "outputs/stage4_noise_adaptive_development_v1/freeze_stage4_dev_v2.py",
    "outputs/stage4_noise_adaptive_development_v1/STAGE4_DEVELOPMENT_FREEZE.json",
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
    prior = json.loads(PRIOR_FREEZE.read_text(encoding="utf-8"))
    files = {}
    for rel in FROZEN_PATHS:
        path = REPO / rel
        if not path.is_file():
            raise FileNotFoundError(f"required v2 freeze input missing: {rel}")
        files[rel] = digest(path)
    prior_hashes = prior.get("files_sha256", {})
    changed_prior_paths = sorted(rel for rel, old_hash in prior_hashes.items()
                                 if files.get(rel) != old_hash)
    expected_repair_paths = sorted([
        "outputs/stage4_noise_adaptive_development_v1/REPRODUCE.md",
        "outputs/stage4_noise_adaptive_development_v1/audit_stage4.py",
        "outputs/stage4_noise_adaptive_development_v1/run_stage4.py",
    ])
    if changed_prior_paths != expected_repair_paths:
        raise RuntimeError(f"unexpected files changed since initial freeze: {changed_prior_paths}")
    return {
        "status": "FROZEN_BEFORE_SAMPLING_V2",
        "study": "qshift-stage4-full-development-v1",
        "supersedes": "STAGE4_DEVELOPMENT_FREEZE.json",
        "prior_freeze_sha256": digest(PRIOR_FREEZE),
        "prior_freeze_changed_files": changed_prior_paths,
        "amendment_scope": "Windows Path conversion at pre-sampling disk-space check only; scientific protocol unchanged",
        "files_sha256": files,
        "sampling_started_at_freeze": False,
        "independent_test_accessed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--create", action="store_true")
    group.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.create:
        if FREEZE.exists():
            raise FileExistsError(f"v2 freeze already exists; refusing overwrite: {FREEZE}")
        run_dir = HERE / "run_v1"
        # Keep the failed preflight log and empty directories. Refuse only if any
        # sample-bearing archive exists before this repair freeze.
        prior_samples = list((run_dir / "profiles").glob("*.npz")) + list((run_dir / "roots").glob("*.npz"))
        if prior_samples:
            raise RuntimeError("sample archives exist before the repair freeze; refusing prospective claim")
        payload = build()
        tmp = FREEZE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        tmp.replace(FREEZE)
        print(f"created superseding freeze {FREEZE} with {len(payload['files_sha256'])} hashes")
        return
    expected = json.loads(FREEZE.read_text(encoding="utf-8"))
    actual = build()
    mismatches = {k: (expected["files_sha256"].get(k), v)
                  for k, v in actual["files_sha256"].items()
                  if expected["files_sha256"].get(k) != v}
    missing = sorted(set(expected["files_sha256"]) - set(actual["files_sha256"]))
    if mismatches or missing or expected.get("status") != "FROZEN_BEFORE_SAMPLING_V2":
        raise RuntimeError(f"v2 freeze verification failed; mismatches={mismatches}; missing={missing}")
    print(f"verified {len(actual['files_sha256'])} superseding frozen hashes")


if __name__ == "__main__":
    main()
