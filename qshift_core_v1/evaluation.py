"""Paired evaluation records over caller-supplied arrays; never samples shots."""
from __future__ import annotations

import hashlib
from typing import Mapping

import numpy as np

from .contracts import DecoderProtocol, binary_matrix

ALLOWED_SCOPES = frozenset({"development", "heldout-development"})


def evaluate_paired(
    detectors: np.ndarray,
    observables: np.ndarray,
    decoders: Mapping[str, DecoderProtocol],
    *,
    baseline_name: str,
    scope: str,
    sample_id: str,
) -> dict:
    """Score decoders on one shared sample array and preserve shot pairing.

    This library function refuses the protected-test scope. The frozen,
    separately authorized study runner remains responsible for protected
    evaluations and must not call this development utility.
    """
    if not isinstance(scope, str):
        raise ValueError("scope must be a string.")
    if scope not in ALLOWED_SCOPES:
        if scope == "protected-test":
            raise PermissionError("Protected-test evaluation is not supported by this development API.")
        raise ValueError(f"Unsupported evaluation scope {scope!r}.")
    if not isinstance(sample_id, str) or not sample_id.strip():
        raise ValueError("sample_id is required for paired evidence provenance.")
    if not decoders or baseline_name not in decoders:
        raise ValueError("A nonempty decoder map containing baseline_name is required.")
    detector_bits = binary_matrix(detectors, name="detectors")
    labels = np.asarray(observables)
    if labels.ndim == 1:
        labels = labels[:, None]
    label_bits = binary_matrix(labels, name="observables")
    if len(detector_bits) != len(label_bits):
        raise ValueError("Detector and observable shot counts differ.")
    if len(detector_bits) == 0:
        raise ValueError("Paired evaluation requires at least one shot.")
    if any(decoder.metadata.detector_count != detector_bits.shape[1] for decoder in decoders.values()):
        raise ValueError("At least one decoder expects a different detector count.")
    if any(name != decoder.metadata.name for name, decoder in decoders.items()):
        raise ValueError("Decoder mapping keys must match each decoder's metadata name.")
    if any(decoder.metadata.observable_count != label_bits.shape[1] for decoder in decoders.values()):
        raise ValueError("At least one decoder expects a different observable count.")

    hasher = hashlib.sha256()
    hasher.update(detector_bits.tobytes(order="C"))
    hasher.update(label_bits.tobytes(order="C"))
    sample_sha256 = hasher.hexdigest()
    records: dict[str, dict] = {}
    error_masks: dict[str, np.ndarray] = {}
    prediction_bits: dict[str, np.ndarray] = {}
    for name, decoder in decoders.items():
        # Separate copy prevents one adapter mutating the shared source array.
        prediction = decoder.decode(detector_bits.copy())
        bits = binary_matrix(
            prediction.bits,
            name=f"{name} predictions",
            columns=label_bits.shape[1],
        )
        if bits.shape != label_bits.shape:
            raise ValueError(f"{name} predictions have shape {bits.shape}; expected {label_bits.shape}.")
        wrong = np.any(bits != label_bits, axis=1)
        errors = int(np.count_nonzero(wrong))
        prediction_bits[name] = bits
        error_masks[name] = wrong
        records[name] = {
            "shots": int(len(labels)),
            "errors": errors,
            "logical_error_rate": errors / len(labels) if len(labels) else None,
            "elapsed_seconds": prediction.elapsed_seconds,
            "prediction_disagreements_vs_baseline": None,
            "candidate_only_failures": None,
            "baseline_only_failures": None,
            "decoder_metadata": prediction.metadata.__dict__,
        }

    baseline_errors = error_masks[baseline_name]
    baseline_prediction = prediction_bits[baseline_name]
    for name in decoders:
        if name == baseline_name:
            continue
        candidate_errors = error_masks[name]
        records[name]["prediction_disagreements_vs_baseline"] = int(
            np.count_nonzero(np.any(prediction_bits[name] != baseline_prediction, axis=1))
        )
        records[name]["candidate_only_failures"] = int(np.count_nonzero(candidate_errors & ~baseline_errors))
        records[name]["baseline_only_failures"] = int(np.count_nonzero(~candidate_errors & baseline_errors))

    return {
        "schema_version": 1,
        "scope": scope,
        "sample_id": sample_id,
        "sample_sha256": sample_sha256,
        "shots": int(len(labels)),
        "detector_count": int(detector_bits.shape[1]),
        "observable_count": int(label_bits.shape[1]),
        "error_unit": "one shot is an error if any logical observable differs",
        "baseline": baseline_name,
        "records": records,
        "paired_input_identity": "All decoders received byte-identical detector samples; observables were used only after decoding for scoring.",
    }
