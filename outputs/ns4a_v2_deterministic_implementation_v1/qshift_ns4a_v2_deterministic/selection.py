"""Twelve-candidate, selection-only pooled-fixed scoring contract."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
from typing import Mapping, Protocol

import numpy as np

from qshift_core_v1.contracts import DecoderPrediction, binary_matrix

from .protocol import CANDIDATE_IDS, CONDITIONS, MODEL_FAMILIES, MODES, make_root_id, selection_shots
from .sample_schema import ArchiveValidationError, make_sample_ids, validate_paired_sample_ids


class SelectionError(ValueError):
    """Selection batch/grid is incomplete or not paired as specified."""


class DetectorDecoder(Protocol):
    metadata: object

    def decode(self, detectors: np.ndarray) -> DecoderPrediction: ...


@dataclass(frozen=True)
class SelectionRootScore:
    condition_id: str
    root_index: int
    root_id: str
    shots: int
    errors_by_candidate: Mapping[str, int]


@dataclass(frozen=True)
class SelectionBatchResult:
    root_score: SelectionRootScore
    predictions_by_candidate: Mapping[str, np.ndarray]
    detector_sha256: str
    row_identity_sha256: str


def candidate_roster(model_families: tuple[str, ...] = MODEL_FAMILIES,
                     modes: tuple[str, ...] = MODES) -> tuple[str, ...]:
    return tuple(f"{family}::{mode}" for family in model_families for mode in modes)


def run_and_score_selection_batch(
    *, condition_id: str, root_index: int, root_id: str,
    detectors: object, detector_sample_ids: tuple[str, ...],
    labels: object, label_sample_ids: tuple[str, ...],
    prediction_sample_ids: tuple[str, ...],
    decoders: Mapping[str, DetectorDecoder],
) -> SelectionBatchResult:
    """Decode a selection batch detector-only; labels are touched afterward.

    Every candidate receives an independent immutable copy of identical
    detector bytes. The condition/root labels are not passed to decoders.
    """
    if condition_id not in CONDITIONS or type(root_index) is not int or not 0 <= root_index < 8:
        raise SelectionError("invalid selection condition or root index.")
    if root_id != f"selection:{condition_id}:r{root_index:02d}":
        raise SelectionError("root_id must encode the declared selection condition/root index.")
    if tuple(decoders.keys()) != CANDIDATE_IDS:
        raise SelectionError("the decoder mapping must contain all 12 candidates in frozen order.")

    detector_bits = binary_matrix(detectors, name="selection detectors", columns=40)
    shots = len(detector_bits)
    expected_shots = selection_shots(CONDITIONS.index(condition_id), root_index)
    if shots != expected_shots:
        raise SelectionError(f"root received {shots} shots; V2 allocation requires {expected_shots}.")
    try:
        ids = validate_paired_sample_ids(detector_sample_ids, label_sample_ids, prediction_sample_ids)
    except ArchiveValidationError as exc:
        raise SelectionError(str(exc)) from exc
    if len(ids) != shots:
        raise SelectionError("sample ID count differs from detector shot count.")
    if ids != make_sample_ids("selection", condition_id, root_id, shots):
        raise SelectionError("sample IDs do not match the declared selection root offsets.")

    original = detector_bits.tobytes(order="C")
    import hashlib
    detector_digest = hashlib.sha256(original).hexdigest()
    row_digest = hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()
    predictions: dict[str, np.ndarray] = {}
    for candidate_id in CANDIDATE_IDS:
        model_input = np.array(detector_bits, dtype=np.uint8, order="C", copy=True)
        model_input.setflags(write=False)
        result = decoders[candidate_id].decode(model_input)
        if not isinstance(result, DecoderPrediction):
            raise SelectionError(f"{candidate_id} did not return DecoderPrediction.")
        expected_metadata = getattr(decoders[candidate_id], "metadata", None)
        if expected_metadata is None or result.metadata != expected_metadata:
            raise SelectionError(f"{candidate_id} prediction metadata differs from its registered decoder.")
        bits = np.asarray(result.bits)
        if bits.shape != (shots, 1) or bits.dtype != np.dtype(np.uint8) or np.any(bits > 1):
            raise SelectionError(f"{candidate_id} returned an invalid prediction shape/dtype/value.")
        predictions[candidate_id] = np.array(bits, copy=True)
        if detector_bits.tobytes(order="C") != original:
            raise SelectionError("paired evaluation input was mutated by a decoder.")

    # Intentionally convert/read labels only after all candidate decoders return.
    label_array = np.asarray(labels)
    if label_array.ndim == 1:
        label_array = label_array[:, None]
    observable_bits = binary_matrix(label_array, name="selection labels", columns=1)
    if observable_bits.shape != (shots, 1):
        raise SelectionError("selection label shape differs from detector rows.")
    errors = {
        candidate_id: int(np.count_nonzero(predictions[candidate_id] != observable_bits))
        for candidate_id in CANDIDATE_IDS
    }
    return SelectionBatchResult(
        SelectionRootScore(condition_id, root_index, root_id, shots, errors),
        predictions, detector_digest, row_digest,
    )


def _validate_root_scores(records: tuple[SelectionRootScore, ...] | list[SelectionRootScore]) -> dict[str, dict[int, SelectionRootScore]]:
    by_condition: dict[str, dict[int, SelectionRootScore]] = {condition: {} for condition in CONDITIONS}
    seen_root_ids: set[str] = set()
    for record in records:
        if record.condition_id not in by_condition or type(record.root_index) is not int or not 0 <= record.root_index < 8:
            raise SelectionError("invalid selection root/condition record.")
        if record.root_id != make_root_id("selection", record.condition_id, record.root_index):
            raise SelectionError("selection root_id does not match its condition/root index.")
        if record.root_index in by_condition[record.condition_id]:
            raise SelectionError("duplicate selection root-condition record.")
        if record.root_id in seen_root_ids:
            raise SelectionError("root IDs must be unique across selection conditions.")
        seen_root_ids.add(record.root_id)
        if record.shots != selection_shots(CONDITIONS.index(record.condition_id), record.root_index):
            raise SelectionError("selection root shot count differs from the frozen 1,333/1,334 schedule.")
        if tuple(record.errors_by_candidate.keys()) != CANDIDATE_IDS:
            raise SelectionError("every root must report all 12 candidates in frozen order.")
        for errors in record.errors_by_candidate.values():
            if type(errors) is not int or not 0 <= errors <= record.shots:
                raise SelectionError("candidate error count must be an integer within the root shot count.")
        by_condition[record.condition_id][record.root_index] = record
    for condition, roots in by_condition.items():
        if tuple(sorted(roots)) != tuple(range(8)):
            raise SelectionError(f"selection condition {condition} must contain root indices 0..7 exactly once.")
    return by_condition


def selection_scores(records: tuple[SelectionRootScore, ...] | list[SelectionRootScore]) -> tuple[tuple[str, Fraction], ...]:
    """Exact equal-condition/equal-root score for each candidate."""
    by_condition = _validate_root_scores(records)
    values: list[tuple[str, Fraction]] = []
    for candidate_id in CANDIDATE_IDS:
        condition_means = []
        for condition in CONDITIONS:
            condition_means.append(sum(
                (Fraction(by_condition[condition][r].errors_by_candidate[candidate_id], by_condition[condition][r].shots)
                 for r in range(8)), Fraction(0, 1)
            ) / 8)
        values.append((candidate_id, sum(condition_means, Fraction(0, 1)) / 6))
    return tuple(values)


def choose_global_candidate(records: tuple[SelectionRootScore, ...] | list[SelectionRootScore]) -> dict[str, object]:
    scores = selection_scores(records)
    best_score = min(value for _, value in scores)
    tied = tuple(candidate for candidate, value in scores if value == best_score)
    # selection_scores follows the frozen family-major, ordinary-before-correlated roster.
    selected = tied[0]
    return {
        "selected_candidate": selected,
        "exact_tie_set": tied,
        "score_fraction_by_candidate": {name: f"{score.numerator}/{score.denominator}" for name, score in scores},
        "score_by_candidate": {name: float(score) for name, score in scores},
        "candidate_order": CANDIDATE_IDS,
        "selection_conditions": CONDITIONS,
    }
