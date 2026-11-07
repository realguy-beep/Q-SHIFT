"""Small paired CPU integration check for atomic pause/resume equivalence.

Uses fresh development roots and never creates or reads a test split. The same
small development samples are replayed only to compare uninterrupted versus
resumed training determinism.
"""
from __future__ import annotations

import json
import hashlib
import tempfile
import argparse
from pathlib import Path
import sys

import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

from seed_protocol import historical_seeds
from structured_training import inventory_seed_values, run, screen_inventory
from structured_protocol import build_inventory


def make_inventory() -> dict:
    regimes = ("x_biased", "balanced", "z_biased")
    streams = []
    for split, first in (("train", 1_190_000_001), ("validation", 1_190_050_001)):
        for i, regime in enumerate(regimes):
            root = first + 10_000 * i
            seeds = list(range(root, root + 3))
            streams.append({"split": split, "regime": regime, "root": root, "shots": 96,
                            "batch_size": 32, "batch_count": 3,
                            "seed_range_inclusive": [root, root + 2], "seeds": seeds})
    model_seed = 1_190_100_001
    model_seeds = list(range(model_seed, model_seed + 6))
    diagnostics = [1_190_200_001, 1_190_200_002, 1_190_200_003]
    all_values = {s for stream in streams for s in stream["seeds"]} | set(model_seeds) | set(diagnostics)
    inventory = {"passed": True, "train_per_regime": 96, "validation_per_regime": 96,
                 "batch_size": 32, "model_seed": model_seed, "model_seeds": model_seeds,
                 "diagnostic_seeds": diagnostics, "streams": streams,
                 "unique_derived_seed_count": len(all_values), "derived_seed_count": len(all_values)}
    frozen = build_inventory()
    if all_values & inventory_seed_values(frozen) or all_values & historical_seeds():
        raise RuntimeError("Resume-test roots collide with recovered or frozen seeds.")
    screen = screen_inventory(inventory, prior_allocations=[], candidate_count=1)
    if not screen["passed"]:
        raise RuntimeError(f"Resume-test seed preflight failed: {screen['collisions']}")
    return inventory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "neural_decoder_diagnostic" /
                        "structured_integration" / "resume_equivalence_audit.json")
    args = parser.parse_args()
    inventory = make_inventory()
    cfg = {"mode": "development", "experiment_id": "qshift_resume_equivalence_small_v1",
           "training_shots_by_regime": {r: 96 for r in ("x_biased", "balanced", "z_biased")},
           "validation_shots_by_regime": {r: 96 for r in ("x_biased", "balanced", "z_biased")},
           "batch_size": 32, "candidates": ["structured_ch8_unweighted"],
           "learning_rate": 0.001, "weight_decay": 0.0001, "max_epochs": 2,
           "early_stopping_patience": 1, "checkpoint_frequency_steps": 1,
           "max_wall_seconds_per_invocation": 0, "device": "cpu",
           "seed_inventory": inventory, "test_access": "disabled"}
    with tempfile.TemporaryDirectory(prefix="qshift-structured-resume-") as td:
        root = Path(td)
        cfg_path = root / "config.json"
        cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        paused_dir = root / "paused"
        did_pause = False
        def request_pause(event):
            nonlocal did_pause
            if not did_pause and event.get("type") == "progress":
                (paused_dir / "control.request").write_text("pause", encoding="utf-8")
                did_pause = True
        paused = run(cfg_path, paused_dir, event_callback=request_pause, prior_allocations=[])
        if paused.get("status") != "paused" or not did_pause:
            raise AssertionError("Runner did not pause at a checkpointed minibatch boundary.")
        resumed = run(cfg_path, paused_dir, resume=True, prior_allocations=[])
        uninterrupted = run(cfg_path, root / "uninterrupted", prior_allocations=[])
        if (resumed.get("candidate_fits", {}).get("structured_ch8_unweighted", {}).get("status") != "completed"
                or uninterrupted.get("candidate_fits", {}).get("structured_ch8_unweighted", {}).get("status") != "completed"):
            raise AssertionError("One of the small integration fits failed to complete.")
        partial_weights = torch.load(paused_dir / "best_models" / "structured_ch8_unweighted.pt",
                                     map_location="cpu", weights_only=False)["state_dict"]
        full_weights = torch.load(root / "uninterrupted" / "best_models" / "structured_ch8_unweighted.pt",
                                  map_location="cpu", weights_only=False)["state_dict"]
        for key in full_weights:
            if not torch.equal(partial_weights[key], full_weights[key]):
                raise AssertionError(f"Resumed model differs from uninterrupted model at {key}.")
        paused_evidence = sorted((paused_dir / "validation_evidence").glob("*.npz"))
        full_evidence = sorted((root / "uninterrupted" / "validation_evidence").glob("*.npz"))
        if len(paused_evidence) != len(full_evidence):
            raise AssertionError("Resumed/uninterrupted evidence file counts differ.")
        report = {"status": "PASS", "pause_requested": did_pause,
                  "resumed_global_steps": resumed["candidate_fits"]["structured_ch8_unweighted"]["global_steps"],
                  "uninterrupted_global_steps": uninterrupted["candidate_fits"]["structured_ch8_unweighted"]["global_steps"],
                  "best_weights_bitwise_equal": True,
                  "validation_evidence_batch_count": len(paused_evidence),
                  "test_samples_generated_or_accessed": 0,
                  "seed_unique_count": len(inventory_seed_values(inventory)),
                  "seed_replay_note": "The same small collision-screened development seeds are deliberately replayed in this integration check to compare resumed and uninterrupted deterministic training; they are not counted as independent performance data.",
                  "cpu_only": True}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({**report, "output": str(args.output.resolve())}, indent=2))


if __name__ == "__main__":
    main()
