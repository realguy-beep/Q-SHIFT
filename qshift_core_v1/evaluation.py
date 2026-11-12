"""Paired evaluation records over caller-supplied arrays; never samples shots."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict
from numbers import Real
from typing import Mapping

import numpy as np

from .contracts import DecoderMetadata, DecoderPrediction, DecoderProtocol, binary_matrix

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
    detector_source = np.asarray(detectors)
    observable_source = np.asarray(observables)
    detector_bits = binary_matrix(detector_source, name="detectors")
    labels = observable_source
    if labels.ndim == 1:
        labels = labels[:, None]
    label_bits = binary_matrix(labels, name="observables")
    if len(detector_bits) != len(label_bits):
        raise ValueError("Detector and observable shot counts differ.")
    if len(detector_bits) == 0:
        raise ValueError("Paired evaluation requires at least one shot.")
    registered_metadata: dict[str, DecoderMetadata] = {}
    for name, decoder in decoders.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Decoder mapping keys must be nonempty strings.")
        if not callable(getattr(decoder, "decode", None)):
            raise TypeError(f"Registered decoder {name!r} must provide decode().")
        metadata = getattr(decoder, "metadata", None)
        if not isinstance(metadata, DecoderMetadata):
            raise TypeError(f"Registered decoder {name!r} must expose DecoderMetadata.")
        if name != metadata.name:
            raise ValueError("Decoder mapping keys must match each decoder's metadata name.")
        if metadata.detector_count != detector_bits.shape[1]:
            raise ValueError(f"Decoder {name!r} expects {metadata.detector_count} detectors; "
                             f"the paired samples contain {detector_bits.shape[1]}.")
        if metadata.observable_count != label_bits.shape[1]:
            raise ValueError(f"Decoder {name!r} declares {metadata.observable_count} observables; "
                             f"the paired labels contain {label_bits.shape[1]}.")
        registered_metadata[name] = metadata

    hasher = hashlib.sha256()
    hasher.update(detector_bits.tobytes(order="C"))
    hasher.update(label_bits.tobytes(order="C"))
    sample_sha256 = hasher.hexdigest()
    detector_identity = {
        "provided_shape": list(detector_source.shape),
        "provided_dtype": str(detector_source.dtype),
        "canonical_shape": list(detector_bits.shape),
        "canonical_dtype": str(detector_bits.dtype),
        "convention": "unpacked binary uint8 [shots, detectors], detector IDs in caller-provided column order",
    }
    observable_identity = {
        "provided_shape": list(observable_source.shape),
        "provided_dtype": str(observable_source.dtype),
        "canonical_shape": list(label_bits.shape),
        "canonical_dtype": str(label_bits.dtype),
        "convention": "unpacked binary uint8 [shots, observables]; 1D input is normalized to one observable",
    }
    metadata_identity = {
        name: asdict(metadata) for name, metadata in sorted(registered_metadata.items())
    }
    identity_payload = {
        "identity_schema": "qshift-paired-evidence-v1",
        "scope": scope,
        "sample_id": sample_id,
        "legacy_sample_sha256": sample_sha256,
        "detectors": detector_identity,
        "observables": observable_identity,
        "decoder_metadata": metadata_identity,
        "error_unit": "one shot is an error if any logical observable differs",
    }
    evidence_sha256 = hashlib.sha256(
        json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    records: dict[str, dict] = {}
    error_masks: dict[str, np.ndarray] = {}
    prediction_bits: dict[str, np.ndarray] = {}
    for name, decoder in decoders.items():
        # Separate copy prevents one adapter mutating the shared source array.
        prediction = decoder.decode(detector_bits.copy())
        if not isinstance(prediction, DecoderPrediction):
            raise TypeError(f"{name} decoder must return DecoderPrediction, got "
                            f"{type(prediction).__name__}.")
        if getattr(decoder, "metadata", None) != registered_metadata[name]:
            raise ValueError(f"{name} decoder metadata changed while paired evaluation was running.")
        if not isinstance(prediction.metadata, DecoderMetadata):
            raise TypeError(f"{name} prediction must contain DecoderMetadata.")
        if prediction.metadata != registered_metadata[name]:
            raise ValueError(
                f"{name} prediction metadata differs from its registered metadata "
                "(identity, implementation/version, dimensions, noise model, correlation mode, "
                "experimental flag, or construction provenance)."
            )
        elapsed = prediction.elapsed_seconds
        if elapsed is not None and (
            isinstance(elapsed, bool) or not isinstance(elapsed, Real)
            or not math.isfinite(elapsed) or elapsed < 0
        ):
            raise ValueError(f"{name} prediction elapsed_seconds must be finite and nonnegative.")
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
            "elapsed_seconds": float(elapsed) if elapsed is not None else None,
            "prediction_disagreements_vs_baseline": None,
            "candidate_only_failures": None,
            "baseline_only_failures": None,
            "decoder_metadata": asdict(registered_metadata[name]),
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
        "sample_identity": {
            **identity_payload,
            "evidence_sha256": evidence_sha256,
            "provenance_limit": (
                "Content identity only; hashes do not prove upstream provenance, authorization, "
                "or absence of leakage."
            ),
        },
        "shots": int(len(labels)),
        "detector_count": int(detector_bits.shape[1]),
        "observable_count": int(label_bits.shape[1]),
        "error_unit": "one shot is an error if any logical observable differs",
        "baseline": baseline_name,
        "records": records,
        "paired_input_identity": "All decoders received byte-identical detector samples; observables were used only after decoding for scoring.",
    }
