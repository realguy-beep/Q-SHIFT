"""Create/verify the prospective Stage 4 feasibility-pilot input freeze."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FREEZE = HERE / "STAGE4_FEASIBILITY_FREEZE.json"

FROZEN_FILES = [
    "AGENTS.md",
    "outputs/cnn_architecture_stage2_v1/stage2_config.json",
    "outputs/cnn_architecture_stage2_v1/CNN_STAGE2_RESULTS.md",
    "outputs/cnn_architecture_stage2_v1/CNN_STAGE2_INDEPENDENT_AUDIT.md",
    "outputs/cnn_stage3_residual_gate_v1/stage3_config.json",
    "outputs/cnn_stage3_residual_gate_v1/CNN_STAGE3_PROTOCOL.md",
    "outputs/cnn_stage3_residual_gate_v1/CNN_STAGE3_RESULTS.json",
    "outputs/cnn_stage3_residual_gate_v1/CNN_STAGE3_AUDIT_RESULTS.json",
    "outputs/phase3a_correlated_noise_preflight/simulator.py",
    "outputs/phase3a_correlated_noise_preflight/PREFLIGHT_RESULTS.json",
    "outputs/phase2b_pauli_bias/noise_model.py",
    "outputs/stage4_noise_adaptive_feasibility_v1/STAGE4_FEASIBILITY_REVIEW.md",
    "outputs/stage4_noise_adaptive_feasibility_v1/STAGE4_NOISE_ESTIMATION_DESIGN.md",
    "outputs/stage4_noise_adaptive_feasibility_v1/STAGE4_PROPOSED_PROTOCOL.md",
    "outputs/stage4_noise_adaptive_feasibility_v1/stage4_feasibility_config.json",
    "outputs/stage4_noise_adaptive_feasibility_v1/seed_inventory.json",
    "outputs/stage4_noise_adaptive_feasibility_v1/seed_audit.json",
    "outputs/stage4_noise_adaptive_feasibility_v1/SEED_AUDIT_INITIAL_EXTRACTION_BUG.json",
    "outputs/stage4_noise_adaptive_feasibility_v1/STAGE4_PROPOSED_SEED_PLAN.json",
    "outputs/stage4_noise_adaptive_feasibility_v1/REPRODUCE.md",
    "outputs/stage4_noise_adaptive_feasibility_v1/prepare_stage4.py",
    "outputs/stage4_noise_adaptive_feasibility_v1/freeze_stage4.py",
    "outputs/stage4_noise_adaptive_feasibility_v1/prototype.py",
    "outputs/stage4_noise_adaptive_feasibility_v1/run_identifiability_pilot.py",
    "outputs/stage4_noise_adaptive_feasibility_v1/tests/test_prototype.py",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def current_inputs() -> dict[str, dict]:
    out = {}
    for rel in FROZEN_FILES:
        path = REPO / rel
        if not path.is_file():
            raise FileNotFoundError(f"missing frozen input: {rel}")
        out[rel] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    return out


def create() -> dict:
    run = HERE / "run_v1"
    if run.exists():
        raise RuntimeError("run_v1 already exists; refusing to replace pilot evidence")
    if FREEZE.exists():
        raise RuntimeError("freeze already exists; refusing to overwrite historical freeze")
    data = {
        "freeze_status": "PRE_SAMPLING_FROZEN",
        "scope": "small detector-only identifiability and decoder-rebuild pilot; not full Stage 4",
        "shot_budget": 48000,
        "inputs": current_inputs(),
    }
    tmp = FREEZE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(FREEZE)
    return data


def verify() -> dict:
    data = json.loads(FREEZE.read_text(encoding="utf-8"))
    current = current_inputs()
    differences = []
    for rel, expected in data["inputs"].items():
        actual = current.get(rel)
        if actual != expected:
            differences.append({"file": rel, "expected": expected, "actual": actual})
    if set(current) != set(data["inputs"]):
        differences.append({"file": "input inventory", "expected": sorted(data["inputs"]), "actual": sorted(current)})
    if differences:
        raise RuntimeError(f"freeze verification failed: {differences}")
    return {"status": "PASS", "shot_budget": data["shot_budget"], "verified_inputs": len(current)}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--create", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.create == args.verify:
        parser.error("select exactly one of --create or --verify")
    print(json.dumps(create() if args.create else verify(), indent=2))

