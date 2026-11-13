"""Build the explicit, small NS-2B supervisor review ZIP."""
from __future__ import annotations

import argparse
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 32 * 1024 * 1024
FILES = (
    "qshift_core_v1/__init__.py",
    "qshift_core_v1/contracts.py",
    "qshift_core_v1/circuit_identity.py",
    "qshift_core_v1/sampling_model_identity.py",
    "dashboard/tests/test_sampling_model_identity_v2.py",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_SAMPLING_MODEL_IDENTITY_DESIGN.md",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_MODEL_INFORMATION_PARITY_POLICY.md",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_MIGRATION_COMPATIBILITY_REPORT.md",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_LIMITATIONS_AND_UNRESOLVED.md",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_IMPLEMENTATION_REPORT.md",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_FAILURE_INVESTIGATION.md",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_CHANGED_FILE_INVENTORY.md",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_REVIEW_PACKAGE_CONTENTS.md",
    "outputs/core_system_upgrade_ns2b_v1/REPRODUCE_NS2B.md",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_VALIDATION_RESULTS.json",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_TEST_RESULTS.txt",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_FOCUSED_REGRESSION_RESULTS.txt",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_DASHBOARD_COMPATIBILITY_RESULTS.txt",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_BASE_COMPARISON_TEST_RESULTS.txt",
    "outputs/core_system_upgrade_ns2b_v1/NS2B_ENGINEERING_MANIFEST.json",
    "outputs/core_system_upgrade_ns2b_v1/create_manifest.py",
    "outputs/core_system_upgrade_ns2b_v1/verify_manifest.py",
    "outputs/core_system_upgrade_ns2b_v1/create_review_package.py",
)


def create_package(destination: Path) -> tuple[int, int]:
    destination = destination.expanduser().resolve()
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing review package: {destination}")
    records = []
    total_uncompressed = 0
    for rel in FILES:
        source = (ROOT / rel).resolve()
        if not source.is_file() or ROOT.resolve() not in source.parents:
            raise FileNotFoundError(f"Missing or out-of-root package input: {rel}")
        total_uncompressed += source.stat().st_size
        if total_uncompressed >= MAX_BYTES:
            raise ValueError("Uncompressed review inputs exceed the 32 MiB package ceiling.")
        records.append((source, f"Q-SHIFT/{rel.replace(chr(92), '/') }"))

    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, arcname in records:
            archive.write(source, arcname)

    with zipfile.ZipFile(destination, "r") as archive:
        bad_member = archive.testzip()
        names = set(archive.namelist())
        expected = {arcname for _, arcname in records}
        if bad_member is not None or names != expected:
            raise RuntimeError(f"Review ZIP verification failed; bad={bad_member!r}, names_match={names == expected}.")
    final_size = destination.stat().st_size
    if final_size >= MAX_BYTES:
        raise ValueError(f"Compressed review package is {final_size} bytes; limit is strictly below 32 MiB.")
    return len(records), final_size


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    count, size = create_package(args.output)
    print(f"Created verified review package: {args.output.resolve()}")
    print(f"Included files: {count}")
    print(f"ZIP bytes: {size} (< {MAX_BYTES})")


if __name__ == "__main__":
    main()
