"""Read-only verification of the published Stage 5 evidence package.

Uses the included internal-audit per-root records and the frozen statistical
implementation already present in the Q-SHIFT repository. It never samples
Stim circuits or opens the local/raw recovery archives.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[1]
STATS_DIR = ROOT / "outputs/stage5_secondary_inference_repair_v1"
sys.path.insert(0, str(STATS_DIR))
from stage5_statistics_repaired import analyze  # noqa: E402

PROBS = (0.0, 0.004, 0.008, 0.012, 0.016)
ROOTS_PER_CONDITION = 1210
SHOTS_PER_ROOT = 2500
EXPECTED_ROOTS = 6050
EXPECTED_SHOTS = 27_225_000


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def compare_tree(a, b, path="statistics"):
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            raise AssertionError(f"key mismatch at {path}")
        for k in a:
            compare_tree(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            raise AssertionError(f"length mismatch at {path}")
        for i, (x, y) in enumerate(zip(a, b)):
            compare_tree(x, y, f"{path}[{i}]")
    elif isinstance(a, bool) or isinstance(b, bool):
        if a != b:
            raise AssertionError(f"boolean mismatch at {path}")
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if not math.isclose(float(a), float(b), rel_tol=1e-13, abs_tol=1e-15):
            raise AssertionError(f"numeric mismatch at {path}: {a} != {b}")
    elif a != b:
        raise AssertionError(f"value mismatch at {path}")


def main() -> None:
    manifest = json.loads((PACKAGE / "EVIDENCE_MANIFEST.json").read_text(encoding="utf-8"))
    if manifest.get("format") != "qshift-stage5-publication-evidence-v1":
        raise AssertionError("unexpected evidence manifest format")
    for rel, info in manifest["published_files"].items():
        p = PACKAGE / rel
        if not p.is_file() or digest(p) != info["sha256"] or p.stat().st_size != info["size_bytes"]:
            raise AssertionError(f"published-file hash/size mismatch: {rel}")
    if set(manifest["published_files"]) != {
        p.relative_to(PACKAGE).as_posix()
        for p in PACKAGE.rglob("*")
        if p.is_file() and p.name != "EVIDENCE_MANIFEST.json"
    }:
        raise AssertionError("published file inventory is incomplete or has unexpected files")

    # Verify the active 53-file Stage 5 freeze against its actual SHA map.
    # The broader readiness evidence manifest separately lists 56 files; that
    # count includes readiness records and is not the active freeze count.
    freeze_path = ROOT / "outputs/stage5_secondary_inference_repair_v1/STAGE5_PRETEST_FREEZE_V2.json"
    if digest(freeze_path) != manifest["active_stage5_freeze_sha256"]:
        raise AssertionError("active Stage 5 freeze file hash mismatch")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    frozen = manifest["active_stage5_frozen_sources"]
    if len(frozen) != 53 or len(freeze["sha256"]) != 53:
        raise AssertionError("active Stage 5 source inventory must contain 53 frozen files")
    for rel, info in frozen.items():
        if rel not in freeze["sha256"]:
            raise AssertionError(f"source file absent from active freeze: {rel}")
        expected_hash = freeze["sha256"][rel]
        path = ROOT / rel
        if not path.is_file() or digest(path) != info["sha256"] or path.stat().st_size != info["size_bytes"]:
            raise AssertionError(f"active Stage 5 frozen source mismatch: {rel}")
        if info["sha256"] != expected_hash:
            raise AssertionError(f"active freeze and publication inventory disagree: {rel}")

    readiness_path = ROOT / manifest["readiness_evidence_manifest_path"]
    if digest(readiness_path) != manifest["readiness_evidence_manifest_sha256"]:
        raise AssertionError("readiness evidence manifest hash mismatch")
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    readiness_files = manifest["readiness_inventory_files"]
    if len(readiness_files) != 56 or len(readiness["files"]) != 56:
        raise AssertionError("readiness inventory must contain its recorded 56 files")
    if readiness.get("active_freeze_file_count") != 53:
        raise AssertionError("readiness inventory's active freeze count changed")
    for rel, info in readiness_files.items():
        expected_key = Path(rel).relative_to(Path("outputs/stage5_secondary_inference_repair_v1")).as_posix()
        expected = readiness["files"].get(expected_key)
        path = ROOT / rel
        if expected is None or not path.is_file():
            raise AssertionError(f"readiness source missing: {rel}")
        if digest(path) != info["sha256"] or path.stat().st_size != info["size_bytes"]:
            raise AssertionError(f"readiness source hash/size mismatch: {rel}")
        if info["sha256"] != expected["sha256"] or info["size_bytes"] != expected["bytes"]:
            raise AssertionError(f"readiness source and publication inventory disagree: {rel}")

    # Verify the v3.4.4 source snapshot against its original frozen inventory.
    v44_dir = PACKAGE / "source/v3.4.4"
    v44_manifest = json.loads((v44_dir / "V44_EVIDENCE_MANIFEST.json").read_text(encoding="utf-8"))
    if digest(v44_dir / "V44_EVIDENCE_MANIFEST.json") != manifest["v3_4_4_source_manifest_sha256"]:
        raise AssertionError("v3.4.4 source manifest hash mismatch")
    if len(v44_manifest["files"]) != 19 or len(manifest["v3_4_4_sources"]) != 19:
        raise AssertionError("v3.4.4 source inventory must contain 19 files")
    if v44_manifest.get("stage5_recovery_executed") is not False:
        raise AssertionError("v3.4.4 pre-run safety freeze metadata changed")
    for rel, info in manifest["v3_4_4_sources"].items():
        path = v44_dir / rel
        frozen = v44_manifest["files"].get(rel)
        if frozen is None or not path.is_file():
            raise AssertionError(f"v3.4.4 frozen source missing: {rel}")
        if digest(path) != info["sha256"] or path.stat().st_size != info["size_bytes"]:
            raise AssertionError(f"v3.4.4 published source hash mismatch: {rel}")
        if info["sha256"] != frozen["sha256"] or info["size_bytes"] != frozen["size_bytes"]:
            raise AssertionError(f"v3.4.4 source manifest and publication inventory disagree: {rel}")

    for rel, info in manifest["published_original_artifacts"].items():
        if info["copy_status"] != "byte_identical":
            raise AssertionError(f"historical artifact was not marked as an exact copy: {rel}")
        if info["source_sha256"] != info["published_sha256"] or info["source_size_bytes"] != info["published_size_bytes"]:
            raise AssertionError(f"historical source/copy hash record differs: {rel}")
        if digest(PACKAGE / rel) != info["published_sha256"]:
            raise AssertionError(f"historical published copy hash differs: {rel}")
    redacted = json.loads((PACKAGE / "RECOVERY_PROVENANCE_REDACTED.json").read_text(encoding="utf-8"))
    redaction = manifest["redacted_provenance_artifact"]
    if redaction["copy_status"] != "redacted_derivative" or redaction["sha256"] != redacted["original_unredacted_provenance_sha256"]:
        raise AssertionError("redacted provenance does not document the original hash")
    deviation = manifest["historical_safety_report_hash_deviation"]
    limitations = (PACKAGE / "LIMITATIONS.md").read_text(encoding="utf-8")
    if deviation["expected_sha256"] not in limitations or deviation["observed_sha256"] not in limitations:
        raise AssertionError("historical safety-report hash deviation is not fully disclosed")
    failed_run = manifest["historical_failed_run_inventory"]
    if failed_run["verified_original_files"] != 265 or failed_run["current_verification"] != {"files_checked": 265, "mismatches": 0}:
        raise AssertionError("original failed-run inventory reconciliation is incomplete")

    # Fail closed if publication content contains a user-home path or a likely credential.
    banned = [
        re.compile(r"(?i)[A-Z]:\\Users\\"),
        re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
        re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ]
    for p in PACKAGE.rglob("*"):
        if p.is_file() and p.suffix.lower() not in {".npz", ".npy", ".pt", ".pth", ".ckpt"}:
            raw = p.read_bytes()
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue
            for pattern in banned:
                if pattern.search(content):
                    raise AssertionError(f"sensitive-pattern match in {p.name}")
    if any(next(PACKAGE.rglob(ext), None) is not None for ext in ("*.npz", "*.npy", "*.pt", "*.pth", "*.ckpt")):
        raise AssertionError("unexpected raw dataset or model checkpoint included")

    result = json.loads((PACKAGE / "RESULTS.json").read_text(encoding="utf-8"))
    audit = json.loads((PACKAGE / "INDEPENDENT_AUDIT.json").read_text(encoding="utf-8"))
    summary = json.loads((PACKAGE / "RUNNER_SUMMARY.json").read_text(encoding="utf-8"))
    final = json.loads((PACKAGE / "FINALIZATION_MANIFEST.json").read_text(encoding="utf-8"))
    root_manifest = json.loads((PACKAGE / "ROOT_ARCHIVE_MANIFEST.json").read_text(encoding="utf-8"))
    execution = json.loads((PACKAGE / "EXECUTION_RECORD.json").read_text(encoding="utf-8"))

    if audit.get("status") != "PASS_INDEPENDENT_AUDIT" or audit.get("benchmark_only") is not False:
        raise AssertionError("production independent audit did not pass")
    if audit.get("predictions_independently_redecoded") is not True:
        raise AssertionError("predictions lack independent re-decoding")
    if audit.get("roots_verified") != EXPECTED_ROOTS or audit.get("checkpoint_hashes_verified") != EXPECTED_ROOTS:
        raise AssertionError("independent audit root/hash total mismatch")
    if audit.get("unique_shots_recomputed") != EXPECTED_SHOTS:
        raise AssertionError("independently recomputed unique-shot count mismatch")
    if result.get("run_status") != "completed" or result.get("root_count") != EXPECTED_ROOTS or result.get("unique_shots") != EXPECTED_SHOTS:
        raise AssertionError("published run status or allocation mismatch")
    if execution.get("terminal_status") != "completed" or execution.get("roots_verified") != EXPECTED_ROOTS:
        raise AssertionError("execution record does not match terminal result")
    if execution.get("unique_shots_verified") != EXPECTED_SHOTS or execution.get("supervisor_exit_code") != 0:
        raise AssertionError("execution record shot total/exit code mismatch")
    if final.get("root_count") != EXPECTED_ROOTS or final.get("unique_shots") != EXPECTED_SHOTS:
        raise AssertionError("finalization manifest allocation mismatch")
    if root_manifest.get("root_count") != EXPECTED_ROOTS or len(root_manifest.get("sha256", {})) != EXPECTED_ROOTS:
        raise AssertionError("root archive manifest is incomplete")

    audit_rows = audit.get("per_root", [])
    summary_rows = summary.get("per_root", [])
    if len(audit_rows) != EXPECTED_ROOTS or len(summary_rows) != EXPECTED_ROOTS:
        raise AssertionError("per-root record count mismatch")
    audit_map = {}
    groups = {p: [] for p in PROBS}
    condition = {p: {"roots": 0, "shots": 0, "fixed": 0, "adaptive": 0, "oracle": 0,
                     "adaptive_only": 0, "fixed_only": 0} for p in PROBS}
    for row in audit_rows:
        p, r = float(row["probability"]), int(row["root"])
        key = (p, r)
        if key in audit_map or p not in condition or not 0 <= r < ROOTS_PER_CONDITION:
            raise AssertionError(f"duplicate/invalid root key {key}")
        if row["shots"] != SHOTS_PER_ROOT or len(row["errors"]) != 3:
            raise AssertionError(f"invalid root shot/error shape {key}")
        name = f"root_p{p:.3f}_r{r:03d}.npz"
        if root_manifest["sha256"].get(name) != row["archive_sha256"]:
            raise AssertionError(f"root archive hash differs from audit row {name}")
        audit_map[key] = row
        fixed, adaptive, oracle = map(int, row["errors"])
        groups[p].append((adaptive - fixed) / SHOTS_PER_ROOT)
        c = condition[p]
        c["roots"] += 1
        c["shots"] += SHOTS_PER_ROOT
        c["fixed"] += fixed
        c["adaptive"] += adaptive
        c["oracle"] += oracle
        c["adaptive_only"] += int(row["candidate_only"])
        c["fixed_only"] += int(row["fixed_only"])

    summary_map = {(float(x["probability"]), int(x["root"])): x for x in summary_rows}
    if len(summary_map) != EXPECTED_ROOTS or set(summary_map) != set(audit_map):
        raise AssertionError("runner summary condition/root grid differs from audit")
    for key, row in audit_map.items():
        s = summary_map[key]
        expected = list(map(int, row["errors"]))
        if [int(s["fixed_errors"]), int(s["profile_errors"]), int(s["oracle_errors"])] != expected:
            raise AssertionError(f"runner/auditor per-root error mismatch {key}")
        if int(s["candidate_only"]) != int(row["candidate_only"]) or int(s["fixed_only"]) != int(row["fixed_only"]):
            raise AssertionError(f"runner/auditor paired-discordance mismatch {key}")

    with (PACKAGE / "PER_ROOT_RESULTS.csv").open(newline="", encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(f))
    if len(csv_rows) != EXPECTED_ROOTS:
        raise AssertionError("published per-root CSV count mismatch")
    for row in csv_rows:
        key = (float(row["condition_probability"]), int(row["root_index"]))
        if key not in audit_map or row["archive_sha256"] != audit_map[key]["archive_sha256"]:
            raise AssertionError(f"published CSV root/hash mismatch {key}")
        source = audit_map[key]
        summary = summary_map[key]
        fixed, adaptive, oracle = map(int, source["errors"])
        expected_counts = {
            "evaluation_shots": int(source["shots"]),
            "fixed_errors": fixed,
            "adaptive_errors": adaptive,
            "oracle_reference_errors": oracle,
            "adaptive_only_failures": int(source["candidate_only"]),
            "fixed_only_failures": int(source["fixed_only"]),
            "paired_prediction_disagreements": int(summary["prediction_disagreements"]),
        }
        for field, expected in expected_counts.items():
            if int(row[field]) != expected:
                raise AssertionError(f"published CSV count mismatch {key} {field}")
        expected_rates = {
            "fixed_ler": fixed / SHOTS_PER_ROOT,
            "adaptive_ler": adaptive / SHOTS_PER_ROOT,
            "oracle_reference_ler": oracle / SHOTS_PER_ROOT,
            "adaptive_minus_fixed_ler": (adaptive - fixed) / SHOTS_PER_ROOT,
        }
        for field, expected in expected_rates.items():
            if not math.isclose(float(row[field]), expected, rel_tol=1e-13, abs_tol=1e-15):
                raise AssertionError(f"published CSV rate mismatch {key} {field}")

    config = json.loads((STATS_DIR / "STAGE5_REPAIR_CONFIG.json").read_text(encoding="utf-8"))
    reproduced = analyze(groups, config, ROOTS_PER_CONDITION)
    compare_tree(reproduced, result["statistics"])
    for p, row in condition.items():
        published = result["conditions"][str(p)]
        shots = row["shots"]
        if row["roots"] != ROOTS_PER_CONDITION or shots != 3_025_000:
            raise AssertionError(f"condition allocation mismatch {p}")
        checks = {
            "fixed_errors": row["fixed"], "adaptive_errors": row["adaptive"], "oracle_errors": row["oracle"],
            "adaptive_only_failures": row["adaptive_only"], "fixed_only_failures": row["fixed_only"],
        }
        for field, value in checks.items():
            if int(published[field]) != value:
                raise AssertionError(f"condition aggregate mismatch {p} {field}")

    if result["decision"] != "PASS_ENDPOINT_B_AND_P0_NO_HARM":
        raise AssertionError("published frozen decision label mismatch")
    print(json.dumps({
        "status": "PASS_PUBLISHED_PACKAGE",
        "roots": EXPECTED_ROOTS,
        "unique_shots": EXPECTED_SHOTS,
        "audit": audit["status"],
        "primary_delta": reproduced["primary_delta"],
        "primary_upper_bound": reproduced["primary_one_sided_upper_bound"],
        "endpoint_b_pass": reproduced["primary_calibrated_reject"],
        "p0_no_harm_pass": reproduced["p0_no_harm_pass"],
        "secondary_holm": reproduced["secondary_finite_envelope_p_holm"],
    }, indent=2))


if __name__ == "__main__":
    main()
