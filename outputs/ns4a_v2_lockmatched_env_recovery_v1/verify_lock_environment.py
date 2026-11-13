from __future__ import annotations

import hashlib
import importlib.metadata as metadata
import json
import re
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
VENV = Path(sys.prefix).resolve()
LOCK = OUT / "requirements-ns3b.lock.txt"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
EXPECTED_LOCK_SHA256 = "403d567f1063e5406fac93e9292ddb43a5524c274992b9dff29d14ddf06a3fac"
EXPECTED_UPSTREAM_COMMIT = "4458c278bbec273c8c1a26411dadccc49222f8ef"
EXPECTED_UPSTREAM_URL = "https://github.com/oscarhiggott/BeliefMatching.git"
EXPECTED_BM_VERSION = "0.2.0"
GLOBAL_BEFORE = {
    "distribution_count": 82,
    "inventory_sha256": "f4570507bc9ffdf9f57111b3ab13354c50c32df36499de50d016c70f2ce52383",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def global_inventory() -> dict:
    result = subprocess.run(
        [sys.base_prefix + "\\python.exe", "-m", "pip", "list", "--format=json"],
        check=True,
        capture_output=True,
        text=True,
    )
    packages = json.loads(result.stdout)
    encoded = json.dumps(
        sorted((item["name"].lower(), item["version"]) for item in packages),
        separators=(",", ":"),
    ).encode()
    return {"distribution_count": len(packages), "inventory_sha256": sha(encoded)}


def main() -> int:
    lock_bytes = LOCK.read_bytes()
    lock_hash = sha(lock_bytes)
    locked: dict[str, str] = {}
    lock_vcs = None
    for raw_line in lock_bytes.decode("utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-e git+"):
            lock_vcs = line
            continue
        name, version = line.split("==", 1)
        locked[canonical_name(name)] = version

    dist_versions = {
        canonical_name(dist.metadata["Name"]): dist.version
        for dist in metadata.distributions()
        if dist.metadata.get("Name")
    }
    expected_versions = dict(locked)
    expected_versions["beliefmatching"] = EXPECTED_BM_VERSION
    actual_locked = {name: dist_versions.get(name) for name in expected_versions}
    version_mismatches = {
        name: {"expected": version, "actual": actual_locked.get(name)}
        for name, version in expected_versions.items()
        if actual_locked.get(name) != version
    }
    extras = sorted(set(dist_versions) - set(expected_versions) - {"pip"})
    missing = sorted(set(expected_versions) - set(dist_versions))

    cfg_path = VENV / "pyvenv.cfg"
    cfg = dict(
        line.split(" = ", 1)
        for line in cfg_path.read_text(encoding="utf-8").splitlines()
        if " = " in line
    )
    venv_isolated = (
        cfg.get("include-system-site-packages") == "false"
        and cfg.get("version") == "3.12.10"
        and Path(sys.prefix).resolve() == VENV
        and Path(sys.prefix).resolve() != Path(sys.base_prefix).resolve()
    )

    direct_url = json.loads(
        metadata.distribution("beliefmatching").read_text("direct_url.json") or "{}"
    )
    source_checkout = VENV / "src" / "beliefmatching"
    source_commit = subprocess.run(
        ["git", "-C", str(source_checkout), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    source_origin = subprocess.run(
        ["git", "-C", str(source_checkout), "remote", "get-url", "origin"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    import beliefmatching.belief_matching as upstream_core
    from qshift_core_v1.research_adapters.beliefmatching_adapter_ns3b import (
        UPSTREAM_COMMIT,
        UPSTREAM_CORE_SOURCE_SHA256_LF,
        UPSTREAM_VERSION,
    )

    upstream_source = Path(upstream_core.__file__).read_bytes().replace(b"\r\n", b"\n")
    installed_core_hash = sha(upstream_source)
    source_identity_ok = (
        source_commit == EXPECTED_UPSTREAM_COMMIT == UPSTREAM_COMMIT
        and source_origin.rstrip("/") == EXPECTED_UPSTREAM_URL.rstrip("/")
        and installed_core_hash == UPSTREAM_CORE_SOURCE_SHA256_LF
        and UPSTREAM_VERSION == EXPECTED_BM_VERSION
    )

    pip_check = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        capture_output=True,
        text=True,
    )
    dist_locations = {}
    locations_inside_venv = True
    for dist in metadata.distributions():
        name = dist.metadata.get("Name")
        if not name:
            continue
        location = Path(dist.locate_file("")).resolve()
        try:
            location.relative_to(VENV)
            inside = True
        except ValueError:
            inside = False
        dist_locations[canonical_name(name)] = {"path": str(location), "inside_venv": inside}
        locations_inside_venv &= inside

    current_global = global_inventory()
    global_unchanged = current_global == GLOBAL_BEFORE
    lock_vcs_ok = bool(
        lock_vcs
        and EXPECTED_UPSTREAM_COMMIT in lock_vcs
        and EXPECTED_UPSTREAM_URL in lock_vcs
    )
    checks = {
        "lock_sha256": lock_hash == EXPECTED_LOCK_SHA256,
        "pinned_versions_match": not version_mismatches and not missing,
        "no_unpinned_installed_distributions": not extras,
        "python_3_12_10_isolated_venv": venv_isolated and sys.version.split()[0] == "3.12.10",
        "beliefmatching_source_identity": source_identity_ok,
        "lock_vcs_pin_matches": lock_vcs_ok,
        "all_distributions_inside_venv": locations_inside_venv,
        "pip_check": pip_check.returncode == 0,
        "global_python_package_inventory_unchanged": global_unchanged,
    }
    result = {
        "schema": "qshift-ns4a-v2-lockmatched-dependency-verification-v1",
        "checks": checks,
        "overall": "PASS" if all(checks.values()) else "FAIL",
        "python": {"version": sys.version.split()[0], "executable": sys.executable},
        "environment": {
            "venv": str(VENV),
            "base_prefix": sys.base_prefix,
            "pyvenv_cfg": cfg,
            "include_system_site_packages": cfg.get("include-system-site-packages"),
        },
        "lock": {
            "path": "requirements-ns3b.lock.txt",
            "sha256": lock_hash,
            "locked_distribution_count": len(locked) + 1,
            "vcs_requirement": lock_vcs,
        },
        "installed_locked_versions": actual_locked,
        "version_mismatches": version_mismatches,
        "missing_distributions": missing,
        "extra_distributions_excluding_venv_pip": extras,
        "distribution_locations": dist_locations,
        "beliefmatching": {
            "version": dist_versions.get("beliefmatching"),
            "requested_source": EXPECTED_UPSTREAM_URL,
            "expected_commit": EXPECTED_UPSTREAM_COMMIT,
            "installed_source_checkout": str(source_checkout),
            "installed_commit": source_commit,
            "remote_origin": source_origin,
            "installed_core_file": str(upstream_core.__file__),
            "installed_core_sha256_lf": installed_core_hash,
            "expected_core_sha256_lf": UPSTREAM_CORE_SOURCE_SHA256_LF,
            "direct_url_metadata": direct_url,
        },
        "pip_check": {"returncode": pip_check.returncode, "output": (pip_check.stdout + pip_check.stderr).strip()},
        "global_python_inventory": {"before": GLOBAL_BEFORE, "after": current_global},
        "installation_scope": {
            "pip_cache": str(VENV / "pip-cache"),
            "temporary_directory": str(VENV / "tmp"),
            "package_destinations_within_venv": locations_inside_venv,
            "global_python_changed": not global_unchanged,
        },
    }
    with (OUT / "DEPENDENCY_VERIFICATION.json").open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"overall": result["overall"], "checks": checks, "versions": actual_locked}, indent=2))
    return 0 if result["overall"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
