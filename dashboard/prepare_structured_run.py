"""Create a collision-screened configuration for the structured worker.

Nothing is sampled by this script. Use structured_worker.py explicitly to run
the resulting configuration. The worker does not implement test sampling.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for p in (str(ROOT), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

from structured_training import (REGIMES, make_development_inventory, make_scale_inventory,
                                 scale_budget_allocation)


def saved_allocations():
    try:
        from manager import WorkerManager
        return WorkerManager().allocations()
    except Exception:
        return []


def prepare(args):
    prior = saved_allocations()
    if args.mode == "development":
        inv = make_development_inventory(args.train_per_regime, args.validation_per_regime,
                                         args.batch_size, prior)
        if not inv["passed"]:
            raise SystemExit(f"Seed preflight failed: {inv['collisions']}")
        config = {"mode": "development", "experiment_id": "qshift_structured_development_v1",
                  "training_shots_by_regime": {r: args.train_per_regime for r in REGIMES},
                  "validation_shots_by_regime": {r: args.validation_per_regime for r in REGIMES},
                  "batch_size": args.batch_size, "candidates": args.candidates,
                  "learning_rate": args.learning_rate, "weight_decay": 0.0001,
                  "max_epochs": args.epochs, "early_stopping_patience": 1,
                  "checkpoint_frequency_steps": args.checkpoint_frequency,
                  "max_wall_seconds_per_invocation": args.max_wall_seconds,
                  "device": args.device, "seed_inventory": inv,
                  "noise_parameters": {"distance": 3, "rounds": 5, "basis": "z",
                                       "gate_p": 0.003, "measurement_p": 0.003,
                                       "bias_ratio": 10.0},
                  "test_access": "disabled; development validation only"}
    else:
        inv = make_scale_inventory(args.budget, args.batch_size, prior)
        if not inv.get("passed"):
            raise SystemExit(f"Seed preflight failed: {inv.get('collisions')}")
        allocation = scale_budget_allocation(args.budget)
        if args.budget == 100_000:
            train = {r: 23_334 if r == "x_biased" else 23_333 for r in REGIMES}
            validation = {r: 5_000 for r in REGIMES}
            mode = "official_100k"
            candidates = ["direct_mlp", "residual_mlp", "structured_ch8_unweighted",
                          "structured_ch8_weighted", "structured_ch16_unweighted",
                          "structured_ch16_weighted"]
        else:
            train, validation, mode = allocation["training"], allocation["validation"], "development"
            candidates = args.candidates
        config = {"mode": mode, "experiment_id": f"qshift_structured_budget_{args.budget}_v1",
                  "training_shots_by_regime": train,
                  "validation_shots_by_regime": validation,
                  "budget": allocation, "batch_size": args.batch_size, "candidates": candidates,
                  "learning_rate": args.learning_rate, "weight_decay": 0.0001,
                  "max_epochs": args.epochs, "early_stopping_patience": 1,
                  "checkpoint_frequency_steps": args.checkpoint_frequency,
                  "max_wall_seconds_per_invocation": args.max_wall_seconds,
                  "device": args.device,
                  "seed_inventory": inv,
                  "noise_parameters": {"distance": 3, "rounds": 5, "basis": "z",
                                       "gate_p": 0.003, "measurement_p": 0.003,
                                       "bias_ratio": 10.0},
                  "test_access": "reserved and never sampled by this worker"}
        if args.budget != 100_000:
            config["mode"] = "development"
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    inventory_path = output.with_name(output.stem + "_seed_inventory.json")
    inventory_path.write_text(json.dumps(inv, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"config": str(output), "seed_inventory": str(inventory_path),
                      "passed": inv.get("passed"), "unique_derived_seed_count": inv.get("unique_derived_seed_count", inv.get("unique_seed_count")),
                      "collisions": inv.get("collisions", []),
                      "test_policy": config["test_access"]}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("development", "budget"), default="development")
    parser.add_argument("--budget", type=int, choices=(100_000, 1_000_000, 10_000_000, 100_000_000), default=100_000)
    parser.add_argument("--train-per-regime", type=int, default=2_000)
    parser.add_argument("--validation-per-regime", type=int, default=1_000)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--checkpoint-frequency", type=int, default=8)
    parser.add_argument("--max-wall-seconds", type=float, default=28_800,
                        help="Maximum worker time for one invocation before safe pause; default 8 hours.")
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    parser.add_argument("--candidates", nargs="+", default=["direct_mlp", "residual_mlp",
                    "structured_ch8_unweighted", "structured_ch8_weighted"])
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "neural_decoder_diagnostic" /
                        "structured_integration" / "development_config.json")
    prepare(parser.parse_args())


if __name__ == "__main__":
    main()
