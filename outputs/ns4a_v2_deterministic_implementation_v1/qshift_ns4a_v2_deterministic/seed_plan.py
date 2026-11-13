"""Validate a later seed inventory; intentionally allocates no seeds."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .protocol import CONDITIONS


SELECTION_STREAM = "selection"
EVALUATION_STREAM = "evaluation"
ANALYSIS_STREAMS = (
    "selection_rank_bootstrap",
    "primary_bootstrap",
    "primary_sign_flip",
    "secondary_sign_flip_bm_vs_selected_dem_ordinary_pm",
    "secondary_sign_flip_bm_vs_selected_dem_correlation_enabled_pm",
    "secondary_sign_flip_selected_pm_vs_nominal_ordinary_pm",
)


class SeedInventoryError(ValueError):
    """Seed inventory is incomplete, colliding, or lacks historical coverage."""


def required_root_keys() -> tuple[tuple[str, str, int], ...]:
    roots = [(SELECTION_STREAM, condition, index) for condition in CONDITIONS for index in range(8)]
    roots.extend((EVALUATION_STREAM, condition, index) for condition in CONDITIONS for index in range(10))
    return tuple(roots)


def validate_seed_inventory(
    inventory: Mapping[str, Any], *, historical_seeds: Sequence[int], historical_coverage_complete: bool,
) -> dict[str, int]:
    """Validate caller-supplied values without generating or reserving values.

    `historical_seeds` must come from a separately authorized, allowlisted
    metadata audit. This function does not discover or open seed files.
    """
    if inventory.get("status") != "candidate_frozen" or inventory.get("numeric_seeds_allocated") is not True:
        raise SeedInventoryError("only an explicitly prepared candidate inventory can be checked.")
    if historical_coverage_complete is not True:
        raise SeedInventoryError("historical seed coverage is incomplete; collision check fails closed.")
    roots = inventory.get("root_seeds")
    if not isinstance(roots, list):
        raise SeedInventoryError("root_seeds must be an explicit list.")
    expected = set(required_root_keys())
    seen_keys: set[tuple[str, str, int]] = set()
    values: list[int] = []
    for entry in roots:
        if not isinstance(entry, Mapping):
            raise SeedInventoryError("each root seed record must be an object.")
        key = (entry.get("partition"), entry.get("condition_id"), entry.get("root_index"))
        if key not in expected or key in seen_keys:
            raise SeedInventoryError(f"unexpected or duplicate root seed key: {key!r}.")
        seen_keys.add(key)
        values.append(_validate_seed(entry.get("seed")))
    if seen_keys != expected:
        raise SeedInventoryError("root seed inventory does not cover all 108 selection/evaluation roots.")

    analyses = inventory.get("analysis_seeds")
    if not isinstance(analyses, list):
        raise SeedInventoryError("analysis_seeds must be an explicit list.")
    analysis_values: list[int] = []
    names: list[str] = []
    for entry in analyses:
        if not isinstance(entry, Mapping):
            raise SeedInventoryError("each analysis seed record must be an object.")
        name = entry.get("stream")
        if name not in ANALYSIS_STREAMS or name in names:
            raise SeedInventoryError(f"unexpected or duplicate analysis stream: {name!r}.")
        names.append(name)
        analysis_values.append(_validate_seed(entry.get("seed")))
    if tuple(names) != ANALYSIS_STREAMS:
        raise SeedInventoryError("analysis streams must appear exactly once in the predeclared order.")

    all_values = values + analysis_values
    historic = [_validate_seed(x) for x in historical_seeds]
    if len(set(all_values)) != len(all_values):
        raise SeedInventoryError("duplicate seed within NS-4A V2 inventory.")
    collision = set(all_values).intersection(historic)
    if collision:
        raise SeedInventoryError("proposed seeds collide with recoverable historical seed metadata.")
    return {"selection_roots": 48, "evaluation_roots": 60, "analysis_streams": 6,
            "total_unique_seed_values": len(all_values), "historical_values_screened": len(set(historic))}


def _validate_seed(value: Any) -> int:
    if type(value) is not int or value < 0 or value > 2**63 - 1:
        raise SeedInventoryError("seed values must be nonnegative signed-64-bit integers.")
    return value
