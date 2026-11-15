"""Create a hash-bound review-only V2 pre-sampling freeze; never authorizes sampling."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version

from outputs.strong_fixed_baselines_v2.freeze_pretest_v2 import (
    CONFIG_PATH,
    FREEZE_PATH,
    HERE,
    INVENTORY_PATH,
    REQUIRED_HASHES,
    ROOT,
    sha256,
)


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    if config.get("execution", {}).get("sampling_authorized") is not False:
        raise RuntimeError("freeze builder requires sampling_authorized=false")
    if inventory.get("sampling_performed") is not False or inventory.get("sealed_test_access") is not False:
        raise RuntimeError("freeze builder requires a no-sampling/no-test-access inventory")
    if inventory.get("historical_collisions") or inventory.get("candidate_internal_collisions"):
        raise RuntimeError("freeze builder refuses a seed inventory with collisions")
    missing = [rel for rel in REQUIRED_HASHES if not (ROOT / rel).is_file()]
    if missing:
        raise FileNotFoundError(f"freeze inputs are missing: {sorted(missing)}")
    rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                         capture_output=True, text=True).stdout.strip()
    software_versions = {"python": sys.version.split()[0]}
    for distribution in ("stim", "pymatching", "numpy"):
        try:
            software_versions[distribution] = version(distribution)
        except PackageNotFoundError:
            software_versions[distribution] = "not-installed"
    record = {
        "schema_version": 2,
        "freeze_status": "PRETEST_FREEZE_REVIEW_ONLY",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision_before_freeze_commit": rev,
        "software_versions": software_versions,
        "sampling_performed_at_freeze": False,
        "sampling_authorized": False,
        "owner_authorization_required_before_sampling": True,
        "sealed_test_access": False,
        "primary_contrast": config["statistics"]["primary_contrast"],
        "practical_effect_benchmark": config["statistics"]["primary_practical_effect_benchmark"],
        "primary_benefit_boundary": config["statistics"]["primary_benefit_boundary"],
        "no_burst_safety_rule": {
            "selection_mean_harm_limit": config["decoders"]["static_zero_burst_mean_harm_limit"],
            "validation_upper_bound_harm_limit": config["decoders"]["validation_upper_bound_harm_limit"],
            "comparison_reference": "nominal_fixed_p0",
            "validation_action": "accept selected candidate or fallback to p=0; never reselect",
        },
        "allocation": config["allocation"],
        "historical_seed_coverage": {
            "status": inventory["historical_coverage_status"],
            "historical_coverage_complete": False,
            "limitation": inventory["coverage_limitation"],
            "historical_metadata_sources": len(inventory["historical_sources_checked"]),
            "candidate_streams": inventory["candidate_stream_count"],
            "candidate_seed_count": inventory["candidate_unique_seed_count"],
            "candidate_collisions": 0,
        },
        "sha256": {rel: sha256(ROOT / rel) for rel in sorted(REQUIRED_HASHES)},
    }
    payload = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if FREEZE_PATH.exists():
        if FREEZE_PATH.read_text(encoding="utf-8") != payload:
            raise FileExistsError("pretest freeze already exists and differs; preserve it and create a versioned revision")
        print(f"existing identical review-only freeze: {FREEZE_PATH.relative_to(ROOT)}")
    else:
        FREEZE_PATH.write_text(payload, encoding="utf-8")
        print(f"created review-only freeze: {FREEZE_PATH.relative_to(ROOT)}")
    print(json.dumps({
        "freeze_status": record["freeze_status"],
        "sampling_authorized": record["sampling_authorized"],
        "hashes": len(record["sha256"]),
        "freeze_sha256": sha256(FREEZE_PATH),
        "primary_contrast": record["primary_contrast"],
    }, indent=2))


if __name__ == "__main__":
    main()
