"""Immutable identifiers and allocation arithmetic copied from NS-4A V2."""
from __future__ import annotations

from dataclasses import dataclass


CONDITIONS = (
    "balanced_no_burst",
    "x_biased_no_burst",
    "z_biased_no_burst",
    "balanced_burst_0.005",
    "balanced_burst_0.010",
    "balanced_burst_0.015",
)
MODEL_FAMILIES = CONDITIONS
MODES = ("ordinary_pymatching", "correlation_enabled_pymatching")
CANDIDATE_IDS = tuple(f"{family}::{mode}" for family in MODEL_FAMILIES for mode in MODES)
EVALUATION_ARMS = (
    "nominal_ordinary_pymatching",
    "nominal_correlation_enabled_pymatching",
    "pooled_selected_fixed_pymatching",
    "matched_selected_dem_pymatching_other_mode_control",
    "beliefmatching_same_selected_dem",
)

SELECTION_ROOTS_PER_CONDITION = 8
EVALUATION_ROOTS_PER_CONDITION = 10
EVALUATION_SHOTS_PER_ROOT = 4_000
SELECTION_SHOTS_PER_ROOT_BASE = 1_333
SELECTION_UNIQUE_SHOTS = 64_000
EVALUATION_UNIQUE_SHOTS = 240_000
TOTAL_UNIQUE_SHOTS = 304_000
PRIMARY_BOOTSTRAP_REPLICATES = 100_000
SIGN_FLIP_REPLICATES = 100_000
SELECTION_RANK_BOOTSTRAP_REPLICATES = 20_000


class ProtocolValidationError(ValueError):
    """Input contradicts the prospective NS-4A V2 allocation or roster."""


def selection_shots(condition_index: int, root_index: int) -> int:
    """Return V2's deterministic 1,333/1,334 selection allocation."""
    if type(condition_index) is not int or not 0 <= condition_index < 6:
        raise ProtocolValidationError("condition_index must be an integer in [0, 5].")
    if type(root_index) is not int or not 0 <= root_index < SELECTION_ROOTS_PER_CONDITION:
        raise ProtocolValidationError("root_index must be an integer in [0, 7].")
    extra_roots = 3 if condition_index < 4 else 2
    return SELECTION_SHOTS_PER_ROOT_BASE + int(root_index < extra_roots)


def make_root_id(partition: str, condition_id: str, root_index: int) -> str:
    max_roots = 8 if partition == "selection" else 10 if partition == "evaluation" else 0
    if condition_id not in CONDITIONS or type(root_index) is not int or not 0 <= root_index < max_roots:
        raise ProtocolValidationError("invalid partition/condition/root index for canonical root ID.")
    return f"{partition}:{condition_id}:r{root_index:02d}"


def parse_root_id(partition: str, condition_id: str, root_id: str) -> int:
    prefix = f"{partition}:{condition_id}:r"
    if not isinstance(root_id, str) or not root_id.startswith(prefix):
        raise ProtocolValidationError("root_id is not canonical for its partition and condition.")
    suffix = root_id[len(prefix):]
    if len(suffix) != 2 or not suffix.isdigit():
        raise ProtocolValidationError("root_id must end with a two-digit root index.")
    index = int(suffix)
    if root_id != make_root_id(partition, condition_id, index):
        raise ProtocolValidationError("root_id contains an invalid root index.")
    return index


def shots_for_root(partition: str, condition_id: str, root_index: int) -> int:
    if partition == "selection":
        return selection_shots(CONDITIONS.index(condition_id), root_index)
    if partition == "evaluation" and condition_id in CONDITIONS and type(root_index) is int and 0 <= root_index < 10:
        return EVALUATION_SHOTS_PER_ROOT
    raise ProtocolValidationError("invalid partition/condition/root allocation.")


def validate_allocation() -> dict[str, int]:
    selection = sum(selection_shots(c, r) for c in range(6) for r in range(8))
    evaluation = len(CONDITIONS) * EVALUATION_ROOTS_PER_CONDITION * EVALUATION_SHOTS_PER_ROOT
    if selection != SELECTION_UNIQUE_SHOTS:
        raise ProtocolValidationError(f"selection allocation is {selection}, expected 64000.")
    if evaluation != EVALUATION_UNIQUE_SHOTS:
        raise ProtocolValidationError(f"evaluation allocation is {evaluation}, expected 240000.")
    if selection + evaluation != TOTAL_UNIQUE_SHOTS:
        raise ProtocolValidationError("total allocation differs from the 304000-shot ceiling.")
    return {"selection": selection, "evaluation": evaluation, "total": selection + evaluation}


@dataclass(frozen=True)
class CandidateScore:
    candidate_id: str
    numerator: int
    denominator: int

    @property
    def value(self) -> float:
        return self.numerator / self.denominator
