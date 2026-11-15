"""Verify preserved V1 training/calibration archives without loading arrays."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

V1_COMPLETED_COMMIT = "0da212941ce4cce43cc4d27821e3a59c0acb6cd2"
V1_RUN_SOURCE_COMMIT = "bfd971d06d0deadaac965086c3a6cbdca58eeb4b"
V1_FREEZE_SHA256 = "5f5111de8bc8fad30e4f2a904c7bb6fad1d43e767deac0d160f4d95d4e50d711"
EXPECTED_SHOTS = {"training": 3000, "calibration": 15000, "evaluation": 0}


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_head(repo: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


def verify(v1_repo: Path) -> dict:
    v1_out = v1_repo / "outputs/qshift_correlated_decoder_feasibility_v1"
    run = v1_out / "pilot_runs/attempt_001"
    status_raw = (run / "status.json").read_bytes()
    identity_raw = (run / "execution_identity.json").read_bytes()
    evidence_raw = (v1_out / "FAILED_ATTEMPT_EVIDENCE_MANIFEST.json").read_bytes()
    inventory_raw = (v1_out / "seed_inventory.json").read_bytes()
    status, identity = json.loads(status_raw), json.loads(identity_raw)
    evidence, inventory = json.loads(evidence_raw), json.loads(inventory_raw)

    if git_head(v1_repo) != V1_COMPLETED_COMMIT:
        raise ValueError("V1 archival worktree is not at the accepted completed commit")
    if identity.get("git_head") != V1_RUN_SOURCE_COMMIT:
        raise ValueError("V1 execution identity does not match the source commit that created the attempt")
    if identity.get("pretest_freeze_sha256") != V1_FREEZE_SHA256:
        raise ValueError("V1 pretest-freeze identity mismatch")
    if status.get("state") != "inconclusive_calibration_gate":
        raise ValueError("V1 attempt is not the documented pre-evaluation calibration-gate stop")
    calls = status.get("sampler_calls_started")
    if not isinstance(calls, list) or len(calls) != 33 or any(c.get("state") != "committed" for c in calls):
        raise ValueError("V1 attempt does not have exactly 33 fully committed training/calibration calls")
    if any(c.get("phase") == "evaluation" for c in calls):
        raise ValueError("V1 has evaluation call metadata; reuse is not allowed")
    if status.get("shots_started") != 18000 or status.get("shots_committed") != 18000:
        raise ValueError("V1 status shot counts are not exactly 18,000")
    if EXPECTED_SHOTS != {"training": 3000, "calibration": 15000, "evaluation": 0}:
        raise AssertionError("internal allocation check failed")

    seed_map = inventory.get("seeds", {})
    call_seeds = []
    phase_shots = {"training": 0, "calibration": 0, "evaluation": 0}
    expected_archive_paths = set()
    for call in calls:
        phase, key, value = call.get("phase"), call.get("key"), call.get("seed")
        seed_key = f"train:{key}" if phase == "training" else key
        if phase not in phase_shots or seed_map.get(seed_key) != value:
            raise ValueError(f"V1 seed/partition mapping mismatch for {key}")
        phase_shots[phase] += int(call.get("shots", 0))
        call_seeds.append(value)
        expected_archive_paths.add(call.get("archive"))
    if len(set(call_seeds)) != 33:
        raise ValueError("V1 training/calibration seeds are not unique")
    if phase_shots != EXPECTED_SHOTS:
        raise ValueError(f"V1 phase shot allocation mismatch: {phase_shots}")

    if len(status.get("archives", [])) != 33 or len(evidence.get("archive_manifest", [])) != 33:
        raise ValueError("V1 manifests do not list exactly 33 archives")
    status_by_path = {row["path"]: row for row in status["archives"]}
    evidence_by_path = {row["path"]: row for row in evidence["archive_manifest"]}
    if set(status_by_path) != expected_archive_paths or set(evidence_by_path) != expected_archive_paths:
        raise ValueError("V1 archive path sets disagree with committed sampler calls")

    entries = []
    for rel in sorted(expected_archive_paths):
        if not isinstance(rel, str) or Path(rel).is_absolute() or ".." in Path(rel).parts:
            raise ValueError(f"unsafe archive path in V1 records: {rel!r}")
        path = run.parent / rel
        raw = path.read_bytes()
        digest = sha256(raw)
        status_entry, evidence_entry = status_by_path[rel], evidence_by_path[rel]
        expected_digest = status_entry.get("sha256", status_entry.get("archive_sha256"))
        expected_bytes = status_entry.get("bytes", status_entry.get("archive_bytes"))
        if (digest != expected_digest or digest != evidence_entry.get("sha256") or
                len(raw) != expected_bytes or len(raw) != evidence_entry.get("bytes")):
            raise ValueError(f"V1 archive integrity mismatch: {rel}")
        # Zip member names are inspected without decompressing array data.
        import zipfile
        with zipfile.ZipFile(path, "r") as archive:
            members = set(archive.namelist())
        if members != {"detectors.npy", "observables.npy"}:
            raise ValueError(f"unexpected V1 archive schema for {rel}: {sorted(members)}")
        entries.append({"path": rel, "sha256": digest, "bytes": len(raw),
                        "shots": int(status_entry["shots"]),
                        "partition": "training" if "/training/" in f"/{rel}" else "calibration",
                        "detector_array_loaded": False, "observable_array_loaded": False})

    evaluation_dir = run / "evaluation"
    eval_files = [p.name for p in evaluation_dir.iterdir() if p.is_file()]
    if eval_files:
        raise ValueError("V1 evaluation directory is not empty")
    return {
        "schema": "qshift-v1-1-verified-reuse-v1",
        "source_v1_completed_commit": V1_COMPLETED_COMMIT,
        "source_v1_attempt_commit": V1_RUN_SOURCE_COMMIT,
        "source_v1_pretest_freeze_sha256": V1_FREEZE_SHA256,
        "v1_run_status_sha256": sha256(status_raw),
        "v1_execution_identity_sha256": sha256(identity_raw),
        "v1_failed_attempt_manifest_sha256": sha256(evidence_raw),
        "v1_seed_inventory_sha256": sha256(inventory_raw),
        "v1_terminal_state": status["state"],
        "v1_sampler_calls": len(calls),
        "v1_committed_shots": 18000,
        "v1_phase_shots": phase_shots,
        "v1_phase_sampling_seconds": {
            phase: float(sum(float(c.get("sampling_seconds", 0.0)) for c in calls if c.get("phase") == phase))
            for phase in ("training", "calibration", "evaluation")
        },
        "v1_archive_bytes": int(sum(int(row["bytes"]) for row in status["archives"])),
        "v1_evaluation_calls": 0,
        "v1_evaluation_archives": 0,
        "archive_count": len(entries),
        "archives": entries,
        "archives_verified_by_sha256": True,
        "archive_array_policy": "only archive container names were inspected; no arrays were decompressed during this verification",
        "reuse_policy": "V1.1 may read only the detectors member; stored V1 observables are prohibited and are never copied",
        "training_observable_arrays_stored_in_v1_archives": True,
        "training_observable_arrays_read_by_v1_1_verifier": False,
        "calibration_observable_arrays_stored_in_v1_archives": True,
        "calibration_observable_arrays_read_by_v1_1_verifier": False,
        "evaluation_observable_arrays_exist": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v1-repo", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.v1_repo.resolve())
    out = Path(__file__).resolve().parent / "REUSE_VERIFICATION.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: result[k] for k in ("v1_terminal_state", "v1_sampler_calls", "v1_committed_shots", "archive_count", "v1_evaluation_archives", "archives_verified_by_sha256")}, indent=2))


if __name__ == "__main__":
    main()
