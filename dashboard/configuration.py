"""Input validation and resource limits for local run controls."""
from __future__ import annotations

import math
from numbers import Integral, Real
from typing import Any

PRESETS = {
    "smoke": {"training_shots": 8000, "validation_shots": 1000, "test_shots": 1000,
              "label": "Smoke test · 10K total (8K train + 1K validation + 1K test)"},
    "pipeline": {"training_shots": 100000, "validation_shots": 5000, "test_shots": 5000,
                 "label": "Pipeline validation · 100K train"},
    "initial": {"training_shots": 1000000, "validation_shots": 10000, "test_shots": 10000,
                "label": "Initial training · 1M train"},
    "architecture": {"training_shots": 10000000, "validation_shots": 20000, "test_shots": 20000,
                      "label": "Architecture comparison · 10M train"},
    "scaling": {"training_shots": 100000000, "validation_shots": 20000, "test_shots": 20000,
                "label": "Scaling experiment · 100M train"},
    "extended": {"training_shots": 1000000000, "validation_shots": 20000, "test_shots": 20000,
                 "label": "Extended experiment · 1B train"},
}

DEFAULT_CONFIG = {
    "preset": "smoke", "model_selection": "direct_plus_residual",
    "training_shots": 8000, "validation_shots": 1000, "test_shots": 1000,
    "batch_size": 256, "learning_rate": 0.001, "noise_regime": "balanced",
    "memory_basis": "z", "gate_p": 0.003, "measurement_p": 0.003,
    "bias_ratio": 10.0, "validation_frequency_steps": 8,
    "checkpoint_frequency_steps": 8, "seed": 1_800_000_001, "device": "auto",
    "distance": 3, "rounds": 5, "mixed_precision": True,
}


MAX_STIM_SEED = 2_147_483_647


def _strict_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an integer.")
    return int(value)


def _strict_float(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a number.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite.")
    return result


def validate_config(raw: dict[str, Any]) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("Configuration must be a JSON object.")
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(raw)
    if not isinstance(cfg["preset"], str) or cfg["preset"] not in PRESETS:
        raise ValueError("Unknown training preset.")
    if not isinstance(cfg["model_selection"], str) or cfg["model_selection"] not in {"direct_mlp", "direct_plus_residual"}:
        raise ValueError("Choose Direct MLP or Direct + PyMatching residual.")
    if not isinstance(cfg["noise_regime"], str) or cfg["noise_regime"] not in {"x_biased", "balanced", "z_biased"}:
        raise ValueError("Noise regime must be x_biased, balanced, or z_biased.")
    if not isinstance(cfg["memory_basis"], str) or cfg["memory_basis"] not in {"x", "z"}:
        raise ValueError("Memory basis must be x or z.")
    if not isinstance(cfg["device"], str) or cfg["device"] not in {"auto", "cuda", "cpu"}:
        raise ValueError("Device must be auto, cuda, or cpu.")
    cfg["distance"] = _strict_int(cfg["distance"], "distance")
    cfg["rounds"] = _strict_int(cfg["rounds"], "rounds")
    if cfg["distance"] != 3 or cfg["rounds"] != 5:
        raise ValueError("This dashboard pilot is locked to the audited distance-3, five-round Phase 2B circuit.")
    for key in ("training_shots", "validation_shots", "test_shots", "batch_size",
                "validation_frequency_steps", "checkpoint_frequency_steps", "seed"):
        cfg[key] = _strict_int(cfg[key], key)
    if not 1 <= cfg["training_shots"] <= 1_000_000_000:
        raise ValueError("Training shots must be in [1, 1,000,000,000].")
    if not 1 <= cfg["validation_shots"] <= 100_000 or not 1 <= cfg["test_shots"] <= 100_000:
        raise ValueError("Validation and test budgets must each be in [1, 100,000].")
    if not 32 <= cfg["batch_size"] <= 4096:
        raise ValueError("Batch size must be in [32, 4096].")
    if not 1 <= cfg["seed"] <= MAX_STIM_SEED:
        raise ValueError(f"Seed must be in [1, {MAX_STIM_SEED}].")
    if not 1 <= cfg["validation_frequency_steps"] <= math.ceil(cfg["training_shots"] / cfg["batch_size"]):
        raise ValueError("Validation frequency is outside the training step count.")
    if not 1 <= cfg["checkpoint_frequency_steps"] <= math.ceil(cfg["training_shots"] / cfg["batch_size"]):
        raise ValueError("Checkpoint frequency is outside the training step count.")
    cfg["learning_rate"] = _strict_float(cfg["learning_rate"], "learning_rate")
    if not 1e-5 <= cfg["learning_rate"] <= 1e-2:
        raise ValueError("Learning rate must be between 1e-5 and 1e-2.")
    for key in ("gate_p", "measurement_p"):
        cfg[key] = _strict_float(cfg[key], key)
        if not 0.0 <= cfg[key] <= 0.1:
            raise ValueError(f"{key} must be in [0, 0.1].")
    cfg["bias_ratio"] = _strict_float(cfg["bias_ratio"], "bias_ratio")
    if not 1.0 <= cfg["bias_ratio"] <= 100.0:
        raise ValueError("Pauli bias ratio must be in [1, 100].")
    if type(cfg["mixed_precision"]) is not bool:
        raise ValueError("mixed_precision must be a boolean.")
    return cfg


def needs_confirmation(training_shots: int) -> str | None:
    if training_shots > 10_000_000:
        return "extreme"
    if training_shots > 10_000:
        return "large"
    return None

