"""Detector-only paired evaluation for the five frozen NS-4A V2 arms."""
from __future__ import annotations

from typing import Mapping, Protocol

import numpy as np

from qshift_core_v1.contracts import DecoderPrediction, binary_matrix

from .protocol import EVALUATION_ARMS, CONDITIONS
from .sample_schema import ArchiveValidationError, make_sample_ids, validate_paired_sample_ids


class PairedEvaluationError(ValueError):
    """Evaluation fixture violates row identity, decoder, or output contract."""


class DecoderLike(Protocol):
    metadata: object

    def decode(self, detectors: np.ndarray) -> DecoderPrediction: ...


def run_paired_evaluation_batch(
    *, condition_id: str, root_index: int, root_id: str,
    detectors: object, detector_sample_ids: tuple[str, ...],
    labels: object, label_sample_ids: tuple[str, ...],
    prediction_sample_ids: tuple[str, ...], decoders: Mapping[str, DecoderLike],
) -> dict[str, object]:
    if condition_id not in CONDITIONS or type(root_index) is not int or not 0 <= root_index < 10:
        raise PairedEvaluationError("invalid evaluation condition/root index.")
    if root_id != f"evaluation:{condition_id}:r{root_index:02d}":
        raise PairedEvaluationError("root_id must encode the declared evaluation condition/root index.")
    if tuple(decoders.keys()) != EVALUATION_ARMS:
        raise PairedEvaluationError("all five evaluation arms must be registered in frozen order.")
    detector_bits = binary_matrix(detectors, name="evaluation detectors", columns=40)
    if detector_bits.shape[0] != 4_000:
        raise PairedEvaluationError("each evaluation root must contain exactly 4000 rows.")
    try:
        ids = validate_paired_sample_ids(detector_sample_ids, label_sample_ids, prediction_sample_ids)
    except ArchiveValidationError as exc:
        raise PairedEvaluationError(str(exc)) from exc
    if ids != make_sample_ids("evaluation", condition_id, root_id, 4_000):
        raise PairedEvaluationError("evaluation sample IDs do not match canonical root offsets.")
    if len(ids) != len(detector_bits):
        raise PairedEvaluationError("evaluation sample ID count differs from detector rows.")

    original = detector_bits.tobytes(order="C")
    predictions: dict[str, np.ndarray] = {}
    for arm in EVALUATION_ARMS:
        model_input = np.array(detector_bits, dtype=np.uint8, order="C", copy=True)
        model_input.setflags(write=False)
        result = decoders[arm].decode(model_input)
        if not isinstance(result, DecoderPrediction):
            raise PairedEvaluationError(f"{arm} did not return DecoderPrediction.")
        metadata = getattr(decoders[arm], "metadata", None)
        if metadata is None or result.metadata != metadata:
            raise PairedEvaluationError(f"{arm} metadata differs from registered decoder metadata.")
        bits = np.asarray(result.bits)
        if bits.shape != (4_000, 1) or bits.dtype != np.dtype(np.uint8) or np.any(bits > 1):
            raise PairedEvaluationError(f"{arm} returned invalid binary predictions.")
        predictions[arm] = np.array(bits, copy=True)
        if detector_bits.tobytes(order="C") != original:
            raise PairedEvaluationError("decoder mutated the paired detector input.")

    # Logical labels become visible to the scorer only after every arm returns.
    label_array = np.asarray(labels)
    if label_array.ndim == 1:
        label_array = label_array[:, None]
    observable_bits = binary_matrix(label_array, name="evaluation labels", columns=1)
    if observable_bits.shape != (4_000, 1):
        raise PairedEvaluationError("evaluation label shape differs from detector rows.")

    errors = {arm: int(np.count_nonzero(predictions[arm] != observable_bits)) for arm in EVALUATION_ARMS}
    primary = "pooled_selected_fixed_pymatching"
    candidate = "beliefmatching_same_selected_dem"
    candidate_wrong = predictions[candidate] != observable_bits
    baseline_wrong = predictions[primary] != observable_bits
    return {
        "shots": 4_000,
        "sample_id_sha256": __import__("hashlib").sha256("\n".join(ids).encode("utf-8")).hexdigest(),
        "errors_by_arm": errors,
        "primary_paired_discordances": {
            "BM_wrong_PM_correct": int(np.count_nonzero(candidate_wrong & ~baseline_wrong)),
            "BM_correct_PM_wrong": int(np.count_nonzero(~candidate_wrong & baseline_wrong)),
        },
        "predictions_by_arm": predictions,
        "labels_read_after_all_decoders": True,
    }
