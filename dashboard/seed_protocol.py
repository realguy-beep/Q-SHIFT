"""Deterministic, separated sample-stream allocation for dashboard runs."""
from __future__ import annotations

import json
from numbers import Integral
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_SCAN = REPO_ROOT / "outputs" / "headroom_feasibility" / "HISTORICAL_SEED_SCAN.json"
TRAIN_OFFSET = 0
VALIDATION_OFFSET = 50_000_000
TEST_OFFSET = 60_000_000
MODEL_OFFSET = 70_000_000
MAX_STIM_SEED = 2_147_483_647


def _strict_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an integer.")
    return int(value)


def batches(shots: int, batch_size: int) -> int:
    shots = _strict_int(shots, "shots")
    batch_size = _strict_int(batch_size, "batch_size")
    if shots <= 0 or batch_size <= 0:
        raise ValueError("shot and batch sizes must be positive")
    return (shots + batch_size - 1) // batch_size


def seed_plan(base_seed: int, training_shots: int, validation_shots: int,
              test_shots: int, batch_size: int) -> dict:
    base_seed = _strict_int(base_seed, "base_seed")
    if not 1 <= base_seed <= MAX_STIM_SEED:
        raise ValueError(f"seed must be in [1, {MAX_STIM_SEED}]")
    train_n = batches(training_shots, batch_size)
    val_n = batches(validation_shots, batch_size)
    test_n = batches(test_shots, batch_size)
    ranges = {
        "train": [base_seed + TRAIN_OFFSET, base_seed + TRAIN_OFFSET + train_n - 1],
        "validation": [base_seed + VALIDATION_OFFSET, base_seed + VALIDATION_OFFSET + val_n - 1],
        "test": [base_seed + TEST_OFFSET, base_seed + TEST_OFFSET + test_n - 1],
        "model_rng": [base_seed + MODEL_OFFSET, base_seed + MODEL_OFFSET],
    }
    for name, (lo, hi) in ranges.items():
        if lo < 1 or hi > MAX_STIM_SEED:
            raise ValueError(f"{name} stream exceeds Stim's supported seed range")
    names = list(ranges)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if max(ranges[a][0], ranges[b][0]) <= min(ranges[a][1], ranges[b][1]):
                raise ValueError(f"derived stream overlap: {a} and {b}")
    return {
        "base_seed": base_seed,
        "method": "split-specific root offsets; deterministic batch seed = stream root + batch index",
        "stream_ranges_inclusive": ranges,
        "batches": {"train": train_n, "validation": val_n, "test": test_n},
        "shots": {"train": _strict_int(training_shots, "training_shots"),
                  "validation": _strict_int(validation_shots, "validation_shots"),
                  "test": _strict_int(test_shots, "test_shots")},
        "no_overlap_within_run": True,
        "max_stim_seed": MAX_STIM_SEED,
    }


def historical_seeds() -> set[int]:
    if not HISTORICAL_SCAN.is_file():
        return set()
    data = json.loads(HISTORICAL_SCAN.read_text(encoding="utf-8"))
    return {int(v) for v in data.get("recoverable_unique_seed_values", [])
            if isinstance(v, (int, float, str)) and str(v).lstrip("+-").isdigit()}


def screen_plan(plan: dict, extra_allocations: list[dict] | None = None) -> dict:
    hist = historical_seeds()
    collisions = []
    for stream, (lo, hi) in plan["stream_ranges_inclusive"].items():
        hits = sorted(s for s in hist if lo <= s <= hi)
        collisions.extend({"stream": stream, "seed": s, "source": "historical_seed_scan"} for s in hits)
    for prior in extra_allocations or []:
        prev = prior.get("stream_ranges_inclusive", {})
        for stream, (lo, hi) in plan["stream_ranges_inclusive"].items():
            for prev_name, (p_lo, p_hi) in prev.items():
                if max(lo, p_lo) <= min(hi, p_hi):
                    collisions.append({"stream": stream, "other_stream": prev_name,
                                       "overlap": [max(lo, p_lo), min(hi, p_hi)],
                                       "source": "prior_dashboard_run"})
    return {
        "historical_seed_scan": str(HISTORICAL_SCAN.relative_to(REPO_ROOT)) if HISTORICAL_SCAN.exists() else None,
        "historical_seed_values_checked": len(hist),
        "collisions": collisions,
        "passed": not collisions,
        "coverage_limit": "only seeds recoverable from the archived historical scan and prior dashboard run manifests are screened",
    }


def batch_seed(plan: dict, split: str, batch_index: int) -> int:
    batch_index = _strict_int(batch_index, "batch_index")
    if split not in ("train", "validation", "test"):
        raise ValueError("split must be train, validation, or test")
    if not 0 <= batch_index < plan["batches"][split]:
        raise ValueError("batch index is outside the frozen stream")
    return int(plan["stream_ranges_inclusive"][split][0] + batch_index)
