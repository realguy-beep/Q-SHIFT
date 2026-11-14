"""Build the NS-5A versioned source/evidence hash manifest (no sampling)."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESEARCH = ROOT / "outputs" / "qshift_method_landscape_research_v1"
OUTPUT = HERE / "SOURCE_HASH_MANIFEST.json"
BASE = "cae447e30d3179ac40586471ee80f535c3c21f87"
ADDITIONAL_INPUTS = (
    "AGENTS.md",
    "outputs/phase2b_pauli_bias/noise_model.py",
    "outputs/phase3a_correlated_noise_preflight/simulator.py",
    "outputs/qshift_method_landscape_research_v1/efactor_fixedpoint_mixture_audit.py",
    "outputs/qshift_method_landscape_research_v1/EFACTOR_FIXEDPOINT_MIXTURE_AUDIT_PRE_THRESHOLD_FIX.json",
    "outputs/qshift_method_landscape_research_v1/EFACTOR_FIXEDPOINT_MIXTURE_AUDIT.json",
    "outputs/qshift_method_landscape_research_v1/test_efactor_mixture_recurrence.py",
    "outputs/qshift_method_landscape_research_v1/EXACT_THREE_PARAMETER_EFACTOR_ENVELOPE.json",
    "outputs/qshift_method_landscape_research_v1/exact_three_parameter_efactor_envelope.py",
    "outputs/qshift_method_landscape_research_v1/CATEGORICAL_CIRCUIT_FEATURE_EXPECTATIONS.json",
    "outputs/qshift_method_landscape_research_v1/categorical_circuit_feature_expectations.py",
    "outputs/qshift_method_landscape_research_v1/PUBLISHED_EDGE_MOMENT_INVERSION_AUDIT.json",
    "outputs/qshift_method_landscape_research_v1/published_edge_moment_inversion_audit.py",
    "outputs/qshift_method_landscape_research_v1/THREE_PARAMETER_DETECTOR_IDENTIFIABILITY.json",
    "outputs/qshift_method_landscape_research_v1/three_parameter_detector_identifiability.py",
    "outputs/qshift_method_landscape_research_v1/EFACTOR_MIXTURE_CHANGEPOINT_DELAY.json",
    "outputs/qshift_method_landscape_research_v1/efactor_mixture_changepoint_delay.py",
    "outputs/qshift_method_landscape_research_v1/EFACTOR_FREEDMAN_MEAN_RANGE_BOUNDS.json",
    "outputs/qshift_method_landscape_research_v1/efactor_freedman_mean_range_bounds.py",
    "outputs/qshift_method_landscape_research_v1/DEM_THREE_PARAMETER_ENVELOPE_TRANSFER.json",
    "outputs/qshift_method_landscape_research_v1/dem_three_parameter_envelope_transfer.py",
    "outputs/qshift_method_landscape_research_v1/RESEARCH_LOG.md",
    "outputs/qshift_method_landscape_research_v1/SOURCE_VERIFICATION.md",
    "outputs/qshift_method_landscape_research_v1/UNRESOLVED_QUESTIONS.md",
    "outputs/qshift_method_landscape_research_v1/LITERATURE_DATABASE.md",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def base_is_ancestor() -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=ROOT).returncode == 0


def file_record(path: Path, relative: str) -> dict:
    return {"path": relative.replace("\\", "/"), "bytes": path.stat().st_size, "sha256": sha256(path)}


def main() -> None:
    if not base_is_ancestor():
        raise SystemExit(f"required source base {BASE} is not an ancestor of {git_head()}")
    historical_diff = subprocess.run(
        ["git", "diff", "--quiet", BASE, "HEAD", "--", "outputs/qshift_method_landscape_research_v1"],
        cwd=ROOT,
    )
    if historical_diff.returncode != 0:
        raise SystemExit("historical research package differs from the approved base commit")
    research_files = sorted(p for p in RESEARCH.rglob("*") if p.is_file())
    if len(research_files) != 139:
        raise SystemExit(f"research package inventory drift: expected 139 files, found {len(research_files)}")
    historical = [file_record(p, p.relative_to(ROOT).as_posix()) for p in research_files]
    additional = []
    for rel in ADDITIONAL_INPUTS:
        p = ROOT / rel
        if not p.is_file():
            raise SystemExit(f"missing allowlisted input: {rel}")
        rec = file_record(p, rel)
        if rec not in historical:
            additional.append(rec)
    new_outputs = []
    for p in sorted(HERE.rglob("*")):
        if not p.is_file() or p == OUTPUT or "__pycache__" in p.parts:
            continue
        new_outputs.append(file_record(p, p.relative_to(ROOT).as_posix()))
    manifest = {
        "manifest_version": "ns5a-source-evidence-v1",
        "base_commit": BASE,
        "worktree_branch_expected": "codex/ns5a-mathematical-audit-v1",
        "research_package": {
            "path": "outputs/qshift_method_landscape_research_v1",
            "file_count": len(historical),
            "files": historical,
        },
        "additional_source_and_audit_inputs": additional,
        "new_versioned_outputs_excluding_this_manifest": new_outputs,
        "self_hash_excluded": True,
        "scope": "Read-only historical evidence plus deterministic mathematical audit; no scientific experiment.",
        "workspace_metadata_scope_deviation": "A final read-only status query in the separate main development checkout exposed pre-existing Stage 5-related untracked pathnames only; no listed contents were inspected or changed. Run/live-marker status is unknown.",
        "sampling_calls": 0,
        "new_detector_shots": 0,
        "decoder_evaluations": 0,
        "sealed_outcome_access": False,
    }
    OUTPUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "manifest": str(OUTPUT.relative_to(ROOT)).replace("\\", "/"),
        "research_files": len(historical),
        "additional_inputs": len(additional),
        "new_outputs": len(new_outputs),
        "manifest_sha256": sha256(OUTPUT),
    }, indent=2))


if __name__ == "__main__":
    main()
